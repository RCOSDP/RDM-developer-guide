"""Unit tests for grdm_dev.host (SPEC-02 §3, §8, §10). No Docker, no OS access: Probe + fake runner."""
import unittest

from grdm_dev import host

GIB = host.GIB

UBUNTU_2404 = 'NAME="Ubuntu"\nVERSION_ID="24.04"\nID=ubuntu\nID_LIKE=debian\nPRETTY_NAME="Ubuntu 24.04 LTS"\n'
DEBIAN_12 = 'NAME="Debian GNU/Linux"\nVERSION_ID="12"\nID=debian\n'


def macos_probe(**over):
    base = dict(system="Darwin", release="24.1.0", machine="arm64", mac_ver="15.1",
                python_version=(3, 12, 4), memory_bytes=32 * GIB, disk_free_bytes=200 * GIB,
                docker_path="/usr/local/bin/docker")
    base.update(over)
    return host.Probe(**base)


def ubuntu_probe(**over):
    base = dict(system="Linux", release="6.8.0-45-generic", machine="x86_64", os_release=UBUNTU_2404,
                proc_version="Linux version 6.8.0-45-generic (buildd@lcy02) ...",
                python_version=(3, 12, 3), memory_bytes=16 * GIB, disk_free_bytes=100 * GIB,
                docker_path="/usr/bin/docker")
    base.update(over)
    return host.Probe(**base)


def docker_runner(server="29.0.1", compose="Docker Compose version v2.30.3", buildx="github.com/docker/buildx v0.18.0 abc"):
    """A fake `docker` that answers the three doctor queries; None for a part means 'missing'."""
    calls = []

    def run(argv):
        calls.append(list(argv))
        if argv[:2] == ["docker", "version"]:
            if server is None:
                return 127, "docker: command not found"
            if server == "down":
                return 1, "Cannot connect to the Docker daemon at unix:///var/run/docker.sock. Is the docker daemon running?"
            return 0, server + "\n"
        if argv[:3] == ["docker", "compose", "version"]:
            return (1, "docker: 'compose' is not a docker command.") if compose is None else (0, compose + "\n")
        if argv[:3] == ["docker", "buildx", "version"]:
            return (1, "docker: 'buildx' is not a docker command.") if buildx is None else (0, buildx + "\n")
        return 1, f"unexpected: {argv}"

    run.calls = calls
    return run


class ClassifyTests(unittest.TestCase):
    def test_macos_arm64(self):
        self.assertEqual(host.classify_os(macos_probe()), ("macos", "15.1"))
        self.assertEqual(host.classify_arch("arm64"), "arm64")

    def test_ubuntu_from_os_release(self):
        self.assertEqual(host.classify_os(ubuntu_probe()), ("ubuntu", "24.04"))
        self.assertEqual(host.classify_arch("x86_64"), "amd64")
        self.assertEqual(host.classify_arch("aarch64"), "arm64")

    def test_wsl2_from_proc_version(self):
        p = ubuntu_probe(release="5.15.153.1-microsoft-standard-WSL2",
                         proc_version="Linux version 5.15.153.1-microsoft-standard-WSL2 (root@...) ...")
        self.assertEqual(host.classify_os(p), ("wsl2", "24.04"))

    def test_wsl2_from_env(self):
        p = ubuntu_probe(proc_version="Linux version 6.6.0 ...", env={"WSL_DISTRO_NAME": "Ubuntu-24.04"})
        self.assertEqual(host.classify_os(p)[0], "wsl2")

    def test_other_linux_and_unsupported(self):
        self.assertEqual(host.classify_os(ubuntu_probe(os_release=DEBIAN_12))[0], "linux-other")
        self.assertEqual(host.classify_os(host.Probe(system="Windows", release="11"))[0], "unsupported")
        self.assertEqual(host.classify_arch("i686"), "other")

    def test_parse_version(self):
        self.assertEqual(host.parse_version("Docker Compose version v2.30.3"), (2, 30, 3))
        self.assertEqual(host.parse_version("29.0.1\n"), (29, 0, 1))
        self.assertEqual(host.parse_version("no digits"), ())


class DetectTests(unittest.TestCase):
    def test_macos_arm64_docker29_supported(self):
        run = docker_runner()
        info = host.detect(runner=run, probe=macos_probe())
        self.assertTrue(info.supported, info.problems)
        self.assertTrue(info.docker_ok, info.problems)
        self.assertEqual(info.os_name, "macos")
        self.assertEqual(info.arch, "arm64")
        self.assertEqual(info.platform_string, "linux/arm64")
        self.assertEqual(info.docker_version, "29.0.1")
        self.assertEqual(info.compose_version, "2.30.3")
        self.assertTrue(info.buildx_present)
        self.assertTrue(info.docker_running)
        self.assertEqual(info.python_version, "3.12.4")
        self.assertEqual(info.warnings, [])
        self.assertEqual(run.calls[0], ["docker", "version", "--format", "{{.Server.Version}}"])

    def test_ubuntu_amd64_docker_missing(self):
        info = host.detect(runner=docker_runner(server=None), probe=ubuntu_probe())
        self.assertTrue(info.supported)
        self.assertFalse(info.docker_ok)
        self.assertFalse(info.docker_running)
        self.assertEqual(info.platform_string, "linux/amd64")
        self.assertTrue(any("docker command not found" in p for p in info.problems), info.problems)

    def test_docker_daemon_not_running(self):
        info = host.detect(runner=docker_runner(server="down"), probe=ubuntu_probe())
        self.assertTrue(info.supported)
        self.assertFalse(info.docker_ok)
        self.assertTrue(any("not running" in p for p in info.problems), info.problems)

    def test_docker_too_old(self):
        info = host.detect(runner=docker_runner(server="24.0.7"), probe=ubuntu_probe())
        self.assertFalse(info.docker_ok)
        self.assertTrue(any("older than 27" in p for p in info.problems), info.problems)

    def test_compose_plugin_missing(self):
        info = host.detect(runner=docker_runner(compose=None), probe=macos_probe())
        self.assertTrue(info.supported)
        self.assertFalse(info.docker_ok)
        self.assertEqual(info.compose_version, "")
        self.assertTrue(any("compose plugin missing" in p for p in info.problems), info.problems)

    def test_buildx_missing(self):
        info = host.detect(runner=docker_runner(buildx=None), probe=macos_probe())
        self.assertFalse(info.docker_ok)
        self.assertFalse(info.buildx_present)

    def test_unsupported_os(self):
        probe = host.Probe(system="Windows", release="11", machine="AMD64", python_version=(3, 12, 0),
                           memory_bytes=32 * GIB, disk_free_bytes=100 * GIB)
        info = host.detect(runner=docker_runner(), probe=probe)
        self.assertFalse(info.supported)
        self.assertEqual(info.os_name, "unsupported")
        self.assertTrue(any("operating system not supported" in p for p in info.problems), info.problems)

    def test_low_memory_is_problem(self):
        info = host.detect(runner=docker_runner(), probe=macos_probe(memory_bytes=4 * GIB))
        self.assertFalse(info.supported)
        self.assertTrue(any("8 GiB" in p for p in info.problems), info.problems)

    def test_old_python_is_problem(self):
        info = host.detect(runner=docker_runner(), probe=ubuntu_probe(python_version=(3, 9, 19)))
        self.assertFalse(info.supported)
        self.assertTrue(any("older than 3.11" in p for p in info.problems), info.problems)

    def test_best_effort_hosts_warn_and_continue(self):
        intel_mac = host.detect(runner=docker_runner(), probe=macos_probe(machine="x86_64"))
        self.assertTrue(intel_mac.supported)
        self.assertTrue(any("best-effort" in w for w in intel_mac.warnings), intel_mac.warnings)
        debian = host.detect(runner=docker_runner(), probe=ubuntu_probe(os_release=DEBIAN_12))
        self.assertTrue(debian.supported)
        self.assertEqual(debian.os_name, "linux-other")
        self.assertTrue(any("best-effort" in w for w in debian.warnings), debian.warnings)

    def test_memory_and_disk_warnings(self):
        info = host.detect(runner=docker_runner(), probe=macos_probe(memory_bytes=12 * GIB, disk_free_bytes=10 * GIB))
        self.assertTrue(info.supported)
        self.assertTrue(any("recommended 16 GiB" in w for w in info.warnings), info.warnings)
        self.assertTrue(any("recommended 40 GiB" in w for w in info.warnings), info.warnings)

    def test_as_report_is_flat_and_toon_friendly(self):
        from grdm_dev import toon

        info = host.detect(runner=docker_runner(), probe=macos_probe())
        data = host.as_report(info)
        for key in ("os_name", "os_version", "arch", "memory_bytes", "disk_free_bytes", "python_version",
                    "docker_version", "compose_version", "buildx_present", "docker_running", "supported",
                    "docker_ok", "problems", "warnings", "platform_string", "memory_gib", "disk_free_gib", "official"):
            self.assertIn(key, data)
        self.assertTrue(data["official"])
        self.assertEqual(data["memory_gib"], 32.0)
        text = toon.encode(data, name="doctor")
        self.assertIn("platform_string: linux/arm64", text)
        self.assertIn("supported: true", text)

    def test_default_runner_handles_missing_command(self):
        rc, out = host.default_runner(["/nonexistent/grdm-dev-no-such-binary", "x"])
        self.assertEqual(rc, 127)
        self.assertIn("not found", out)


if __name__ == "__main__":
    unittest.main()
