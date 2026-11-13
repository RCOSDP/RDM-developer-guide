"""grdm-dev up / down / reset — container lifecycle for the rendered profile (SPEC-02 §3, §7).

up     finishes or rolls back an interrupted `db upgrade`/`db rollback`, then refuses (exit 15) a
       runtime/volumes/postgres_data written by another PostgreSQL major than the rendered image, or one whose major
       cannot be read (database.recover_pending, database.preflight, ADR-12); then `docker compose up -d`, then wait for health (exit 40 on timeout),
       then open the browser at http://127.0.0.1:<GRDM_PORT_WEB> unless --no-open; the browser is only opened when stdin is a
       terminal. Idempotent: healthy services are left alone by Compose. Without --timeout the wait is
       DEFAULT_TIMEOUT, or QEMU_TIMEOUT on Linux arm64 when the profile has amd64 services (default_timeout).
down   `docker compose down` — containers stop, volumes stay.
reset  down, then delete runtime/volumes/ after ctx.confirm(). Non-interactive without --yes → exit 2.
       On Linux the files belong to the containers' uids, so the host user cannot remove them: the contents
       are deleted by a root container with only DAC_OVERRIDE and FOWNER, on the local owner-init image, and
       the emptied directory is removed from the host. Exit 14 when that still fails.

Helpers for other modules: running_services(ctx) and recreate(ctx) (used by secrets rotate).
`recreate` is `docker compose up -d --force-recreate`: a plain `restart` keeps the containers' old
environment, so rotated secrets would never reach them (review PR #21 finding 1).
Runner: `runner(argv) -> (rc, stdout)`; tests inject a fake and never need Docker.
"""
from __future__ import annotations

import json
import platform
import shutil
import sys
import webbrowser
from pathlib import Path

from . import compose, database, exit_codes, health, manifest as _manifest, plan, report
from .context import Context

DEFAULT_TIMEOUT = 1800.0  # cold start: the former prebuilt ember's first build under amd64 emulation took 13-25 min and osf_init runs migrations (real install runs 10-18; PR #33 review r1)
# Linux arm64 emulates amd64 with QEMU, which is slower than Rosetta: the former prebuilt ember's first build took 44 min
# there, on one core, so more CPUs do not help, and 1800 s stopped an otherwise healthy install with exit 40 (DEMO-21 run 2).
# About twice the measurement. ember now builds nothing at start (static image); both values stay until a cold start
# without it is measured, and QEMU_TIMEOUT still applies while another service (mfr) runs as linux/amd64.
QEMU_TIMEOUT = 5400.0
_ARM64 = ("aarch64", "arm64")


def default_timeout(ctx: Context, system: str | None = None, machine: str | None = None) -> float:
    """The health wait when --timeout is not given: QEMU_TIMEOUT on Linux arm64 when a service of the profile runs as
    linux/amd64 (manifest build_platform, as doctor counts them), otherwise DEFAULT_TIMEOUT. On macOS Docker Desktop
    reports Darwin here and emulates with Rosetta, so it keeps the default. An unreadable manifest keeps the default."""
    system = system if system is not None else platform.system()
    machine = (machine if machine is not None else platform.machine()).lower()
    if system != "Linux" or machine not in _ARM64:
        return DEFAULT_TIMEOUT
    try:
        man = _manifest.load(ctx)
        services = _manifest.services_for_profile(man, plan.resolve_profile(ctx))
    except (_manifest.ManifestError, ValueError, OSError):
        return DEFAULT_TIMEOUT
    emulated = [s for s in services if "amd64" in str(man.component(s.component).get("build_platform") or "")]
    return QEMU_TIMEOUT if emulated else DEFAULT_TIMEOUT


def default_runner(argv: list[str]) -> tuple[int, str]:
    return health.default_runner(argv)


def streaming_runner(argv: list[str]) -> tuple[int, str]:
    from .build import default_runner as _stream

    return _stream(argv)


def web_url(ctx: Context) -> str:
    from .secrets import DEFAULT_PORTS, env_path, read_env

    port = read_env(env_path(ctx)).get("GRDM_PORT_WEB") or str(DEFAULT_PORTS["web"])
    return f"http://127.0.0.1:{port}/"


def running_services(ctx: Context, runner=None) -> list[str]:
    runner = runner or default_runner
    if not health.compose_path(ctx).exists():
        return []
    rc, out = runner(health.compose_base(ctx) + ["ps", "--format", "json"])
    if rc != 0:
        raise RuntimeError(f"docker compose ps exited {rc}")
    ps = health.parse_ps(out)
    return [name for name, info in ps.items() if str(info.get("State") or info.get("state") or "").lower() == "running"]


def recreate(ctx: Context, runner=None) -> int:
    """Recreate every container of the rendered profile so it reads the current runtime/.env."""
    runner = runner or default_runner
    rc, _ = runner(health.compose_base(ctx) + ["up", "-d", "--force-recreate", "--remove-orphans"])
    return rc


def register(subparsers) -> None:
    up = subparsers.add_parser("up", help="start the profile and wait for health; exit 40 on failure")
    up.add_argument("--no-open", dest="no_open", action="store_true", help="do not open the browser")
    up.add_argument("--timeout", type=float, default=None,
                    help=f"seconds to wait for health (default {int(DEFAULT_TIMEOUT)}; {int(QEMU_TIMEOUT)} on Linux arm64 with amd64 services)")
    up.set_defaults(_module=sys.modules[__name__], lifecycle_action="up")
    down = subparsers.add_parser("down", help="stop containers, keep volumes")
    down.set_defaults(_module=sys.modules[__name__], lifecycle_action="down")
    reset = subparsers.add_parser("reset", help="stop containers and delete runtime/volumes/ (asks first; --yes skips)")
    reset.set_defaults(_module=sys.modules[__name__], lifecycle_action="reset")


def run(ctx: Context, args, runner=None, prober=None, opener=None, sleep=None, rmtree=None) -> int:
    action = getattr(args, "lifecycle_action", None)
    if action == "up":
        given = getattr(args, "timeout", None)
        timeout = float(given) if given is not None else default_timeout(ctx)
        return run_up(ctx, no_open=bool(getattr(args, "no_open", False)), timeout=timeout,
                      runner=runner, prober=prober, opener=opener, sleep=sleep)
    if action == "down":
        return run_down(ctx, runner=runner)
    if action == "reset":
        return run_reset(ctx, runner=runner, rmtree=rmtree)
    return report.error(ctx, exit_codes.USAGE, "choose up, down or reset")


def _require_compose(ctx: Context) -> int | None:
    path = health.compose_path(ctx)
    if not path.exists():
        return report.error(ctx, exit_codes.USAGE, f"{path} not found; run `grdm-dev compose render` first")
    return None


def run_up(ctx: Context, no_open: bool = False, timeout: float = DEFAULT_TIMEOUT, runner=None, prober=None, opener=None, sleep=None) -> int:
    missing = _require_compose(ctx)
    if missing is not None:
        return missing
    # the owner step runs as root against whatever these paths point at when `up` starts (PR #36 review r1 R1-01)
    bad_paths = compose.volume_path_problems(ctx.root, ctx.runtime)
    if bad_paths:
        return report.error(ctx, exit_codes.PREFLIGHT_FAILED, "unsafe volume path: " + "; ".join(bad_paths))
    # Under the lock of `grdm-dev db` (PR #42 review r2 R2-02), from the checks until Compose has started the
    # containers: an interrupted `db upgrade`/`db rollback` is finished or rolled back first; then a server refuses a
    # data directory of another major, or one whose major cannot be read (ADR-12).
    checker = runner or health.default_runner
    with database.lifecycle_lock(ctx) as held:
        db_problem = held or database.recover_pending(ctx, checker) or database.preflight(ctx, checker)
        if db_problem:
            return report.error(ctx, exit_codes.DB_UPGRADE_FAILED, db_problem)
        runner = runner or streaming_runner
        rc, out = runner(health.compose_base(ctx) + ["up", "-d", "--remove-orphans"])
    if rc != 0:
        return report.error(ctx, exit_codes.HEALTH_FAILED, f"docker compose up exited {rc}")
    kwargs = {"runner": runner, "prober": prober}
    if sleep is not None:
        kwargs["sleep"] = sleep
    rows, ok = health.wait_until_healthy(ctx, timeout, **kwargs)
    url = web_url(ctx)
    report.emit(ctx, "up", {"url": url, "healthy": ok, "timeout_s": timeout, "services": rows})
    if not ok:
        bad = ", ".join(r["service"] for r in rows if not r["ok"])
        return report.error(ctx, exit_codes.HEALTH_FAILED, f"not healthy after {int(timeout)}s: {bad}")
    if not no_open and ctx.stdin_is_tty:
        (opener or webbrowser.open)(url)
    sys.stderr.write(f"[grdm-dev] ready: {url}\n")
    return exit_codes.OK


def run_down(ctx: Context, runner=None, volumes: bool = False) -> int:
    missing = _require_compose(ctx)
    if missing is not None:
        return missing
    runner = runner or streaming_runner
    argv = health.compose_base(ctx) + ["down", "--remove-orphans"]
    if volumes:
        argv.append("--volumes")
    rc, _ = runner(argv)
    report.emit(ctx, "down", {"stopped": rc == 0, "volumes_removed": volumes and rc == 0})
    if rc != 0:
        return report.error(ctx, exit_codes.HEALTH_FAILED, f"docker compose down exited {rc}")
    return exit_codes.OK


def wipe_argv(image: str, volumes_dir: Path, platform: str | None) -> list[str]:
    """Delete the contents of runtime/volumes/ as root with only the two capabilities removal needs.
    `--pull never`: the image is ours, built by `build`; no network, read-only root, no new privileges."""
    argv = ["docker", "run", "--rm", "--pull", "never", "--network", "none", "--read-only", "--user", "0:0",
            "--cap-drop", "ALL", "--cap-add", "DAC_OVERRIDE", "--cap-add", "FOWNER", "--security-opt", "no-new-privileges:true"]
    if platform:
        argv += ["--platform", platform]
    return argv + ["-v", f"{volumes_dir}:/volumes", image, "find", "/volumes", "-xdev", "-mindepth", "1", "-delete"]


def _owner_init_service(ctx: Context) -> dict:
    """The owner-init service of the rendered file, {} when there is none to use."""
    try:
        data = json.loads(health.compose_path(ctx).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return (data.get("services") or {}).get(compose.OWNER_INIT_SERVICE) or {}


def run_reset(ctx: Context, runner=None, rmtree=None) -> int:
    volumes_dir = ctx.runtime / "volumes"
    if not ctx.confirm(f"Stop all services and delete {volumes_dir} (all data)?", default=False):
        if not ctx.yes and not ctx.stdin_is_tty:
            return report.error(ctx, exit_codes.USAGE, "reset needs a confirmation; add --yes when no terminal is attached")
        sys.stderr.write("[grdm-dev] reset cancelled\n")
        return exit_codes.OK
    # Checked again at each destructive step (R2-01): `down --volumes`, the root wipe, the host deletion.
    identity = compose.volume_root_identity(ctx.runtime)

    def refused() -> str | None:
        bad = compose.volume_path_problems(ctx.root, ctx.runtime)
        if compose.volume_root_identity(ctx.runtime) != identity:
            bad = [f"{volumes_dir} changed during reset", *bad]
        return "; ".join(bad) or None

    # Under the lock of `grdm-dev db` from the checks through the deletion (PR #42 review r2 R2-02): no upgrade or
    # rollback can start on these directories while they are being deleted, and none is running now.
    with database.lifecycle_lock(ctx) as held:
        if held:
            return report.error(ctx, exit_codes.DB_UPGRADE_FAILED, held)
        problem = refused()
        if problem:
            return report.error(ctx, exit_codes.RESET_FAILED, f"refusing to delete: {problem}")
        # a pending `grdm-dev db` operation may still own helper containers on these directories (ADR-12)
        pending = database.recover_pending(ctx, runner or health.default_runner)
        if pending:
            return report.error(ctx, exit_codes.DB_UPGRADE_FAILED, pending)
        if health.compose_path(ctx).exists():
            rc = run_down(ctx, runner=runner, volumes=True)
            if rc != exit_codes.OK:
                return rc
        removed = False
        if volumes_dir.exists() or volumes_dir.is_symlink():
            problem = refused()
            if problem:
                return report.error(ctx, exit_codes.RESET_FAILED, f"refusing to delete: {problem}")
            owner_init = _owner_init_service(ctx)
            if owner_init.get("image"):
                # rc is not decisive: without the image, nothing was ever written by a container and the host can delete it all.
                (runner or streaming_runner)(wipe_argv(str(owner_init["image"]), volumes_dir, owner_init.get("platform")))
                problem = refused()
                if problem:
                    return report.error(ctx, exit_codes.RESET_FAILED, f"refusing to delete: {problem}")
            try:
                (rmtree or shutil.rmtree)(volumes_dir)
            except OSError as exc:
                return report.error(ctx, exit_codes.RESET_FAILED, f"could not delete {volumes_dir}: {exc}; remove it with `sudo rm -rf {volumes_dir}` / {volumes_dir} を削除できません。`sudo rm -rf {volumes_dir}` で消してください")
            removed = True
    report.emit(ctx, "reset", {"volumes_dir": str(volumes_dir), "removed": removed})
    return exit_codes.OK
