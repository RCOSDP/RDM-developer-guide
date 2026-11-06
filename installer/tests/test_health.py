import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from grdm_dev import exit_codes, health
from grdm_dev.context import Context

COMPOSE = {
    "services": {
        "web": {"image": "grdm-dev/osf.io:abc", "ports": ["127.0.0.1:5000:5000"]},
        "api": {"image": "grdm-dev/osf.io:abc", "ports": ["127.0.0.1:8000:8000"]},
        "postgres": {"image": "postgres:9.6"},
    }
}

def ps_row(service, host_ip="127.0.0.1"):
    row = {"Service": service, "Name": f"grdm-dev-{service}-1", "State": "running", "Health": "healthy", "Publishers": []}
    if service in ("web", "api"):
        port = 5000 if service == "web" else 8000
        row["Publishers"] = [{"URL": host_ip, "TargetPort": port, "PublishedPort": port, "Protocol": "tcp"}]
    return row


PS_OK = "\n".join(json.dumps(ps_row(s)) for s in ("web", "api", "postgres"))
PS_PUBLISH_ANY = json.dumps([ps_row("web", host_ip="0.0.0.0"), ps_row("api"), ps_row("postgres")])


def inspect_ports(name, host_ip="127.0.0.1"):
    port = {"grdm-dev-web-1": "5000", "grdm-dev-api-1": "8000"}.get(name)
    if not port:
        return "{}"
    return json.dumps({f"{port}/tcp": [{"HostIp": host_ip, "HostPort": port}]})

PS_BAD = json.dumps([
    {"Service": "web", "State": "running", "Health": "healthy"},
    {"Service": "api", "State": "exited", "Health": ""},
    {"Service": "postgres", "State": "running", "Health": "unhealthy"},
])

LSOF_BAD = """COMMAND     PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
com.docke  4242 user   55u  IPv4 0x1  0t0  TCP *:5000 (LISTEN)
com.docke  4242 user   56u  IPv6 0x2  0t0  TCP [::]:8000 (LISTEN)
rapportd    512 user    4u  IPv4 0x3  0t0  TCP *:49152 (LISTEN)
"""
LSOF_OK = """COMMAND     PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
com.docke  4242 user   55u  IPv4 0x1  0t0  TCP 127.0.0.1:5000 (LISTEN)
com.docke  4242 user   56u  IPv4 0x2  0t0  TCP 127.0.0.1:8000 (LISTEN)
rapportd    512 user    4u  IPv4 0x3  0t0  TCP *:49152 (LISTEN)
"""
# macOS AirPlay Receiver (ControlCenter) binds *:5000 beside our loopback-only web (real install run 16)
LSOF_FOREIGN = """COMMAND     PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
ControlCe   777 user   10u  IPv4 0x9  0t0  TCP *:5000 (LISTEN)
com.docke  4242 user   55u  IPv4 0x1  0t0  TCP 127.0.0.1:5000 (LISTEN)
com.docke  4242 user   56u  IPv4 0x2  0t0  TCP 127.0.0.1:8000 (LISTEN)
"""
SS_BAD = """State  Recv-Q Send-Q Local Address:Port  Peer Address:Port Process
LISTEN 0      4096   0.0.0.0:5000        0.0.0.0:*     users:(("docker-proxy",pid=99,fd=4))
LISTEN 0      4096   127.0.0.1:8000      0.0.0.0:*     users:(("docker-proxy",pid=98,fd=4))
LISTEN 0      128    0.0.0.0:22          0.0.0.0:*     users:(("sshd",pid=1,fd=3))
"""
# unprivileged `ss -ltnp`: a root-owned docker-proxy socket shows no process field at all
SS_NO_PROCESS = """State  Recv-Q Send-Q Local Address:Port  Peer Address:Port Process
LISTEN 0      4096   0.0.0.0:5000        0.0.0.0:*
LISTEN 0      4096   127.0.0.1:8000      0.0.0.0:*
LISTEN 0      128    0.0.0.0:22          0.0.0.0:*
"""
SS_OK = """State  Recv-Q Send-Q Local Address:Port  Peer Address:Port Process
LISTEN 0      4096   127.0.0.1:5000      0.0.0.0:*
LISTEN 0      4096   127.0.0.1:8000      0.0.0.0:*
LISTEN 0      128    0.0.0.0:22          0.0.0.0:*     users:(("sshd",pid=1,fd=3))
"""


def make_runner(ps_output, sockets_output="", ps_rc=0, inspect_host_ip="127.0.0.1", inspect_rc=0):
    calls = []

    def runner(argv):
        calls.append(argv)
        if argv[:2] == ["docker", "compose"]:
            return ps_rc, ps_output
        if argv[:2] == ["docker", "inspect"]:
            return inspect_rc, inspect_ports(argv[-1], inspect_host_ip) if inspect_rc == 0 else ""
        if argv[0] in ("lsof", "ss"):
            return 0, sockets_output
        return 1, ""

    runner.calls = calls
    return runner


def ok_prober(url):
    return True, "HTTP 302"


class HealthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "runtime").mkdir()
        (self.root / "runtime" / "docker-compose.yml").write_text(json.dumps(COMPOSE))
        self.ctx = Context(root=self.root, stdin_is_tty=False)
        self.out, self.err = io.StringIO(), io.StringIO()

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, network, runner, prober=ok_prober, system="Darwin"):
        with redirect_stdout(self.out), redirect_stderr(self.err):
            return health.run(self.ctx, argparse.Namespace(network=network), runner=runner, prober=prober, system=system)

    def test_all_healthy_is_0_and_probes_http_ports(self):
        probed = []

        def prober(url):
            probed.append(url)
            return True, "HTTP 200"

        self.assertEqual(self.run_cmd(False, make_runner(PS_OK), prober), exit_codes.OK)
        self.assertEqual(sorted(probed), ["http://127.0.0.1:5000/login/", "http://127.0.0.1:8000/"])  # web probed at /login/ (HTTP_PATHS)
        self.assertIn("services[3]", self.out.getvalue())

    def test_unhealthy_service_is_40(self):
        self.assertEqual(self.run_cmd(False, make_runner(PS_BAD)), exit_codes.HEALTH_FAILED)
        self.assertIn("api", self.err.getvalue())
        self.assertIn("postgres", self.err.getvalue())

    def test_one_shot_service_is_healthy_once_exited_0_and_unhealthy_otherwise(self):
        """A `restart: "no"` service (wiki_assets, SPEC-01 overlay_of) runs to completion: `exited` with code 0 is ok."""
        compose = json.loads(json.dumps(COMPOSE))
        compose["services"]["wiki_assets"] = {"image": "grdm-dev/wiki-frontend:aaaaaaaaaaaa-bbbbbbbbbbbb", "restart": "no"}
        (self.root / "runtime" / "docker-compose.yml").write_text(json.dumps(compose))
        done = dict(ps_row("wiki_assets"), State="exited", Health="", ExitCode=0)
        rows = [ps_row(s) for s in ("web", "api", "postgres")] + [done]
        self.assertEqual(self.run_cmd(False, make_runner(json.dumps(rows))), exit_codes.OK)
        report = json.loads((self.root / "runtime" / "reports" / "health_latest.json").read_text())
        wa = next(r for r in report["services"] if r["service"] == "wiki_assets")
        self.assertEqual((wa["state"], wa["health"], wa["ok"]), ("exited", "completed", True))
        # a failed one-shot (non-zero exit) or one still running is not healthy
        no_code = {k: v for k, v in done.items() if k != "ExitCode"}
        for bad in (dict(done, ExitCode=1), dict(done, State="running", ExitCode=None), dict(done, ExitCode=None), no_code):
            rows = [ps_row(s) for s in ("web", "api", "postgres")] + [bad]
            self.assertEqual(self.run_cmd(False, make_runner(json.dumps(rows))), exit_codes.HEALTH_FAILED)
            self.assertIn("wiki_assets", self.err.getvalue())
        # an ordinary service that exited stays unhealthy
        rows = [dict(ps_row("web"), State="exited", ExitCode=0), ps_row("api"), ps_row("postgres"), done]
        self.assertEqual(self.run_cmd(False, make_runner(json.dumps(rows))), exit_codes.HEALTH_FAILED)

    def test_http_probe_failure_is_40(self):
        rc = self.run_cmd(False, make_runner(PS_OK), prober=lambda url: (False, "connection refused"))
        self.assertEqual(rc, exit_codes.HEALTH_FAILED)

    def test_network_non_loopback_docker_port_is_40(self):
        runner = make_runner(PS_OK, LSOF_BAD)
        self.assertEqual(self.run_cmd(True, runner), exit_codes.HEALTH_FAILED)
        self.assertIn(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"], runner.calls)
        self.assertIn("5000", self.err.getvalue())
        self.assertIn("not loopback", self.err.getvalue())

    def test_network_loopback_only_is_0_and_ignores_non_docker(self):
        self.assertEqual(self.run_cmd(True, make_runner(PS_OK, LSOF_OK)), exit_codes.OK)
        self.assertIn("loopback_only: true", self.out.getvalue())
        self.assertNotIn("rapportd", self.out.getvalue())

    def test_network_linux_uses_ss(self):
        runner = make_runner(PS_OK, SS_BAD)
        self.assertEqual(self.run_cmd(True, runner, system="Linux"), exit_codes.HEALTH_FAILED)
        self.assertIn(["ss", "-ltnp"], runner.calls)
        _, problems = health.check_network(self.ctx, runner, "Linux")
        self.assertEqual(len(problems), 1)
        self.assertIn("0.0.0.0:5000", problems[0])

    # ---- fail closed (review PR #21 finding 3)

    def test_network_named_foreign_listener_on_project_port_is_a_warning(self):
        runner = make_runner(PS_OK, LSOF_FOREIGN)
        self.assertEqual(self.run_cmd(True, runner, system="Darwin"), exit_codes.OK)
        data, problems = health.check_network(self.ctx, runner, "Darwin")
        self.assertEqual(problems, [])
        self.assertEqual(len(data["warnings"]), 1)
        self.assertIn("foreign-listener: ControlCe listens on *:5000", data["warnings"][0])
        self.assertIn("GRDM_PORT_<SERVICE>", data["warnings"][0])

    def test_network_project_port_without_process_field_is_40(self):
        runner = make_runner(PS_OK, SS_NO_PROCESS)
        self.assertEqual(self.run_cmd(True, runner, system="Linux"), exit_codes.HEALTH_FAILED)
        err = self.err.getvalue()
        self.assertIn("0.0.0.0:5000", err)
        self.assertIn("owner not visible", err)
        self.assertNotIn(":22", err)  # sshd on a non-project port is not ours to judge

    def test_network_inspect_host_ip_any_is_40(self):
        runner = make_runner(PS_OK, SS_OK, inspect_host_ip="0.0.0.0")
        self.assertEqual(self.run_cmd(True, runner, system="Linux"), exit_codes.HEALTH_FAILED)
        self.assertIn("inspect", self.err.getvalue())
        self.assertIn("0.0.0.0:5000", self.err.getvalue())
        self.assertTrue(any(c[:2] == ["docker", "inspect"] and c[-1] == "grdm-dev-web-1" for c in runner.calls))

    def test_network_compose_ps_publisher_any_is_40(self):
        runner = make_runner(PS_PUBLISH_ANY, SS_OK)
        self.assertEqual(self.run_cmd(True, runner, system="Linux"), exit_codes.HEALTH_FAILED)
        self.assertIn("web publishes 0.0.0.0:5000 (ps", self.err.getvalue())

    def test_network_all_loopback_is_0_on_linux(self):
        runner = make_runner(PS_OK, SS_OK)
        self.assertEqual(self.run_cmd(True, runner, system="Linux"), exit_codes.OK)
        self.assertIn("loopback_only: true", self.out.getvalue())
        self.assertNotIn("sshd", self.out.getvalue())

    def test_network_inspect_failure_is_40(self):
        runner = make_runner(PS_OK, SS_OK, inspect_rc=1)
        self.assertEqual(self.run_cmd(True, runner, system="Linux"), exit_codes.HEALTH_FAILED)
        self.assertIn("docker inspect", self.err.getvalue())

    def test_network_ss_failure_is_40(self):
        def runner(argv):
            if argv[:2] == ["docker", "compose"]:
                return 0, PS_OK
            if argv[:2] == ["docker", "inspect"]:
                return 0, inspect_ports(argv[-1])
            return 2, ""
        self.assertEqual(self.run_cmd(True, runner, system="Linux"), exit_codes.HEALTH_FAILED)
        self.assertIn("ss exited 2", self.err.getvalue())

    def test_missing_compose_is_usage_error(self):
        (self.root / "runtime" / "docker-compose.yml").unlink()
        self.assertEqual(self.run_cmd(False, make_runner(PS_OK)), exit_codes.USAGE)

    def test_parse_ps_accepts_array_and_lines(self):
        self.assertEqual(set(health.parse_ps(PS_OK)), {"web", "api", "postgres"})
        self.assertEqual(health.parse_ps(PS_BAD)["api"]["State"], "exited")
        self.assertEqual(health.parse_ps(""), {})

    def test_host_port_from_env_fallback(self):
        self.assertEqual(health.host_port("web", COMPOSE, {}), 5000)
        self.assertEqual(health.host_port("mfr", {"services": {"mfr": {}}}, {"GRDM_PORT_MFR": "7778"}), 7778)
        self.assertIsNone(health.host_port("mfr", {"services": {"mfr": {}}}, {}))


if __name__ == "__main__":
    unittest.main()
