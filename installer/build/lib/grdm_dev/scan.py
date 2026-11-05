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
"""
from __future__ import annotations

import datetime as _dt
import json
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
FORBIDDEN_ALIAS = "192.168.168.167"
IMAGE_PREFIX = "grdm-dev/"

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


def default_which(name: str) -> bool:
    return shutil.which(name) is not None


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


def check_baseline(compose_path: Path) -> tuple[list[dict], list[str]]:
    """Re-check the SPEC-03 §3.2/§3.3 controls of a rendered compose file. Returns (findings, notes)."""
    if not compose_path.exists():
        return [], ["runtime/docker-compose.yml not found; baseline controls not checked (run compose render)"]
    data, text = _load_compose(compose_path)
    findings: list[dict] = []
    loc = "runtime/docker-compose.yml"
    if FORBIDDEN_ALIAS in text:
        findings.append(_finding("baseline", "BASE-ALIAS", "HIGH", "compose", loc,
                                 f"loopback alias {FORBIDDEN_ALIAS} must not appear (ADR-02)"))
    if data is None:
        # Not JSON: best-effort text checks only.
        for m in re.finditer(r'^\s*-\s*"?(?P<spec>[^"\s]+)"?\s*$', text, re.M):
            spec = m.group("spec")
            if re.match(r"^\d+:\d+", spec) or re.match(r"^0\.0\.0\.0:", spec):
                findings.append(_finding("baseline", "BASE-PUBLISH", "HIGH", "compose", loc,
                                         f"port {spec} is not published on 127.0.0.1"))
        if re.search(r"^\s*privileged:\s*true", text, re.M):
            findings.append(_finding("baseline", "BASE-PRIVILEGED", "CRITICAL", "compose", loc, "privileged: true is forbidden"))
        return findings, ["compose file is not JSON; user/cap_drop checks skipped"]
    services = data.get("services") or {}
    for name, svc in services.items():
        if not isinstance(svc, dict):
            continue
        for p in svc.get("ports") or []:
            spec = p if isinstance(p, str) else str((p or {}).get("host_ip", "")) + ":" + str((p or {}).get("published", ""))
            if isinstance(p, dict):
                ok = p.get("host_ip") == "127.0.0.1"
            else:
                ok = spec.startswith("127.0.0.1:")
            if not ok:
                findings.append(_finding("baseline", "BASE-PUBLISH", "HIGH", name, f"{loc}#services.{name}.ports",
                                         f"port {spec} is not published on 127.0.0.1"))
        if not str(svc.get("user") or "").strip():
            findings.append(_finding("baseline", "BASE-USER", "HIGH", name, f"{loc}#services.{name}", "no user: set (runs as root)"))
        caps = [str(c).upper() for c in (svc.get("cap_drop") or [])]
        if "ALL" not in caps:
            findings.append(_finding("baseline", "BASE-CAPDROP", "MEDIUM", name, f"{loc}#services.{name}", "cap_drop must contain ALL"))
        if svc.get("privileged") is True:
            findings.append(_finding("baseline", "BASE-PRIVILEGED", "CRITICAL", name, f"{loc}#services.{name}", "privileged: true is forbidden"))
    return findings, []


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


def run_trivy(ctx: Context, runner: Runner, which: Callable[[str], bool], ts: str,
              secrets: list[str] | None = None) -> tuple[list[dict], dict, list[str]]:
    secrets = secrets or []
    _require(which, "trivy")
    notes: list[str] = []
    findings: list[dict] = []
    images: list[str] = []
    if which("docker"):
        rc, out = runner(["docker", "image", "ls", "--format", "{{.Repository}}:{{.Tag}}"])
        if rc == 0:
            images = [l.strip() for l in out.splitlines() if l.strip().startswith(IMAGE_PREFIX) and not l.strip().endswith(":<none>")]
    reports = ctx.reports_dir
    reports.mkdir(parents=True, exist_ok=True)
    if images:
        for img in images:
            safe = re.sub(r"[^A-Za-z0-9_.-]", "_", img)
            sbom = reports / f"sbom_{safe}_{ts}.json"
            rc, _ = runner(["trivy", "image", "--quiet", "--format", "cyclonedx", "--output", str(sbom), img])
            if rc != 0:
                notes.append(f"trivy sbom failed for {img} (rc {rc})")
            rc, out = runner(["trivy", "image", "--quiet", "--format", "json", "--scanners", "vuln", img])
            data = _json_or_empty(out)
            if rc != 0 or data is None:
                raise ScannerMissing("trivy", f"image scan of {img} failed (rc {rc}); vulnerability database download may have failed")
            _save_raw(ctx, f"trivy_{safe}_{ts}.json", out, secrets)
            findings.extend(normalize_trivy(data, img))
    else:
        notes.append(f"no {IMAGE_PREFIX}* image found; trivy fs scan of the repository instead (SPEC-03 §4.1 M1 scope)")
        sbom = reports / f"sbom_repo_{ts}.json"
        rc, _ = runner(["trivy", "fs", "--quiet", "--format", "cyclonedx", "--output", str(sbom), "."])
        if rc != 0:
            notes.append(f"trivy sbom of the repository failed (rc {rc})")
        rc, out = runner(["trivy", "fs", "--quiet", "--format", "json", "--scanners", "vuln,misconfig", "."])
        data = _json_or_empty(out)
        if rc != 0 or data is None:
            raise ScannerMissing("trivy", f"fs scan failed (rc {rc}); vulnerability database download may have failed")
        _save_raw(ctx, f"trivy_repo_{ts}.json", out, secrets)
        findings.extend(normalize_trivy(data, "."))
    tool = {"name": "trivy", "version": _tool_version(runner, ["trivy", "--version"]), "result": "ok",
            "targets": len(images) if images else 1}
    return findings, tool, notes


def run_semgrep(ctx: Context, runner: Runner, which: Callable[[str], bool], ts: str,
                secrets: list[str] | None = None) -> tuple[list[dict], dict]:
    _require(which, "semgrep")
    rc, out = runner(["semgrep", "scan", "--config", "p/default", "--json", "--quiet", "."])
    data = _json_or_empty(out)
    if data is None:
        raise ScannerMissing("semgrep", f"no JSON output (rc {rc})")
    _save_raw(ctx, f"semgrep_{ts}.json", out, secrets or [])
    return normalize_semgrep(data), {"name": "semgrep", "version": _tool_version(runner, ["semgrep", "--version"]),
                                     "result": "ok", "targets": 1}


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
    data = None
    if out_path.exists():
        data = _json_or_empty(out_path.read_text(encoding="utf-8"))
    if data is None:
        data = _json_or_empty(out)
    if data is None:
        if rc != 0:
            raise ScannerMissing("gitleaks", f"rc {rc} and no report")
        data = []
    findings = mask_secrets(normalize_gitleaks(data), secrets or [])
    # Rewrite the saved report with only the normalized fields: never Secret / Match / Line.
    out_path.write_text(json.dumps(findings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return findings, {"name": "gitleaks", "version": _tool_version(runner, ["gitleaks", "version"]), "result": "ok", "targets": 1}


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
        return [], {"name": "zap", "version": "stable", "result": "skipped", "targets": 0}, notes
    ctx.reports_dir.mkdir(parents=True, exist_ok=True)
    findings: list[dict] = []
    for svc, port in targets.items():
        url = f"http://{svc}:{port}"  # service name, never 127.0.0.1 (SPEC-03 §4.3)
        out_name = f"zap_{svc}_{ts}.json"
        argv = ["docker", "run", "--rm", "--network", network, "-v", f"{ctx.reports_dir}:/zap/wrk:rw",
                ZAP_IMAGE, "zap-baseline.py", "-t", url, "-J", out_name, "-I"]
        rc, out = runner(argv)
        if rc == 127:
            raise ScannerMissing("docker", "docker not found")
        out_path = ctx.reports_dir / out_name
        data = _json_or_empty(out_path.read_text(encoding="utf-8")) if out_path.exists() else _json_or_empty(out)
        if data is None:
            raise ScannerMissing("zap", f"no ZAP report for {url} (rc {rc}); image {ZAP_IMAGE} pull may have failed")
        if out_path.exists():
            _save_raw(ctx, out_name, json.dumps(data, ensure_ascii=False, indent=2), secrets or [])
        findings.extend(normalize_zap(data, url))
    return findings, {"name": "zap", "version": "stable", "result": "ok", "targets": len(targets)}, notes


# --------------------------------------------------------------------------- gate

def gate_decision(milestone: str, findings: list[dict], allowlisted: list[dict], allow_entries: list[dict],
                  baseline_failed: bool, allowlist_invalid: bool, count: int, baseline_count: int | None) -> dict[str, Any]:
    rule = GATE_BY_MILESTONE.get(milestone, "report-only")
    reasons: list[str] = []
    if baseline_failed:
        reasons.append("baseline control violated (SPEC-03 §3)")
    if allowlist_invalid:
        reasons.append("allow-list entry malformed (SPEC-03 §5.1 rule 1)")
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
        problems.append(f"unknown milestone {milestone!r}; treating as M1")
        milestone = "M1"

    findings: list[dict] = []
    tools: list[dict] = []
    notes: list[str] = list(problems)
    baseline_result = "not-run"
    dynamic_unhealthy = False
    missing: ScannerMissing | None = None

    try:
        if full or "baseline" in only:
            bfind, bnotes = check_baseline(ctx.runtime / "docker-compose.yml")
            findings.extend(bfind)
            notes.extend(bnotes)
            baseline_result = "pass" if not bfind else "fail"
            if bnotes and not (ctx.runtime / "docker-compose.yml").exists():
                baseline_result = "skipped"
        if full:
            tf, tt, tn = run_trivy(ctx, runner, which, ts, secrets)
            findings.extend(tf)
            tools.append(tt)
            notes.extend(tn)
            sf, st = run_semgrep(ctx, runner, which, ts, secrets)
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
    gate = gate_decision(milestone, open_findings, allowlisted, active, baseline_failed, allowlist_invalid, count, baseline_count)

    by_sev = {s.lower(): sum(1 for f in open_findings if f["severity"] == s) for s in SEVERITIES}
    if missing is not None:
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
    if code == exit_codes.SERVICES_UNHEALTHY:
        return report.error(ctx, code, "run grdm-dev up / grdm-dev health first")
    if code == exit_codes.SCAN_GATE_FAILED:
        return report.error(ctx, code, "; ".join(gate["reasons"]))
    return code
