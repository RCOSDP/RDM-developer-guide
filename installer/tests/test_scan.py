"""Unit tests for grdm-dev scan (SPEC-03): staged gate, allow-list, scanner availability, --dynamic.

All scanners are faked through the injectable runner / which; Docker is never required.
"""
from __future__ import annotations

import datetime as _dt
import io
import json
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from grdm_dev import exit_codes, scan
from grdm_dev.context import Context

TODAY = _dt.date(2026, 11, 5)

TRIVY_HIGH = json.dumps({"Results": [{"Target": "grdm-dev/web:dev", "Vulnerabilities": [
    {"VulnerabilityID": "CVE-2021-3177", "Severity": "HIGH", "PkgName": "python", "InstalledVersion": "3.6.15",
     "Title": "ctypes buffer overflow"},
    {"VulnerabilityID": "CVE-2020-0001", "Severity": "LOW", "PkgName": "zlib", "InstalledVersion": "1.2", "Title": "low"},
]}]})
TRIVY_CRITICAL = json.dumps({"Results": [{"Target": ".", "Vulnerabilities": [
    {"VulnerabilityID": "CVE-2020-8265", "Severity": "CRITICAL", "PkgName": "node", "InstalledVersion": "12",
     "Title": "use after free"}]}]})
TRIVY_CLEAN = json.dumps({"Results": []})
SEMGREP_EMPTY = json.dumps({"results": [], "errors": []})
SEMGREP_WARNING = json.dumps({"results": [{"check_id": "python.lang.security.audit.x", "path": "a.py",
                                           "start": {"line": 3}, "extra": {"severity": "WARNING", "message": "m"}}]})
GITLEAKS_EMPTY = "[]"


def fake_runner(trivy_json=TRIVY_CLEAN, semgrep_json=SEMGREP_EMPTY, gitleaks_json=GITLEAKS_EMPTY,
                images="", compose_ps=None, zap_json=None, calls=None):
    """Return a runner that answers canned output per tool and records argv in `calls`."""
    def _run(argv):
        if calls is not None:
            calls.append(list(argv))
        tool = argv[0]
        if tool == "git":
            return 0, "abc1234\n"
        if tool == "trivy":
            if "--version" in argv:
                return 0, "Version: 0.68.0\n"
            if "cyclonedx" in argv:
                Path(argv[argv.index("--output") + 1]).write_text('{"bomFormat":"CycloneDX"}')
                return 0, ""
            return 0, trivy_json
        if tool == "semgrep":
            return (0, "1.140.0\n") if "--version" in argv else (0, semgrep_json)
        if tool == "gitleaks":
            if argv[1] == "version":
                return 0, "8.21.2\n"
            Path(argv[argv.index("--report-path") + 1]).write_text(gitleaks_json)
            return 0, ""
        if tool == "docker":
            if argv[1:3] == ["image", "ls"]:
                return 0, images
            if argv[1:3] == ["compose", "ps"] if len(argv) > 2 else False:
                return (0, compose_ps) if compose_ps is not None else (1, "")
            if argv[1] == "compose":
                return (0, compose_ps) if compose_ps is not None else (1, "")
            if argv[1] == "run":
                Path(argv[argv.index("-v") + 1].split(":")[0]) .joinpath(argv[argv.index("-J") + 1]).write_text(zap_json or '{"site":[]}')
                return 0, ""
        return 127, ""
    return _run


def all_tools(name):
    return True


class ScanTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "manifest").mkdir()
        (self.root / "manifest" / "upstreams.json").write_text("{}")
        self.ctx = Context(root=self.root, yes=True, json_output=True, stdin_is_tty=False)

    def tearDown(self):
        self.tmp.cleanup()

    def write_manifest(self, name, data):
        (self.root / "manifest" / name).write_text(json.dumps(data), encoding="utf-8")

    def write_compose(self, services=None, networks=None):
        services = services if services is not None else {
            "web": {"image": "grdm-dev/web", "user": "1000:1000", "cap_drop": ["ALL"], "ports": ["127.0.0.1:5000:5000"]}}
        doc = {"services": services, "networks": networks or {"grdm": {"internal": True}}}
        (self.root / "runtime").mkdir(exist_ok=True)
        (self.root / "runtime" / "docker-compose.yml").write_text(json.dumps(doc))

    def run_scan(self, runner, which=all_tools, **flags):
        args = Namespace(baseline=False, secrets=False, dynamic=False, milestone=None)
        for k, v in flags.items():
            setattr(args, k, v)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = scan.run(self.ctx, args, runner=runner, which=which, today=TODAY, prober=lambda url: (True, "200"))
        return code, json.loads(out.getvalue()), err.getvalue()

    def latest(self):
        return json.loads((self.root / "runtime" / "reports" / "scan_latest.json").read_text())


class StagedGateTests(ScanTestBase):
    def test_m1_report_only_passes_with_high_findings_and_creates_manifest_files(self):
        self.write_compose()
        code, data, _ = self.run_scan(fake_runner(trivy_json=TRIVY_HIGH, images="grdm-dev/web:dev\n"))
        self.assertEqual(code, exit_codes.OK)
        self.assertEqual(data["milestone"], "M1")
        self.assertEqual(data["gate"], "pass")
        self.assertEqual(data["findings_by_severity"]["high"], 1)
        self.assertEqual(data["baseline"], "pass")
        for name in ("allowlist.json", "allowlist.baseline.json", "milestone.json"):
            self.assertTrue((self.root / "manifest" / name).exists(), name)
        allow = json.loads((self.root / "manifest" / "allowlist.json").read_text())
        self.assertEqual(allow["entries"], [])
        self.assertEqual(allow["fields"], list(scan.ALLOWLIST_FIELDS))
        self.assertEqual(json.loads((self.root / "manifest" / "allowlist.baseline.json").read_text())["counts"], {"M1": 0})
        reports = list((self.root / "runtime" / "reports").glob("scan_*"))
        self.assertTrue(any(p.suffix == ".json" and p.stem != "scan_latest" for p in reports))
        self.assertTrue(any(p.suffix == ".toon" for p in reports))

    def test_m4_high_finding_fails_50(self):
        self.write_manifest("milestone.json", {"milestone": "M4", "gate": "fail-high"})
        code, data, err = self.run_scan(fake_runner(trivy_json=TRIVY_HIGH, images="grdm-dev/web:dev\n"))
        self.assertEqual(code, exit_codes.SCAN_GATE_FAILED)
        self.assertEqual(data["gate"], "fail")
        self.assertEqual(data["over_threshold"], 1)
        self.assertIn("exit 50", err)

    def test_m4_passes_when_high_is_allowlisted(self):
        self.write_manifest("milestone.json", {"milestone": "M4", "gate": "fail-high"})
        self.write_manifest("allowlist.json", {"entries": [{
            "cve": "CVE-2021-3177", "component": "python@3.6.15", "reason": "EOL interpreter, removed in M4 port",
            "owner": "AID", "expires": "2027-03-31", "added_at": "2026-11-05"}]})
        self.write_manifest("allowlist.baseline.json", {"counts": {"M1": 1}})
        code, data, _ = self.run_scan(fake_runner(trivy_json=TRIVY_HIGH, images="grdm-dev/web:dev\n"))
        self.assertEqual(code, exit_codes.OK)
        self.assertEqual(data["allowlisted"], 1)
        self.assertEqual(data["findings_by_severity"]["high"], 0)

    def test_m5_critical_fails_50_via_milestone_flag(self):
        code, data, _ = self.run_scan(fake_runner(trivy_json=TRIVY_CRITICAL), milestone="M5")
        self.assertEqual(code, exit_codes.SCAN_GATE_FAILED)
        self.assertEqual(data["milestone"], "M5")
        self.assertEqual(data["findings_by_severity"]["critical"], 1)

    def test_m2_count_grew_fails_50(self):
        self.write_manifest("milestone.json", {"milestone": "M2"})
        self.write_manifest("allowlist.json", {"entries": [{
            "cve": "CVE-2021-3177", "component": "python", "reason": "r", "owner": "AID",
            "expires": "2027-03-31", "added_at": "2026-11-05"}]})
        self.write_manifest("allowlist.baseline.json", {"counts": {"M1": 0}})
        code, data, _ = self.run_scan(fake_runner())
        self.assertEqual(code, exit_codes.SCAN_GATE_FAILED)
        self.assertTrue(any("grew" in r for r in data["gate_reasons"]))

    def test_baseline_violation_fails_even_at_m1(self):
        self.write_compose({"web": {"ports": ["0.0.0.0:5000:5000"], "privileged": True}})
        code, data, _ = self.run_scan(fake_runner(), baseline=True)
        self.assertEqual(code, exit_codes.SCAN_GATE_FAILED)
        ids = {f["id"] for f in data["findings"]}
        self.assertEqual(ids, {"BASE-PUBLISH", "BASE-USER", "BASE-CAPDROP", "BASE-PRIVILEGED"})
        self.assertEqual(data["parts"], ["baseline"])
        self.assertEqual(data["tools"], [])

    def test_forbidden_alias_is_a_baseline_finding(self):
        (self.root / "runtime").mkdir()
        (self.root / "runtime" / "docker-compose.yml").write_text("services:\n  web:\n    extra_hosts:\n      - 'x:192.168.168.167'\n")
        code, data, _ = self.run_scan(fake_runner(), baseline=True)
        self.assertEqual(code, exit_codes.SCAN_GATE_FAILED)
        self.assertIn("BASE-ALIAS", {f["id"] for f in data["findings"]})


class AllowlistTests(ScanTestBase):
    def test_expired_entry_becomes_finding_and_stops_suppressing(self):
        self.write_manifest("allowlist.json", {"entries": [{
            "cve": "CVE-2021-3177", "component": "python", "reason": "r", "owner": "AID",
            "expires": "2026-01-31", "added_at": "2025-11-05"}]})
        code, data, _ = self.run_scan(fake_runner(trivy_json=TRIVY_HIGH, images="grdm-dev/web:dev\n"))
        self.assertEqual(code, exit_codes.OK)  # M1 is report-only
        expired = [f for f in data["findings"] if f["id"] == "ALLOWLIST-EXPIRED"]
        self.assertEqual(len(expired), 1)
        self.assertEqual(expired[0]["tool"], "allowlist")
        self.assertEqual(data["allowlisted"], 0)
        self.assertEqual(data["findings_by_severity"]["high"], 1)

    def test_malformed_entry_fails_gate_at_m1(self):
        self.write_manifest("allowlist.json", {"entries": [{"cve": "CVE-1", "component": "x", "reason": "r"}]})
        code, data, _ = self.run_scan(fake_runner())
        self.assertEqual(code, exit_codes.SCAN_GATE_FAILED)
        f = [f for f in data["findings"] if f["id"] == "ALLOWLIST-MALFORMED"][0]
        self.assertIn("owner", f["title"])
        self.assertIn("expires", f["title"])

    def test_validate_allowlist_rejects_team_owner(self):
        active, findings = scan.validate_allowlist([{
            "cve": "CVE-1", "component": "x", "reason": "r", "owner": "team",
            "expires": "2027-01-01", "added_at": "2026-01-01"}], TODAY)
        self.assertEqual(active, [])
        self.assertEqual(findings[0]["id"], "ALLOWLIST-MALFORMED")


class ScannerAvailabilityTests(ScanTestBase):
    def test_missing_trivy_exits_51_and_names_it(self):
        code, data, err = self.run_scan(fake_runner(), which=lambda n: n != "trivy")
        self.assertEqual(code, exit_codes.SCANNER_UNAVAILABLE)
        self.assertIn("trivy", err)
        self.assertEqual(data["exit_code"], 51)
        self.assertEqual(data["tools"][0]["name"], "trivy")
        self.assertEqual(data["tools"][0]["version"], "missing")

    def test_missing_gitleaks_with_secrets_flag_exits_51(self):
        code, _, err = self.run_scan(fake_runner(), which=lambda n: n != "gitleaks", secrets=True)
        self.assertEqual(code, exit_codes.SCANNER_UNAVAILABLE)
        self.assertIn("gitleaks", err)

    def test_trivy_fs_used_when_no_images(self):
        calls = []
        code, data, _ = self.run_scan(fake_runner(calls=calls))
        self.assertEqual(code, exit_codes.OK)
        self.assertTrue(any(c[:2] == ["trivy", "fs"] for c in calls))
        self.assertTrue(any("sbom_repo_" in str(c) for c in calls))
        self.assertTrue(any("fs scan" in n for n in data["notes"]))

    def test_semgrep_warning_maps_to_medium(self):
        code, data, _ = self.run_scan(fake_runner(semgrep_json=SEMGREP_WARNING))
        self.assertEqual(code, exit_codes.OK)
        self.assertEqual(data["findings_by_severity"]["medium"], 1)


class DynamicTests(ScanTestBase):
    def test_dynamic_with_unhealthy_services_exits_52(self):
        self.write_compose()
        ps = json.dumps([{"Service": "web", "State": "running", "Health": "unhealthy"}])
        code, data, err = self.run_scan(fake_runner(compose_ps=ps), dynamic=True)
        self.assertEqual(code, exit_codes.SERVICES_UNHEALTHY)
        self.assertIn("exit 52", err)
        self.assertEqual(data["tools"][0]["result"], "services-unhealthy")
        self.assertTrue((self.root / "runtime" / "reports" / "scan_latest.json").exists())

    def test_full_scan_skips_dynamic_when_unhealthy(self):
        self.write_compose()
        code, data, _ = self.run_scan(fake_runner(compose_ps=None))
        self.assertEqual(code, exit_codes.OK)
        self.assertTrue(any("dynamic (ZAP) part skipped" in n for n in data["notes"]))

    def test_dynamic_targets_service_names_on_compose_network(self):
        self.write_compose({
            "web": {"user": "1", "cap_drop": ["ALL"], "ports": ["127.0.0.1:5000:5000"]},
            "admin": {"user": "1", "cap_drop": ["ALL"]},
            "postgres": {"user": "1", "cap_drop": ["ALL"]},
        }, networks={"grdm": {"name": "grdm", "internal": True}})
        ps = json.dumps([{"Service": s, "State": "running", "Health": "healthy"} for s in ("web", "admin", "postgres")])
        zap = json.dumps({"site": [{"alerts": [{"pluginid": "10038", "riskcode": "2", "alert": "CSP header missing",
                                                "instances": [{"uri": "http://web:5000/"}]}]}]})
        calls = []
        code, data, _ = self.run_scan(fake_runner(compose_ps=ps, zap_json=zap, calls=calls), dynamic=True)
        self.assertEqual(code, exit_codes.OK)
        runs = [c for c in calls if c[:2] == ["docker", "run"]]
        targets = sorted(c[c.index("-t") + 1] for c in runs)
        self.assertEqual(targets, ["http://admin:8001", "http://web:5000"])
        for c in runs:
            self.assertEqual(c[c.index("--network") + 1], "grdm")
            self.assertIn(scan.ZAP_IMAGE, c)
            self.assertNotIn("127.0.0.1", " ".join(c[c.index(scan.ZAP_IMAGE):]))
        self.assertEqual(data["findings_by_severity"]["medium"], 2)
        self.assertEqual(data["findings"][0]["tool"], "zap")


class SecretsHygieneTests(ScanTestBase):
    def test_gitleaks_values_never_reach_the_report_and_env_values_are_masked(self):
        (self.root / "runtime").mkdir()
        (self.root / "runtime" / ".env").write_text("POSTGRES_PASSWORD=sup3rs3cretvalue\nSHORT=ab\n")
        leak = json.dumps([{"RuleID": "generic-api-key", "File": "a.env", "StartLine": 2, "Secret": "sup3rs3cretvalue",
                            "Match": "KEY=sup3rs3cretvalue", "Description": "found sup3rs3cretvalue"}])
        code, data, _ = self.run_scan(fake_runner(gitleaks_json=leak), secrets=True)
        self.assertEqual(code, exit_codes.SCAN_GATE_FAILED)  # a secret in the repo is a baseline failure (§3.5)
        text = json.dumps(data) + (self.root / "runtime" / "reports" / "scan_latest.json").read_text()
        text += (self.root / "runtime" / "reports").joinpath(
            next(p.name for p in (self.root / "runtime" / "reports").glob("gitleaks_*.json"))).read_text()
        self.assertNotIn("sup3rs3cretvalue", text)
        self.assertEqual(data["findings"][0]["tool"], "gitleaks")
        self.assertEqual(data["findings"][0]["location"], "a.env:2")


class NormalizerTests(unittest.TestCase):
    def test_trivy_unknown_severity_maps_low_and_shape(self):
        f = scan.normalize_trivy({"Results": [{"Target": "t", "Vulnerabilities": [
            {"VulnerabilityID": "CVE-X", "Severity": "UNKNOWN", "PkgName": "p", "InstalledVersion": "1"}]}]}, "t")[0]
        self.assertEqual(set(f), {"tool", "id", "severity", "component", "location", "title"})
        self.assertEqual(f["severity"], "LOW")
        self.assertEqual(f["component"], "p@1")

    def test_zap_risk_mapping(self):
        f = scan.normalize_zap({"site": [{"alerts": [{"pluginid": "1", "riskcode": "3", "name": "x"}]}]}, "http://web:5000")[0]
        self.assertEqual(f["severity"], "HIGH")
        self.assertEqual(f["location"], "http://web:5000")


if __name__ == "__main__":
    unittest.main()
