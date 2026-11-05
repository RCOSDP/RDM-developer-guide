import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from grdm_dev import cli, exit_codes, redteam
from grdm_dev.context import Context

REPO_MANIFEST = Path(__file__).resolve().parent.parent.parent / "manifest" / "redteam-targets.json"


def network_json(internal=True, containers=("grdm-redteam-web-1", "grdm-redteam-api-1")):
    return json.dumps({
        "Name": "grdm-redteam", "Internal": internal,
        "Containers": {f"id{i}": {"Name": n} for i, n in enumerate(containers)},
    })


class FakeDocker:
    def __init__(self, internal=True, containers=("grdm-redteam-web-1", "grdm-redteam-api-1"),
                 egress=False, network_missing=False, probe_rc=0):
        self.internal, self.containers, self.egress = internal, containers, egress
        self.network_missing, self.probe_rc = network_missing, probe_rc
        self.calls = []

    def __call__(self, argv):
        self.calls.append(argv)
        if argv[:3] == ["docker", "network", "inspect"]:
            if self.network_missing:
                return 1, "Error: No such network: grdm-redteam"
            return 0, network_json(self.internal, self.containers)
        if argv[:2] == ["docker", "run"]:
            if self.probe_rc:
                return self.probe_rc, "docker: Error response from daemon: No such image: alpine:latest"
            return 0, (redteam.PROBE_MARKER if self.egress else "blocked") + "\n"
        return 1, f"unexpected {argv}"


class RedteamPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "manifest").mkdir()
        (self.root / "manifest" / "upstreams.json").write_text("{}")
        (self.root / "manifest" / "redteam-targets.json").write_text(REPO_MANIFEST.read_text())
        (self.root / "docs" / "demo").mkdir(parents=True)
        (self.root / "docs" / "demo" / "30_redteam_2026-11-05.md").write_text("# approval\n")
        self.ctx = Context(root=self.root, yes=True)

    def tearDown(self):
        self.tmp.cleanup()

    def preflight(self, runner, **kw):
        args = argparse.Namespace(redteam_command="preflight", targets=None, approval=None, **kw)
        err, out = io.StringIO(), io.StringIO()
        with redirect_stderr(err), redirect_stdout(out):
            rc = redteam.run(self.ctx, args, runner=runner)
        return rc, err.getvalue(), out.getvalue()

    def test_repo_manifest_is_valid_and_lists_only_our_services(self):
        data = redteam.load_targets(REPO_MANIFEST)
        self.assertEqual(data["project"], "grdm-redteam")
        self.assertEqual(data["network"], "grdm-redteam")
        self.assertEqual(set(data["targets"]), {"web", "api", "admin", "wb", "mfr", "ember_osf_web", "cas"})

    def test_all_checks_pass_is_exit_0(self):
        docker = FakeDocker()
        rc, err, out = self.preflight(docker)
        self.assertEqual(rc, exit_codes.OK, err)
        self.assertIn("result: pass", out)
        self.assertIn("checks[4]{check,ok,detail}:", out)
        run = [a for a in docker.calls if a[:2] == ["docker", "run"]][0]
        self.assertIn("--pull", run)
        self.assertIn("never", run)
        self.assertEqual(run[run.index("--network") + 1], "grdm-redteam")
        self.assertIn("example.invalid", run[-1])
        # preflight never runs anything but inspect + the probe
        self.assertEqual(sorted(a[1] for a in docker.calls), ["network", "run"])

    def test_network_not_internal_is_53(self):
        rc, err, _ = self.preflight(FakeDocker(internal=False))
        self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED)
        self.assertIn("network_internal", err)

    def test_egress_reachable_is_53(self):
        rc, err, _ = self.preflight(FakeDocker(egress=True))
        self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED)
        self.assertIn("egress_blocked", err)

    def test_probe_container_not_runnable_is_53_not_a_pass(self):
        rc, err, _ = self.preflight(FakeDocker(probe_rc=125))
        self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED)
        self.assertIn("did not run", err)

    def test_unknown_container_on_network_is_53(self):
        rc, err, _ = self.preflight(FakeDocker(containers=("grdm-redteam-web-1", "grdm-core-postgres-1")))
        self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED)
        self.assertIn("grdm-core-postgres-1", err)

    def test_missing_network_is_53(self):
        rc, err, _ = self.preflight(FakeDocker(network_missing=True))
        self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED)

    def test_missing_approval_record_is_53(self):
        (self.root / "docs" / "demo" / "30_redteam_2026-11-05.md").unlink()
        rc, err, _ = self.preflight(FakeDocker())
        self.assertEqual(rc, exit_codes.REDTEAM_PREFLIGHT_FAILED)
        self.assertIn("approval_record", err)

    def test_invalid_manifest_is_20(self):
        (self.root / "manifest" / "redteam-targets.json").write_text('{"project": "x"}')
        rc, err, _ = self.preflight(FakeDocker())
        self.assertEqual(rc, exit_codes.MANIFEST_INVALID)
        (self.root / "manifest" / "redteam-targets.json").unlink()
        rc, err, _ = self.preflight(FakeDocker())
        self.assertEqual(rc, exit_codes.MANIFEST_INVALID)

    def test_service_of_handles_compose_naming(self):
        self.assertEqual(redteam.service_of("grdm-redteam-ember_osf_web-1", "grdm-redteam"), "ember_osf_web")
        self.assertEqual(redteam.service_of("grdm-redteam_web_1", "grdm-redteam"), "web")
        self.assertEqual(redteam.service_of("stray", "grdm-redteam"), "stray")

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
