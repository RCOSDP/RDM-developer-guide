import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from grdm_dev import accept, cli, exit_codes
from grdm_dev.context import Context

JUNIT_ONE_FAILURE = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" tests="3" failures="1" skipped="1">
<testcase classname="acceptance.test_c1_login" name="test_c1_login_success" time="1.250">
  <properties><property name="http_status" value="200"/></properties></testcase>
<testcase classname="acceptance.test_c1_login" name="test_c1_login_rejection" time="0.300">
  <properties><property name="http_status" value="200"/></properties>
  <failure message="assert 200 == 401">AssertionError</failure></testcase>
<testcase classname="acceptance.test_s1_y_websocket" name="test_s1_y_websocket_success" time="0.001"><skipped message="M3"/></testcase>
</testsuite></testsuites>
"""


def importer_ok(name):
    return object()


def importer_missing(name):
    if name == "playwright":
        raise ImportError(name)
    return object()


class FakeRunner:
    """Records argv; writes junit.xml when asked to run pytest."""

    def __init__(self, pytest_rc=0, junit=None, seed_rc=0):
        self.calls = []
        self.pytest_rc = pytest_rc
        self.junit = junit
        self.seed_rc = seed_rc

    def __call__(self, argv, env=None, cwd=None):
        self.calls.append((argv, env))
        if "pytest" in argv:
            if self.junit is not None:
                Path(argv[argv.index("--junitxml") + 1]).write_text(self.junit, encoding="utf-8")
            return self.pytest_rc, "pytest output"
        if "manage.py" in argv:
            return self.seed_rc, "seeded"
        return 0, ""


class AcceptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "manifest").mkdir()
        (self.root / "manifest" / "upstreams.json").write_text("{}")
        (self.root / ".venv" / ".playwright" / "chromium-1").mkdir(parents=True)
        self.ctx = Context(root=self.root, yes=True)
        self.ctx.env = {}

    def tearDown(self):
        self.tmp.cleanup()

    def args(self, **kw):
        base = dict(only=None, seed=False, base_url=None, headed=False)
        base.update(kw)
        return argparse.Namespace(**base)

    def run_accept(self, args, runner, importer=importer_ok):
        err, out = io.StringIO(), io.StringIO()
        with redirect_stderr(err), redirect_stdout(out):
            rc = accept.run(self.ctx, args, runner=runner, importer=importer)
        return rc, err.getvalue(), out.getvalue()

    def test_missing_playwright_is_usage_error_with_hint(self):
        runner = FakeRunner()
        rc, err, _ = self.run_accept(self.args(), runner, importer=importer_missing)
        self.assertEqual(rc, exit_codes.USAGE)
        self.assertIn("playwright", err)
        self.assertIn('pip install -e "installer[accept]"', err)
        self.assertIn("playwright install chromium", err)
        self.assertEqual(runner.calls, [])

    def test_non_loopback_base_url_is_refused(self):
        for url in ("http://localhost:5000", "http://192.168.1.10:5000", "https://127.0.0.1:5000", "http://example.com"):
            runner = FakeRunner()
            rc, err, _ = self.run_accept(self.args(base_url=url), runner)
            self.assertEqual(rc, exit_codes.USAGE, url)
            self.assertEqual(runner.calls, [], url)
        self.assertIsNone(accept.loopback_problem("http://127.0.0.1:5001"))

    def test_missing_browser_cache_is_usage_error(self):
        for p in (self.root / ".venv" / ".playwright").iterdir():
            p.rmdir()
        rc, err, _ = self.run_accept(self.args(), FakeRunner())
        self.assertEqual(rc, exit_codes.USAGE)
        self.assertIn(".playwright", err)

    def test_pytest_failure_maps_to_60_and_writes_results(self):
        runner = FakeRunner(pytest_rc=1, junit=JUNIT_ONE_FAILURE)
        rc, err, out = self.run_accept(self.args(base_url="http://127.0.0.1:5000"), runner)
        self.assertEqual(rc, exit_codes.ACCEPTANCE_FAILED)
        runs = list((self.root / "docs" / "demo" / "runs").iterdir())
        self.assertEqual(len(runs), 1)
        run_dir = runs[0]
        self.assertTrue(run_dir.name.startswith("acc-"))
        results = json.loads((run_dir / "results.json").read_text())
        self.assertEqual(results["summary"], {"passed": 1, "failed": 1, "error": 0, "skipped": 1, "total": 3})
        by_test = {r["test"]: r for r in results["tests"]}
        rej = by_test["test_c1_login_rejection"]
        self.assertEqual((rej["id"], rej["name"], rej["case"], rej["status"]), ("C1", "Login via fakecas", "rejection", "failed"))
        self.assertEqual(rej["http_status"], 200)
        self.assertEqual(by_test["test_c1_login_success"]["duration_ms"], 1250)
        self.assertEqual(by_test["test_s1_y_websocket_success"]["status"], "skipped")
        toon_text = (run_dir / "results.toon").read_text()
        self.assertIn("accept:", toon_text)
        self.assertIn("tests[3]{", toon_text)
        self.assertIn("C1,Login via fakecas,rejection", toon_text)
        self.assertIn("results.toon", str(list(run_dir.iterdir())))
        self.assertTrue((run_dir / "junit.xml").exists())
        # pytest was invoked with the SPEC-04 evidence flags and the loopback URL, inside the venv browsers path
        argv, env = runner.calls[-1]
        self.assertIn("--junitxml", argv)
        self.assertEqual(argv[argv.index("--base-url") + 1], "http://127.0.0.1:5000")
        self.assertEqual(argv[argv.index("--screenshot") + 1], "only-on-failure")
        self.assertEqual(argv[argv.index("--tracing") + 1], "retain-on-failure")
        self.assertEqual(env["PLAYWRIGHT_BROWSERS_PATH"], str(self.root / ".venv" / ".playwright"))
        self.assertEqual(env["GRDM_BASE_URL"], "http://127.0.0.1:5000")
        self.assertTrue(env["GRDM_ACCEPT_USER_A"].endswith("@acceptance.test"))

    def test_all_green_is_exit_0_and_collector_preferred(self):
        class CollectorRunner(FakeRunner):
            def __call__(self, argv, env=None, cwd=None):
                rc = super().__call__(argv, env, cwd)
                if "pytest" in argv:
                    Path(env["GRDM_ACCEPT_RESULTS"]).write_text(json.dumps([
                        {"nodeid": "installer/acceptance/test_c2_create_project.py::test_c2_create_project_success",
                         "id": "C2", "name": "Create project", "case": "success", "status": "passed",
                         "duration_ms": 900, "http_status": 201, "evidence": None}]))
                return rc

        runner = CollectorRunner(pytest_rc=0, junit=JUNIT_ONE_FAILURE)
        rc, _, _ = self.run_accept(self.args(), runner)
        self.assertEqual(rc, exit_codes.OK)
        run_dir = next((self.root / "docs" / "demo" / "runs").iterdir())
        results = json.loads((run_dir / "results.json").read_text())
        self.assertEqual(results["summary"]["total"], 1)
        self.assertEqual(results["tests"][0]["id"], "C2")
        self.assertEqual(results["base_url"], "http://127.0.0.1:5000")  # default: no runtime/.env -> port 5000

    def test_base_url_default_reads_runtime_env_port(self):
        (self.root / "runtime").mkdir()
        (self.root / "runtime" / ".env").write_text("GRDM_PORT_WEB=5050\nGRDM_PORT_API=8000\n")
        self.assertEqual(accept.default_base_url(self.ctx), "http://127.0.0.1:5050")

    def test_seed_runs_management_command_then_cleanup(self):
        runner = FakeRunner(pytest_rc=0, junit='<testsuites><testsuite><testcase classname="t" name="test_c1_login_success" time="1"/></testsuite></testsuites>')
        rc, _, _ = self.run_accept(self.args(seed=True), runner)
        self.assertEqual(rc, exit_codes.OK)
        seed_calls = [a for a, _ in runner.calls if "manage.py" in a]
        self.assertEqual(len(seed_calls), 4)  # user_a, user_b, admin, cleanup
        self.assertEqual(seed_calls[0][:3], ["docker", "compose", "exec"])
        self.assertIn("web", seed_calls[0])
        self.assertIn("create_confirmed", seed_calls[0][-1])
        self.assertIn("delete()", seed_calls[-1][-1])
        # pytest ran between seeding and cleanup
        order = ["seed" if "manage.py" in a else "pytest" for a, _ in runner.calls]
        self.assertEqual(order, ["seed", "seed", "seed", "pytest", "seed"])

    def test_seed_failure_is_52(self):
        runner = FakeRunner(seed_rc=1)
        rc, err, _ = self.run_accept(self.args(seed=True), runner)
        self.assertEqual(rc, exit_codes.SERVICES_UNHEALTHY)
        self.assertFalse(any("pytest" in a for a, _ in runner.calls))

    def test_only_selection(self):
        paths, extra = accept.select_tests("C3")
        self.assertEqual([Path(p).name for p in paths], ["test_c3_file_upload.py"])
        paths, extra = accept.select_tests("login")
        self.assertEqual([Path(p).name for p in paths], ["test_c1_login.py"])
        paths, extra = accept.select_tests("subsystem")
        self.assertEqual(extra, ["-m", "subsystem"])
        self.assertIsNone(accept.select_tests("no-such-scenario"))
        rc, err, _ = self.run_accept(self.args(only="zzz"), FakeRunner())
        self.assertEqual(rc, exit_codes.USAGE)

    def test_scenario_files_cover_c1_to_c6_and_s1_to_s5_with_both_cases(self):
        for sid in accept.SCENARIOS:
            files = list(accept.ACCEPTANCE_DIR.glob(f"test_{sid.lower()}_*.py"))
            self.assertEqual(len(files), 1, sid)
            src = files[0].read_text()
            self.assertIn("_success(", src, sid)
            self.assertIn("_rejection(", src, sid)
            self.assertIn("pytest.mark.core" if sid.startswith("C") else 'pytest.mark.skip(reason="M3")', src, sid)

    def test_cli_registers_accept(self):
        parser = cli.build_parser()
        args = parser.parse_args(["accept", "--only", "C1", "--seed", "--base-url", "http://127.0.0.1:5000"])
        self.assertIs(args._module, accept)
        self.assertEqual((args.only, args.seed, args.base_url), ("C1", True, "http://127.0.0.1:5000"))


if __name__ == "__main__":
    unittest.main()
