"""grdm-dev health [--network] — service health and loopback-only check (SPEC-02 §3, SPEC-03 §3.2, ADR-02).

Reads runtime/docker-compose.yml (written as JSON by `compose render`) for the service names,
asks `docker compose ps --format json` for container state and health, and probes the browser-
facing HTTP endpoints on 127.0.0.1:<port> for the services of the SPEC-02 §4 ports table that the
Compose file defines. Any missing, stopped, unhealthy or unreachable service is exit 40.

--network lists the listening TCP sockets of the host (`lsof -nP -iTCP -sTCP:LISTEN` on macOS,
`ss -ltnp` on Linux) and fails with exit 40 when a Docker-owned socket (docker-proxy, com.docker)
is bound to 0.0.0.0, :: / * or any other non-loopback address.

Injection points for tests: `runner(argv) -> (rc, stdout)`, `prober(url) -> (ok, detail)`,
`system` ("Darwin" / "Linux").
"""
from __future__ import annotations

import json
import platform as _platform
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import exit_codes, report
from .context import Context

COMPOSE_PROJECT = "grdm-dev"
HTTP_SERVICES: tuple[str, ...] = ("web", "api", "admin", "wb", "mfr", "ember_osf_web", "fakecas")
DOCKER_PROCESS_MARKERS: tuple[str, ...] = ("docker-proxy", "docker-pr", "com.docker", "com.docke", "vpnkit")
HTTP_TIMEOUT = 3.0


def default_runner(argv: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(argv, capture_output=True, text=True)
    except OSError as exc:
        return 127, str(exc)
    return proc.returncode, proc.stdout


def default_prober(url: str) -> tuple[bool, str]:
    """HTTP GET; any response below 500 counts as reachable (login redirects are fine)."""
    try:
        with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) as resp:  # noqa: S310 - loopback only
            return resp.status < 500, f"HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        return exc.code < 500, f"HTTP {exc.code}"
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return False, str(getattr(exc, "reason", exc))


def compose_path(ctx: Context) -> Path:
    return ctx.runtime / "docker-compose.yml"


def compose_base(ctx: Context) -> list[str]:
    return ["docker", "compose", "-f", str(compose_path(ctx)), "--project-name", COMPOSE_PROJECT]


def load_compose(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_ps(output: str) -> dict[str, dict]:
    """`docker compose ps --format json` prints either a JSON array or one object per line."""
    text = output.strip()
    if not text:
        return {}
    items: list[dict] = []
    try:
        parsed = json.loads(text)
        items = parsed if isinstance(parsed, list) else [parsed]
    except ValueError:
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    items.append(json.loads(line))
                except ValueError:
                    continue
    by_service: dict[str, dict] = {}
    for it in items:
        name = it.get("Service") or it.get("service") or it.get("Name") or ""
        if name:
            by_service[name] = it
    return by_service


def host_port(service: str, compose: dict, env: dict[str, str]) -> int | None:
    """Host port from the Compose `ports` entry (127.0.0.1:host:container) or GRDM_PORT_<SERVICE>."""
    svc = compose.get("services", {}).get(service) or {}
    for entry in svc.get("ports", []) or []:
        if isinstance(entry, dict):
            published = entry.get("published")
            if published:
                try:
                    return int(str(published))
                except ValueError:
                    pass
            continue
        parts = str(entry).split(":")
        if len(parts) >= 2:
            try:
                return int(parts[-2])
            except ValueError:
                continue
    value = env.get(f"GRDM_PORT_{service.upper()}")
    if value and value.isdigit():
        return int(value)
    return None


def check_services(ctx: Context, runner, prober) -> tuple[list[dict], bool]:
    """One row per service of the Compose file; returns (rows, all_healthy)."""
    from .secrets import env_path, read_env

    compose = load_compose(compose_path(ctx))
    env = read_env(env_path(ctx))
    services = list((compose.get("services") or {}).keys())
    rc, out = runner(compose_base(ctx) + ["ps", "--all", "--format", "json"])
    ps = parse_ps(out) if rc == 0 else {}
    rows: list[dict] = []
    all_ok = rc == 0
    for name in services:
        info = ps.get(name, {})
        state = str(info.get("State") or info.get("state") or ("missing" if not info else "unknown")).lower()
        health = str(info.get("Health") or info.get("health") or "").lower()
        ok = state == "running" and health in ("", "healthy")
        url = ""
        http = ""
        if name in HTTP_SERVICES:
            port = host_port(name, compose, env)
            if port:
                url = f"http://127.0.0.1:{port}/"
                reachable, http = prober(url)
                ok = ok and reachable
        rows.append({"service": name, "state": state, "health": health or "n/a", "url": url, "http": http, "ok": ok})
        all_ok = all_ok and ok
    return rows, all_ok


def _addr_port(addr: str) -> tuple[str, str]:
    addr = addr.strip()
    if addr.startswith("["):  # [::1]:5000
        host, _, port = addr[1:].partition("]:")
        return host, port
    host, _, port = addr.rpartition(":")
    return host, port


def is_loopback(host: str) -> bool:
    host = host.strip("[]")
    return host.startswith("127.") or host in ("::1", "localhost", "::ffff:127.0.0.1")


def is_docker_process(name: str) -> bool:
    low = name.lower()
    return any(marker in low for marker in DOCKER_PROCESS_MARKERS)


def parse_lsof(output: str) -> list[dict]:
    rows = []
    for line in output.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 9 or "LISTEN" not in line:
            continue
        host, port = _addr_port(parts[8])
        rows.append({"process": parts[0], "address": host or "*", "port": port, "loopback": is_loopback(host)})
    return rows


def parse_ss(output: str) -> list[dict]:
    rows = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0] != "LISTEN":
            continue
        host, port = _addr_port(parts[3])
        proc = ""
        for p in parts[5:]:
            if p.startswith("users:(("):
                proc = p[len("users:((") :].split('"')[1] if '"' in p else p
        rows.append({"process": proc, "address": host or "*", "port": port, "loopback": is_loopback(host)})
    return rows


def listening_sockets(runner, system: str | None = None) -> tuple[list[dict], str]:
    system = system or _platform.system()
    if system == "Darwin":
        rc, out = runner(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"])
        # lsof exits 1 when nothing matched; that is still a valid (empty) answer
        return (parse_lsof(out) if rc in (0, 1) else []), ("" if rc in (0, 1) else f"lsof exited {rc}")
    rc, out = runner(["ss", "-ltnp"])
    return (parse_ss(out) if rc == 0 else []), ("" if rc == 0 else f"ss exited {rc}")


def check_network(runner, system: str | None = None) -> tuple[list[dict], list[dict], str]:
    """Return (docker sockets, offending non-loopback docker sockets, error)."""
    sockets, err = listening_sockets(runner, system)
    docker = [s for s in sockets if is_docker_process(s["process"])]
    bad = [s for s in docker if not s["loopback"]]
    return docker, bad, err


def wait_until_healthy(ctx: Context, timeout: float, runner=None, prober=None, sleep=time.sleep, interval: float = 5.0) -> tuple[list[dict], bool]:
    """Poll check_services until every service is healthy or the timeout passes."""
    runner = runner or default_runner
    prober = prober or default_prober
    deadline = time.monotonic() + timeout
    rows, ok = check_services(ctx, runner, prober)
    while not ok and time.monotonic() < deadline:
        sleep(interval)
        rows, ok = check_services(ctx, runner, prober)
    return rows, ok


def register(subparsers) -> None:
    p = subparsers.add_parser("health", help="check every service; --network also fails on non-loopback listeners (exit 40)")
    p.add_argument("--network", action="store_true", help="list listening sockets and require 127.0.0.1 only")
    p.set_defaults(_module=sys.modules[__name__])


def run(ctx: Context, args, runner=None, prober=None, system: str | None = None) -> int:
    runner = runner or default_runner
    prober = prober or default_prober
    path = compose_path(ctx)
    if not path.exists():
        return report.error(ctx, exit_codes.USAGE, f"{path} not found; run `grdm-dev compose render` first")
    try:
        rows, ok = check_services(ctx, runner, prober)
    except ValueError as exc:
        return report.error(ctx, exit_codes.HEALTH_FAILED, f"cannot parse {path}: {exc}")
    data: dict = {"services": rows, "healthy": ok}
    problems: list[str] = [f"{r['service']} ({r['state']}, {r['health']}{', ' + r['http'] if r['http'] else ''})" for r in rows if not r["ok"]]
    if getattr(args, "network", False):
        docker, bad, err = check_network(runner, system)
        data["sockets"] = docker
        data["loopback_only"] = not bad and not err
        if err:
            problems.append(err)
        for s in bad:
            problems.append(f"{s['process']} listens on {s['address']}:{s['port']} (not loopback)")
        ok = ok and not bad and not err
    report.emit(ctx, "health", data)
    if not ok:
        return report.error(ctx, exit_codes.HEALTH_FAILED, "; ".join(problems))
    return exit_codes.OK
