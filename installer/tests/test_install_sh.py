"""Tests for installer/install.sh (SPEC-02 §2.1): syntax, --help, old python -> exit 10, CRLF -> exit 2.

The script is copied into a temporary tree with a fake `python3` so no real .venv/ is created.
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "installer" / "install.sh"
MESSAGES = REPO / "installer" / "grdm_dev" / "messages.tsv"

FAKE_PY = """#!/bin/sh
# Fake python3 reporting {version}: understands the two -c snippets install.sh uses.
case "$*" in
  *version_info*'>='*) exit {ok} ;;
  *version_info*) echo '{version}' ;;
  *) exit 99 ;;
esac
"""


def _which_bash():
    return shutil.which("bash") or "/bin/bash"


class InstallShTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "installer" / "grdm_dev").mkdir(parents=True)
        (root / "bin").mkdir()
        # Only these tools are on PATH, so the host's own python3 is never found by accident.
        (root / "tools").mkdir()
        for tool in ("grep", "awk", "sed", "uname", "dirname", "cat", "rm", "tr", "head", "bash"):
            src = shutil.which(tool)
            if src:
                os.symlink(src, root / "tools" / tool)
        self.script = root / "installer" / "install.sh"
        shutil.copy(SCRIPT, self.script)
        shutil.copy(MESSAGES, root / "installer" / "grdm_dev" / "messages.tsv")
        self.root = root
        self.bin = root / "bin"

    def tearDown(self):
        self.tmp.cleanup()

    def _fake_python(self, version="3.9.19", ok=False):
        for name in ("python3", "python3.13", "python3.12", "python3.11", "python"):
            p = self.bin / name
            p.write_text(FAKE_PY.format(version=version, ok=0 if ok else 1))
            p.chmod(0o755)

    def _run(self, *args, env_extra=None):
        env = {"PATH": f"{self.bin}:{self.root / 'tools'}", "HOME": self.tmp.name, "LANG": "C"}
        env.update(env_extra or {})
        return subprocess.run([_which_bash(), str(self.script), *args], env=env, capture_output=True, text=True, timeout=60)

    def test_bash_n_syntax(self):
        cp = subprocess.run([_which_bash(), "-n", str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(cp.returncode, 0, cp.stderr)

    def test_is_executable_and_has_no_crlf(self):
        self.assertTrue(os.access(SCRIPT, os.X_OK), "install.sh must be executable")
        self.assertNotIn(b"\r", SCRIPT.read_bytes())

    def test_help_is_english_then_japanese(self):
        cp = self._run("--help")
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertIn("Usage:", cp.stdout)
        self.assertIn("使い方:", cp.stdout)
        self.assertLess(cp.stdout.index("Usage:"), cp.stdout.index("使い方:"))

    def test_old_python_exits_10_with_hint(self):
        self._fake_python("3.9.19", ok=False)
        cp = self._run("--yes")
        self.assertEqual(cp.returncode, 10, cp.stderr)
        self.assertIn("exit 10", cp.stderr)
        # Same wording as messages.tsv row 10, English and Japanese.
        self.assertIn("host unsupported", cp.stderr)
        self.assertIn("ホスト非対応", cp.stderr)
        self.assertIn("3.9.19", cp.stderr)
        # A per-OS hint is printed (brew / apt / python.org).
        self.assertTrue(any(k in cp.stderr for k in ("brew install", "apt install", "python.org")), cp.stderr)
        self.assertFalse((self.root / ".venv").exists())

    def test_no_python_exits_10(self):
        cp = self._run("--yes")  # PATH has no python at all
        self.assertEqual(cp.returncode, 10, cp.stderr)
        self.assertIn("python3 not found", cp.stderr)
        self.assertFalse((self.root / ".venv").exists())

    def test_crlf_script_exits_2(self):
        data = self.script.read_bytes().replace(b"\n", b"\r\n")
        self.script.write_bytes(data)
        self._fake_python("3.12.0", ok=True)
        cp = self._run("--yes")
        self.assertEqual(cp.returncode, 2, cp.stderr)
        self.assertIn("CRLF", cp.stderr)
        self.assertIn("usage error", cp.stderr)
        self.assertFalse((self.root / ".venv").exists())

    def test_messages_tsv_rows_are_used(self):
        # The awk lookup reads messages.tsv: changing row 10 changes the output.
        tsv = self.root / "installer" / "grdm_dev" / "messages.tsv"
        tsv.write_text(tsv.read_text().replace("host unsupported", "HOST-UNSUPPORTED-MARKER"))
        self._fake_python("3.8.0", ok=False)
        cp = self._run()
        self.assertEqual(cp.returncode, 10)
        self.assertIn("HOST-UNSUPPORTED-MARKER", cp.stderr)


if __name__ == "__main__":
    unittest.main()
