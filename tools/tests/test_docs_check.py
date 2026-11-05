"""Unit tests for tools/docs_check.py (SPEC-06 §8 checks).

Run from the repository root:  python3 -m unittest discover -s tools/tests
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import docs_check as dc  # noqa: E402

SHA_A = "a" * 40
SHA_B = "b" * 40

HEADER = """# Title / 題

> **Summary:** s
> **概要:** s

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-05

---

<a id="english"></a>
## English

### 2. Component map

Body text.

<a id="japanese"></a>
## 日本語

本文。
"""


class _Repo:
    """A throw-away repository root with docs/ and helper writers."""

    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "docs").mkdir()

    def write(self, rel: str, text: str) -> str:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return rel

    def check(self, rel: str, terms: list[str] | None = None) -> dc.FileResult:
        return dc.check_file(rel, self.root, terms or [])

    def cleanup(self):
        self._tmp.cleanup()


class DocsCheckTests(unittest.TestCase):
    def setUp(self):
        self.repo = _Repo()
        self.addCleanup(self.repo.cleanup)

    def test_compliant_document_passes(self):
        rel = self.repo.write("docs/a.md", HEADER)
        self.assertEqual(self.repo.check(rel).errors, [])

    def test_missing_same_file_anchor_fails(self):
        rel = self.repo.write("docs/a.md", HEADER + "\nSee [there](#nowhere).\n")
        errors = self.repo.check(rel).errors
        self.assertTrue(any("#nowhere" in e for e in errors), errors)

    def test_existing_anchor_and_heading_slug_pass(self):
        rel = self.repo.write("docs/a.md", HEADER + "\n[jp](#japanese) and [map](#2-component-map)\n")
        self.assertEqual(self.repo.check(rel).errors, [])

    def test_broken_file_with_fragment_fails(self):
        rel = self.repo.write("docs/a.md", HEADER + "\n[x](absent-file.md#english)\n")
        errors = self.repo.check(rel).errors
        self.assertTrue(any("absent-file.md#english" in e for e in errors), errors)

    def test_fragment_missing_in_existing_target_fails(self):
        self.repo.write("docs/b.md", HEADER)
        rel = self.repo.write("docs/a.md", HEADER + "\n[ok](b.md#english) [bad](b.md#no-such-id)\n")
        errors = self.repo.check(rel).errors
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("#no-such-id", errors[0])

    def test_links_inside_code_are_ignored(self):
        rel = self.repo.write("docs/a.md", HEADER + "\n```md\n[x](missing.md)\n```\n`[y](also-missing.md)`\n")
        self.assertEqual(self.repo.check(rel).errors, [])

    def test_pointer_file_exemption(self):
        self.repo.write("docs/guides/README.md", HEADER)
        self.repo.write("docs/guides/skeleton/README.md", HEADER)
        rel = self.repo.write(
            "Skelton/README.md",
            "# Skeleton\n\nMoved to [docs/guides/skeleton/](../docs/guides/skeleton/).\n\n- [index](../docs/guides/README.md)\n",
        )
        result = self.repo.check(rel)
        self.assertEqual(result.category, "pointer")
        self.assertEqual(result.errors, [])  # no anchors / jump / version required

    def test_pointer_file_with_broken_link_fails(self):
        rel = self.repo.write("Environment.md", "# Env\n\nMoved to [here](docs/guides/environment/).\n")
        result = self.repo.check(rel)
        self.assertEqual(result.category, "pointer")
        self.assertTrue(any("non-existent" in e for e in result.errors), result.errors)

    def test_classification_of_exceptions(self):
        self.assertEqual(dc.classify("docs/guides/api/README.legacy.md")[0], "legacy")
        self.assertEqual(dc.classify("docs/guides/api/Decorators.md")[0], "sample")
        self.assertEqual(dc.classify("docs/guides/api/osf/addon/README.md")[0], "sample")
        self.assertEqual(dc.classify("docs/guides/api/README.md")[0], "full")
        self.assertEqual(dc.classify("manifest/README.md")[0], "full")
        self.assertEqual(dc.classify("installer/README.md")[0], "full")
        self.assertEqual(dc.classify("APIGuide/README.md")[0], "pointer")

    def test_legacy_and_sample_are_skipped(self):
        rel = self.repo.write("docs/guides/x/README.legacy.md", "no anchors at all")
        self.assertEqual(self.repo.check(rel).errors, [])
        rel = self.repo.write("docs/guides/x/code/README.md", "no anchors at all")
        self.assertEqual(self.repo.check(rel).errors, [])

    def test_toon_sha_mismatch_fails(self):
        self.repo.write("manifest/upstreams.json", json.dumps({"components": [{"upstreams": [{"sha": SHA_A}]}]}))
        body = (
            "\n<!-- canonical: manifest/upstreams.json -->\n```toon\n"
            f"upstreams[1]{{repo,sha}}:\n  RDM-x,{SHA_B}\n```\n"
        )
        rel = self.repo.write("docs/a.md", HEADER + body)
        errors = self.repo.check(rel).errors
        self.assertTrue(any(SHA_B in e and "stale" in e for e in errors), errors)

    def test_toon_sha_match_passes_and_inline_declaration(self):
        self.repo.write("manifest/upstreams.json", json.dumps({"sha": SHA_A}))
        body = f"\nThe canonical file is `manifest/upstreams.json`; canonical: `manifest/upstreams.json`.\n```toon\nrow: {SHA_A}\n```\n"
        rel = self.repo.write("docs/a.md", HEADER + body)
        self.assertEqual(self.repo.check(rel).errors, [])

    def test_toon_missing_canonical_json_fails(self):
        body = "\n<!-- canonical: manifest/nope.json -->\n```toon\nrow: 1\n```\n"
        rel = self.repo.write("docs/a.md", HEADER + body)
        errors = self.repo.check(rel).errors
        self.assertTrue(any("does not exist" in e for e in errors), errors)

    def test_toon_without_declaration_is_not_checked(self):
        body = f"\n```toon\nrow: {SHA_B}\n```\n"
        rel = self.repo.write("docs/a.md", HEADER + body)
        self.assertEqual(self.repo.check(rel).errors, [])

    def test_glossary_warning_does_not_fail(self):
        body = "\nThe manifest pins every Upstream. A Mirror (an automatic copy) is refreshed daily.\n"
        text = HEADER.replace("Body text.\n", body)
        rel = self.repo.write("docs/a.md", text)
        result = self.repo.check(rel, terms=["Upstream", "Mirror"])
        self.assertEqual(result.errors, [])
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("'Upstream'", result.warnings[0])

    def test_glossary_warning_skips_review_records(self):
        body = "\nThe manifest pins every Upstream.\n"
        text = HEADER.replace("Body text.\n", body)
        rel = self.repo.write("docs/reviews/2026-11-06_PR99_r1.md", text)
        result = self.repo.check(rel, terms=["Upstream"])
        self.assertEqual(result.errors, [])  # anchors, links and version are still checked
        self.assertEqual(result.warnings, [])  # review records are kept verbatim (SPEC-06 §8)
        self.assertFalse(dc.glossary_check_applies("docs/reviews/README.md"))
        self.assertFalse(dc.glossary_check_applies("docs/reference/REF-01_Glossary.md"))
        self.assertTrue(dc.glossary_check_applies("docs/spec/00_overview.md"))
        rel = self.repo.write("docs/spec/a.md", text)
        self.assertEqual(len(self.repo.check(rel, terms=["Upstream"]).warnings), 1)

    def test_review_record_still_fails_other_checks(self):
        # the exemption covers the glossary warning only: anchors, Jump, Version and links still fail
        broken = HEADER.replace('<a id="japanese"></a>\n', "").replace("- Version / 版: 0.1 — 2026-11-05\n", "")
        rel = self.repo.write("docs/reviews/2026-11-06_PR99_r2.md", broken + "\nSee [gone](missing.md).\n")
        result = self.repo.check(rel, terms=["Upstream"])
        self.assertEqual(result.warnings, [])
        joined = "\n".join(result.errors)
        self.assertIn('<a id="japanese">', joined)
        self.assertIn("Version", joined)
        self.assertIn("missing.md", joined)

    def test_glossary_terms_loaded_from_ref01(self):
        self.repo.write(
            "docs/reference/REF-01_Glossary.md",
            '<a id="english"></a>\n| Term | For everyone |\n|---|---|\n| Pull request (PR) | x |\n| Loopback / localhost | y |\n<a id="japanese"></a>\n',
        )
        self.assertEqual(dc.load_glossary_terms(self.repo.root), ["Pull request", "PR", "Loopback", "localhost"])


if __name__ == "__main__":
    unittest.main()
