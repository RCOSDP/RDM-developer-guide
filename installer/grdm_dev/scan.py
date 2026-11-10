"""grdm-dev scan — the security gate of SPEC-03 (baseline controls, Trivy, gitleaks, Semgrep, ZAP,
allow-list diff, staged gate per ADR-03).

Usage: grdm-dev scan [--baseline] [--secrets] [--dynamic] [--milestone M1..M5]

Without part flags the whole gate runs (baseline, Trivy, Semgrep, gitleaks, and ZAP only when the
services are healthy). Each part flag restricts the run to that part. Exit codes (SPEC-03 §8):
0 pass, 50 gate failed, 51 scanner unavailable, 52 --dynamic requested while services unhealthy.

Every external program goes through an injectable `runner(argv) -> (returncode, stdout)` and tool
presence through an injectable `which(name) -> bool`, so unit tests feed canned scanner JSON and
never need Docker (SPEC-02 §10). Reports never contain secret values (SPEC-03 §3.1): gitleaks runs
with --redact, only rule id / file / line are kept, and every value of runtime/.env is masked.

Fail-closed rules (review r1 findings 2 and 5):
  * the baseline validator reads manifest/hardening.json: a service that runs as root or with a
    writable root filesystem passes only through a recorded exception whose review date has not
    passed, and the report lists each accepted exception with its reason and review date;
  * a scanner that exits nonzero, prints no JSON, reports its own errors, or cannot write an SBOM is
    `incomplete`; one incomplete scanner makes the whole run exit 51, never 0;
  * Trivy scans every image the rendered compose file references (project-built and infrastructure),
    every integration repository under runtime/src/, and this repository.

Recorded egress (SPEC-03 §3.2, review r2 finding R2-04): `compose render --egress` records the granted
services in runtime/.env as GRDM_EGRESS_SERVICES (and in the compose file's `x-grdm-dev.egress_services`).
A non-publishing service on `grdm-edge` passes the baseline only when that record names it (reported as
`accepted-egress`); an attachment the record does not name is BASE-NETWORK, and a record that names a
service which is not attached is BASE-EGRESS-STALE (re-render so record and reality agree).

Semgrep rule timeouts (SPEC-03 §4.2): at M1-M3 a timeout is a coverage warning on the tool row and the
gate judges the findings it has; at M4-M5 it makes the run incomplete (exit 51) like any scanner error.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from . import exit_codes, report
from .context import Context

Runner = Callable[[list[str]], tuple[int, str]]

SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")
ALLOWLIST_FIELDS = ("cve", "component", "reason", "owner", "expires", "added_at")
MILESTONES = ("M1", "M2", "M3", "M4", "M5")
# Milestone -> gate rule name (SPEC-03 §5.2 / ADR-03 §3). manifest/milestone.json may carry the
# same word in its "gate" field; the milestone number decides when the two disagree.
GATE_BY_MILESTONE = {
    "M1": "report-only",
    "M2": "count-not-growing",
    "M3": "count-not-growing",
    "M4": "fail-high",
    "M5": "zero-critical-high",
}
# ZAP targets by Compose service name and container port (SPEC-03 §4.3); only services that the
# rendered compose file defines are scanned.
ZAP_DEFAULT_TARGETS = {"web": 5000, "admin": 8001, "ember_osf_web": 4200}
ZAP_IMAGE = "ghcr.io/zaproxy/zaproxy:stable"
DEFAULT_NETWORK = "grdm"
EGRESS_ENV_KEY = "GRDM_EGRESS_SERVICES"
EGRESS_NONE = "none"
FORBIDDEN_ALIAS = "192.168.168.167"
IMAGE_PREFIX = "grdm-dev/"
# Semgrep rule packs of SPEC-03 §4.2; all four run in one invocation.
SEMGREP_PACKS = ("p/default", "p/python", "p/javascript", "p/docker-compose")
# Semgrep exit codes with --error: 0 clean, 1 findings present, anything else is a failed run.
SEMGREP_OK_CODES = (0, 1)
# zap-baseline.py: 0 clean, 1 warnings, 2 fails, 3+ error (and -I ignores warnings).
ZAP_OK_CODES = (0, 1, 2)
ENV_SECRET_MODE = 0o600
MIN_SECRET_LEN = 32
# Keys of runtime/.env that must hold a generated secret (SPEC-03 §3.1). Taken from compose.py's
# REQUIRED_SECRETS when available; the pattern below also catches keys added later.
_SECRET_KEY_PATTERN = re.compile(r"(PASSWORD|SECRET|_PASS$|_KEY$|SALT|TOKEN)", re.I)
FORBIDDEN_DEFAULTS = frozenset({"postgres", "changeme", "guest", "password", "secret", "osf", "admin", "root", ""})

DEFAULT_ALLOWLIST: dict[str, Any] = {
    "schema_version": 1,
    "note": "Accepted findings (SPEC-03 §5.1). Every entry needs cve, component, reason, owner, "
            "expires, added_at; optional severity. Only the owner approves additions.",
    "fields": list(ALLOWLIST_FIELDS),
    "entries": [],
}
DEFAULT_BASELINE: dict[str, Any] = {
    "schema_version": 1,
    "note": "Allow-list entry count at each milestone exit, owner-maintained (SPEC-03 §5.1 rule 5). "
            "The count for the current milestone is the ceiling; it must never grow.",
    "counts": {"M1": 0},
}
DEFAULT_MILESTONE: dict[str, Any] = {"milestone": "M1", "gate": "report-only"}


# --------------------------------------------------------------------------- CLI contract

def register(subparsers) -> None:
    p = subparsers.add_parser("scan", help="security gate: baseline, Trivy, gitleaks, Semgrep, ZAP (SPEC-03)")
    p.add_argument("--baseline", action="store_true", help="only re-check the baseline controls of runtime/docker-compose.yml")
    p.add_argument("--secrets", action="store_true", help="only run gitleaks over the repository")
    p.add_argument("--dynamic", action="store_true", help="only run the OWASP ZAP baseline (exit 52 if services are unhealthy)")
    p.add_argument("--milestone", choices=MILESTONES, help="override manifest/milestone.json for this run")
    p.set_defaults(_module=sys.modules[__name__])


def default_runner(cwd: Path) -> Runner:
    def _run(argv: list[str]) -> tuple[int, str]:
        try:
            proc = subprocess.run(argv, capture_output=True, text=True, cwd=str(cwd))
        except FileNotFoundError:
            return 127, ""
        return proc.returncode, proc.stdout
    return _run


def _exe(name: str) -> str:
    """Executable to run for `name`: PATH first, else the one next to the running interpreter (see default_which)."""
    found = shutil.which(name)
    if found:
        return found
    local = Path(sys.executable).parent / name
    return str(local) if local.exists() else name


def default_which(name: str) -> bool:
    """On PATH, or next to the running interpreter: the bootstrap installs semgrep into the same .venv as
    grdm-dev, and install.sh runs `.venv/bin/grdm-dev` without putting .venv/bin on PATH (real install run 17)."""
    if shutil.which(name) is not None:
        return True
    return (Path(sys.executable).parent / name).exists()


# --------------------------------------------------------------------------- manifest files

def _load_or_create(path: Path, default: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Read a JSON file; create it from `default` when missing. Returns (data, problems)."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(default, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return json.loads(json.dumps(default)), []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return dict(default), [f"{path.name} is not valid JSON: {exc}"]
    if not isinstance(data, dict):
        return dict(default), [f"{path.name} must be a JSON object"]
    return data, []


def _parse_date(value: Any) -> _dt.date | None:
    if not isinstance(value, str):
        return None
    try:
        return _dt.date.fromisoformat(value[:10])
    except ValueError:
        return None


def validate_allowlist(entries: Any, today: _dt.date) -> tuple[list[dict], list[dict]]:
    """Split allow-list entries into (active, findings). Malformed or expired entries become findings
    of tool `allowlist`; a malformed entry fails the gate at any milestone (SPEC-03 §5.1 rule 1)."""
    active: list[dict] = []
    findings: list[dict] = []
    if not isinstance(entries, list):
        return [], [_finding("allowlist", "ALLOWLIST-MALFORMED", "HIGH", "manifest/allowlist.json", "entries",
                             "entries must be a list")]
    for idx, e in enumerate(entries):
        loc = f"manifest/allowlist.json#entries[{idx}]"
        if not isinstance(e, dict):
            findings.append(_finding("allowlist", "ALLOWLIST-MALFORMED", "HIGH", "manifest/allowlist.json", loc,
                                     "entry is not an object"))
            continue
        missing = [f for f in ALLOWLIST_FIELDS if not isinstance(e.get(f), str) or not e.get(f).strip()]
        if missing:
            findings.append(_finding("allowlist", "ALLOWLIST-MALFORMED", "HIGH", str(e.get("component", "")), loc,
                                     f"missing or empty field(s): {', '.join(missing)}"))
            continue
        if str(e["owner"]).strip().lower() == "team":
            findings.append(_finding("allowlist", "ALLOWLIST-MALFORMED", "HIGH", e["component"], loc,
                                     "owner must be a person or a role, never 'team'"))
            continue
        expires = _parse_date(e["expires"])
        added = _parse_date(e["added_at"])
        if expires is None or added is None:
            findings.append(_finding("allowlist", "ALLOWLIST-MALFORMED", "HIGH", e["component"], loc,
                                     "expires and added_at must be ISO dates"))
            continue
        if expires < today:
            findings.append(_finding("allowlist", "ALLOWLIST-EXPIRED", "MEDIUM", e["component"], loc,
                                     f"{e['cve']} expired {expires.isoformat()}; the finding counts again"))
            continue
        active.append(e)
    return active, findings


def _entry_matches(entry: dict, finding: dict) -> bool:
    if entry["cve"] != finding["id"]:
        return False
    comp = entry.get("component", "*")
    if comp in ("", "*"):
        return True
    fcomp = finding.get("component", "") or ""
    return fcomp == comp or fcomp.startswith(comp.split("@")[0])


# --------------------------------------------------------------------------- findings

def _finding(tool: str, fid: str, severity: str, component: str, location: str, title: str) -> dict[str, Any]:
    sev = str(severity or "").upper()
    if sev == "UNKNOWN":
        sev = "LOW"
    if sev not in SEVERITIES:
        sev = "INFO"
    return {"tool": tool, "id": str(fid), "severity": sev, "component": str(component or ""),
            "location": str(location or ""), "title": str(title or "")[:200]}


def _json_or_empty(text: str) -> Any:
    try:
        return json.loads(text) if text and text.strip() else None
    except json.JSONDecodeError:
        return None


def normalize_trivy(data: Any, target: str) -> list[dict]:
    out: list[dict] = []
    if not isinstance(data, dict):
        return out
    for res in data.get("Results") or []:
        loc = res.get("Target") or target
        for v in res.get("Vulnerabilities") or []:
            comp = f"{v.get('PkgName', '')}@{v.get('InstalledVersion', '')}".rstrip("@")
            out.append(_finding("trivy", v.get("VulnerabilityID", ""), v.get("Severity", ""), comp, loc, v.get("Title", "")))
        for m in res.get("Misconfigurations") or []:
            out.append(_finding("trivy", m.get("ID", ""), m.get("Severity", ""), loc, loc, m.get("Title", "")))
    return out


_SEMGREP_SEVERITY = {"ERROR": "HIGH", "WARNING": "MEDIUM", "INFO": "LOW"}


def normalize_semgrep(data: Any) -> list[dict]:
    out: list[dict] = []
    if not isinstance(data, dict):
        return out
    for r in data.get("results") or []:
        extra = r.get("extra") or {}
        sev = _SEMGREP_SEVERITY.get(str(extra.get("severity", "")).upper(), "LOW")
        path = r.get("path", "")
        line = (r.get("start") or {}).get("line", "")
        out.append(_finding("semgrep", r.get("check_id", ""), sev, path, f"{path}:{line}", extra.get("message", "")))
    return out


def normalize_gitleaks(data: Any) -> list[dict]:
    """Keep only rule id, file, line, description; never Secret/Match/Line (SPEC-03 §3.1)."""
    out: list[dict] = []
    if not isinstance(data, list):
        return out
    for leak in data:
        if not isinstance(leak, dict):
            continue
        f = leak.get("File", "")
        out.append(_finding("gitleaks", leak.get("RuleID", "secret"), "HIGH", f,
                            f"{f}:{leak.get('StartLine', '')}", leak.get("Description", "secret detected")))
    return out


_ZAP_RISK = {"3": "HIGH", "2": "MEDIUM", "1": "LOW", "0": "INFO"}


def normalize_zap(data: Any, target: str) -> list[dict]:
    out: list[dict] = []
    if not isinstance(data, dict):
        return out
    for site in data.get("site") or []:
        for a in site.get("alerts") or []:
            inst = (a.get("instances") or [{}])[0]
            out.append(_finding("zap", f"ZAP-{a.get('pluginid', '')}", _ZAP_RISK.get(str(a.get("riskcode", "0")), "INFO"),
                                target, inst.get("uri", target), a.get("alert") or a.get("name", "")))
    return out


# --------------------------------------------------------------------------- baseline controls

def _load_compose(path: Path) -> tuple[dict | None, str]:
    text = path.read_text(encoding="utf-8")
    data = _json_or_empty(text)  # compose render writes JSON, which Compose accepts as YAML (SPEC-02 §2.2)
    return (data if isinstance(data, dict) else None), text


def _required_secret_keys() -> tuple[str, ...]:
    try:  # compose.py is owned by another task; its constant is the canonical list when present
        from . import compose as _compose  # type: ignore
        keys = getattr(_compose, "REQUIRED_SECRETS", ())
        return tuple(str(k) for k in keys)
    except Exception:
        return ()


def load_hardening_exceptions(path: Path) -> tuple[dict[str, dict], list[str]]:
    """manifest/hardening.json exceptions keyed by service (SPEC-03 §3.3). Returns (by_service, problems)."""
    if not path.exists():
        return {}, []
    data = _json_or_empty(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("exceptions"), list):
        return {}, [f"{path.name} is not a JSON object with an 'exceptions' list; no exception is honoured"]
    out: dict[str, dict] = {}
    problems: list[str] = []
    for idx, e in enumerate(data["exceptions"]):
        if not isinstance(e, dict) or not isinstance(e.get("service"), str):
            problems.append(f"{path.name}#exceptions[{idx}] has no service name; ignored")
            continue
        if not isinstance(e.get("controls"), list) or not e["controls"]:
            problems.append(f"{path.name}#exceptions[{idx}] ({e['service']}) lists no controls; ignored")
            continue
        if not str(e.get("reason") or "").strip() or _parse_date(e.get("review")) is None:
            problems.append(f"{path.name}#exceptions[{idx}] ({e['service']}) needs reason and an ISO review date; ignored")
            continue
        out[e["service"]] = e
    return out, problems


def _is_root_user(value: Any) -> bool:
    text = str(value if value is not None else "").strip()
    if not text:
        return True
    uid = text.split(":", 1)[0].strip()
    return uid in ("0", "root")


def _port_published_on_loopback(p: Any) -> tuple[bool, str]:
    if isinstance(p, dict):
        spec = f"{p.get('host_ip', '')}:{p.get('published', '')}:{p.get('target', '')}"
        return p.get("host_ip") == "127.0.0.1", spec
    spec = str(p)
    return spec.startswith("127.0.0.1:") and spec.count(":") == 2, spec


def _network_names(networks: Any) -> list[str]:
    if isinstance(networks, dict):
        return [str(k) for k in networks]
    if isinstance(networks, list):
        return [str(n) for n in networks]
    return []


def _internal_networks(doc: dict) -> tuple[set[str], set[str], bool]:
    """Return (internal network keys, all network keys, grdm_internal_ok)."""
    nets = doc.get("networks") or {}
    if not isinstance(nets, dict):
        return set(), set(), False
    internal: set[str] = set()
    grdm_ok = False
    for key, val in nets.items():
        val = val if isinstance(val, dict) else {}
        is_internal = val.get("internal") is True
        if is_internal:
            internal.add(str(key))
        name = str(val.get("name") or key)
        if (str(key) == DEFAULT_NETWORK or name == DEFAULT_NETWORK or name.endswith(f"_{DEFAULT_NETWORK}")) and is_internal:
            grdm_ok = True
    return internal, {str(k) for k in nets}, grdm_ok


def _env_values(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        values[k.strip()] = v.strip().strip("'\"")
    return values


def _split_services(raw: Any) -> list[str]:
    if isinstance(raw, list):
        parts = [str(x) for x in raw]
    elif isinstance(raw, str):
        parts = raw.split(",")
    else:
        parts = []
    out: list[str] = []
    for part in parts:
        name = part.strip()
        if name and name.lower() != EGRESS_NONE and name not in out:
            out.append(name)
    return out


def egress_grant(doc: dict | None, env_path: Path | None) -> tuple[list[str], str]:
    """The recorded egress grant (SPEC-03 §3.2) and where it came from.

    runtime/.env GRDM_EGRESS_SERVICES is the record `compose render --egress` writes and keeps; it wins.
    When the key is absent (older render, or no .env given) the compose file's own `x-grdm-dev.egress_services`
    is used. Returns (services, source) with source one of 'env', 'compose', 'none'.
    """
    if env_path is not None and env_path.exists():
        values = _env_values(env_path)
        if EGRESS_ENV_KEY in values:
            return _split_services(values[EGRESS_ENV_KEY]), "env"
    if isinstance(doc, dict):
        meta = doc.get("x-grdm-dev")
        if isinstance(meta, dict) and "egress_services" in meta:
            return _split_services(meta.get("egress_services")), "compose"
    return [], "none"


def check_env_file(env_path: Path, required_keys: tuple[str, ...] | None = None) -> list[dict]:
    """SPEC-03 §3.1: runtime/.env is mode 0600 and holds no default, empty, or short secret.
    Findings name keys only, never values."""
    loc = "runtime/.env"
    if not env_path.exists():
        return [_finding("baseline", "BASE-ENV-MISSING", "HIGH", "env", loc, "runtime/.env not found; run grdm-dev secrets init")]
    findings: list[dict] = []
    mode = env_path.stat().st_mode & 0o777
    if mode != ENV_SECRET_MODE:
        findings.append(_finding("baseline", "BASE-ENV-MODE", "HIGH", "env", loc, f"mode {mode:04o}; must be 0600"))
    values = _env_values(env_path)
    required = tuple(required_keys if required_keys is not None else _required_secret_keys())
    secret_keys = [k for k in values if _SECRET_KEY_PATTERN.search(k) or k in required]
    for k in required:
        if k not in values:
            findings.append(_finding("baseline", "BASE-ENV-DEFAULT", "HIGH", k, f"{loc}#{k}", f"{k} is missing"))
    for k in secret_keys:
        v = values[k]
        if v.lower() in FORBIDDEN_DEFAULTS:
            findings.append(_finding("baseline", "BASE-ENV-DEFAULT", "HIGH", k, f"{loc}#{k}", f"{k} holds an upstream default or empty value"))
        elif len(v) < MIN_SECRET_LEN:
            findings.append(_finding("baseline", "BASE-ENV-DEFAULT", "HIGH", k, f"{loc}#{k}", f"{k} is shorter than {MIN_SECRET_LEN} characters"))
    return findings


def check_baseline(compose_path: Path, hardening_path: Path | None = None, env_path: Path | None = None,
                   today: _dt.date | None = None, required_keys: tuple[str, ...] | None = None) -> tuple[list[dict], list[str], list[dict]]:
    """Re-check the SPEC-03 §3.1–§3.3 controls of a rendered compose file plus runtime/.env.

    Returns (findings, notes, accepted). `accepted` lists every hardening exception that was applied:
    {service, control, status: accepted-exception, reason, review}, and every recorded egress grant that
    was applied: {service, control: egress, status: accepted-egress, reason, network, source}. An exception
    whose review date has passed is not applied and becomes a BASE-EXCEPTION-EXPIRED finding (fail-closed).
    """
    today = today or _dt.date.today()
    if not compose_path.exists():
        return [], ["runtime/docker-compose.yml not found; baseline controls not checked (run compose render)"], []
    data, text = _load_compose(compose_path)
    findings: list[dict] = []
    notes: list[str] = []
    accepted: list[dict] = []
    loc = "runtime/docker-compose.yml"
    if FORBIDDEN_ALIAS in text:
        findings.append(_finding("baseline", "BASE-ALIAS", "HIGH", "compose", loc,
                                 f"loopback alias {FORBIDDEN_ALIAS} must not appear (ADR-02)"))
    if data is None:
        # Not JSON: best-effort text checks only, and the structural checks count as failed.
        for m in re.finditer(r'^\s*-\s*"?(?P<spec>[^"\s]+)"?\s*$', text, re.M):
            spec = m.group("spec")
            if re.match(r"^\d+:\d+", spec) or re.match(r"^0\.0\.0\.0:", spec):
                findings.append(_finding("baseline", "BASE-PUBLISH", "HIGH", "compose", loc,
                                         f"port {spec} is not published on 127.0.0.1"))
        if re.search(r"^\s*privileged:\s*true", text, re.M):
            findings.append(_finding("baseline", "BASE-PRIVILEGED", "CRITICAL", "compose", loc, "privileged: true is forbidden"))
        findings.append(_finding("baseline", "BASE-UNREADABLE", "HIGH", "compose", loc,
                                 "compose file is not the JSON that compose render writes; user/cap_drop/network checks impossible"))
        return findings, notes, accepted

    exceptions: dict[str, dict] = {}
    if hardening_path is not None:
        exceptions, problems = load_hardening_exceptions(hardening_path)
        notes.extend(problems)

    def exception_for(service: str, control: str) -> dict | None:
        e = exceptions.get(service)
        if not e or control not in [str(c) for c in e.get("controls", [])]:
            return None
        return e

    def relaxed(service: str, control: str, sloc: str) -> bool:
        """True when a valid exception covers (service, control); records it or its expiry."""
        e = exception_for(service, control)
        if e is None:
            return False
        review = _parse_date(e.get("review"))
        if review is None or review < today:
            findings.append(_finding("baseline", "BASE-EXCEPTION-EXPIRED", "HIGH", service, sloc,
                                     f"hardening exception for control '{control}' passed its review date {e.get('review')}"))
            return False
        accepted.append({"service": service, "control": control, "status": "accepted-exception",
                         "reason": str(e.get("reason", "")), "review": review.isoformat(),
                         "target": str(e.get("target", ""))})
        return True

    internal, all_nets, grdm_ok = _internal_networks(data)
    if not grdm_ok:
        findings.append(_finding("baseline", "BASE-NETWORK", "HIGH", "compose", f"{loc}#networks",
                                 f"no network '{DEFAULT_NETWORK}' with internal: true (SPEC-03 §3.2, ADR-02)"))

    # Recorded egress grant (SPEC-03 §3.2): a declared service may sit on the edge bridge without a port.
    granted, grant_source = egress_grant(data, env_path)
    grant_desc = f"runtime/.env {EGRESS_ENV_KEY}" if grant_source == "env" else f"{loc}#x-grdm-dev.egress_services"
    egress_used: set[str] = set()

    services = data.get("services") or {}
    for name, svc in services.items():
        if not isinstance(svc, dict):
            continue
        sloc = f"{loc}#services.{name}"
        ports = svc.get("ports") or []
        for p in ports:
            ok, spec = _port_published_on_loopback(p)
            if not ok:
                findings.append(_finding("baseline", "BASE-PUBLISH", "HIGH", name, f"{sloc}.ports",
                                         f"port {spec} is not published on 127.0.0.1"))
        if _is_root_user(svc.get("user")) and not relaxed(name, "user", sloc):
            shown = str(svc.get("user") or "").strip() or "(unset)"
            findings.append(_finding("baseline", "BASE-USER", "HIGH", name, sloc,
                                     f"user {shown} runs as root and no hardening exception covers it"))
        if svc.get("read_only") is not True and not relaxed(name, "read_only", sloc):
            findings.append(_finding("baseline", "BASE-READONLY", "MEDIUM", name, sloc,
                                     "read_only: true missing and no hardening exception covers it"))
        caps = [str(c).upper() for c in (svc.get("cap_drop") or [])]
        if "ALL" not in caps:
            findings.append(_finding("baseline", "BASE-CAPDROP", "MEDIUM", name, sloc, "cap_drop must contain ALL"))
        added = [str(c) for c in (svc.get("cap_add") or [])]
        if added:
            e = exception_for(name, "cap_add")
            allowed = {str(c).upper() for c in (e or {}).get("cap_add", [])}
            extra = [c for c in added if c.upper() not in allowed]
            if extra or not relaxed(name, "cap_add", sloc):
                findings.append(_finding("baseline", "BASE-CAPADD", "MEDIUM", name, sloc,
                                         f"cap_add {', '.join(added)} not covered by a hardening exception"))
        sec_opts = [str(o) for o in (svc.get("security_opt") or [])]
        if not any(o.startswith("no-new-privileges") and not o.endswith(":false") for o in sec_opts):
            findings.append(_finding("baseline", "BASE-NNP", "MEDIUM", name, sloc, "security_opt must contain no-new-privileges:true"))
        if svc.get("privileged") is True:
            findings.append(_finding("baseline", "BASE-PRIVILEGED", "CRITICAL", name, sloc, "privileged: true is forbidden"))
        missing_limits = [k for k in ("mem_limit", "pids_limit") if not svc.get(k)]
        if missing_limits:
            findings.append(_finding("baseline", "BASE-LIMITS", "MEDIUM", name, sloc,
                                     f"resource limit(s) missing: {', '.join(missing_limits)}"))
        attached = _network_names(svc.get("networks"))
        if not attached:
            findings.append(_finding("baseline", "BASE-NETWORK", "HIGH", name, f"{sloc}.networks",
                                     "service is on the default bridge, not on the internal network"))
        on_internal = any(n in internal for n in attached)
        for net in attached:
            if net not in all_nets:
                findings.append(_finding("baseline", "BASE-NETWORK", "HIGH", name, f"{sloc}.networks", f"network {net} is not defined"))
            elif net not in internal and not ports and on_internal:
                if name in granted:
                    egress_used.add(name)
                    accepted.append({"service": name, "control": "egress", "status": "accepted-egress",
                                     "reason": f"egress granted by {grant_desc} (SPEC-03 §3.2)",
                                     "network": net, "source": grant_source})
                else:
                    findings.append(_finding("baseline", "BASE-NETWORK", "HIGH", name, f"{sloc}.networks",
                                             f"attached to non-internal network {net} without publishing a port and "
                                             f"without a recorded egress grant ({EGRESS_ENV_KEY})"))
        if attached and not on_internal:
            findings.append(_finding("baseline", "BASE-NETWORK", "HIGH", name, f"{sloc}.networks",
                                     "service is not attached to any internal network"))
        if svc.get("network_mode"):
            findings.append(_finding("baseline", "BASE-NETWORK", "HIGH", name, sloc, f"network_mode {svc['network_mode']} is forbidden"))

    # A grant that names a service which is not actually on a non-internal network is stale: the record and
    # the rendered file disagree, so the report would claim egress that does not exist. Re-render to fix.
    for name in granted:
        if name in egress_used:
            continue
        svc = services.get(name) if isinstance(services, dict) else None
        attached = _network_names(svc.get("networks")) if isinstance(svc, dict) else []
        if isinstance(svc, dict) and (svc.get("ports") or []) and any(n in all_nets and n not in internal for n in attached):
            continue  # a publishing service is on the edge bridge anyway; the grant is redundant, not stale
        why = "is not a service of the rendered file" if svc is None else "is not attached to a non-internal network"
        findings.append(_finding("baseline", "BASE-EGRESS-STALE", "MEDIUM", name, f"{loc}#services.{name}.networks",
                                 f"egress grant in {grant_desc} names {name}, which {why}; re-run compose render"))

    if env_path is not None:
        findings.extend(check_env_file(env_path, required_keys))
    return findings, notes, accepted


# --------------------------------------------------------------------------- secrets masking

def _env_secrets(env_path: Path) -> list[str]:
    if not env_path.exists():
        return []
    vals: list[str] = []
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        v = line.split("=", 1)[1].strip().strip("'\"")
        if len(v) >= 8:
            vals.append(v)
    return vals


def mask_secrets(data: Any, secrets: list[str]) -> Any:
    if not secrets:
        return data
    if isinstance(data, str):
        for s in secrets:
            if s in data:
                data = data.replace(s, "***")
        return data
    if isinstance(data, list):
        return [mask_secrets(x, secrets) for x in data]
    if isinstance(data, dict):
        return {k: mask_secrets(v, secrets) for k, v in data.items()}
    return data


# --------------------------------------------------------------------------- scanners

def _save_raw(ctx: Context, name: str, text: str, secrets: list[str]) -> Path:
    """Save a scanner's raw output under runtime/reports/ with runtime/.env values masked."""
    ctx.reports_dir.mkdir(parents=True, exist_ok=True)
    path = ctx.reports_dir / name
    path.write_text(mask_secrets(text, secrets), encoding="utf-8")
    return path


class ScannerMissing(Exception):
    def __init__(self, tool: str, detail: str = ""):
        super().__init__(tool)
        self.tool = tool
        self.detail = detail


def _require(which: Callable[[str], bool], tool: str) -> None:
    if not which(tool):
        raise ScannerMissing(tool, "not found on PATH")


def _tool_version(runner: Runner, argv: list[str]) -> str:
    rc, out = runner(argv)
    if rc != 0 or not out:
        return "unknown"
    m = re.search(r"\d+\.\d+(\.\d+)?", out)
    return m.group(0) if m else out.strip().splitlines()[0][:40]


def _tool(name: str, version: str, targets: int, problems: list[str]) -> dict:
    """Tool row of the report. Any problem makes the result `incomplete: ...`, never `ok` (SPEC-03 §8, 51)."""
    result = "ok" if not problems else "incomplete: " + "; ".join(problems)[:300]
    return {"name": name, "version": version, "result": result, "targets": targets, "problems": list(problems)}


def _safe_name(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", text)


def compose_images(compose_path: Path) -> list[str]:
    """Every image the rendered compose file references (project-built and infrastructure), in order."""
    if not compose_path.exists():
        return []
    data, _ = _load_compose(compose_path)
    if data is None:
        return []
    out: list[str] = []
    for svc in (data.get("services") or {}).values():
        img = (svc or {}).get("image") if isinstance(svc, dict) else None
        if isinstance(img, str) and img.strip() and img not in out:
            out.append(img.strip())
    return out


def integration_checkouts(ctx: Context) -> tuple[list[Path], list[str]]:
    """runtime/src/<repo>/ directories that build.py cloned (SPEC-03 §4.1: lockfiles live there), and notes
    about directories skipped: `_overlay/` (a copy of a base checkout plus overlay files, scanned through its
    parts) and the stale checkout of a component that is now `prebuilt_image` (nothing is built from it; its
    pom.xml made Trivy query Maven Central until a 429 in real install run 17)."""
    src = ctx.runtime / "src"
    if not src.is_dir():
        return [], []
    prebuilt_repos: set[str] = set()
    try:
        from . import manifest as _manifest
        for comp in _manifest.load(ctx).components:
            if comp.get("prebuilt_image") and comp.get("integration_repo"):
                prebuilt_repos.add(str(comp["integration_repo"]))
    except Exception:  # manifest unreadable: scan everything that is there
        prebuilt_repos = set()
    out: list[Path] = []
    notes: list[str] = []
    for p in sorted(src.iterdir()):
        if not p.is_dir() or p.name.startswith("."):
            continue
        if p.name.startswith("_"):
            notes.append(f"src/{p.name} skipped (assembled overlay context; its parts are scanned)")
            continue
        if p.name in prebuilt_repos:
            notes.append(f"src/{p.name} skipped (component uses prebuilt_image; the image itself is scanned)")
            continue
        out.append(p)
    return out, notes


def run_trivy(ctx: Context, runner: Runner, which: Callable[[str], bool], ts: str,
              secrets: list[str] | None = None) -> tuple[list[dict], dict, list[str]]:
    """Trivy over every compose image, every integration checkout, and this repository.

    A failed SBOM or scan of any target is a finding (SBOM-FAILED / SCAN-FAILED) and marks the tool
    incomplete; the remaining targets are still scanned so the report is as complete as possible.
    """
    secrets = secrets or []
    _require(which, "trivy")
    notes: list[str] = []
    findings: list[dict] = []
    problems: list[str] = []
    reports = ctx.reports_dir
    reports.mkdir(parents=True, exist_ok=True)

    images = compose_images(ctx.runtime / "docker-compose.yml")
    if not images and which("docker"):
        rc, out = runner(["docker", "image", "ls", "--format", "{{.Repository}}:{{.Tag}}"])
        if rc == 0:
            images = [l.strip() for l in out.splitlines() if l.strip().startswith(IMAGE_PREFIX) and not l.strip().endswith(":<none>")]
        if images:
            notes.append("runtime/docker-compose.yml not rendered; scanned the locally built grdm-dev/* images instead")
    if not images:
        notes.append("no compose file and no grdm-dev/* image; image scan skipped (SPEC-03 §4.1 M1 scope)")

    def scan_target(kind: str, target: str, label: str, scanners: str, extra: list[str] | None = None) -> None:
        safe = _safe_name(label)
        sbom = reports / f"sbom_{safe}_{ts}.json"
        # --offline-scan: never resolve pom.xml parents or dependencies from remote Maven repositories
        # (Maven Central answered 429 and blocked the host in real install run 17); lockfiles are enough.
        fs_opts = (["--offline-scan"] if kind == "fs" else []) + list(extra or [])
        rc, out = runner(["trivy", kind, "--quiet", *fs_opts, "--format", "cyclonedx", "--output", str(sbom), target])
        if rc != 0 or not sbom.exists():
            findings.append(_finding("trivy", "SBOM-FAILED", "HIGH", label, label, f"trivy {kind} SBOM failed (rc {rc})"))
            problems.append(f"sbom {label} rc {rc}")
        rc, out = runner(["trivy", kind, "--quiet", *fs_opts, "--format", "json", "--scanners", scanners, target])
        data = _json_or_empty(out)
        if rc != 0 or data is None:
            findings.append(_finding("trivy", "SCAN-FAILED", "HIGH", label, label,
                                     f"trivy {kind} scan failed (rc {rc}); database download or image access may have failed"))
            problems.append(f"scan {label} rc {rc}")
            return
        _save_raw(ctx, f"trivy_{safe}_{ts}.json", out, secrets)
        findings.extend(normalize_trivy(data, label))

    for img in images:
        scan_target("image", img, img, "vuln")
    checkouts, skipped = integration_checkouts(ctx)
    notes.extend(skipped)
    for d in checkouts:
        scan_target("fs", str(d), f"src/{d.name}", "vuln,misconfig,secret")
    if not checkouts:
        notes.append("no integration checkout under runtime/src/; lockfile scan covers this repository only")
    # The repository itself, without runtime/ (checkouts, reports and volumes live there and are scanned
    # or excluded above), the bootstrap .venv/ and the generated site/.
    scan_target("fs", ".", "repo", "vuln,misconfig", ["--skip-dirs", "runtime,.venv,site"])
    targets = len(images) + len(checkouts) + 1
    return findings, _tool("trivy", _tool_version(runner, ["trivy", "--version"]), targets, problems), notes


def run_semgrep(ctx: Context, runner: Runner, which: Callable[[str], bool], ts: str,
                secrets: list[str] | None = None, strict: bool = False) -> tuple[list[dict], dict]:
    """Semgrep with the four SPEC-03 §4.2 packs and --error: rc 1 means findings, rc 0 clean, any other
    rc or a nonempty `errors` array means the run was incomplete — except Semgrep rule timeouts at M1-M3,
    which are coverage warnings (SPEC-03 §4.2); at M4/M5 they are incomplete too."""
    _require(which, "semgrep")
    argv = [_exe("semgrep"), "scan"]
    for pack in SEMGREP_PACKS:
        argv += ["--config", pack]
    # --timeout 30 / --timeout-threshold 3: Semgrep's default 5 s per rule per file trips on large
    # checkouts while other containers load the CPU (real install run 20: 148 timeouts under a cold
    # start); a file is dropped after three timeouts and reported below as a coverage warning.
    argv += ["--json", "--quiet", "--metrics=off", "--error", "--timeout", "30", "--timeout-threshold", "3", "."]
    rc, out = runner(argv)
    data = _json_or_empty(out)
    problems: list[str] = []
    if data is None:
        problems.append(f"no JSON output (rc {rc})")
        return [], _tool("semgrep", _tool_version(runner, [_exe("semgrep"), "--version"]), len(SEMGREP_PACKS), problems)
    _save_raw(ctx, f"semgrep_{ts}.json", out, secrets or [])
    if rc not in SEMGREP_OK_CODES:
        problems.append(f"semgrep exited {rc} (0 clean, 1 findings; other codes mean the run failed)")
    errors = data.get("errors") if isinstance(data, dict) else None
    timeouts: list[dict] = []
    if errors:
        # A rule timeout is a coverage gap on one file. At the reporting milestones (M1-M3, SPEC-03 §4.2)
        # it is recorded as a warning so the gate still judges the findings it has; at the strict
        # milestones (M4 fail-high, M5 zero) a rule that never finished cannot establish a clean result,
        # so it stays a problem and the run is incomplete (exit 51) — PR #33 review r2 R2-02.
        timeouts = [e for e in errors if isinstance(e, dict) and str(e.get("type", "")).startswith("Timeout")]
        others = [e for e in errors if e not in timeouts]
        if others:
            msgs = [str((e or {}).get("message", e))[:80] for e in others[:3] if isinstance(e, (dict, str))]
            problems.append(f"semgrep reported {len(others)} error(s): " + " | ".join(msgs))
        if timeouts and strict:
            problems.append(f"semgrep: {len(timeouts)} rule timeout(s) left files unscanned; a strict milestone needs complete coverage (raise --timeout or scan on an idle host)")
    tool = _tool("semgrep", _tool_version(runner, [_exe("semgrep"), "--version"]), len(SEMGREP_PACKS), problems)
    if timeouts:
        files = sorted({str(e.get("path", "?")) for e in timeouts})
        tool["warnings"] = [f"{len(timeouts)} rule timeout(s) on {len(files)} file(s); coverage gap" + (" (incomplete at this milestone)" if strict else ", reported at M1-M3") + ": " + ", ".join(files[:5]) + (" ..." if len(files) > 5 else "")]
        if not problems:
            tool["result"] = f"ok ({len(timeouts)} rule timeouts, see warnings)"
    return normalize_semgrep(data), tool


def run_gitleaks(ctx: Context, runner: Runner, which: Callable[[str], bool], ts: str,
                 secrets: list[str] | None = None) -> tuple[list[dict], dict]:
    _require(which, "gitleaks")
    ctx.reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = ctx.reports_dir / f"gitleaks_{ts}.json"
    argv = ["gitleaks", "detect", "--source", ".", "--redact", "--report-format", "json", "--report-path", str(out_path),
            "--exit-code", "0"]
    if (ctx.root / ".gitleaks.toml").exists():
        argv[4:4] = ["--config", ".gitleaks.toml"]
    rc, out = runner(argv)
    problems: list[str] = []
    data = None
    if out_path.exists():
        data = _json_or_empty(out_path.read_text(encoding="utf-8"))
    if data is None:
        data = _json_or_empty(out)
    if rc != 0:  # --exit-code 0 makes leaks exit 0, so any other code is a failed run
        problems.append(f"gitleaks exited {rc}")
    if data is None:
        if rc == 0:
            data = []
        else:
            problems.append("no report written")
            data = []
    findings = mask_secrets(normalize_gitleaks(data), secrets or [])
    # Rewrite the saved report with only the normalized fields: never Secret / Match / Line.
    out_path.write_text(json.dumps(findings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return findings, _tool("gitleaks", _tool_version(runner, ["gitleaks", "version"]), 1, problems)


def _compose_services_and_network(compose_path: Path) -> tuple[list[str], str]:
    if not compose_path.exists():
        return list(ZAP_DEFAULT_TARGETS), DEFAULT_NETWORK
    data, _ = _load_compose(compose_path)
    if data is None:
        return list(ZAP_DEFAULT_TARGETS), DEFAULT_NETWORK
    services = list((data.get("services") or {}).keys())
    nets = data.get("networks") or {}
    network = DEFAULT_NETWORK
    for key, val in nets.items():
        network = (val or {}).get("name") if isinstance(val, dict) and (val or {}).get("name") else key
        break
    return services, network


def services_healthy(ctx: Context, runner: Runner, which: Callable[[str], bool], prober=None) -> bool:
    """All services healthy? Uses grdm_dev.health.check_services when the module exists (its `prober`
    is injectable so tests never open sockets); otherwise falls back to `docker compose ps`."""
    compose = ctx.runtime / "docker-compose.yml"
    if not compose.exists() or not which("docker"):
        return False
    try:  # health.py is owned by another task; use it when present, never require it
        from . import health as _health  # type: ignore
    except ImportError:
        _health = None
    if _health is not None and callable(getattr(_health, "check_services", None)):
        try:
            _, ok = _health.check_services(ctx, runner, prober or _health.default_prober)
            return bool(ok)
        except Exception as exc:  # a broken health probe is "not healthy", not a traceback
            sys.stderr.write(f"[grdm-dev] health check failed: {exc}\n")
            return False
    rc, out = runner(["docker", "compose", "-f", str(compose), "ps", "--format", "json"])
    if rc != 0 or not out.strip():
        return False
    rows: list[dict] = []
    data = _json_or_empty(out)
    if isinstance(data, list):
        rows = [r for r in data if isinstance(r, dict)]
    else:
        for line in out.splitlines():
            row = _json_or_empty(line)
            if isinstance(row, dict):
                rows.append(row)
    if not rows:
        return False
    for r in rows:
        if str(r.get("State", "")).lower() != "running":
            return False
        health = str(r.get("Health", "")).lower()
        if health and health != "healthy":
            return False
    return True


def run_zap(ctx: Context, runner: Runner, which: Callable[[str], bool], ts: str,
            secrets: list[str] | None = None) -> tuple[list[dict], dict, list[str]]:
    _require(which, "docker")
    services, network = _compose_services_and_network(ctx.runtime / "docker-compose.yml")
    targets = {s: p for s, p in ZAP_DEFAULT_TARGETS.items() if s in services}
    notes: list[str] = []
    if not targets:
        notes.append("no ZAP target service (web, admin, ember_osf_web) in the compose file; dynamic scan skipped")
        return [], {"name": "zap", "version": "stable", "result": "skipped", "targets": 0, "problems": []}, notes
    ctx.reports_dir.mkdir(parents=True, exist_ok=True)
    findings: list[dict] = []
    problems: list[str] = []
    for svc, port in targets.items():
        url = f"http://{svc}:{port}"  # service name, never 127.0.0.1 (SPEC-03 §4.3)
        out_name = f"zap_{svc}_{ts}.json"
        # ZAP writes as its own uid (1000, "zap"). On Linux a host directory owned by another uid is not writable
        # for it, so zap-baseline exited 0 without a report (DEMO-21 run 3, host uid 2001). Each target gets its
        # own work directory, writable by any uid: it sits inside runtime/ (0700), which no other host user can
        # enter, holds only this report, and is removed once the masked copy is saved in reports/.
        wrk = ctx.reports_dir / f"zap_wrk_{svc}_{ts}"
        wrk.mkdir(exist_ok=True)
        os.chmod(wrk, 0o777)  # nosemgrep: python.lang.security.audit.insecure-file-permissions.insecure-file-permissions -- per-scan ZAP work directory inside runtime/ (0700), holds only the report, removed in `finally`
        argv = ["docker", "run", "--rm", "--network", network, "-v", f"{wrk}:/zap/wrk:rw",
                ZAP_IMAGE, "zap-baseline.py", "-t", url, "-J", out_name, "-I"]
        try:
            rc, out = runner(argv)
            if rc == 127:
                raise ScannerMissing("docker", "docker not found")
            out_path = wrk / out_name
            data = _json_or_empty(out_path.read_text(encoding="utf-8")) if out_path.exists() else _json_or_empty(out)
        finally:
            shutil.rmtree(wrk, ignore_errors=True)
        if data is None:
            problems.append(f"no ZAP report for {url} (rc {rc}); image {ZAP_IMAGE} pull or the scan may have failed")
            continue
        if rc not in ZAP_OK_CODES:
            problems.append(f"zap-baseline exited {rc} for {url}")
        _save_raw(ctx, out_name, json.dumps(data, ensure_ascii=False, indent=2), secrets or [])
        findings.extend(normalize_zap(data, url))
    return findings, _tool("zap", "stable", len(targets), problems), notes


# --------------------------------------------------------------------------- gate

def gate_decision(milestone: str, findings: list[dict], allowlisted: list[dict], allow_entries: list[dict],
                  baseline_failed: bool, allowlist_invalid: bool, count: int, baseline_count: int | None,
                  manifest_problems: list[str] | None = None) -> dict[str, Any]:
    rule = GATE_BY_MILESTONE.get(milestone, "report-only")
    reasons: list[str] = []
    if baseline_failed:
        reasons.append("baseline control violated (SPEC-03 §3)")
    if allowlist_invalid:
        reasons.append("allow-list entry malformed (SPEC-03 §5.1 rule 1)")
    if manifest_problems:  # a malformed milestone/allow-list file never silently falls back to M1
        reasons.append("gate manifest unreadable: " + "; ".join(manifest_problems))
    open_high = [f for f in findings if f["severity"] in ("CRITICAL", "HIGH") and f["tool"] not in ("baseline", "gitleaks", "allowlist")]
    over = 0
    if rule in ("count-not-growing", "fail-high", "zero-critical-high") and baseline_count is not None and count > baseline_count:
        reasons.append(f"allow-list grew: {count} > baseline {baseline_count} (SPEC-03 §5.1 rule 5)")
    if rule in ("fail-high", "zero-critical-high"):
        over = len(open_high)
        if over:
            reasons.append(f"{over} CRITICAL/HIGH finding(s) not in the allow-list")
    if rule == "zero-critical-high":
        hi_entries = [e for e in allow_entries if str(e.get("severity", "")).upper() in ("CRITICAL", "HIGH")]
        hi_entries += [e for e in allowlisted if e["severity"] in ("CRITICAL", "HIGH")]
        if hi_entries:
            reasons.append(f"{len(hi_entries)} CRITICAL/HIGH allow-list entr(ies) at M5 (must be empty)")
    return {"rule": rule, "over_threshold": over if rule in ("fail-high", "zero-critical-high") else len(open_high),
            "pass": not reasons, "reasons": reasons}


# --------------------------------------------------------------------------- run

def run(ctx: Context, args, runner: Runner | None = None, which: Callable[[str], bool] | None = None,
        today: _dt.date | None = None, prober=None) -> int:
    runner = runner or default_runner(ctx.root)
    which = which or default_which
    today = today or _dt.date.today()
    ts = report.timestamp()
    secrets = _env_secrets(ctx.runtime / ".env")
    only = {k for k in ("baseline", "secrets", "dynamic") if getattr(args, k, False)}
    full = not only

    milestone_data, problems = _load_or_create(ctx.root / "manifest" / "milestone.json", DEFAULT_MILESTONE)
    allow_data, p2 = _load_or_create(ctx.root / "manifest" / "allowlist.json", DEFAULT_ALLOWLIST)
    base_data, p3 = _load_or_create(ctx.root / "manifest" / "allowlist.baseline.json", DEFAULT_BASELINE)
    problems += p2 + p3
    milestone = getattr(args, "milestone", None) or str(milestone_data.get("milestone", "M1"))
    if milestone not in MILESTONES:
        problems.append(f"unknown milestone {milestone!r} in manifest/milestone.json")
        milestone = "M1"

    findings: list[dict] = []
    tools: list[dict] = []
    notes: list[str] = list(problems)
    accepted: list[dict] = []
    baseline_result = "not-run"
    dynamic_unhealthy = False
    missing: ScannerMissing | None = None

    try:
        if full or "baseline" in only:
            compose_path = ctx.runtime / "docker-compose.yml"
            bfind, bnotes, accepted = check_baseline(compose_path, ctx.root / "manifest" / "hardening.json",
                                                     ctx.runtime / ".env", today)
            findings.extend(bfind)
            notes.extend(bnotes)
            baseline_result = "pass" if not bfind else "fail"
            if not compose_path.exists():
                baseline_result = "skipped"
        if full:
            tf, tt, tn = run_trivy(ctx, runner, which, ts, secrets)
            findings.extend(tf)
            tools.append(tt)
            notes.extend(tn)
            sf, st = run_semgrep(ctx, runner, which, ts, secrets, strict=GATE_BY_MILESTONE.get(milestone, "report-only") in ("fail-high", "zero-critical-high"))
            findings.extend(sf)
            tools.append(st)
        if full or "secrets" in only:
            gf, gt = run_gitleaks(ctx, runner, which, ts, secrets)
            findings.extend(gf)
            tools.append(gt)
        if full or "dynamic" in only:
            healthy = services_healthy(ctx, runner, which, prober)
            if healthy:
                zf, zt, zn = run_zap(ctx, runner, which, ts, secrets)
                findings.extend(zf)
                tools.append(zt)
                notes.extend(zn)
            elif "dynamic" in only:
                dynamic_unhealthy = True
                tools.append({"name": "zap", "version": "stable", "result": "services-unhealthy", "targets": 0})
            else:
                notes.append("services not healthy; dynamic (ZAP) part skipped (SPEC-03 §4.3)")
                tools.append({"name": "zap", "version": "stable", "result": "skipped", "targets": 0})
    except ScannerMissing as exc:
        missing = exc
        tools.append({"name": exc.tool, "version": "missing", "result": f"unavailable: {exc.detail}", "targets": 0})

    # Allow-list
    entries = allow_data.get("entries", [])
    active, allow_findings = validate_allowlist(entries, today)
    allowlist_invalid = any(f["id"] == "ALLOWLIST-MALFORMED" for f in allow_findings)
    findings.extend(allow_findings)
    open_findings: list[dict] = []
    allowlisted: list[dict] = []
    for f in findings:
        if f["tool"] in ("baseline", "gitleaks", "allowlist"):  # no allow-list for baseline controls (ADR-03 §3.2)
            open_findings.append(f)
        elif any(_entry_matches(e, f) for e in active):
            allowlisted.append(f)
        else:
            open_findings.append(f)
    counts = base_data.get("counts") if isinstance(base_data.get("counts"), dict) else {}
    baseline_count: int | None = None
    for m in reversed(MILESTONES[: MILESTONES.index(milestone) + 1]):
        if isinstance(counts.get(m), int):
            baseline_count = counts[m]
            break
    count = len(entries) if isinstance(entries, list) else 0
    baseline_failed = any(f["tool"] in ("baseline", "gitleaks") for f in findings)
    gate = gate_decision(milestone, open_findings, allowlisted, active, baseline_failed, allowlist_invalid, count, baseline_count,
                         manifest_problems=problems)

    by_sev = {s.lower(): sum(1 for f in open_findings if f["severity"] == s) for s in SEVERITIES}
    incomplete = [t for t in tools if str(t.get("result", "")).startswith("incomplete")]
    if missing is not None or incomplete:
        code = exit_codes.SCANNER_UNAVAILABLE
    elif dynamic_unhealthy:
        code = exit_codes.SERVICES_UNHEALTHY
    elif not gate["pass"]:
        code = exit_codes.SCAN_GATE_FAILED
    else:
        code = exit_codes.OK

    rc, sha = runner(["git", "rev-parse", "--short", "HEAD"])
    data: dict[str, Any] = {
        "date": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "milestone": milestone,
        "commit": sha.strip() if rc == 0 else "unknown",
        "host": f"{platform.system().lower()}-{platform.machine().lower()}",
        "parts": sorted(only) if only else ["baseline", "trivy", "semgrep", "gitleaks", "zap"],
        "baseline": baseline_result,
        "baseline_exceptions": accepted,
        "tools": tools,
        "findings_total": len(open_findings),
        "findings_by_severity": by_sev,
        "allowlisted": len(allowlisted),
        "allowlist_count": count,
        "allowlist_baseline": baseline_count,
        "over_threshold": gate["over_threshold"],
        "gate_rule": gate["rule"],
        "gate": "pass" if gate["pass"] else "fail",
        "gate_reasons": gate["reasons"],
        "notes": notes,
        "findings": open_findings,
        "exit_code": code,
    }
    data = mask_secrets(data, secrets)
    report.emit(ctx, "scan", data)
    if code == exit_codes.SCANNER_UNAVAILABLE and missing is not None:
        return report.error(ctx, code, f"{missing.tool}: {missing.detail}")
    if code == exit_codes.SCANNER_UNAVAILABLE:
        return report.error(ctx, code, "; ".join(f"{t['name']}: {t['result']}" for t in incomplete))
    if code == exit_codes.SERVICES_UNHEALTHY:
        return report.error(ctx, code, "run grdm-dev up / grdm-dev health first")
    if code == exit_codes.SCAN_GATE_FAILED:
        return report.error(ctx, code, "; ".join(gate["reasons"]))
    return code
