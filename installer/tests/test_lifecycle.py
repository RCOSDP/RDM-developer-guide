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

    def test_running_services_and_recreate_helpers(self):
        ctx = Context(root=self.root, stdin_is_tty=False)
        runner = make_runner(json.dumps([{"Service": "web", "State": "running"}, {"Service": "api", "State": "exited"}]))
        self.assertEqual(lifecycle.running_services(ctx, runner=runner), ["web"])
        self.assertEqual(lifecycle.recreate(ctx, runner=runner), 0)
        self.assertEqual(runner.calls[-1][6:], ["up", "-d", "--force-recreate", "--remove-orphans"])
        self.assertFalse(hasattr(lifecycle, "restart"))  # restart keeps the old environment: not offered

    def render_with_volumes(self, here: Path):
        vols = {n: {"driver": "local", "driver_opts": {"type": "none", "o": "bind", "device": str(here / "runtime" / "volumes" / n)}}
                for n in ("postgres_data", "redis_data")}
        (self.root / "runtime" / "docker-compose.yml").write_text(json.dumps({**COMPOSE, "volumes": vols}))

    def runner_with_existing_volumes(self, existing: dict):
        base = make_runner(PS_OK)

        def runner(argv):
            if argv[:3] == ["docker", "volume", "inspect"]:
                base.calls.append(argv)
                name = argv[-1]
                if name in existing:
                    return 0, json.dumps({"type": "none", "o": "bind", "device": existing[name]}) + "\n"
                return 1, ""
            return base(argv)

        runner.calls = base.calls
        return runner

    def test_up_refuses_volumes_that_another_checkout_created(self):
        self.render_with_volumes(self.root)
        old = "/home/someone/RDM-developer-guide/runtime/volumes"
        runner = self.runner_with_existing_volumes({"grdm-dev_postgres_data": f"{old}/postgres_data"})
        ctx = Context(root=self.root, stdin_is_tty=False)
        self.assertEqual(self.run_cmd(ctx, "up", runner), exit_codes.PREFLIGHT_FAILED)
        err = self.err.getvalue()
        self.assertIn("exit 13", err)
        self.assertIn(f"grdm-dev_postgres_data is bound to {old}/postgres_data", err)
        self.assertIn("docker volume rm grdm-dev_postgres_data", err)
        self.assertNotIn("grdm-dev_redis_data", err)  # it does not exist, so Compose creates it here
        self.assertFalse([c for c in runner.calls if "up" in c and c[0] == "docker" and c[1] == "compose"])  # nothing started
        self.assertFalse([c for c in runner.calls if "rm" in c])  # and nothing deleted

    def test_up_accepts_volumes_bound_to_this_checkout_or_absent(self):
        self.render_with_volumes(self.root)
        here = self.root / "runtime" / "volumes"
        runner = self.runner_with_existing_volumes({"grdm-dev_postgres_data": str(here / "postgres_data"),
                                                    "grdm-dev_redis_data": str(here / "redis_data")})
        ctx = Context(root=self.root, stdin_is_tty=False)
        self.assertEqual(self.run_cmd(ctx, "up", runner), exit_codes.OK)
        runner = self.runner_with_existing_volumes({})
        self.assertEqual(self.run_cmd(ctx, "up", runner), exit_codes.OK)

    def test_up_ignores_a_volume_listing_it_cannot_read(self):
        self.render_with_volumes(self.root)
        base = make_runner(PS_OK)

        def runner(argv):
            if argv[:3] == ["docker", "volume", "inspect"]:
                return 0, "not json"
            return base(argv)

        ctx = Context(root=self.root, stdin_is_tty=False)
        self.assertEqual(self.run_cmd(ctx, "up", runner), exit_codes.OK)

    def test_missing_compose_is_usage_error(self):
        (self.root / "runtime" / "docker-compose.yml").unlink()
        ctx = Context(root=self.root, stdin_is_tty=False)
        self.assertEqual(self.run_cmd(ctx, "up", make_runner(PS_OK)), exit_codes.USAGE)


if __name__ == "__main__":
    unittest.main()


class DefaultTimeoutTests(unittest.TestCase):
    """DEMO-21 run 2: on Linux arm64 QEMU took 44 min for ember's first build, so 1800 s stopped a good install."""

    def setUp(self):
        import shutil
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copytree(Path(__file__).resolve().parents[2] / "manifest", self.root / "manifest")
        # no component pins build_platform linux/amd64 today; pin one on the copy to keep the rule covered
        import json
        path = self.root / "manifest" / "upstreams.json"
        data = json.loads(path.read_text())
        for comp in data["components"]:
            if comp["id"] == "modular-file-renderer":
                comp["build_platform"] = "linux/amd64"
        path.write_text(json.dumps(data))

    def timeout(self, profile, system, machine):
        return lifecycle.default_timeout(Context(root=self.root, profile=profile), system=system, machine=machine)

    def test_linux_arm64_with_amd64_services_waits_longer(self):
        self.assertEqual(self.timeout("core", "Linux", "aarch64"), lifecycle.QEMU_TIMEOUT)
        self.assertGreaterEqual(lifecycle.QEMU_TIMEOUT, 2 * 44 * 60)

    def test_other_hosts_and_profiles_keep_the_default(self):
        self.assertEqual(self.timeout("core", "Linux", "x86_64"), lifecycle.DEFAULT_TIMEOUT)
        self.assertEqual(self.timeout("core", "Darwin", "arm64"), lifecycle.DEFAULT_TIMEOUT)
        self.assertEqual(self.timeout("minimum", "Linux", "aarch64"), lifecycle.DEFAULT_TIMEOUT)

    def test_unreadable_manifest_keeps_the_default(self):
        (self.root / "manifest" / "upstreams.json").write_text("{not json")
        self.assertEqual(self.timeout("core", "Linux", "aarch64"), lifecycle.DEFAULT_TIMEOUT)

    def test_explicit_timeout_wins_and_none_means_default(self):
        seen = []
        original = lifecycle.run_up
        self.addCleanup(setattr, lifecycle, "run_up", original)
        lifecycle.run_up = lambda ctx, **kw: seen.append(kw["timeout"]) or 0
        ctx = Context(root=self.root, profile="core")
        lifecycle.run(ctx, argparse.Namespace(lifecycle_action="up", no_open=True, timeout=12.0))
        lifecycle.run(ctx, argparse.Namespace(lifecycle_action="up", no_open=True, timeout=None))
        self.assertEqual(seen[0], 12.0)
        self.assertEqual(seen[1], lifecycle.default_timeout(ctx))
