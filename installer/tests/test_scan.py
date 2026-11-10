"""Unit tests for grdm-dev scan (SPEC-03): staged gate, allow-list, baseline validator against the real
renderer and against synthetic violations, scanner robustness (incomplete -> 51), --dynamic.

All scanners are faked through the injectable runner / which; Docker is never required.
"""
from __future__ import annotations

import datetime as _dt
import io
import json
import os
import shutil
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
     "Title": "ctypes buffer overflow"},
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
                sbom_rc=0, trivy_fail_target=None, zap_rc=0):
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
            # (elasticsearch left this list in real install run 8: it now runs as uid 101; cas joined it)
            for svc in ("postgres", "mongo", "rabbitmq", "cas"):
                self.assertIn("user", by_service[svc], svc)
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
            "elasticsearch": hardened("elasticsearch:2"),
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
                                       "elasticsearch:2", "rabbitmq:3-management", "mongo:3.4",
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
        self.assertEqual(set(f), {"tool", "id", "severity", "component", "location", "title"})
        self.assertEqual(f["severity"], "LOW")
        self.assertEqual(f["component"], "p@1")

    def test_zap_risk_mapping(self):
        f = scan.normalize_zap({"site": [{"alerts": [{"pluginid": "1", "riskcode": "3", "name": "x"}]}]}, "http://web:5000")[0]
        self.assertEqual(f["severity"], "HIGH")
        self.assertEqual(f["location"], "http://web:5000")


if __name__ == "__main__":
    unittest.main()
