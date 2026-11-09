"""Cross-OS install preflight and Linux volume ownership (SPEC-02 §3, §4, §6, §8).

`doctor` must report what would otherwise stop `install` after the long build. Each behaviour has a
success and a rejection case; no Docker, no network: Probe, fake runner and a copied manifest.
"""
import argparse
import io
import json
import shutil
import subprocess
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
SECRET_URL = "fatal: unable to access 'https://x-access-token:s3cr3t-token@github.com/RCOSDP/RDM-osf.io-dev2027.git/'"
HOME = "/Users/dev"


def preflight_runner(ls_remote=(0, "abc\tHEAD\n"), vm_bytes=64 * GIB, **docker):
    """docker_runner, plus `docker info` and `git ls-remote` (one answer, or a function of the repository)."""
    base = docker_runner(**docker)
    calls = []

    def run(argv):
        calls.append(list(argv))
        if argv[:2] == ["docker", "info"]:
            return 0, f"{vm_bytes}\n"
        if "ls-remote" in argv:
            return ls_remote(argv) if callable(ls_remote) else ls_remote
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
        self.assertNotIn("RDM-cas-overlay-dev2027", repos)
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
        self.assertIn("docker run --privileged --rm tonistiigi/binfmt --install amd64", err)
        self.assertIn("mfr", err)

    def test_unreadable_binfmt_is_a_warning(self):
        code, out, _ = self.doctor(self.arm(binfmt_amd64=None), preflight_runner())
        self.assertEqual(code, exit_codes.OK)
        self.assertIn("cannot read binfmt_misc", out)

    def test_not_probed_on_amd64_or_macos(self):
        self.assertEqual(self.doctor(self.ubuntu(binfmt_amd64=False), preflight_runner())[0], exit_codes.OK)
        self.assertEqual(self.doctor(self.mac(binfmt_amd64=False), preflight_runner())[0], exit_codes.OK)


class RepoPathTests(PreflightBase):
    def test_wsl2_under_home_passes(self):
        code, _, _ = self.doctor(ubuntu_probe(**WSL, memory_bytes=64 * GIB, tools=dict(TOOLS_OK), repo_root="/home/dev/rdm"), preflight_runner())
        self.assertEqual(code, exit_codes.OK)

    def test_wsl2_on_a_windows_drive_is_exit_13(self):
        code, _, err = self.doctor(ubuntu_probe(**WSL, memory_bytes=64 * GIB, tools=dict(TOOLS_OK), repo_root="/mnt/c/Users/dev/rdm"), preflight_runner())
        self.assertEqual(code, exit_codes.PREFLIGHT_FAILED)
        self.assertIn("0600", err)

    def test_plain_ubuntu_may_live_under_mnt(self):
        self.assertEqual(self.doctor(self.ubuntu(repo_root="/mnt/data/rdm"), preflight_runner())[0], exit_codes.OK)

    def test_mac_outside_home_is_exit_13(self):
        code, _, err = self.doctor(self.mac(repo_root="/private/tmp/rdm"), preflight_runner())
        self.assertEqual(code, exit_codes.PREFLIGHT_FAILED)
        self.assertIn("silently empty", err)

    def test_mac_home_prefix_is_not_enough(self):
        self.assertEqual(self.doctor(self.mac(repo_root=f"{HOME}-other/rdm"), preflight_runner())[0], exit_codes.PREFLIGHT_FAILED)

    def test_mac_external_volume_is_a_warning(self):
        code, out, _ = self.doctor(self.mac(repo_root="/Volumes/ssd/rdm"), preflight_runner())
        self.assertEqual(code, exit_codes.OK)
        self.assertIn("must be shared", out)


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

    def test_a_correct_owner_is_not_walked_again(self):
        cmd = self.render()["volume_owner_init"]["command"][2]
        self.assertIn('[ "$$(stat -c %u:%g "$$2")" = "$$1" ] || chown -R "$$1" "$$2"', cmd)

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

    @unittest.skipUnless(shutil.which("sh"), "no shell")
    def test_the_shell_step_really_chowns_only_when_the_owner_differs(self):
        """The generated script, run for real against a fake `chown` on PATH."""
        from test_compose import make_root, render

        root = make_root()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        render(root, memory_gib=64.0)
        cmd = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))["services"]["volume_owner_init"]["command"][2]
        script = cmd.replace("$$", "$")
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "bin").mkdir()
            log = base / "log"
            for name, body in (("chown", f'echo "$@" >> {log}\n'), ("stat", 'case "$3" in */redis_data) echo 999:999;; *) echo 501:20;; esac\n'), ("ls", "exit 0\n")):
                (base / "bin" / name).write_text(f"#!/bin/sh\n{body}")
                (base / "bin" / name).chmod(0o755)
            proc = subprocess.run(["/bin/sh", "-c", script], env={"PATH": f"{base / 'bin'}:/bin:/usr/bin"}, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            lines = log.read_text().splitlines()
        self.assertFalse([line for line in lines if "redis_data" in line])  # 999:999 already
        self.assertIn("-R 1000:1000 /volumes/elasticsearch_data", lines)


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
        self.assertEqual(argv[-6:], [self.IMAGE, "find", "/volumes", "-mindepth", "1", "-delete"])
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

    def test_no_rendered_file_means_no_container(self):
        (self.root / "runtime" / "docker-compose.yml").unlink()
        code, _ = self.reset(self.runner())
        self.assertEqual(code, exit_codes.OK)
        self.assertEqual(self.calls, [])
        self.assertFalse(self.volumes.exists())


class ExitCodeTests(unittest.TestCase):
    def test_new_codes_have_messages_in_both_languages(self):
        for code in (exit_codes.PREFLIGHT_FAILED, exit_codes.RESET_FAILED):
            self.assertNotEqual(exit_codes.describe(code, "en"), "unknown exit code")
            self.assertNotEqual(exit_codes.describe(code, "ja"), "不明な終了コード")

    def test_spec_table_lists_them(self):
        text = (REPO_ROOT / "docs" / "spec" / "02_installer_cli.md").read_text(encoding="utf-8")
        self.assertEqual(text.count("exit_codes[16]{code,meaning}:"), 2)
        self.assertEqual(len(exit_codes.messages()), 16)


if __name__ == "__main__":
    unittest.main()
