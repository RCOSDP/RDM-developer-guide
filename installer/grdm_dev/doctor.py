"""grdm-dev doctor — host detection and install preflight (SPEC-02 §3). Reference implementation of the module contract.

Contract for every subcommand module:
  register(subparsers): add the sub-parser and call set_defaults(_module=sys.modules[__name__])
  run(ctx, args) -> int: return an exit code from grdm_dev.exit_codes
Tests inject a fake `runner` (callable taking argv list, returning (returncode, stdout)) so Docker
is never required by unit tests (SPEC-02 §10).

Exit codes: 10 when the host itself is unsupported (OS, CPU, memory, Python), 11 when Docker is
missing, not running, or lacks the Compose / buildx plugin, 13 when a prerequisite of the build is
missing (git, read access to the private integration repositories, amd64 emulation on Linux arm64,
a checkout the Docker engine cannot see, or one that cannot keep 0600), 51 when a scanner is missing. Warnings (best-effort host, low
memory, little disk) do not change the exit code unless `--strict` is given, which turns them
into exit 10 so CI can insist on an official host.

The preflight exists so a problem appears here and not after the long build: the profile's memory
floors (the same arithmetic `compose render` refuses on) and the integration repositories of the
profile are checked with the manifest. A manifest that cannot be read is `plan`'s exit 20, so it
only skips these checks here, with a warning.

A token is never handled here. `git ls-remote` uses whatever credential helper the developer set
up, cannot prompt, and its output is classified but never printed: a remote URL can contain a token.
"""
from __future__ import annotations

import sys

from . import build, compose, exit_codes, host, manifest as _manifest, plan, report
from .context import Context

REPO_ACCESS_HINT = (
    "give Git read access with `gh auth login` then `gh auth setup-git`, or a credential helper holding a personal "
    "access token with read access to the RCOSDP repositories; never put a token in a URL or in runtime/.env / "
    "`gh auth login` に続けて `gh auth setup-git` を実行するか、RCOSDP のリポジトリを読める個人アクセストークンを資格情報ヘルパーに"
    "登録して、Git に読み取り権限を与えてください。トークンを URL や runtime/.env に書かないでください"
)
_NETWORK_ERRORS = ("could not resolve host", "failed to connect", "network is unreachable", "timed out", "operation timed out")


DOCKER_SHARED_ENV = "GRDM_DOCKER_SHARED"  # macOS: "1" skips the engine check when it cannot be run
_MOUNT_REJECTED = ("mounts denied", "not shared from the host", "not known to docker", "invalid mount", "bind source path does not exist")


def register(subparsers) -> None:
    p = subparsers.add_parser("doctor", help="detect OS, CPU, memory, disk, Docker and install prerequisites; exit 10/11/13/51 if unmet")
    p.add_argument("--strict", action="store_true", help="treat warnings (best-effort host, low memory) as exit 10")
    p.add_argument("--memory-gib", type=float, help="the value you will give `compose render --memory-gib`: a knowing overcommit, reported as a warning")
    p.set_defaults(_module=sys.modules[__name__])


def ls_remote_argv(repo: str) -> list[str]:
    """`git ls-remote` that can never wait for a terminal or a credential dialog."""
    return ["env", "GIT_TERMINAL_PROMPT=0", "GCM_INTERACTIVE=never", "LC_ALL=C", "git", "ls-remote", "--exit-code", build.clone_url(repo), "HEAD"]


def repos_to_clone(man: _manifest.Manifest, profile: str) -> list[str]:
    """Integration repositories `build` will clone for this profile: not a prebuilt or in-repo image; an overlay's base is included."""
    components = list(man.components)
    by_id = {c["id"]: c for c in components}
    repos: list[str] = []
    for comp in build.buildable_components(components, profile):
        if comp.get("prebuilt_image") or not comp.get("integration_repo"):
            continue
        names = [comp["integration_repo"]]
        if comp.get("overlay_of"):
            names.append(by_id[comp["overlay_of"]]["integration_repo"])
        repos += [r for r in names if r not in repos]
    return repos


def check_repo_access(repos: list[str], runner, info: host.HostInfo) -> None:
    """Fill prerequisite_problems for repositories Git cannot read; an unreachable network is only a warning."""
    denied: list[str] = []
    unverified: list[str] = []
    for repo in repos:
        rc, out = runner(ls_remote_argv(repo))
        if rc == 0:
            continue
        text = (out or "").lower()
        if rc == 124 or any(marker in text for marker in _NETWORK_ERRORS):
            unverified.append(repo)
        else:
            denied.append(repo)
    if denied:
        names = ", ".join(denied)
        info.prerequisite_problems.append(f"Git cannot read these private repositories: {names}; {REPO_ACCESS_HINT} / 次の非公開リポジトリを Git で読めません: {names}")
    if unverified:
        names = ", ".join(unverified)
        info.warnings.append(f"could not reach GitHub to check {names}; `build` needs the network / {names} の確認のため GitHub に届きませんでした。`build` にはネットワークが要ります")


def check_memory_floors(services: list, info: host.HostInfo, vm_gib: float | None, memory_gib: float | None, profile: str) -> None:
    """The arithmetic `compose render` refuses on, moved up front: exit 10 here, or a warning with --memory-gib."""
    need_gib = compose.memory_floor_need_gib(services)
    if memory_gib:
        if need_gib > memory_gib:
            info.warnings.append(f"--memory-gib {memory_gib:g} is below the {need_gib:.1f} GiB that profile {profile} needs: a knowing overcommit / --memory-gib {memory_gib:g} はプロファイル {profile} に必要な {need_gib:.1f} GiB 未満です（承知の上の過剰割当）")
        return
    known = [g for g in (None if info.memory_bytes is None else info.memory_bytes / host.GIB, vm_gib) if g]
    if not known or need_gib <= min(known):
        return
    info.problems.append(
        f"profile {profile} needs {need_gib:.1f} GiB but this Docker engine has {min(known):.1f} GiB; use --profile minimum, or --memory-gib to overcommit knowingly, or: {host.memory_hint(info.os_name, need_gib)} / "
        f"プロファイル {profile} には {need_gib:.1f} GiB 必要ですが Docker エンジンは {min(known):.1f} GiB です。--profile minimum にするか、--memory-gib で承知の上で過剰割当にするか、次の対処をしてください"
    )
    info.supported = False


def visibility_argv(image: str, repo_root: str) -> list[str]:
    """List a known file through a read-only bind mount of this checkout: what the engine sees, as `up` will mount it."""
    return ["docker", "run", "--rm", "--pull", "missing", "--network", "none", "--read-only", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges:true", "--entrypoint", "ls", "-v", f"{repo_root}/manifest:/probe:ro", image, "/probe/upstreams.json"]


def check_engine_visibility(probe: host.Probe, info: host.HostInfo, runner, image: str) -> None:
    """macOS: can the Docker VM see this checkout? Asked of the engine, because sharing differs between Docker
    Desktop and Colima and a bind mount from an unshared path is silently empty. Uses the postgres image `up` needs.
    The engine refusing the mount, or the mount coming up empty, is exit 13; a probe that could not run (no image,
    no network) has established nothing and says so as a warning."""
    if info.os_name != "macos" or not probe.repo_root or not info.docker_running:
        return
    if probe.env.get(DOCKER_SHARED_ENV) == "1":
        info.warnings.append(f"{DOCKER_SHARED_ENV}=1: not checking that the Docker VM can see {probe.repo_root} / {DOCKER_SHARED_ENV}=1 のため Docker VM から {probe.repo_root} が見えるか確かめていません")
        return
    rc, out = runner(visibility_argv(image, probe.repo_root))
    if rc == 0:
        return
    text = (out or "").lower()
    if any(marker in text for marker in _MOUNT_REJECTED) or (rc != 125 and "no such file" in text):
        info.prerequisite_problems.append(
            f"the Docker engine cannot see {probe.repo_root}, so bind mounts would be silently empty; share that path with the Docker VM or clone the repository under a shared one / "
            f"Docker エンジンから {probe.repo_root} が見えないため bind mount が黙って空になります。そのパスを Docker VM と共有するか、共有された場所へ clone してください"
        )
    else:
        info.warnings.append(
            f"could not ask the Docker engine whether it sees {probe.repo_root}; if services start empty, share that path (set {DOCKER_SHARED_ENV}=1 to skip this check) / "
            f"Docker エンジンに {probe.repo_root} が見えるか確かめられませんでした。サービスの中身が空なら、そのパスを共有してください（{DOCKER_SHARED_ENV}=1 でこの確認を省けます）"
        )


def preflight(ctx: Context, runner, long_runner, probe: host.Probe, info: host.HostInfo, memory_gib: float | None) -> None:
    if not ctx.manifest_path.exists():
        return  # not a checkout of this repository (`doctor --root` elsewhere): only the host checks apply
    try:
        man = _manifest.load(ctx)
        profile = plan.resolve_profile(ctx)
        services = _manifest.services_for_profile(man, profile)
    except (_manifest.ManifestError, ValueError, OSError) as exc:
        info.warnings.append(f"manifest unreadable, so the memory and repository checks were skipped ({exc}) / manifest を読めないためメモリとリポジトリの確認を省きました")
        return
    if info.docker_running:
        check_memory_floors(services, info, compose.detect_docker_memory_gib(runner), memory_gib, profile)
        postgres = next((s.image for s in services if s.name == "postgres"), None)
        if postgres:
            check_engine_visibility(probe, info, long_runner, postgres)
    amd64 = [s.name for s in services if "amd64" in str(man.component(s.component).get("build_platform") or "")]
    host.check_amd64_emulation(probe, info, amd64)
    if probe.tools is not None and probe.tools.get("git"):
        check_repo_access(repos_to_clone(man, profile), runner, info)


def run(ctx: Context, args, runner=None, probe=None) -> int:
    long_runner = runner or build.default_runner  # no 15 s limit: the visibility check may pull its image
    runner = runner or host.default_runner
    probe = probe or host.Probe.from_system(root=ctx.root, runner=runner)
    info = host.detect(runner=runner, probe=probe, root=ctx.root)
    preflight(ctx, runner, long_runner, probe, info, getattr(args, "memory_gib", None))
    data = host.as_report(info)
    data["strict"] = bool(getattr(args, "strict", False))
    report.emit(ctx, "doctor", data)
    if not info.supported:
        return report.error(ctx, exit_codes.HOST_UNSUPPORTED, "; ".join(info.problems))
    if not info.docker_ok:
        return report.error(ctx, exit_codes.DOCKER_MISSING, "; ".join(info.problems))
    if info.prerequisite_problems:
        return report.error(ctx, exit_codes.PREFLIGHT_FAILED, "; ".join(info.prerequisite_problems))
    if info.scanner_problems:
        return report.error(ctx, exit_codes.SCANNER_UNAVAILABLE, "; ".join(info.scanner_problems))
    if data["strict"] and info.warnings:
        return report.error(ctx, exit_codes.HOST_UNSUPPORTED, "--strict: " + "; ".join(info.warnings))
    return exit_codes.OK
