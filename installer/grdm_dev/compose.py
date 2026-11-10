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
  component carries `build_platform` (SPEC-01; e.g. mfr, ember-osf-web on
  "linux/amd64"): that value is written instead so Compose runs the image built by `grdm-dev build`
  under emulation on an arm64 host;
* `image:` is the manifest-derived reference: `grdm-dev/<component>:<sha12>` for a built component
  (sha12 from the build report when present and equal to the manifest pin; a recorded build that
  differs from the pin is stale, so the pinned tag is rendered, `stale_build_tags` lists it in the
  report and stderr says to run `grdm-dev build` before `up`; the build report's tag is used as is
  only for a component the manifest does not pin), `grdm-dev/<overlay>:<base_sha12>-<overlay_sha12>` for
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
target, ro?}]), tmpfs?, user?, only_networks?, extra_networks?, depends_on? (service names, or {service, condition} for the Compose
long form, e.g. `service_completed_successfully` on a one-shot), restart?, one_shot? (a container
that runs to completion: rendered with `restart: "no"`, and `health` accepts `exited` with code 0),
weight, mem_min_mb, pids_limit, note?. Strings may use
`{{HOST_PORT:<service>}}` / `{{CONTAINER_PORT:<service>}}`. `command` strings are written for the
container shell: every `$` in them is escaped to `$$` on output, so Compose does not interpolate
them; `environment` values are the only place where `${KEY}` means a value from runtime/.env.

Upstream settings are rewritten under runtime/config/ (ADR-02 §3.3): osf/local.py, osf/api_local.py,
osf.env, wb.env, mfr.env, sharejs.env, postgres-init/10-cas.sql, cas/cas.properties, cas/services/. Internal URLs use
service names, browser-facing URLs use http://127.0.0.1:<port>.
"""
from __future__ import annotations

import json
import math
import os
import platform
import re
import socket
import stat
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

from . import exit_codes, host, manifest as _manifest, report
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
CONVERT_NETWORK = "grdm-convert"  # internal: true — mfr and the document converter, nothing else (ADR-07)
EGRESS_ENV_KEY = "GRDM_EGRESS_SERVICES"
EGRESS_NONE = "none"
PROJECT_NAME = "grdm-dev"
COMPOSE_FILE = "docker-compose.yml"
CONFIG_DIR = "config"
VOLUMES_DIR = "volumes"
OWNER_INIT_SERVICE = "volume_owner_init"  # one-shot: hands every writable bind volume to its non-root owner
OWNER_INIT_MOUNT = "/volumes"
ACCESS_CHECK_PREFIX = "volume_access_check_"  # one-shots, one per owner uid: write a probe file as that uid
# Mounts that present every path as root:root and ignore chown: Docker Desktop (fakeowner, fuse.grpcfuse),
# Colima and Lima (virtiofs measured; 9p, fuse.sshfs). Anywhere else a chown without effect is a failure.
OWNERSHIP_IGNORING_FILESYSTEMS = ("virtiofs", "fakeowner", "fuse.grpcfuse", "fuse.sshfs", "9p")
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

from .secrets import cas_key_problems as _cas_key_problems  # noqa: E402

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

    def __init__(self, message: str, need_gib: float):
        super().__init__(message)
        self.need_gib = need_gib


def memory_floor_need_gib(services: list[_manifest.Service]) -> float:
    """Memory the engine must have for this profile's `mem_min_mb` floors to fit the budget."""
    return sum(int(s.template.get("mem_min_mb", 128)) for s in services) / 1024 / MEMORY_SHARE


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
        need_gib = memory_floor_need_gib(services)
        raise MemoryBudgetError(
            f"the {len(services)} services of this profile need at least {sum(floors.values())} MiB of memory floors, "
            f"but the budget is {int(budget_mb)} MiB ({MEMORY_SHARE:.0%} of {memory_gib:.1f} GiB). Choose a smaller --profile, "
            f"pass --memory-gib to overcommit knowingly (PR #33 review r1 R1-04), or give the Docker engine at least {need_gib:.0f} GiB",
            need_gib)
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


def volume_owners(services: list[_manifest.Service], hardening: dict[str, dict[str, Any]]) -> tuple[dict[str, str], dict[str, list[str]]]:
    """The owner each writable bind volume needs, and the services that must wait for it being set.

    Returns ({volume: "uid:gid"}, {service: [volumes]}). The owner is the fixed `user:` of the services
    that mount the volume writable. A service with the `user` control relaxed starts as root and may set
    its own ownership, so it never decides an owner: chowning postgres_data to anything but its own uid
    would break it. It still waits when it shares a volume that has an owner. Two
    different owners for one volume are a template error (ValueError, exit 20 upstream)."""
    owners: dict[str, str] = {}
    writers: dict[str, list[str]] = {}
    relaxed_services: list[_manifest.Service] = []
    for svc in services:
        if svc.name == OWNER_INIT_SERVICE or svc.name.startswith(ACCESS_CHECK_PREFIX):
            continue
        if "user" in set(hardening.get(svc.name, {}).get("controls", [])):
            relaxed_services.append(svc)
            continue
        user = str(svc.template.get("user", "1000:1000"))
        for mount in svc.template.get("volumes", []):
            name = mount.get("volume")
            if not name or mount.get("ro"):
                continue
            if owners.setdefault(name, user) != user:
                raise ValueError(f"volume {name}: services need different owners ({owners[name]} and {user}, service {svc.name})")
            writers.setdefault(svc.name, []).append(name)
    for svc in relaxed_services:
        shared = [m["volume"] for m in svc.template.get("volumes", []) if m.get("volume") in owners and not m.get("ro")]
        if shared:
            writers[svc.name] = shared
    return owners, writers


def _owner_init_command(owners: dict[str, str]) -> list[str]:
    """Hand every volume to its owner (SPEC-02 §4, the migration and retry contract).

    Every `up` walks the whole tree; there is no marker and no shortcut on the top directory, so a run that
    stopped half way is finished by the next one, and a correct top directory cannot hide wrong descendants.
    A root with only CAP_CHOWN is subject to file permissions and cannot enter another uid's 0700 directory,
    but it may take ownership of it and then enter as its owner: the loop does that one level per pass, only for
    directories "other" cannot read, with -prune because GNU find does not act on a directory it cannot open
    (measured), and stops if a pass makes no progress. It needs GNU coreutils: the elasticsearch2 base has uutils
    chown, which returned 0 without changing such a directory (measured), so the step runs on the postgres image.
    A walk that fails must stop the step, so no `find` is piped (a pipeline reports the last command, and a
    `while` condition ignores `set -e`); its whole output is captured and its status checked (R4-01).
    A chown that exits 0 proves nothing, so every result is read back: files by a walk while the tree is open,
    directories one by one, deepest first, while their parent is still open (a private directory handed back
    cannot be reached again by this process; the next run reopens it).

    A top directory that keeps its old owner after chown stops the step, unless its mount is one of
    OWNERSHIP_IGNORING_FILESYSTEMS, the VM shares that present every path as root:root (measured on Colima
    virtiofs: chown exits 0, stat still reads 0:0). Even then only the volume_access_check_* one-shots, which
    run as the real uid and walk the existing tree, establish that the writers can use it. Nothing follows symlinks or leaves the volume."""
    steps = "".join(f'fix {owner} {OWNER_INIT_MOUNT}/{name}; ' for name, owner in owners.items())
    different = '\\( ! -user "$u" -o ! -group "$g" \\)'
    private = "-type d ! -user 0 ! -perm -005 -prune"
    ignoring = "|".join(OWNERSHIP_IGNORING_FILESYSTEMS)
    failed = 'echo "volume_owner_init: cannot walk $2" >&2; exit 1;'
    # awk prints the filesystem type: the field after the "-" separator of the line whose mount point is $2
    fstype = """$(awk -v m="$2" '$5 == m { for (i = 7; i <= NF; i++) if ($i == "-") t = $(i + 1) } END { print t }' /proc/self/mountinfo)"""
    back = """for d; do chown -h "$0" "$d"; if [ "$(stat -c %u:%g "$d")" != "$0" ]; then echo "volume_owner_init: $d stayed $(stat -c %u:%g "$d") after chown to $0" >&2; exit 1; fi; done"""
    function = (
        'fix() { chown -h "$1" "$2"; '
        's=$(stat -c %u:%g "$2"); if [ "$s" != "$1" ]; then t=' + fstype + '; case "$t" in '
        f'{ignoring}) echo "$2: $t does not keep ownership; volume_access_check decides whether the writers can use it"; return 0;; '
        '*) echo "volume_owner_init: $2 stayed $s after chown to $1 on filesystem [$t]" >&2; exit 1;; esac; fi; '
        'u=${1%:*}; g=${1#*:}; prev=; '
        f'while :; do now=$(find "$2" -xdev {private}) || {{ {failed} }}; [ -n "$now" ] || break; '
        'if [ "$now" = "$prev" ]; then echo "volume_owner_init: cannot take ownership of $now" >&2; exit 1; fi; prev=$now; '
        f'find "$2" -xdev {private} -exec chown -h 0:0 {{}} + ; done; '
        f'find "$2" -xdev ! -type d {different} -exec chown -h "$1" {{}} + ; '
        f'left=$(find "$2" -xdev ! -type d {different}) || {{ {failed} }}; '
        'if [ -n "$left" ]; then echo "volume_owner_init: $left is not $1; run up again, or reset to start over" >&2; exit 1; fi; '
        f"""find "$2" -xdev -depth -type d {different} -exec sh -c '{back}' "$1" {{}} + ; }}; """
    )
    return ["sh", "-c", f"set -e; {function}{steps}ls -ld {OWNER_INIT_MOUNT}/*"]


def _access_check_command(volumes: list[str]) -> list[str]:
    """As the writer's own uid: prove it can create a file in each volume and use what is already there.

    The probe file comes from mktemp, which creates a new name exclusively and never follows a symlink, and
    only that file is removed, so nothing existing can be truncated (PR #36 review r3 R3-02). The walk asks the
    kernel about access (GNU find -readable, -writable, -executable), changing nothing: a writable root says
    nothing about a private child (R3-01). A directory must be enterable, listable and writable; a file readable.
    -prune because GNU find does not act on a directory it cannot open (measured)."""
    paths = " ".join(f"{OWNER_INIT_MOUNT}/{name}" for name in volumes)
    denied = r"\( -type d \( ! -readable -o ! -executable -o ! -writable \) -prune -o ! -type d ! -type l ! -readable \)"
    return ["sh", "-c", (
        f'set -e; for v in {paths}; do p=$(mktemp "$v/.grdm-write-probe.XXXXXX"); rm -f -- "$p"; '
        f'bad=$(find "$v" -xdev {denied} -print) || {{ echo "volume_access_check: cannot walk $v" >&2; exit 1; }}; '
        'if [ -n "$bad" ]; then echo "volume_access_check: uid $(id -u) cannot use $bad" >&2; exit 1; fi; '
        'echo "$v: usable by $(id -u)"; done'
    )]


def with_owner_init(services: list[_manifest.Service], hardening: dict[str, dict[str, Any]]) -> list[_manifest.Service]:
    """Fill the owner step and the per-uid access checks from the profile; every writer waits for both. No-op without the step."""
    if not any(s.name == OWNER_INIT_SERVICE for s in services):
        return services
    owners, writers = volume_owners(services, hardening)
    finished = "service_completed_successfully"
    wait_owner = {"service": OWNER_INIT_SERVICE, "condition": finished}
    checks = {svc.template.get("user"): svc.name for svc in services if svc.name.startswith(ACCESS_CHECK_PREFIX)}
    out: list[_manifest.Service] = []
    for svc in services:
        if svc.name == OWNER_INIT_SERVICE:
            mounts = [{"volume": name, "target": f"{OWNER_INIT_MOUNT}/{name}"} for name in owners]
            out.append(replace(svc, template={**svc.template, "volumes": mounts, "command": _owner_init_command(owners)}))
        elif svc.name.startswith(ACCESS_CHECK_PREFIX):
            names = [name for name, owner in owners.items() if owner == svc.template.get("user")]
            if names:  # a uid that owns nothing in this profile has nothing to prove
                mounts = [{"volume": name, "target": f"{OWNER_INIT_MOUNT}/{name}"} for name in names]
                out.append(replace(svc, template={**svc.template, "volumes": mounts, "command": _access_check_command(names), "depends_on": [wait_owner]}))
        elif svc.name in writers:
            needed = sorted({checks[owners[v]] for v in writers[svc.name] if owners[v] in checks})
            depends = [*svc.template.get("depends_on", []), wait_owner, *({"service": c, "condition": finished} for c in needed)]
            out.append(replace(svc, template={**svc.template, "depends_on": depends}))
        else:
            out.append(svc)
    return out


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
    # A template may replace grdm (`only_networks`) or add to it (`extra_networks`): the converter of untrusted
    # documents shares a network with mfr only.
    on_edge = svc.name in published or svc.name in egress
    networks = list(tpl.get("only_networks") or [NETWORK]) + list(tpl.get("extra_networks", []))
    out["networks"] = networks + [EDGE_NETWORK] if on_edge else networks
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
    services = with_owner_init(services, hardening)
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
            CONVERT_NETWORK: {"driver": "bridge", "internal": True, "name": f"{PROJECT_NAME}_{CONVERT_NETWORK}"},
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
        "# web alone runs with False (GRDM_OSF_DEBUG_MODE in its template): the mako filter webpack_asset returns the",
        "# unhashed name in debug mode, and the image holds only hashed bundles (webpack-prod), so every legacy page",
        "# 404ed on base-page.js, vendor.js and project-base-page.js. web never imports api/base/wsgi.py.",
        "DEBUG_MODE = environ.get('GRDM_OSF_DEBUG_MODE', 'True') == 'True'",
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
        "DEFAULT_HMAC_SECRET = environ['WATERBUTLER_HMAC_SECRET']",
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
        "# The institution login keys CAS encrypts and signs with; api/base/settings/defaults.py carries public defaults.",
        "JWE_SECRET = environ['OSF_API_INSTITUTIONS_AUTH_JWESECRET'].encode('utf-8')",
        "JWT_SECRET = environ['OSF_API_INSTITUTIONS_AUTH_JWTSECRET'].encode('utf-8')",
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


def render_wiki_local_py(published: dict[str, int]) -> str:
    """addons/wiki/settings/local.py — the host:port the browser uses for the wiki's collaboration services.

    Upstream defaults are `localhost:<port>`, which is not the loopback origin of ADR-02. Only a service that
    `compose render` really publishes is rewritten: advertising a port nothing listens on would be worse.
    SHAREJS_HOST / SHAREJS_PORT stay untouched; they address sharejs from the server side.
    """
    lines = [
        "# -*- coding: utf-8 -*-",
        f"# {GENERATED_HEADER}",
        "# Browser-facing collaboration endpoints only (ADR-02 §3.3): published services on the loopback address.",
    ]
    for setting, service in (("Y_WEBSOCKET_URL", "y_websocket"), ("SHAREJS_URL", "sharejs")):
        if service in published:
            lines.append(f"{setting} = '{LOOPBACK}:{published[service]}'")
    return "\n".join(lines) + "\n"


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
        ("OSF_PROVIDER_CONFIG_CREDENTIAL_SOURCE_ORIGINS", "http://web:5000"),
        ("OSF_PROVIDER_CONFIG_CREDENTIAL_TARGET_ORIGINS", "http://wb:7777"),
        ("UNOCONV_PORT_2002_TCP_ADDR", "unoconv"),
        ("UNOCONV_PORT_2002_TCP_PORT", "2002"),
        ("UNOCONV_CONVERT_URL", "http://unoconv:2002/convert"),
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


# Federation clients the CAS context always constructs; the values are the ones the image ships in etc/cas.properties.
_CAS_DELEGATED_CLIENTS = {
    "callutheran": ("https://sso.callutheran.edu/cas/login", "https://sso.callutheran.edu/cas/"),
    "cord": ("https://bprdeis.cord.edu:8443/cas/login", "https://bprdeis.cord.edu:8443/cas/"),
    "okstate": ("https://stwcas.okstate.edu/cas/login", "https://stwcas.okstate.edu/cas/"),
}


def render_cas_properties(host_ports: dict[str, int]) -> str:
    """The whole of /etc/cas/cas.properties for the image built from the integration repository (ADR-07).

    Secrets are not here: Spring reads DATABASE_PASSWORD, OSF_DATABASE_PASSWORD, TGC_ENCRYPTION_KEY, TGC_SIGNING_KEY
    and OSF_API_INSTITUTIONS_AUTH_JW{E,T}SECRET from the environment. The Secure flags are off because the stack is
    plain HTTP on loopback (ADR-02); the image's own default is on."""
    web = _ext(host_ports, "web", "/")
    lines = [
        f"# {GENERATED_HEADER}",
        "server.name=http://cas:8080",
        "server.prefix=${server.name}",
        f"osf.url={web}",
        f"osf.resendConfirmation.url={web}resend/",
        f"osf.forgotPassword.url={web}forgotpassword/",
        f"osf.createAccount.url={web}register/",
        "osf.api.url=http://api:8000/",
        "database.url=jdbc:postgresql://postgres:5432/cas",
        "database.user=postgres",
        "database.driverClass=org.postgresql.Driver",
        "database.hibernate.dialect=org.hibernate.dialect.PostgreSQLDialect",
        "osf.database.url=jdbc:postgresql://postgres:5432/osf",
        "osf.database.user=postgres",
        "osf.database.driverClass=org.postgresql.Driver",
        "osf.database.hibernate.dialect=io.cos.cas.adaptors.postgres.hibernate.OSFPostgreSQLDialect",
        "osf.api.institutions.auth.url=http://api:8000/v2/institutions/auth/",
        "osf.api.institutions.login.availability.url=http://api:8000/v2/institutions/login_availability/",
        "osf.api.institutions.auth.xslLocation=file:/etc/cas/institutions-auth.xsl",
        "log4j.config.location=file:/etc/cas/log4j2.xml",
        "service.registry.config.location=file:/etc/cas/services",
        "cas.securityContext.status.access=hasIpAddress('127.0.0.1')",
        "cas.securityContext.statistics.access=hasIpAddress('127.0.0.1')",
        "cas.themeResolver.defaultThemeName=cas-theme-default",
        "delegation.redirect.uri=${server.name}/login",
        "host.name=cas",
        "oauth.orcid.client.id=grdm-dev-orcid-not-configured",
        "oauth.orcid.client.secret=grdm-dev-orcid-not-configured",
        "oauth.orcid.member=false",
        "oauth.orcid.scope=/authenticate",
        "tgc.cookie.secure=false",
        "jsession.cookie.secure=false",
    ]
    for name, (login_url, prefix_url) in _CAS_DELEGATED_CLIENTS.items():
        lines += [
            f"cas.{name}.login.url={login_url}",
            f"cas.{name}.prefix.url={prefix_url}",
            f"cas.{name}.client.name={name}",
            f"cas.{name}.cas.protocol=SAML",
        ]
    return "\n".join(lines) + "\n"


def render_cas_service(host_ports: dict[str, int]) -> str:
    """The only application CAS may issue tickets for: the web service at its published URL. The mount replaces the
    image's /etc/cas/services, whose definitions name other hosts and ports."""
    title = {
        "@class": "org.jasig.cas.services.DefaultRegisteredServiceProperty",
        "values": ["java.util.HashSet", ["GakuNin RDM"]],
    }
    service = {
        "@class": "org.jasig.cas.services.RegexRegisteredService",
        "id": 1,
        "name": "grdm-web",
        "description": GENERATED_HEADER,
        "serviceId": f"^http://{re.escape(LOOPBACK)}:{host_ports['web']}/.*",
        "evaluationOrder": "1000",
        "logo": "",
        "attributeReleasePolicy": {
            "@class": "org.jasig.cas.services.ReturnAllowedAttributeReleasePolicy",
            "allowedAttributes": ["java.util.ArrayList", ["givenName", "familyName"]],
        },
        "properties": {"@class": "java.util.HashMap", "title": title, "titleAbbr": title},
    }
    return json.dumps(service, indent=2, ensure_ascii=False) + "\n"


def config_files(host_ports: dict[str, int], published: dict[str, int]) -> dict[str, str]:
    """Relative path under runtime/config -> content."""
    return {
        "osf/local.py": render_website_local_py(host_ports),
        "osf/wiki_local.py": render_wiki_local_py(published),
        "osf/api_local.py": render_api_local_py(host_ports),
        "osf/admin_local.py": render_admin_local_py(),
        "osf.env": render_osf_env(host_ports),
        "wb.env": render_wb_env(host_ports),
        "mfr.env": render_mfr_env(host_ports),
        "sharejs.env": render_sharejs_env(host_ports),
        "postgres-init/10-cas.sql": render_postgres_init(),
        "cas/cas.properties": render_cas_properties(host_ports),
        "cas/services/grdm-web.json": render_cas_service(host_ports),
    }


# --------------------------------------------------------------------------- files


def _write_if_changed(path: Path, text: str, mode: int = 0o644) -> bool:
    """Write `text` to `path` when it differs. A new file is created atomically (temp file + rename); an
    existing file is rewritten **in place** so its inode survives: the generated settings files are
    bind-mounted one by one into running containers, and a rename would leave those containers with a
    deleted inode ("No such file or directory: /code/website/settings/local.py" from `docker compose exec`
    after a re-render, real acceptance run 2). The running process keeps its old settings until it is
    restarted; `up` recreates a container only when the Compose file itself changed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") == text:
            return False
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return True
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


def split_stale_build_tags(man: _manifest.Manifest, recorded: dict[str, str]) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Keep the build report's tags that agree with the manifest pin; return the others as stale.

    `grdm-dev build` always builds the pinned commit, so a recorded tag that differs from the tag the
    manifest pins means the pin moved after the last build. Using the record then runs the old image
    without a word (it happened on 2026-11-10: the pin of osf.io moved and `compose render` ran before
    `build`). For a stale component the manifest pin wins, and the caller warns. A component the manifest
    does not pin (no `integration_sha` and no merged upstream, or an overlay whose base is unpinned) keeps
    the recorded tag, because nothing else names the commit that was built.

    Returns (tags to use, stale rows {component, pinned, recorded, image}).
    """
    usable: dict[str, str] = {}
    stale: list[dict[str, str]] = []
    for cid, tag in recorded.items():
        try:
            comp = man.component(cid)
        except KeyError:
            continue  # a component no longer in the manifest renders nothing
        base = man.component(comp.overlay_of) if comp.is_overlay else None
        pinned = comp.sha12 if base is None else (
            _manifest.overlay_tag(base.sha12, comp.sha12) if (base.sha12 and comp.sha12) else None)
        if not comp.is_built or pinned is None or tag == pinned:
            usable[cid] = tag
            continue
        stale.append({"component": cid, "pinned": pinned, "recorded": tag, "image": comp.local_image(pinned)})
    return usable, stale


def stale_build_warning(stale: list[dict[str, str]]) -> str:
    """The loud stderr block for `compose render` when the last build is older than the manifest pin."""
    lines = ["", "[grdm-dev] compose render: WARNING: the last build does not match the manifest pin", ""]
    for row in stale:
        lines.append(f"  {row['component']}: manifest pins {row['pinned']}, last build recorded {row['recorded']}")
    lines += [
        "",
        "  The rendered file uses the pinned tag(s), not the recorded build, so old images never run silently.",
        "  Fix: run `grdm-dev build` now, then `grdm-dev up` (`up` cannot start an image that was never built).",
        "",
    ]
    return "\n".join(lines) + "\n"


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


def detect_docker_cpus(runner) -> float | None:
    """CPUs of the Docker engine's VM (`docker info --format {{.NCPU}}`), or None when unknown. Read-only."""
    try:
        rc, out = runner(["docker", "info", "--format", "{{.NCPU}}"])
    except Exception:  # a runner that only knows `docker compose ps` (tests) or a missing docker
        return None
    if rc != 0:
        return None
    try:
        count = int(str(out).strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None
    return float(count) if count > 0 else None


# --------------------------------------------------------------------------- entry point



def host_mount_points() -> list[str] | None:
    """Every mount point of this host, from the mount table; None when the table cannot be read.
    A same-filesystem bind mount has no device-number difference, so only the table reveals it."""
    system = platform.system()
    try:
        if system == "Linux":
            with open("/proc/self/mountinfo", encoding="utf-8", errors="surrogateescape") as fh:
                return [re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), line.split()[4]) for line in fh if len(line.split()) > 4]
        if system == "Darwin":
            out = subprocess.run(["/sbin/mount"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=15, check=True).stdout
            points = [m.group(1) for m in re.finditer(r"^.+? on (.+) \(", out, re.MULTILINE)]
            return points or None
    except (OSError, subprocess.SubprocessError):
        return None
    return None


def volume_root_identity(runtime: Path) -> tuple[int, int, int] | None:
    """(device, inode, file type) of the volumes root as it is now, or None when absent: the same path may be
    something else later. The type counts because a filesystem can give a replacement the inode just freed (seen
    on ext4 in CI); a replacement directory that reuses the inode is within the limit stated in SPEC-02 §3."""
    try:
        info = (runtime / VOLUMES_DIR).lstat()
    except OSError:
        return None
    return info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode)


def volume_path_problems(root: Path, runtime: Path, names: list[str] | None = None) -> list[str]:
    """Why runtime/volumes/ (or one of `names`, default every entry) must not be mounted or deleted.

    A root container follows the bind source on the host side, so restricting the path inside the
    container restricts nothing (PR #36 review r1 R1-01): a symlink here would hand an unrelated directory
    to the owner step or to `reset`. Refused: a symlinked runtime/ or volumes root, a root that resolves
    outside the checkout, a symlinked volume, runtime/ or the volumes root being a mount, and any mount at
    any depth inside the tree, by the host mount table (same-filesystem bind mounts included), because the
    host fallback of `reset` is an ordinary rmtree. A table that cannot be read refuses too.

    This is a snapshot: Docker resolves the bind later and no check can close that window, so the checkout
    is assumed not to be changed concurrently by someone else (SPEC-02 §3). `reset` repeats it at each step."""
    base = runtime / VOLUMES_DIR
    for path in (runtime, base):
        if path.is_symlink():
            return [f"{path} is a symbolic link"]
    mounts = host_mount_points()
    if mounts is None:
        return ["the host mount table cannot be read, so mounts inside runtime/volumes cannot be excluded"]
    top = str(runtime.resolve())
    inside = str(runtime.resolve() / VOLUMES_DIR)
    data_prefix = "/System/Volumes/Data"  # macOS lists firmlinked paths under it
    for point in mounts:
        point = point[len(data_prefix):] if point.startswith(data_prefix + "/") else point
        if point == top or point == inside or point.startswith(inside + "/"):
            return [f"{point} is a mount inside the runtime tree"]
    if not base.exists():
        return []
    expected = root.resolve() / runtime.name / VOLUMES_DIR
    if base.resolve() != expected:
        return [f"{base} resolves to {base.resolve()}, outside {expected.parent}"]
    problems: list[str] = []
    try:
        entries = names if names is not None else sorted(p.name for p in base.iterdir())
        base_dev = base.stat().st_dev
    except OSError as exc:
        return [f"cannot inspect {base}: {exc}"]
    for name in entries:
        path = base / name
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            problems.append(f"cannot inspect {path}: {exc}")
            continue
        if stat.S_ISLNK(info.st_mode):
            problems.append(f"{path} is a symbolic link")
        elif stat.S_ISDIR(info.st_mode) and info.st_dev != base_dev:
            problems.append(f"{path} is a separate mount")
    return problems


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
    bad_lengths = _cas_key_problems(env)
    if bad_lengths:
        return report.error(ctx, exit_codes.USAGE, f"runtime/.env has an unusable value (length, alphabet or a published default) for {', '.join(bad_lengths)} (SPEC-02 §3); run `grdm-dev secrets rotate`")

    try:
        man = _manifest.load(ctx)
        profile = resolve_profile(ctx, env)
        auth = getattr(args, "auth", None) or _manifest.AUTH_FAKECAS
        image_tags, stale_builds = split_stale_build_tags(man, built_image_tags(ctx))
        services = _manifest.services_for_profile(man, profile, auth, image_tags=image_tags)
        rendered_components = {s.component for s in services}
        stale_builds = [row for row in stale_builds if row["component"] in rendered_components]
        hardening = load_hardening(ctx.root)
        service_platforms = {
            s.name: str(man.component(s.component).get("build_platform"))
            for s in services
            if man.component(s.component).get("build_platform")
        }
    except (_manifest.ManifestError, ValueError, OSError) as exc:
        return report.error(ctx, exit_codes.MANIFEST_INVALID, str(exc))

    bad_paths = volume_path_problems(ctx.root, ctx.runtime, volumes_of(services))
    if bad_paths:
        return report.error(ctx, exit_codes.PREFLIGHT_FAILED, "unsafe volume path: " + "; ".join(bad_paths))

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
        # Docker Desktop and Colima run containers in a VM with fewer CPUs than the host; Compose rejects a
        # `cpus:` above what the engine has, so the engine's own count wins over the host's.
        cpus = getattr(args, "cpus", None) or detect_docker_cpus(runner) or float(os.cpu_count() or 0) or DEFAULT_CPUS
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
        os_name, _ = host.classify_os(host.Probe.from_system(root=ctx.root, runner=runner))
        return report.error(ctx, exit_codes.HOST_UNSUPPORTED, f"memory: {exc}; {host.memory_hint(os_name, exc.need_gib)}")
    except ValueError as exc:  # two owners for one volume (a template error)
        return report.error(ctx, exit_codes.MANIFEST_INVALID, str(exc))
    compose_text = json.dumps(compose, indent=2, ensure_ascii=False) + "\n"
    configs = config_files(host_ports, published)
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
        "stale_build_tags": stale_builds,
    }
    if stale_builds:
        sys.stderr.write(stale_build_warning(stale_builds))
    report.emit(ctx, "compose", data)
    return exit_codes.OK
