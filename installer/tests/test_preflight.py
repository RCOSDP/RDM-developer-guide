"""Cross-OS install preflight and Linux volume ownership (SPEC-02 §3, §4, §6, §8).

`doctor` must report what would otherwise stop `install` after the long build. Each behaviour has a
success and a rejection case; no Docker, no network: Probe, fake runner and a copied manifest.
"""
import argparse
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from grdm_dev import build, compose, doctor, exit_codes, host, install, lifecycle, manifest
from grdm_dev.context import Context

from test_host import GIB, docker_runner, macos_probe, ubuntu_probe

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_OK = {"git": True, "trivy": True, "gitleaks": True, "semgrep": True}
WSL = dict(release="5.15.153.1-microsoft-standard-WSL2", proc_version="Linux version 5.15.153.1-microsoft-standard-WSL2 (root@...)")
SECRET_URL = "fatal: unable to access 'https://x-access-token:s3cr3t-token@example.invalid/org/repo.git/'"
HOME = "/Users/dev"


def preflight_runner(ls_remote=(0, "abc\tHEAD\n"), vm_bytes=64 * GIB, visible=(0, "/probe/upstreams.json\n"), **docker):
    """docker_runner, plus `docker info` and `git ls-remote` (one answer, or a function of the repository)."""
    base = docker_runner(**docker)
    calls = []

    def run(argv):
        calls.append(list(argv))
        if argv[:2] == ["docker", "info"]:
            return 0, f"{vm_bytes}\n"
        if "ls-remote" in argv:
            return ls_remote(argv) if callable(ls_remote) else ls_remote
        if argv[:2] == ["docker", "run"]:
            return visible
        return base(argv)

    run.calls = calls
    return run


def ls_remote_calls(runner):
    return [c for c in runner.calls if "ls-remote" in c]


class PreflightBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        shutil.copytree(REPO_ROOT / "manifest", self.root / "manifest")

    def tearDown(self):
        self.tmp.cleanup()

    def doctor(self, probe, runner, profile="core", memory_gib=None, strict=False):
        ctx = Context(root=self.root, yes=True, stdin_is_tty=False, profile=profile)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = doctor.run(ctx, argparse.Namespace(command="doctor", strict=strict, memory_gib=memory_gib), runner=runner, probe=probe)
        return code, out.getvalue(), err.getvalue()

    def mac(self, **over):
        base = dict(memory_bytes=64 * GIB, tools=dict(TOOLS_OK), repo_root=f"{HOME}/rdm", env={"HOME": HOME})
        base.update(over)
        return macos_probe(**base)

    def ubuntu(self, **over):
        base = dict(memory_bytes=64 * GIB, tools=dict(TOOLS_OK), repo_root="/home/dev/rdm", env={"HOME": "/home/dev"})
        base.update(over)
        return ubuntu_probe(**base)


class RepositoryAccessTests(PreflightBase):
    def test_readable_repositories_pass_without_any_prompt(self):
        runner = preflight_runner()
        code, _, _ = self.doctor(self.mac(), runner)
        self.assertEqual(code, exit_codes.OK)
        calls = ls_remote_calls(runner)
        self.assertTrue(calls)
        for argv in calls:
            self.assertEqual(argv[:2], ["env", "GIT_TERMINAL_PROMPT=0"])
            self.assertIn("GCM_INTERACTIVE=never", argv)

    def test_clones_only_what_build_clones(self):
        runner = preflight_runner()
        self.doctor(self.mac(), runner)
        repos = {argv[-2].rsplit("/", 1)[1].removesuffix(".git") for argv in ls_remote_calls(runner)}
        self.assertIn("RDM-osf.io-dev2027", repos)
        self.assertNotIn("RDM-ember-osf-web-dev2027", repos)  # prebuilt: never cloned
        self.assertIn("RDM-cas-overlay-dev2027", repos)       # built natively since ADR-07 covered it
        self.assertNotIn("RDM-rdmcp-dev2027", repos)          # full profile only

    def test_denied_repository_is_exit_13_and_explains_the_token(self):
        code, out, err = self.doctor(self.mac(), preflight_runner(ls_remote=(128, "fatal: could not read Username: terminal prompts disabled\n")))
        self.assertEqual(code, exit_codes.PREFLIGHT_FAILED)
        self.assertIn("exit 13", err)
        self.assertIn("RDM-osf.io-dev2027", err)
        self.assertIn("gh auth setup-git", err)

    def test_git_output_is_never_printed(self):
        code, out, err = self.doctor(self.mac(), preflight_runner(ls_remote=(128, SECRET_URL)))
        self.assertEqual(code, exit_codes.PREFLIGHT_FAILED)
        self.assertNotIn("s3cr3t-token", out + err)
        self.assertNotIn("s3cr3t-token", (self.root / "runtime" / "reports" / "doctor_latest.json").read_text(encoding="utf-8"))

    def test_unreachable_network_is_a_warning_not_a_denial(self):
        code, out, _ = self.doctor(self.mac(), preflight_runner(ls_remote=(128, "fatal: unable to access: Could not resolve host: github.com")))
        self.assertEqual(code, exit_codes.OK)
        self.assertIn("could not reach GitHub", out)

    def test_timeout_is_a_warning(self):
        code, out, _ = self.doctor(self.mac(), preflight_runner(ls_remote=(124, "timed out")))
        self.assertEqual(code, exit_codes.OK)
        self.assertIn("could not reach GitHub", out)

    def test_build_cannot_prompt_either(self):
        popen = mock.MagicMock()
        popen.return_value.stdout = []
        popen.return_value.wait.return_value = 0
        with mock.patch.object(build.subprocess, "Popen", popen):
            build.default_runner(["git", "clone", "x"])
        self.assertEqual(popen.call_args.kwargs["env"]["GIT_TERMINAL_PROMPT"], "0")


class ToolTests(PreflightBase):
    def test_all_tools_present_is_exit_0(self):
        self.assertEqual(self.doctor(self.mac(), preflight_runner())[0], exit_codes.OK)

    def test_missing_git_is_exit_13_and_skips_the_repository_check(self):
        runner = preflight_runner()
        code, _, err = self.doctor(self.ubuntu(tools={**TOOLS_OK, "git": False}), runner)
        self.assertEqual(code, exit_codes.PREFLIGHT_FAILED)
        self.assertIn("git not found", err)
        self.assertIn("apt install", err)
        self.assertEqual(ls_remote_calls(runner), [])

    def test_missing_scanner_is_exit_51_before_the_build(self):
        for tool in ("trivy", "gitleaks", "semgrep"):
            with self.subTest(tool):
                code, _, err = self.doctor(self.mac(tools={**TOOLS_OK, tool: False}), preflight_runner())
                self.assertEqual(code, exit_codes.SCANNER_UNAVAILABLE)
                self.assertIn(f"{tool} not found", err)

    def test_mac_hint_names_homebrew(self):
        _, _, err = self.doctor(self.mac(tools={**TOOLS_OK, "trivy": False}), preflight_runner())
        self.assertIn("brew install trivy", err)

    def test_without_scan_leaves_semgrep_a_warning(self):
        probe = self.ubuntu(tools={**TOOLS_OK, "semgrep": False}, env={"HOME": "/home/dev", host.WITHOUT_SCAN_ENV: "1"})
        code, out, _ = self.doctor(probe, preflight_runner())
        self.assertEqual(code, exit_codes.OK)
        self.assertIn("semgrep left out", out)

    def test_docker_problem_is_reported_before_a_missing_tool(self):
        code, _, _ = self.doctor(self.mac(tools={**TOOLS_OK, "git": False}), preflight_runner(server=None))
        self.assertEqual(code, exit_codes.DOCKER_MISSING)

    def test_from_system_probes_tools_and_repo_root(self):
        probe = host.Probe.from_system(root=self.root, runner=lambda argv: (1, ""))
        self.assertEqual(set(probe.tools), {"git", "trivy", "gitleaks", "semgrep"})
        self.assertEqual(probe.repo_root, str(self.root.resolve()))


class MemoryFloorTests(PreflightBase):
    def test_floors_match_the_compose_budget(self):
        services = manifest.services_for_profile(manifest.load(Context(root=self.root)), "core")
        need = compose.memory_floor_need_gib(services)
        self.assertGreater(need, 16.0)   # a 16 GiB laptop cannot hold core
        self.assertLess(need, 24.0)      # SPEC-02 §8: the 24 GiB Docker VM can

    def test_core_on_16_gib_is_exit_10_with_the_remedies(self):
        code, _, err = self.doctor(self.ubuntu(memory_bytes=16 * GIB), preflight_runner(vm_bytes=16 * GIB))
        self.assertEqual(code, exit_codes.HOST_UNSUPPORTED)
        self.assertIn("--profile minimum", err)
        self.assertIn("--memory-gib", err)

    def test_the_vm_counts_when_smaller_than_the_host(self):
        code, _, err = self.doctor(self.mac(memory_bytes=64 * GIB), preflight_runner(vm_bytes=8 * GIB))
        self.assertEqual(code, exit_codes.HOST_UNSUPPORTED)
        self.assertIn("8.0 GiB", err)
        self.assertIn("Settings > Resources", err)

    def test_wsl2_gets_wslconfig_not_docker_desktop(self):
        code, _, err = self.doctor(ubuntu_probe(**WSL, memory_bytes=16 * GIB, tools=dict(TOOLS_OK), repo_root="/home/dev/rdm"), preflight_runner(vm_bytes=16 * GIB))
        self.assertEqual(code, exit_codes.HOST_UNSUPPORTED)
        self.assertIn(".wslconfig", err)
        self.assertIn("wsl --shutdown", err)
        self.assertNotIn("Settings > Resources", err)

    def test_small_wsl2_host_gets_the_wslconfig_hint(self):
        info = host.detect(runner=docker_runner(), probe=ubuntu_probe(**WSL, memory_bytes=4 * GIB))
        self.assertIn(".wslconfig", " ".join(info.problems))

    def test_minimum_profile_fits_16_gib(self):
        code, _, _ = self.doctor(self.ubuntu(memory_bytes=16 * GIB), preflight_runner(vm_bytes=16 * GIB), profile="minimum")
        self.assertEqual(code, exit_codes.OK)

    def test_memory_gib_downgrades_to_a_warning(self):
        code, out, _ = self.doctor(self.ubuntu(memory_bytes=16 * GIB), preflight_runner(vm_bytes=16 * GIB), memory_gib=16.0)
        self.assertEqual(code, exit_codes.OK)
        self.assertIn("knowing overcommit", out)

    def test_install_forwards_memory_gib(self):
        ctx = Context(root=self.root, yes=True, stdin_is_tty=False)
        steps = dict(install.plan_steps(ctx, platform=None, no_open=True, memory_gib=16.0))
        self.assertEqual(steps["doctor"], ["doctor", "--memory-gib", "16"])
        self.assertEqual(steps["compose render"], ["compose", "render", "--memory-gib", "16"])

    def test_install_without_memory_gib_is_unchanged(self):
        ctx = Context(root=self.root, yes=True, stdin_is_tty=False)
        steps = dict(install.plan_steps(ctx, platform=None, no_open=True))
        self.assertEqual(steps["doctor"], ["doctor"])
        self.assertEqual(steps["compose render"], ["compose", "render"])


class DockerCpuTests(unittest.TestCase):
    def test_reads_the_engine_cpu_count(self):
        self.assertEqual(compose.detect_docker_cpus(lambda argv: (0, "8\n")), 8.0)

    def test_unknown_is_none(self):
        self.assertIsNone(compose.detect_docker_cpus(lambda argv: (1, "")))
        self.assertIsNone(compose.detect_docker_cpus(lambda argv: (0, "not a number")))
        self.assertIsNone(compose.detect_docker_cpus(lambda argv: (0, "0\n")))


class ArmEmulationTests(PreflightBase):
    def arm(self, **over):
        return self.ubuntu(machine="aarch64", **over)

    def test_enabled_emulation_passes(self):
        self.assertEqual(self.doctor(self.arm(binfmt_amd64=True), preflight_runner())[0], exit_codes.OK)

    def test_missing_emulation_is_exit_13_and_prints_the_command(self):
        code, _, err = self.doctor(self.arm(binfmt_amd64=False), preflight_runner())
        self.assertEqual(code, exit_codes.PREFLIGHT_FAILED)
        self.assertIn(host.ENABLE_AMD64_EMULATION, err)
        self.assertIn("tonistiigi/binfmt:qemu-v10.2.3-68@sha256:", err)
        self.assertIn("mfr", err)

    def test_measured_bad_ubuntu_qemu_is_exit_13_and_prints_the_replacement(self):
        # DEMO-21 run 1: Ubuntu 24.04's qemu-user-static crashed in libgvc6's post-install script after a 48-minute run.
        bad = "qemu-x86_64 version 8.2.2 (Debian 1:8.2.2+ds-0ubuntu1.18)"
        code, _, err = self.doctor(self.arm(binfmt_amd64=True, binfmt_amd64_qemu=bad), preflight_runner())
        self.assertEqual(code, exit_codes.PREFLIGHT_FAILED)
        self.assertIn("QEMU internal SIGSEGV", err)
        self.assertIn("--uninstall qemu-x86_64", err)
        self.assertIn(host.REPLACE_AMD64_EMULATION, err)

    def test_other_or_unknown_qemu_builds_pass(self):
        for line in ("", "qemu-x86_64 version 10.2.3", "qemu-x86_64 version 8.2.2", "qemu-x86_64 version 9.2.2 (Debian 1:9.2.2+ds-1)"):
            with self.subTest(line=line):
                self.assertEqual(self.doctor(self.arm(binfmt_amd64=True, binfmt_amd64_qemu=line), preflight_runner())[0], exit_codes.OK)

    def test_unreadable_binfmt_is_a_warning(self):
        code, out, _ = self.doctor(self.arm(binfmt_amd64=None), preflight_runner())
        self.assertEqual(code, exit_codes.OK)
        self.assertIn("cannot read binfmt_misc", out)

    def test_not_probed_on_amd64_or_macos(self):
        self.assertEqual(self.doctor(self.ubuntu(binfmt_amd64=False), preflight_runner())[0], exit_codes.OK)
        self.assertEqual(self.doctor(self.mac(binfmt_amd64=False), preflight_runner())[0], exit_codes.OK)


class QemuProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def entry(self, interpreter):
        path = self.root / "qemu-x86_64"
        path.write_text(f"enabled\ninterpreter {interpreter}\nflags: OPF\noffset 0\n")
        return str(path)

    def test_resolves_the_interpreter_and_reads_its_version(self):
        real = self.root / "qemu-x86_64-static"
        real.write_text("")
        link = self.root / "x86_64-binfmt-P"
        link.symlink_to(real)
        seen = []

        def runner(argv):
            seen.append(argv)
            return 0, "qemu-x86_64 version 8.2.2 (Debian 1:8.2.2+ds-0ubuntu1.18)\nCopyright\n"

        line = host._binfmt_amd64_qemu(runner, self.entry(str(link)))
        self.assertEqual(seen, [[str(real.resolve()), "--version"]])
        self.assertEqual(host.known_bad_qemu(line), "Ubuntu 24.04 qemu-user-static 8.2.2")

    def test_container_registered_handler_is_unknown_not_bad(self):
        def runner(argv):
            raise AssertionError("must not run a file that is not on this host")

        self.assertEqual(host._binfmt_amd64_qemu(runner, self.entry("/usr/bin/qemu-x86_64-does-not-exist")), "")
        self.assertEqual(host._binfmt_amd64_qemu(runner, str(self.root / "missing-entry")), "")

    def test_failing_version_is_unknown(self):
        real = self.root / "qemu"
        real.write_text("")
        self.assertEqual(host._binfmt_amd64_qemu(lambda argv: (1, "has to be run using kernel binfmt-misc"), self.entry(str(real))), "")


class RepoPathTests(PreflightBase):
    NO_SUCH_FILE = (2, "ls: cannot access '/probe/upstreams.json': No such file or directory\n")

    def wsl(self, **over):
        base = dict(memory_bytes=64 * GIB, tools=dict(TOOLS_OK), repo_root="/home/dev/rdm", repo_modes_enforced=True)
        base.update(over)
        return ubuntu_probe(**WSL, **base)

    def test_wsl2_filesystem_that_keeps_modes_passes(self):
        self.assertEqual(self.doctor(self.wsl(), preflight_runner())[0], exit_codes.OK)

    def test_wsl2_linux_disk_under_mnt_passes(self):
        self.assertEqual(self.doctor(self.wsl(repo_root="/mnt/data/rdm", repo_modes_enforced=True), preflight_runner())[0], exit_codes.OK)

    def test_wsl2_filesystem_that_drops_modes_is_exit_13_wherever_it_is_mounted(self):
        for where in ("/mnt/c/Users/dev/rdm", "/win/rdm"):
            with self.subTest(where):
                code, _, err = self.doctor(self.wsl(repo_root=where, repo_modes_enforced=False), preflight_runner())
                self.assertEqual(code, exit_codes.PREFLIGHT_FAILED)
                self.assertIn("0600", err)

    def test_wsl2_unknown_modes_is_a_warning(self):
        code, out, _ = self.doctor(self.wsl(repo_modes_enforced=None), preflight_runner())
        self.assertEqual(code, exit_codes.OK)
        self.assertIn("could not test file modes", out)

    def test_mode_probe_reads_a_real_chmod_back_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertIs(host._modes_enforced(Path(td)), True)
            self.assertEqual(list(Path(td).iterdir()), [])
            with mock.patch.object(host.os, "stat", return_value=mock.Mock(st_mode=0o100777)):
                self.assertIs(host._modes_enforced(Path(td)), False)
        self.assertIsNone(host._modes_enforced(Path("/nonexistent/grdm")))

    def test_macos_path_the_engine_sees_passes_wherever_it_is(self):
        runner = preflight_runner()
        for where in ("/Users/dev/rdm", "/private/tmp/rdm", "/opt/rdm"):
            with self.subTest(where):
                self.assertEqual(self.doctor(self.mac(repo_root=where), runner)[0], exit_codes.OK)
        argv = next(c for c in runner.calls if c[:2] == ["docker", "run"])
        self.assertIn("/opt/rdm/manifest:/probe:ro", [c for c in runner.calls if c[:2] == ["docker", "run"]][-1])
        self.assertIn("--read-only", argv)
        self.assertEqual(argv[argv.index("--network") + 1], "none")
        self.assertEqual(argv[argv.index("--cap-drop") + 1], "ALL")

    def test_macos_path_the_engine_cannot_see_is_exit_13(self):
        code, _, err = self.doctor(self.mac(repo_root="/Users/dev/rdm"), preflight_runner(visible=self.NO_SUCH_FILE))
        self.assertEqual(code, exit_codes.PREFLIGHT_FAILED)
        self.assertIn("silently empty", err)

    def test_macos_check_that_cannot_run_is_a_warning_naming_the_override(self):
        code, out, _ = self.doctor(self.mac(), preflight_runner(visible=(125, "Unable to find image; pull failed")))
        self.assertEqual(code, exit_codes.OK)
        self.assertIn("GRDM_DOCKER_SHARED=1", out)

    def test_macos_mount_the_engine_refuses_is_exit_13(self):
        denied = (125, "docker: Error response from daemon: Mounts denied:\nThe path /Volumes/x is not shared from the host and is not known to Docker.\n")
        code, _, err = self.doctor(self.mac(repo_root="/Volumes/x/rdm"), preflight_runner(visible=denied))
        self.assertEqual(code, exit_codes.PREFLIGHT_FAILED)
        self.assertIn("cannot see", err)

    def test_macos_override_skips_the_engine(self):
        runner = preflight_runner(visible=self.NO_SUCH_FILE)
        code, out, _ = self.doctor(self.mac(env={"HOME": HOME, doctor.DOCKER_SHARED_ENV: "1"}), runner)
        self.assertEqual(code, exit_codes.OK)
        self.assertEqual([c for c in runner.calls if c[:2] == ["docker", "run"]], [])
        self.assertIn("not checking", out)

    def test_engine_question_is_macos_only(self):
        runner = preflight_runner(visible=self.NO_SUCH_FILE)
        self.assertEqual(self.doctor(self.ubuntu(), runner)[0], exit_codes.OK)
        self.assertEqual([c for c in runner.calls if c[:2] == ["docker", "run"]], [])


class OwnerInitTests(unittest.TestCase):
    def render(self):
        from test_compose import make_root, render

        root = make_root()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        rc, _, err, _ = render(root, memory_gib=64.0)
        self.assertEqual(rc, exit_codes.OK, err)
        return json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))["services"]

    def test_each_writable_volume_goes_to_its_writers_uid(self):
        cmd = self.render()["volume_owner_init"]["command"][2]
        self.assertIn("fix 999:999 /volumes/redis_data", cmd)
        for name in ("elasticsearch_data", "elasticsearch6_data", "ember_osf_web_dist", "wiki_static", "wb_tmp", "osfstoragecache"):
            self.assertIn(f"fix 1000:1000 /volumes/{name}", cmd)

    def test_self_managing_volumes_are_left_alone(self):
        services = self.render()
        init = services["volume_owner_init"]
        for name in ("postgres_data", "mongo_data", "rabbitmq_data"):
            self.assertNotIn(name, init["command"][2])
            self.assertFalse([v for v in init["volumes"] if v.startswith(f"{name}:")])
        self.assertNotIn("volume_owner_init", services["postgres"].get("depends_on", {}))

    def test_the_hardening_baseline_holds(self):
        init = self.render()["volume_owner_init"]
        self.assertEqual(init["user"], "0:0")
        self.assertEqual(init["cap_drop"], ["ALL"])
        self.assertEqual(init["cap_add"], ["CHOWN"])
        self.assertIs(init["read_only"], True)
        self.assertIn("no-new-privileges:true", init["security_opt"])
        self.assertEqual(init["restart"], "no")
        self.assertEqual(init["networks"], ["grdm"])
        self.assertNotIn("chmod", init["command"][2])
        self.assertEqual(init["labels"]["org.gakunin-rdm.hardening-exception"], "cap_add,user")

    def test_scan_baseline_accepts_it(self):
        from grdm_dev import scan
        from test_compose import make_root, render

        root = make_root()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        render(root, memory_gib=64.0)
        findings, _, accepted = scan.check_baseline(root / "runtime" / "docker-compose.yml", root / "manifest" / "hardening.json")
        self.assertFalse([f for f in findings if "volume_owner_init" in json.dumps(f)])
        self.assertEqual({a["control"] for a in accepted if a["service"] == "volume_owner_init"}, {"user", "cap_add"})

    def test_every_writer_waits_for_it(self):
        services = self.render()
        wait = {"condition": "service_completed_successfully"}
        for name in ("redis", "elasticsearch", "elasticsearch6", "wb", "wb_worker", "mfr", "ember_osf_web", "wiki_assets", "web"):
            self.assertEqual(services[name]["depends_on"]["volume_owner_init"], wait, name)

    def test_unoconv_shares_no_volume_and_runs_unprivileged(self):
        services = self.render()
        unoconv = services["unoconv"]
        self.assertEqual(unoconv["user"], "1000:1000")
        self.assertEqual(unoconv["cap_drop"], ["ALL"])
        self.assertNotIn("cap_add", unoconv)
        self.assertNotIn("volumes", unoconv)
        self.assertNotIn("volume_owner_init", unoconv.get("depends_on", {}))
        self.assertEqual(unoconv["tmpfs"], ["/tmp:mode=1777,size=1g"])

    def test_access_checks_write_as_each_owner_and_gate_the_writers(self):
        services = self.render()
        wait = {"condition": "service_completed_successfully"}
        check_1000, check_999 = services["volume_access_check_1000"], services["volume_access_check_999"]
        self.assertEqual((check_1000["user"], check_999["user"]), ("1000:1000", "999:999"))
        self.assertEqual(check_999["volumes"], ["redis_data:/volumes/redis_data"])
        self.assertIn("wb_tmp:/volumes/wb_tmp", check_1000["volumes"])
        for check in (check_1000, check_999):
            self.assertEqual(check["depends_on"], {"volume_owner_init": wait})
            self.assertEqual(check["cap_drop"], ["ALL"])
            self.assertNotIn("cap_add", check)
            self.assertIs(check["read_only"], True)
            self.assertEqual(check["labels"]["org.gakunin-rdm.hardening-exception"], "none")
        self.assertEqual(services["redis"]["depends_on"]["volume_access_check_999"], wait)
        self.assertNotIn("volume_access_check_1000", services["redis"]["depends_on"])

    def test_no_shortcut_on_the_top_directory(self):
        cmd = self.render()["volume_owner_init"]["command"][2]
        self.assertNotIn("chown -R", cmd)
        self.assertIn("-xdev", cmd)
        self.assertIn("chown -h", cmd)

    def test_conflicting_owners_are_rejected(self):
        svc = lambda name, user: manifest.Service(name=name, component="c", role="r", image="i", profile="core", build=None,  # noqa: E731
                                                  template={"user": user, "volumes": [{"volume": "shared", "target": "/d"}]})
        with self.assertRaises(ValueError):
            compose.volume_owners([svc("a", "1000:1000"), svc("b", "999:999")], {})

    def test_a_read_only_mount_sets_no_owner(self):
        reader = manifest.Service(name="r", component="c", role="r", image="i", profile="core", build=None,
                                  template={"user": "1000:1000", "volumes": [{"volume": "v", "target": "/d", "ro": True}]})
        self.assertEqual(compose.volume_owners([reader], {}), ({}, {}))

    def test_a_list_without_the_step_is_unchanged(self):
        reader = manifest.Service(name="r", component="c", role="r", image="i", profile="core", build=None, template={})
        self.assertEqual(compose.with_owner_init([reader], {}), [reader])



FAKE_FS = r"""#!PYTHON
# find, chown and stat over a JSON model of a tree, matching GNU find and chown measured on a real kernel: {path: [uid, gid, mode]}. Directories are the entries that
# have children or mode bit 0o40000. The caller is root with only CAP_CHOWN: file permissions apply to it.
import json, os, sys

STATE = os.environ["FS_STATE"]
FAIL_ONCE = os.environ.get("FS_FAIL_ONCE", "")
tool = os.path.basename(sys.argv[0])
fs = json.load(open(STATE))

# FS_FIND_FAULT: this kind of listing walk fails part way, as an I/O error would; it prints nothing and exits 1
fault = os.environ.get("FS_FIND_FAULT")
listing = "-exec" not in sys.argv
if tool == "find" and listing and (
    (fault == "open" and "-perm" in sys.argv)
    or (fault == "verify" and "-perm" not in sys.argv and "-readable" not in sys.argv)
    or (fault == "access" and "-readable" in sys.argv)
):
    print("find: Input/output error", file=sys.stderr)
    sys.exit(1)


def save():
    json.dump(fs, open(STATE, "w"))


def reachable(path):
    # Root with only CAP_CHOWN: every ancestor must be searchable through its owner or "other" bits.
    parent = os.path.dirname(path)
    while parent in fs:
        uid, _, mode = fs[parent]
        if ((mode >> 6) & 1) == 0 if uid == 0 else (mode & 1) == 0:
            return False
        parent = os.path.dirname(parent)
    return True


def chown(owner, path):
    if os.environ.get("FS_NO_OWNERSHIP") or path == os.environ.get("FS_SILENT_CHOWN"):
        return
    if not reachable(path):
        print(f"chown: cannot access {path}: Permission denied", file=sys.stderr)
        sys.exit(1)
    fs[path][:2] = [int(x) for x in owner.split(":")]
    save()


def children(path):
    return sorted(p for p in fs if os.path.dirname(p) == path)


def is_dir(path):
    return bool(children(path)) or fs[path][2] & 0o40000


if tool == "stat" and os.environ.get("FS_STAT_FAULT"):
    sys.exit(1)
if tool == "stat":
    uid, gid, _ = fs[sys.argv[-1]]
    print("0:0" if os.environ.get("FS_NO_OWNERSHIP") else f"{uid}:{gid}")
elif tool == "chown":
    for path in sys.argv[3:]:
        if path == FAIL_ONCE and os.path.exists(STATE + ".fail"):
            os.unlink(STATE + ".fail")
            sys.exit(1)
        chown(sys.argv[2], path)
elif tool == "mktemp":
    print("/nonexistent/.grdm-write-probe.model")
elif tool == "find" and "-readable" in sys.argv:
    # the access check, as an unprivileged uid: access() per entry, -prune on a directory that fails
    me = int(os.environ["FS_UID"])

    def can(path, bits):
        uid, _, mode = fs[path]
        return ((mode >> 6) if uid == me else mode) & bits == bits

    def walk(path):
        if is_dir(path):
            if not can(path, 7):
                print(path)
                return
            for child in children(path):
                walk(child)
        elif not can(path, 4):
            print(path)

    walk(sys.argv[1])
elif tool == "find":
    args = sys.argv[2:]
    opening = "-perm" in args
    only_dirs = not opening and "-type" in args and args[args.index("-type") - 1] != "!"
    only_files = not opening and "-type" in args and args[args.index("-type") - 1] == "!"
    u, g = (int(args[args.index("-user") + 1]), None) if opening else (int(args[args.index("-user") + 1]), int(args[args.index("-group") + 1]))
    batch = []
    code = 0

    def walk(path):
        global code
        uid, gid, mode = fs[path]
        if opening:
            if is_dir(path) and uid != 0 and (mode & 5) != 5:
                batch.append(path)
                return  # -prune: GNU find does not open it
        elif (uid != u or gid != g) and not (only_dirs and not is_dir(path)) and not (only_files and is_dir(path)):
            batch.append(path)
        if is_dir(path):
            allowed = (mode >> 6) & 5 == 5 if fs[path][0] == 0 else (mode & 5) == 5
            if not allowed:
                print(f"find: {path}: Permission denied", file=sys.stderr)
                code = 1
                return
            for child in children(path):
                walk(child)

    walk(sys.argv[1])
    if "-depth" in args:
        batch.reverse()  # children before their directory
    if "-exec" in args and args[args.index("-exec") + 1] == "sh":
        start = args.index("-exec") + 1
        import subprocess
        sys.exit(subprocess.run(args[start:args.index("{}")] + batch).returncode or code)
    if "-exec" in args:
        owner = args[args.index("-exec") + 3]
        for path in batch:
            if path == FAIL_ONCE and os.path.exists(STATE + ".fail"):
                os.unlink(STATE + ".fail")
                sys.exit(1)
            chown(owner, path)
    else:
        print("\n".join(batch))
    sys.exit(code)
"""

DIR = 0o40000


class OwnerStepContractTests(unittest.TestCase):
    """The generated script over a model of Linux permissions (the model is proven against a real kernel by hand)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        (base / "bin").mkdir()
        (base / "bin" / "awk").write_text('#!/bin/sh\necho "$FS_TYPE"\n')
        (base / "bin" / "awk").chmod(0o755)
        for tool in ("find", "chown", "stat", "mktemp"):
            (base / "bin" / tool).write_text(FAKE_FS.replace("#!PYTHON", f"#!{sys.executable}"))
            (base / "bin" / tool).chmod(0o755)
        (base / "bin" / "ls").write_text("#!/bin/sh\nexit 0\n")
        (base / "bin" / "ls").chmod(0o755)
        self.base = base
        self.state = base / "state.json"
        self.script = compose._owner_init_command({"data": "1000:1000"})[2]

    def tearDown(self):
        self.tmp.cleanup()

    def run_step(self, tree, **env):
        if tree is not None:
            self.state.write_text(json.dumps(tree))
        proc = subprocess.run(["/bin/sh", "-c", self.script], capture_output=True, text=True,
                              env={"PATH": f"{self.base / 'bin'}:/bin:/usr/bin", "FS_STATE": str(self.state), **env})
        return proc, json.loads(self.state.read_text())

    def owners(self, fs):
        return {p: tuple(v[:2]) for p, v in fs.items()}

    def assert_all_owned(self, fs):
        self.assertEqual(set(self.owners(fs).values()), {(1000, 1000)}, fs)

    def test_fresh_host_owned_tree(self):
        proc, fs = self.run_step({"/volumes/data": [501, 20, DIR | 0o755], "/volumes/data/f": [501, 20, 0o644]})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assert_all_owned(fs)

    def test_private_descendants_of_another_uid(self):
        proc, fs = self.run_step({
            "/volumes/data": [101, 101, DIR | 0o700],
            "/volumes/data/private": [101, 101, DIR | 0o700],
            "/volumes/data/private/deep": [999, 999, DIR | 0o700],
            "/volumes/data/private/deep/secret": [999, 999, 0o600],
        })
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assert_all_owned(fs)
        self.assertEqual(fs["/volumes/data/private/deep"][2], DIR | 0o700)  # never chmods

    def test_directories_are_handed_back_deepest_first(self):
        self.assertIn('-xdev -depth -type d', self.script)
        tree = {"/volumes/data": [1000, 1000, DIR | 0o755], "/volumes/data/a": [999, 999, DIR | 0o700], "/volumes/data/a/b": [999, 999, DIR | 0o700], "/volumes/data/a/b/c": [999, 999, DIR | 0o700]}
        proc, fs = self.run_step(tree)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assert_all_owned(fs)

    def test_a_second_run_reopens_directories_it_handed_back(self):
        tree = {"/volumes/data": [1000, 1000, DIR | 0o755], "/volumes/data/p": [1000, 1000, DIR | 0o700], "/volumes/data/p/wrong": [999, 999, 0o600]}
        proc, fs = self.run_step(tree)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assert_all_owned(fs)
        proc, fs = self.run_step(None)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assert_all_owned(fs)

    def test_mixed_ownership_under_a_correct_top_directory(self):
        proc, fs = self.run_step({
            "/volumes/data": [1000, 1000, DIR | 0o755],
            "/volumes/data/ok": [1000, 1000, 0o644],
            "/volumes/data/wrong": [999, 1000, 0o644],
            "/volumes/data/group": [1000, 0, 0o644],
        })
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assert_all_owned(fs)

    def test_failure_stops_and_a_retry_finishes_the_tree(self):
        tree = {"/volumes/data": [101, 101, DIR | 0o700], "/volumes/data/a": [101, 101, 0o600], "/volumes/data/b": [101, 101, 0o600]}
        self.state.with_name("state.json.fail").write_text("")
        env = {"FS_FAIL_ONCE": "/volumes/data/b"}
        proc, fs = self.run_step(tree, **env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.owners(fs)["/volumes/data/b"], (101, 101))  # really stopped part way
        proc, fs = self.run_step(None, **env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assert_all_owned(fs)

    def test_a_run_interrupted_after_opening_a_directory_is_repaired(self):
        proc, fs = self.run_step({"/volumes/data": [1000, 1000, DIR | 0o755], "/volumes/data/p": [0, 0, DIR | 0o700], "/volumes/data/p/f": [1000, 1000, 0o600]})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assert_all_owned(fs)

    def test_an_unreachable_directory_fails_loudly(self):
        tree = {"/volumes/data": [1000, 1000, DIR | 0o755], "/volumes/data/sealed": [101, 101, DIR | 0o000], "/volumes/data/sealed/f": [101, 101, 0o600]}
        proc, _ = self.run_step(tree)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("/volumes/data/sealed", proc.stderr)

    def test_a_failing_walk_while_opening_directories_stops_the_step(self):
        proc, _ = self.run_step({"/volumes/data": [1000, 1000, DIR | 0o755], "/volumes/data/f": [1000, 1000, 0o644]}, FS_FIND_FAULT="open")
        self.assertNotEqual(proc.returncode, 0)

    def test_a_failing_stat_is_not_taken_for_a_share_without_ownership(self):
        proc, _ = self.run_step({"/volumes/data": [0, 0, DIR | 0o755]}, FS_STAT_FAULT="1", FS_TYPE="virtiofs")
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("does not keep ownership", proc.stdout)

    def test_a_failing_verification_walk_stops_the_step(self):
        proc, _ = self.run_step({"/volumes/data": [1000, 1000, DIR | 0o755], "/volumes/data/f": [1000, 1000, 0o644]}, FS_FIND_FAULT="verify")
        self.assertNotEqual(proc.returncode, 0)

    def test_a_known_vm_share_is_left_to_the_access_check(self):
        tree = {"/volumes/data": [0, 0, DIR | 0o755], "/volumes/data/f": [0, 0, 0o644]}
        for fstype in compose.OWNERSHIP_IGNORING_FILESYSTEMS:
            with self.subTest(fstype):
                proc, fs = self.run_step(tree, FS_NO_OWNERSHIP="1", FS_TYPE=fstype)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(fs, tree)
                self.assertIn("does not keep ownership", proc.stdout)

    def test_an_ineffective_chown_elsewhere_stops_the_step(self):
        for fstype in ("ext4", "xfs", ""):
            with self.subTest(fstype):
                proc, _ = self.run_step({"/volumes/data": [0, 0, DIR | 0o755]}, FS_NO_OWNERSHIP="1", FS_TYPE=fstype)
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn("after chown", proc.stderr)

    def test_an_ineffective_chown_of_a_directory_is_caught(self):
        tree = {"/volumes/data": [1000, 1000, DIR | 0o755], "/volumes/data/p": [999, 999, DIR | 0o700], "/volumes/data/p/f": [999, 999, 0o600]}
        proc, fs = self.run_step(tree, FS_SILENT_CHOWN="/volumes/data/p")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("/volumes/data/p", proc.stderr)

    def test_an_ineffective_chown_of_a_nested_directory_is_caught_by_read_back(self):
        tree = {"/volumes/data": [1000, 1000, DIR | 0o755], "/volumes/data/p": [0, 0, DIR | 0o755], "/volumes/data/p/q": [0, 0, DIR | 0o755]}
        proc, fs = self.run_step(tree, FS_SILENT_CHOWN="/volumes/data/p/q")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("/volumes/data/p/q stayed 0:0", proc.stderr)

    def test_an_ineffective_chown_of_a_file_is_caught(self):
        tree = {"/volumes/data": [1000, 1000, DIR | 0o755], "/volumes/data/f": [999, 999, 0o644]}
        proc, _ = self.run_step(tree, FS_SILENT_CHOWN="/volumes/data/f")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("/volumes/data/f", proc.stderr)


class AccessCheckTests(OwnerStepContractTests):
    """R3-01: the writer's view of the existing tree, on the same model as the owner step."""

    def setUp(self):
        super().setUp()
        self.script = compose._access_check_command(["data"])[2]

    def check(self, tree):
        return self.run_step(tree, FS_UID="1000")

    def test_a_private_child_under_a_writable_root_is_refused(self):
        tree = {"/volumes/data": [0, 0, DIR | 0o777], "/volumes/data/private": [999, 999, DIR | 0o700], "/volumes/data/private/f": [999, 999, 0o600]}
        proc, fs = self.check(tree)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("/volumes/data/private", proc.stderr)
        self.assertEqual(fs, tree)  # asks, never changes

    def test_an_unreadable_file_is_refused(self):
        proc, _ = self.check({"/volumes/data": [1000, 1000, DIR | 0o755], "/volumes/data/f": [999, 999, 0o600]})
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("/volumes/data/f", proc.stderr)

    def test_a_read_only_directory_is_refused(self):
        proc, _ = self.check({"/volumes/data": [1000, 1000, DIR | 0o755], "/volumes/data/d": [999, 999, DIR | 0o755]})
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("/volumes/data/d", proc.stderr)

    def test_a_failing_walk_is_not_reported_as_usable(self):
        proc, _ = self.run_step({"/volumes/data": [1000, 1000, DIR | 0o755], "/volumes/data/f": [1000, 1000, 0o644]}, FS_UID="1000", FS_FIND_FAULT="access")
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("usable by", proc.stdout)

    def test_a_usable_tree_passes(self):
        proc, _ = self.check({"/volumes/data": [1000, 1000, DIR | 0o755], "/volumes/data/d": [1000, 1000, DIR | 0o700], "/volumes/data/d/f": [1000, 1000, 0o600], "/volumes/data/ro": [1000, 1000, 0o444]})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("usable by", proc.stdout)

    # the owner-step scenarios do not apply to this script
    for _name in [n for n in dir(OwnerStepContractTests) if n.startswith("test_")]:
        locals()[_name] = None
    del _name


class AccessProbeFileTests(unittest.TestCase):
    """R3-02: the generated shell against a real directory, with real mktemp and rm; find is stubbed (BSD find has no -readable)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.volume = self.base / "volumes" / "data"
        self.volume.mkdir(parents=True)
        (self.base / "bin").mkdir()
        (self.base / "bin" / "find").write_text("#!/bin/sh\nexit 0\n")
        (self.base / "bin" / "find").chmod(0o755)
        self.script = compose._access_check_command(["data"])[2].replace(compose.OWNER_INIT_MOUNT, str(self.base / "volumes"))

    def tearDown(self):
        self.tmp.cleanup()

    def run_check(self):
        proc = subprocess.run(["/bin/sh", "-c", self.script], capture_output=True, text=True, env={"PATH": f"{self.base / 'bin'}:/bin:/usr/bin"})
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_an_existing_file_with_the_old_fixed_name_is_untouched(self):
        existing = self.volume / ".grdm-write-probe"
        existing.write_text("KEEP")
        self.run_check()
        self.assertEqual(existing.read_text(), "KEEP")

    def test_an_existing_symlink_and_its_target_are_untouched(self):
        sentinel = self.base / "sentinel"
        sentinel.write_text("KEEP")
        link = self.volume / ".grdm-write-probe"
        link.symlink_to(sentinel)
        self.run_check()
        self.assertTrue(link.is_symlink())
        self.assertEqual(sentinel.read_text(), "KEEP")

    def test_only_the_new_probe_file_is_removed(self):
        (self.volume / "data").write_text("x")
        self.run_check()
        self.assertEqual(sorted(p.name for p in self.volume.iterdir()), ["data"])

    def test_the_probe_is_created_exclusively(self):
        self.assertIn('mktemp "$v/.grdm-write-probe.XXXXXX"', self.script)
        self.assertNotIn(': > "', self.script)


class VolumePathTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        self.runtime = self.root / "runtime"
        self.volumes = self.runtime / "volumes"
        self.outside = Path(self.tmp.name) / "outside"
        self.outside.mkdir()
        (self.outside / "sentinel").write_text("keep")

    def tearDown(self):
        self.tmp.cleanup()

    def problems(self, names=None):
        return compose.volume_path_problems(self.root, self.runtime, names)

    def test_a_plain_tree_and_a_missing_tree_are_fine(self):
        self.runtime.mkdir(parents=True)
        self.assertEqual(self.problems(), [])
        (self.volumes / "redis_data").mkdir(parents=True)
        self.assertEqual(self.problems(), [])
        self.assertEqual(self.problems(["redis_data", "not_yet"]), [])

    def test_symlinked_volumes_root_is_refused(self):
        self.runtime.mkdir(parents=True)
        self.volumes.symlink_to(self.outside)
        self.assertIn("symbolic link", self.problems()[0])

    def test_symlinked_runtime_is_refused(self):
        self.root.mkdir()
        self.runtime.symlink_to(self.outside)
        self.assertIn("symbolic link", self.problems()[0])

    def test_escaping_parent_is_refused(self):
        (self.outside / "volumes").mkdir()
        self.root.mkdir()
        self.runtime.mkdir()
        # a tree whose own components are real directories but whose root differs from the checkout
        other = Path(self.tmp.name) / "elsewhere"
        (other / "runtime" / "volumes").mkdir(parents=True)
        self.assertIn("outside", compose.volume_path_problems(self.root, other / "runtime")[0])

    def test_symlinked_volume_is_refused(self):
        self.volumes.mkdir(parents=True)
        (self.volumes / "redis_data").symlink_to(self.outside)
        self.assertIn("symbolic link", self.problems()[0])
        self.assertIn("symbolic link", self.problems(["redis_data"])[0])

    def test_a_dangling_symlink_is_refused(self):
        self.volumes.mkdir(parents=True)
        (self.volumes / "redis_data").symlink_to(self.outside / "gone")
        self.assertIn("symbolic link", self.problems()[0])

    def with_mounts(self, *points):
        return mock.patch.object(compose, "host_mount_points", return_value=list(points))

    def test_a_same_device_bind_mount_at_any_depth_is_refused(self):
        (self.volumes / "wb_tmp" / "deep").mkdir(parents=True)
        with self.with_mounts("/", str(self.volumes.resolve() / "wb_tmp" / "deep")):
            self.assertIn("mount inside", self.problems()[0])

    def test_runtime_or_volumes_root_being_a_mount_is_refused(self):
        self.volumes.mkdir(parents=True)
        for point in (self.runtime, self.volumes):
            with self.subTest(point.name), self.with_mounts("/", str(point.resolve())):
                self.assertIn("mount inside", self.problems()[0])

    def test_mounts_elsewhere_do_not_matter(self):
        self.volumes.mkdir(parents=True)
        with self.with_mounts("/", str(self.volumes.resolve()) + "-other", str(self.root.resolve().parent)):
            self.assertEqual(self.problems(), [])

    def test_an_unreadable_mount_table_refuses(self):
        self.volumes.mkdir(parents=True)
        with mock.patch.object(compose, "host_mount_points", return_value=None):
            self.assertIn("cannot be read", self.problems()[0])

    def test_macos_mount_table_is_parsed(self):
        out = "/dev/disk3s1s1 on / (apfs, sealed)\n/dev/disk3s5 on /System/Volumes/Data (apfs, local)\nmap auto_home on /System/Volumes/Data/home with space (autofs)\n"
        with mock.patch.object(compose.platform, "system", return_value="Darwin"), \
                mock.patch.object(compose.subprocess, "run", return_value=mock.Mock(stdout=out)):
            self.assertEqual(compose.host_mount_points(), ["/", "/System/Volumes/Data", "/System/Volumes/Data/home with space"])

    def test_macos_data_prefix_is_compared_too(self):
        (self.volumes / "a").mkdir(parents=True)
        with self.with_mounts("/System/Volumes/Data" + str(self.volumes.resolve() / "a")):
            self.assertIn("mount inside", self.problems()[0])

    def test_linux_mount_table_decodes_escapes(self):
        text = "36 35 98:0 / /mnt/with\\040space rw - ext3 /dev/root rw\n"
        with mock.patch.object(compose.platform, "system", return_value="Linux"), \
                mock.patch("builtins.open", mock.mock_open(read_data=text)):
            self.assertEqual(compose.host_mount_points(), ["/mnt/with space"])

    def test_nested_mount_is_refused(self):
        (self.volumes / "redis_data").mkdir(parents=True)
        real = self.volumes.stat()
        fake = mock.Mock(st_mode=(self.volumes / "redis_data").lstat().st_mode, st_dev=real.st_dev + 1)
        with mock.patch.object(Path, "lstat", return_value=fake):
            self.assertIn("separate mount", self.problems()[0])

    def test_compose_render_refuses_a_symlinked_volume_before_writing(self):
        from test_compose import make_root, render

        root = make_root()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        (root / "runtime" / "volumes").mkdir(parents=True)
        (root / "runtime" / "volumes" / "redis_data").symlink_to(self.outside)
        rc, _, err, _ = render(root, memory_gib=64.0)
        self.assertEqual(rc, exit_codes.PREFLIGHT_FAILED)
        self.assertIn("redis_data", err)
        self.assertFalse((root / "runtime" / "docker-compose.yml").exists())


class ResetTests(unittest.TestCase):
    IMAGE = "grdm-dev/elasticsearch2:2.4.6-1"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "runtime" / "volumes" / "redis_data").mkdir(parents=True)
        compose_doc = {"services": {compose.OWNER_INIT_SERVICE: {"image": self.IMAGE, "platform": "linux/arm64"}}}
        (self.root / "runtime" / "docker-compose.yml").write_text(json.dumps(compose_doc))
        self.ctx = Context(root=self.root, stdin_is_tty=False, yes=True)
        self.volumes = self.root / "runtime" / "volumes"
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def runner(self, wipe_rc=0):
        def run(argv):
            self.calls.append(argv)
            return (wipe_rc if argv[:2] == ["docker", "run"] else 0), ""
        return run

    def reset(self, runner, **kw):
        out, err = io.StringIO(), io.StringIO()
        args = argparse.Namespace(lifecycle_action="reset")
        with redirect_stdout(out), redirect_stderr(err):
            code = lifecycle.run(self.ctx, args, runner=runner, **kw)
        return code, err.getvalue()

    def wipe(self):
        return next(c for c in self.calls if c[:2] == ["docker", "run"])

    def test_contents_are_deleted_through_a_minimal_container(self):
        code, _ = self.reset(self.runner())
        self.assertEqual(code, exit_codes.OK)
        argv = self.wipe()
        self.assertEqual(argv[-7:], [self.IMAGE, "find", "/volumes", "-xdev", "-mindepth", "1", "-delete"])
        self.assertIn(f"{self.volumes}:/volumes", argv)
        self.assertIn("--read-only", argv)
        self.assertEqual(argv[argv.index("--network") + 1], "none")
        self.assertEqual(argv[argv.index("--pull") + 1], "never")
        self.assertEqual(argv[argv.index("--cap-drop") + 1], "ALL")
        self.assertEqual(sorted(argv[i + 1] for i, a in enumerate(argv) if a == "--cap-add"), ["DAC_OVERRIDE", "FOWNER"])
        self.assertNotIn("--privileged", argv)
        self.assertFalse(self.volumes.exists())

    def test_runs_after_the_stack_is_down(self):
        self.reset(self.runner())
        down = next(i for i, c in enumerate(self.calls) if "down" in c)
        run = next(i for i, c in enumerate(self.calls) if c[:2] == ["docker", "run"])
        self.assertLess(down, run)

    def test_host_only_delete_still_works_without_the_image(self):
        code, _ = self.reset(self.runner(wipe_rc=125))
        self.assertEqual(code, exit_codes.OK)
        self.assertFalse(self.volumes.exists())

    def test_permission_error_is_exit_14_not_a_traceback(self):
        def denied(path):
            raise PermissionError(13, "Permission denied", str(path))
        code, err = self.reset(self.runner(), rmtree=denied)
        self.assertEqual(code, exit_codes.RESET_FAILED)
        self.assertIn("exit 14", err)
        self.assertIn("sudo rm -rf", err)

    def test_declined_confirmation_touches_nothing(self):
        self.ctx.yes = False
        code, err = self.reset(self.runner())
        self.assertEqual(code, exit_codes.USAGE)
        self.assertIn("--yes", err)
        self.assertEqual(self.calls, [])
        self.assertTrue(self.volumes.exists())

    def assert_nothing_destructive(self):
        self.assertEqual(self.calls, [])  # neither `down --volumes` nor the root wipe was submitted

    def test_symlinked_volumes_root_is_refused_before_anything_runs(self):
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "sentinel").write_text("keep")
        shutil.rmtree(self.volumes)
        self.volumes.symlink_to(outside)
        code, err = self.reset(self.runner())
        self.assertEqual(code, exit_codes.RESET_FAILED)
        self.assertIn("symbolic link", err)
        self.assert_nothing_destructive()
        self.assertEqual((outside / "sentinel").read_text(), "keep")

    def test_symlinked_volume_is_refused_before_anything_runs(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.volumes / "linked").symlink_to(outside)
        code, _ = self.reset(self.runner())
        self.assertEqual(code, exit_codes.RESET_FAILED)
        self.assert_nothing_destructive()

    def test_symlinked_volume_stops_up_with_exit_13(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.volumes / "linked").symlink_to(outside)
        out, err = io.StringIO(), io.StringIO()
        args = argparse.Namespace(lifecycle_action="up", no_open=True, timeout=1.0)
        with redirect_stdout(out), redirect_stderr(err):
            code = lifecycle.run(self.ctx, args, runner=self.runner())
        self.assertEqual(code, exit_codes.PREFLIGHT_FAILED)
        self.assert_nothing_destructive()

    def substitute_volumes(self):
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "sentinel").write_text("keep")
        shutil.rmtree(self.volumes)
        self.volumes.symlink_to(outside)

    def test_substitution_during_down_stops_before_the_wipe(self):
        def run(argv):
            self.calls.append(argv)
            if "down" in argv:
                self.substitute_volumes()
            return 0, ""
        code, err = self.reset(run)
        self.assertEqual(code, exit_codes.RESET_FAILED)
        self.assertEqual([c for c in self.calls if c[:2] == ["docker", "run"]], [])
        self.assertEqual((self.root / "outside" / "sentinel").read_text(), "keep")
        self.assertIn("changed during reset", err)

    def test_substitution_during_the_wipe_stops_before_host_deletion(self):
        deleted = []

        def run(argv):
            self.calls.append(argv)
            if argv[:2] == ["docker", "run"]:
                self.substitute_volumes()
            return 0, ""
        code, _ = self.reset(run, rmtree=deleted.append)
        self.assertEqual(code, exit_codes.RESET_FAILED)
        self.assertEqual(deleted, [])

    def test_a_different_directory_with_the_same_path_is_refused(self):
        def run(argv):
            self.calls.append(argv)
            if "down" in argv:
                shutil.rmtree(self.volumes)
                self.volumes.mkdir()
                (self.volumes / "filler").write_text("x")  # keeps the old inode number from being reused
            return 0, ""
        with mock.patch.object(compose, "volume_root_identity", side_effect=[(1, 1), (1, 2), (1, 2)]):
            code, err = self.reset(run)
        self.assertEqual(code, exit_codes.RESET_FAILED)
        self.assertIn("changed during reset", err)

    def test_a_mount_found_after_down_stops_the_wipe(self):
        real = compose.host_mount_points()

        def run(argv):
            self.calls.append(argv)
            return 0, ""
        with mock.patch.object(compose, "host_mount_points", side_effect=[real, [str(self.volumes.resolve() / "x")]]):
            code, _ = self.reset(run)
        self.assertEqual(code, exit_codes.RESET_FAILED)
        self.assertEqual([c for c in self.calls if c[:2] == ["docker", "run"]], [])

    def test_no_rendered_file_means_no_container(self):
        (self.root / "runtime" / "docker-compose.yml").unlink()
        code, _ = self.reset(self.runner())
        self.assertEqual(code, exit_codes.OK)
        self.assertEqual(self.calls, [])
        self.assertFalse(self.volumes.exists())


class ExitCodeTests(unittest.TestCase):
    def test_new_codes_have_messages_in_both_languages(self):
        for code in (exit_codes.PREFLIGHT_FAILED, exit_codes.RESET_FAILED, exit_codes.DB_UPGRADE_FAILED):
            self.assertNotEqual(exit_codes.describe(code, "en"), "unknown exit code")
            self.assertNotEqual(exit_codes.describe(code, "ja"), "不明な終了コード")

    def test_spec_table_lists_them(self):
        text = (REPO_ROOT / "docs" / "spec" / "02_installer_cli.md").read_text(encoding="utf-8")
        self.assertEqual(text.count("exit_codes[17]{code,meaning}:"), 2)
        self.assertEqual(len(exit_codes.messages()), 17)


if __name__ == "__main__":
    unittest.main()
