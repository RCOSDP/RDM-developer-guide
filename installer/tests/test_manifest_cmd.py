"""Unit tests for grdm-dev manifest check | toon (SPEC-01, SPEC-02 §3)."""
from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from grdm_dev import exit_codes, manifest_cmd
from grdm_dev.context import Context, find_repo_root

REPO = find_repo_root(Path(__file__).resolve().parent)


def run_cmd(ctx, **kw):
    args = Namespace(manifest_action=None, manifest_only=False, policy_only=False, check=False, write=False)
    for k, v in kw.items():
        setattr(args, k, v)
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = manifest_cmd.run(ctx, args)
    return code, out.getvalue(), err.getvalue()


class ManifestCheckTests(unittest.TestCase):
    def setUp(self):
        self.ctx = Context(root=REPO, yes=True, stdin_is_tty=False)

    def test_check_passes_on_repository_manifest(self):
        code, out, _ = run_cmd(self.ctx, manifest_action="check", manifest_only=True)
        self.assertEqual(code, exit_codes.OK)
        self.assertIn("PASSED", out)

    def test_map_exit_codes(self):
        self.assertEqual(manifest_cmd.map_check_exit(0), exit_codes.OK)
        self.assertEqual(manifest_cmd.map_check_exit(20), exit_codes.MANIFEST_INVALID)
        self.assertEqual(manifest_cmd.map_check_exit(1), 1)
        self.assertEqual(manifest_cmd.map_check_exit(2), exit_codes.USAGE)

    def test_invalid_manifest_exits_20(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "manifest").mkdir()
            (root / "tools").mkdir()
            shutil.copy(REPO / "tools" / "manifest_check.py", root / "tools" / "manifest_check.py")
            (root / "manifest" / "upstreams.json").write_text('{"schema_version": 2, "components": "nope"}')
            ctx = Context(root=root, yes=True, stdin_is_tty=False)
            code, _, err = run_cmd(ctx, manifest_action="check", manifest_only=True)
            self.assertEqual(code, exit_codes.MANIFEST_INVALID)
            self.assertIn("exit 20", err)

    def test_missing_action_is_usage(self):
        code, _, _ = run_cmd(self.ctx)
        self.assertEqual(code, exit_codes.USAGE)


class ManifestToonTests(unittest.TestCase):
    def setUp(self):
        self.ctx = Context(root=REPO, yes=True, stdin_is_tty=False)

    def test_toon_equals_committed_excerpt(self):
        code, out, _ = run_cmd(self.ctx, manifest_action="toon")
        self.assertEqual(code, exit_codes.OK)
        self.assertEqual(out, (REPO / "manifest" / "upstreams.toon").read_text(encoding="utf-8"))

    def test_toon_check_detects_stale_excerpt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "manifest").mkdir()
            (root / "tools").mkdir()
            shutil.copy(REPO / "tools" / "manifest_check.py", root / "tools")
            shutil.copy(REPO / "manifest" / "upstreams.json", root / "manifest")
            (root / "manifest" / "upstreams.toon").write_text("schema_version: 1\n")
            ctx = Context(root=root, yes=True, stdin_is_tty=False)
            code, _, err = run_cmd(ctx, manifest_action="toon", check=True)
            self.assertEqual(code, exit_codes.MANIFEST_INVALID)
            code, out, _ = run_cmd(ctx, manifest_action="toon", write=True)
            self.assertEqual(code, exit_codes.OK)
            code, _, _ = run_cmd(ctx, manifest_action="toon", check=True)
            self.assertEqual(code, exit_codes.OK)

    def test_excerpt_parses_back_to_the_projection(self):
        mc = manifest_cmd.load_tool(REPO, "manifest_check")
        data = json.loads((REPO / "manifest" / "upstreams.json").read_text(encoding="utf-8"))
        parsed = mc.parse_toon(manifest_cmd.excerpt(data, mc))
        self.assertEqual(mc.compare_toon(data, parsed), [])


if __name__ == "__main__":
    unittest.main()
