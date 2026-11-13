import argparse
import io
import json
import os
import re
import stat
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock
from urllib.parse import quote

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


class TotpTests(unittest.TestCase):
    """RFC 6238 appendix B (HMAC-SHA1, secret "12345678901234567890"): the 8-digit vectors end in the 6-digit codes."""
    SECRET = b"12345678901234567890".hex()  # the RFC 6238 test key, written as ASCII so no scanner reads it as a leaked secret

    def test_rfc_6238_vectors(self):
        from acceptance import totp
        for when, expected in ((59, "287082"), (1111111109, "081804"), (1111111111, "050471"), (1234567890, "005924"), (2000000000, "279037")):
            self.assertEqual(totp.code_at(self.SECRET, when), expected, when)

    def test_a_step_is_never_used_twice(self):
        """PR #10 accepts a code once per 30 s step: next_code waits for the next step instead of repeating."""
        from acceptance import totp
        totp._last_step.clear()
        now = [1111111109.0]
        slept = []
        def sleep(seconds):
            slept.append(seconds); now[0] += seconds
        first = totp.next_code(self.SECRET, clock=lambda: now[0], sleep=sleep)
        second = totp.next_code(self.SECRET, clock=lambda: now[0], sleep=sleep)
        self.assertEqual(first, "081804")
        self.assertEqual(second, totp.code_at(self.SECRET, 1111111109.0 + 30))
        self.assertNotEqual(first, second)
        self.assertEqual(len(slept), 1)
        self.assertLessEqual(slept[0], 31)


class FakeRunner:
    """Records argv; writes junit.xml (and optionally collector.json) when asked to run pytest."""

    def __init__(self, pytest_rc=0, junit=None, seed_rc=0, output="pytest output", collector=None, trace_members=None):
        self.calls = []
        self.pytest_rc = pytest_rc
        self.junit = junit
        self.seed_rc = seed_rc
        self.output = output
        self.collector = collector
        self.trace_members = trace_members  # {member name: bytes} -> artifacts/<test>/trace.zip like pytest-playwright

    def __call__(self, argv, env=None, cwd=None):
        self.calls.append((argv, env))
        if "pytest" in argv:
            if self.junit is not None:
                Path(argv[argv.index("--junitxml") + 1]).write_text(self.junit, encoding="utf-8")
            if self.collector is not None:
                Path(env["GRDM_ACCEPT_RESULTS"]).write_text(json.dumps(self.collector), encoding="utf-8")
            if self.trace_members is not None:
                run_dir = Path(argv[argv.index("--junitxml") + 1]).parent
                write_zip(run_dir / "artifacts" / "test-c1-login-rejection-chromium" / "trace.zip", self.trace_members)
            return self.pytest_rc, self.output
        if "manage.py" in argv:
            return self.seed_rc, "seeded " + self.output
        return 0, ""


def write_zip(path: Path, members: dict[str, bytes]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return path


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def trace_members(secret: str) -> dict[str, bytes]:
    """A Playwright-shaped trace: JSON-lines members plus response bodies under resources/."""
    return {
        "trace.trace": json.dumps({"type": "before", "apiName": "page.goto", "params": {"url": f"http://127.0.0.1:5000/?t={secret}"}}).encode(),
        "trace.network": (json.dumps({"type": "resource-snapshot", "snapshot": {"request": {"headers": [{"name": "Cookie", "value": f"osf={secret}"}]},
                                                                                "response": {"headers": [{"name": "Set-Cookie", "value": f"osf={secret}; Path=/"}]}}}) + "\n").encode(),
        "trace.stacks": json.dumps({"stacks": [[0, 0, 0, f"POSTGRES_PASSWORD={secret}"]]}).encode(),
        "resources/0a1b2c.html": f"<html>{secret}</html>".encode(),
        "resources/9f8e7d.dat": secret.encode() + b"\x00\x01",
        "resources/c0ffee.png": PNG,
        "screenshot.png": PNG,
    }


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
        base = dict(only=None, seed=False, base_url=None, headed=False, trace=False)
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

    def test_linux_hint_adds_libatomic_and_system_libraries(self):
        # DEMO-21: on the Ubuntu 24.04 arm64 cloud image Playwright's driver could not start without libatomic1.
        linux = accept.install_hint("linux")
        self.assertTrue(linux.startswith("sudo apt-get install -y libatomic1 && "))
        self.assertIn("playwright install chromium", linux)
        self.assertIn("playwright install-deps chromium", linux)
        self.assertEqual(accept.install_hint("darwin"), accept.INSTALL_HINT)
        self.assertNotIn("apt-get", accept.install_hint("darwin"))

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

    """--wait-scale: a slow or emulated host can stretch the suite's waits without patching it (DEMO-22 C4)."""

    def test_wait_scale_reaches_the_suite_only_when_asked(self):
        for scale, expected in ((None, None), (10.0, "10")):
            runner = FakeRunner(junit=JUNIT_ALL_PASS) if "JUNIT_ALL_PASS" in globals() else FakeRunner(junit=JUNIT_ONE_FAILURE)
            self.run_accept(self.args(base_url="http://127.0.0.1:5000", wait_scale=scale), runner)
            env = [e for a, e in runner.calls if "pytest" in a][-1]
            self.assertEqual(env.get("GRDM_ACCEPT_WAIT_SCALE"), expected)
            newest = sorted((self.root / "docs" / "demo" / "runs").iterdir(), key=lambda d: d.stat().st_mtime_ns)[-1]
            results = json.loads((newest / "results.json").read_text())
            self.assertEqual(results["wait_scale"], scale or 1.0)  # the run says which waits it used

    def test_scale_is_parsed_within_one_to_twenty_and_nothing_else(self):
        self.assertEqual(accept.wait_scale("10"), 10.0)
        self.assertEqual(accept.wait_scale("1"), 1.0)
        self.assertEqual(accept.wait_scale("2.5"), 2.5)
        for bad in ("0", "0.5", "21", "-3", "nan", "inf", "ten", ""):
            with self.assertRaises(argparse.ArgumentTypeError, msg=bad):
                accept.wait_scale(bad)

    def test_the_acceptance_suite_has_no_unscaled_wait_and_never_scales_the_convergence_budget(self):
        """Every `timeout=<n>_000` in the suite goes through scaled(); the 5 s budget (CONVERGE_*) never does."""
        suite = Path(__file__).resolve().parent.parent / "acceptance"
        raw = re.compile(r"timeout=\d+_000")
        for f in sorted(suite.glob("*.py")):
            if f.name == "selectors.py":
                continue
            for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                self.assertIsNone(raw.search(line), f"{f.name}:{n} has an unscaled wait: {line.strip()}")
                if "CONVERGE" in line and "=" in line.split("CONVERGE", 1)[1][:12]:
                    self.assertNotIn("scaled(", line, f"{f.name}:{n} scales the SPEC-04 convergence budget")

    def test_a_stray_scale_in_the_environment_neither_stretches_nor_mislabels_a_run(self):
        self.ctx.env = {"GRDM_ACCEPT_WAIT_SCALE": "20"}
        runner = FakeRunner(junit=JUNIT_ONE_FAILURE)
        self.run_accept(self.args(base_url="http://127.0.0.1:5000"), runner)
        env = [e for a, e in runner.calls if "pytest" in a][-1]
        self.assertNotIn("GRDM_ACCEPT_WAIT_SCALE", env)
        self.assertEqual(json.loads((self.run_dir() / "results.json").read_text())["wait_scale"], 1.0)

    def test_the_parent_limit_follows_the_scale_the_child_was_given(self):
        seen = []

        def fake_run(argv, **kw):
            seen.append(kw.get("timeout"))
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(accept.subprocess, "run", fake_run):
            accept.default_runner(["x"], env={})
            accept.default_runner(["x"], env={"GRDM_ACCEPT_WAIT_SCALE": "20"})
            accept.default_runner(["x"], env={"GRDM_ACCEPT_WAIT_SCALE": "21"})   # out of range counts as 1, like the suite
            accept.default_runner(["x"], env={"GRDM_ACCEPT_WAIT_SCALE": "bad"})
            accept.default_runner(["x"], env={}, timeout=5)
        self.assertEqual(seen, [1900, 38000, 1900, 1900, 5])
        self.assertGreater(38000, 30 * 60 * 20 + 1)  # the suite's stretched 36,000 s fits inside the parent's limit

    # --- results, exit 60 -------------------------------------------------------------------------

    def test_pytest_failure_maps_to_60_and_writes_results(self):
        runner = FakeRunner(pytest_rc=1, junit=JUNIT_ONE_FAILURE)
        rc, err, out = self.run_accept(self.args(base_url="http://127.0.0.1:5000"), runner)
        self.assertEqual(rc, exit_codes.ACCEPTANCE_FAILED)
        run_dir = self.run_dir()
        self.assertTrue(run_dir.name.startswith("acc-"))
        results = json.loads((run_dir / "results.json").read_text())
        self.assertEqual(results["summary"], {"passed": 1, "failed": 1, "error": 0, "skipped": 1, "total": 3, "known_external_blocked": 0})
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
        self.assertEqual(argv[argv.index("--tracing") + 1], "off")  # traces only with --trace (R2-01)
        self.assertIsNone(results["trace_quarantine"])
        self.assertEqual(results["tracing"], "off")
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
        self.assertEqual(results["summary"]["total"], 24)  # collector wins over junit.xml
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
        self.assertEqual(accept.expected_scenarios(*accept.select_tests("core")), ["C1", "C2", "C3", "C4", "C5", "C6", "C7"])
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
        self.assertEqual(len(seed_calls), 6)  # user_a, user_b, institution_member, other_institution_member, admin, cleanup
        self.assertEqual(seed_calls[0][:3], ["docker", "compose", "exec"])
        self.assertIn("web", seed_calls[0])
        self.assertIn("create_confirmed", seed_calls[0][-1])
        self.assertIn("have_email = True", seed_calls[0][-1])  # without it GRDM redirects every view to /settings/account/email
        self.assertIn("delete()", seed_calls[-1][-1])
        # pytest ran between seeding and cleanup
        order = ["seed" if "manage.py" in a else "pytest" for a, _ in runner.calls]
        self.assertEqual(order, ["seed", "seed", "seed", "seed", "seed", "pytest", "seed"])

    def test_seed_makes_admin_an_affiliated_institution_admin_and_leaves_user_a_unaffiliated(self):
        runner = FakeRunner()
        self.run_accept(self.args(seed=True), runner)
        snippets = [a[-1] for a, _ in runner.calls if "manage.py" in a][:5]
        for snippet in snippets:
            self.assertIn("u.is_superuser = False", snippet)
        user_a, user_b, member, other, admin = snippets
        self.assertIn("u.is_staff = True", admin)
        for snippet in (user_a, user_b, member, other):
            self.assertIn("u.is_staff = False", snippet)
        self.assertIn("order_by('id')[0:1]", admin)   # only the first institution
        self.assertIn("order_by('id')[0:1]", member)  # the admin's institution
        self.assertIn("order_by('id')[1:2]", other)   # only a different institution (PR #40 review r1 R1-01)
        self.assertIn("order_by('id')[0:0]", user_b)  # an affiliated user's login does not reach the dashboard
        self.assertIn("order_by('id')[0:0]", user_a)

    def _c6_success(self):
        """test_c6_admin_success imported for real, with pytest and the Playwright conftest replaced by stubs
        (neither is installed for the unit tests); the function under test is the unmodified source."""
        import importlib
        import types

        class _Mark:
            def __getattr__(self, _name):
                return lambda *a, **k: (lambda f: f)

        fake_pytest = types.ModuleType("pytest")
        fake_pytest.mark = _Mark()
        fake_conftest = types.ModuleType("acceptance.conftest")
        fake_conftest.api = lambda ctx: ctx
        fake_conftest.scaled = lambda ms: ms
        with mock.patch.dict(sys.modules, {"pytest": fake_pytest, "acceptance.conftest": fake_conftest}):
            sys.modules.pop("acceptance.test_c6_admin", None)
            module = importlib.import_module("acceptance.test_c6_admin")
            sys.modules.pop("acceptance.test_c6_admin", None)
        return module.test_c6_admin_success

    def _run_c6_against(self, listing):
        """Run C6 success on a fake admin app whose institution list is `listing(query)` -> e-mails."""
        users = {k: {"email": f"{k}@acceptance.test", "password": "x"} for k in ("admin", "a", "member", "other")}
        users["admin"]["totp_secret"] = b"12345678901234567890".hex()  # the RFC 6238 test key
        filled = []

        class Resp:
            status = 200

        class Page:
            query = ""
            url = ""
            step = 0  # the fake admin app: password -> two-factor page -> signed in

            def click(self, sel):
                self.step += 1
                self.url = "http://127.0.0.1:8001/account/login/two-factor/" if self.step == 1 else "http://127.0.0.1:8001/"

            def fill(self, sel, value):
                filled.append((sel, value))

            def goto(self, url, **_):
                self.query = url.split("?", 1)[1] if "?" in url else ""
                return Resp()

            def inner_text(self, _sel):
                return "GUID\tEmail\n" + "\n".join(listing(self.query))

            def __getattr__(self, _name):
                return lambda *a, **k: None

        self._c6_success()(Page(), lambda s: "http://127.0.0.1:8001", users["admin"], users["a"], users["member"],
                           users["other"], lambda *a: None)
        code = [v for sel, v in filled if "code" in sel]
        self.assertEqual(len(code), 1)  # the second factor was typed once, as a 6-digit code
        self.assertRegex(code[0], r"^\d{6}$")

    def test_c6_fails_when_the_institution_filter_is_removed(self):
        everyone_affiliated = ["member@acceptance.test", "other@acceptance.test"]
        def leaky(query):  # every affiliated user, whatever the admin's institution
            return [e for e in everyone_affiliated if not query or e.split("@")[0] in query]
        with self.assertRaisesRegex(AssertionError, "another institution"):
            self._run_c6_against(leaky)

    def test_c6_passes_when_only_the_admins_institution_is_listed(self):
        def filtered(query):
            return [e for e in ["member@acceptance.test"] if not query or e.split("@")[0] in query]
        self._run_c6_against(filtered)

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

    def _assert_zip_has_no_secret(self, zip_path: Path):
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            for name in names:
                data = zf.read(name)
                self.assertNotIn(SECRET.encode(), data, f"{zip_path.name}:{name}")
                self.assertNotIn(json.dumps(SECRET)[1:-1].encode(), data, f"{zip_path.name}:{name}")
        return names

    def test_sanitize_run_dir_masks_zip_members_and_every_text_file(self):
        """R2-01: a .env value inside pytest.log and inside a trace ZIP member must be gone after sanitize."""
        run_dir = self.root / "docs" / "demo" / "runs" / "acc-x"
        run_dir.mkdir(parents=True)
        (run_dir / "pytest.log").write_text(f"E  assert cookie osf={SECRET}\n")
        nested = run_dir / "artifacts" / "test-c1-login-rejection-chromium"
        nested.mkdir(parents=True)
        (nested / "network.har").write_text(json.dumps({"log": {"entries": [{"request": {"headers": [{"name": "Cookie", "value": f"osf={SECRET}"}]}}]}}))
        (nested / "notes.md").write_text(f"saw {SECRET}\n")
        (nested / "context.json").write_text(json.dumps({"cookies": [{"value": SECRET}]}))
        (nested / "console.txt").write_text(f"{SECRET}\n")
        (nested / "screenshot.png").write_bytes(PNG)
        zip_path = write_zip(nested / "trace.zip", trace_members(SECRET))
        with zipfile.ZipFile(zip_path) as zf:  # precondition: the raw trace leaks
            self.assertIn(SECRET.encode(), zf.read("trace.network"))

        accept.sanitize_run_dir(run_dir, [SECRET])

        self._assert_no_secret_under(run_dir)  # text files, permissions
        names = self._assert_zip_has_no_secret(zip_path)
        self.assertIn("trace.network", names)
        self.assertIn("trace.trace", names)
        self.assertIn("trace.stacks", names)
        self.assertIn("resources/c0ffee.png", names)   # image bodies stay
        self.assertIn("screenshot.png", names)
        self.assertNotIn("resources/0a1b2c.html", names)  # response bodies are dropped
        self.assertNotIn("resources/9f8e7d.dat", names)
        with zipfile.ZipFile(zip_path) as zf:
            self.assertIn(b"***", zf.read("trace.network"))
            self.assertIn(b"page.goto", zf.read("trace.trace"))  # structure survives, value masked
            self.assertEqual(zf.read("screenshot.png"), PNG)
        self.assertEqual(stat.S_IMODE(zip_path.stat().st_mode), 0o600)
        self.assertEqual((nested / "screenshot.png").read_bytes(), PNG)
        for name in ("network.har", "notes.md", "context.json", "console.txt"):
            self.assertIn("***", (nested / name).read_text(), name)
        # a corrupt archive cannot be sanitized and is removed rather than kept
        bad = nested / "broken.zip"
        bad.write_bytes(b"not a zip")
        self.assertEqual(accept.sanitize_zip(bad, [SECRET]), {"kept": 0, "dropped": -1})
        self.assertFalse(bad.exists())

    def test_sanitize_zip_member_rules(self):
        self.assertIsNone(accept.sanitize_zip_member("resources/a.html", b"<html>x</html>", []))
        self.assertIsNone(accept.sanitize_zip_member("resources/a.json", b"{}", []))
        self.assertEqual(accept.sanitize_zip_member("resources/a.png", PNG, []), PNG)
        self.assertEqual(accept.sanitize_zip_member("resources/noext", b"\xff\xd8\xff\xe0jpeg", []), b"\xff\xd8\xff\xe0jpeg")
        self.assertEqual(accept.sanitize_zip_member("trace.network", f"x={SECRET}".encode(), [SECRET]), b"x=***")
        self.assertIsNone(accept.sanitize_zip_member("blob.bin", b"\x00\x01" + SECRET.encode(), [SECRET]))  # unknown binary: dropped

    def test_trace_flag_quarantines_zips_outside_the_run_dir(self):
        """R2-01 quarantine design: --trace keeps traces under runtime/reports/quarantine/<run_id>/, never in docs/demo/runs/."""
        self._write_env()
        runner = FakeRunner(pytest_rc=1, junit=JUNIT_ONE_FAILURE, trace_members=trace_members(SECRET))
        rc, err, _ = self.run_accept(self.args(trace=True, base_url="http://127.0.0.1:5000"), runner)
        self.assertEqual(rc, exit_codes.ACCEPTANCE_FAILED)
        argv, _ = runner.calls[-1]
        self.assertEqual(argv[argv.index("--tracing") + 1], "retain-on-failure")
        run_dir = self.run_dir()
        self.assertEqual(list(run_dir.rglob("*.zip")), [])
        self._assert_no_secret_under(run_dir)
        quarantine = self.root / "runtime" / "reports" / "quarantine" / run_dir.name
        zips = list(quarantine.rglob("*.zip"))
        self.assertEqual([z.relative_to(quarantine).as_posix() for z in zips], ["artifacts/test-c1-login-rejection-chromium/trace.zip"])
        self.assertEqual(stat.S_IMODE(quarantine.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(zips[0].stat().st_mode), 0o600)
        results = json.loads((run_dir / "results.json").read_text())
        self.assertEqual(results["tracing"], "retain-on-failure")
        q = results["trace_quarantine"]
        self.assertEqual(q["dir"], f"runtime/reports/quarantine/{run_dir.name}")
        self.assertEqual(q["files"], ["artifacts/test-c1-login-rejection-chromium/trace.zip"])
        self.assertIn("not sanitized evidence", q["note"])
        self.assertNotIn(SECRET, err)
        # runtime/ is git-ignored, so the quarantine never reaches a commit
        self.assertIn("runtime/", (Path(__file__).resolve().parents[2] / ".gitignore").read_text())

    def test_zip_left_in_run_dir_is_sanitized_even_if_quarantine_is_skipped(self):
        run_dir = self.root / "docs" / "demo" / "runs" / "acc-y"
        zip_path = write_zip(run_dir / "artifacts" / "t" / "trace.zip", trace_members(SECRET))
        accept.sanitize_run_dir(run_dir, [SECRET])
        self._assert_zip_has_no_secret(zip_path)

    def test_seed_failure_output_is_masked(self):
        self._write_env()
        runner = FakeRunner(seed_rc=1, output=f"django.db.utils.OperationalError: password authentication failed for {SECRET}")
        rc, err, _ = self.run_accept(self.args(seed=True), runner)
        self.assertEqual(rc, exit_codes.SERVICES_UNHEALTHY)
        self.assertIn("seed failed", err)
        self.assertNotIn(SECRET, err)

    def test_seeded_credentials_are_masked_on_failure_in_pytest_junit_and_collector(self):
        """PR #35 review r1 R1-01: a failing test prints the user fixture, so the identities must be masked."""
        self._write_env()
        leaks: list[str] = []

        class Leaky(FakeRunner):
            def __call__(inner, argv, env=None, cwd=None):
                if "pytest" in argv:
                    email = env["GRDM_ACCEPT_USER_A"]
                    password = next(re.search(r"password='([^']+)'", a[-1]).group(1) for a, _ in inner.calls if "create_confirmed" in a[-1])
                    leaks[:] = [email, email.lower(), quote(email, safe=""), password]
                    fixture = f"user_a = {{'email': '{email}', 'password': '{email}'}}"
                    extra = f"{fixture} {email.lower()} {quote(email, safe='')} {password}"
                    inner.output = f"E   assert 200 == 401\n{extra}"
                    inner.junit = junit_all_green(ids=["C1"], extra_body=f'<failure message="{email}">{extra}</failure>')
                    inner.collector = [{"nodeid": "x::test_c1_x_success", "id": "C1", "name": extra, "case": "success",
                                        "status": "failed", "duration_ms": 1, "http_status": None, "evidence": email}]
                return super().__call__(argv, env=env, cwd=cwd)

        rc, err, out = self.run_accept(self.args(seed=True), Leaky(pytest_rc=1))
        self.assertEqual(rc, exit_codes.ACCEPTANCE_FAILED)
        self.assertEqual(len(leaks), 4)
        run_dir = self.run_dir()
        for name in ("pytest.log", "junit.xml", "collector.json", "results.json", "results.toon"):
            text = (run_dir / name).read_text(encoding="utf-8")
            self.assertNotRegex(text, r"(?i)(?:@|%40)acceptance\.test", name)
            for value in leaks:
                self.assertNotIn(value, text, name)
        for value in leaks:
            self.assertNotIn(value, err + out)
        self.assertIn("'password': '***", (run_dir / "pytest.log").read_text(encoding="utf-8"))

    def test_seed_error_masks_the_identity_and_the_osf_password(self):
        calls: list[str] = []

        def failing(argv, env=None, cwd=None):
            calls.append(argv[-1])
            return 1, f"Traceback: {argv[-1]}"

        rc, err, _ = self.run_accept(self.args(seed=True), failing)
        self.assertEqual(rc, exit_codes.SERVICES_UNHEALTHY)
        email, osf_password = re.search(r"username='([^']+)', password='([^']+)'", calls[0]).groups()
        self.assertIn("seed failed", err)
        self.assertNotIn(email, err)
        self.assertNotIn(osf_password, err)

    def test_only_the_admin_is_enrolled_for_two_factor_and_its_secret_is_a_masked_run_secret(self):
        """RDM-osf.io-dev2027 PR #10: the admin app asks for TOTP after the password; the seeded administrator is
        confirmed beforehand with a random secret, and nobody else gets one."""
        users = accept.seed_users("acc-1")
        for key, user in users.items():
            self.assertEqual("totp_secret" in user, key == "admin_user", key)
        secret = users["admin_user"]["totp_secret"]
        self.assertRegex(secret, r"^[0-9a-f]{40}$")
        self.assertNotEqual(secret, accept.seed_users("acc-1")["admin_user"]["totp_secret"])
        self.assertIn(secret, accept.seed_secret_values(users))
        enrol = accept.SEED_SNIPPET.format(email="a@b.test", osf_password="pw", fullname="n", admin=True, institutions="0:1",
                                           two_factor=accept.TWO_FACTOR_SNIPPET.format(totp_secret=secret))
        self.assertIn("a.is_confirmed = True", enrol)
        self.assertIn(f"a.totp_secret = '{secret}'", enrol)
        plain = accept.SEED_SNIPPET.format(email="a@b.test", osf_password="pw", fullname="n", admin=False, institutions="0:0", two_factor="")
        self.assertNotIn("twofactor", plain)
        compile(enrol, "<seed>", "exec")  # it is a valid one-line Python program for `manage.py shell -c`

    def test_the_admin_secret_reaches_pytest_only_through_the_environment(self):
        runner = FakeRunner(pytest_rc=0, junit=junit_all_green())
        self.run_accept(self.args(seed=True), runner)
        env = [e for a, e in runner.calls if "pytest" in a][-1]
        self.assertRegex(env["GRDM_ACCEPT_ADMIN_TOTP_SECRET"], r"^[0-9a-f]{40}$")
        seed = [a for a, _ in runner.calls if "manage.py" in a]
        # the secret is also in the seed snippet of the administrator only (the run's other users have none)
        self.assertEqual(sum(env["GRDM_ACCEPT_ADMIN_TOTP_SECRET"] in " ".join(a) for a in seed), 1)

    def test_osf_password_is_random_not_derived_from_the_identity(self):
        first, second = accept.seed_users("acc-1"), accept.seed_users("acc-1")
        self.assertNotEqual(first["user_a"]["osf_password"], second["user_a"]["osf_password"])
        self.assertNotEqual(first["user_a"]["osf_password"], first["user_b"]["osf_password"])
        self.assertNotIn(first["user_a"]["email"], first["user_a"]["osf_password"])

    def test_cleanup_matches_the_lower_cased_username_osf_stores(self):
        """OSF lower-cases usernames, so a case-sensitive match on the run id deleted nothing (33 accounts left)."""
        runner = FakeRunner(pytest_rc=0, junit=junit_all_green())
        self.run_accept(self.args(seed=True), runner)
        self.assertIn("username__icontains=", [a for a, _ in runner.calls if "manage.py" in a][-1][-1])

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
        self.assertEqual((args.only, args.seed, args.base_url, args.trace), ("C1", True, "http://127.0.0.1:5000", False))
        self.assertTrue(parser.parse_args(["accept", "--trace"]).trace)


class NetGuardTests(unittest.TestCase):
    """acceptance/netguard.py — exact-origin loopback check (finding 7, SPEC-04 §3.4)."""

    def test_known_external_asset_matches_only_the_listed_host_path_and_type(self):
        known = netguard.known_external_asset_host
        self.assertEqual(known("https://cdnjs.cloudflare.com/ajax/libs/es6-shim/0.35.0/es6-shim.min.js", "script"), "cdnjs.cloudflare.com")
        self.assertEqual(known("http://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.1/MathJax.js?config=x", "script"), "cdnjs.cloudflare.com")
        self.assertEqual(known("https://cdnjs.cloudflare.com/ajax/libs/zxcvbn/4.4.2/zxcvbn.js", "script"), "cdnjs.cloudflare.com")  # ember's index.html
        for url, kind in (("https://cdnjs.cloudflare.com/ajax/libs/zxcvbn/4.4.2/zxcvbn.js", "fetch"), ("https://cdnjs.cloudflare.com/ajax/libs/zxcvbn/latest/zxcvbn.js", "script"),
                          ("https://cdnjs.cloudflare.com/ajax/libs/zxcvbn/4.4.2/other.js", "script")):
            self.assertIsNone(known(url, kind), url)
        self.assertEqual(known("https://fonts.googleapis.com/css?family=Open+Sans:400", "stylesheet"), "fonts.googleapis.com")
        self.assertEqual(known("https://secure.gravatar.com/avatar/0123456789abcdef0123456789abcdef?d=identicon", "image"), "secure.gravatar.com")
        self.assertEqual(known("https://secure.gravatar.com/avatar/placeholder?d=identicon&s=20", "image"), "secure.gravatar.com")
        self.assertEqual(known("https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined", "stylesheet"), "fonts.googleapis.com")
        for url, kind in (
            ("https://cdnjs.cloudflare.com/ajax/libs/jquery/3.2.1/jquery.min.js", "script"),      # another library
            ("https://cdnjs.cloudflare.com/ajax/libs/es6-shim/0.35.0/x.js", "document"),          # a navigation is not an asset
            ("https://cdnjs.cloudflare.com/ajax/libs/es6-shim/0.35.0/x.js", "fetch"),             # data can leave by fetch
            ("https://fonts.googleapis.com/css", "script"),                                       # listed host, wrong type
            ("https://cdnjs.cloudflare.com.evil.test/ajax/libs/es6-shim/x.js", "script"),         # suffix trick
            ("https://user@cdnjs.cloudflare.com/ajax/libs/es6-shim/x.js", "script"),              # credentials
            ("https://cdnjs.cloudflare.com:8443/ajax/libs/es6-shim/x.js", "script"),              # another port
            ("wss://secure.gravatar.com/avatar/x", "image"),                                      # another scheme
            ("https://example.com/", "image"),
        ):
            self.assertIsNone(known(url, kind), (url, kind))
        self.assertIsNone(known(None, "script"))  # type: ignore[arg-type]

    def test_known_external_asset_refuses_lookalike_and_unknown_paths(self):
        """PR #35 review r1 R1-02: a path is known only as a whole; the rest of the host still fails the test."""
        known = netguard.known_external_asset_host
        for url, kind in (
            ("https://fonts.googleapis.com/css-unlisted", "stylesheet"),
            ("https://fonts.googleapis.com/css3", "stylesheet"),
            ("https://fonts.googleapis.com/css/", "stylesheet"),
            ("https://fonts.googleapis.com/css/evil", "stylesheet"),
            ("https://fonts.googleapis.com/CSS", "stylesheet"),
            ("https://cdnjs.cloudflare.com/ajax/libs/es6-shim/0.35.0/evil.js", "script"),
            ("https://cdnjs.cloudflare.com/ajax/libs/es6-shim/latest/es6-shim.min.js", "script"),
            ("https://cdnjs.cloudflare.com/ajax/libs/es6-shim/0.35.0/../../jquery/3.2.1/jquery.min.js", "script"),
            ("https://cdnjs.cloudflare.com/ajax/libs/es6-shim/0.35.0/es6-shim.min.js/x", "script"),
            ("https://cdnjs.cloudflare.com/ajax/libs/es6-shim-evil/0.35.0/es6-shim.min.js", "script"),
            ("https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.2/extensions/evil.js", "script"),
            ("https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.2/MathJax.js.map", "script"),
            ("https://secure.gravatar.com/avatar/", "image"),
            ("https://secure.gravatar.com/avatar/abc", "image"),
            ("https://secure.gravatar.com/avatar/0123456789abcdef0123456789abcdef/x", "image"),
            ("https://secure.gravatar.com/avatarx/0123456789abcdef0123456789abcdef", "image"),
        ):
            self.assertIsNone(known(url, kind), url)
        real = "https://cdnjs.cloudflare.com/ajax/libs/es6-shim/0.35.0/es6-shim.min.js"
        self.assertEqual(known(real, "script"), "cdnjs.cloudflare.com")
        for kind in ("document", "fetch", "xhr", "websocket", "eventsource", "other"):
            self.assertIsNone(known(real, kind), kind)
            self.assertIsNone(known("https://secure.gravatar.com/avatar/placeholder", kind), kind)
            self.assertIsNone(known("https://fonts.googleapis.com/css", kind), kind)
        self.assertIsNone(known("wss://fonts.googleapis.com/css", "stylesheet"))
        self.assertIsNone(known("https://api.test.example/v2/users/me/", "fetch"))

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

    # --- redirects (R2-02) --------------------------------------------------------------------------

    def test_forced_redirect_kwargs_rejects_overrides(self):
        self.assertEqual(netguard.forced_redirect_kwargs({}), {"max_redirects": 0})
        self.assertEqual(netguard.forced_redirect_kwargs({"max_redirects": 0, "headers": {"a": "b"}}), {"max_redirects": 0, "headers": {"a": "b"}})
        self.assertEqual(netguard.forced_redirect_kwargs({"max_redirects": None}), {"max_redirects": 0})
        for bad in (1, 20, -1):
            with self.assertRaises(ValueError):
                netguard.forced_redirect_kwargs({"max_redirects": bad})

    def test_redirect_target_resolves_location_against_answered_url(self):
        self.assertEqual(netguard.redirect_target("http://127.0.0.1:5000/login", 302, {"location": "/dashboard"}), "http://127.0.0.1:5000/dashboard")
        self.assertEqual(netguard.redirect_target("http://127.0.0.1:5000/login", 302, {"Location": "http://evil.test/"}), "http://evil.test/")
        self.assertEqual(netguard.redirect_target("http://127.0.0.1:5000/a/b", 301, {"location": "../c"}), "http://127.0.0.1:5000/c")
        self.assertEqual(netguard.redirect_target("http://127.0.0.1:5000/a", 302, {"location": "//evil.test/x"}), "http://evil.test/x")
        self.assertIsNone(netguard.redirect_target("http://127.0.0.1:5000/", 200, {"location": "/x"}))
        self.assertIsNone(netguard.redirect_target("http://127.0.0.1:5000/", 302, {}))
        self.assertIsNone(netguard.redirect_target("http://127.0.0.1:5000/", 302, None))
        self.assertIsNone(netguard.redirect_target("http://127.0.0.1:5000/", 304, {"location": "/x"}))

    def test_redirect_follow_up_method_and_body(self):
        self.assertEqual(netguard.redirect_follow_up("post", 302, {"data": "x", "headers": {"h": 1}, "max_redirects": 0}),
                         ("get", {"headers": {"h": 1}, "max_redirects": 0}))
        self.assertEqual(netguard.redirect_follow_up("post", 307, {"data": "x", "max_redirects": 0}), ("post", {"data": "x", "max_redirects": 0}))
        self.assertEqual(netguard.redirect_follow_up("put", 308, {"form": {"a": 1}}), ("put", {"form": {"a": 1}}))
        self.assertEqual(netguard.redirect_follow_up("post", 303, {"multipart": {}}), ("get", {}))
        self.assertEqual(netguard.MAX_REDIRECT_HOPS, 5)
        self.assertIn("1.48", netguard.WEBSOCKET_ROUTE_REQUIREMENT)


try:
    import pytest as _pytest  # the conftest imports pytest; the unit tests below need the venv with [accept]
    from acceptance import conftest as _conftest
except ImportError:  # pragma: no cover - system python without pytest
    _pytest = _conftest = None


class FakeResponse:
    def __init__(self, url, status=200, headers=None):
        self.url, self.status, self.headers = url, status, headers or {}


class FakeRequestContext:
    """Scripted APIRequestContext: answers in order, records every (verb, url, kwargs) it was asked."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def _answer(self, verb, url, **kwargs):
        self.calls.append((verb, url, kwargs))
        return self.responses.pop(0)

    def get(self, url, **kw):
        return self._answer("get", url, **kw)

    def post(self, url, **kw):
        return self._answer("post", url, **kw)


class FakeBrowserContext:
    def __init__(self, websocket_routing=True):
        self.routes, self.ws_routes, self.handlers, self.pages = [], [], [], []
        if websocket_routing:
            self.route_web_socket = lambda pattern, handler: self.ws_routes.append((pattern, handler))

    def route(self, pattern, handler):
        self.routes.append((pattern, handler))

    def on(self, event, handler):
        self.handlers.append(event)


@unittest.skipIf(_conftest is None, "pytest/acceptance conftest not importable in this interpreter (use .venv with [accept])")
class GuardedRequestTests(unittest.TestCase):
    """acceptance/conftest.py GuardedRequest and guard_context (R2-02)."""

    LOCAL = "http://127.0.0.1:8000/v2/"

    def guarded(self, responses):
        rc = FakeRequestContext(responses)
        return rc, _conftest.GuardedRequest(rc, offenders=[])

    def test_max_redirects_override_is_a_value_error_and_nothing_is_sent(self):
        rc, g = self.guarded([FakeResponse(self.LOCAL)])
        with self.assertRaises(ValueError):
            g.get(self.LOCAL, max_redirects=20)
        self.assertEqual(rc.calls, [])

    def test_max_redirects_is_forced_to_zero_on_every_call(self):
        rc, g = self.guarded([FakeResponse(self.LOCAL, 200)])
        resp = g.get(self.LOCAL, headers={"Accept": "x"})
        self.assertEqual(resp.status, 200)
        self.assertEqual(rc.calls, [("get", self.LOCAL, {"headers": {"Accept": "x"}, "max_redirects": 0})])

    def test_redirect_to_external_host_fails_before_the_hop_is_sent(self):
        rc, g = self.guarded([FakeResponse(self.LOCAL + "login", 302, {"location": "https://cas.example.org/login"}),
                              FakeResponse("https://cas.example.org/login", 200)])
        with self.assertRaises(_pytest.fail.Exception) as cm:
            g.get(self.LOCAL + "login")
        self.assertIn("cas.example.org", str(cm.exception))
        self.assertEqual(len(rc.calls), 1)  # the external hop was never requested
        self.assertEqual(g._offenders, ["https://cas.example.org/login"])

    def test_redirect_to_lookalike_or_other_loopback_scheme_fails(self):
        for location in ("http://localhost:8000/x", "http://127.0.0.1.evil.test/x", "https://127.0.0.1:8000/x", "//evil.test/x"):
            rc, g = self.guarded([FakeResponse(self.LOCAL, 301, {"Location": location}), FakeResponse(self.LOCAL)])
            with self.assertRaises(_pytest.fail.Exception):
                g.get(self.LOCAL)
            self.assertEqual(len(rc.calls), 1, location)

    def test_redirect_to_loopback_is_followed_with_each_hop_checked(self):
        rc, g = self.guarded([FakeResponse(self.LOCAL + "login", 302, {"location": "/v2/dashboard"}),
                              FakeResponse("http://127.0.0.1:8000/v2/dashboard", 307, {"location": "http://127.0.0.1:5000/home"}),
                              FakeResponse("http://127.0.0.1:5000/home", 200)])
        resp = g.post(self.LOCAL + "login", data="a=b")
        self.assertEqual((resp.status, resp.url), (200, "http://127.0.0.1:5000/home"))
        self.assertEqual([(v, u) for v, u, _ in rc.calls],
                         [("post", self.LOCAL + "login"), ("get", "http://127.0.0.1:8000/v2/dashboard"), ("get", "http://127.0.0.1:5000/home")])
        self.assertTrue(all(kw["max_redirects"] == 0 for _, _, kw in rc.calls))
        self.assertNotIn("data", rc.calls[1][2])  # 302 -> GET without body
        self.assertEqual(g._offenders, [])

    def test_more_than_five_hops_fails(self):
        responses = [FakeResponse(self.LOCAL, 302, {"location": f"/hop{i}"}) for i in range(7)] + [FakeResponse(self.LOCAL)]
        rc, g = self.guarded(responses)
        with self.assertRaises(_pytest.fail.Exception) as cm:
            g.get(self.LOCAL)
        self.assertIn("redirect hops", str(cm.exception))
        self.assertEqual(len(rc.calls), _conftest.MAX_REDIRECT_HOPS + 1)

    def test_answer_from_another_origin_fails(self):
        rc, g = self.guarded([FakeResponse("http://localhost:8000/v2/", 200)])
        with self.assertRaises(_pytest.fail.Exception):
            g.get(self.LOCAL)

    def test_guard_context_fails_closed_without_websocket_routing(self):
        ctx = FakeBrowserContext(websocket_routing=False)
        with self.assertRaises(RuntimeError) as cm:
            _conftest.guard_context(ctx, offenders=[])
        self.assertIn("1.48", str(cm.exception))
        self.assertIn("route_web_socket", str(cm.exception))
        self.assertEqual(ctx.routes, [])  # nothing half-installed

    def test_guard_context_installs_http_and_websocket_routes(self):
        ctx = FakeBrowserContext()
        _conftest.guard_context(ctx, offenders=[])
        self.assertEqual([p for p, _ in ctx.routes], ["**/*"])
        self.assertEqual([p for p, _ in ctx.ws_routes], ["**/*"])
        self.assertIn("serviceworker", ctx.handlers)
        self.assertIn("page", ctx.handlers)

    def test_pyproject_requires_playwright_with_websocket_routing(self):
        text = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()
        self.assertIn('"playwright>=1.48"', text)
        self.assertIn('"pytest-playwright>=0.6"', text)


if __name__ == "__main__":
    unittest.main()
