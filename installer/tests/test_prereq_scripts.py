"""Tests for the per-OS prerequisite scripts (ADR-08, SPEC-02 §2.3).

Every run below is `--dry-run` or `--help` under a PATH of stubs, so no test can change the machine. A stub `sudo`,
`brew`, `apt-get`, `curl`, `open` or `usermod` records its call; the tests assert that nothing was recorded.
The PowerShell script is only inspected as text here: the parser runs in CI on windows-latest.
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
INSTALLER = REPO / "installer"
UBUNTU = INSTALLER / "install-ubuntu.sh"
MACOS = INSTALLER / "install-macos.sh"
LIB = INSTALLER / "prereq-lib.sh"
WINDOWS = INSTALLER / "install-windows.ps1"

MUTATING = ("sudo", "apt-get", "curl", "gpg", "usermod", "systemctl", "brew", "open", "sg", "wsl.exe")
UBUNTU_RELEASE = 'ID=ubuntu\nVERSION_ID="24.04"\n'
BINFMT_IMAGE = "tonistiigi/binfmt:qemu-v10.2.3-68@sha256:400a4873b838d1b89194d982c45e5fb3cda4593fbfd7e08a02e76b03b21166f0"
DOCKER_OK = """#!/bin/sh
case "$*" in
  "version --format"*) echo 29.1.0 ;;
esac
exit 0
"""
DOCKER_DOWN = """#!/bin/sh
case "$*" in
  "version --format"*) echo 29.1.0 ;;
  "compose version"|"buildx version") exit 0 ;;
esac
exit 1
"""


def _bash():
    return "/bin/bash" if Path("/bin/bash").exists() else shutil.which("bash")


class ScriptRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bin = self.root / "bin"
        self.home = self.root / "home"
        self.calls = self.root / "calls.log"
        self.bin.mkdir()
        self.home.mkdir()
        for tool in ("awk", "sed", "grep", "dirname", "mktemp", "rm", "tr", "id", "cat", "bash", "mkdir", "sh", "head", "readlink"):
            src = shutil.which(tool)
            if src:
                os.symlink(src, self.bin / tool)
        for tool in MUTATING:
            self._stub(tool, f'#!/bin/sh\necho "{tool} $*" >> "{self.calls}"\nexit 0\n')

    def _stub(self, name, body):
        path = self.bin / name
        if path.exists() or path.is_symlink():
            path.unlink()
        path.write_text(body)
        path.chmod(0o755)

    def _host(self, system, machine):
        self._stub("uname", f'#!/bin/sh\ncase "$1" in -s) echo {system} ;; -m) echo {machine} ;; esac\n')

    def _run(self, script, *args, env_extra=None):
        env = {"PATH": str(self.bin), "HOME": str(self.home), "LANG": "C"}
        env.update(env_extra or {})
        return subprocess.run([_bash(), str(script), *args], env=env, capture_output=True, text=True,
                              timeout=60, stdin=subprocess.DEVNULL)

    def assert_nothing_changed(self):
        recorded = self.calls.read_text() if self.calls.exists() else ""
        self.assertEqual(recorded, "", f"a mutating command ran in a dry run:\n{recorded}")


class UbuntuTests(ScriptRun):
    def setUp(self):
        super().setUp()
        self.release = self.root / "os-release"
        self.release.write_text(UBUNTU_RELEASE)
        self.mounts = self.root / "mounts"
        self.mounts.write_text("/dev/vda1 / ext4 rw,relatime 0 0\n")
        self.env = {"GRDM_PREREQ_OS_RELEASE": str(self.release), "GRDM_PREREQ_PROC_VERSION": str(self.root / "none"),
                    "GRDM_PREREQ_BINFMT_DIR": str(self.root / "binfmt"), "GRDM_PREREQ_MOUNTS": str(self.mounts)}
        self._stub("dpkg-query", "#!/bin/sh\nexit 1\n")

    def test_fresh_amd64_plans_engine_and_scanners(self):
        self._host("Linux", "x86_64")
        cp = self._run(UBUNTU, "--dry-run", "--yes", "--profile", "minimum", env_extra=self.env)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertIn("9DC858229FC7DD38854AE2D88D81803C0EBFCD88", cp.stdout)
        self.assertIn("noble stable amd64", cp.stdout)
        self.assertIn("docker-buildx-plugin docker-compose-plugin", cp.stdout)
        self.assertIn("trivy_0.75.0_Linux-64bit.tar.gz", cp.stdout)
        self.assertIn("gitleaks_8.21.2_linux_x64.tar.gz", cp.stdout)
        self.assertNotIn("qemu-user-static", cp.stdout)
        self.assertRegex(cp.stdout, r"would run: \S*installer/install\.sh --yes --profile minimum\n")
        self.assert_nothing_changed()

    def test_arm64_plans_emulation_and_arm_assets(self):
        self._host("Linux", "aarch64")
        cp = self._run(UBUNTU, "--dry-run", "--yes", env_extra=self.env)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        # QEMU comes from the pinned image, never from Ubuntu's qemu-user-static (DEMO-21 run 1).
        self.assertIn(f"sudo docker run --privileged --rm {BINFMT_IMAGE} --install amd64", cp.stdout)
        self.assertNotIn("--uninstall", cp.stdout)
        self.assertNotIn("apt-get install -y qemu-user-static", cp.stdout)
        self.assertIn("trivy_0.75.0_Linux-ARM64.tar.gz", cp.stdout)
        self.assertIn("gitleaks_8.21.2_linux_arm64.tar.gz", cp.stdout)
        self.assert_nothing_changed()

    def _binfmt_entry(self, flags, version_line=None):
        """A fake binfmt_misc entry; with version_line, its interpreter is a host file (reached through a symlink,
        like Ubuntu's x86_64-binfmt-P) that prints that line for --version."""
        interpreter = "/usr/bin/qemu-x86_64-from-a-container"
        if version_line is not None:
            real = self.root / "qemu-x86_64-static"
            real.write_text(f'#!/bin/sh\n[ "$1" = --version ] && echo "{version_line}" && echo Copyright\n')
            real.chmod(0o755)
            link = self.root / "x86_64-binfmt-P"
            link.symlink_to(real)
            interpreter = str(link)
        (self.root / "binfmt").mkdir()
        (self.root / "binfmt" / "qemu-x86_64").write_text(f"enabled\ninterpreter {interpreter}\nflags: {flags}\n")

    def _arm_ready(self):
        self._host("Linux", "aarch64")
        self._stub("dpkg-query", '#!/bin/sh\nprintf "install ok installed"\n')
        self._stub("docker", DOCKER_OK)
        self._stub("trivy", "#!/bin/sh\nexit 0\n")
        self._stub("gitleaks", "#!/bin/sh\nexit 0\n")

    def test_arm64_measured_bad_ubuntu_qemu_is_replaced(self):
        self._arm_ready()
        self._binfmt_entry("OPF", "qemu-x86_64 version 8.2.2 (Debian 1:8.2.2+ds-0ubuntu1.18)")
        cp = self._run(UBUNTU, "--dry-run", "--yes", env_extra=self.env)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertIn("replace the registered amd64 emulator (qemu-x86_64 version 8.2.2", cp.stdout)
        self.assertIn(f"sudo docker run --privileged --rm {BINFMT_IMAGE} --uninstall qemu-x86_64", cp.stdout)
        self.assertIn(f"sudo docker run --privileged --rm {BINFMT_IMAGE} --install amd64", cp.stdout)
        self.assert_nothing_changed()

    def test_arm64_good_emulation_is_kept(self):
        for version_line in (None, "qemu-x86_64 version 10.2.3"):
            with self.subTest(version_line=version_line):
                shutil.rmtree(self.root / "binfmt", ignore_errors=True)
                for name in ("qemu-x86_64-static", "x86_64-binfmt-P"):
                    (self.root / name).unlink(missing_ok=True)
                self._arm_ready()
                self._binfmt_entry("POCF", version_line)
                cp = self._run(UBUNTU, "--dry-run", "--yes", env_extra=self.env)
                self.assertEqual(cp.returncode, 0, cp.stderr)
                self.assertIn("nothing to change", cp.stdout)
                self.assertNotIn("binfmt", cp.stdout)
                self.assert_nothing_changed()

    def test_arm64_handler_without_f_flag_is_registered_again(self):
        self._arm_ready()
        self._binfmt_entry("OP")
        cp = self._run(UBUNTU, "--dry-run", "--yes", env_extra=self.env)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertIn("register QEMU from", cp.stdout)
        self.assertIn("--uninstall qemu-x86_64", cp.stdout)
        self.assert_nothing_changed()

    def test_accept_extra_adds_libatomic(self):
        self._host("Linux", "x86_64")
        cp = self._run(UBUNTU, "--dry-run", "--yes", env_extra=dict(self.env, GRDM_WITH_ACCEPT="1"))
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertIn("libatomic1", cp.stdout)
        cp = self._run(UBUNTU, "--dry-run", "--yes", env_extra=self.env)
        self.assertNotIn("libatomic1", cp.stdout)
        self.assert_nothing_changed()

    def _shared_home(self, fstype, with_credentials):
        home = self.root / "host-home"
        (home / ".config" / "gh").mkdir(parents=True)
        if with_credentials:
            (home / ".config" / "gh" / "hosts.yml").write_text("not read by the script\n")
        self.mounts.write_text(f"/dev/vda1 / ext4 rw 0 0\nlima-abc {home} {fstype} ro,relatime 0 0\n")
        return home

    def test_shared_host_credentials_stop_with_exit_10(self):
        # DEMO-21: Lima's template mounted the host home read-only, so ~/.config/gh was visible in the VM.
        self._host("Linux", "x86_64")
        home = self._shared_home("virtiofs", True)
        cp = self._run(UBUNTU, "--yes", env_extra=self.env)
        self.assertEqual(cp.returncode, 10, cp.stdout + cp.stderr)
        self.assertIn(f"{home}/.config/gh/hosts.yml", cp.stderr)
        self.assertIn("lima.yaml", cp.stderr)
        self.assert_nothing_changed()
        cp = self._run(UBUNTU, "--dry-run", "--yes", env_extra=self.env)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertIn("would stop with exit 10", cp.stdout)

    def test_trailing_newlines_in_mount_names_are_kept(self):
        # PR #44 review r2 R2-01: $(...) stripped the trailing newline of "host\012", so host/.netrc was checked.
        self._host("Linux", "x86_64")
        cases = (("host\n", "host\\012"), ("host\n\n", "host\\012\\012"), ("host\\012", "host\\134012"))
        for fstype in ("virtiofs", "9p", "fuse.sshfs", "vboxsf", "fuse.vmhgfs-fuse", "fuse.virtiofsd"):
            for name, encoded in cases:
                with self.subTest(fstype=fstype, name=repr(name)):
                    base = self.root / f"nl-{fstype}"
                    (base / name).mkdir(parents=True, exist_ok=True)
                    (base / name / ".netrc").write_text("dummy\n")
                    (base / "host").mkdir(exist_ok=True)  # the wrong, stripped path exists but holds nothing
                    self.mounts.write_text(f"share {base}/{encoded} {fstype} ro 0 0\n")
                    cp = self._run(UBUNTU, "--yes", env_extra=self.env)
                    self.assertEqual(cp.returncode, 10, cp.stdout + cp.stderr)
                    self.assertIn("host credentials are visible", cp.stderr)
                    self.assert_nothing_changed()

    def test_shared_folder_without_credentials_or_local_disk_passes(self):
        self._host("Linux", "x86_64")
        for fstype, creds in (("virtiofs", False), ("ext4", True)):
            with self.subTest(fstype=fstype):
                shutil.rmtree(self.root / "host-home", ignore_errors=True)
                self._shared_home(fstype, creds)
                cp = self._run(UBUNTU, "--dry-run", "--yes", env_extra=self.env)
                self.assertEqual(cp.returncode, 0, cp.stderr)
                self.assertNotIn("would stop with exit 10", cp.stdout)

    def test_powershell_steps_are_one_line_calls(self):
        # DEMO-21 run 3: inline PowerShell in `run:` made Semgrep's engine fail ("Internal matching error"),
        # so `grdm-dev scan` stopped with exit 51. The PowerShell lives in .github/scripts/.
        workflow = (REPO / ".github" / "workflows" / "installer-prereq-lint.yml").read_text()
        lines = workflow.splitlines()
        shells = [i for i, line in enumerate(lines) if re.match(r"\s+shell: (powershell|pwsh)\s*$", line)]
        self.assertGreaterEqual(len(shells), 3)
        for i in shells:
            run = lines[i + 1]
            self.assertRegex(run, r"^\s+run: \./\S+\.ps1( |$)", run)
            self.assertNotIn("|", run)
        helper = REPO / ".github" / "scripts" / "Test-PowerShellSyntax.ps1"
        self.assertIn("Parser]::ParseFile", helper.read_text())

    def test_binfmt_image_and_bad_build_match_doctor(self):
        import sys
        sys.path.insert(0, str(INSTALLER))
        from grdm_dev import host
        text = UBUNTU.read_text()
        self.assertIn(f'BINFMT_IMAGE="{host.BINFMT_IMAGE}"', text)
        self.assertRegex(host.BINFMT_IMAGE, r"@sha256:[0-9a-f]{64}$")
        self.assertIn(f"KNOWN_BAD_QEMU_RE='{host.KNOWN_BAD_QEMU[0][0].pattern}'", text)

    def test_second_run_is_a_no_op(self):
        self._host("Linux", "x86_64")
        self._stub("dpkg-query", '#!/bin/sh\nprintf "install ok installed"\n')
        self._stub("docker", DOCKER_OK)
        self._stub("trivy", "#!/bin/sh\nexit 0\n")
        self._stub("gitleaks", "#!/bin/sh\nexit 0\n")
        cp = self._run(UBUNTU, "--dry-run", env_extra=self.env)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertIn("nothing to change", cp.stdout)
        self.assertNotIn("apt-get", cp.stdout)
        self.assertNotIn("would stop", cp.stdout)
        self.assert_nothing_changed()

    def test_no_terminal_without_yes_is_refused(self):
        self._host("Linux", "x86_64")
        cp = self._run(UBUNTU, "--dry-run", env_extra=self.env)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertIn("would stop with exit 2", cp.stdout)
        self.assert_nothing_changed()

    def test_unsupported_release_exits_10(self):
        self._host("Linux", "x86_64")
        self.release.write_text('ID=ubuntu\nVERSION_ID="22.04"\n')
        cp = self._run(UBUNTU, "--dry-run", "--yes", env_extra=self.env)
        self.assertEqual(cp.returncode, 10, cp.stderr)
        self.assertIn("exit 10", cp.stderr)
        self.assertIn("host unsupported", cp.stderr)
        self.assert_nothing_changed()

    def test_macos_host_exits_10(self):
        self._host("Darwin", "arm64")
        cp = self._run(UBUNTU, "--dry-run", "--yes", env_extra=self.env)
        self.assertEqual(cp.returncode, 10, cp.stderr)
        self.assertIn("install-macos.sh", cp.stderr)

    def test_conflicting_package_is_reported_not_removed(self):
        self._host("Linux", "x86_64")
        self._stub("dpkg-query", '#!/bin/sh\ncase "$*" in *docker.io*) printf "install ok installed" ;; *) exit 1 ;; esac\n')
        cp = self._run(UBUNTU, "--dry-run", "--yes", env_extra=self.env)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertIn("would stop with exit 11", cp.stdout)
        self.assertIn("sudo apt-get remove docker.io", cp.stdout)
        self.assert_nothing_changed()

    def test_wsl_uses_docker_desktop_and_never_installs_engine(self):
        self._host("Linux", "x86_64")
        env = dict(self.env, WSL_DISTRO_NAME="Ubuntu-24.04")
        cp = self._run(UBUNTU, "--dry-run", "--yes", env_extra=env)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertIn("would stop with exit 11", cp.stdout)
        self.assertIn("WSL Integration", cp.stdout)
        self.assertNotIn("download.docker.com", cp.stdout)
        self.assert_nothing_changed()

    def _copy_checkout(self, dest):
        (dest / "installer" / "grdm_dev").mkdir(parents=True)
        for name in ("install-ubuntu.sh", "prereq-lib.sh"):
            shutil.copy2(INSTALLER / name, dest / "installer" / name)
        shutil.copy2(INSTALLER / "grdm_dev" / "messages.tsv", dest / "installer" / "grdm_dev" / "messages.tsv")
        return dest

    def _wsl_run(self, checkout_link):
        self._host("Linux", "x86_64")
        env = dict(self.env, WSL_DISTRO_NAME="Ubuntu-24.04", GRDM_PREREQ_WSL_WINDOWS_ROOT=str(self.root / "win"))
        return self._run(checkout_link / "installer" / "install-ubuntu.sh", "--dry-run", "--yes", env_extra=env)

    def test_wsl_refuses_a_checkout_on_the_windows_disk_even_through_a_symlink(self):
        # PR #44 review r1 R2: the logical path ~/rdm passed the /mnt/* check while the files were on the Windows disk.
        real = self._copy_checkout(self.root / "win" / "c" / "Users" / "dev" / "rdm")
        link = self.home / "rdm"
        link.symlink_to(real, target_is_directory=True)
        for checkout in (real, link):
            with self.subTest(checkout=str(checkout)):
                cp = self._wsl_run(checkout)
                self.assertEqual(cp.returncode, 10, cp.stdout + cp.stderr)
                self.assertIn("on the Windows disk", cp.stderr)
        self.assert_nothing_changed()

    def test_wsl_accepts_a_checkout_inside_wsl(self):
        (self.root / "win").mkdir()
        checkout = self._copy_checkout(self.home / "rdm")
        cp = self._wsl_run(checkout)
        self.assertNotIn("on the Windows disk", cp.stderr)

    def test_mount_escapes_are_decoded_before_the_credential_check(self):
        # PR #44 review r1 R1: /proc/mounts writes "host home" as host\040home, which the check used literally.
        self._host("Linux", "x86_64")
        for name, encoded in (("host home", "host\\040home"), ("back\\slash", "back\\134slash"), ("tab\there", "tab\\011here")):
            for fstype in ("virtiofs", "9p", "fuse.sshfs"):
                with self.subTest(name=name, fstype=fstype):
                    base = self.root / f"share-{fstype}"
                    home = base / name
                    (home / ".config" / "gh").mkdir(parents=True, exist_ok=True)
                    (home / ".config" / "gh" / "hosts.yml").write_text("not read\n")
                    self.mounts.write_text(f"/dev/vda1 / ext4 rw 0 0\nshare {base}/{encoded} {fstype} ro 0 0\n")
                    cp = self._run(UBUNTU, "--yes", env_extra=self.env)
                    self.assertEqual(cp.returncode, 10, cp.stdout + cp.stderr)
                    self.assertIn(f"{home}/.config/gh/hosts.yml", cp.stderr)
                    self.assert_nothing_changed()


class MacosTests(ScriptRun):
    def setUp(self):
        super().setUp()
        self._host("Darwin", "arm64")
        self._stub("python3", "#!/bin/sh\nexit 1\n")
        self._stub("git", "#!/bin/sh\nexit 1\n")
        # Without these the script would look at the real Homebrew and /Applications of the machine running the tests.
        self.env = {"GRDM_PREREQ_BREW_CANDIDATES": "", "GRDM_PREREQ_APPLICATIONS": str(self.root / "apps")}

    def _run(self, script, *args, env_extra=None):
        return super()._run(script, *args, env_extra=dict(self.env, **(env_extra or {})))

    def test_plan_uses_homebrew(self):
        self._stub("docker", DOCKER_OK)
        cp = self._run(MACOS, "--dry-run", "--yes", "--profile", "minimum")
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertIn("brew install python@3.12 git trivy gitleaks", cp.stdout)
        self.assertRegex(cp.stdout, r"would run: \S*installer/install\.sh --yes --profile minimum\n")
        self.assert_nothing_changed()

    def test_no_docker_runtime_stops_with_guidance(self):
        cp = self._run(MACOS, "--dry-run", "--yes")
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertIn("would stop with exit 11", cp.stdout)
        self.assertIn("Docker Desktop", cp.stdout)
        self.assert_nothing_changed()

    def test_linux_host_exits_10(self):
        self._host("Linux", "x86_64")
        cp = self._run(MACOS, "--dry-run", "--yes")
        self.assertEqual(cp.returncode, 10, cp.stderr)
        self.assertIn("install-ubuntu.sh", cp.stderr)


class SharedRules(unittest.TestCase):
    def test_syntax_on_the_bash_that_ships_with_macos(self):
        for script in (UBUNTU, MACOS, LIB):
            cp = subprocess.run([_bash(), "-n", str(script)], capture_output=True, text=True)
            self.assertEqual(cp.returncode, 0, f"{script.name}: {cp.stderr}")

    def test_help_is_english_then_japanese(self):
        for script in (UBUNTU, MACOS):
            cp = subprocess.run([_bash(), str(script), "--help"], capture_output=True, text=True, timeout=30)
            self.assertEqual(cp.returncode, 0, cp.stderr)
            self.assertLess(cp.stdout.index("Usage:"), cp.stdout.index("使い方:"))

    def test_scripts_are_executable_lf_and_end_at_install_sh(self):
        for script in (UBUNTU, MACOS):
            self.assertTrue(os.access(script, os.X_OK), f"{script.name} must be executable")
            self.assertNotIn(b"\r", script.read_bytes())
            self.assertEqual(script.read_text(encoding="utf-8").strip().splitlines()[-1].split()[0], "prereq_handover")
        self.assertIn('target="${PREREQ_ROOT}/installer/install.sh"', LIB.read_text(encoding="utf-8"))

    def test_no_pipe_to_shell_and_no_token_handling(self):
        pipe_to_shell = re.compile(r"(curl|wget)[^\n|]*\|\s*(sudo\s+)?(ba|z)?sh\b|Invoke-Expression|\biex\b")
        token_read = re.compile(r"(GH_TOKEN|GITHUB_TOKEN|ACCESS_TOKEN|Read-Host\s+-AsSecureString|read\s+-s)")
        for script in (UBUNTU, MACOS, LIB, WINDOWS):
            text = script.read_text(encoding="utf-8-sig")
            self.assertIsNone(pipe_to_shell.search(text), script.name)
            self.assertIsNone(token_read.search(text), script.name)

    def test_downloads_are_pinned(self):
        text = UBUNTU.read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r'_SUM="[0-9a-f]{64}"', text)), 4)
        self.assertIn("sha256sum -c --status", text)
        self.assertRegex(text, r'DOCKER_SIGNER_FPR="[0-9A-F]{40}"')

    def test_no_new_exit_codes(self):
        known = {line.split("\t")[0] for line in (INSTALLER / "grdm_dev" / "messages.tsv").read_text(encoding="utf-8").splitlines()}
        for script in (UBUNTU, MACOS, LIB):
            text = script.read_text(encoding="utf-8")
            for code in re.findall(r"prereq_(?:fail|stop|step) (\d+)", text):
                self.assertIn(code, known, f"{script.name}: exit {code}")
        for code in re.findall(r"Stop-Prereq (\d+)", WINDOWS.read_text(encoding="utf-8-sig")):
            self.assertIn(code, known, f"{WINDOWS.name}: exit {code}")


class WindowsBootScript(unittest.TestCase):
    """Runs the bash that install-windows.ps1 sends into WSL, taken from its $bootLines, under bash with a fake
    Windows-disk root (PR #44 review r1 R2: a home or checkout symlinked into /mnt/c passed a textual check)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.win = self.root / "win"
        (self.win / "c").mkdir(parents=True)
        self.boot = self._boot_text()

    @staticmethod
    def _boot_text():
        text = WINDOWS.read_text(encoding="utf-8-sig")
        block = text[text.index("$bootLines = @(") + len("$bootLines = @("):]
        block = block[:block.index("\n)")]
        lines = []
        for entry in block.strip().splitlines():
            entry = entry.strip().rstrip(",")
            if entry.startswith("'"):
                lines.append(entry[1:-1])
            else:  # a PowerShell expandable string: the four substitutions it uses
                entry = entry[1:-1].replace("`\"", "\"").replace("`$", "$")
                entry = entry.replace("$(ConvertTo-BashWord $Branch)", "develop").replace("$(ConvertTo-BashWord $RepoUrl)", "/nonexistent.git")
                entry = entry.replace("$Directory", "rdm").replace("$forwardWords", "--dry-run")
                lines.append(entry)
        return "\n".join(lines) + "\n"

    def _run(self, home):
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(home), "GRDM_WSL_WINDOWS_ROOT": str(self.win)}
        return subprocess.run([_bash(), "-c", self.boot], env=env, cwd=str(home), capture_output=True, text=True, timeout=60)

    def _checkout(self, path):
        (path / ".git").mkdir(parents=True)
        (path / "installer").mkdir()
        (path / "installer" / "install-ubuntu.sh").write_text('echo "reached install-ubuntu.sh $*"\n')
        return path

    def test_symlinked_checkout_on_the_windows_disk_is_refused(self):
        home = self.root / "home"
        home.mkdir()
        (home / "rdm").symlink_to(self._checkout(self.win / "c" / "rdm"), target_is_directory=True)
        cp = self._run(home)
        self.assertEqual(cp.returncode, 10, cp.stdout + cp.stderr)
        self.assertIn("is on the Windows disk", cp.stderr)
        self.assertNotIn("reached", cp.stdout)

    def test_symlinked_home_on_the_windows_disk_is_refused(self):
        real_home = self.win / "c" / "Users" / "dev"
        real_home.mkdir(parents=True)
        home = self.root / "home"
        home.symlink_to(real_home, target_is_directory=True)
        cp = self._run(home)
        self.assertEqual(cp.returncode, 10, cp.stdout + cp.stderr)
        self.assertIn("the WSL home directory is on the Windows disk", cp.stderr)

    def test_checkout_inside_wsl_is_used(self):
        home = self.root / "home"
        self._checkout(home / "rdm")
        cp = self._run(home)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        self.assertIn("reached install-ubuntu.sh --dry-run", cp.stdout)


class WindowsScriptText(unittest.TestCase):
    """Text-level rules only; `Parser.ParseFile` and the dry run happen on windows-latest (installer-prereq-lint.yml)."""

    def setUp(self):
        self.raw = WINDOWS.read_bytes()
        self.text = self.raw.decode("utf-8-sig")

    def test_bom_is_present(self):
        self.assertTrue(self.raw.startswith(b"\xef\xbb\xbf"), "Windows PowerShell 5.1 needs a BOM to read the Japanese strings")

    def test_consent_and_dry_run_flags(self):
        for needle in ("[switch]$Yes", "[switch]$DryRun", "'--yes'", "'--dry-run'", "Confirm-Step", "-Verb RunAs"):
            self.assertIn(needle, self.text)

    def test_clone_target_is_a_single_folder_name(self):
        self.assertIn(r"$Directory -notmatch '^[A-Za-z0-9._-]+$'", self.text)
        self.assertIn('home_real="$(pwd -P)"', self.text)  # the physical checks themselves run in WindowsBootScript

    def test_runs_the_ubuntu_script_inside_wsl(self):
        self.assertIn("exec bash installer/install-ubuntu.sh", self.text)
        self.assertIn("--distribution $Distro --cd '~' --exec bash -c", self.text)

    def test_checks_wsl_integration(self):
        self.assertIn("'docker', 'info'", self.text)
        self.assertIn("WSL Integration", self.text)

    def test_quotes_and_braces_balance_outside_strings(self):
        depth = 0
        quote = None
        lines = self.text.splitlines()
        in_here = False
        for line in lines:
            stripped = line.strip()
            if in_here:
                if stripped.startswith("'@"):
                    in_here = False
                continue
            if stripped.endswith("@'"):
                in_here = True
                continue
            i = 0
            while i < len(line):
                ch = line[i]
                if quote:
                    if ch == "`" and quote == '"':
                        i += 2
                        continue
                    if ch == quote:
                        if i + 1 < len(line) and line[i + 1] == quote:
                            i += 2
                            continue
                        quote = None
                elif ch in "'\"":
                    quote = ch
                elif ch == "#":
                    break
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    self.assertGreaterEqual(depth, 0)
                i += 1
        self.assertEqual(depth, 0)
        self.assertIsNone(quote)


class LineEndingRules(unittest.TestCase):
    def test_gitattributes_forces_lf_where_linux_runs(self):
        text = (REPO / ".gitattributes").read_text(encoding="utf-8")
        for pattern in ("*.sh ", "Dockerfile ", "installer/grdm_dev/templates/**", "installer/images/**", "manifest/**"):
            self.assertRegex(text, re.escape(pattern) + r"\s*text eol=lf")
        self.assertNotRegex(text, r"(?m)^\*\s+text=auto")

    def test_crlf_hint_is_portable(self):
        text = (INSTALLER / "install.sh").read_text(encoding="utf-8")
        self.assertNotIn('sed -i ""', text)
        self.assertIn("perl -pi -e", text)


if __name__ == "__main__":
    unittest.main()
