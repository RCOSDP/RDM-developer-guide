"""grdm-dev redteam preflight (SPEC-03 §6, review r1 finding 4): approval record with scope/owner/date,
internal network, attacker attached to exactly that network, and isolation proven by a canary probe run
inside the attacker container with a control probe from the canary's own network. Docker is faked."""
import argparse
import datetime as _dt
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from grdm_dev import cli, exit_codes, redteam
from grdm_dev.context import Context

REPO_MANIFEST = Path(__file__).resolve().parent.parent.parent / "manifest" / "redteam-targets.json"
TODAY = _dt.date(2026, 11, 5)
ATTACKER = "grdm-redteam-attacker-1"
CANARY_NET = "grdm-redteam-canary"
CANARY_IP = "172.30.0.2"

APPROVAL = """# Red-team run approval

- approved_by: owner (Yusuke KOMIYAMA)
- approved_on: 2026-11-05
- run_id: rt-2026-11-05-01
- scope: web, api, admin, wb, mfr, ember_osf_web, cas
- commits: web@1a2b3c4, api@1a2b3c4
- model: Claude Code Fable; stop conditions: credential obtained -> stop and rotate
"""


def network_json(name="grdm-redteam", internal=True, containers=("grdm-redteam-web-1", "grdm-redteam-api-1", ATTACKER)):
    return json.dumps({"Name": name, "Internal": internal, "Containers": {f"id{i}": {"Name": n} for i, n in enumerate(containers)}})


class FakeDocker:
    """Answers docker argv with a configurable world. Records every call in `calls`."""

    def __init__(self, internal=True, containers=("grdm-redteam-web-1", "grdm-redteam-api-1", ATTACKER),
                 network_missing=False, attacker_networks=("grdm-redteam",), attacker_running=True, attacker_missing=False,
                 canary_net_exists=False, canary_run_rc=0, canary_ip=CANARY_IP, control="reachable",
                 attacker_to_canary="unreachable", attacker_to_external="unreachable"):
        self.internal, self.containers, self.network_missing = internal, containers, network_missing
        self.attacker_networks, self.attacker_running, self.attacker_missing = attacker_networks, attacker_running, attacker_missing
        self.canary_net_exists, self.canary_run_rc, self.canary_ip = canary_net_exists, canary_run_rc, canary_ip
        self.control, self.attacker_to_canary, self.attacker_to_external = control, attacker_to_canary, attacker_to_external
        self.calls = []
        self.canary_created = False
        self.canary_name = None
        self.removed = []

    @staticmethod
    def _probe_out(kind):
        return {"reachable": (0, redteam.REACH_OK + "\n"), "unreachable": (0, redteam.REACH_FAIL + "\n"),
                "notool": (0, redteam.PROBE_NOTOOL + "\n"), "crash": (126, "OCI runtime exec failed")}[kind]

    def __call__(self, argv):
        self.calls.append(list(argv))
        if argv[:3] == ["docker", "network", "inspect"]:
            name = argv[3]
            if name == CANARY_NET:
                return (0, CANARY_NET) if (self.canary_net_exists or self.canary_created) else (1, "No such network")
            if self.network_missing:
                return 1, f"Error: No such network: {name}"
            return 0, network_json(name, self.internal, self.containers)
        if argv[:3] == ["docker", "network", "create"]:
            self.canary_created = True
            return 0, "netid\n"
        if argv[:3] == ["docker", "network", "rm"]:
            self.removed.append(argv[3])
            return 0, ""
        if argv[:2] == ["docker", "inspect"]:
            name = argv[2]
            if name == ATTACKER:
                if self.attacker_missing:
                    return 1, "Error: No such object"
                return 0, json.dumps({"Name": "/" + ATTACKER, "State": {"Running": self.attacker_running},
                                      "NetworkSettings": {"Networks": {n: {"IPAddress": "10.9.0.5"} for n in self.attacker_networks}}})
            if name == self.canary_name:
                return 0, json.dumps({"State": {"Running": True},
                                      "NetworkSettings": {"Networks": {CANARY_NET: {"IPAddress": self.canary_ip}}}})
            return 1, "Error: No such object"
        if argv[:3] == ["docker", "run", "-d"]:
            if self.canary_run_rc:
                return self.canary_run_rc, "Unable to find image"
            self.canary_name = argv[argv.index("--name") + 1]
            return 0, "containerid\n"
        if argv[:3] == ["docker", "run", "--rm"]:  # control probe from the canary network
            return self._probe_out(self.control)
        if argv[:2] == ["docker", "exec"]:
            script = argv[-1]
            if CANARY_IP in script or (self.canary_ip and self.canary_ip in script):
                return self._probe_out(self.attacker_to_canary)
            return self._probe_out(self.attacker_to_external)
        if argv[:3] == ["docker", "rm", "-f"]:
            self.removed.append(argv[3])
            return 0, ""
        return 1, f"unexpected {argv}"


class RedteamPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "manifest").mkdir()
        (self.root / "manifest" / "upstreams.json").write_text("{}")
        (self.root / "manifest" / "redteam-targets.json").write_text(REPO_MANIFEST.read_text())
        (self.root / "docs" / "demo").mkdir(parents=True)
        self.approval = self.root / "docs" / "demo" / "30_redteam_2026-11-05.md"
        self.approval.write_text(APPROVAL)
        self.ctx = Context(root=self.root, yes=True, json_output=True)

    def tearDown(self):
        self.tmp.cleanup()

    def preflight(self, runner, **kw):
        ns = {"redteam_command": "preflight", "targets": None, "approval": None}
        ns.update(kw)
        args = argparse.Namespace(**ns)
        err, out = io.StringIO(), io.StringIO()
        with redirect_stderr(err), redirect_stdout(out):
            rc = redteam.run(self.ctx, args, runner=runner, today=TODAY)
        return rc, err.getvalue(), json.loads(out.getvalue()) if out.getvalue().strip() else {}

    def checks(self, data):
        return {c["check"]: c for c in data["checks"]}

    # ---- manifest

    def test_repo_manifest_is_valid_and_lists_only_our_services(self):
        data = redteam.load_targets(REPO_MANIFEST)
        self.assertEqual(data["project"], "grdm-redteam")
        self.assertEqual(data["network"], "grdm-redteam")
        self.assertEqual(data["attacker"], ATTACKER)
        self.assertEqual(set(data["targets"]), {"web", "api", "admin", "wb", "mfr", "ember_osf_web", "cas"})
        self.assertEqual(data["canary"], {"network": CANARY_NET, "image": "alpine:3.20", "port": 8080})
        self.assertEqual(data["external_probe"], "1.1.1.1:443")
        self.assertEqual(data["approval_max_age_days"], 30)

    def test_invalid_manifest_is_20(self):
        path = self.root / "manifest" / "redteam-targets.json"
        for bad in ('{"project": "x"}', '{"project":"p","network":"n","targets":["web"]}',  # attacker missing
                    '{"project":"p","network":"n","attacker":"a","targets":["web"],"canary":{"network":"n"}}',  # same as red-team net
                    '{"project":"p","network":"n","attacker":"a","targets":["web"],"external_probe":"example.invalid"}'):
            path.write_text(bad)
            rc, err, _ = self.preflight(FakeDocker())
            self.assertEqual(rc, exit_codes.MANIFEST_INVALID, bad)
        path.unlink()
        rc, err, _ = self.preflight(FakeDocker())
        self.assertEqual(rc, exit_codes.MANIFEST_INVALID)

    # ---- the happy path

    def test_all_checks_pass_is_exit_0_and_canary_is_cleaned_up(self):
        docker = FakeDocker()
        rc, err, data = self.preflight(docker)
        self.assertEqual(rc, exit_codes.OK, err)
        self.assertEqual(data["result"], "pass")
        self.assertEqual([c["check"] for c in data["checks"]],
                         ["approval_record", "network_internal", "targets_only", "attacker_network", "probe_control", "attacker_isolated"])
        self.assertTrue(all(c["ok"] for c in data["checks"]), data["checks"])
        self.assertEqual(data["approval"]["approved_by"], "owner (Yusuke KOMIYAMA)")
        self.assertEqual(data["approval"]["run_id"], "rt-2026-11-05-01")
        self.assertEqual(data["canary"], {"network": CANARY_NET, "ip": CANARY_IP, "port": 8080})
        # probes ran INSIDE the attacker container, against the canary IP and the external address
        execs = [a for a in docker.calls if a[:2] == ["docker", "exec"]]
        self.assertEqual([a[2] for a in execs], [ATTACKER, ATTACKER])
        self.assertIn(f"{CANARY_IP} 8080", execs[0][-1])
        self.assertIn("1.1.1.1 443", execs[1][-1])
        self.assertEqual([p["destination"] for p in data["probes"]], [f"{CANARY_IP}:8080", "1.1.1.1:443"])
        # the control probe ran on the canary's own network, and the canary got the run_id in its name
        control = [a for a in docker.calls if a[:3] == ["docker", "run", "--rm"]][0]
        self.assertEqual(control[control.index("--network") + 1], CANARY_NET)
        self.assertIn("rt-2026-11-05-01", docker.canary_name)
        # canary container and the network preflight created were removed
        self.assertIn(docker.canary_name, docker.removed)
        self.assertIn(CANARY_NET, docker.removed)
        # never anything but inspect / run / exec / rm / network
        self.assertEqual(set(a[1] for a in docker.calls), {"network", "inspect", "run", "exec", "rm"})

    def test_existing_canary_network_is_reused_not_removed(self):
        docker = FakeDocker(canary_net_exists=True)
        rc, err, _ = self.preflight(docker)
        self.assertEqual(rc, exit_codes.OK, err)
        self.assertFalse(any(a[:3] == ["docker", "network", "create"] for a in docker.calls))
        self.assertNotIn(CANARY_NET, docker.removed)
        self.assertIn(docker.canary_name, docker.removed)

    # ---- isolation must be proven

    def test_attacker_reaching_canary_is_53(self):
        rc, err, data = self.preflight(FakeDocker(attacker_to_canary="reachable"))
        self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED)
        self.assertIn("attacker_isolated", err)
        self.assertIn("NOT isolated", self.checks(data)["attacker_isolated"]["detail"])

    def test_attacker_reaching_external_address_is_53(self):
        docker = FakeDocker(attacker_to_external="reachable")
        rc, err, data = self.preflight(docker)
        self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED)
        self.assertIn("1.1.1.1:443", self.checks(data)["attacker_isolated"]["detail"])
        self.assertIn(docker.canary_name, docker.removed)  # cleanup also on failure

    def test_control_probe_failure_is_inconclusive_never_pass(self):
        for control in ("unreachable", "notool", "crash"):
            rc, err, data = self.preflight(FakeDocker(control=control))
            self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED, control)
            self.assertIn("probe inconclusive", self.checks(data)["probe_control"]["detail"], control)
            self.assertFalse(self.checks(data)["attacker_isolated"]["ok"], control)

    def test_attacker_probe_without_tool_or_crashing_is_inconclusive_53(self):
        for kind in ("notool", "crash"):
            rc, err, data = self.preflight(FakeDocker(attacker_to_canary=kind))
            self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED, kind)
            self.assertIn("inconclusive", self.checks(data)["attacker_isolated"]["detail"], kind)

    def test_canary_not_startable_is_53_not_a_pass(self):
        docker = FakeDocker(canary_run_rc=125)
        rc, err, data = self.preflight(docker)
        self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED)
        self.assertIn("could not start canary", self.checks(data)["probe_control"]["detail"])
        self.assertFalse(self.checks(data)["attacker_isolated"]["ok"])
        self.assertFalse(any(a[:2] == ["docker", "exec"] for a in docker.calls))
        self.assertIn(CANARY_NET, docker.removed)  # the network we created is removed even then

    def test_canary_without_ip_is_53(self):
        rc, err, data = self.preflight(FakeDocker(canary_ip=""))
        self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED)
        self.assertIn("no IP address", self.checks(data)["probe_control"]["detail"])

    # ---- network and attacker shape

    def test_network_not_internal_is_53(self):
        rc, err, data = self.preflight(FakeDocker(internal=False))
        self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED)
        self.assertIn("network_internal", err)
        self.assertEqual(self.checks(data)["network_internal"]["detail"], "Internal=False")

    def test_missing_network_is_53_and_skips_probes(self):
        docker = FakeDocker(network_missing=True)
        rc, err, data = self.preflight(docker)
        self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED)
        self.assertFalse(any(a[:2] == ["docker", "exec"] or a[:2] == ["docker", "run"] for a in docker.calls))
        self.assertFalse(self.checks(data)["attacker_isolated"]["ok"])

    def test_unknown_container_on_network_is_53(self):
        rc, err, _ = self.preflight(FakeDocker(containers=("grdm-redteam-web-1", ATTACKER, "grdm-core-postgres-1")))
        self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED)
        self.assertIn("grdm-core-postgres-1", err)
        self.assertNotIn(ATTACKER, err)  # the attacker itself is allowed on the network

    def test_attacker_on_second_network_is_53(self):
        docker = FakeDocker(attacker_networks=("grdm-redteam", "bridge"))
        rc, err, data = self.preflight(docker)
        self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED)
        self.assertIn("bridge", self.checks(data)["attacker_network"]["detail"])
        self.assertFalse(any(a[:2] == ["docker", "exec"] for a in docker.calls))

    def test_attacker_not_running_or_missing_is_53(self):
        rc, err, data = self.preflight(FakeDocker(attacker_running=False))
        self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED)
        self.assertIn("not running", self.checks(data)["attacker_network"]["detail"])
        rc, err, data = self.preflight(FakeDocker(attacker_missing=True))
        self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED)
        self.assertIn("isolation not proven", self.checks(data)["attacker_isolated"]["detail"])

    # ---- approval record

    def test_missing_approval_record_is_53(self):
        self.approval.unlink()
        rc, err, data = self.preflight(FakeDocker())
        self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED)
        self.assertIn("no record, no run", err)
        self.assertIsNone(data["approval"])

    def test_approval_without_header_fields_is_53(self):
        self.approval.write_text("# approval\n\nlooks fine to me\n")
        rc, err, data = self.preflight(FakeDocker())
        self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED)
        detail = self.checks(data)["approval_record"]["detail"]
        for k in redteam.APPROVAL_FIELDS:
            self.assertIn(f"missing {k}", detail)

    def test_stale_or_future_approval_is_53(self):
        self.approval.write_text(APPROVAL.replace("2026-11-05", "2026-10-05"))  # 31 days old
        rc, err, data = self.preflight(FakeDocker())
        self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED)
        self.assertIn("older than 30 days", self.checks(data)["approval_record"]["detail"])
        self.approval.write_text(APPROVAL.replace("approved_on: 2026-11-05", "approved_on: 2026-11-06"))
        rc, err, data = self.preflight(FakeDocker())
        self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED)
        self.assertIn("in the future", self.checks(data)["approval_record"]["detail"])
        self.approval.write_text(APPROVAL.replace("approved_on: 2026-11-05", "approved_on: 2026-10-06"))  # exactly 30 days: ok
        rc, err, _ = self.preflight(FakeDocker())
        self.assertEqual(rc, exit_codes.OK, err)

    def test_target_outside_approved_scope_is_53(self):
        self.approval.write_text(APPROVAL.replace("scope: web, api, admin, wb, mfr, ember_osf_web, cas", "scope: web, api"))
        rc, err, data = self.preflight(FakeDocker())
        self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED)
        detail = self.checks(data)["approval_record"]["detail"]
        self.assertIn("outside the approved scope", detail)
        for t in ("admin", "wb", "mfr", "ember_osf_web", "cas"):
            self.assertIn(t, detail)

    def test_scope_accepts_container_names_and_bullet_lists(self):
        self.approval.write_text(
            "approved_by: owner\napproved_on: 2026-11-05\nrun_id: r1\nscope:\n"
            + "".join(f"- grdm-redteam-{s}-1\n" for s in ("web", "api", "admin", "wb", "mfr", "ember_osf_web", "cas"))
            + "\nmodel: x\n")
        rc, err, data = self.preflight(FakeDocker())
        self.assertEqual(rc, exit_codes.OK, err)
        self.assertEqual(len(data["approval"]["scope"]), 7)

    def test_explicit_approval_path_is_used(self):
        other = self.root / "docs" / "demo" / "31_redteam_2026-11-05.md"
        other.write_text("approved_by: owner\napproved_on: 2026-11-05\nrun_id: r2\nscope: web\n")
        rc, err, data = self.preflight(FakeDocker(), approval=str(other))
        self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED)
        self.assertIn("31_redteam", data["approval"]["path"])

    # ---- helpers and CLI

    def test_service_of_handles_compose_naming(self):
        self.assertEqual(redteam.service_of("grdm-redteam-ember_osf_web-1", "grdm-redteam"), "ember_osf_web")
        self.assertEqual(redteam.service_of("grdm-redteam_web_1", "grdm-redteam"), "web")
        self.assertEqual(redteam.service_of("stray", "grdm-redteam"), "stray")

    def test_verdict_mapping(self):
        self.assertEqual(redteam.verdict(0, "GRDM_REACH_OK\n")[0], "reachable")
        self.assertEqual(redteam.verdict(0, "GRDM_REACH_FAIL\n")[0], "unreachable")
        self.assertEqual(redteam.verdict(0, "GRDM_PROBE_NOTOOL\n")[0], "inconclusive")
        self.assertEqual(redteam.verdict(1, "")[0], "inconclusive")
        self.assertEqual(redteam.verdict(0, "blocked")[0], "inconclusive")  # a bare word never counts as proof

    def test_probe_script_targets_exact_host_and_port(self):
        script = redteam.probe_script("172.30.0.2", 8080)
        self.assertIn("nc -z -w 3 172.30.0.2 8080", script)
        self.assertIn("http://172.30.0.2:8080/", script)
        self.assertIn(redteam.PROBE_NOTOOL, script)
        self.assertNotIn("example.invalid", script)

    def test_cli_registers_redteam_preflight_and_rejects_bare_redteam(self):
        parser = cli.build_parser()
        args = parser.parse_args(["redteam", "preflight"])
        self.assertIs(args._module, redteam)
        self.assertEqual(args.redteam_command, "preflight")
        err = io.StringIO()
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            rc = redteam.run(self.ctx, parser.parse_args(["redteam"]), runner=FakeDocker())
        self.assertEqual(rc, exit_codes.USAGE)


if __name__ == "__main__":
    unittest.main()
