"""Unit tests for grdm-dev scan (SPEC-03): staged gate, allow-list, baseline validator against the real
renderer and against synthetic violations, scanner robustness (incomplete -> 51), --dynamic.

All scanners are faked through the injectable runner / which; Docker is never required.
"""
from __future__ import annotations

import datetime as _dt
import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from grdm_dev import compose, exit_codes, scan
from grdm_dev.context import Context

import test_compose  # same directory; its make_root/render drive compose.py on the real manifest

TODAY = _dt.date(2026, 11, 5)
REPO_ROOT = Path(__file__).resolve().parents[2]

TRIVY_HIGH = json.dumps({"Results": [{"Target": "grdm-dev/web:dev", "Vulnerabilities": [
    {"VulnerabilityID": "CVE-2021-3177", "Severity": "HIGH", "PkgName": "python", "InstalledVersion": "3.6.15",
     "Status": "affected", "Title": "ctypes buffer overflow"},
    {"VulnerabilityID": "CVE-2020-0001", "Severity": "LOW", "PkgName": "zlib", "InstalledVersion": "1.2", "Title": "low"},
]}]})
TRIVY_CRITICAL = json.dumps({"Results": [{"Target": ".", "Vulnerabilities": [
    {"VulnerabilityID": "CVE-2020-8265", "Severity": "CRITICAL", "PkgName": "node", "InstalledVersion": "12",
     "Title": "use after free"}]}]})
TRIVY_CLEAN = json.dumps({"Results": []})
SEMGREP_EMPTY = json.dumps({"results": [], "errors": []})
SEMGREP_WARNING = json.dumps({"results": [{"check_id": "python.lang.security.audit.x", "path": "a.py",
                                           "start": {"line": 3}, "extra": {"severity": "WARNING", "message": "m"}}],
                              "errors": []})
SEMGREP_ERRORS = json.dumps({"errors": [{"message": "failed"}], "results": []})
GITLEAKS_EMPTY = "[]"


def fake_runner(trivy_json=TRIVY_CLEAN, semgrep_json=SEMGREP_EMPTY, gitleaks_json=GITLEAKS_EMPTY,
                images="", compose_ps=None, zap_json=None, calls=None, semgrep_rc=0, gitleaks_rc=0,
                sbom_rc=0, trivy_fail_target=None, zap_rc=0, zap_out=None, probe=None):
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
                if sbom_rc:
                    return sbom_rc, ""
                Path(argv[argv.index("--output") + 1]).write_text('{"bomFormat":"CycloneDX"}')
                return 0, ""
            if trivy_fail_target is not None and argv[-1] == trivy_fail_target:
                return 1, "FATAL: unable to find the specified image"
            return 0, trivy_json
        if tool == "semgrep":
            return (0, "1.140.0\n") if "--version" in argv else (semgrep_rc, semgrep_json)
        if tool == "gitleaks":
            if argv[1] == "version":
                return 0, "8.21.2\n"
            if gitleaks_rc:
                return gitleaks_rc, "config error"
            Path(argv[argv.index("--report-path") + 1]).write_text(gitleaks_json)
            return 0, ""
        if tool == "docker":
            if argv[1:3] == ["image", "ls"]:
                return 0, images
            if argv[1] == "compose":
                return (0, compose_ps) if compose_ps is not None else (1, "")
            if argv[1] == "run" and "python3" in argv:  # the redirect probe of zap_behind_sign_in
                return probe if probe is not None else (1, "")
            if argv[1] == "run" and zap_out is not None:  # zap-baseline.py ended without writing a report
                return zap_rc, zap_out
            if argv[1] == "run":
                Path(argv[argv.index("-v") + 1].split(":")[0]).joinpath(argv[argv.index("-J") + 1]).write_text(zap_json or '{"site":[]}')
                return zap_rc, ""
        return 127, ""
    return _run


def all_tools(name):
    return True


def hardened(image="grdm-dev/web:dev", ports=None, networks=None, **override):
    """A service that satisfies every SPEC-03 §3.3 control; `override` relaxes or breaks one."""
    svc = {"image": image, "user": "1000:1000", "read_only": True, "cap_drop": ["ALL"],
           "security_opt": ["no-new-privileges:true"], "mem_limit": "512m", "cpus": 1.0, "pids_limit": 256,
           "networks": networks or ["grdm"]}
    if ports:
        svc["ports"] = ports
    for k, v in override.items():
        if v is None:
            svc.pop(k, None)
        else:
            svc[k] = v
    return svc


NETWORKS = {"grdm": {"driver": "bridge", "internal": True, "name": "grdm-dev_grdm"},
            "grdm-edge": {"driver": "bridge", "name": "grdm-dev_grdm-edge"}}


class ScanTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "manifest").mkdir()
        (self.root / "manifest" / "upstreams.json").write_text("{}")
        self.ctx = Context(root=self.root, yes=True, json_output=True, stdin_is_tty=False)
        self.write_env()

    def tearDown(self):
        self.tmp.cleanup()

    def write_env(self, text=None, mode=0o600):
        (self.root / "runtime").mkdir(exist_ok=True)
        p = self.root / "runtime" / ".env"
        p.write_text(text if text is not None else test_compose.fake_secrets(), encoding="utf-8")
        os.chmod(p, mode)

    def write_manifest(self, name, data):
        (self.root / "manifest" / name).write_text(json.dumps(data), encoding="utf-8")

    def write_hardening(self, exceptions):
        self.write_manifest("hardening.json", {"schema_version": 1, "exceptions": exceptions})

    def write_compose(self, services=None, networks=None):
        services = services if services is not None else {"web": hardened(ports=["127.0.0.1:5000:5000"], networks=["grdm", "grdm-edge"])}
        doc = {"services": services, "networks": networks if networks is not None else NETWORKS}
        (self.root / "runtime").mkdir(exist_ok=True)
        os.chmod(self.root / "runtime", 0o700)  # nosemgrep: python.lang.security.audit.insecure-file-permissions.insecure-file-permissions -- test fixture: the private runtime/ that `secrets init` leaves
        (self.root / "runtime" / "docker-compose.yml").write_text(json.dumps(doc))

    def run_scan(self, runner, which=all_tools, **flags):
        args = Namespace(baseline=False, secrets=False, dynamic=False, milestone=None)
        for k, v in flags.items():
            setattr(args, k, v)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = scan.run(self.ctx, args, runner=runner, which=which, today=TODAY, prober=lambda url: (True, "200"))
        return code, json.loads(out.getvalue()), err.getvalue()

    def baseline_ids(self, **flags):
        code, data, err = self.run_scan(fake_runner(), baseline=True, **flags)
        return code, data, {f["id"] for f in data["findings"]}


class TrivyTimeoutTests(ScanTestBase):
    """--trivy-timeout: Trivy's own 5 minute per-call limit stops a very large image on a slow host (DEMO-22, exit 51)."""

    def _trivy_calls(self, **flags):
        self.write_compose()
        calls = []
        code, data, _ = self.run_scan(fake_runner(calls=calls), **flags)
        return code, [c for c in calls if c[0] == "trivy" and "--version" not in c]

    def test_without_the_flag_trivy_keeps_its_own_default(self):
        code, calls = self._trivy_calls()
        self.assertEqual(code, exit_codes.OK)
        self.assertTrue(calls)
        self.assertTrue(all("--timeout" not in c for c in calls))

    def test_the_flag_reaches_every_sbom_and_scan_call_once(self):
        code, calls = self._trivy_calls(trivy_timeout="45m")
        self.assertEqual(code, exit_codes.OK)
        self.assertTrue(len(calls) >= 4)  # an SBOM and a scan for the image and for the repository
        for c in calls:
            self.assertEqual(c.count("--timeout"), 1, c)
            self.assertEqual(c[c.index("--timeout") + 1], "45m")

    def test_only_a_bounded_whole_duration_is_accepted(self):
        for ok in ("30s", "30m", "1h", "24h", " 2h ", "1440m", "10000s", "86400s"):
            self.assertEqual(scan.trivy_duration(ok), ok.strip())
        for bad in ("", "0m", "-5m", "1.5h", "25h", "86401s", "1441m", "999999s", "1000000s", "30", "m", "30min", "1d", "9999h", "5m; rm"):
            with self.assertRaises(argparse.ArgumentTypeError, msg=bad):
                scan.trivy_duration(bad)


class StagedGateTests(ScanTestBase):
    def test_m1_report_only_passes_with_high_findings_and_creates_manifest_files(self):
        self.write_compose()
        code, data, _ = self.run_scan(fake_runner(trivy_json=TRIVY_HIGH))
        self.assertEqual(code, exit_codes.OK)
        self.assertEqual(data["milestone"], "M1")
        self.assertEqual(data["gate"], "pass")
        self.assertEqual(data["findings_by_severity"]["high"], 2)  # one image + one repo fs scan, same canned output
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
        self.assertTrue(all(t["result"] == "ok" for t in data["tools"] if t["name"] != "zap"), data["tools"])

    def test_m4_high_finding_fails_50(self):
        self.write_manifest("milestone.json", {"milestone": "M4", "gate": "fail-high"})
        code, data, err = self.run_scan(fake_runner(trivy_json=TRIVY_HIGH))
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
        code, data, _ = self.run_scan(fake_runner(trivy_json=TRIVY_HIGH))
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

    def _entries(self, n):
        return [{"cve": f"CVE-2026-{i:05d}", "component": f"pkg{i}", "reason": "r", "owner": "AID",
                 "expires": "2026-12-31", "added_at": "2026-11-05"} for i in range(n)]

    def test_m3_ceiling_is_the_m2_exit_count(self):
        # Owner decision of 2026-11-13: M2 closed with 58 entries; at M3 the ceiling is the M2 count, not M1's 0.
        self.write_manifest("milestone.json", {"milestone": "M3", "gate": "count-not-growing"})
        self.write_manifest("allowlist.baseline.json", {"counts": {"M1": 0, "M2": 58}})
        self.write_manifest("allowlist.json", {"entries": self._entries(58)})
        code, data, _ = self.run_scan(fake_runner())
        self.assertEqual(code, exit_codes.OK, data["gate_reasons"])
        self.assertEqual(data["milestone"], "M3")
        self.assertEqual(data["allowlist_baseline"], 58)
        self.assertFalse(any("grew" in r for r in data["gate_reasons"]))
        self.write_manifest("allowlist.json", {"entries": self._entries(59)})
        code, data, _ = self.run_scan(fake_runner())
        self.assertEqual(code, exit_codes.SCAN_GATE_FAILED)
        self.assertEqual(data["allowlist_baseline"], 58)
        self.assertIn("allow-list grew: 59 > baseline 58 (SPEC-03 §5.1 rule 5)", data["gate_reasons"])

    def test_repository_gate_manifest_holds_its_own_count(self):
        # The committed manifest/ must pass its own count rule: from M2 on, the allow-list size must not exceed
        # the count of the current (or latest earlier) milestone in allowlist.baseline.json (SPEC-03 §5.1 rule 5).
        manifest = REPO_ROOT / "manifest"
        milestone = json.loads((manifest / "milestone.json").read_text())["milestone"]
        if scan.GATE_BY_MILESTONE[milestone] == "report-only":
            self.skipTest(f"{milestone} is report-only; the count is not enforced")
        counts = json.loads((manifest / "allowlist.baseline.json").read_text())["counts"]
        entries = json.loads((manifest / "allowlist.json").read_text())["entries"]
        ceiling = next(counts[m] for m in reversed(scan.MILESTONES[: scan.MILESTONES.index(milestone) + 1]) if m in counts)
        self.assertLessEqual(len(entries), ceiling, (milestone, counts))

    def test_malformed_milestone_json_fails_closed_not_m1(self):
        (self.root / "manifest" / "milestone.json").write_text("{not json")
        code, data, _ = self.run_scan(fake_runner())
        self.assertEqual(code, exit_codes.SCAN_GATE_FAILED)
        self.assertTrue(any("milestone.json" in r for r in data["gate_reasons"]), data["gate_reasons"])

    def test_baseline_violation_fails_even_at_m1(self):
        self.write_compose({"web": {"ports": ["0.0.0.0:5000:5000"], "privileged": True}})
        code, data, ids = self.baseline_ids()
        self.assertEqual(code, exit_codes.SCAN_GATE_FAILED)
        self.assertEqual(ids, {"BASE-PUBLISH", "BASE-USER", "BASE-READONLY", "BASE-CAPDROP", "BASE-NNP",
                               "BASE-PRIVILEGED", "BASE-LIMITS", "BASE-NETWORK"})
        self.assertEqual(data["parts"], ["baseline"])
        self.assertEqual(data["tools"], [])

    def test_forbidden_alias_is_a_baseline_finding(self):
        (self.root / "runtime" / "docker-compose.yml").write_text("services:\n  web:\n    extra_hosts:\n      - 'x:192.168.168.167'\n")
        code, data, ids = self.baseline_ids()
        self.assertEqual(code, exit_codes.SCAN_GATE_FAILED)
        self.assertIn("BASE-ALIAS", ids)
        self.assertIn("BASE-UNREADABLE", ids)  # a non-JSON compose file never passes silently


class BaselineValidatorTests(ScanTestBase):
    """Finding 2: root detection, hardening exceptions, resource limits, networks, runtime/.env."""

    def test_real_renderer_output_passes_with_exceptions_recorded(self):
        root = test_compose.make_root()
        try:
            rc, _, err, _ = test_compose.render(root)
            self.assertEqual(rc, exit_codes.OK, err)
            findings, notes, accepted = scan.check_baseline(root / "runtime" / "docker-compose.yml",
                                                            REPO_ROOT / "manifest" / "hardening.json",
                                                            root / "runtime" / ".env", TODAY)
            self.assertEqual(findings, [], json.dumps(findings, indent=1))
            self.assertEqual(notes, [])
            by_service = {}
            for a in accepted:
                self.assertEqual(a["status"], "accepted-exception")
                self.assertTrue(a["reason"] and a["review"])
                by_service.setdefault(a["service"], set()).add(a["control"])
            # every root-running service of the core profile is covered by a recorded `user` exception
            # (elasticsearch left this list in real install run 8; cas left it with the native image, ADR-07)
            for svc in ("postgres", "rabbitmq"):  # mongo left with ADR-13
                self.assertIn("user", by_service[svc], svc)
            self.assertNotIn("cas", by_service)
            # and the full scan reports them under baseline_exceptions
            shutil.copytree(root / "runtime", self.root / "runtime", dirs_exist_ok=True)
            shutil.copy(REPO_ROOT / "manifest" / "hardening.json", self.root / "manifest" / "hardening.json")
            code, data, _ = self.run_scan(fake_runner(), baseline=True)
            self.assertEqual(code, exit_codes.OK)
            self.assertEqual(data["baseline"], "pass")
            self.assertEqual({(a["service"], a["control"]) for a in data["baseline_exceptions"]},
                             {(a["service"], a["control"]) for a in accepted})
        finally:
            shutil.rmtree(root, ignore_errors=True)

    # ---- recorded egress grant (SPEC-03 §3.2, review r2 finding R2-04)

    def render_and_check(self, egress=None, mutate=None):
        """Render the real core manifest, optionally mutate the JSON, and run check_baseline on it."""
        root = test_compose.make_root()
        try:
            rc, _, err, _ = test_compose.render(root, egress=egress)
            self.assertEqual(rc, exit_codes.OK, err)
            compose_path = root / "runtime" / "docker-compose.yml"
            if mutate is not None:
                doc = json.loads(compose_path.read_text(encoding="utf-8"))
                mutate(doc)
                compose_path.write_text(json.dumps(doc), encoding="utf-8")
            env_text = (root / "runtime" / ".env").read_text(encoding="utf-8")
            findings, notes, accepted = scan.check_baseline(compose_path, REPO_ROOT / "manifest" / "hardening.json",
                                                            root / "runtime" / ".env", TODAY)
            return findings, notes, accepted, env_text
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_rendered_egress_grant_is_accepted_not_a_network_finding(self):
        findings, notes, accepted, env_text = self.render_and_check(egress="worker")
        self.assertIn("GRDM_EGRESS_SERVICES=worker", env_text)  # the record check_baseline reads
        self.assertEqual([f for f in findings if f["id"] == "BASE-NETWORK"], [], json.dumps(findings, indent=1))
        self.assertEqual([f for f in findings if f["id"] == "BASE-EGRESS-STALE"], [])
        self.assertEqual(findings, [], json.dumps(findings, indent=1))
        egress = [a for a in accepted if a["status"] == "accepted-egress"]
        self.assertEqual(len(egress), 1, accepted)
        self.assertEqual(egress[0]["service"], "worker")
        self.assertEqual(egress[0]["control"], "egress")
        self.assertEqual(egress[0]["network"], "grdm-edge")
        self.assertEqual(egress[0]["source"], "env")
        self.assertIn("GRDM_EGRESS_SERVICES", egress[0]["reason"])
        # the other accepted rows are still the hardening exceptions of the plain render
        self.assertTrue(all(a["status"] == "accepted-exception" for a in accepted if a is not egress[0]))

    def test_undeclared_attachment_to_edge_is_base_network(self):
        def attach_worker(doc):
            doc["services"]["worker"]["networks"] = ["grdm", "grdm-edge"]
        findings, notes, accepted, env_text = self.render_and_check(egress=None, mutate=attach_worker)
        self.assertIn("GRDM_EGRESS_SERVICES=\n", env_text)  # rendered without a grant
        net = [f for f in findings if f["id"] == "BASE-NETWORK"]
        self.assertEqual(len(net), 1, json.dumps(findings, indent=1))
        self.assertEqual(net[0]["component"], "worker")
        self.assertIn("grdm-edge", net[0]["title"])
        self.assertIn("without a recorded egress grant", net[0]["title"])
        self.assertEqual([a for a in accepted if a["status"] == "accepted-egress"], [])

    def test_grant_naming_an_unattached_service_is_stale_warning(self):
        # grant recorded for worker, but worker is only on the internal network (someone edited the file)
        def detach_worker(doc):
            doc["services"]["worker"]["networks"] = ["grdm"]
        findings, notes, accepted, _ = self.render_and_check(egress="worker", mutate=detach_worker)
        stale = [f for f in findings if f["id"] == "BASE-EGRESS-STALE"]
        self.assertEqual(len(stale), 1, json.dumps(findings, indent=1))
        self.assertEqual(stale[0]["component"], "worker")
        self.assertEqual(stale[0]["severity"], "MEDIUM")
        self.assertIn("compose render", stale[0]["title"])
        self.assertEqual([f for f in findings if f["id"] == "BASE-NETWORK"], [])
        self.assertEqual([a for a in accepted if a["status"] == "accepted-egress"], [])
        # a stale grant still fails the baseline gate (fail-closed: record and reality must agree)
        self.write_compose({"api": hardened("grdm-dev/api:dev")})
        self.write_env(test_compose.fake_secrets() + "GRDM_EGRESS_SERVICES=api\n")
        code, data, ids = self.baseline_ids()
        self.assertEqual(ids, {"BASE-EGRESS-STALE"})
        self.assertEqual(code, exit_codes.SCAN_GATE_FAILED)
        self.assertEqual(data["baseline"], "fail")

    def test_grant_sources_env_wins_over_compose_and_publishing_service_grant_is_not_stale(self):
        edge = hardened("grdm-dev/api:dev", networks=["grdm", "grdm-edge"])
        # grant only in x-grdm-dev (no key in .env): accepted from the compose record
        self.write_compose({"api": edge})
        doc = json.loads((self.root / "runtime" / "docker-compose.yml").read_text())
        doc["x-grdm-dev"] = {"egress_services": ["api"]}
        (self.root / "runtime" / "docker-compose.yml").write_text(json.dumps(doc))
        code, data, ids = self.baseline_ids()
        self.assertEqual(ids, set())
        self.assertEqual([(a["service"], a["source"]) for a in data["baseline_exceptions"] if a["status"] == "accepted-egress"],
                         [("api", "compose")])
        # .env present and empty: it is the record, so the compose list alone does not grant anything
        self.write_env(test_compose.fake_secrets() + "GRDM_EGRESS_SERVICES=\n")
        self.assertEqual(self.baseline_ids()[2], {"BASE-NETWORK"})
        # .env grants a service that publishes a port: redundant, not stale, and no accepted-egress row
        self.write_compose({"web": hardened(ports=["127.0.0.1:5000:5000"], networks=["grdm", "grdm-edge"])})
        self.write_env(test_compose.fake_secrets() + "GRDM_EGRESS_SERVICES=web\n")
        code, data, ids = self.baseline_ids()
        self.assertEqual(ids, set())
        self.assertEqual([a for a in data["baseline_exceptions"] if a["status"] == "accepted-egress"], [])
        # `none` and an unknown service: none clears, unknown is stale
        self.write_env(test_compose.fake_secrets() + "GRDM_EGRESS_SERVICES=none\n")
        self.assertEqual(self.baseline_ids()[2], set())
        self.write_env(test_compose.fake_secrets() + "GRDM_EGRESS_SERVICES=ghost\n")
        code, data, ids = self.baseline_ids()
        self.assertEqual(ids, {"BASE-EGRESS-STALE"})
        self.assertIn("not a service", data["findings"][0]["title"])

    def test_root_user_forms_fail_without_exception(self):
        for user in ("0:0", "0", "root", "root:root", "", None):
            self.write_compose({"db": hardened("postgres:15", user=user)})
            code, data, ids = self.baseline_ids()
            self.assertEqual(code, exit_codes.SCAN_GATE_FAILED, user)
            self.assertEqual(ids, {"BASE-USER"}, user)
            self.assertEqual(data["findings"][0]["component"], "db")

    def test_root_user_with_valid_exception_is_accepted_and_reported(self):
        self.write_hardening([{"service": "db", "controls": ["user"], "reason": "entrypoint drops with gosu",
                               "review": "2027-01-31", "target": "M5"}])
        self.write_compose({"db": hardened("postgres:15", user=None)})
        code, data, ids = self.baseline_ids()
        self.assertEqual(code, exit_codes.OK, data["findings"])
        self.assertEqual(data["baseline_exceptions"], [{"service": "db", "control": "user", "status": "accepted-exception",
                                                        "reason": "entrypoint drops with gosu", "review": "2027-01-31",
                                                        "target": "M5"}])

    def test_exception_past_review_date_fails(self):
        self.write_hardening([{"service": "db", "controls": ["user"], "reason": "r", "review": "2026-11-04"}])
        self.write_compose({"db": hardened("postgres:15", user="0:0")})
        code, data, ids = self.baseline_ids()
        self.assertEqual(code, exit_codes.SCAN_GATE_FAILED)
        self.assertEqual(ids, {"BASE-EXCEPTION-EXPIRED", "BASE-USER"})  # expiry is reported and the root rule applies again
        self.assertEqual(data["baseline_exceptions"], [])

    def test_exception_for_another_control_does_not_cover_user(self):
        self.write_hardening([{"service": "db", "controls": ["read_only"], "reason": "r", "review": "2027-01-31"}])
        self.write_compose({"db": hardened("postgres:15", user="root", read_only=False)})
        code, data, ids = self.baseline_ids()
        self.assertEqual(ids, {"BASE-USER"})
        self.assertEqual([a["control"] for a in data["baseline_exceptions"]], ["read_only"])

    def test_malformed_hardening_entry_is_ignored_and_noted(self):
        self.write_hardening([{"service": "db", "controls": ["user"], "reason": "r"}])  # no review date
        self.write_compose({"db": hardened("postgres:15", user="0:0")})
        code, data, ids = self.baseline_ids()
        self.assertEqual(ids, {"BASE-USER"})
        self.assertTrue(any("review" in n for n in data["notes"]))

    def test_cap_add_requires_matching_exception(self):
        self.write_compose({"db": hardened("postgres:15", cap_add=["CHOWN"])})
        self.assertEqual(self.baseline_ids()[2], {"BASE-CAPADD"})
        self.write_hardening([{"service": "db", "controls": ["cap_add"], "cap_add": ["CHOWN"], "reason": "r", "review": "2027-01-31"}])
        self.assertEqual(self.baseline_ids()[2], set())
        self.write_compose({"db": hardened("postgres:15", cap_add=["CHOWN", "SYS_ADMIN"])})
        self.assertEqual(self.baseline_ids()[2], {"BASE-CAPADD"})

    def test_missing_limits_readonly_nnp_privileged(self):
        self.write_compose({"web": hardened(mem_limit=None, pids_limit=None)})
        self.assertEqual(self.baseline_ids()[2], {"BASE-LIMITS"})
        self.write_compose({"web": hardened(read_only=False)})
        self.assertEqual(self.baseline_ids()[2], {"BASE-READONLY"})
        self.write_compose({"web": hardened(security_opt=["no-new-privileges:false"])})
        self.assertEqual(self.baseline_ids()[2], {"BASE-NNP"})
        self.write_compose({"web": hardened(privileged=True)})
        self.assertEqual(self.baseline_ids()[2], {"BASE-PRIVILEGED"})

    def test_ports_must_be_loopback(self):
        for spec in ("0.0.0.0:5000:5000", "5000:5000", "192.168.1.10:5000:5000", {"host_ip": "0.0.0.0", "published": 5000, "target": 5000}):
            self.write_compose({"web": hardened(ports=[spec], networks=["grdm", "grdm-edge"])})
            self.assertEqual(self.baseline_ids()[2], {"BASE-PUBLISH"}, spec)
        self.write_compose({"web": hardened(ports=[{"host_ip": "127.0.0.1", "published": 5000, "target": 5000}], networks=["grdm", "grdm-edge"])})
        self.assertEqual(self.baseline_ids()[2], set())

    def test_network_shape(self):
        # no internal grdm network at all
        self.write_compose({"web": hardened()}, networks={"grdm": {"driver": "bridge"}})
        self.assertEqual(self.baseline_ids()[2], {"BASE-NETWORK"})
        # internal network under a project-prefixed name is accepted
        self.write_compose({"web": hardened()}, networks={"grdm": {"internal": True, "name": "grdm-dev_grdm"}})
        self.assertEqual(self.baseline_ids()[2], set())
        # publishing service on grdm + grdm-edge is the accepted shape
        self.write_compose({"web": hardened(ports=["127.0.0.1:5000:5000"], networks=["grdm", "grdm-edge"]), "api": hardened("grdm-dev/api:dev")})
        self.assertEqual(self.baseline_ids()[2], set())
        # a non-publishing service on the edge bridge without a recorded grant has a route out: finding
        self.write_compose({"api": hardened("grdm-dev/api:dev", networks=["grdm", "grdm-edge"])})
        self.assertEqual(self.baseline_ids()[2], {"BASE-NETWORK"})
        # ... and with the grant recorded in runtime/.env it is an accepted, reported egress (R2-04)
        self.write_env(test_compose.fake_secrets() + "GRDM_EGRESS_SERVICES=api\n")
        code, data, ids = self.baseline_ids()
        self.assertEqual(ids, set())
        self.assertEqual([a["service"] for a in data["baseline_exceptions"] if a["status"] == "accepted-egress"], ["api"])
        self.write_env()
        # a service on no network (default bridge), on an undefined network, or with network_mode
        self.write_compose({"api": hardened(networks=None) | {"networks": []}})
        self.assertEqual(self.baseline_ids()[2], {"BASE-NETWORK"})
        self.write_compose({"api": hardened(network_mode="host")})
        self.assertEqual(self.baseline_ids()[2], {"BASE-NETWORK"})

    def test_env_mode_and_default_values(self):
        self.write_compose()
        self.write_env(mode=0o644)
        code, data, ids = self.baseline_ids()
        self.assertEqual(ids, {"BASE-ENV-MODE"})
        self.assertIn("0644", data["findings"][0]["title"])
        self.write_env(test_compose.fake_secrets(POSTGRES_PASSWORD="postgres", DJANGO_SECRET_KEY="", MFR_SERVER_SECRET="tinyval"))
        code, data, ids = self.baseline_ids()
        self.assertEqual(ids, {"BASE-ENV-DEFAULT"})
        self.assertEqual(sorted(f["component"] for f in data["findings"]), ["DJANGO_SECRET_KEY", "MFR_SERVER_SECRET", "POSTGRES_PASSWORD"])
        self.assertNotIn("tinyval", json.dumps(data["findings"]))  # titles name keys, never values
        self.write_env(test_compose.fake_secrets() + "EXTRA_TOKEN=changeme\n")
        self.assertEqual({f["component"] for f in self.baseline_ids()[1]["findings"]}, {"EXTRA_TOKEN"})
        (self.root / "runtime" / ".env").unlink()
        self.assertEqual(self.baseline_ids()[2], {"BASE-ENV-MISSING"})

    def test_env_required_keys_follow_compose_module(self):
        self.write_compose()
        text = "".join(f"{k}={'y' * 40}\n" for k in compose.REQUIRED_SECRETS if k != "POSTGRES_PASSWORD")
        self.write_env(text)
        code, data, ids = self.baseline_ids()
        self.assertEqual(ids, {"BASE-ENV-DEFAULT"})
        self.assertEqual(data["findings"][0]["component"], "POSTGRES_PASSWORD")


class AllowlistTests(ScanTestBase):
    def test_expired_entry_becomes_finding_and_stops_suppressing(self):
        self.write_manifest("allowlist.json", {"entries": [{
            "cve": "CVE-2021-3177", "component": "python", "reason": "r", "owner": "AID",
            "expires": "2026-01-31", "added_at": "2025-11-05"}]})
        code, data, _ = self.run_scan(fake_runner(trivy_json=TRIVY_HIGH))
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

    # An entry scoped to one image (Debian 13 packages without a fix in the Python 3.13 WaterButler and
    # MFR images) must not hide the same CVE in another image, where a fixed version may exist, nor a
    # package the entry does not name, nor the same package once a fixed version appears (PR #45 r1 R1-01).
    SCOPED = {"cve": "CVE-2025-0001", "component": "util-linux@2.41-5", "image": "grdm-dev/waterbutler",
              "packages": ["util-linux@2.41-5", "libmount1@2.41-5"],
              "reason": "no fixed version in Debian 13", "owner": "AID", "expires": "2027-01-01",
              "added_at": "2026-11-11"}

    @staticmethod
    def trivy_finding(target="grdm-dev/waterbutler:3319c1067916 (debian 13.2)", pkg="util-linux",
                      version="2.41-5", status="affected", fixed="", cls="os-pkgs", cve="CVE-2025-0001"):
        vuln = {"VulnerabilityID": cve, "Severity": "HIGH", "PkgName": pkg, "InstalledVersion": version, "Title": "t"}
        if status is not None:
            vuln["Status"] = status
        if fixed:
            vuln["FixedVersion"] = fixed
        result = {"Target": target, "Vulnerabilities": [vuln]}
        if cls is not None:
            result["Class"] = cls
            result["Type"] = "debian" if cls == "os-pkgs" else "pip"
        return scan.normalize_trivy({"Results": [result]}, target)[0]

    def test_image_scoped_entry_matches_its_no_fix_packages(self):
        for pkg in ("util-linux", "libmount1"):
            self.assertTrue(scan._entry_matches(self.SCOPED, self.trivy_finding(pkg=pkg)), pkg)
        for status in ("will_not_fix", "fix_deferred", "end_of_life"):
            self.assertTrue(scan._entry_matches(self.SCOPED, self.trivy_finding(status=status)), status)
        self.assertTrue(scan._entry_matches(self.SCOPED, self.trivy_finding(target="grdm-dev/waterbutler@sha256:ab (debian 13.2)")))

    def test_image_scoped_entry_rejects_other_images(self):
        for target in ("postgres:9.6 (debian 9.13)", "grdm-dev/waterbutler-extra:1 (debian 13.2)",
                       "grdm-dev/waterbutlerx:1 (debian 13.2)", "grdm-dev/waterbutler (debian 13.2)"):
            self.assertFalse(scan._entry_matches(self.SCOPED, self.trivy_finding(target=target)), target)

    def test_image_scoped_entry_rejects_unrelated_and_prefix_packages(self):
        for pkg in ("unrelated-package", "util-linux-extra", "util", "libmount1-dev", "libmount"):
            self.assertFalse(scan._entry_matches(self.SCOPED, self.trivy_finding(pkg=pkg)), pkg)
        # the installed version is part of the identity: another build of the package is a new finding
        self.assertFalse(scan._entry_matches(self.SCOPED, self.trivy_finding(version="2.41-6")))

    def test_entry_stops_matching_once_a_fixed_version_exists(self):
        # the reviewer's reproduction: same image, same named package, a fix published later
        self.assertFalse(scan._entry_matches(self.SCOPED, self.trivy_finding(status="fixed", fixed="2.41-6")))
        self.assertFalse(scan._entry_matches(self.SCOPED, self.trivy_finding(status="affected", fixed="2.41-6")))
        self.assertFalse(scan._entry_matches(self.SCOPED, self.trivy_finding(status="fixed")))
        unscoped = {k: v for k, v in self.SCOPED.items() if k not in ("image", "packages")}
        self.assertTrue(scan._entry_matches(unscoped, self.trivy_finding()))
        self.assertFalse(scan._entry_matches(unscoped, self.trivy_finding(status="fixed", fixed="2.41-6")))

    def test_unknown_fix_status_or_class_stays_open(self):
        for status in (None, "", "unknown", "under_investigation"):
            self.assertFalse(scan._entry_matches(self.SCOPED, self.trivy_finding(status=status)), status)
        self.assertFalse(scan._entry_matches(self.SCOPED, self.trivy_finding(cls=None)))
        # a Trivy finding built without its recorded status (not from normalize_trivy) is unknown too
        bare = scan._finding("trivy", "CVE-2025-0001", "HIGH", "util-linux@2.41-5",
                             "grdm-dev/waterbutler:3319c1067916 (debian 13.2)", "t")
        self.assertFalse(scan._entry_matches(self.SCOPED, bare))

    def test_image_scoped_entry_never_matches_a_language_package(self):
        f = self.trivy_finding(target="usr/local/lib/python3.13/site-packages", cls="lang-pkgs")
        self.assertFalse(scan._entry_matches(self.SCOPED, f))
        f = self.trivy_finding(cls="lang-pkgs")  # even inside the named image's target
        self.assertFalse(scan._entry_matches(self.SCOPED, f))

    def test_unscoped_entry_compares_whole_package_names(self):
        entry = {"cve": "CVE-2025-0001", "component": "util-linux", "reason": "r", "owner": "AID",
                 "expires": "2027-01-01", "added_at": "2026-11-11"}
        self.assertTrue(scan._entry_matches(entry, self.trivy_finding(target="postgres:9.6 (debian 9.13)")))
        self.assertFalse(scan._entry_matches(entry, self.trivy_finding(pkg="util-linux-extra")))
        pinned = dict(entry, component="util-linux@2.41-5")
        self.assertTrue(scan._entry_matches(pinned, self.trivy_finding()))
        self.assertFalse(scan._entry_matches(pinned, self.trivy_finding(version="2.41-6")))

    def test_wildcard_component_and_image_without_packages_are_malformed(self):
        cases = [dict(self.SCOPED, component="*"), dict(self.SCOPED, component=""),
                 {k: v for k, v in self.SCOPED.items() if k != "packages"},
                 dict(self.SCOPED, packages=[]), dict(self.SCOPED, packages=["util-linux"]),
                 dict(self.SCOPED, packages=["util-linux@*"]), dict(self.SCOPED, packages=["*@1"]),
                 dict(self.SCOPED, packages="util-linux@2.41-5")]
        for bad in cases:
            active, findings = scan.validate_allowlist([bad], TODAY)
            self.assertEqual(active, [], bad)
            self.assertEqual(findings[0]["id"], "ALLOWLIST-MALFORMED", bad)

    def test_real_allowlist_has_no_wildcards_and_is_valid(self):
        data = json.loads((REPO_ROOT / "manifest" / "allowlist.json").read_text(encoding="utf-8"))
        active, findings = scan.validate_allowlist(data["entries"], _dt.date(2026, 11, 11))
        self.assertEqual(findings, [])
        self.assertEqual(len(active), len(data["entries"]))
        for e in data["entries"]:
            self.assertNotIn(e["component"], ("", "*"))
            if "image" in e:
                self.assertIn(e["component"], e["packages"])

    def test_image_scoped_entry_in_a_full_scan(self):
        trivy = json.dumps({"Results": [
            {"Target": "grdm-dev/waterbutler:3319c1067916 (debian 13.2)", "Class": "os-pkgs", "Type": "debian",
             "Vulnerabilities": [
                {"VulnerabilityID": "CVE-2025-0001", "Severity": "HIGH", "PkgName": "util-linux",
                 "InstalledVersion": "2.41-5", "Status": "affected", "Title": "t"},
                {"VulnerabilityID": "CVE-2025-0001", "Severity": "HIGH", "PkgName": "libmount1",
                 "InstalledVersion": "2.41-5", "Status": "fixed", "FixedVersion": "2.41-6", "Title": "fixable"},
                {"VulnerabilityID": "CVE-2025-0001", "Severity": "HIGH", "PkgName": "unrelated-package",
                 "InstalledVersion": "1", "Status": "affected", "Title": "unnamed"}]},
            {"Target": "postgres:9.6 (debian 9.13)", "Class": "os-pkgs", "Type": "debian", "Vulnerabilities": [
                {"VulnerabilityID": "CVE-2025-0001", "Severity": "HIGH", "PkgName": "util-linux",
                 "InstalledVersion": "2.29.2-1", "Status": "affected", "Title": "t"}]}]})
        self.write_manifest("allowlist.json", {"entries": [self.SCOPED]})
        code, data, _ = self.run_scan(fake_runner(trivy_json=trivy))
        self.assertEqual(code, exit_codes.OK)
        open_ = [f for f in data["findings"] if f["id"] == "CVE-2025-0001"]
        self.assertGreater(data["allowlisted"], 0)
        self.assertTrue(any(f["component"] == "libmount1@2.41-5" for f in open_))  # fixable stays open
        self.assertTrue(any(f["component"] == "unrelated-package@1" for f in open_))
        self.assertTrue(any(f["location"].startswith("postgres:") for f in open_))
        self.assertFalse(any(f["component"] == "util-linux@2.41-5" and f["location"].startswith("grdm-dev/")
                             for f in open_))
        # internal matching data never reaches the report
        self.assertTrue(all(set(f) == {"tool", "id", "severity", "component", "location", "title"}
                            for f in data["findings"]))

    def test_empty_image_is_malformed(self):
        for bad in ("", "  ", 3):
            active, findings = scan.validate_allowlist([dict(self.SCOPED, image=bad)], TODAY)
            self.assertEqual(active, [], bad)
            self.assertEqual(findings[0]["id"], "ALLOWLIST-MALFORMED", bad)
            self.assertIn("image", findings[0]["title"])


class ScannerRobustnessTests(ScanTestBase):
    """Finding 5: scanner errors never become `ok`; Trivy covers every image and lockfile tree."""

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

    def test_semgrep_errors_array_with_exit_2_is_incomplete_51_never_ok(self):
        calls = []
        code, data, err = self.run_scan(fake_runner(semgrep_json=SEMGREP_ERRORS, semgrep_rc=2, calls=calls))
        self.assertEqual(code, exit_codes.SCANNER_UNAVAILABLE)
        sem = [t for t in data["tools"] if t["name"] == "semgrep"][0]
        self.assertTrue(sem["result"].startswith("incomplete"), sem)
        self.assertIn("failed", sem["result"])
        self.assertIn("exited 2", sem["result"])
        self.assertIn("semgrep", err)
        self.assertNotEqual(data["exit_code"], 0)

    def test_semgrep_errors_array_with_exit_0_is_still_incomplete(self):
        code, data, _ = self.run_scan(fake_runner(semgrep_json=SEMGREP_ERRORS, semgrep_rc=0))
        self.assertEqual(code, exit_codes.SCANNER_UNAVAILABLE)

    def test_semgrep_rule_timeouts_are_warnings_not_failures(self):
        """Real install run 20: 148 per-file rule timeouts under load made the gate fail closed; a timeout is a
        coverage gap recorded on the tool row, other errors still make the run incomplete."""
        only_timeouts = json.dumps({"results": [], "errors": [
            {"code": 2, "level": "warn", "type": "Timeout", "rule_id": "python.lang.x", "message": "Timeout when running python.lang.x on a.py", "path": "a.py"},
            {"code": 2, "level": "warn", "type": "Timeout", "rule_id": "python.lang.y", "message": "Timeout when running python.lang.y on a.py", "path": "a.py"}]})
        code, data, _ = self.run_scan(fake_runner(semgrep_json=only_timeouts, semgrep_rc=0))
        self.assertEqual(code, exit_codes.OK)
        sem = [t for t in data["tools"] if t["name"] == "semgrep"][0]
        self.assertTrue(sem["result"].startswith("ok ("), sem)
        self.assertIn("2 rule timeout(s) on 1 file(s)", sem["warnings"][0])
        mixed = json.loads(only_timeouts); mixed["errors"].append({"code": 2, "level": "error", "type": "SemgrepError", "message": "boom", "path": "b.py"})
        code, data, _ = self.run_scan(fake_runner(semgrep_json=json.dumps(mixed), semgrep_rc=2))
        self.assertEqual(code, exit_codes.SCANNER_UNAVAILABLE)
        sem = [t for t in data["tools"] if t["name"] == "semgrep"][0]
        self.assertIn("1 error(s)", sem["result"])

    def test_semgrep_timeouts_are_incomplete_at_strict_milestones(self):
        """M4 (fail-high) and M5 (zero): a rule that never finished cannot prove a clean result → 51 (review r2 R2-02)."""
        only_timeouts = json.dumps({"results": [], "errors": [
            {"code": 2, "level": "warn", "type": "Timeout", "rule_id": "python.lang.x", "message": "Timeout", "path": "a.py"}]})
        for ms in ("M4", "M5"):
            code, data, _ = self.run_scan(fake_runner(semgrep_json=only_timeouts, semgrep_rc=0), milestone=ms)
            self.assertEqual(code, exit_codes.SCANNER_UNAVAILABLE, ms)
            sem = [t for t in data["tools"] if t["name"] == "semgrep"][0]
            self.assertIn("incomplete", sem["result"]); self.assertIn("timeout", sem["result"])
        for ms in ("M1", "M2", "M3"):
            code, _, _ = self.run_scan(fake_runner(semgrep_json=only_timeouts, semgrep_rc=0), milestone=ms)
            self.assertEqual(code, exit_codes.OK, ms)

    def test_semgrep_argv_raises_the_timeout(self):
        calls = []
        self.run_scan(fake_runner(semgrep_json=SEMGREP_WARNING, semgrep_rc=1, calls=calls))
        sem = [c for c in calls if c and "semgrep" in str(c[0]) and "scan" in c][0]
        self.assertIn("--timeout", sem); self.assertEqual(sem[sem.index("--timeout") + 1], "30")
        self.assertIn("--timeout-threshold", sem)

    def test_semgrep_exit_1_means_findings_not_failure(self):
        code, data, _ = self.run_scan(fake_runner(semgrep_json=SEMGREP_WARNING, semgrep_rc=1))
        self.assertEqual(code, exit_codes.OK)
        self.assertEqual(data["findings_by_severity"]["medium"], 1)
        self.assertEqual([t["result"] for t in data["tools"] if t["name"] == "semgrep"], ["ok"])

    def test_semgrep_no_json_is_incomplete(self):
        code, data, _ = self.run_scan(fake_runner(semgrep_json="Traceback ...", semgrep_rc=2))
        self.assertEqual(code, exit_codes.SCANNER_UNAVAILABLE)
        self.assertIn("no JSON", [t for t in data["tools"] if t["name"] == "semgrep"][0]["result"])

    def test_semgrep_runs_all_four_spec_packs_with_error_flag(self):
        calls = []
        self.run_scan(fake_runner(calls=calls))
        argv = [c for c in calls if c[:2] == ["semgrep", "scan"]][0]
        packs = [argv[i + 1] for i, a in enumerate(argv) if a == "--config"]
        self.assertEqual(packs, ["p/default", "p/python", "p/javascript", "p/docker-compose"])
        self.assertEqual(len(packs), 4)
        self.assertIn("--error", argv)
        self.assertIn("--json", argv)

    def test_trivy_enumerates_every_compose_image_plus_checkouts_plus_repo(self):
        self.write_compose({
            "web": hardened("grdm-dev/web:abc123", ports=["127.0.0.1:5000:5000"], networks=["grdm", "grdm-edge"]),
            "api": hardened("grdm-dev/api:abc123"),
            "postgres": hardened("postgres:9.6"),
            "redis": hardened("redis:7-alpine"),
            "elasticsearch": hardened("elasticsearch:8"),
            "rabbitmq": hardened("rabbitmq:3-management"),
            "mongo": hardened("mongo:3.4"),
            "unoconv": hardened("centerforopenscience/unoconv"),
            "fakecas": hardened("grdm-dev/fakecas:abc123", ports=["127.0.0.1:8080:8080"], networks=["grdm", "grdm-edge"]),
            "dup": hardened("redis:7-alpine"),
        })
        for repo in ("osf.io", "waterbutler"):
            (self.root / "runtime" / "src" / repo).mkdir(parents=True)
        calls = []
        code, data, _ = self.run_scan(fake_runner(calls=calls))
        self.assertEqual(code, exit_codes.OK)
        image_scans = [c[-1] for c in calls if c[:2] == ["trivy", "image"] and "json" in c]
        self.assertEqual(image_scans, ["grdm-dev/web:abc123", "grdm-dev/api:abc123", "postgres:9.6", "redis:7-alpine",
                                       "elasticsearch:8", "rabbitmq:3-management", "mongo:3.4",
                                       "centerforopenscience/unoconv", "grdm-dev/fakecas:abc123"])
        fs_scans = [c[-1] for c in calls if c[:2] == ["trivy", "fs"] and "json" in c]
        self.assertEqual(fs_scans, [str(self.root / "runtime" / "src" / "osf.io"), str(self.root / "runtime" / "src" / "waterbutler"), "."])
        sboms = [c for c in calls if c[0] == "trivy" and "cyclonedx" in c]
        self.assertEqual(len(sboms), 9 + 2 + 1)
        self.assertFalse(any(c[:2] == ["docker", "image"] for c in calls))  # compose file, not `docker image ls`, is the source
        trivy = [t for t in data["tools"] if t["name"] == "trivy"][0]
        self.assertEqual(trivy["targets"], 12)
        self.assertEqual(trivy["result"], "ok")

    def test_trivy_fs_used_when_no_compose_and_no_images(self):
        calls = []
        code, data, _ = self.run_scan(fake_runner(calls=calls))
        self.assertEqual(code, exit_codes.OK)
        self.assertEqual([c[-1] for c in calls if c[:2] == ["trivy", "fs"] and "json" in c], ["."])
        self.assertFalse(any(c[:2] == ["trivy", "image"] for c in calls))
        self.assertTrue(any("image scan skipped" in n for n in data["notes"]))

    def test_trivy_sbom_failure_is_a_finding_and_51(self):
        self.write_compose()
        code, data, err = self.run_scan(fake_runner(sbom_rc=1))
        self.assertEqual(code, exit_codes.SCANNER_UNAVAILABLE)
        sbom = [f for f in data["findings"] if f["id"] == "SBOM-FAILED"]
        self.assertEqual(len(sbom), 2)  # one image + the repository
        self.assertEqual(sbom[0]["severity"], "HIGH")
        self.assertEqual(sbom[0]["tool"], "trivy")
        self.assertTrue([t for t in data["tools"] if t["name"] == "trivy"][0]["result"].startswith("incomplete"))
        self.assertFalse(any("sbom" in n.lower() for n in data["notes"]))  # not a note

    def test_trivy_one_failed_image_marks_incomplete_but_scans_the_rest(self):
        self.write_compose({"web": hardened("grdm-dev/web:dev", ports=["127.0.0.1:5000:5000"], networks=["grdm", "grdm-edge"]),
                            "postgres": hardened("postgres:9.6")})
        calls = []
        code, data, _ = self.run_scan(fake_runner(trivy_json=TRIVY_HIGH, trivy_fail_target="grdm-dev/web:dev", calls=calls))
        self.assertEqual(code, exit_codes.SCANNER_UNAVAILABLE)
        self.assertIn("postgres:9.6", [c[-1] for c in calls if c[:2] == ["trivy", "image"] and "json" in c])
        ids = [f["id"] for f in data["findings"]]
        self.assertIn("SCAN-FAILED", ids)
        self.assertIn("CVE-2021-3177", ids)  # the other targets were still scanned and reported

    def test_gitleaks_nonzero_exit_is_incomplete(self):
        code, data, _ = self.run_scan(fake_runner(gitleaks_rc=1), secrets=True)
        self.assertEqual(code, exit_codes.SCANNER_UNAVAILABLE)
        self.assertTrue(data["tools"][0]["result"].startswith("incomplete"))

    def test_zap_error_exit_is_incomplete(self):
        self.write_compose()
        ps = json.dumps([{"Service": "web", "State": "running", "Health": "healthy"}])
        code, data, _ = self.run_scan(fake_runner(compose_ps=ps, zap_rc=3), dynamic=True)
        self.assertEqual(code, exit_codes.SCANNER_UNAVAILABLE)
        self.assertIn("exited 3", data["tools"][0]["result"])

    SIGN_IN_OUT = ("Automation plan failures:\n\tJob spider failed to access URL http://web:5000 : "
                   "Connect to http://127.0.0.1:8081 failed: Connection refused\n")
    SIGN_IN_PROBE = (0, "302 http://127.0.0.1:8081/login?service=http%3A%2F%2F127.0.0.1%3A8000%2F\n")

    def write_osf_env(self, public_access="false", cas="http://127.0.0.1:8081"):
        cfg = self.root / "runtime" / "config"
        cfg.mkdir(parents=True, exist_ok=True)
        (cfg / "osf.env").write_text(f"# generated\nENABLE_PUBLIC_ACCESS={public_access}\nCAS_SERVER_URL={cas}\n", encoding="utf-8")

    def zap_web(self, out=SIGN_IN_OUT, probe=SIGN_IN_PROBE, calls=None):
        self.write_compose()
        ps = json.dumps([{"Service": "web", "State": "running", "Health": "healthy"}])
        return self.run_scan(fake_runner(compose_ps=ps, zap_rc=3, zap_out=out, probe=probe, calls=calls), dynamic=True)

    def assertZapUnverified(self, code, data):
        self.assertEqual(code, exit_codes.SCANNER_UNAVAILABLE)
        self.assertTrue(data["tools"][0]["result"].startswith("incomplete"), data["tools"][0])
        self.assertIn("no ZAP report for http://web:5000", data["tools"][0]["result"])
        self.assertNotIn("skipped_targets", data["tools"][0])
        self.assertFalse(any("ZAP NOT RUN" in n for n in data["notes"]), data["notes"])

    def test_zap_records_a_verified_sign_in_wall_as_skipped_coverage_not_as_a_scanned_target(self):
        """Mandatory sign-in (RDM-osf.io-dev2027 PR #8): web answers every anonymous request with a 302 to the configured
        CAS_SERVER_URL, and zap-baseline.py ends with "failed to access URL" and no report."""
        self.write_osf_env()
        calls = []
        code, data, _ = self.zap_web(calls=calls)
        self.assertEqual(code, exit_codes.OK)
        zap = data["tools"][0]
        self.assertEqual(zap["targets"], 0)  # nothing was scanned
        self.assertEqual(zap["skipped_targets"], ["http://web:5000"])
        self.assertTrue(zap["result"].startswith("ok (0 scanned, 1 skipped behind sign-in"), zap["result"])
        self.assertTrue(any("ZAP NOT RUN on web" in n and "127.0.0.1:8081" in n and "no page behind sign-in was scanned" in n
                            for n in data["notes"]), data["notes"])
        probes = [c for c in calls if "python3" in c]
        self.assertEqual(len(probes), 1)  # a request of its own proves the redirect
        self.assertEqual(probes[0][probes[0].index(scan.ZAP_IMAGE) + 1:][0], "python3")
        self.assertEqual(probes[0][-1], "http://web:5000")

    def test_zap_still_fails_when_the_redirect_goes_to_an_unknown_host(self):
        """REV r1 R1-01: an arbitrary 'Connect to ... failed' must not be a success, even if the probe also shows a redirect."""
        self.write_osf_env()
        out = self.SIGN_IN_OUT.replace("http://127.0.0.1:8081", "http://unexpected.invalid:9443")
        for probe in (self.SIGN_IN_PROBE, (0, "302 http://unexpected.invalid:9443/login\n")):
            code, data, _ = self.zap_web(out=out, probe=probe)
            self.assertZapUnverified(code, data)

    def test_zap_still_fails_when_the_probe_does_not_show_the_configured_redirect(self):
        self.write_osf_env()
        for probe in (None,                                          # the probe could not run
                      (0, "200 \n"),                                # web answered; nothing redirects
                      (0, "302 http://unexpected.invalid:9443/\n"),  # redirects somewhere else
                      (0, "302 /login\n"),                           # relative: not the configured address
                      (0, "302 \n"), (1, "302 http://127.0.0.1:8081/\n"),
                      (0, "500 http://127.0.0.1:8081/\n")):
            code, data, _ = self.zap_web(probe=probe)
            self.assertZapUnverified(code, data)

    def test_zap_malformed_evidence_is_no_evidence_and_the_scan_still_reports_incomplete(self):
        """REV r2 R2-01: a Location or address that cannot be parsed, or an osf.env that cannot be decoded, must end in
        exit 51 with a written report (an incomplete ZAP result, no skipped target), never an uncaught exception."""
        self.write_osf_env()
        for probe in ((0, "302 http://[broken\n"), (0, "302 http://[::1\n")):
            code, data, _ = self.zap_web(probe=probe)
            self.assertZapUnverified(code, data)
        out = self.SIGN_IN_OUT.replace("http://127.0.0.1:8081", "http://[broken")
        self.assertZapUnverified(*self.zap_web(out=out)[:2])
        self.write_osf_env(cas="http://[broken")  # a configured destination that cannot be parsed
        self.assertZapUnverified(*self.zap_web()[:2])
        (self.root / "runtime" / "config" / "osf.env").write_bytes(b"ENABLE_PUBLIC_ACCESS=false\nCAS_SERVER_URL=\xff\xfe\n")
        self.assertZapUnverified(*self.zap_web()[:2])

    def test_zap_still_fails_for_another_representation_of_the_sign_in_address_or_a_different_seed(self):
        self.write_osf_env()
        for out in (self.SIGN_IN_OUT.replace("127.0.0.1:8081", "localhost:8081"),
                    self.SIGN_IN_OUT.replace("127.0.0.1:8081", "127.0.0.1:8082"),
                    self.SIGN_IN_OUT.replace("http://web:5000", "http://web:5001")):
            code, data, _ = self.zap_web(out=out)
            self.assertZapUnverified(code, data)

    def test_zap_still_fails_in_public_access_or_without_a_rendered_sign_in_configuration(self):
        for public_access in ("true", "", "maybe"):
            self.write_osf_env(public_access=public_access)
            code, data, _ = self.zap_web()
            self.assertZapUnverified(code, data)
        self.write_osf_env(cas="")  # no configured sign-in address to compare with
        self.assertZapUnverified(*self.zap_web()[:2])
        (self.root / "runtime" / "config" / "osf.env").unlink()  # never rendered: no evidence
        self.assertZapUnverified(*self.zap_web()[:2])
        self.write_osf_env()
        self.write_env(test_compose.fake_secrets() + "GRDM_ENABLE_PUBLIC_ACCESS=true\n")  # the operator's setting disagrees
        self.assertZapUnverified(*self.zap_web()[:2])

    def test_zap_sign_in_exception_applies_to_web_only(self):
        self.write_osf_env()
        self.write_compose({"admin": hardened(ports=["127.0.0.1:8001:8001"], networks=["grdm", "grdm-edge"])})
        ps = json.dumps([{"Service": "admin", "State": "running", "Health": "healthy"}])
        out = self.SIGN_IN_OUT.replace("http://web:5000", "http://admin:8001")
        code, data, _ = self.run_scan(fake_runner(compose_ps=ps, zap_rc=3, zap_out=out, probe=self.SIGN_IN_PROBE), dynamic=True)
        self.assertEqual(code, exit_codes.SCANNER_UNAVAILABLE)
        self.assertIn("no ZAP report for http://admin:8001", data["tools"][0]["result"])

    def test_zap_still_fails_when_the_target_itself_cannot_be_reached(self):
        self.write_osf_env()
        out = "Automation plan failures:\n\tJob spider failed to access URL http://web:5000 : Connect to http://web:5000 failed: Connection refused\n"
        code, data, _ = self.zap_web(out=out)
        self.assertZapUnverified(code, data)
        ctx = self.ctx
        for text in ("", "something else"):
            self.assertIsNone(scan.zap_behind_sign_in(ctx, fake_runner(probe=self.SIGN_IN_PROBE), "grdm", "web", "http://web:5000", text))

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

    def test_zap_writes_into_its_own_world_writable_directory_that_is_removed(self):
        # DEMO-21 run 3: ZAP (uid 1000) could not write into runtime/reports owned by host uid 2001.
        self.write_compose()
        ps = json.dumps([{"Service": "web", "State": "running", "Health": "healthy"}])
        base = fake_runner(compose_ps=ps)
        seen = []

        def runner(argv):
            if argv[:2] == ["docker", "run"]:
                mount = Path(argv[argv.index("-v") + 1].split(":")[0])
                seen.append((mount, oct(mount.stat().st_mode & 0o777)))
            return base(argv)

        code, data, _ = self.run_scan(runner, dynamic=True)
        self.assertEqual(code, exit_codes.OK, data["tools"])
        reports = self.root / "runtime" / "reports"
        self.assertEqual(len(seen), 1)
        mount, mode = seen[0]
        self.assertEqual(mount.parent, reports)
        self.assertEqual(mode, "0o777")
        self.assertFalse(mount.exists())
        self.assertEqual(len(list(reports.glob("zap_web_*.json"))), 1)
        self.assertEqual(list(reports.glob("zap_wrk_*")), [])

    def _zap_ready(self):
        self.write_compose()
        return json.dumps([{"Service": "web", "State": "running", "Health": "healthy"}])

    def test_zap_refuses_a_runtime_that_others_can_enter(self):
        # PR #44 review r1 R3: with runtime/ at 0755 the 0777 work directory was reachable by other local users.
        ps = self._zap_ready()
        os.chmod(self.root / "runtime", 0o755)  # nosemgrep: python.lang.security.audit.insecure-file-permissions.insecure-file-permissions -- test fixture: the permissive runtime/ the scan must refuse
        calls = []
        code, data, _ = self.run_scan(fake_runner(compose_ps=ps, calls=calls), dynamic=True)
        self.assertEqual(code, exit_codes.SCANNER_UNAVAILABLE)
        self.assertIn("must be 0700", data["tools"][0]["result"])
        self.assertEqual([c for c in calls if c[:2] == ["docker", "run"]], [])
        self.assertEqual(list((self.root / "runtime" / "reports").glob("zap_wrk_*")), [])

    def test_zap_refuses_symlinked_runtime_or_reports(self):
        ps = self._zap_ready()
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir(mode=0o700)
        reports = self.root / "runtime" / "reports"
        reports.symlink_to(elsewhere, target_is_directory=True)
        calls = []
        code, data, _ = self.run_scan(fake_runner(compose_ps=ps, calls=calls), dynamic=True)
        self.assertEqual(code, exit_codes.SCANNER_UNAVAILABLE)
        self.assertIn("symbolic link", data["tools"][0]["result"])
        self.assertEqual([c for c in calls if c[:2] == ["docker", "run"]], [])
        self.assertEqual(list(elsewhere.glob("zap_wrk_*")), [])

    def test_zap_work_directory_names_are_unpredictable_and_reports_symlinks_are_refused(self):
        ps = self._zap_ready()
        outside = self.root / "outside.json"
        outside.write_text('{"site": [{"alerts": [{"pluginid": "1", "riskcode": "3", "alert": "planted"}]}]}')
        base = fake_runner(compose_ps=ps)
        mounts = []

        def runner(argv):
            if argv[:2] == ["docker", "run"]:
                wrk = Path(argv[argv.index("-v") + 1].split(":")[0])
                mounts.append(wrk.name)
                (wrk / argv[argv.index("-J") + 1]).symlink_to(outside)  # what another user could plant
                return 0, ""
            return base(argv)

        code, data, _ = self.run_scan(runner, dynamic=True)
        self.assertEqual(code, exit_codes.SCANNER_UNAVAILABLE)
        self.assertIn("symlink is refused", data["tools"][0]["result"])
        self.assertNotIn("planted", json.dumps(data["findings"]))
        self.assertEqual(len(mounts), 1)
        self.assertRegex(mounts[0], r"^zap_wrk_web_\S+_[A-Za-z0-9_]{6,}$")
        self.assertTrue(outside.exists())

    def test_fifo_report_is_refused_without_blocking(self):
        # PR #44 review r2 R2-02: os.open on a FIFO with no writer blocked before the type check. Bounded by a child.
        fifo = self.root / "report.json"
        os.mkfifo(fifo)
        code = ("import sys; from pathlib import Path; from grdm_dev import scan; "
                "print(scan._read_zap_report(Path(sys.argv[1]))[1])")
        cp = subprocess.run([sys.executable, "-c", code, str(fifo)], capture_output=True, text=True, timeout=10,
                            env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertIn("not a regular file", cp.stdout)

    def test_zap_does_not_write_into_a_fifo_in_reports(self):
        ps = self._zap_ready()
        reports = self.root / "runtime" / "reports"
        reports.mkdir()
        base = fake_runner(compose_ps=ps)
        planted = []

        def runner(argv):
            if argv[:2] == ["docker", "run"] and not planted:
                name = argv[argv.index("-J") + 1]
                os.mkfifo(reports / name)  # a FIFO where the masked copy will be saved
                # A reader keeps the test bounded: without it a regression would block in open() instead of failing.
                planted.append(os.open(reports / name, os.O_RDONLY | os.O_NONBLOCK))
                self.addCleanup(os.close, planted[-1])
            return base(argv)

        code, data, _ = self.run_scan(runner, dynamic=True)
        self.assertEqual(code, exit_codes.SCANNER_UNAVAILABLE)
        self.assertIn("only a regular file is written", data["tools"][0]["result"])

    def test_dynamic_targets_service_names_on_compose_network(self):
        self.write_compose({
            "web": hardened(ports=["127.0.0.1:5000:5000"], networks=["grdm", "grdm-edge"]),
            "admin": hardened("grdm-dev/admin:dev"),
            "postgres": hardened("postgres:9.6"),
        }, networks={"grdm": {"name": "grdm", "internal": True}, "grdm-edge": {"driver": "bridge"}})
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
        self.write_env("POSTGRES_PASSWORD=sup3rs3cretvalue\nSHORT=ab\n")
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
        self.assertEqual(set(scan.public_finding(f)), {"tool", "id", "severity", "component", "location", "title"})
        self.assertEqual(f["_trivy"]["pkg"], "p")
        self.assertEqual(f["severity"], "LOW")
        self.assertEqual(f["component"], "p@1")

    def test_zap_risk_mapping(self):
        f = scan.normalize_zap({"site": [{"alerts": [{"pluginid": "1", "riskcode": "3", "name": "x"}]}]}, "http://web:5000")[0]
        self.assertEqual(f["severity"], "HIGH")
        self.assertEqual(f["location"], "http://web:5000")


if __name__ == "__main__":
    unittest.main()
