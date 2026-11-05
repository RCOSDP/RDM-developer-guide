"""grdm-dev redteam preflight — isolation checks before an AI red-team run (SPEC-02 §3, SPEC-03 §6).

Checks, none of them an attack (review r1 finding 4: isolation is proven, never inferred):
  1. approval record: the newest `docs/demo/*_redteam_*.md` carries a header block with `approved_by`,
     `approved_on` (ISO date, not in the future, at most 30 days old), `scope` (the target container or
     service names) and `run_id`; every target of manifest/redteam-targets.json must be inside `scope`;
  2. `docker network inspect` shows `Internal: true` for the red-team network, and every container on it
     is a listed target or the attacker;
  3. the attacker container (manifest field `attacker`) is running and attached to exactly that network;
  4. a canary container listens on a separate, ordinary bridge network; a probe run from the canary's
     own network must reach it (control: otherwise the probe itself is broken and the result is
     "probe inconclusive" -> fail); the same probe run inside the attacker container must reach neither
     the canary nor an external address (1.1.1.1:443). Reaching either proves egress -> fail.

Exit 53 if any check fails or is inconclusive, 20 if the targets manifest is missing or malformed,
0 otherwise. External commands go through an injectable `runner(argv) -> (returncode, output)`. The
canary container and (if preflight created it) its network are removed before returning.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import subprocess
import sys
from pathlib import Path

from . import exit_codes, report
from .context import Context

REQUIRED_KEYS = ("project", "network", "targets", "attacker")
APPROVAL_FIELDS = ("approved_by", "approved_on", "scope", "run_id")
DEFAULT_CANARY = {"network": "grdm-redteam-canary", "image": "alpine:3.20", "port": 8080}
DEFAULT_EXTERNAL_PROBE = "1.1.1.1:443"
DEFAULT_APPROVAL_MAX_AGE_DAYS = 30
REACH_OK = "GRDM_REACH_OK"
REACH_FAIL = "GRDM_REACH_FAIL"
PROBE_NOTOOL = "GRDM_PROBE_NOTOOL"
_NAME_RE = r"[a-z0-9][a-zA-Z0-9_.-]*"


def register(subparsers) -> None:
    p = subparsers.add_parser("redteam", help="AI red-team helpers (preflight only; never runs attacks)")
    sub = p.add_subparsers(dest="redteam_command", metavar="<action>")
    pre = sub.add_parser("preflight", help="prove no egress from the attacker container, approval record, targets only; exit 53 on failure")
    pre.add_argument("--targets", help="path to the targets manifest (default: manifest/redteam-targets.json)")
    pre.add_argument("--approval", help="path to the approval record (default: newest docs/demo/*_redteam_*.md)")
    p.set_defaults(_module=sys.modules[__name__])


def default_runner(argv: list[str], timeout: int = 60) -> tuple[int, str]:
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        return 127, str(exc)
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


# --------------------------------------------------------------------------- manifest

def load_targets(path: Path) -> dict:
    """Parse and validate the targets manifest. Raises ValueError with a readable reason."""
    if not path.exists():
        raise ValueError(f"{path} not found")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be an object")
    for k in REQUIRED_KEYS:
        if k not in data:
            raise ValueError(f"{path}: missing key {k!r}")
    if not isinstance(data["targets"], list) or not data["targets"] or not all(isinstance(t, str) and t for t in data["targets"]):
        raise ValueError(f"{path}: 'targets' must be a non-empty list of names")
    for k in ("project", "network", "attacker"):
        if not isinstance(data[k], str) or not re.fullmatch(_NAME_RE, data[k]):
            raise ValueError(f"{path}: {k!r} must be a plain Docker name")
    canary = dict(DEFAULT_CANARY)
    if "canary" in data:
        if not isinstance(data["canary"], dict):
            raise ValueError(f"{path}: 'canary' must be an object")
        canary.update({k: v for k, v in data["canary"].items() if k in DEFAULT_CANARY})
    if not isinstance(canary["network"], str) or not re.fullmatch(_NAME_RE, canary["network"]) or canary["network"] == data["network"]:
        raise ValueError(f"{path}: canary.network must be a plain Docker name different from the red-team network")
    if not isinstance(canary["port"], int) or not 1 <= canary["port"] <= 65535:
        raise ValueError(f"{path}: canary.port must be a port number")
    if not isinstance(canary["image"], str) or not canary["image"]:
        raise ValueError(f"{path}: canary.image must be an image reference")
    data["canary"] = canary
    ext = data.get("external_probe", DEFAULT_EXTERNAL_PROBE)
    if not isinstance(ext, str) or not re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}:\d{1,5}", ext):
        raise ValueError(f"{path}: external_probe must be <ipv4>:<port>")
    data["external_probe"] = ext
    age = data.get("approval_max_age_days", DEFAULT_APPROVAL_MAX_AGE_DAYS)
    if not isinstance(age, int) or age < 1:
        raise ValueError(f"{path}: approval_max_age_days must be a positive integer")
    data["approval_max_age_days"] = age
    return data


def service_of(container_name: str, project: str) -> str:
    """Compose names containers `<project>-<service>-<n>` (or with `_` on old versions)."""
    m = re.fullmatch(rf"{re.escape(project)}[-_](.+?)[-_][0-9]+", container_name)
    return m.group(1) if m else container_name


# --------------------------------------------------------------------------- approval record

def find_approval(root: Path) -> Path | None:
    demo = root / "docs" / "demo"
    candidates = sorted(demo.glob("*_redteam_*.md")) if demo.is_dir() else []
    return candidates[-1] if candidates else None


def parse_approval(text: str) -> dict[str, str]:
    """Pull the header fields out of an approval record. Accepts `key: value`, `- key: value`, `**key**: value`
    and a `scope:` whose names are comma/space separated or listed on following `- name` lines."""
    out: dict[str, str] = {}
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        m = re.match(r"^\s*(?:[-*]\s+)?\**(?P<key>[a-z_]+)\**\s*:\s*(?P<val>.*?)\s*$", line, re.I)
        if not m:
            continue
        key = m.group("key").lower()
        if key not in APPROVAL_FIELDS or key in out:
            continue
        val = m.group("val").strip().strip("`")
        if key == "scope" and not val:
            items: list[str] = []
            for nxt in lines[idx + 1:]:
                lm = re.match(r"^\s*[-*]\s+`?([A-Za-z0-9_.-]+)`?\s*(?:\(.*\))?\s*$", nxt)
                if not lm:
                    break
                items.append(lm.group(1))
            val = " ".join(items)
        out[key] = val
    return out


def validate_approval(fields: dict[str, str], targets: list[str], project: str, today: _dt.date,
                      max_age_days: int) -> tuple[list[str], dict]:
    """Return (problems, summary). Empty problems means the record authorises exactly these targets."""
    problems: list[str] = []
    summary: dict = {k: fields.get(k, "") for k in APPROVAL_FIELDS}
    for k in APPROVAL_FIELDS:
        if not fields.get(k, "").strip():
            problems.append(f"missing {k}")
    if fields.get("approved_on", "").strip():
        try:
            approved = _dt.date.fromisoformat(fields["approved_on"].strip()[:10])
        except ValueError:
            approved = None
            problems.append("approved_on is not an ISO date")
        if approved is not None:
            if approved > today:
                problems.append(f"approved_on {approved.isoformat()} is in the future")
            elif (today - approved).days > max_age_days:
                problems.append(f"approved_on {approved.isoformat()} is older than {max_age_days} days; re-approve")
    scope = [s for s in re.split(r"[,\s]+", fields.get("scope", "")) if s]
    scope_services = {service_of(s, project) for s in scope} | set(scope)
    summary["scope"] = scope
    outside = [t for t in targets if t not in scope_services]
    if outside and "missing scope" not in problems:
        problems.append(f"target(s) outside the approved scope: {', '.join(outside)}")
    return problems, summary


# --------------------------------------------------------------------------- docker helpers

def _json_out(out: str):
    try:
        data = json.loads(out.strip() or "null")
    except json.JSONDecodeError:
        return None
    if isinstance(data, list):
        data = data[0] if data else None
    return data


def inspect_network(runner, network: str) -> tuple[dict | None, str]:
    rc, out = runner(["docker", "network", "inspect", network, "--format", "{{json .}}"])
    if rc != 0:
        return None, f"docker network inspect {network} failed: {out.strip()[-200:]}"
    data = _json_out(out)
    if not isinstance(data, dict):
        return None, f"network {network} not found or unreadable"
    return data, ""


def inspect_container(runner, name: str) -> tuple[dict | None, str]:
    rc, out = runner(["docker", "inspect", name, "--format", "{{json .}}"])
    if rc != 0:
        return None, f"docker inspect {name} failed: {out.strip()[-200:]}"
    data = _json_out(out)
    if not isinstance(data, dict):
        return None, f"container {name} not found or unreadable"
    return data, ""


def probe_script(host: str, port: int) -> str:
    """Shell that prints REACH_OK / REACH_FAIL / PROBE_NOTOOL for a TCP connect to host:port."""
    url = f"http://{host}:{port}/"
    return (
        f"if command -v nc >/dev/null 2>&1; then nc -z -w 3 {host} {port} >/dev/null 2>&1 && echo {REACH_OK} || echo {REACH_FAIL}; "
        f"elif command -v wget >/dev/null 2>&1; then wget -T 3 -q -O- {url} >/dev/null 2>&1 && echo {REACH_OK} || echo {REACH_FAIL}; "
        f"elif command -v curl >/dev/null 2>&1; then curl -s -m 3 -o /dev/null {url} >/dev/null 2>&1 && echo {REACH_OK} || echo {REACH_FAIL}; "
        f"elif command -v bash >/dev/null 2>&1; then bash -c 'exec 3<>/dev/tcp/{host}/{port}' >/dev/null 2>&1 && echo {REACH_OK} || echo {REACH_FAIL}; "
        f"else echo {PROBE_NOTOOL}; fi"
    )


def verdict(rc: int, out: str) -> tuple[str, str]:
    """Map probe output to 'reachable' | 'unreachable' | 'inconclusive' with a detail string."""
    if REACH_OK in out:
        return "reachable", "connect succeeded"
    if REACH_FAIL in out:
        return "unreachable", "connect failed"
    if PROBE_NOTOOL in out:
        return "inconclusive", "no nc/wget/curl/bash in the container; probe inconclusive"
    return "inconclusive", f"probe did not run (rc={rc}): {out.strip()[-160:]}; probe inconclusive"


class Canary:
    """A listener on an ordinary bridge network, used as a reachable control target."""

    def __init__(self, runner, cfg: dict, run_id: str):
        self.runner = runner
        self.network = cfg["network"]
        self.image = cfg["image"]
        self.port = int(cfg["port"])
        self.name = "grdm-redteam-canary-" + re.sub(r"[^A-Za-z0-9_.-]", "-", run_id or "preflight")[:40]
        self.created_network = False
        self.started = False
        self.ip = ""

    def start(self) -> str:
        """Return '' on success, else the reason the canary is unavailable."""
        rc, _ = self.runner(["docker", "network", "inspect", self.network, "--format", "{{.Name}}"])
        if rc != 0:
            rc, out = self.runner(["docker", "network", "create", "--driver", "bridge", self.network])
            if rc != 0:
                return f"could not create canary network {self.network}: {out.strip()[-160:]}"
            self.created_network = True
        listener = (f"while true; do printf 'HTTP/1.0 200 OK\\r\\n\\r\\nGRDM_CANARY\\n' | nc -l -p {self.port}; done")
        rc, out = self.runner(["docker", "run", "-d", "--rm", "--name", self.name, "--network", self.network,
                               "--cap-drop", "ALL", "--read-only", self.image, "sh", "-c", listener])
        if rc != 0:
            return f"could not start canary container: {out.strip()[-160:]}"
        self.started = True
        info, err = inspect_container(self.runner, self.name)
        if info is None:
            return err
        nets = ((info.get("NetworkSettings") or {}).get("Networks") or {})
        ip = str((nets.get(self.network) or {}).get("IPAddress") or "")
        if not ip:
            return f"canary has no IP address on {self.network}"
        self.ip = ip
        return ""

    def control_probe(self) -> tuple[str, str]:
        rc, out = self.runner(["docker", "run", "--rm", "--network", self.network, self.image, "sh", "-c",
                               probe_script(self.ip, self.port)])
        return verdict(rc, out)

    def stop(self) -> None:
        if self.started:
            self.runner(["docker", "rm", "-f", self.name])
        if self.created_network:
            self.runner(["docker", "network", "rm", self.network])


# --------------------------------------------------------------------------- preflight

def preflight(ctx: Context, targets_path: Path, approval: Path | None, runner, today: _dt.date | None = None) -> tuple[dict, list[str]]:
    """Run every check. Returns (report data, list of failure reasons)."""
    today = today or _dt.date.today()
    failures: list[str] = []
    manifest = load_targets(targets_path)  # ValueError propagates: caller maps it to exit 20
    project, network, targets, attacker = manifest["project"], manifest["network"], manifest["targets"], manifest["attacker"]
    data: dict = {"project": project, "network": network, "attacker": attacker, "targets": targets, "checks": []}

    def check(name: str, ok: bool, detail: str) -> None:
        data["checks"].append({"check": name, "ok": ok, "detail": detail})
        if not ok:
            failures.append(f"{name}: {detail}")

    # 1. approval record (SPEC-03 §6 rule 3): owner, date, scope, run id
    approval = approval if approval is not None else find_approval(ctx.root)
    run_id = ""
    if approval and approval.is_file():
        fields = parse_approval(approval.read_text(encoding="utf-8", errors="replace"))
        problems, summary = validate_approval(fields, targets, project, today, manifest["approval_max_age_days"])
        rel = str(approval.relative_to(ctx.root)) if approval.is_relative_to(ctx.root) else str(approval)
        data["approval"] = {"path": rel, **summary}
        run_id = summary.get("run_id", "")
        check("approval_record", not problems, rel if not problems else f"{rel}: " + "; ".join(problems))
    else:
        data["approval"] = None
        check("approval_record", False, "no docs/demo/nn_redteam_<date>.md; no record, no run")

    # 2. network is internal and carries only targets + attacker
    net, err = inspect_network(runner, network)
    if net is None:
        check("network_internal", False, err)
        for name in ("targets_only", "attacker_network", "probe_control", "attacker_isolated"):
            check(name, False, "skipped: network unavailable")
        return data, failures
    check("network_internal", net.get("Internal") is True, f"Internal={net.get('Internal')}")
    attached = sorted(c.get("Name", "") for c in (net.get("Containers") or {}).values())
    unknown = [n for n in attached if n not in targets and n != attacker and service_of(n, project) not in targets]
    data["attached"] = attached
    data["unknown"] = unknown
    check("targets_only", not unknown, "all attached containers are listed" if not unknown else f"outside list: {', '.join(unknown)}")

    # 3. attacker: running, attached to exactly the red-team network
    info, err = inspect_container(runner, attacker)
    attacker_ok = False
    if info is None:
        check("attacker_network", False, err)
    else:
        running = bool(((info.get("State") or {}).get("Running")))
        nets = sorted(((info.get("NetworkSettings") or {}).get("Networks") or {}).keys())
        if not running:
            check("attacker_network", False, f"{attacker} is not running")
        elif nets != [network]:
            check("attacker_network", False, f"{attacker} is attached to {', '.join(nets) or 'no network'}; must be exactly {network}")
        else:
            attacker_ok = True
            check("attacker_network", True, f"{attacker} attached only to {network}")
    if not attacker_ok:
        check("probe_control", False, "skipped: attacker container unavailable")
        check("attacker_isolated", False, "skipped: attacker container unavailable; isolation not proven")
        return data, failures

    # 4. canary + probes: prove isolation, never infer it
    canary = Canary(runner, manifest["canary"], run_id)
    try:
        err = canary.start()
        if err:
            check("probe_control", False, err + "; probe inconclusive")
            check("attacker_isolated", False, "skipped: canary unavailable; isolation not proven")
            return data, failures
        data["canary"] = {"network": canary.network, "ip": canary.ip, "port": canary.port}
        v, detail = canary.control_probe()
        if v != "reachable":
            check("probe_control", False, f"canary {canary.ip}:{canary.port} not reached from its own network ({detail}); probe inconclusive")
        else:
            check("probe_control", True, f"canary {canary.ip}:{canary.port} reached from network {canary.network}")
        ext_host, ext_port = manifest["external_probe"].rsplit(":", 1)
        probes = []
        reachable: list[str] = []
        inconclusive: list[str] = []
        for label, host, port in (("canary", canary.ip, canary.port), ("external", ext_host, int(ext_port))):
            rc, out = runner(["docker", "exec", attacker, "sh", "-c", probe_script(host, port)])
            pv, pdetail = verdict(rc, out)
            probes.append({"probe": label, "destination": f"{host}:{port}", "verdict": pv, "detail": pdetail})
            if pv == "reachable":
                reachable.append(f"{label} {host}:{port}")
            elif pv == "inconclusive":
                inconclusive.append(f"{label}: {pdetail}")
        data["probes"] = probes
        if reachable:
            check("attacker_isolated", False, f"reachable from {attacker}: {', '.join(reachable)}; network is NOT isolated")
        elif inconclusive:
            check("attacker_isolated", False, "; ".join(inconclusive))
        elif v != "reachable":
            check("attacker_isolated", False, "probe inconclusive (control failed); isolation not proven")
        else:
            check("attacker_isolated", True, f"{attacker} reached neither the canary nor {manifest['external_probe']}")
    finally:
        canary.stop()
    return data, failures


def run(ctx: Context, args, runner=None, today: _dt.date | None = None) -> int:
    runner = runner or default_runner
    if getattr(args, "redteam_command", None) != "preflight":
        return report.error(ctx, exit_codes.USAGE, "usage: grdm-dev redteam preflight")
    targets_path = Path(args.targets) if getattr(args, "targets", None) else ctx.root / "manifest" / "redteam-targets.json"
    approval = Path(args.approval) if getattr(args, "approval", None) else None
    try:
        data, failures = preflight(ctx, targets_path, approval, runner, today)
    except ValueError as exc:
        return report.error(ctx, exit_codes.MANIFEST_INVALID, str(exc))
    data["result"] = "pass" if not failures else "fail"
    report.emit(ctx, "redteam_preflight", data)
    if failures:
        return report.error(ctx, exit_codes.REDTEAM_PREFLIGHT_FAILED, "; ".join(failures))
    return exit_codes.OK
