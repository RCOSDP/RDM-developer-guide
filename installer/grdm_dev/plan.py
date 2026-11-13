"""grdm-dev plan — what would be built and started for a profile, with published ports (SPEC-02 §3, §4).

Touches no Docker. Resolves the profile (flag > runtime/.env GRDM_PROFILE > core), validates the
manifest (exit 20 on any SPEC-01 finding), and prints a TOON report: profile, platform, services
with image and build origin (integration repository name + sha12; `prebuilt <reference>` for a
component whose manifest `prebuilt_image` bypasses the build, SPEC-01 §3; `<overlay repo>@<sha12> over
<base repo>@<sha12> (overlay of <base>)` with origin `overlay` for the one-shot service of an
`overlay_of` component, ADR-06), published ports (SPEC-02 §4
table, honoring GRDM_PORT_<SERVICE> overrides in runtime/.env), and named volumes.

The helpers here (`read_dotenv`, `resolve_profile`, `published_ports`, `detect_platform`) are
shared with compose.py.
"""
from __future__ import annotations

import platform as _platform
import sys
from pathlib import Path
from typing import Any

from . import exit_codes, manifest as _manifest, report
from .context import Context

# SPEC-02 §4 ports table: the only place default host ports are defined. Container ports equal the
# default host ports (SPEC-03 §4.3).
DEFAULT_PORTS: dict[str, int] = {
    "web": 5000,
    "api": 8000,
    "admin": 8001,
    "wb": 7777,
    "mfr": 7778,
    "fakecas": 8080,
    "ember_osf_web": 4200,
}
PORT_ENV_PREFIX = "GRDM_PORT_"
PROFILE_ENV_KEY = "GRDM_PROFILE"
LOOPBACK = "127.0.0.1"


def register(subparsers) -> None:
    p = subparsers.add_parser("plan", help="show images to build and services to start with their ports; exit 20 if the manifest is invalid")
    p.add_argument("--auth", choices=[_manifest.AUTH_FAKECAS, _manifest.AUTH_SHIBBOLETH], default=_manifest.AUTH_FAKECAS,
                   help="auth provider for the full profile (shibboleth replaces fakecas with shibboleth_sp + test_idp)")
    p.set_defaults(_module=sys.modules[__name__])


# --------------------------------------------------------------------------- shared helpers


def env_path(ctx: Context) -> Path:
    return ctx.runtime / ".env"


def read_dotenv(path: Path) -> dict[str, str]:
    """Parse KEY=value lines; comments and blanks ignored, surrounding quotes stripped. Missing file -> {}."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def port_key(service: str) -> str:
    return PORT_ENV_PREFIX + service.upper()


def resolve_profile(ctx: Context, env: dict[str, str] | None = None) -> str:
    """Flag > runtime/.env GRDM_PROFILE > core. An unknown saved value falls back to core."""
    if ctx.profile:
        return ctx.profile
    env = env if env is not None else read_dotenv(env_path(ctx))
    saved = env.get(PROFILE_ENV_KEY, "")
    return saved if saved in _manifest.PROFILE_RANK else _manifest.DEFAULT_PROFILE


def published_ports(services: list[_manifest.Service], env: dict[str, str]) -> list[dict[str, Any]]:
    """Rows {service, host_port, container_port, url, source} for services with a host port.

    The default is the template's host_port (SPEC-02 §4 table); a valid GRDM_PORT_<SERVICE> in
    runtime/.env overrides it (source = env). Services without a host_port are internal only.
    """
    rows: list[dict[str, Any]] = []
    for svc in services:
        tpl = svc.template
        default = tpl.get("host_port", DEFAULT_PORTS.get(svc.name))
        if default is None:
            continue
        container = int(tpl.get("container_port", default))
        host, source = int(default), "default"
        raw = env.get(port_key(svc.name))
        if raw and raw.isdigit() and 0 < int(raw) < 65536:
            host, source = int(raw), "env"
        rows.append({
            "service": svc.name,
            "host_port": host,
            "container_port": container,
            "url": f"http://{LOOPBACK}:{host}",
            "source": source,
        })
    return rows


def detect_platform(host_info: Any = None) -> str:
    """linux/arm64 or linux/amd64. Uses a HostInfo when given, else host.classify_arch (pure) when
    importable, else platform.machine(). Never probes Docker (plan touches no Docker)."""
    if host_info is not None:
        plat = getattr(host_info, "platform_string", "") or ""
        if plat:
            return plat
        arch = getattr(host_info, "arch", "")
        return f"linux/{arch}" if arch in ("arm64", "amd64") else "unknown"
    machine = _platform.machine()
    try:
        from . import host  # other owner; optional

        arch = host.classify_arch(machine)
        if arch in ("arm64", "amd64"):
            return f"linux/{arch}"
    except Exception:
        pass
    m = machine.lower()
    if m in ("arm64", "aarch64"):
        return "linux/arm64"
    if m in ("x86_64", "amd64"):
        return "linux/amd64"
    return "unknown"


def volumes_of(services: list[_manifest.Service]) -> list[str]:
    names: list[str] = []
    for svc in services:
        for vol in svc.template.get("volumes", []):
            name = vol.get("volume")
            if name and name not in names:
                names.append(name)
    return names


# --------------------------------------------------------------------------- report


def _build_from(svc: _manifest.Service) -> str:
    if svc.is_prebuilt:
        return f"prebuilt {svc.prebuilt_image}"
    if svc.build and svc.build.overlay_of:
        own_sha12 = (svc.build.sha or "")[:12] or "develop"
        return (f"{svc.build.repo}@{own_sha12} over {svc.build.base_repo}@{svc.build.base_sha12 or 'develop'}"
                f" (overlay of {svc.build.overlay_of})")
    if svc.build and svc.build.sha12:
        return f"{svc.build.repo}@{svc.build.sha12}"
    return svc.build.repo if svc.build else "pinned image"


def build_report(ctx: Context, profile: str, auth: str, services: list[_manifest.Service], env: dict[str, str], platform_string: str) -> dict[str, Any]:
    rows = []
    for svc in services:
        rows.append({
            "service": svc.name,
            "component": svc.component,
            "role": svc.role,
            "image": svc.image,
            "build_from": _build_from(svc),
            "origin": svc.origin,
            "profile": svc.profile,
        })
    ports = published_ports(services, env)
    return {
        "profile": profile,
        "auth": auth,
        "platform": platform_string,
        "manifest": str(ctx.manifest_path.relative_to(ctx.root)) if ctx.manifest_path.is_relative_to(ctx.root) else str(ctx.manifest_path),
        "services": rows,
        "images_to_build": sorted({svc.image for svc in services if svc.is_built}),
        "prebuilt_images": sorted({svc.image for svc in services if svc.is_prebuilt}),
        "ports": ports,
        "volumes": volumes_of(services),
        "network": "grdm",
    }


def run(ctx: Context, args, platform_string: str | None = None) -> int:
    errors = _manifest.validate(ctx)
    if errors:
        for line in errors:
            sys.stderr.write(f"  - {line}\n")
        return report.error(ctx, exit_codes.MANIFEST_INVALID, f"{len(errors)} finding(s); run `grdm-dev manifest check`")
    try:
        man = _manifest.load(ctx)
        env = read_dotenv(env_path(ctx))
        profile = resolve_profile(ctx, env)
        auth = getattr(args, "auth", None) or _manifest.AUTH_FAKECAS
        services = _manifest.services_for_profile(man, profile, auth)
    except (_manifest.ManifestError, ValueError, OSError) as exc:
        return report.error(ctx, exit_codes.MANIFEST_INVALID, str(exc))
    data = build_report(ctx, profile, auth, services, env, platform_string or detect_platform())
    report.emit(ctx, "plan", data)
    return exit_codes.OK
