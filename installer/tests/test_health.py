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

PS_OK = "\n".join(json.dumps({"Service": s, "State": "running", "Health": "healthy"}) for s in ("web", "api", "postgres"))
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
SS_BAD = """State  Recv-Q Send-Q Local Address:Port  Peer Address:Port Process
LISTEN 0      4096   0.0.0.0:5000        0.0.0.0:*     users:(("docker-proxy",pid=99,fd=4))
LISTEN 0      4096   127.0.0.1:8000      0.0.0.0:*     users:(("docker-proxy",pid=98,fd=4))
LISTEN 0      128    0.0.0.0:22          0.0.0.0:*     users:(("sshd",pid=1,fd=3))
"""


def make_runner(ps_output, sockets_output="", ps_rc=0):
    calls = []

    def runner(argv):
        calls.append(argv)
        if argv[:2] == ["docker", "compose"]:
            return ps_rc, ps_output
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
        self.assertEqual(sorted(probed), ["http://127.0.0.1:5000/", "http://127.0.0.1:8000/"])
        self.assertIn("services[3]", self.out.getvalue())

    def test_unhealthy_service_is_40(self):
        self.assertEqual(self.run_cmd(False, make_runner(PS_BAD)), exit_codes.HEALTH_FAILED)
        self.assertIn("api", self.err.getvalue())
        self.assertIn("postgres", self.err.getvalue())

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
        _, bad, _ = health.check_network(runner, "Linux")
        self.assertEqual([(s["address"], s["port"]) for s in bad], [("0.0.0.0", "5000")])

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
