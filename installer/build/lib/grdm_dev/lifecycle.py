"""grdm-dev up / down / reset — container lifecycle for the rendered profile (SPEC-02 §3, §7).

up     `docker compose up -d`, then wait for health (exit 40 on timeout), then open the browser at
       http://127.0.0.1:<GRDM_PORT_WEB> unless --no-open; the browser is only opened when stdin is a
       terminal. Idempotent: healthy services are left alone by Compose.
down   `docker compose down` — containers stop, volumes stay.
reset  down, then delete runtime/volumes/ after ctx.confirm(). Non-interactive without --yes → exit 2.

Helpers for other modules: running_services(ctx) and restart(ctx, services) (used by secrets rotate).
Runner: `runner(argv) -> (rc, stdout)`; tests inject a fake and never need Docker.
"""
from __future__ import annotations

import shutil
import sys
import webbrowser

from . import exit_codes, health, report
from .context import Context

DEFAULT_TIMEOUT = 300.0


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


def restart(ctx: Context, services: list[str] | None = None, runner=None) -> int:
    runner = runner or default_runner
    rc, _ = runner(health.compose_base(ctx) + ["restart", *(services or [])])
    return rc


def register(subparsers) -> None:
    up = subparsers.add_parser("up", help="start the profile and wait for health; exit 40 on failure")
    up.add_argument("--no-open", dest="no_open", action="store_true", help="do not open the browser")
    up.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help=f"seconds to wait for health (default {int(DEFAULT_TIMEOUT)})")
    up.set_defaults(_module=sys.modules[__name__], lifecycle_action="up")
    down = subparsers.add_parser("down", help="stop containers, keep volumes")
    down.set_defaults(_module=sys.modules[__name__], lifecycle_action="down")
    reset = subparsers.add_parser("reset", help="stop containers and delete runtime/volumes/ (asks first; --yes skips)")
    reset.set_defaults(_module=sys.modules[__name__], lifecycle_action="reset")


def run(ctx: Context, args, runner=None, prober=None, opener=None, sleep=None, rmtree=None) -> int:
    action = getattr(args, "lifecycle_action", None)
    if action == "up":
        return run_up(ctx, no_open=bool(getattr(args, "no_open", False)), timeout=float(getattr(args, "timeout", DEFAULT_TIMEOUT)),
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


def run_reset(ctx: Context, runner=None, rmtree=None) -> int:
    volumes_dir = ctx.runtime / "volumes"
    if not ctx.confirm(f"Stop all services and delete {volumes_dir} (all data)?", default=False):
        if not ctx.yes and not ctx.stdin_is_tty:
            return report.error(ctx, exit_codes.USAGE, "reset needs a confirmation; add --yes when no terminal is attached")
        sys.stderr.write("[grdm-dev] reset cancelled\n")
        return exit_codes.OK
    if health.compose_path(ctx).exists():
        rc = run_down(ctx, runner=runner, volumes=True)
        if rc != exit_codes.OK:
            return rc
    removed = False
    if volumes_dir.exists():
        (rmtree or shutil.rmtree)(volumes_dir)
        removed = True
    report.emit(ctx, "reset", {"volumes_dir": str(volumes_dir), "removed": removed})
    return exit_codes.OK
