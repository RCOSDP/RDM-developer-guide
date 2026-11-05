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

Overlay (SPEC-01 §3 `overlay_of`, ADR-06): a component whose manifest entry names a base component
(wiki-frontend → osf.io) is not built on its own and has no image. Real install run 4 on Mac Studio
showed why: the wiki-frontend Dockerfile is a derivative of osf.io's and COPYs `./addons/*`,
`./admin/...`, `./website/...` that only the osf.io tree contains, so building it from its own
checkout fails with "not found" on the first such COPY. Instead, after the base checkout is synced,
the overlay checkout is synced too, `runtime/src/_overlay/<overlay id>/` is recreated as a copy of
the base checkout (without `.git`) with the overlay's files copied over it (without `.git`), and
ONE `docker buildx build` runs with that directory as context and `-f <context>/Dockerfile` (the
overlay's Dockerfile, which the copy placed there). The image is the BASE component's image, tagged
with both commits:

    grdm-dev/<base>:<base_sha12>-<overlay_sha12>      (local; `--push`: ghcr.io/rcosdp/<base>:<same>)

The base component is never built a second time without the overlay. The build report row of the
base carries `overlay`, `overlay_repo`, `overlay_sha12` and `image_tag` (the combined tag), which
`compose render` reads as the image tag. `--component <overlay id>` builds its base (with the
overlay) and says so.

Runner: `runner(argv) -> (returncode, stdout)`; the default streams the child's output lines to
stderr while collecting them, so a long build stays visible. Tests inject a fake.
"""
from __future__ import annotations

import platform as _platform
import shutil
import subprocess
import sys
from pathlib import Path

from . import exit_codes, report
from .context import Context
from .manifest import overlay_tag

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
    """Components that get a build step: those with an integration repository in the profile (or the
    one named by `only`). An overlay component is replaced by its base, so the list never contains an
    overlay and never contains the same base twice."""
    rank = PROFILE_RANK.get(profile, PROFILE_RANK[DEFAULT_PROFILE])
    by_id = {c.get("id"): c for c in components}
    out: list[dict] = []
    for comp in components:
        if not comp.get("integration_repo"):
            continue
        if PROFILE_RANK.get(comp.get("profile", "full"), 2) > rank and only is None:
            continue
        if only is not None and comp.get("id") != only:
            continue
        base_id = comp.get("overlay_of")
        if base_id:
            comp = by_id.get(base_id)
            if comp is None:
                continue  # manifest check (MC-14) rejects a dangling overlay_of before build runs
        if not any(c.get("id") == comp.get("id") for c in out):
            out.append(comp)
    return out


def overlays_by_base(components: list[dict]) -> dict[str, dict]:
    """base component id -> the overlay component applied on top of it (SPEC-01 §3 `overlay_of`)."""
    return {c["overlay_of"]: c for c in components if c.get("overlay_of")}


def overlay_context_dir(runtime: Path, overlay_id: str) -> Path:
    return runtime / "src" / "_overlay" / overlay_id


def _ignore_git(_dir: str, names: list[str]) -> set[str]:
    return {n for n in names if n == ".git"}


def assemble_overlay_context(target: Path, base_dir: Path, overlay_dir: Path) -> Path:
    """Recreate `target` as a copy of the base checkout with the overlay checkout copied over it.

    `.git` of either checkout is left out. The directory is removed first so a file deleted from
    the overlay since the last run does not survive; a path the overlay also provides (Dockerfile,
    package.json, webpack configs, addons/wiki/static) is the overlay's version."""
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(base_dir, target, symlinks=True, ignore=_ignore_git)
    shutil.copytree(overlay_dir, target, symlinks=True, ignore=_ignore_git, dirs_exist_ok=True)
    return target


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


def buildx_argv(component_id: str, context_dir: Path, sha12: str, platforms: list[str], push: bool,
                overlay: tuple[str, str] | None = None, dockerfile: Path | None = None) -> list[str]:
    """`--push` carries only the fully qualified GHCR tag; `--load` carries only the local tag.

    `sha12` is the tag (for a base with an overlay: `<base_sha12>-<overlay_sha12>`); `overlay` is
    `(overlay id, overlay sha12)` and adds two labels; `dockerfile` adds `-f` (the overlay's
    Dockerfile inside the assembled context)."""
    argv = ["docker", "buildx", "build", "--platform", ",".join(platforms)]
    if push:
        argv += ["--push", "-t", registry_tag(component_id, sha12)]
    else:
        argv += ["--load", "-t", local_tag(component_id, sha12)]
    argv += ["--label", f"org.gakunin-rdm.component={component_id}", "--label", f"org.gakunin-rdm.sha={sha12}"]
    if overlay:
        argv += ["--label", f"org.gakunin-rdm.overlay={overlay[0]}", "--label", f"org.gakunin-rdm.overlay-sha={overlay[1]}"]
    if dockerfile is not None:
        argv += ["-f", str(dockerfile)]
    argv.append(str(context_dir))
    return argv


def component_platforms(comp, override: str | None) -> list[str]:
    """Platforms to build `comp` for: --platform > manifest build_platform > host platform."""
    raw = override or comp.get("build_platform") or host_platform()
    return [s.strip() for s in str(raw).split(",") if s.strip()]


def pull_argv(reference: str, platform: str | None) -> list[str]:
    """`docker pull` of a prebuilt reference for one platform (a digest names one manifest, so the
    caller pulls once per requested platform and records each result)."""
    argv = ["docker", "pull"]
    if platform:
        argv += ["--platform", platform]
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
    overlays = overlays_by_base(components)
    if only is not None and selected and selected[0]["id"] != only:
        sys.stderr.write(f"[grdm-dev] build: {only} is an overlay of {selected[0]['id']}; building {selected[0]['id']} with the overlay applied\n")

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
            if push:
                # A prebuilt image is someone else's artefact: it is never re-published under
                # ghcr.io/rcosdp. It is still pulled for local use and reported as not pushed (review r4).
                sys.stderr.write(f"[grdm-dev] build: {cid} is prebuilt; --push does not re-publish third-party images\n")
            # One pull per requested platform: a digest names a single manifest, so a platform the
            # image does not provide must fail visibly instead of being reported as pulled (review r3).
            results = []
            for plat in (platforms or [None]):
                rc, _ = runner(pull_argv(str(prebuilt), plat))
                results.append((plat or "host", rc))
            bad = [f"{plat}: exit {rc}" for plat, rc in results if rc != 0]
            rows.append({"component": cid, "repo": repo, "sha12": "", "platforms": ",".join(platforms),
                         "status": ("pull-failed" if bad else ("prebuilt-not-pushed" if push else "prebuilt")),
                         "image": str(prebuilt), "pushed": False,
                         "pulled": ",".join(plat for plat, rc in results if rc == 0),
                         "note": comp.get("note") or ""})
            if bad:
                failed, detail = cid, "docker pull of prebuilt_image failed for " + "; ".join(bad)
                break
            continue
        rc, sha, log = sync_source(repo, dest, pinned_ref(comp), runner)
        if rc != 0 or not sha:
            rows.append({"component": cid, "repo": repo, "sha12": "", "platforms": ",".join(platforms), "status": "source-failed"})
            failed, detail = cid, f"could not fetch {repo} at {pinned_ref(comp)}"
            break
        sha12 = sha[:12]
        tag = sha12
        context_dir = dest
        dockerfile = None
        overlay = overlays.get(cid)
        overlay_row: dict = {}
        if overlay:
            oid, orepo = overlay["id"], overlay["integration_repo"]
            odest = ctx.runtime / "src" / orepo
            sys.stderr.write(f"[grdm-dev] build: {oid} is an overlay of {cid}: one image from {repo} + {orepo} (SPEC-01 overlay_of)\n")
            orc, osha, olog = sync_source(orepo, odest, pinned_ref(overlay), runner)
            if orc != 0 or not osha:
                rows.append({"component": cid, "repo": repo, "sha12": sha12, "platforms": ",".join(platforms), "status": "source-failed",
                             "overlay": oid, "overlay_repo": orepo, "overlay_sha12": ""})
                failed, detail = oid, f"could not fetch {orepo} at {pinned_ref(overlay)} (overlay of {cid})"
                break
            osha12 = osha[:12]
            tag = overlay_tag(sha12, osha12)
            try:
                context_dir = assemble_overlay_context(overlay_context_dir(ctx.runtime, oid), dest, odest)
            except OSError as exc:
                rows.append({"component": cid, "repo": repo, "sha12": sha12, "platforms": ",".join(platforms), "status": "source-failed",
                             "overlay": oid, "overlay_repo": orepo, "overlay_sha12": osha12})
                failed, detail = oid, f"could not assemble the overlay context for {cid}: {exc}"
                break
            dockerfile = context_dir / "Dockerfile"
            overlay_row = {"overlay": oid, "overlay_repo": orepo, "overlay_sha12": osha12, "context": str(context_dir)}
            overlay_arg = (oid, osha12)
        else:
            overlay_arg = None
        rc, out = runner(buildx_argv(cid, context_dir, tag, platforms, push, overlay=overlay_arg, dockerfile=dockerfile))
        status = "pushed" if (rc == 0 and push) else "built" if rc == 0 else "build-failed"
        rows.append({"component": cid, "repo": repo, "sha12": sha12, "image_tag": tag, "platforms": ",".join(platforms), "status": status,
                     "image": registry_tag(cid, tag) if push else local_tag(cid, tag), **overlay_row})
        if rc != 0:
            failed, detail = cid, f"docker buildx build exited {rc}" + (f" (with overlay {overlay['id']})" if overlay else "")
            break

    data = {"profile": profile, "platform_override": override or "(per component)", "push": push, "components": rows, "failed": failed}
    report.emit(ctx, "build", data)
    if failed is not None:
        return report.error(ctx, exit_codes.BUILD_FAILED, f"component {failed}: {detail}")
    return exit_codes.OK
