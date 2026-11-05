"""Unit tests for grdm-dev docs build | check (SPEC-02 §3, SPEC-06 §8)."""
from __future__ import annotations

import io
import unittest
from argparse import Namespace
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from grdm_dev import docs, exit_codes
from grdm_dev.context import Context, find_repo_root

REPO = find_repo_root(Path(__file__).resolve().parent)


def run_cmd(ctx, runner=None, mkdocs=None, **kw):
    args = Namespace(docs_action=None, all_warnings=False)
    for k, v in kw.items():
        setattr(args, k, v)
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = docs.run(ctx, args, runner=runner, mkdocs=mkdocs)
    return code, out.getvalue(), err.getvalue()


class DocsTests(unittest.TestCase):
    def setUp(self):
        self.ctx = Context(root=REPO, yes=True, stdin_is_tty=False)

    def test_check_wrapper_returns_0_on_repository(self):
        code, out, _ = run_cmd(self.ctx, docs_action="check")
        self.assertEqual(code, exit_codes.OK)
        self.assertIn("PASSED", out)

    def test_build_runs_mkdocs_strict_with_fake_runner(self):
        calls = []

        def runner(argv):
            calls.append(argv)
            return 0, ""

        code, out, _ = run_cmd(self.ctx, runner=runner, mkdocs="/fake/mkdocs", docs_action="build")
        self.assertEqual(code, exit_codes.OK)
        self.assertEqual(calls[0][:3], ["/fake/mkdocs", "build", "--strict"])
        self.assertIn(str(REPO / "mkdocs.yml"), calls[0])

    def test_build_failure_returns_1(self):
        code, _, err = run_cmd(self.ctx, runner=lambda argv: (1, ""), mkdocs="/fake/mkdocs", docs_action="build")
        self.assertEqual(code, 1)
        self.assertIn("failed", err)

    def test_build_without_mkdocs_is_exit_2_with_install_hint(self):
        code, _, err = run_cmd(self.ctx, runner=lambda argv: (127, ""), mkdocs="/nonexistent/mkdocs", docs_action="build")
        self.assertEqual(code, exit_codes.USAGE)
        self.assertIn(docs.INSTALL_HINT, err)

    def test_missing_action_is_usage(self):
        code, _, _ = run_cmd(self.ctx)
        self.assertEqual(code, exit_codes.USAGE)


if __name__ == "__main__":
    unittest.main()
