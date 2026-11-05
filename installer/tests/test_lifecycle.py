import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from grdm_dev import exit_codes, lifecycle
from grdm_dev.context import Context

COMPOSE = {"services": {"web": {"ports": ["127.0.0.1:5000:5000"]}, "postgres": {}}}
PS_OK = json.dumps([{"Service": "web", "State": "running", "Health": "healthy"},
                    {"Service": "postgres", "State": "running", "Health": "healthy"}])
PS_DOWN = json.dumps([{"Service": "web", "State": "created", "Health": ""}])


def make_runner(ps_output, fail_cmd=None):
    calls = []

    def runner(argv):
        calls.append(argv)
        sub = argv[6] if argv[:2] == ["docker", "compose"] and len(argv) > 6 else argv[0]
        if sub == fail_cmd:
            return 1, "boom"
        if sub == "ps":
            return 0, ps_output
        return 0, ""

    runner.calls = calls
    return runner


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "runtime").mkdir()
        (self.root / "runtime" / "docker-compose.yml").write_text(json.dumps(COMPOSE))
        (self.root / "runtime" / ".env").write_text("GRDM_PROFILE=core\nGRDM_PORT_WEB=5001\n")
        self.out, self.err = io.StringIO(), io.StringIO()

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, ctx, action, runner, **kw):
        args = argparse.Namespace(lifecycle_action=action, no_open=kw.pop("no_open", False), timeout=kw.pop("timeout", 1.0))
        with redirect_stdout(self.out), redirect_stderr(self.err):
            return lifecycle.run(ctx, args, runner=runner, prober=lambda url: (True, "HTTP 200"), sleep=lambda s: None, **kw)

    def test_up_starts_waits_and_opens_browser_on_tty(self):
        ctx = Context(root=self.root, stdin_is_tty=True)
        runner = make_runner(PS_OK)
        opened = []
        self.assertEqual(self.run_cmd(ctx, "up", runner, opener=opened.append), exit_codes.OK)
        up = [c for c in runner.calls if "up" in c][0]
        self.assertEqual(up[:4], ["docker", "compose", "-f", str(self.root / "runtime" / "docker-compose.yml")])
        self.assertIn("-d", up)
        self.assertEqual(opened, ["http://127.0.0.1:5001/"])  # port from runtime/.env

    def test_up_does_not_open_without_tty_or_with_no_open(self):
        opened = []
        ctx = Context(root=self.root, stdin_is_tty=False)
        self.assertEqual(self.run_cmd(ctx, "up", make_runner(PS_OK), opener=opened.append), exit_codes.OK)
        ctx = Context(root=self.root, stdin_is_tty=True)
        self.assertEqual(self.run_cmd(ctx, "up", make_runner(PS_OK), opener=opened.append, no_open=True), exit_codes.OK)
        self.assertEqual(opened, [])

    def test_up_health_timeout_is_40(self):
        ctx = Context(root=self.root, stdin_is_tty=False)
        self.assertEqual(self.run_cmd(ctx, "up", make_runner(PS_DOWN), timeout=0.0), exit_codes.HEALTH_FAILED)
        self.assertIn("postgres", self.err.getvalue())

    def test_up_compose_failure_is_40(self):
        ctx = Context(root=self.root, stdin_is_tty=False)
        self.assertEqual(self.run_cmd(ctx, "up", make_runner(PS_OK, fail_cmd="up")), exit_codes.HEALTH_FAILED)

    def test_down_keeps_volumes(self):
        ctx = Context(root=self.root, stdin_is_tty=False)
        runner = make_runner(PS_OK)
        self.assertEqual(self.run_cmd(ctx, "down", runner), exit_codes.OK)
        down = [c for c in runner.calls if "down" in c][0]
        self.assertNotIn("--volumes", down)
        self.assertNotIn("-v", down)

    def test_reset_without_yes_and_no_tty_is_usage_error(self):
        ctx = Context(root=self.root, stdin_is_tty=False, yes=False)
        vol = self.root / "runtime" / "volumes"
        vol.mkdir()
        runner = make_runner(PS_OK)
        self.assertEqual(self.run_cmd(ctx, "reset", runner), exit_codes.USAGE)
        self.assertIn("--yes", self.err.getvalue())
        self.assertTrue(vol.exists())
        self.assertEqual(runner.calls, [])

    def test_reset_with_yes_downs_and_deletes_volumes(self):
        ctx = Context(root=self.root, stdin_is_tty=False, yes=True)
        vol = self.root / "runtime" / "volumes"
        (vol / "postgres").mkdir(parents=True)
        runner = make_runner(PS_OK)
        self.assertEqual(self.run_cmd(ctx, "reset", runner), exit_codes.OK)
        self.assertFalse(vol.exists())
        down = [c for c in runner.calls if "down" in c][0]
        self.assertIn("--volumes", down)

    def test_running_services_and_restart_helpers(self):
        ctx = Context(root=self.root, stdin_is_tty=False)
        runner = make_runner(json.dumps([{"Service": "web", "State": "running"}, {"Service": "api", "State": "exited"}]))
        self.assertEqual(lifecycle.running_services(ctx, runner=runner), ["web"])
        self.assertEqual(lifecycle.restart(ctx, ["web"], runner=runner), 0)
        self.assertEqual(runner.calls[-1][-2:], ["restart", "web"])

    def test_missing_compose_is_usage_error(self):
        (self.root / "runtime" / "docker-compose.yml").unlink()
        ctx = Context(root=self.root, stdin_is_tty=False)
        self.assertEqual(self.run_cmd(ctx, "up", make_runner(PS_OK)), exit_codes.USAGE)


if __name__ == "__main__":
    unittest.main()
