"""Unit tests for tools/manifest_check.py (SPEC-01 MC checks, TOON parity, policy scan).

Run from the repository root:  python3 -m unittest discover -s tools/tests
"""

from __future__ import annotations

import contextlib
import copy
import datetime as dt
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import manifest_check as mc  # noqa: E402

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "0123456789abcdef0123456789abcdef01234567"
TODAY = dt.date(2026, 11, 5)


def valid_manifest() -> dict:
    return {
        "schema_version": 1,
        "generated_at": "2026-11-05",
        "note": "Names and SHAs only.",
        "components": [
            {
                "id": "osf.io",
                "role": "core",
                "services": ["web", "api"],
                "integration_repo": "RDM-osf.io-dev2027",
                "integration_branch": "develop",
                "upstreams": [
                    {"repo": "RDM-osf.io", "branch": "develop", "kind": "public",
                     "tracking_branch": "upstream/public-develop", "status": "merged",
                     "sha": SHA_A, "fetched_at": "2026-11-05"},
                    {"repo": "RDM-osf.io-develop-private", "branch": "develop", "kind": "private",
                     "tracking_branch": "upstream/private-develop", "status": "merged",
                     "sha": SHA_B, "fetched_at": "2026-11-05"},
                    {"repo": "CenterForOpenScience/osf.io", "branch": "develop", "kind": "cos",
                     "tracking_branch": "upstream/cos-develop", "status": "reference",
                     "sha": SHA_C, "fetched_at": "2026-11-05"},
                    {"repo": "RDM-osf.io-private", "branch": "fix/sec-test", "kind": "private",
                     "tracking_branch": "upstream/private-sec-test-fix-sec-test", "status": "candidate",
                     "sha": SHA_C, "fetched_at": "2026-11-05"},
                ],
                "adopted_prs": [
                    {"repo": "RDM-osf.io", "number": 796, "title": "t", "reason": "r", "status": "adopted"},
                ],
                "candidate_prs": [
                    {"repo": "RDM-osf.io", "number": 812, "title": "t", "reason": "r", "status": "candidate"},
                ],
                "base_image": "python:3.6-slim",
                "base_image_digest": None,
                "target_image": {"M4": "python:3.13-slim", "M5": None},
                "profile": "minimum",
                "platforms": ["linux/arm64", "linux/amd64"],
                "note": None,
            },
            {
                "id": "postgres",
                "role": "infra",
                "services": ["postgres"],
                "integration_repo": None,
                "integration_branch": None,
                "upstreams": [],
                "adopted_prs": [],
                "candidate_prs": [],
                "base_image": "postgres:9.6",
                "base_image_digest": None,
                "target_image": {"M4": None, "M5": "postgres:15"},
                "profile": "minimum",
                "platforms": ["linux/arm64", "linux/amd64"],
                "note": None,
            },
        ],
    }


VALID_TOON = f"""schema_version: 1
generated_at: 2026-11-05
note: "Names and SHAs only."
components[2]:
  - id: osf.io
    role: core
    integration_repo: RDM-osf.io-dev2027
    profile: minimum
    upstreams[4]{{repo,branch,kind,tracking_branch,status,sha,fetched_at}}:
      RDM-osf.io,develop,public,upstream/public-develop,merged,{SHA_A},2026-11-05
      RDM-osf.io-develop-private,develop,private,upstream/private-develop,merged,{SHA_B},2026-11-05
      CenterForOpenScience/osf.io,develop,cos,upstream/cos-develop,reference,{SHA_C},2026-11-05
      RDM-osf.io-private,fix/sec-test,private,upstream/private-sec-test-fix-sec-test,candidate,{SHA_C},2026-11-05
    adopted_prs[1]{{repo,number,status}}:
      RDM-osf.io,796,adopted
  - id: postgres
    role: infra
    integration_repo: null
    profile: minimum
    upstreams[0]:
    adopted_prs[0]:
"""


def codes(errors: list[str]) -> set[str]:
    return {e.split(":", 1)[0] for e in errors}


class ValidateManifestTests(unittest.TestCase):
    def test_valid_manifest_passes(self):
        self.assertEqual(mc.validate_manifest(valid_manifest(), today=TODAY), [])

    def test_bad_role_fails(self):
        data = valid_manifest()
        data["components"][0]["role"] = "plugin"
        errors = mc.validate_manifest(data, today=TODAY)
        self.assertIn("MC-03", codes(errors))

    def test_missing_sha_fails(self):
        data = valid_manifest()
        del data["components"][0]["upstreams"][0]["sha"]
        errors = mc.validate_manifest(data, today=TODAY)
        self.assertIn("MC-06", codes(errors))
        self.assertTrue(any("sha" in e for e in errors))

    def test_short_or_uppercase_sha_fails(self):
        data = valid_manifest()
        data["components"][0]["upstreams"][0]["sha"] = "ABC"
        self.assertIn("MC-06", codes(mc.validate_manifest(data, today=TODAY)))

    def test_future_fetched_at_fails(self):
        data = valid_manifest()
        data["components"][0]["upstreams"][0]["fetched_at"] = "2030-01-01"
        self.assertIn("MC-06", codes(mc.validate_manifest(data, today=TODAY)))

    def test_bad_tracking_branch_fails_rule_7(self):
        data = valid_manifest()
        data["components"][0]["upstreams"][0]["tracking_branch"] = "upstream/develop"
        self.assertIn("MC-13", codes(mc.validate_manifest(data, today=TODAY)))

    def test_tagged_tracking_branch_needs_two_of_same_kind(self):
        data = valid_manifest()
        # drop the second private upstream, so the tag form is no longer allowed
        data["components"][0]["upstreams"].pop(1)
        self.assertIn("MC-13", codes(mc.validate_manifest(data, today=TODAY)))

    def test_bad_integration_repo_fails(self):
        data = valid_manifest()
        data["components"][0]["integration_repo"] = "RDM-osf.io"
        self.assertIn("MC-04", codes(mc.validate_manifest(data, today=TODAY)))
        data["components"][1]["integration_repo"] = "RDM-postgres-dev2027"
        self.assertIn("MC-04", codes(mc.validate_manifest(data, today=TODAY)))

    def test_pr_number_and_status(self):
        data = valid_manifest()
        data["components"][0]["adopted_prs"][0]["number"] = 0
        self.assertIn("MC-09", codes(mc.validate_manifest(data, today=TODAY)))
        data = valid_manifest()
        data["components"][0]["adopted_prs"][0]["status"] = "candidate"
        self.assertIn("MC-09", codes(mc.validate_manifest(data, today=TODAY)))
        data = valid_manifest()
        data["components"][0]["candidate_prs"][0]["status"] = "adopted"
        self.assertIn("MC-09", codes(mc.validate_manifest(data, today=TODAY)))

    def test_cos_upstream_must_be_reference(self):
        data = valid_manifest()
        data["components"][0]["upstreams"][2]["status"] = "merged"
        self.assertIn("MC-09", codes(mc.validate_manifest(data, today=TODAY)))

    def test_same_repo_branch_different_sha_fails(self):
        data = valid_manifest()
        other = copy.deepcopy(data["components"][0])
        other["id"] = "second"
        other["integration_repo"] = "RDM-second-dev2027"
        other["upstreams"][0]["sha"] = SHA_B
        data["components"].append(other)
        self.assertIn("MC-08", codes(mc.validate_manifest(data, today=TODAY)))

    def test_url_in_value_fails(self):
        data = valid_manifest()
        data["components"][0]["note"] = "see https://github.com/example/x"
        self.assertIn("MC-07", codes(mc.validate_manifest(data, today=TODAY)))

    def test_token_in_value_fails(self):
        data = valid_manifest()
        data["components"][0]["note"] = "token " + "ghp" + "_" + "A" * 36
        self.assertIn("MC-07", codes(mc.validate_manifest(data, today=TODAY)))

    def test_core_needs_both_platforms(self):
        data = valid_manifest()
        data["components"][0]["platforms"] = ["linux/arm64"]
        self.assertIn("MC-10", codes(mc.validate_manifest(data, today=TODAY)))

    def test_duplicate_id_fails(self):
        data = valid_manifest()
        data["components"][1]["id"] = "osf.io"
        self.assertIn("MC-02", codes(mc.validate_manifest(data, today=TODAY)))


class ToonParityTests(unittest.TestCase):
    def test_parse_toon_roundtrip(self):
        parsed = mc.parse_toon(VALID_TOON)
        self.assertEqual(parsed, mc.project_manifest(valid_manifest()))

    def test_matching_toon_passes(self):
        self.assertEqual(mc.compare_toon(valid_manifest(), mc.parse_toon(VALID_TOON)), [])

    def test_changed_sha_fails(self):
        stale = VALID_TOON.replace(SHA_A, "f" * 40, 1)
        errors = mc.compare_toon(valid_manifest(), mc.parse_toon(stale))
        self.assertTrue(errors)
        self.assertTrue(any("upstreams[0].sha" in e for e in errors))

    def test_changed_pr_number_and_profile_fail(self):
        stale = VALID_TOON.replace("RDM-osf.io,796,adopted", "RDM-osf.io,797,adopted")
        self.assertTrue(any("adopted_prs[0].number" in e for e in mc.compare_toon(valid_manifest(), mc.parse_toon(stale))))
        stale = VALID_TOON.replace("profile: minimum\n    upstreams[4]", "profile: core\n    upstreams[4]")
        self.assertTrue(any("profile" in e for e in mc.compare_toon(valid_manifest(), mc.parse_toon(stale))))

    def test_missing_component_fails(self):
        data = valid_manifest()
        data["components"].append(copy.deepcopy(data["components"][1]) | {"id": "redis", "services": ["redis"]})
        errors = mc.compare_toon(data, mc.parse_toon(VALID_TOON))
        self.assertTrue(any("count" in e for e in errors))
        self.assertTrue(any("'redis'" in e for e in errors))

    def test_wrong_row_count_is_a_parse_error(self):
        broken = VALID_TOON.replace("upstreams[4]{", "upstreams[3]{")
        with self.assertRaises(mc.ToonError):
            mc.parse_toon(broken)

    def test_missing_toon_file_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors = mc.validate_toon_parity(valid_manifest(), Path(tmp) / "upstreams.toon")
        self.assertEqual(len(errors), 1)
        self.assertIn("missing", errors[0])

    def test_check_manifest_files_reports_stale_toon(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "upstreams.json").write_text(json.dumps(valid_manifest()), encoding="utf-8")
            (root / "upstreams.toon").write_text(VALID_TOON.replace(SHA_B, "e" * 40), encoding="utf-8")
            errors = mc.check_manifest_files(root / "upstreams.json", root / "upstreams.toon")
        self.assertTrue(errors)
        self.assertTrue(all(e.startswith("MC-11") for e in errors))


class PolicyScanTests(unittest.TestCase):
    def test_private_url_in_text_fails(self):
        # Built at run time so that this test file never contains a private URL literal
        # (the policy scan covers tools/tests/ too).
        dev, priv = "-dev" + "2027", "-priv" + "ate"
        for url in (
            "https://github.com/RCOSDP/RDM-osf.io" + dev,
            "https://github.com/rcosdp/RDM-osf.io" + dev,
            "git@github.com:RCOSDP/RDM-osf.io" + priv + ".git",
            "ssh://git@github.com/RCOSDP/RDM-osf.io-develop" + priv + ".git",
        ):
            findings = mc.scan_text_for_policy(f"see {url} here\n", "x.md")
            self.assertEqual(len(findings), 1, url)
            self.assertNotIn("github.com", findings[0])  # the URL itself is never echoed

    def test_public_url_and_bare_names_pass(self):
        text = "https://github.com/RCOSDP/RDM-osf.io and the name RDM-osf.io-dev2027 and RDM-osf.io-private\n"
        self.assertEqual(mc.scan_text_for_policy(text, "x.md"), [])

    def test_synthetic_tokens_fail(self):
        ghp = "ghp" + "_" + "x" * 36
        akia = "AKIA" + "Q" * 16
        key = "-----BEGIN " + "RSA PRIVATE KEY-----"
        for sample in (ghp, akia, key):
            self.assertTrue(mc.scan_text_for_policy(sample + "\n", "x.txt"), sample)

    def test_exclusions(self):
        self.assertTrue(mc.policy_excluded("site/index.html"))
        self.assertTrue(mc.policy_excluded("docs/guides/api/README.legacy.md"))
        self.assertTrue(mc.policy_excluded("docs/guides/api/osf/addon/x.py"))
        self.assertFalse(mc.policy_excluded("docs/guides/api/README.md"))
        self.assertFalse(mc.policy_excluded("manifest/README.md"))

    def test_run_policy_scan_on_file_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.md").write_text("git@github.com:RCOSDP/RDM-x" + "-dev2027" + ".git\n", encoding="utf-8")
            (root / "b.md").write_text("clean\n", encoding="utf-8")
            findings = mc.run_policy_scan(root, files=["a.md", "b.md"])
        self.assertEqual(len(findings), 1)
        self.assertTrue(findings[0].startswith("a.md:1:"))


class CliTests(unittest.TestCase):
    def test_exit_codes_are_documented(self):
        self.assertEqual(mc.EXIT_MANIFEST, 20)
        self.assertEqual(mc.EXIT_POLICY, 1)
        self.assertIn("20", mc.__doc__)

    def test_manifest_only_exit_20_on_missing_toon(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "manifest").mkdir()
            (root / "manifest" / "upstreams.json").write_text(json.dumps(valid_manifest()), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                code = mc.main(["--manifest-only", "--root", tmp])
        self.assertEqual(code, 20)


if __name__ == "__main__":
    unittest.main()
