"""grdm-dev compose render — write runtime/docker-compose.yml from templates + manifest (SPEC-02 §3, ADR-02).

Output is JSON (Compose accepts JSON because JSON is YAML). Rules applied to every service:

* two networks (SPEC-03 §3.2, ADR-02 §3.1):
  - `grdm` is `internal: true` and carries every service-to-service call; services address each
    other by Compose service name. An internal network has no route to the host's interfaces, the
    LAN or the Internet, so a compromised container cannot call home from it.
  - `grdm-edge` is a plain bridge attached only to the services that publish a port on 127.0.0.1
    (web, api, admin, wb, mfr, ember_osf_web, fakecas): Docker cannot publish a port from an
    internal network, and the browser must reach exactly those services. Nothing else joins it.
  Egress is therefore NOT available on `grdm`. A service that must reach the Internet (for example
  an external storage provider while developing an add-on in waterbutler, or a package index at
  run time) has no route unless it is attached to `grdm-edge` explicitly with
  `compose render --egress <service>[,<service>...]`. The choice is recorded in runtime/.env as
  `GRDM_EGRESS_SERVICES` (so `scan --baseline` and the install report can show it), is kept on
  later renders, and is cleared with `--egress none`. Publishing services are on `grdm-edge`
  anyway, so they always have egress; the flag matters for the others.
* ports only as `127.0.0.1:<host>:<container>`; host ports from the SPEC-02 §4 table, overridden by
  `GRDM_PORT_<SERVICE>` in runtime/.env. Before choosing, the bindings of the project's own running
  containers are read (`docker compose ps --format json`) and kept: a port that our own service
  already publishes is not a collision (review PR #21 finding 10). Only a port held by another
  process moves to the next free one (exit 12 when none is free within +100); every decision is
  logged in the report (`port_decisions`) and every chosen port is written back to runtime/.env;
* `user:` non-root (uid from the template), `read_only: true` with explicit `tmpfs`/volumes,
  `cap_drop: [ALL]`, `security_opt: [no-new-privileges:true]`, `mem_limit`/`cpus`/`pids_limit`
  scaled from the detected memory (argument; default 16 GiB), `platform:` from the argument or
  host detection; per-service exceptions come from manifest/hardening.json (SPEC-03 §3.3);
* `platform:` is the argument or the detected host platform, except for a service whose manifest
  component carries `build_platform` (SPEC-01; e.g. mfr, ember-osf-web, cas-overlay on
  "linux/amd64"): that value is written instead so Compose runs the image built by `grdm-dev build`
  under emulation on an arm64 host;
* `image:` is the manifest-derived reference: `grdm-dev/<component>:<sha12>` for a built component
  (sha12 from the build report when present), `grdm-dev/<overlay>:<base_sha12>-<overlay_sha12>` for
  an overlay component (SPEC-01 §3 `overlay_of`, ADR-06: `wiki_assets` runs the wiki-frontend bundle
  builder once, copies `/code/website/static/public/js/` into the named volume `wiki_static` and
  exits — `restart: "no"`; web/api/admin/worker mount that volume read-only at
  `/code/website/static/public/js/wiki/` and depend on it with `condition:
  service_completed_successfully`; the report row says `origin: overlay`), `base_image[@digest]` for infra, and
  the `prebuilt_image` reference itself for a component that bypasses the build (SPEC-01 §3; e.g.
  ember-osf-web until M4). A prebuilt service gets `platform:` from `build_platform` like any
  other, and the report row says `origin: prebuilt`; `scan` sees it as one more compose image;
* named volumes are local bind volumes under runtime/volumes/<name>;
* secrets never enter generated files: the compose file references `${KEY}` and Compose reads
  runtime/.env (same directory) at `up`; `secrets init` must have run (exit 2 otherwise).

Template schema (templates/<service>.json): service, component, profile?, container_port?,
host_port?, expose?, command?, environment?, env_files?, volumes? ([{volume|config|config_dir,
target, ro?}]), tmpfs?, user?, depends_on? (service names, or {service, condition} for the Compose
long form, e.g. `service_completed_successfully` on a one-shot), restart?, one_shot? (a container
that runs to completion: rendered with `restart: "no"`, and `health` accepts `exited` with code 0),
weight, mem_min_mb, pids_limit, note?. Strings may use
`{{HOST_PORT:<service>}}` / `{{CONTAINER_PORT:<service>}}`. `command` strings are written for the
container shell: every `$` in them is escaped to `$$` on output, so Compose does not interpolate
them; `environment` values are the only place where `${KEY}` means a value from runtime/.env.

Upstream settings are rewritten under runtime/config/ (ADR-02 §3.3): osf/local.py, osf/api_local.py,
osf.env, wb.env, mfr.env, sharejs.env, postgres-init/10-cas.sql, cas/cas.properties. Internal URLs use
service names, browser-facing URLs use http://127.0.0.1:<port>.
"""
from __future__ import annotations

import json
import math
import os
import re
import socket
import sys
from pathlib import Path
from typing import Any, Callable

from . import exit_codes, manifest as _manifest, report
from .context import Context
from .plan import (
    DEFAULT_PORTS,
    LOOPBACK,
    PROFILE_ENV_KEY,
    detect_platform,
    env_path,
    port_key,
    published_ports,
    read_dotenv,
    resolve_profile,
    volumes_of,
)

NETWORK = "grdm"               # internal: true — service-to-service only, no egress
EDGE_NETWORK = "grdm-edge"     # plain bridge — only services that publish a port on 127.0.0.1 (+ --egress)
EGRESS_ENV_KEY = "GRDM_EGRESS_SERVICES"
EGRESS_NONE = "none"
PROJECT_NAME = "grdm-dev"
COMPOSE_FILE = "docker-compose.yml"
CONFIG_DIR = "config"
VOLUMES_DIR = "volumes"
DEFAULT_MEMORY_GIB = 16.0
DEFAULT_CPUS = 4.0
MEMORY_SHARE = 0.70          # fraction of host memory handed out as the sum of mem_limit
CPU_OVERSUBSCRIBE = 2.0      # limits may add up to twice the host CPUs (they are ceilings)
PORT_SEARCH_RANGE = 100
FORBIDDEN_ADDRESS = "192.168.168.167"  # the old loopback alias; must never appear (ADR-02)

# Keys that compose output references; all are written by `grdm-dev secrets init` (secrets.py).
# Every secret that `secrets init` generates must be present before rendering, so the generated
# Compose file never references an unset variable (Compose would warn and substitute "").
# The list is the single source of truth in secrets.py; we copy it to avoid drift (REV r1 of PR #30).
from .secrets import SECRET_KEYS as _SECRET_KEYS  # noqa: E402

REQUIRED_SECRETS: tuple[str, ...] = tuple(_SECRET_KEYS)

PortChecker = Callable[[int], bool]

GENERATED_HEADER = "generated by grdm-dev compose render; do not edit (SPEC-02 §3, ADR-02)"


def register(subparsers) -> None:
    p = subparsers.add_parser("compose", help="render runtime/docker-compose.yml from manifest, profile and templates")
    sub = p.add_subparsers(dest="compose_command", metavar="<action>")
    r = sub.add_parser("render", help="write runtime/docker-compose.yml and runtime/config/*; touches no Docker")
    r.add_argument("--auth", choices=[_manifest.AUTH_FAKECAS, _manifest.AUTH_SHIBBOLETH], default=_manifest.AUTH_FAKECAS,
                   help="auth provider for the full profile (shibboleth replaces fakecas)")
    r.add_argument("--platform", help="Compose platform, e.g. linux/arm64 (default: detected host)")
    r.add_argument("--memory-gib", type=float, help="host memory to scale resource limits from (default: detected, else 16)")
    r.add_argument("--cpus", type=float, help="host CPUs to scale cpu limits from (default: detected, else 4)")
    r.add_argument("--egress", metavar="SERVICES",
                   help=f"comma-separated services to attach to {EDGE_NETWORK} so they can reach the Internet "
                        f"(default: the value of {EGRESS_ENV_KEY} in runtime/.env; `{EGRESS_NONE}` clears it)")
    p.set_defaults(_module=sys.modules[__name__])


# --------------------------------------------------------------------------- hardening


def load_hardening(root: Path) -> dict[str, dict[str, Any]]:
    """manifest/hardening.json exceptions keyed by service. Missing file -> no exceptions."""
    path = root / "manifest" / "hardening.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict[str, Any]] = {}
    for entry in data.get("exceptions", []):
        if not entry.get("reason") or not entry.get("review"):
            raise ValueError(f"hardening.json: exception for {entry.get('service')!r} needs reason and review")
        out[entry["service"]] = entry
    return out


# --------------------------------------------------------------------------- ports


def default_port_checker(port: int) -> bool:
    """True when 127.0.0.1:<port> can be bound right now."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((LOOPBACK, port))
            return True
        except OSError:
            return False


def current_bindings(ctx: Context, runner) -> dict[str, int]:
    """Host ports the project's own running containers publish right now: {service: host_port}.

    Read from `docker compose ps --format json` (Publishers[].PublishedPort). {} when the compose
    file does not exist yet, Docker is unavailable, or the output is unreadable: nothing is then
    treated as owned and the free-port check alone decides.
    """
    from . import health  # lazy: health is a sibling command module

    if not health.compose_path(ctx).exists():
        return {}
    try:
        rc, out = runner(health.compose_base(ctx) + ["ps", "--format", "json"])
    except Exception:  # noqa: BLE001 - a broken docker must not stop rendering
        return {}
    if rc != 0:
        return {}
    owned: dict[str, int] = {}
    for service, info in health.parse_ps(out).items():
        for pub in info.get("Publishers") or []:
            try:
                port = int(pub.get("PublishedPort") or 0)
            except (TypeError, ValueError):
                continue
            if port > 0 and service not in owned:
                owned[service] = port
    return owned


def assign_ports(
    rows: list[dict[str, Any]], checker: PortChecker, owned: dict[str, int] | None = None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Keep ports our own running containers hold; move only ports held by other processes.

    Returns (rows, decisions, unresolved). A decision row is {service, wanted, chosen, reason}
    with reason `kept-own-binding` (our running container already publishes it), `free`,
    or `remapped-foreign-listener` (another process holds the wanted port).
    """
    owned = owned or {}
    taken: set[int] = set()
    decisions: list[dict[str, Any]] = []
    unresolved: list[str] = []
    out: list[dict[str, Any]] = []
    for row in rows:
        wanted = int(row["host_port"])
        own = owned.get(row["service"])
        chosen = None
        reason = "free"
        if own and own not in taken:
            # Our own container publishes `own`; the port is busy because of us, not a foreign process.
            chosen, reason = own, "kept-own-binding"
        else:
            for cand in range(wanted, wanted + PORT_SEARCH_RANGE + 1):
                if cand in taken or cand > 65535:
                    continue
                if checker(cand):
                    chosen = cand
                    break
            if chosen is not None and chosen != wanted:
                reason = "remapped-foreign-listener"
        if chosen is None:
            unresolved.append(row["service"])
            out.append(row)
            continue
        taken.add(chosen)
        new = dict(row)
        new["host_port"] = chosen
        new["url"] = f"http://{LOOPBACK}:{chosen}"
        if reason == "kept-own-binding":
            new["source"] = "running"
        elif reason == "remapped-foreign-listener":
            new["source"] = "remapped"
        decisions.append({"service": row["service"], "wanted": wanted, "chosen": chosen, "reason": reason})
        out.append(new)
    return out, decisions, unresolved


def parse_egress(raw: str | None, services: list[str]) -> list[str]:
    """Normalize a comma-separated --egress / GRDM_EGRESS_SERVICES value against the profile's services.

    Unknown names raise ValueError (exit 2 upstream); `none`/empty clears the list.
    """
    if not raw or raw.strip().lower() == EGRESS_NONE:
        return []
    names: list[str] = []
    for part in raw.split(","):
        name = part.strip()
        if not name or name in names:
            continue
        if name not in services:
            raise ValueError(f"--egress: {name!r} is not a service of this profile (choose from {', '.join(services)})")
        names.append(name)
    return names


def host_port_map(env: dict[str, str], rows: list[dict[str, Any]]) -> dict[str, int]:
    """Host port per service: assigned rows first, then .env overrides, then the SPEC-02 §4 defaults.

    Services outside the profile still get a port so generated settings (e.g. WATERBUTLER_URL) are complete.
    """
    ports = dict(DEFAULT_PORTS)
    for name in DEFAULT_PORTS:
        raw = env.get(port_key(name))
        if raw and raw.isdigit():
            ports[name] = int(raw)
    for row in rows:
        ports[row["service"]] = int(row["host_port"])
    return ports


_PLACEHOLDER = re.compile(r"\{\{(HOST_PORT|CONTAINER_PORT):([A-Za-z0-9_]+)\}\}|\{\{(AUTH_URL|SERVICE_IMAGE)\}\}")


def auth_url(auth: str, host_ports: dict[str, int]) -> str:
    """Where a browser starts a login: fakecas's published port, or web's own /login when Shibboleth
    replaces fakecas (osf.io's login route then redirects to the SP). Used by `{{AUTH_URL}}`
    (ember-osf-web's CAS_URL), so no template carries the fakecas port when fakecas is absent."""
    from . import manifest as _manifest

    if auth == _manifest.AUTH_SHIBBOLETH:
        return f"http://{LOOPBACK}:{host_ports['web']}"
    return f"http://{LOOPBACK}:{host_ports['fakecas']}"


def substitute(value: Any, host_ports: dict[str, int], container_ports: dict[str, int], extras: dict[str, str] | None = None) -> Any:
    """Resolve `{{HOST_PORT:svc}}`, `{{CONTAINER_PORT:svc}}`, `{{AUTH_URL}}` and `{{SERVICE_IMAGE}}` (the
    service's own image reference, so a container can fingerprint what it was built from; from `extras`)."""
    extras = extras or {}
    if isinstance(value, str):
        def repl(m: re.Match) -> str:
            if m.group(3):
                if m.group(3) not in extras:
                    raise ValueError(f"template placeholder {m.group(0)} is not available here")
                return extras[m.group(3)]
            table = host_ports if m.group(1) == "HOST_PORT" else container_ports
            if m.group(2) not in table:
                raise ValueError(f"template placeholder {m.group(0)} has no known port")
            return str(table[m.group(2)])
        return _PLACEHOLDER.sub(repl, value)
    if isinstance(value, list):
        return [substitute(v, host_ports, container_ports, extras) for v in value]
    if isinstance(value, dict):
        return {k: substitute(v, host_ports, container_ports, extras) for k, v in value.items()}
    return value


# --------------------------------------------------------------------------- resources


class MemoryBudgetError(ValueError):
    """The memory floors of the profile do not fit the budget (exit 10, host unsupported)."""


def scale_resources(services: list[_manifest.Service], memory_gib: float, cpus: float, allow_overcommit: bool = False) -> dict[str, dict[str, Any]]:
    budget_mb = memory_gib * 1024 * MEMORY_SHARE
    total_weight = sum(float(s.template.get("weight", 1)) for s in services) or 1.0
    # Memory in two passes so the floors (`mem_min_mb`) do not push the total past the budget: a
    # service whose weighted share is below its floor gets the floor; the budget that remains is
    # then shared by weight among the others. Only when the floors alone exceed the budget does the
    # total exceed it (real install run 10: ember needs 8 GiB under emulation on a 47 GiB Docker VM).
    floors = {s.name: int(s.template.get("mem_min_mb", 128)) for s in services}
    weights = {s.name: float(s.template.get("weight", 1)) for s in services}
    if sum(floors.values()) > budget_mb and not allow_overcommit:
        need_gib = sum(floors.values()) / 1024 / MEMORY_SHARE
        raise MemoryBudgetError(
            f"the {len(services)} services of this profile need at least {sum(floors.values())} MiB of memory floors, "
            f"but the budget is {int(budget_mb)} MiB ({MEMORY_SHARE:.0%} of {memory_gib:.1f} GiB). Give the Docker engine "
            f"at least {need_gib:.0f} GiB (Docker Desktop: Settings > Resources), choose a smaller --profile, or pass "
            f"--memory-gib to overcommit knowingly (PR #33 review r1 R1-04)")
    mem: dict[str, int] = {}
    pinned: set[str] = set()
    while True:
        rest_weight = sum(w for n, w in weights.items() if n not in pinned) or 1.0
        rest_budget = budget_mb - sum(floors[n] for n in pinned)
        newly = [n for n in weights if n not in pinned and math.floor(rest_budget * weights[n] / rest_weight) < floors[n]]
        if not newly:
            break
        pinned.update(newly)
    for n in weights:
        mem[n] = floors[n] if n in pinned else int(math.floor(rest_budget * weights[n] / rest_weight))
    out: dict[str, dict[str, Any]] = {}
    for svc in services:
        tpl = svc.template
        weight = weights[svc.name]
        cpu = min(cpus, max(0.5, cpus * CPU_OVERSUBSCRIBE * weight / total_weight))
        out[svc.name] = {"mem_limit": f"{mem[svc.name]}m", "cpus": round(cpu, 2), "pids_limit": int(tpl.get("pids_limit", 512))}
    return out


# --------------------------------------------------------------------------- rendering


def _mount(entry: dict[str, Any]) -> str:
    target = entry["target"]
    suffix = ":ro" if entry.get("ro") else ""
    if "volume" in entry:
        return f"{entry['volume']}:{target}{suffix}"
    if "config" in entry:
        return f"./{CONFIG_DIR}/{entry['config']}:{target}{suffix}"
    if "config_dir" in entry:
        return f"./{CONFIG_DIR}/{entry['config_dir']}:{target}{suffix}"
    raise ValueError(f"unknown volume entry {entry!r}")


def escape_compose_dollar(text: str) -> str:
    """`$` -> `$$` so Compose leaves the string for the container shell (a template never means host interpolation in a command)."""
    return text.replace("$", "$$")


def render_depends_on(entries: list[Any], in_profile: set[str]) -> list[str] | dict[str, dict[str, str]]:
    """Template `depends_on`: strings, or `{service, condition}` objects (Compose long form).

    Services outside the profile are dropped. The short list form is kept when no remaining entry
    carries a condition, so existing files do not change; otherwise every entry is written in the
    long form (`condition: service_started` for plain names)."""
    kept: list[tuple[str, str | None]] = []
    for entry in entries:
        if isinstance(entry, dict):
            name, cond = str(entry.get("service", "")), entry.get("condition")
        else:
            name, cond = str(entry), None
        if name in in_profile:
            kept.append((name, cond))
    if not kept:
        return []
    if all(cond is None for _, cond in kept):
        return [name for name, _ in kept]
    return {name: {"condition": cond or "service_started"} for name, cond in kept}


def render_service(
    svc: _manifest.Service,
    *,
    in_profile: set[str],
    host_ports: dict[str, int],
    container_ports: dict[str, int],
    published: dict[str, int],
    hardening: dict[str, dict[str, Any]],
    resources: dict[str, Any],
    platform_string: str,
    egress: set[str] | None = None,
    service_platform: str | None = None,
    extras: dict[str, str] | None = None,
) -> dict[str, Any]:
    egress = egress or set()
    tpl = substitute(svc.template, host_ports, container_ports, {**(extras or {}), "SERVICE_IMAGE": svc.image})
    exc = hardening.get(svc.name, {})
    relaxed = set(exc.get("controls", []))
    out: dict[str, Any] = {"image": svc.image}
    plat = service_platform or platform_string  # manifest build_platform wins over the host platform
    if plat and plat != "unknown":
        out["platform"] = plat
    if "command" in tpl:
        # Compose interpolates `$VAR`/`${VAR}` in every string of the file before the container's shell
        # sees it (review PR #30 R1-01: `$src` became ""). Commands are written for the container shell,
        # so every `$` is escaped to `$$`; only `environment` values keep Compose interpolation (`${KEY}`).
        out["command"] = [escape_compose_dollar(c) for c in tpl["command"]]
    if "user" not in relaxed:
        out["user"] = tpl.get("user", "1000:1000")
    elif tpl.get("run_as"):
        # a relaxed service may name the user it needs explicitly with `run_as` (an owner-init one-shot that
        # must run as root on an image whose own USER is 1000, PR #34 review r1 R1-01); `user` in a template
        # is only the non-root default and is dropped when the control is relaxed. The exception stays recorded.
        out["user"] = str(tpl["run_as"])
    out["read_only"] = "read_only" not in relaxed
    out["cap_drop"] = ["ALL"]
    if "cap_add" in relaxed and exc.get("cap_add"):
        out["cap_add"] = list(exc["cap_add"])
    out["security_opt"] = ["no-new-privileges:true"]
    if tpl.get("environment"):
        out["environment"] = dict(tpl["environment"])
    if tpl.get("env_files"):
        out["env_file"] = [f"./{CONFIG_DIR}/{name}" for name in tpl["env_files"]]
    if tpl.get("volumes"):
        out["volumes"] = [_mount(v) for v in tpl["volumes"]]
    if tpl.get("tmpfs"):
        # Compose's short `tmpfs:` entry mounts with mode 0755 owned by root (unlike `docker run --tmpfs`,
        # which uses 1777), so a non-root service could not write to it (real install run 11:
        # PermissionError on /code/website/static/built/nodeCategories.json). The docker-CLI option
        # suffix is accepted by Compose and gives the sticky world-writable mode a tmpfs is expected to have.
        out["tmpfs"] = [p if ":" in p else f"{p}:mode=1777" for p in tpl["tmpfs"]]
    if svc.name in published:
        out["ports"] = [f"{LOOPBACK}:{published[svc.name]}:{container_ports[svc.name]}"]
    expose = [str(p) for p in tpl.get("expose", [])]
    if "container_port" in tpl and str(tpl["container_port"]) not in expose and svc.name not in published:
        expose.insert(0, str(tpl["container_port"]))
    if expose:
        out["expose"] = expose
    deps = render_depends_on(tpl.get("depends_on", []), in_profile)
    if deps:
        out["depends_on"] = deps
    # grdm (internal) for every service; grdm-edge only where a port is published or egress was granted.
    on_edge = svc.name in published or svc.name in egress
    out["networks"] = [NETWORK, EDGE_NETWORK] if on_edge else [NETWORK]
    out["restart"] = "no" if tpl.get("one_shot") else tpl.get("restart", "unless-stopped")
    if tpl.get("stdin_open"):
        # invoke (osf.io's task runner) spawns a stdin-forwarding thread that calls FIONREAD on fd 0 and
        # dies with `OSError: [Errno 25] Not a tty` when stdin is closed (real install run 9); upstream's
        # compose file keeps stdin open for the same services.
        out["stdin_open"] = True
    out["init"] = True
    out.update(resources)
    out["labels"] = {
        "org.gakunin-rdm.component": svc.component,
        "org.gakunin-rdm.profile": svc.profile,
        "org.gakunin-rdm.hardening-exception": ",".join(sorted(relaxed)) if relaxed else "none",
        "org.gakunin-rdm.egress": "explicit" if svc.name in egress else "published" if svc.name in published else "none",
    }
    return out


def render_compose(
    services: list[_manifest.Service],
    *,
    runtime: Path,
    host_ports: dict[str, int],
    published: dict[str, int],
    hardening: dict[str, dict[str, Any]],
    memory_gib: float,
    cpus: float,
    platform_string: str,
    egress: list[str] | None = None,
    service_platforms: dict[str, str] | None = None,
    auth: str = "fakecas",
    allow_overcommit: bool = False,
) -> dict[str, Any]:
    egress = list(egress or [])
    service_platforms = service_platforms or {}
    extras = {"AUTH_URL": auth_url(auth, host_ports)}
    in_profile = {s.name for s in services}
    container_ports = {s.name: int(s.template.get("container_port", DEFAULT_PORTS.get(s.name, 0))) for s in services}
    for name, port in DEFAULT_PORTS.items():
        container_ports.setdefault(name, port)
    resources = scale_resources(services, memory_gib, cpus, allow_overcommit=allow_overcommit)
    rendered = {
        svc.name: render_service(
            svc,
            in_profile=in_profile,
            host_ports=host_ports,
            container_ports=container_ports,
            published=published,
            hardening=hardening,
            resources=resources[svc.name],
            platform_string=platform_string,
            egress=set(egress),
            service_platform=service_platforms.get(svc.name),
            extras=extras,
        )
        for svc in services
    }
    volumes = {
        name: {
            "driver": "local",
            "driver_opts": {"type": "none", "o": "bind", "device": str(runtime / VOLUMES_DIR / name)},
        }
        for name in volumes_of(services)
    }
    return {
        "name": PROJECT_NAME,
        "x-grdm-dev": {
            "generated": GENERATED_HEADER,
            "network_model": "ADR-02",
            "memory_gib": memory_gib,
            "cpus": cpus,
            "egress_services": egress,
        },
        # `grdm` first: scan --dynamic attaches ZAP to the first network and must reach services by name.
        "networks": {
            NETWORK: {"driver": "bridge", "internal": True, "name": f"{PROJECT_NAME}_{NETWORK}"},
            EDGE_NETWORK: {"driver": "bridge", "name": f"{PROJECT_NAME}_{EDGE_NETWORK}"},
        },
        "volumes": volumes,
        "services": rendered,
    }


# --------------------------------------------------------------------------- settings rewrite (ADR-02 §3.3)


def _ext(host_ports: dict[str, int], service: str, trailing: str = "") -> str:
    return f"http://{LOOPBACK}:{host_ports[service]}{trailing}"


def render_website_local_py(host_ports: dict[str, int]) -> str:
    """website/settings/local.py — internal URLs by service name, browser URLs on 127.0.0.1."""
    lines = [
        "# -*- coding: utf-8 -*-",
        f"# {GENERATED_HEADER}",
        "# Internal URLs use Compose service names; browser-facing URLs use http://127.0.0.1:<port>/ (ADR-02 §3.3).",
        "# Secrets come from the environment (runtime/.env via Compose), never from this file.",
        "import logging",
        "from os import environ",
        "",
        "from . import defaults",
        "",
        "DEV_MODE = True",
        "# DEBUG_MODE must stay True for a development server: api/base/wsgi.py monkey-patches gevent when",
        "# it is False, and Django's runserver then fails with 'DatabaseWrapper objects created in a thread",
        "# can only be used in that same thread' (real install run 14). The Django DEBUG flags of the api and",
        "# admin projects are set to False separately (api_local.py, admin_local.py) because their urls.py",
        "# import debug_toolbar under DEBUG and the image has no requirements/dev.txt (run 10).",
        "DEBUG_MODE = True",
        "SECURE_MODE = False",
        "PROTOCOL = 'http://'",
        "",
        f"DOMAIN = '{_ext(host_ports, 'web', '/')}'",
        "INTERNAL_DOMAIN = 'http://web:5000/'",
        f"API_DOMAIN = '{_ext(host_ports, 'api', '/')}'",
        f"WATERBUTLER_URL = '{_ext(host_ports, 'wb')}'",
        "WATERBUTLER_INTERNAL_URL = 'http://wb:7777'",
        f"MFR_SERVER_URL = '{_ext(host_ports, 'mfr')}'",
        "MFR_INTERNAL_SERVER_URL = 'http://mfr:7778'",
        f"CAS_SERVER_URL = '{_ext(host_ports, 'fakecas')}'",
        "CAS_INTERNAL_SERVER_URL = 'http://fakecas:8080'  # server-side ticket validation inside the network",
        f"ADMIN_URL = '{_ext(host_ports, 'admin', '/')}'",
        "ADMIN_INTERNAL_DOCKER_URL = 'http://admin:8001/'",
        "",
        "USE_EXTERNAL_EMBER = True",
        "PROXY_EMBER_APPS = True",
        "EMBER_DOMAIN = 'ember_osf_web'  # web proxies to the ember container by service name",
        f"LIVE_RELOAD_DOMAIN = '{_ext(host_ports, 'ember_osf_web')}'  # the browser reaches live reload on the host",
        "EXTERNAL_EMBER_APPS = {",
        "    'ember_osf_web': {",
        "        'server': 'http://ember_osf_web:4200/',",
        "        'path': '/ember_osf_web/',",
        "        'routes': ['collections', 'registries', 'handbook'],",
        "    },",
        "    # preprints and reviews are not run in this environment, but website/views.py reads",
        "    # EXTERNAL_EMBER_APPS['preprints']['path'] at import time (KeyError in real install run 9),",
        "    # so the keys exist with the same shape as upstream local-dist.py; nothing listens there.",
        "    'preprints': {'server': 'http://ember_osf_web:4201/', 'path': '/preprints/'},",
        "    'reviews': {'server': 'http://ember_osf_web:4203/', 'path': '/reviews/'},",
        "}",
        "PREPRINT_PROVIDER_DOMAINS = {'enabled': False, 'prefix': 'http://local.', 'suffix': ':4201/'}",
        "",
        "SEARCH_ENGINE = 'elastic'",
        "ELASTIC_URI = 'elasticsearch:9200'",
        "ELASTIC6_URI = 'elasticsearch6:9200'",
        "ELASTIC_TIMEOUT = 10",
        "",
        "USE_EMAIL = False",
        "MAIL_SERVER = 'localhost:1025'",
        "ENABLE_EMAIL_SUBSCRIPTIONS = False",
        "",
        "COOKIE_NAME = 'osf'",
        "OSF_COOKIE_DOMAIN = None",
        "SECRET_KEY = environ['SECRET_KEY']",
        "SESSION_COOKIE_SECURE = SECURE_MODE",
        "SESSION_COOKIE_SAMESITE = 'Lax'",
        "OSF_SERVER_KEY = None",
        "OSF_SERVER_CERT = None",
        "",
        "WATERBUTLER_JWE_SALT = environ['WATERBUTLER_JWE_SALT']",
        "WATERBUTLER_JWE_SECRET = environ['WATERBUTLER_JWE_SECRET']",
        "WATERBUTLER_JWT_SECRET = environ['WATERBUTLER_JWT_SECRET']",
        "",
        "",
        "class CeleryConfig(defaults.CeleryConfig):",
        "    broker_url = environ['BROKER_URL']",
        "",
        "",
        "USE_CDN_FOR_CLIENT_LIBS = False",
        "SENDGRID_WHITELIST_MODE = True",
        "SENDGRID_EMAIL_WHITELIST = []",
        "OSF_SUPPORT_EMAIL = 'support@example.invalid'",
        "OSF_CONTACT_EMAIL = 'contact@example.invalid'",
        "DOI_FORMAT = '{prefix}/FK2osf.io/{guid}'",
        "CHRONOS_USE_FAKE_FILE = True",
        "ENABLE_TIMESTAMP = False",
        "SHARE_ENABLED = False",
        "logging.getLogger('website.mails.mails').setLevel(logging.DEBUG)",
        "",
    ]
    return "\n".join(lines)


def render_admin_local_py() -> str:
    return "\n".join([
        f"# {GENERATED_HEADER}",
        "from .defaults import *  # noqa",
        "",
        "# Django DEBUG off for the admin project: admin/base/urls.py imports debug_toolbar under DEBUG and",
        "# the image has no requirements/dev.txt (real install run 10); website.settings.DEBUG_MODE itself",
        "# stays True (run 14). defaults.py has already appended debug_toolbar and nplusone to INSTALLED_APPS",
        "# and MIDDLEWARE at import time (it reads DEBUG_MODE before this file runs), so they are removed here (run 15).",
        "DEBUG = False",
        "INSTALLED_APPS = tuple(a for a in INSTALLED_APPS if a not in ('debug_toolbar', 'nplusone.ext.django'))",
        "MIDDLEWARE = tuple(m for m in MIDDLEWARE if not m.startswith(('debug_toolbar.', 'nplusone.')))",
        "# the browser reaches admin on the published loopback port (run 15: 400 DisallowedHost)",
        f"ALLOWED_HOSTS = list(ALLOWED_HOSTS) + ['{LOOPBACK}', 'localhost', 'admin']",
        "",
    ])


def render_api_local_py(host_ports: dict[str, int]) -> str:
    return "\n".join([
        f"# {GENERATED_HEADER}",
        "from .defaults import *  # noqa",
        "from os import environ",
        "from website import settings as osf_settings",
        "",
        "# Django DEBUG off: api/base/urls.py imports debug_toolbar under DEBUG and the image lacks it (run 10);",
        "# website.settings.DEBUG_MODE stays True so api/base/wsgi.py does not monkey-patch gevent (run 14).",
        "DEBUG = False",
        "SECRET_KEY = environ['API_SECRET_KEY']",
        "VARNISH_SERVERS = []",
        "ENABLE_VARNISH = False",
        "ENABLE_ESI = False",
        "CORS_ORIGIN_ALLOW_ALL = True",
        f"ALLOWED_HOSTS += ['{LOOPBACK}', 'localhost', 'api', 'web']",
        "",
        "REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {",
        "    'user': '1000000/second',",
        "    'non-cookie-auth': '1000000/second',",
        "    'add-contributor': '1000000/second',",
        "    'create-guid': '1000000/second',",
        "    'root-anon-throttle': '1000000/second',",
        "    'test-user': '2/hour',",
        "    'test-anon': '1/hour',",
        "    'send-email': '2/minute',",
        "    'burst': '10/second',",
        "}",
        "",
    ])


def _env_text(pairs: list[tuple[str, str]]) -> str:
    return f"# {GENERATED_HEADER}\n" + "".join(f"{k}={v}\n" for k, v in pairs)


def render_osf_env(host_ports: dict[str, int]) -> str:
    return _env_text([
        ("DOMAIN", _ext(host_ports, "web", "/")),
        ("INTERNAL_DOMAIN", "http://web:5000/"),
        ("API_DOMAIN", _ext(host_ports, "api", "/")),
        ("ELASTIC_URI", "elasticsearch:9200"),
        ("ELASTIC6_URI", "elasticsearch6:9200"),
        ("OSF_DB_HOST", "postgres"),
        ("OSF_DB_PORT", "5432"),
        ("OSF_DB_NAME", "osf"),
        ("OSF_DB_USER", "postgres"),
        ("DB_HOST", "postgres"),
        ("WATERBUTLER_URL", _ext(host_ports, "wb")),
        ("WATERBUTLER_INTERNAL_URL", "http://wb:7777"),
        ("CAS_SERVER_URL", _ext(host_ports, "fakecas")),
        ("CAS_INTERNAL_SERVER_URL", "http://fakecas:8080"),
        ("MFR_SERVER_URL", _ext(host_ports, "mfr")),
        ("MFR_INTERNAL_SERVER_URL", "http://mfr:7778"),
        ("REDIS_URL", "redis://redis:6379/1"),
        ("EMBER_DOMAIN", "ember_osf_web"),
        ("ADMIN_URL", _ext(host_ports, "admin", "/")),
        ("ADMIN_INTERNAL_DOCKER_URL", "http://admin:8001/"),
    ])


def render_wb_env(host_ports: dict[str, int]) -> str:
    return _env_text([
        ("DEBUG", ""),
        ("SERVER_CONFIG_DEBUG", ""),
        ("SERVER_CONFIG_ADDRESS", "0.0.0.0"),
        ("SERVER_CONFIG_PORT", "7777"),
        ("SERVER_CONFIG_DOMAIN", _ext(host_ports, "wb")),
        ("OSF_AUTH_CONFIG_API_URL", "http://web:5000/api/v1/files/auth/"),
        ("OSF_URL", "http://web:5000"),
    ])


def render_mfr_env(host_ports: dict[str, int]) -> str:
    allowed = " ".join(["http://web:5000/", "http://wb:7777/", _ext(host_ports, "web", "/"), _ext(host_ports, "wb", "/")])
    return _env_text([
        ("DEBUG", ""),
        ("SERVER_CONFIG_DEBUG", ""),
        ("SERVER_CONFIG_ADDRESS", "0.0.0.0"),
        ("SERVER_CONFIG_PORT", "7778"),
        ("SERVER_CONFIG_ALLOWED_PROVIDER_DOMAINS", f"'{allowed}'"),
        ("UNOCONV_PORT_2002_TCP_ADDR", "unoconv"),
        ("UNOCONV_PORT_2002_TCP_PORT", "2002"),
        ("EXTENSION_CONFIG_LOCAL_DEVELOPMENT", "1"),
        ("EXTENSION_CONFIG_DOCKER_LOCAL_HOST", "wb"),
        ("EXTENSION_CONFIG_LOCAL_HOST", LOOPBACK),
    ])


def render_sharejs_env(host_ports: dict[str, int]) -> str:
    return _env_text([
        ("SHAREJS_SERVER_HOST", "0.0.0.0"),
        ("SHAREJS_SERVER_PORT", "7007"),
        ("SHAREJS_DB_NAME", "sharejs"),
        ("SHAREJS_DB_URL", "mongodb://mongo:27017/sharejs?ssl=true"),
        ("SHAREJS_CORS_ALLOW_ORIGIN", _ext(host_ports, "web")),
    ])


def render_postgres_init() -> str:
    return f"-- {GENERATED_HEADER}\n-- cas-overlay keeps its tickets in a second database on the shared postgres.\nCREATE DATABASE cas;\n"


def render_cas_properties(host_ports: dict[str, int]) -> str:
    return "\n".join([
        f"# {GENERATED_HEADER}",
        "server.name=http://cas:8080",
        "server.prefix=${server.name}",
        f"osf.url={_ext(host_ports, 'web', '/')}",
        "osf.api.url=http://api:8000/",
        "database.url=jdbc:postgresql://postgres:5432/cas",
        "database.user=postgres",
        "# database.password is read from the DATABASE_PASSWORD environment variable",
        "",
    ])


def config_files(host_ports: dict[str, int]) -> dict[str, str]:
    """Relative path under runtime/config -> content."""
    return {
        "osf/local.py": render_website_local_py(host_ports),
        "osf/api_local.py": render_api_local_py(host_ports),
        "osf/admin_local.py": render_admin_local_py(),
        "osf.env": render_osf_env(host_ports),
        "wb.env": render_wb_env(host_ports),
        "mfr.env": render_mfr_env(host_ports),
        "sharejs.env": render_sharejs_env(host_ports),
        "postgres-init/10-cas.sql": render_postgres_init(),
        "cas/cas.properties": render_cas_properties(host_ports),
    }


# --------------------------------------------------------------------------- files


def _write_if_changed(path: Path, text: str, mode: int = 0o644) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)
    return True


def update_dotenv(path: Path, updates: dict[str, str]) -> bool:
    """Set keys in runtime/.env in place, keeping every other line and mode 0600."""
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        key = line.partition("=")[0].strip() if "=" in line and not line.lstrip().startswith("#") else None
        if key in updates:
            out.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            out.append(line)
    for key, value in updates.items():
        if key not in seen:
            out.append(f"{key}={value}")
    text = "\n".join(out) + "\n"
    changed = _write_if_changed(path, text, mode=0o600)
    os.chmod(path, 0o600)
    return changed


def built_image_tags(ctx: Context) -> dict[str, str]:
    """component id -> image tag from the latest build report, when one exists: the row's
    `image_tag` (`<base_sha12>-<overlay_sha12>` for an overlay component) or its sha12."""
    path = ctx.reports_dir / "build_latest.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {
        row["component"]: row.get("image_tag") or row["sha12"]
        for row in data.get("components", [])
        if row.get("sha12") and row.get("status") in ("built", "pushed")
    }


def detect_memory_gib() -> float | None:
    """Physical memory from os.sysconf (Linux, macOS); None when unknown. No subprocess, no Docker."""
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        if pages > 0 and page_size > 0:
            return pages * page_size / (1024 ** 3)
    except (ValueError, OSError, AttributeError):
        pass
    return None


def detect_docker_memory_gib(runner) -> float | None:
    """Memory of the Docker engine's VM (`docker info --format {{.MemTotal}}`), or None when the
    runner fails or prints something that is not a byte count. Read-only."""
    try:
        rc, out = runner(["docker", "info", "--format", "{{.MemTotal}}"])
    except Exception:  # a runner that only knows `docker compose ps` (tests) or a missing docker
        return None
    if rc != 0:
        return None
    try:
        total = int(str(out).strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None
    return total / (1024 ** 3) if total > 0 else None


# --------------------------------------------------------------------------- entry point



def _ensure_volume_dir(vol_dir: Path) -> None:
    """Create a host-side bind volume directory with mode 0755 the first time only.

    Containers only ever chown the directory (CAP_CHOWN works for any owner); the mode is set here
    while the host user still owns the fresh directory. After an init container has handed the
    directory to another uid (e.g. 1000 on a Linux host whose user is not 1000), the host user can
    no longer chmod it, so an existing directory is left untouched (PR #30 reviews r3/r4).
    """
    if vol_dir.exists():
        return
    vol_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(vol_dir, 0o755)  # nosemgrep: python.lang.security.audit.insecure-file-permissions.insecure-file-permissions -- world-readable directory for a bind volume; no secrets live here
    except PermissionError:
        pass  # created by someone else between exists() and here; leave the owner's mode alone

def run(
    ctx: Context,
    args,
    *,
    memory_gib: float | None = None,
    cpus: float | None = None,
    port_checker: PortChecker | None = None,
    platform_string: str | None = None,
    runner=None,
) -> int:
    """`runner(argv) -> (rc, stdout)` is used only for the read-only `docker compose ps` that finds our own
    running bindings; tests inject a fake."""
    if getattr(args, "compose_command", "render") != "render":
        return report.error(ctx, exit_codes.USAGE, "usage: grdm-dev compose render [--profile ...]")

    errors = _manifest.validate(ctx)
    if errors:
        for line in errors:
            sys.stderr.write(f"  - {line}\n")
        return report.error(ctx, exit_codes.MANIFEST_INVALID, f"{len(errors)} finding(s); run `grdm-dev manifest check`")

    dotenv = env_path(ctx)
    if not dotenv.exists():
        return report.error(ctx, exit_codes.USAGE, f"{dotenv} not found; run `grdm-dev secrets init` first")
    env = read_dotenv(dotenv)
    missing = [k for k in REQUIRED_SECRETS if not env.get(k)]
    if missing:
        return report.error(ctx, exit_codes.USAGE, f"runtime/.env lacks {', '.join(missing)}; run `grdm-dev secrets init --force` or `secrets rotate`")

    try:
        man = _manifest.load(ctx)
        profile = resolve_profile(ctx, env)
        auth = getattr(args, "auth", None) or _manifest.AUTH_FAKECAS
        services = _manifest.services_for_profile(man, profile, auth, image_tags=built_image_tags(ctx))
        hardening = load_hardening(ctx.root)
        service_platforms = {
            s.name: str(man.component(s.component).get("build_platform"))
            for s in services
            if man.component(s.component).get("build_platform")
        }
    except (_manifest.ManifestError, ValueError, OSError) as exc:
        return report.error(ctx, exit_codes.MANIFEST_INVALID, str(exc))

    service_names = [s.name for s in services]
    try:
        raw_egress = getattr(args, "egress", None)
        egress = parse_egress(raw_egress if raw_egress is not None else env.get(EGRESS_ENV_KEY), service_names)
    except ValueError as exc:
        return report.error(ctx, exit_codes.USAGE, str(exc))

    if runner is None:
        from . import health

        runner = health.default_runner
    owned = current_bindings(ctx, runner)
    rows, decisions, unresolved = assign_ports(published_ports(services, env), port_checker or default_port_checker, owned)
    if unresolved:
        return report.error(ctx, exit_codes.PORT_IN_USE, f"no free port within +{PORT_SEARCH_RANGE} for: {', '.join(unresolved)}")
    for d in decisions:
        if d["reason"] == "kept-own-binding":
            sys.stderr.write(f"[grdm-dev] compose render: {d['service']} keeps port {d['chosen']} (our own running container holds it)\n")
        elif d["reason"] == "remapped-foreign-listener":
            sys.stderr.write(f"[grdm-dev] compose render: {d['service']} port {d['wanted']} is held by another process; using {d['chosen']}\n")
    remapped = [{"service": d["service"], "wanted": d["wanted"], "chosen": d["chosen"]} for d in decisions if d["reason"] == "remapped-foreign-listener"]
    published = {r["service"]: int(r["host_port"]) for r in rows}
    host_ports = host_port_map(env, rows)

    explicit_memory = bool(getattr(args, "memory_gib", None)) or memory_gib is not None
    if memory_gib is None:
        memory_gib = getattr(args, "memory_gib", None)
        if not memory_gib:
            host_gib = detect_memory_gib()
            vm_gib = detect_docker_memory_gib(runner)
            # Docker Desktop (macOS, Windows) runs containers in a VM whose memory is a fraction of the
            # host's: on the 128 GiB Mac Studio the VM had 47 GiB, so a budget scaled from the host let
            # the sum of mem_limit exceed what the engine can give (real install run 10). The smaller
            # of the two is the real ceiling; on Linux both are the same number.
            candidates = [g for g in (host_gib, vm_gib) if g]
            memory_gib = min(candidates) if candidates else DEFAULT_MEMORY_GIB
            if vm_gib and host_gib and vm_gib < host_gib:
                sys.stderr.write(f"[grdm-dev] compose render: memory budget uses the Docker VM's {vm_gib:.1f} GiB, not the host's {host_gib:.1f} GiB\n")
    if cpus is None:
        cpus = getattr(args, "cpus", None) or float(os.cpu_count() or 0) or DEFAULT_CPUS
    platform_string = platform_string or getattr(args, "platform", None) or detect_platform()

    try:
      compose = render_compose(
        services,
        runtime=ctx.runtime,
        host_ports=host_ports,
        published=published,
        hardening=hardening,
        memory_gib=float(memory_gib),
        cpus=float(cpus),
        platform_string=platform_string,
        egress=egress,
        service_platforms=service_platforms,
        auth=auth,
        allow_overcommit=explicit_memory,
      )
    except MemoryBudgetError as exc:
        return report.error(ctx, exit_codes.HOST_UNSUPPORTED, f"memory: {exc}")
    compose_text = json.dumps(compose, indent=2, ensure_ascii=False) + "\n"
    configs = config_files(host_ports)
    for text in [compose_text, *configs.values()]:
        if FORBIDDEN_ADDRESS in text:  # defence in depth: ADR-02 forbids the alias anywhere
            return report.error(ctx, exit_codes.MANIFEST_INVALID, f"generated output contains {FORBIDDEN_ADDRESS}")

    ctx.runtime.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    if _write_if_changed(ctx.runtime / COMPOSE_FILE, compose_text):
        written.append(COMPOSE_FILE)
    for rel, text in configs.items():
        if _write_if_changed(ctx.runtime / CONFIG_DIR / rel, text):
            written.append(f"{CONFIG_DIR}/{rel}")
    for name in compose["volumes"]:
        _ensure_volume_dir(ctx.runtime / VOLUMES_DIR / name)
    env_updates = {PROFILE_ENV_KEY: profile, EGRESS_ENV_KEY: ",".join(egress)}
    env_updates.update({port_key(name): str(port) for name, port in published.items()})
    if update_dotenv(dotenv, env_updates):
        written.append(f".env (GRDM_PROFILE, GRDM_PORT_*, {EGRESS_ENV_KEY})")

    data = {
        "profile": profile,
        "auth": auth,
        "platform": platform_string,
        "compose_file": str(ctx.runtime / COMPOSE_FILE),
        "network": NETWORK,
        "networks": {NETWORK: "internal (no egress)", EDGE_NETWORK: "bridge; publishing services" + (" + --egress" if egress else "")},
        "egress_services": egress,
        "memory_gib": round(float(memory_gib), 1),
        "cpus": float(cpus),
        "services": [
            {
                "service": s.name,
                "image": s.image,
                "origin": s.origin,
                "platform": compose["services"][s.name].get("platform", "unknown"),
                "user": compose["services"][s.name].get("user", "image default"),
                "read_only": compose["services"][s.name]["read_only"],
                "mem_limit": compose["services"][s.name]["mem_limit"],
                "cpus": compose["services"][s.name]["cpus"],
                "exceptions": compose["services"][s.name]["labels"]["org.gakunin-rdm.hardening-exception"],
            }
            for s in services
        ],
        "ports": rows,
        "port_decisions": decisions,
        "remapped_ports": remapped,
        "volumes": list(compose["volumes"]),
        "config_files": [f"{CONFIG_DIR}/{rel}" for rel in configs],
        "written": written or ["(unchanged)"],
    }
    report.emit(ctx, "compose", data)
    return exit_codes.OK
