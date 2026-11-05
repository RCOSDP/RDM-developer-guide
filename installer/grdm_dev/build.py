"""grdm-dev build — clone integration repositories and build images with docker buildx (SPEC-02 §3).

For every buildable component of the resolved profile (a component with an `integration_repo`),
the integration repository `RDM-<name>-dev2027` is cloned into runtime/src/<name> with
`git clone --filter=blob:none` (or fetched when already present), checked out at the pinned
commit, and built with `docker buildx build`. The clone URL is composed at run time from the
bare repository name in the manifest (SPEC-01 rule 5: names only in files).

Pinned commit: `Component.build_sha` from grdm_dev.manifest — the component's `integration_sha`
when the weekly integration PR has written one, else the first merged upstream SHA in SPEC-01
rule 3 order (public, then private). Without any SHA the head of `origin/<integration_branch>` is
checked out; the SHA actually checked out is always re-read with `git rev-parse` and recorded in
the build report (`components[]{component,sha12}`), which `compose render` reads as image tags.

Images: local builds use `--load` for the host platform (or --platform) and tag
`grdm-dev/<component>:<sha12>` only. With --push, buildx receives exactly one tag,
`ghcr.io/rcosdp/<component>:<sha12>`: an unqualified tag such as `grdm-dev/<component>` would be
pushed to Docker Hub, outside the private GHCR destination (review PR #21 finding 11). A pushed
multi-arch manifest cannot be `--load`ed, so the local tag is not produced in that mode; `compose
render` keeps reading the sha12 from the build report either way. Exit 30 names the failing component.

Platform per component: `--platform` (comma-separated) wins for every component; otherwise the
component's optional manifest field `build_platform` (e.g. "linux/amd64" for images whose EOL base
has no arm64 wheels — mfr's pandas 0.25.1 on Python 3.5 is the case that made install stop with exit
30 on Apple Silicon); otherwise the host platform. The platform actually used is recorded per
component in the build report, and `compose render` writes the same value as `platform:` so Compose
runs the service under emulation.

Prebuilt fallback (SPEC-01 §3 `prebuilt_image`): a component whose manifest entry carries a registry
image pinned by digest is NOT cloned or built. It is recorded in the build report with status
`prebuilt` and `image` = that reference, and the image is pulled through the runner (`docker pull
--platform <build_platform or host> <reference>`) so that `up` does not pull implicitly; a failed
pull is exit 30 like a failed build. The manifest checker only admits the field with a `note`
(why, and until which milestone); ember-osf-web uses it because its Dockerfile's base image is a
schema-1 manifest that current Docker refuses, until M4 modernizes the Dockerfile.

Runner: `runner(argv) -> (returncode, stdout)`; the default streams the child's output lines to
stderr while collecting them, so a long build stays visible. Tests inject a fake.
"""
from __future__ import annotations

import platform as _platform
import subprocess
import sys
from pathlib import Path

from . import exit_codes, report
from .context import Context

GITHUB_ORG = "RCOSDP"
REGISTRY = "ghcr.io/rcosdp"
LOCAL_IMAGE_PREFIX = "grdm-dev"
PROFILE_RANK = {"minimum": 0, "core": 1, "full": 2}
DEFAULT_PROFILE = "core"


def default_runner(argv: list[str]) -> tuple[int, str]:
    """Run argv, stream every output line to stderr, return (returncode, collected output)."""
    lines: list[str] = []
    try:
        proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except OSError as exc:
        return 127, str(exc)
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stderr.write(line)
        lines.append(line)
    return proc.wait(), "".join(lines)


def host_platform() -> str:
    machine = _platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        return "linux/arm64"
    if machine in ("x86_64", "amd64"):
        return "linux/amd64"
    return f"linux/{machine}"


def clone_url(repo_name: str) -> str:
    """Compose the HTTPS URL from the bare name; the URL is never stored in the manifest or docs."""
    return f"https://github.com/{GITHUB_ORG}/{repo_name}.git"


def load_components(ctx: Context) -> list:
    """Components of the manifest (grdm_dev.manifest dataclasses; dict-compatible)."""
    from . import manifest as _manifest

    return list(_manifest.load(ctx).components)


def resolve_profile(ctx: Context) -> str:
    if ctx.profile:
        return ctx.profile
    from .secrets import env_path, read_env

    return read_env(env_path(ctx)).get("GRDM_PROFILE") or DEFAULT_PROFILE


def buildable_components(components: list[dict], profile: str, only: str | None = None) -> list[dict]:
    rank = PROFILE_RANK.get(profile, PROFILE_RANK[DEFAULT_PROFILE])
    out = []
    for comp in components:
        if not comp.get("integration_repo"):
            continue
        if PROFILE_RANK.get(comp.get("profile", "full"), 2) > rank and only is None:
            continue
        if only is not None and comp.get("id") != only:
            continue
        out.append(comp)
    return out


def image_name(component_id: str) -> str:
    return component_id.lower()


def sync_source(repo: str, dest: Path, ref: str, runner) -> tuple[int, str, str]:
    """Clone or fetch `repo` into dest and check out `ref`. Returns (rc, resolved_sha, log)."""
    log: list[str] = []
    if (dest / ".git").exists():
        rc, out = runner(["git", "-C", str(dest), "fetch", "--filter=blob:none", "origin"])
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        rc, out = runner(["git", "clone", "--filter=blob:none", "--no-checkout", clone_url(repo), str(dest)])
    log.append(out)
    if rc != 0:
        return rc, "", "".join(log)
    rc, out = runner(["git", "-C", str(dest), "checkout", "--detach", "--force", ref])
    log.append(out)
    if rc != 0:
        return rc, "", "".join(log)
    rc, out = runner(["git", "-C", str(dest), "rev-parse", "HEAD"])
    log.append(out)
    return rc, out.strip().splitlines()[-1] if out.strip() else "", "".join(log)


def local_tag(component_id: str, sha12: str) -> str:
    return f"{LOCAL_IMAGE_PREFIX}/{image_name(component_id)}:{sha12}"


def registry_tag(component_id: str, sha12: str) -> str:
    return f"{REGISTRY}/{image_name(component_id)}:{sha12}"


def buildx_argv(component_id: str, context_dir: Path, sha12: str, platforms: list[str], push: bool) -> list[str]:
    """`--push` carries only the fully qualified GHCR tag; `--load` carries only the local tag."""
    argv = ["docker", "buildx", "build", "--platform", ",".join(platforms)]
    if push:
        argv += ["--push", "-t", registry_tag(component_id, sha12)]
    else:
        argv += ["--load", "-t", local_tag(component_id, sha12)]
    argv += ["--label", f"org.gakunin-rdm.component={component_id}", "--label", f"org.gakunin-rdm.sha={sha12}"]
    argv.append(str(context_dir))
    return argv


def component_platforms(comp, override: str | None) -> list[str]:
    """Platforms to build `comp` for: --platform > manifest build_platform > host platform."""
    raw = override or comp.get("build_platform") or host_platform()
    return [s.strip() for s in str(raw).split(",") if s.strip()]


def pull_argv(reference: str, platforms: list[str]) -> list[str]:
    """`docker pull` of a prebuilt reference for exactly one platform (a digest names one manifest)."""
    argv = ["docker", "pull"]
    if platforms:
        argv += ["--platform", platforms[0]]
    argv.append(reference)
    return argv


def pinned_ref(comp) -> str:
    sha = getattr(comp, "build_sha", None) or comp.get("integration_sha")
    if sha:
        return sha
    return f"origin/{comp.get('integration_branch') or 'develop'}"


def register(subparsers) -> None:
    p = subparsers.add_parser("build", help="clone integration repos at the pinned SHA and build images with buildx; exit 30 on failure")
    p.add_argument("--platform", help="comma-separated platforms (default: host platform only)")
    p.add_argument("--push", action="store_true", help=f"push the multi-arch manifest to {REGISTRY}/<component>")
    p.add_argument("--component", help="build only this component id")
    p.set_defaults(_module=sys.modules[__name__])


def run(ctx: Context, args, runner=None) -> int:
    runner = runner or default_runner
    override = getattr(args, "platform", None) or None
    push = bool(getattr(args, "push", False))
    only = getattr(args, "component", None)
    profile = resolve_profile(ctx)
    try:
        components = load_components(ctx)
    except Exception as exc:  # manifest.ManifestError, OSError, ValueError → SPEC-02 exit 20
        detail = "; ".join(getattr(exc, "errors", []) or [str(exc)])
        return report.error(ctx, exit_codes.MANIFEST_INVALID, detail)
    selected = buildable_components(components, profile, only)
    if only is not None and not selected:
        return report.error(ctx, exit_codes.USAGE, f"unknown or non-buildable component: {only}")

    rows: list[dict] = []
    failed: str | None = None
    detail = ""
    for comp in selected:
        cid = comp["id"]
        repo = comp["integration_repo"]
        dest = ctx.runtime / "src" / repo
        platforms = component_platforms(comp, override)
        prebuilt = comp.get("prebuilt_image")
        if prebuilt:
            sys.stderr.write(f"[grdm-dev] build: {cid} uses prebuilt_image {prebuilt} (not built from {repo}; see manifest note)\n")
            rc, _ = runner(pull_argv(str(prebuilt), platforms))
            rows.append({"component": cid, "repo": repo, "sha12": "", "platforms": ",".join(platforms),
                         "status": "prebuilt" if rc == 0 else "pull-failed", "image": str(prebuilt),
                         "note": comp.get("note") or ""})
            if rc != 0:
                failed, detail = cid, f"docker pull of prebuilt_image exited {rc}"
                break
            continue
        rc, sha, log = sync_source(repo, dest, pinned_ref(comp), runner)
        if rc != 0 or not sha:
            rows.append({"component": cid, "repo": repo, "sha12": "", "platforms": ",".join(platforms), "status": "source-failed"})
            failed, detail = cid, f"could not fetch {repo} at {pinned_ref(comp)}"
            break
        sha12 = sha[:12]
        rc, out = runner(buildx_argv(cid, dest, sha12, platforms, push))
        status = "pushed" if (rc == 0 and push) else "built" if rc == 0 else "build-failed"
        rows.append({"component": cid, "repo": repo, "sha12": sha12, "platforms": ",".join(platforms), "status": status,
                     "image": registry_tag(cid, sha12) if push else local_tag(cid, sha12)})
        if rc != 0:
            failed, detail = cid, f"docker buildx build exited {rc}"
            break

    data = {"profile": profile, "platform_override": override or "(per component)", "push": push, "components": rows, "failed": failed}
    report.emit(ctx, "build", data)
    if failed is not None:
        return report.error(ctx, exit_codes.BUILD_FAILED, f"component {failed}: {detail}")
    return exit_codes.OK
