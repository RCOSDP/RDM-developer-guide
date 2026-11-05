"""Unit tests for grdm_dev.doctor: exit codes 0 / 10 / 11 and --strict (SPEC-02 §3, §6, §10)."""
import argparse
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from grdm_dev import cli, doctor, exit_codes, host
from grdm_dev.context import Context

from test_host import docker_runner, macos_probe, ubuntu_probe, GIB, DEBIAN_12


def _args(strict=False):
    return argparse.Namespace(command="doctor", strict=strict)


class DoctorRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ctx = Context(root=Path(self.tmp.name), yes=True, stdin_is_tty=False)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, probe, runner, strict=False):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = doctor.run(self.ctx, _args(strict), runner=runner, probe=probe)
        return code, out.getvalue(), err.getvalue()

    def test_macos_arm64_docker29_exit_0(self):
        code, out, err = self._run(macos_probe(), docker_runner())
        self.assertEqual(code, exit_codes.OK)
        self.assertIn("doctor:", out)
        self.assertIn("os_name: macos", out)
        self.assertIn("docker_ok: true", out)
        self.assertEqual(err, "")
        self.assertTrue((self.ctx.reports_dir / "doctor_latest.json").exists())

    def test_ubuntu_docker_missing_exit_11(self):
        code, out, err = self._run(ubuntu_probe(), docker_runner(server=None))
        self.assertEqual(code, exit_codes.DOCKER_MISSING)
        self.assertIn("exit 11", err)
        self.assertIn(exit_codes.describe(11, "en"), err)
        self.assertIn("docker_ok: false", out)

    def test_compose_missing_exit_11(self):
        code, _, err = self._run(macos_probe(), docker_runner(compose=None))
        self.assertEqual(code, exit_codes.DOCKER_MISSING)
        self.assertIn("compose plugin missing", err)

    def test_unsupported_os_exit_10(self):
        probe = host.Probe(system="Windows", release="11", machine="AMD64", python_version=(3, 12, 0),
                           memory_bytes=32 * GIB, disk_free_bytes=100 * GIB)
        code, _, err = self._run(probe, docker_runner())
        self.assertEqual(code, exit_codes.HOST_UNSUPPORTED)
        self.assertIn("exit 10", err)

    def test_low_memory_exit_10(self):
        code, _, err = self._run(macos_probe(memory_bytes=4 * GIB), docker_runner())
        self.assertEqual(code, exit_codes.HOST_UNSUPPORTED)
        self.assertIn("8 GiB", err)

    def test_host_problem_wins_over_docker_problem(self):
        # Both broken: the host code (10) is reported, not 11.
        code, _, _ = self._run(macos_probe(memory_bytes=4 * GIB), docker_runner(server=None))
        self.assertEqual(code, exit_codes.HOST_UNSUPPORTED)

    def test_japanese_message_when_lang_ja(self):
        self.ctx.lang = "ja"
        code, _, err = self._run(ubuntu_probe(), docker_runner(server=None))
        self.assertEqual(code, exit_codes.DOCKER_MISSING)
        self.assertIn(exit_codes.describe(11, "ja"), err)

    def test_best_effort_host_warns_but_exits_0(self):
        code, out, _ = self._run(ubuntu_probe(os_release=DEBIAN_12), docker_runner())
        self.assertEqual(code, exit_codes.OK)
        self.assertIn("best-effort", out)

    def test_strict_turns_warnings_into_exit_10(self):
        code, out, err = self._run(ubuntu_probe(os_release=DEBIAN_12), docker_runner(), strict=True)
        self.assertEqual(code, exit_codes.HOST_UNSUPPORTED)
        self.assertIn("--strict", err)
        self.assertIn("strict: true", out)

    def test_strict_with_no_warnings_exits_0(self):
        code, _, _ = self._run(macos_probe(), docker_runner(), strict=True)
        self.assertEqual(code, exit_codes.OK)


class DoctorCliTests(unittest.TestCase):
    def test_doctor_is_registered_with_strict_flag(self):
        parser = cli.build_parser()
        args = parser.parse_args(["doctor", "--strict"])
        self.assertIs(args._module, doctor)
        self.assertTrue(args.strict)
        self.assertFalse(parser.parse_args(["doctor"]).strict)


if __name__ == "__main__":
    unittest.main()
