"""Unit tests for tools/manifest_check.py (SPEC-01 MC checks, TOON parity, policy scan).

Run from the repository root:  python3 -m unittest discover -s tools/tests
"""

from __future__ import annotations

import contextlib
import copy
import datetime as dt
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))

import manifest_check as mc  # noqa: E402


def private_address(form: str, repo: str) -> str:
    """Build a prohibited private-repository address at run time, so that this test
    source never contains one literally (the policy scan covers tools/tests/ too)."""
    host = "github" + "." + "com"
    if form == "https":
        return "https://" + host + "/RCOSDP/" + repo
    if form == "scp":
        return "git@" + host + ":RCOSDP/" + repo + ".git"
    if form == "ssh":
        return "ssh://git@" + host + "/RCOSDP/" + repo + ".git"
    raise ValueError(form)


DEV2027 = "-dev" + "2027"
PRIVATE = "-priv" + "ate"

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


PREBUILT_DIGEST = "sha256:" + "a" * 64
PREBUILT_REF = "niicloudoperation/rdm-ember-osf-web@" + PREBUILT_DIGEST


def prebuilt_manifest(ref=PREBUILT_REF, note="schema-1 base image refused by Docker; remove at M4") -> dict:
    m = valid_manifest()
    m["components"][0]["prebuilt_image"] = ref
    m["components"][0]["note"] = note
    return m


class PrebuiltImageTests(unittest.TestCase):
    """SPEC-01 §3 `prebuilt_image`: digest-pinned, with a note, never a private URL, not on infra (MC-06)."""

    def test_digest_pinned_reference_with_note_passes(self):
        self.assertEqual(mc.validate_manifest(prebuilt_manifest(), today=TODAY), [])

    def test_null_and_absent_pass(self):
        m = valid_manifest()
        m["components"][0]["prebuilt_image"] = None
        self.assertEqual(mc.validate_manifest(m, today=TODAY), [])
        self.assertEqual(mc.validate_manifest(valid_manifest(), today=TODAY), [])

    def test_registry_host_port_and_tag_before_digest_pass(self):
        m = prebuilt_manifest(ref="registry.example:5000/team/rdm-ember-osf-web:latest@" + PREBUILT_DIGEST)
        self.assertEqual(mc.validate_manifest(m, today=TODAY), [])

    def test_tag_only_or_short_digest_fails(self):
        for ref in ("niicloudoperation/rdm-ember-osf-web:latest", "niicloudoperation/rdm-ember-osf-web@sha256:" + "a" * 63,
                    "niicloudoperation/rdm-ember-osf-web@sha1:" + "a" * 64, "niicloudoperation/rdm-ember-osf-web@" + "a" * 64, ""):
            errors = mc.validate_manifest(prebuilt_manifest(ref=ref), today=TODAY)
            self.assertEqual(codes(errors), {"MC-06"}, ref)
            self.assertTrue(any("name@sha256:<64 hex>" in e for e in errors), errors)

    def test_missing_or_blank_note_fails(self):
        for note in (None, "", "   "):
            errors = mc.validate_manifest(prebuilt_manifest(note=note), today=TODAY)
            self.assertEqual(codes(errors), {"MC-06"}, repr(note))
            self.assertTrue(any("requires a non-empty note" in e for e in errors), errors)

    def test_url_forms_fail(self):
        for ref in (private_address("https", "RDM-ember-osf-web" + DEV2027) + "@" + PREBUILT_DIGEST,
                    private_address("scp", "RDM-ember-osf-web" + PRIVATE),
                    "https://registry.example/x@" + PREBUILT_DIGEST):
            errors = mc.validate_manifest(prebuilt_manifest(ref=ref), today=TODAY)
            self.assertIn("MC-06", codes(errors), ref)
            self.assertTrue(any("private-repository reference" in e for e in errors), errors)

    def test_private_repository_name_in_a_registry_path_fails(self):
        for ref in ("ghcr.io/rcosdp/rdm-osf.io" + DEV2027.lower() + "@" + PREBUILT_DIGEST,
                    "ghcr.io/rcosdp/rdm-ember-osf-web-master" + PRIVATE + "@" + PREBUILT_DIGEST):
            errors = mc.validate_manifest(prebuilt_manifest(ref=ref), today=TODAY)
            self.assertEqual(codes(errors), {"MC-06"}, ref)
            self.assertTrue(any("private-repository reference" in e for e in errors), errors)

    def test_infra_component_cannot_be_prebuilt(self):
        m = valid_manifest()
        m["components"][1]["prebuilt_image"] = "postgres@" + PREBUILT_DIGEST
        m["components"][1]["note"] = "why"
        errors = mc.validate_manifest(m, today=TODAY)
        self.assertEqual(codes(errors), {"MC-06"})
        self.assertTrue(any("not allowed for infra" in e for e in errors), errors)

    def test_wrong_type_is_a_structure_finding(self):
        m = prebuilt_manifest()
        m["components"][0]["prebuilt_image"] = 5
        errors = mc.validate_manifest(m, today=TODAY)
        self.assertEqual(errors, ["MC-06: components[0].prebuilt_image: expected string or null, got integer"])

    def test_prebuilt_image_is_not_part_of_the_toon_projection(self):
        """The TOON excerpt lists ids, roles, repos, profiles, upstreams and adopted PRs only (SPEC-01 §2)."""
        self.assertEqual(mc.compare_toon(prebuilt_manifest(), mc.parse_toon(VALID_TOON)), [])

    def test_real_manifest_ember_osf_web_is_prebuilt_by_digest_with_note(self):
        data = json.loads((REPO_ROOT / "manifest" / "upstreams.json").read_text(encoding="utf-8"))
        ember = next(c for c in data["components"] if c["id"] == "ember-osf-web")
        self.assertRegex(ember["prebuilt_image"], r"^niicloudoperation/rdm-ember-osf-web@sha256:[0-9a-f]{64}$")
        self.assertIn("M4", ember["note"])
        self.assertEqual(ember["build_platform"], "linux/amd64")  # the pinned digest is the linux/amd64 manifest
        self.assertEqual(mc.check_manifest_files(REPO_ROOT / "manifest" / "upstreams.json", REPO_ROOT / "manifest" / "upstreams.toon"), [])


def overlay_manifest() -> dict:
    """valid_manifest() plus a wiki-frontend overlay of osf.io (SPEC-01 §3 overlay_of, ADR-06)."""
    m = valid_manifest()
    m["components"].append({
        "id": "wiki-frontend",
        "role": "core",
        "services": ["wiki_assets"],
        "overlay_of": "osf.io",
        "integration_repo": "RDM-wiki-frontend-dev2027",
        "integration_branch": "develop",
        "upstreams": [
            {"repo": "RDM-wiki-frontend", "branch": "develop", "kind": "public",
             "tracking_branch": "upstream/public-develop", "status": "merged",
             "sha": SHA_B, "fetched_at": "2026-11-05"},
        ],
        "adopted_prs": [],
        "candidate_prs": [],
        "base_image": "node:21-alpine",
        "base_image_digest": None,
        "target_image": {"M4": "node LTS alpine, non-root", "M5": None},
        "profile": "core",
        "platforms": ["linux/arm64", "linux/amd64"],
        "note": "overlay of osf.io: the Dockerfile COPYs osf.io paths",
    })
    return m


class OverlayTests(unittest.TestCase):
    """MC-14: overlay_of names a buildable base; the overlay is buildable and keeps its (one-shot) services."""

    def overlay(self, m: dict) -> dict:
        return next(c for c in m["components"] if c["id"] == "wiki-frontend")

    def test_valid_overlay_passes_with_its_own_services_and_profile(self):
        self.assertEqual(mc.validate_manifest(overlay_manifest(), today=TODAY), [])
        m = overlay_manifest()
        self.overlay(m)["build_platform"] = "linux/amd64"  # its own image: build_platform is allowed like any built component
        self.assertEqual(mc.validate_manifest(m, today=TODAY), [])

    def test_overlay_with_empty_services_is_mc03_like_any_component(self):
        m = overlay_manifest()
        self.overlay(m)["services"] = []
        self.assertEqual(codes(mc.validate_manifest(m, today=TODAY)), {"MC-03"})

    def test_overlay_of_self_unknown_infra_and_overlay_of_overlay_are_rejected(self):
        m = overlay_manifest()
        self.overlay(m)["overlay_of"] = "wiki-frontend"
        errors = mc.validate_manifest(m, today=TODAY)
        self.assertEqual(codes(errors), {"MC-14"})
        self.assertTrue(any("itself" in e for e in errors), errors)

        m = overlay_manifest()
        self.overlay(m)["overlay_of"] = "nope"
        errors = mc.validate_manifest(m, today=TODAY)
        self.assertEqual(codes(errors), {"MC-14"})
        self.assertTrue(any("unknown component 'nope'" in e for e in errors), errors)

        m = overlay_manifest()
        self.overlay(m)["overlay_of"] = "postgres"
        errors = mc.validate_manifest(m, today=TODAY)
        self.assertEqual(codes(errors), {"MC-14"})
        self.assertTrue(any("not infra" in e for e in errors), errors)

        m = overlay_manifest()
        second = copy.deepcopy(self.overlay(m))
        second["id"] = "wiki-theme"
        second["integration_repo"] = "RDM-wiki-theme-dev2027"
        second["services"] = ["wiki_theme_assets"]
        second["overlay_of"] = "wiki-frontend"
        second["upstreams"] = []
        m["components"].append(second)
        errors = mc.validate_manifest(m, today=TODAY)
        self.assertEqual(codes(errors), {"MC-14"})
        self.assertTrue(any("overlay of overlay" in e for e in errors), errors)

    def test_two_overlays_of_one_base_are_rejected(self):
        m = overlay_manifest()
        second = copy.deepcopy(self.overlay(m))
        second["id"] = "wiki-theme"
        second["integration_repo"] = "RDM-wiki-theme-dev2027"
        second["services"] = ["wiki_theme_assets"]
        second["upstreams"] = []
        m["components"].append(second)
        errors = mc.validate_manifest(m, today=TODAY)
        self.assertEqual(codes(errors), {"MC-14"})
        self.assertTrue(any("more than one overlay" in e for e in errors), errors)

    def test_prebuilt_base_or_prebuilt_overlay_are_rejected(self):
        m = overlay_manifest()
        m["components"][0]["prebuilt_image"] = "niicloudoperation/rdm-osf@" + PREBUILT_DIGEST
        m["components"][0]["note"] = "why"
        errors = mc.validate_manifest(m, today=TODAY)
        self.assertEqual(codes(errors), {"MC-14"})
        self.assertTrue(any("base 'osf.io' has prebuilt_image" in e for e in errors), errors)

        m = overlay_manifest()
        self.overlay(m)["prebuilt_image"] = "niicloudoperation/rdm-wiki@" + PREBUILT_DIGEST
        errors = mc.validate_manifest(m, today=TODAY)
        self.assertEqual(codes(errors), {"MC-14"})
        self.assertTrue(any("must not have prebuilt_image" in e for e in errors), errors)

    def test_infra_overlay_is_rejected(self):
        m = overlay_manifest()
        o = self.overlay(m)
        o["role"] = "infra"; o["integration_repo"] = None; o["integration_branch"] = None; o["upstreams"] = []
        errors = mc.validate_manifest(m, today=TODAY)
        self.assertIn("MC-14", codes(errors))
        self.assertTrue(any("must not be infra" in e for e in errors), errors)

    def test_empty_string_overlay_of_is_rejected_not_normalized(self):
        """Review r1: "when present" means a component id; "" is neither absent nor valid."""
        m = overlay_manifest()
        self.overlay(m)["overlay_of"] = ""
        errors = mc.validate_manifest(m, today=TODAY)
        self.assertEqual(codes(errors), {"MC-14"})
        self.assertTrue(any("empty string" in e for e in errors), errors)
        m = overlay_manifest()
        self.overlay(m)["overlay_of"] = None  # null is "absent": an ordinary component
        self.assertEqual(mc.validate_manifest(m, today=TODAY), [])

    def test_wrong_type_is_a_structure_finding(self):
        m = overlay_manifest()
        self.overlay(m)["overlay_of"] = ["osf.io"]
        self.assertEqual(mc.validate_manifest(m, today=TODAY),
                         ["MC-14: components[2].overlay_of: expected string or null, got list"])

    def test_overlay_of_is_not_part_of_the_toon_projection(self):
        proj = mc.project_manifest(overlay_manifest())
        self.assertNotIn("overlay_of", proj["components"][2])
        self.assertNotIn("services", proj["components"][2])

    def test_real_manifest_wiki_frontend_is_an_overlay_of_osf_io(self):
        data = json.loads((REPO_ROOT / "manifest" / "upstreams.json").read_text(encoding="utf-8"))
        comps = {c["id"]: c for c in data["components"]}
        wiki = comps["wiki-frontend"]
        self.assertEqual(wiki["overlay_of"], "osf.io")
        self.assertEqual(wiki["services"], ["wiki_static_init", "wiki_assets"])
        self.assertEqual(wiki["profile"], "core")
        self.assertNotIn("prebuilt_image", comps["osf.io"])
        self.assertRegex(wiki["integration_sha"], r"^[0-9a-f]{40}$")
        self.assertIn("ADR-06", wiki["note"])
        self.assertEqual(mc.check_manifest_files(REPO_ROOT / "manifest" / "upstreams.json", REPO_ROOT / "manifest" / "upstreams.toon"), [])


class StructureValidationTests(unittest.TestCase):
    """R2-02: types are checked before any set membership or projection; a type
    problem is a finding (MC id + JSON path), never an exception."""

    def assert_structural(self, mutate, expected_code: str, expected_path: str):
        data = valid_manifest()
        mutate(data)
        errors = mc.validate_structure(data)
        self.assertTrue(errors, "expected a structural finding")
        self.assertIn(expected_code, codes(errors))
        self.assertTrue(any(expected_path in e for e in errors), errors)
        # validate_manifest must return findings too, without raising
        full = mc.validate_manifest(data, today=TODAY)
        self.assertTrue(full)
        self.assertTrue(any(expected_path in e for e in full), full)
        return errors

    def test_valid_manifest_is_well_formed(self):
        self.assertEqual(mc.validate_structure(valid_manifest()), [])

    def test_schema_version_true_is_rejected(self):
        def m(d):
            d["schema_version"] = True
        errors = self.assert_structural(m, "MC-01", "$.schema_version")
        self.assertIn("boolean", errors[0])

    def test_schema_version_string_and_other_int_are_rejected(self):
        def m(d):
            d["schema_version"] = "1"
        self.assert_structural(m, "MC-01", "$.schema_version")

        def m2(d):
            d["schema_version"] = 2
        self.assert_structural(m2, "MC-01", "$.schema_version")

    def test_target_image_value_true_is_rejected(self):
        def m(d):
            d["components"][0]["target_image"]["M4"] = True
        self.assert_structural(m, "MC-01", "components[0].target_image.M4")

    def test_target_image_null_and_string_values_pass(self):
        data = valid_manifest()
        data["components"][0]["target_image"] = {"M4": None, "M5": "x:1"}
        self.assertEqual(mc.validate_structure(data), [])

    def test_components_string_is_a_finding_not_attribute_error(self):
        def m(d):
            d["components"] = "bad"
        errors = self.assert_structural(m, "MC-01", "$.components")
        self.assertIn("got string", errors[0])
        # no AttributeError from the projection either
        data = valid_manifest()
        data["components"] = "bad"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "upstreams.json").write_text(json.dumps(data), encoding="utf-8")
            (root / "upstreams.toon").write_text(VALID_TOON, encoding="utf-8")
            errors = mc.check_manifest_files(root / "upstreams.json", root / "upstreams.toon")
        self.assertTrue(errors)
        self.assertFalse(any(e.startswith("MC-11") for e in errors), "TOON parity must not run on ill-typed data")

    def test_component_role_list_is_a_finding_not_type_error(self):
        def m(d):
            d["components"][0]["role"] = []
        errors = self.assert_structural(m, "MC-03", "components[0].role")
        self.assertIn("got list", errors[0])

    def test_component_not_an_object(self):
        def m(d):
            d["components"].append(42)
        self.assert_structural(m, "MC-01", "$.components[2]")

    def test_string_fields_reject_booleans(self):
        for field, code in (("id", "MC-02"), ("base_image", "MC-01"), ("profile", "MC-10"),
                            ("integration_repo", "MC-04"), ("integration_branch", "MC-05"),
                            ("base_image_digest", "MC-06")):
            def m(d, field=field):
                d["components"][0][field] = True
            self.assert_structural(m, code, f"components[0].{field}")

    def test_list_fields_reject_non_lists_and_wrong_items(self):
        def m(d):
            d["components"][0]["services"] = "web"
        self.assert_structural(m, "MC-03", "components[0].services")

        def m2(d):
            d["components"][0]["services"] = ["web", False]
        self.assert_structural(m2, "MC-03", "components[0].services[1]")

        def m3(d):
            d["components"][0]["platforms"] = [["linux/arm64"]]  # unhashable item: no TypeError
        self.assert_structural(m3, "MC-10", "components[0].platforms[0]")

        def m4(d):
            d["components"][0]["upstreams"] = {"repo": "x"}
        self.assert_structural(m4, "MC-01", "components[0].upstreams")

    def test_upstream_entries_must_be_objects_with_string_fields(self):
        def m(d):
            d["components"][0]["upstreams"][0] = "RDM-osf.io"
        self.assert_structural(m, "MC-01", "components[0].upstreams[0]")

        def m2(d):
            d["components"][0]["upstreams"][1]["sha"] = 12345
        self.assert_structural(m2, "MC-06", "components[0].upstreams[1].sha")

        def m3(d):
            d["components"][0]["upstreams"][1]["kind"] = ["private"]
        self.assert_structural(m3, "MC-09", "components[0].upstreams[1].kind")

    def test_pr_entries_must_be_objects_with_int_number(self):
        def m(d):
            d["components"][0]["adopted_prs"][0] = 796
        self.assert_structural(m, "MC-09", "components[0].adopted_prs[0]")

        def m2(d):
            d["components"][0]["adopted_prs"][0]["number"] = True
        self.assert_structural(m2, "MC-09", "components[0].adopted_prs[0].number")

        def m3(d):
            d["components"][0]["candidate_prs"][0]["number"] = "93"
        self.assert_structural(m3, "MC-09", "components[0].candidate_prs[0].number")

        def m4(d):
            d["components"][0]["candidate_prs"] = [None]
        self.assert_structural(m4, "MC-09", "components[0].candidate_prs[0]")

    def test_top_level_not_an_object(self):
        for data in ([], "x", None, 1):
            errors = mc.validate_structure(data)
            self.assertEqual(len(errors), 1)
            self.assertIn("MC-01", codes(errors))
            self.assertTrue(mc.validate_manifest(data, today=TODAY))


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

    def test_no_path_exemptions_remain(self):
        # R2-01: the publication policy has no path-based exemption function any more.
        self.assertFalse(hasattr(mc, "policy_excluded"))
        self.assertFalse(hasattr(mc, "POLICY_EXCLUDED_PREFIXES"))
        self.assertFalse(hasattr(mc, "POLICY_TEXT_SUFFIXES"))

    def test_run_policy_scan_on_file_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.md").write_text(private_address("scp", "RDM-x" + DEV2027) + "\n", encoding="utf-8")
            (root / "b.md").write_text("clean\n", encoding="utf-8")
            findings = mc.run_policy_scan(root, files=["a.md", "b.md"])
        self.assertEqual(len(findings), 1)
        self.assertTrue(findings[0].startswith("a.md:1:"))

    def test_previously_excluded_locations_are_now_reported(self):
        """R2-01 reproduction: the same prohibited address in site/, a *.legacy.md and
        nested legacy sample code must each be reported (control: docs/README.md)."""
        cases = {
            "site/index.html": private_address("https", "RDM-osf.io" + DEV2027),
            "site/search/search_index.json": private_address("https", "RDM-osf.io" + DEV2027),
            "docs/guides/api/README.legacy.md": private_address("scp", "RDM-osf.io" + PRIVATE),
            "docs/guides/api/addon/x.py": private_address("ssh", "RDM-osf.io-develop" + PRIVATE),
            "docs/guides/api/osf/addon/deep/y.js": private_address("https", "RDM-x" + PRIVATE),
            "docs/README.md": private_address("https", "RDM-osf.io" + DEV2027),
            "Dockerfile": private_address("scp", "RDM-osf.io" + DEV2027),  # no suffix at all
            "assets/data.unknownext": private_address("https", "RDM-osf.io" + DEV2027),
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel, addr in cases.items():
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("<p>clean</p>\nsee " + addr + " here\n", encoding="utf-8")
                findings = mc.run_policy_scan(root, files=[rel])
                self.assertEqual(len(findings), 1, rel)
                self.assertTrue(findings[0].startswith(f"{rel}:2:"), findings[0])
                self.assertNotIn("github", findings[0].lower())  # address never echoed
            # and all at once
            result = mc.scan_policy(root, files=list(cases))
            self.assertEqual(len(result.findings), len(cases))
            self.assertEqual(sorted(result.scanned), sorted(cases))
            self.assertEqual(result.skipped, [])

    def test_token_in_site_and_legacy_files_is_reported(self):
        ghp = "ghp" + "_" + "x" * 36
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in ("site/js/app.js", "docs/guides/x/README.legacy.md"):
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("token = '" + ghp + "'\n", encoding="utf-8")
                findings = mc.run_policy_scan(root, files=[rel])
                self.assertEqual(len(findings), 1, rel)
                self.assertNotIn(ghp, findings[0])

    def test_binary_and_oversized_files_are_skipped_and_counted(self):
        addr = private_address("https", "RDM-osf.io" + DEV2027)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "img.png").write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe" + addr.encode("utf-8"))
            (root / "big.txt").write_text("x" * 100 + "\n" + addr + "\n", encoding="utf-8")
            (root / "ok.txt").write_text(addr + "\n", encoding="utf-8")
            (root / "latin1.txt").write_bytes("caf\xe9 ".encode("latin-1") + addr.encode("utf-8"))
            result = mc.scan_policy(root, files=["img.png", "big.txt", "ok.txt", "latin1.txt", "missing.md"], max_bytes=80)
        self.assertEqual(result.scanned, ["ok.txt"])
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(result.skipped_binary, 2)
        self.assertEqual(result.skipped_large, 1)
        self.assertEqual(len(result.skipped), 3)
        self.assertEqual(mc.POLICY_MAX_BYTES, 5 * 1024 * 1024)

    def test_real_repository_tracked_set_is_fully_scanned(self):
        """The real checkout: site/**, *.legacy.md and nested guide files are scanned."""
        if not (REPO_ROOT / ".git").exists():
            self.skipTest("not a git checkout")
        result = mc.scan_policy(REPO_ROOT)
        scanned = set(result.scanned)
        tracked = set(mc.git_tracked_files(REPO_ROOT))
        skipped = {p for p, _ in result.skipped}
        present = {p for p in tracked if (REPO_ROOT / p).is_file()}
        self.assertEqual(scanned | skipped, present)
        self.assertTrue(any(p.startswith("site/") and p.endswith(".html") for p in scanned))
        self.assertTrue(any(p.endswith(".legacy.md") for p in scanned))
        self.assertTrue(any(p.startswith("docs/guides/") and p.count("/") >= 4 for p in scanned))
        for p in skipped:
            self.assertNotEqual(Path(p).suffix, ".md", p)  # no Markdown is ever skipped
        self.assertEqual(result.findings, [])


class CliTests(unittest.TestCase):
    def test_exit_codes_are_documented(self):
        self.assertEqual(mc.EXIT_MANIFEST, 20)
        self.assertEqual(mc.EXIT_POLICY, 1)
        self.assertIn("20", mc.__doc__)

    def _run_cli(self, root: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-I", str(TOOLS_DIR / "manifest_check.py"), "--root", str(root), *args],
            capture_output=True, text=True, cwd=str(root),
        )

    def _write_manifest_copy(self, root: Path, mutate) -> None:
        """Temporary copy of the real JSON (mutated) with the unchanged real TOON."""
        (root / "manifest").mkdir(exist_ok=True)
        data = json.loads((REPO_ROOT / "manifest" / "upstreams.json").read_text(encoding="utf-8"))
        mutate(data)
        (root / "manifest" / "upstreams.json").write_text(json.dumps(data), encoding="utf-8")
        (root / "manifest" / "upstreams.toon").write_text(
            (REPO_ROOT / "manifest" / "upstreams.toon").read_text(encoding="utf-8"), encoding="utf-8")

    def test_subprocess_exit_20_without_traceback_for_ill_typed_manifests(self):
        """R2-02 review cases against copies of the real JSON + unchanged TOON."""
        cases = [
            ("schema_version true", lambda d: d.__setitem__("schema_version", True), "$.schema_version"),
            ("target_image.M4 true", lambda d: d["components"][0]["target_image"].__setitem__("M4", True),
             "components[0].target_image.M4"),
            ("components string", lambda d: d.__setitem__("components", "bad"), "$.components"),
            ("role list", lambda d: d["components"][0].__setitem__("role", []), "components[0].role"),
            ("pr number bool", lambda d: d["components"][0]["adopted_prs"][0].__setitem__("number", True),
             "adopted_prs[0].number"),
            ("services bool item", lambda d: d["components"][0].__setitem__("services", [True]),
             "components[0].services[0]"),
            ("top level list", lambda d: None, None),
        ]
        for name, mutate, path in cases:
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                if path is None:
                    (root / "manifest").mkdir()
                    (root / "manifest" / "upstreams.json").write_text("[]", encoding="utf-8")
                    (root / "manifest" / "upstreams.toon").write_text("schema_version: 1\n", encoding="utf-8")
                else:
                    self._write_manifest_copy(root, mutate)
                proc = self._run_cli(root, "--manifest-only")
                self.assertEqual(proc.returncode, 20, proc.stdout + proc.stderr)
                self.assertNotIn("Traceback", proc.stderr)
                self.assertNotIn("Error", proc.stderr.replace("Error:", ""))  # no AttributeError/TypeError
                self.assertIn("MC-0", proc.stdout)
                if path:
                    self.assertIn(path, proc.stdout)
                self.assertNotIn("MC-11", proc.stdout)  # TOON parity not attempted on ill-typed data

    def test_subprocess_real_manifest_copy_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_manifest_copy(root, lambda d: None)
            proc = self._run_cli(root, "--manifest-only")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_subprocess_manifest_errors_take_precedence_over_policy(self):
        """Exit 20 beats exit 1 when both the manifest is invalid and a policy hit exists."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
            self._write_manifest_copy(root, lambda d: d.__setitem__("schema_version", True))
            (root / "site").mkdir()
            (root / "site" / "index.html").write_text(private_address("https", "RDM-x" + DEV2027) + "\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True)
            proc = self._run_cli(root)
            self.assertEqual(proc.returncode, 20, proc.stdout + proc.stderr)
            self.assertIn("site/index.html:1:", proc.stdout)
            # valid manifest + same policy hit -> exit 1, address not echoed, skip count printed
            self._write_manifest_copy(root, lambda d: None)
            proc = self._run_cli(root)
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertIn("site/index.html:1:", proc.stdout)
            self.assertNotIn("github", proc.stdout.lower())
            self.assertIn("skipped", proc.stdout)

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
