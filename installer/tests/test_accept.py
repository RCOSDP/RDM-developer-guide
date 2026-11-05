import argparse
import io
import json
import os
import stat
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from acceptance import netguard
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

SECRET = "sUp3rS3cretValue-abc123"


def junit_all_green(ids=accept.SCENARIOS, extra_body=""):
    """A junit.xml with a passed success and rejection row for every scenario id in `ids`."""
    cases = []
    for sid in ids:
        stem = f"test_{sid.lower()}_x"
        for case in ("success", "rejection"):
            cases.append(f'<testcase classname="acceptance.{stem}" name="{stem}_{case}" time="0.1">'
                         f'<properties><property name="http_status" value="200"/></properties>{extra_body}</testcase>')
    return '<?xml version="1.0"?><testsuites><testsuite name="pytest">' + "".join(cases) + "</testsuite></testsuites>"


def importer_ok(name):
    return object()


def importer_missing(name):
    if name == "playwright":
        raise ImportError(name)
    return object()


def healthy(ctx):
    return [{"service": "web", "ok": True}], True, ""


def unhealthy(ctx):
    return [{"service": "web", "ok": False}], False, "web (exited, n/a, connection refused)"


class FakeRunner:
    """Records argv; writes junit.xml (and optionally collector.json) when asked to run pytest."""

    def __init__(self, pytest_rc=0, junit=None, seed_rc=0, output="pytest output", collector=None):
        self.calls = []
        self.pytest_rc = pytest_rc
        self.junit = junit
        self.seed_rc = seed_rc
        self.output = output
        self.collector = collector

    def __call__(self, argv, env=None, cwd=None):
        self.calls.append((argv, env))
        if "pytest" in argv:
            if self.junit is not None:
                Path(argv[argv.index("--junitxml") + 1]).write_text(self.junit, encoding="utf-8")
            if self.collector is not None:
                Path(env["GRDM_ACCEPT_RESULTS"]).write_text(json.dumps(self.collector), encoding="utf-8")
            return self.pytest_rc, self.output
        if "manage.py" in argv:
            return self.seed_rc, "seeded " + self.output
        return 0, ""


class AcceptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "manifest").mkdir()
        (self.root / "manifest" / "upstreams.json").write_text("{}")
        self.chromium = self.root / ".venv" / ".playwright" / "chromium-1148" / "chrome-mac" / "Chromium.app" / "Contents" / "MacOS" / "Chromium"
        self.chromium.parent.mkdir(parents=True)
        self.chromium.write_bytes(b"#!/bin/sh\n")
        self.ctx = Context(root=self.root, yes=True)
        self.ctx.env = {}

    def tearDown(self):
        self.tmp.cleanup()

    def args(self, **kw):
        base = dict(only=None, seed=False, base_url=None, headed=False)
        base.update(kw)
        return argparse.Namespace(**base)

    def run_accept(self, args, runner, importer=importer_ok, health_check=healthy):
        err, out = io.StringIO(), io.StringIO()
        with redirect_stderr(err), redirect_stdout(out):
            rc = accept.run(self.ctx, args, runner=runner, importer=importer, health_check=health_check)
        return rc, err.getvalue(), out.getvalue()

    def run_dir(self):
        runs = list((self.root / "docs" / "demo" / "runs").iterdir())
        self.assertEqual(len(runs), 1)
        return runs[0]

    # --- preconditions (exit 2 / 40) -------------------------------------------------------------

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

    def test_browser_dir_without_chromium_executable_is_usage_error(self):
        self.chromium.unlink()  # the directory tree stays: a non-empty directory is not enough
        rc, err, _ = self.run_accept(self.args(), FakeRunner())
        self.assertEqual(rc, exit_codes.USAGE)
        self.assertIn("Chromium", err)
        self.assertIn(".playwright", err)
        self.assertIsNone(accept.chromium_executable(self.root / ".venv" / ".playwright"))
        linux = self.root / ".venv" / ".playwright" / "chromium-1148" / "chrome-linux" / "chrome"
        linux.parent.mkdir(parents=True)
        linux.write_bytes(b"ELF")
        self.assertEqual(accept.chromium_executable(self.root / ".venv" / ".playwright"), linux)

    def test_integration_precheck_failure_is_40_before_pytest(self):
        runner = FakeRunner(junit=junit_all_green())
        rc, err, _ = self.run_accept(self.args(seed=True), runner, health_check=unhealthy)
        self.assertEqual(rc, exit_codes.HEALTH_FAILED)
        self.assertIn("integration precheck failed", err)
        self.assertIn("connection refused", err)
        self.assertEqual(runner.calls, [])  # neither seed nor pytest ran
        self.assertFalse((self.root / "docs" / "demo" / "runs").exists())

    def test_default_health_check_requires_compose_file(self):
        rows, ok, problem = accept.default_health_check(self.ctx)
        self.assertEqual((rows, ok), ([], False))
        self.assertIn("docker-compose.yml", problem)

    # --- results, exit 60 -------------------------------------------------------------------------

    def test_pytest_failure_maps_to_60_and_writes_results(self):
        runner = FakeRunner(pytest_rc=1, junit=JUNIT_ONE_FAILURE)
        rc, err, out = self.run_accept(self.args(base_url="http://127.0.0.1:5000"), runner)
        self.assertEqual(rc, exit_codes.ACCEPTANCE_FAILED)
        run_dir = self.run_dir()
        self.assertTrue(run_dir.name.startswith("acc-"))
        results = json.loads((run_dir / "results.json").read_text())
        self.assertEqual(results["summary"], {"passed": 1, "failed": 1, "error": 0, "skipped": 1, "total": 3})
        self.assertTrue(results["precheck"]["healthy"])
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
        self.assertTrue((run_dir / "junit.xml").exists())
        self.assertTrue((run_dir / "pytest.log").exists())
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
        collector = []
        for sid, name in accept.SCENARIOS.items():
            for case in ("success", "rejection"):
                collector.append({"nodeid": f"installer/acceptance/test_{sid.lower()}_x.py::test_{sid.lower()}_x_{case}",
                                  "id": sid, "name": name, "case": case, "status": "passed" if sid.startswith("C") else "skipped",
                                  "duration_ms": 900, "http_status": 201, "evidence": None})
        runner = FakeRunner(pytest_rc=0, junit=JUNIT_ONE_FAILURE, collector=collector)
        rc, err, _ = self.run_accept(self.args(), runner)
        self.assertEqual(rc, exit_codes.OK, err)
        results = json.loads((self.run_dir() / "results.json").read_text())
        self.assertEqual(results["summary"]["total"], 22)  # collector wins over junit.xml
        self.assertEqual(results["tests"][0]["id"], "C1")
        self.assertEqual(results["base_url"], "http://127.0.0.1:5000")  # default: no runtime/.env -> port 5000
        self.assertEqual(results["incomplete_scenarios"], [])

    def test_green_pytest_with_zero_rows_is_60(self):
        runner = FakeRunner(pytest_rc=0, junit="<testsuites><testsuite name='pytest'></testsuite></testsuites>")
        rc, err, _ = self.run_accept(self.args(), runner)
        self.assertEqual(rc, exit_codes.ACCEPTANCE_FAILED)
        self.assertIn("no result rows", err)

    def test_scenario_missing_rejection_row_is_60(self):
        junit = junit_all_green(ids=[s for s in accept.SCENARIOS if s != "C3"]) \
            .replace("</testsuite>", '<testcase classname="acceptance.test_c3_x" name="test_c3_x_success" time="0.1"/></testsuite>')
        rc, err, _ = self.run_accept(self.args(), FakeRunner(pytest_rc=0, junit=junit))
        self.assertEqual(rc, exit_codes.ACCEPTANCE_FAILED)
        self.assertIn("C3", err)
        self.assertIn("rejection", err)
        results = json.loads((self.run_dir() / "results.json").read_text())
        self.assertEqual(results["incomplete_scenarios"], ["C3"])

    def test_only_selection_limits_expected_scenarios(self):
        # --only C1 with rows for C1 only is complete; --only core with only C rows is complete
        rc, err, _ = self.run_accept(self.args(only="C1"), FakeRunner(junit=junit_all_green(ids=["C1"])))
        self.assertEqual(rc, exit_codes.OK, err)
        self.assertEqual(accept.expected_scenarios(*accept.select_tests("C1")), ["C1"])
        self.assertEqual(accept.expected_scenarios(*accept.select_tests("core")), ["C1", "C2", "C3", "C4", "C5", "C6"])
        self.assertEqual(accept.expected_scenarios(*accept.select_tests("subsystem")), ["S1", "S2", "S3", "S4", "S5"])
        self.assertEqual(accept.expected_scenarios(*accept.select_tests(None)), sorted(accept.SCENARIOS))
        rows = [{"id": "C1", "case": "success"}, {"id": "C2", "case": "success"}, {"id": "C2", "case": "rejection"}]
        self.assertEqual(accept.incomplete_scenarios(rows, ["C1", "C2", "C3"]), ["C1", "C3"])

    def test_base_url_default_reads_runtime_env_port(self):
        (self.root / "runtime").mkdir()
        (self.root / "runtime" / ".env").write_text("GRDM_PORT_WEB=5050\nGRDM_PORT_API=8000\n")
        self.assertEqual(accept.default_base_url(self.ctx), "http://127.0.0.1:5050")

    # --- seeding ----------------------------------------------------------------------------------

    def test_seed_runs_management_command_then_cleanup(self):
        runner = FakeRunner(pytest_rc=0, junit=junit_all_green())
        rc, err, _ = self.run_accept(self.args(seed=True), runner)
        self.assertEqual(rc, exit_codes.OK, err)
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

    # --- secret masking and evidence permissions (finding 6) -------------------------------------

    def _write_env(self):
        (self.root / "runtime").mkdir()
        (self.root / "runtime" / ".env").write_text(
            f"GRDM_PROFILE=core\nGRDM_PORT_WEB=5000\nPOSTGRES_PASSWORD={SECRET}\nSECRET_KEY='{SECRET}xyz'\nSHORT=ab\n")

    def _assert_no_secret_under(self, run_dir):
        for p in run_dir.rglob("*"):
            if p.is_file():
                self.assertNotIn(SECRET, p.read_text(encoding="utf-8", errors="replace"), p.name)
                self.assertEqual(stat.S_IMODE(p.stat().st_mode), 0o600, p.name)
            else:
                self.assertEqual(stat.S_IMODE(p.stat().st_mode), 0o700, p.name)
        self.assertEqual(stat.S_IMODE(run_dir.stat().st_mode), 0o700)

    def test_env_values_are_masked_in_every_evidence_file_and_output(self):
        self._write_env()
        junit = junit_all_green(extra_body=f'<failure message="password {SECRET} leaked">{SECRET}</failure>'
                                           f"<system-out>cookie osf={SECRET}</system-out>")
        collector = [{"nodeid": f"x::test_c1_x_success", "id": "C1", "name": f"Login {SECRET}", "case": "success",
                      "status": "failed", "duration_ms": 1, "http_status": None, "evidence": f"trace {SECRET}"}]
        runner = FakeRunner(pytest_rc=1, junit=junit, output=f"E   assert token={SECRET} == 401\nAuthorization: Bearer {SECRET}",
                            collector=collector)
        rc, err, out = self.run_accept(self.args(seed=True, base_url="http://127.0.0.1:5000"), runner)
        self.assertEqual(rc, exit_codes.ACCEPTANCE_FAILED)
        run_dir = self.run_dir()
        for name in ("pytest.log", "junit.xml", "collector.json", "results.json", "results.toon"):
            self.assertTrue((run_dir / name).exists(), name)
        self._assert_no_secret_under(run_dir)
        self.assertNotIn(SECRET, err)
        self.assertNotIn(SECRET, out)
        self.assertIn("***", (run_dir / "pytest.log").read_text())
        # the port and profile stay readable
        self.assertIn("http://127.0.0.1:5000", (run_dir / "results.json").read_text())

    def test_seed_failure_output_is_masked(self):
        self._write_env()
        runner = FakeRunner(seed_rc=1, output=f"django.db.utils.OperationalError: password authentication failed for {SECRET}")
        rc, err, _ = self.run_accept(self.args(seed=True), runner)
        self.assertEqual(rc, exit_codes.SERVICES_UNHEALTHY)
        self.assertIn("seed failed", err)
        self.assertNotIn(SECRET, err)

    def test_mask_text_rules(self):
        env = self.root / ".env"
        env.write_text(f"GRDM_PORT_WEB=5000\nDB_PASS={SECRET}\nFLAG=true\n")
        masked = accept.mask_env_values(f"port 5000 flag true pass {SECRET} escaped {SECRET.replace('-', '&#x2D;')}", env)
        self.assertEqual(masked, "port 5000 flag true pass *** escaped " + SECRET.replace("-", "&#x2D;"))
        self.assertIn("5000", masked)
        # token-like strings are masked even without .env
        self.assertNotIn("eyJhbGciOiJIUzI1NiJ9", accept.mask_text("jwt " + ".".join(["eyJhbGciOiJIUzI1NiJ9", "eyJzdWIiOiIxIn0", "abcdefghij"]) + "", []))
        self.assertEqual(accept.mask_text("Authorization: Bearer abcdefghijklmnop", []), "Authorization: ***")
        self.assertEqual(accept.mask_text("sha 0123456789abcdef0123456789abcdef", []), "sha ***")
        # test slugs and run ids survive
        for keep in ("artifacts/test-c4-wiki-collab-rejection-chromium", "acc-20261105T120000Z-abc123", "test_c2_create_project_rejection"):
            self.assertEqual(accept.mask_text(keep, []), keep)
        self.assertEqual(accept.mask_data({"k": [SECRET, 1, {"n": SECRET}]}, [SECRET]), {"k": ["***", 1, {"n": "***"}]})

    # --- suite location (finding 13) ------------------------------------------------------------

    def test_suite_resolves_from_installed_package_when_repo_dir_is_absent(self):
        absent = self.root / "no-such-checkout" / "acceptance"
        resolved = accept.resolve_acceptance_dir(repo_dir=absent)
        self.assertTrue((resolved / "conftest.py").is_file())
        self.assertNotEqual(resolved, absent)
        self.assertEqual(resolved.name, "acceptance")

    def test_suite_falls_back_to_repo_dir_when_package_is_missing(self):
        def no_package(name):
            raise ImportError(name)
        fallback = self.root / "checkout" / "acceptance"
        self.assertEqual(accept.resolve_acceptance_dir(repo_dir=fallback, importer=no_package), fallback)
        self.assertTrue((accept.ACCEPTANCE_DIR / "conftest.py").is_file())
        self.assertTrue((accept.ACCEPTANCE_DIR / "pytest.ini").is_file())

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

    def test_core_tests_never_create_unguarded_contexts(self):
        """SPEC-04 §3.4: every API/browser context goes through the guarded fixtures."""
        for f in accept.ACCEPTANCE_DIR.glob("test_c*.py"):
            src = f.read_text()
            self.assertNotIn("playwright.request.new_context", src, f.name)
            self.assertNotIn("browser.new_context", src, f.name)
            self.assertNotIn(".context.request.", src, f.name)
            self.assertNotIn('startswith("http://127.0.0.1', src, f.name)
        src = (accept.ACCEPTANCE_DIR / "test_c6_admin.py").read_text()
        self.assertIn("== 403", src)
        self.assertNotIn("(403, 404)", src)

    def test_cli_registers_accept(self):
        parser = cli.build_parser()
        args = parser.parse_args(["accept", "--only", "C1", "--seed", "--base-url", "http://127.0.0.1:5000"])
        self.assertIs(args._module, accept)
        self.assertEqual((args.only, args.seed, args.base_url), ("C1", True, "http://127.0.0.1:5000"))


class NetGuardTests(unittest.TestCase):
    """acceptance/netguard.py — exact-origin loopback check (finding 7, SPEC-04 §3.4)."""

    def test_accepts_only_exact_loopback_http(self):
        for url in ("http://127.0.0.1:5000/", "http://127.0.0.1/x", "http://127.0.0.1:8000/v2/users/me/?a=1#f", "HTTP://127.0.0.1:5000"):
            self.assertTrue(netguard.is_loopback_origin(url), url)

    def test_rejects_lookalikes_other_hosts_and_schemes(self):
        bad = (
            "http://127.0.0.1.evil.test:5000/", "http://127.0.0.1.:5000/", "http://localhost:5000/", "http://[::1]:5000/",
            "https://127.0.0.1:5000/", "http://127.0.0.2:5000/", "http://user:pw@127.0.0.1:5000/", "http://user@127.0.0.1/",
            "http://evil.test@127.0.0.1/", "http://127.0.0.1:99999/", "http://127.0.0.1:abc/", "ws://127.0.0.1:1234/",
            "http://0x7f000001/", "http://2130706433/", "//127.0.0.1:5000/", "127.0.0.1:5000", "", "ftp://127.0.0.1/",
            "http://127.0.0.1@evil.test/",
        )
        for url in bad:
            self.assertFalse(netguard.is_loopback_origin(url), url)
        self.assertFalse(netguard.is_loopback_origin(None))  # type: ignore[arg-type]

    def test_websocket_scheme_only_when_asked(self):
        self.assertTrue(netguard.is_loopback_origin("ws://127.0.0.1:1234/sharejs", netguard.WS_SCHEMES))
        self.assertFalse(netguard.is_loopback_origin("wss://127.0.0.1:1234/", netguard.WS_SCHEMES))
        self.assertFalse(netguard.is_loopback_origin("ws://localhost:1234/", netguard.WS_SCHEMES))
        self.assertFalse(netguard.is_loopback_origin("ws://127.0.0.1:1234/", netguard.HTTP_SCHEMES))

    def test_same_origin_is_exact(self):
        self.assertTrue(netguard.same_origin("http://127.0.0.1:7777/v1/x", "http://127.0.0.1:7777"))
        self.assertFalse(netguard.same_origin("http://127.0.0.1:7778/v1/x", "http://127.0.0.1:7777"))
        self.assertFalse(netguard.same_origin("http://127.0.0.1.evil.test:7777/", "http://127.0.0.1:7777"))
        self.assertFalse(netguard.same_origin("https://127.0.0.1:7777/", "http://127.0.0.1:7777"))
        self.assertFalse(netguard.same_origin("", "http://127.0.0.1:7777"))
        self.assertEqual(netguard.offending_urls(["http://127.0.0.1:1/", "http://example.com/"]), ["http://example.com/"])


if __name__ == "__main__":
    unittest.main()
