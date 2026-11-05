"""grdm-dev redteam preflight (SPEC-03 §6, review r1 finding 4 / r2 finding R2-03): approval record with
scope/owner/date, internal network, attacker attached to exactly that network, and isolation proven by a
canary probe run inside the attacker container with a control probe from the canary's own network. Docker
is faked; the probe shell script itself is additionally executed through /bin/sh with a stub `nc` on PATH so
that a broken tool (unsupported option, wrong exit codes) is classified inconclusive, never blocked."""
import argparse
import datetime as _dt
import io
import json
import os
import stat
import subprocess
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
                 canary_net_exists=False, canary_run_rc=0, canary_ip=CANARY_IP, control="reached",
                 attacker_to_canary="blocked", attacker_to_external="blocked"):
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
        """What the probe script prints inside the container for each simulated world."""
        ok = f"GRDM_TOOL nc\n{redteam.SELFTEST_OK} tool=nc\n"
        return {
            "reached": (0, ok + f"{redteam.REACHED} 198.51.100.1:443\n"),
            "blocked": (0, ok + f"{redteam.BLOCKED} 198.51.100.1:443\n"),
            "toolerror": (0, ok + f"{redteam.TOOL_ERROR} 2 198.51.100.1:443\n"),           # nc exited 2 (bad option)
            "selftest_fail": (0, f"GRDM_TOOL nc\n{redteam.SELFTEST_FAIL} tool=nc open-port-rc=1 closed-port-rc=1\n"),
            "no_selftest": (0, f"{redteam.BLOCKED} 198.51.100.1:443\n"),                    # marker without self-test
            "notool": (0, redteam.PROBE_NOTOOL + "\n"),
            "crash": (126, "OCI runtime exec failed"),
        }[kind]

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
        self.assertIn(f"H={CANARY_IP}; P=8080;", execs[0][-1])
        self.assertIn("H=1.1.1.1; P=443;", execs[1][-1])
        self.assertEqual([p["verdict"] for p in data["probes"]], ["blocked", "blocked"])
        self.assertIn("tool self-test passed", self.checks(data)["attacker_isolated"]["detail"])
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
        rc, err, data = self.preflight(FakeDocker(attacker_to_canary="reached"))
        self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED)
        self.assertIn("attacker_isolated", err)
        self.assertIn("NOT isolated", self.checks(data)["attacker_isolated"]["detail"])

    def test_attacker_reaching_external_address_is_53(self):
        docker = FakeDocker(attacker_to_external="reached")
        rc, err, data = self.preflight(docker)
        self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED)
        self.assertIn("1.1.1.1:443", self.checks(data)["attacker_isolated"]["detail"])
        self.assertIn(docker.canary_name, docker.removed)  # cleanup also on failure

    def test_control_probe_failure_is_inconclusive_never_pass(self):
        for control in ("blocked", "notool", "crash", "toolerror", "selftest_fail"):
            rc, err, data = self.preflight(FakeDocker(control=control))
            self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED, control)
            self.assertIn("probe inconclusive", self.checks(data)["probe_control"]["detail"], control)
            self.assertFalse(self.checks(data)["attacker_isolated"]["ok"], control)

    def test_attacker_probe_without_tool_or_crashing_is_inconclusive_53(self):
        for kind in ("notool", "crash"):
            rc, err, data = self.preflight(FakeDocker(attacker_to_canary=kind))
            self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED, kind)
            self.assertIn("inconclusive", self.checks(data)["attacker_isolated"]["detail"], kind)

    def test_attacker_tool_error_or_failed_selftest_is_inconclusive_53_not_isolated(self):
        """R2-03: a broken probe tool (exit 2, failed self-test, marker without self-test) is never 'blocked'."""
        for kind in ("toolerror", "selftest_fail", "no_selftest"):
            for side in ("attacker_to_canary", "attacker_to_external"):
                rc, err, data = self.preflight(FakeDocker(**{side: kind}))
                self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED, (kind, side))
                iso = self.checks(data)["attacker_isolated"]
                self.assertFalse(iso["ok"], (kind, side))
                self.assertIn("isolation not proven", iso["detail"], (kind, side))
                self.assertIn("inconclusive", iso["detail"], (kind, side))
                verdicts = {p["probe"]: p["verdict"] for p in data["probes"]}
                self.assertEqual(verdicts["canary" if side == "attacker_to_canary" else "external"], "inconclusive", (kind, side))

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
        ok = "GRDM_TOOL nc\nGRDM_SELFTEST_OK tool=nc\n"
        self.assertEqual(redteam.verdict(0, ok + "GRDM_REACHED 1.1.1.1:443\n")[0], "reached")
        self.assertEqual(redteam.verdict(0, ok + "GRDM_BLOCKED 1.1.1.1:443\n")[0], "blocked")
        # tool error after a passing self-test: inconclusive, and the detail names the exit status
        v, detail = redteam.verdict(0, ok + "GRDM_TOOL_ERROR 2 1.1.1.1:443\n")
        self.assertEqual(v, "inconclusive")
        self.assertIn("exit 2", detail)
        # BLOCKED without a self-test, failed self-test, no tool, crash, bare words: never 'blocked'
        self.assertEqual(redteam.verdict(0, "GRDM_BLOCKED 1.1.1.1:443\n")[0], "inconclusive")
        self.assertEqual(redteam.verdict(0, "GRDM_TOOL nc\nGRDM_SELFTEST_FAIL tool=nc open-port-rc=2 closed-port-rc=2\n")[0], "inconclusive")
        self.assertEqual(redteam.verdict(0, "GRDM_PROBE_NOTOOL\n")[0], "inconclusive")
        self.assertEqual(redteam.verdict(1, "")[0], "inconclusive")
        self.assertEqual(redteam.verdict(0, "blocked")[0], "inconclusive")
        self.assertEqual(redteam.verdict(0, ok)[0], "inconclusive")  # self-test only, no result marker
        # a REACHED line is a connection even when the self-test is missing (fails the preflight either way)
        self.assertEqual(redteam.verdict(0, "GRDM_REACHED 1.1.1.1:443\n")[0], "reached")

    def test_probe_script_targets_exact_host_and_port_and_classifies_exit_status(self):
        script = redteam.probe_script("172.30.0.2", 8080)
        self.assertIn("H=172.30.0.2; P=8080;", script)
        self.assertIn('nc -z -w 3 "$1" "$2"', script)
        self.assertIn("/dev/tcp/$1/$2", script)
        for marker in (redteam.SELFTEST_OK, redteam.SELFTEST_FAIL, redteam.REACHED, redteam.BLOCKED, redteam.TOOL_ERROR, redteam.PROBE_NOTOOL):
            self.assertIn(marker, script)
        self.assertIn(f"1|{redteam.TIMEOUT_RC}) echo BLOCKED", script)  # exact exit statuses, not "nonzero"
        self.assertNotIn("wget", script)
        self.assertNotIn("curl", script)
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


STUB_NC = """#!/bin/sh
# Stub netcat for the probe self-test. Listener mode sleeps; connect mode answers by port.
case " $* " in *" -l "*) sleep 3; exit 0;; esac
for a in "$@"; do :; done
port=$a
case "$port" in
  {sp}) exit {open_rc};;
  {cp}) exit {closed_rc};;
  *) exit {target_rc};;
esac
"""


class ProbeScriptWithStubToolTests(unittest.TestCase):
    """R2-03 reproduction: run probe_script through /bin/sh with a stub `nc` first on PATH (no network I/O).
    open_rc / closed_rc are what the stub returns for the self-test ports, target_rc for the real target."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bin = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_probe(self, target_rc, open_rc=0, closed_rc=1, uniform_rc=None):
        if uniform_rc is not None:
            open_rc = closed_rc = target_rc = uniform_rc
        nc = self.bin / "nc"
        nc.write_text(STUB_NC.format(sp=redteam.SELFTEST_PORT, cp=redteam.SELFTEST_PORT + 1,
                                     open_rc=open_rc, closed_rc=closed_rc, target_rc=target_rc))
        nc.chmod(nc.stat().st_mode | stat.S_IXUSR)
        env = {"PATH": f"{self.bin}{os.pathsep}/usr/bin:/bin", "LC_ALL": "C"}
        proc = subprocess.run(["/bin/sh", "-c", redteam.probe_script("192.0.2.1", 443)], capture_output=True, text=True,
                              env=env, timeout=30)
        return proc.returncode, proc.stdout + proc.stderr

    def test_stub_nc_exiting_2_is_inconclusive_not_blocked(self):
        # The review's reproduction: unsupported options -> nc exits 2 for everything. The self-test fails.
        rc, out = self.run_probe(target_rc=2, uniform_rc=2)
        self.assertEqual(rc, 0, out)
        self.assertIn(redteam.SELFTEST_FAIL, out)
        self.assertNotIn(redteam.BLOCKED, out)
        v, detail = redteam.verdict(rc, out)
        self.assertEqual(v, "inconclusive", out)
        self.assertIn("self-test failed", detail)

    def test_tool_error_only_on_the_target_is_inconclusive(self):
        # Self-test passes (0 open / 1 closed) but the target probe exits 2: TOOL_ERROR 2, not BLOCKED.
        rc, out = self.run_probe(target_rc=2)
        self.assertIn(redteam.SELFTEST_OK, out)
        self.assertIn(f"{redteam.TOOL_ERROR} 2 192.0.2.1:443", out)
        v, detail = redteam.verdict(rc, out)
        self.assertEqual(v, "inconclusive", out)
        self.assertIn("exit 2", detail)

    def test_refused_after_passing_selftest_is_blocked(self):
        rc, out = self.run_probe(target_rc=1)
        self.assertIn(redteam.SELFTEST_OK, out)
        self.assertIn(f"{redteam.BLOCKED} 192.0.2.1:443", out)
        self.assertEqual(redteam.verdict(rc, out)[0], "blocked", out)

    def test_connected_target_is_reached(self):
        rc, out = self.run_probe(target_rc=0)
        self.assertIn(f"{redteam.REACHED} 192.0.2.1:443", out)
        self.assertEqual(redteam.verdict(rc, out)[0], "reached", out)

    def test_tool_that_always_succeeds_fails_the_closed_port_selftest(self):
        # A tool that cannot report a refused connection would turn every target into "reached" or hide
        # errors; the closed-port half of the self-test catches it (open 0, closed 0).
        rc, out = self.run_probe(target_rc=1, open_rc=0, closed_rc=0)
        self.assertIn(f"{redteam.SELFTEST_FAIL} tool=nc open-port-rc=0 closed-port-rc=0", out)
        self.assertEqual(redteam.verdict(rc, out)[0], "inconclusive", out)

    def test_tool_that_cannot_reach_its_own_listener_fails_the_selftest(self):
        rc, out = self.run_probe(target_rc=1, open_rc=1, closed_rc=1)
        self.assertIn(f"{redteam.SELFTEST_FAIL} tool=nc open-port-rc=1 closed-port-rc=1", out)
        self.assertEqual(redteam.verdict(rc, out)[0], "inconclusive", out)


if __name__ == "__main__":
    unittest.main()
