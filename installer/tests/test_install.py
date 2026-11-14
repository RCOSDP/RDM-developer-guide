import argparse
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from grdm_dev import exit_codes, install
from grdm_dev.context import Context


def fake_steps(codes: dict[str, int]):
    """run_step that returns codes[argv[0]] (default 0) and records argv; -1 marks a missing module."""
    calls = []

    def run_step(ctx, argv):
        calls.append(argv)
        return codes.get(argv[0], 0)

    run_step.calls = calls
    return run_step


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ctx = Context(root=self.root, stdin_is_tty=False, yes=True)
        self.out, self.err = io.StringIO(), io.StringIO()

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, run_step, **kw):
        args = argparse.Namespace(platform=kw.get("platform"), no_open=kw.get("no_open", False))
        with redirect_stdout(self.out), redirect_stderr(self.err):
            return install.run(self.ctx, args, run_step=run_step)

    def test_full_sequence_in_spec_order_and_prints_url(self):
        step = fake_steps({})
        self.assertEqual(self.run_cmd(step, platform="linux/arm64", no_open=True), exit_codes.OK)
        self.assertEqual(
            step.calls,
            [["doctor"], ["plan"], ["secrets", "init"], ["compose", "render"], ["build", "--platform", "linux/arm64"],
             ["up", "--no-open"], ["health", "--network"], ["scan"], ["report"]],
        )
        self.assertIn("http://127.0.0.1:5000/", self.out.getvalue())

    def test_secrets_init_skipped_when_env_exists(self):
        (self.root / "runtime").mkdir()
        (self.root / "runtime" / ".env").write_text("GRDM_PROFILE=core\nGRDM_PORT_WEB=5001\n")
        step = fake_steps({})
        self.assertEqual(self.run_cmd(step), exit_codes.OK)
        self.assertNotIn(["secrets", "init"], step.calls)
        self.assertIn("http://127.0.0.1:5001/", self.out.getvalue())

    def test_stops_at_first_failure_with_its_code(self):
        step = fake_steps({"plan": exit_codes.MANIFEST_INVALID, "build": exit_codes.BUILD_FAILED})
        self.assertEqual(self.run_cmd(step), exit_codes.MANIFEST_INVALID)
        self.assertEqual(step.calls, [["doctor"], ["plan"]])
        self.assertIn("plan", self.err.getvalue())

    def test_build_failure_returns_30_and_skips_up(self):
        step = fake_steps({"build": exit_codes.BUILD_FAILED})
        self.assertEqual(self.run_cmd(step), exit_codes.BUILD_FAILED)
        self.assertNotIn(["up"], step.calls)
        self.assertNotIn("http://127.0.0.1", self.out.getvalue().split("install:")[0] if "ready" in self.out.getvalue() else "")

    def test_missing_scan_module_is_not_fatal(self):
        step = fake_steps({"scan": -1, "report": -1})
        self.assertEqual(self.run_cmd(step), exit_codes.OK)
        self.assertIn("not yet available", self.err.getvalue())
        self.assertIn(["report"], step.calls)

    def test_volumes_of_another_checkout_stop_install_before_build(self):
        """DEMO-22 0.7: the guard of `up` fired after a 10 h 45 min build; install now checks right after render."""
        run_step = fake_steps({})
        args = argparse.Namespace(platform=None, no_open=True, memory_gib=None, timeout=None)
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            code = install.run(self.ctx, args, run_step=run_step,
                               volume_check=lambda ctx: ["grdm-dev_postgres_data is bound to /old/runtime/volumes/postgres_data, this checkout uses /new/runtime/volumes/postgres_data"])
        self.assertEqual(code, exit_codes.PREFLIGHT_FAILED)
        ran = [argv[0] for argv in run_step.calls]
        self.assertIn("compose", ran)
        self.assertNotIn("build", ran)
        self.assertNotIn("up", ran)
        self.assertIn("docker volume rm grdm-dev_postgres_data", err.getvalue())

    def test_no_stale_volume_lets_install_continue(self):
        run_step = fake_steps({})
        args = argparse.Namespace(platform=None, no_open=True, memory_gib=None, timeout=None)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = install.run(self.ctx, args, run_step=run_step, volume_check=lambda ctx: [])
        self.assertEqual(code, exit_codes.OK)
        self.assertIn("build", [argv[0] for argv in run_step.calls])

    def test_missing_required_module_is_usage_error(self):
        step = fake_steps({"compose": -1})
        self.assertEqual(self.run_cmd(step), exit_codes.USAGE)
        self.assertNotIn(["build"], step.calls)

    def test_default_run_step_reaches_real_modules(self):
        # secrets init runs for real through the CLI parser (no Docker needed)
        with redirect_stdout(self.out), redirect_stderr(self.err):
            self.assertEqual(install.default_run_step(self.ctx, ["secrets", "init"]), exit_codes.OK)
            self.assertEqual(install.default_run_step(self.ctx, ["no-such-command"]), -1)
        self.assertTrue((self.root / "runtime" / ".env").exists())


if __name__ == "__main__":
    unittest.main()
