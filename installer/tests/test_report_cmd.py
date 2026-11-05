"""Unit tests for grdm-dev report (SPEC-02 §3): bundling of *_latest.json reports."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path

from grdm_dev import exit_codes, report_cmd
from grdm_dev.context import Context


class ReportCmdTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "runtime" / "reports").mkdir(parents=True)
        self.ctx = Context(root=self.root, yes=True, json_output=True, stdin_is_tty=False)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_latest(self, name, data):
        (self.root / "runtime" / "reports" / f"{name}_latest.json").write_text(json.dumps(data))

    def run_report(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = report_cmd.run(self.ctx, Namespace())
        return code, json.loads(out.getvalue())

    def test_bundles_existing_reports_and_writes_files(self):
        self._write_latest("doctor", {"os": "macos", "exit_code": 0})
        self._write_latest("scan", {"gate": "pass", "exit_code": 0, "findings_total": 3})
        code, data = self.run_report()
        self.assertEqual(code, exit_codes.OK)
        self.assertEqual(data["overall"], "partial")
        self.assertEqual(data["present"], ["doctor", "scan"])
        self.assertEqual(data["missing"], ["plan", "health", "accept"])
        self.assertEqual(data["bundle"]["scan"]["findings_total"], 3)
        rows = {r["name"]: r for r in data["reports"]}
        self.assertTrue(rows["doctor"]["present"] and rows["doctor"]["timestamp"])
        self.assertEqual(rows["doctor"]["status"], "ok")
        self.assertFalse(rows["health"]["present"])
        files = sorted(p.name for p in (self.root / "runtime" / "reports").glob("report_*"))
        self.assertTrue(any(f.endswith(".json") and f != "report_latest.json" for f in files))
        self.assertTrue(any(f.endswith(".toon") for f in files))
        self.assertIn("report_latest.json", files)

    def test_failed_report_marks_overall_fail_and_secrets_are_masked(self):
        (self.root / "runtime" / ".env").write_text("DB_PASSWORD=verysecretpw123\n")
        self._write_latest("health", {"exit_code": 40, "detail": "db url postgres://u:verysecretpw123@db"})
        code, data = self.run_report()
        self.assertEqual(code, exit_codes.OK)
        self.assertEqual(data["overall"], "fail")
        self.assertEqual(data["failed"], ["health"])
        self.assertNotIn("verysecretpw123", json.dumps(data))
        self.assertNotIn("verysecretpw123", (self.root / "runtime" / "reports" / "report_latest.json").read_text())

    def test_empty_reports_dir(self):
        code, data = self.run_report()
        self.assertEqual(code, exit_codes.OK)
        self.assertEqual(data["overall"], "empty")
        self.assertEqual(len(data["reports"]), 5)


if __name__ == "__main__":
    unittest.main()
