import json
import shutil
import tempfile
import unittest
from pathlib import Path

from grdm_dev import exit_codes, manifest
from grdm_dev.context import Context

REPO_ROOT = Path(__file__).resolve().parents[2]

# SPEC-02 §4 profiles table
MINIMUM = {"web", "api", "postgres", "elasticsearch", "rabbitmq", "fakecas"}
CORE = MINIMUM | {"admin", "worker", "wb", "wb_worker", "mfr", "unoconv", "ember_osf_web", "cas", "wiki", "mongo",
                  "sharejs", "elasticsearch6", "redis", "y_websocket"}
FULL_FAKECAS = CORE | {"rdmcp", "aipf_mcp_data_grdm", "oasys"}
FULL_SHIBBOLETH = (FULL_FAKECAS - {"fakecas"}) | {"shibboleth_sp", "test_idp"}


def temp_root_with_manifest(mutate=None) -> Path:
    """Copy manifest/ into a temporary root; `mutate(data)` edits the JSON before writing."""
    root = Path(tempfile.mkdtemp(prefix="grdm-manifest-"))
    (root / "manifest").mkdir()
    data = json.loads((REPO_ROOT / "manifest" / "upstreams.json").read_text(encoding="utf-8"))
    if mutate:
        mutate(data)
    (root / "manifest" / "upstreams.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    shutil.copy(REPO_ROOT / "manifest" / "upstreams.toon", root / "manifest" / "upstreams.toon")
    return root


class ManifestLoadTests(unittest.TestCase):
    def setUp(self):
        self.ctx = Context(root=REPO_ROOT, yes=True)

    def test_real_manifest_loads_and_validates(self):
        self.assertEqual(manifest.validate(self.ctx), [])
        man = manifest.load(self.ctx)
        self.assertEqual(man.schema_version, 1)
        ids = {c.id for c in man.components}
        self.assertIn("osf.io", ids)
        self.assertIn("postgres", ids)
        osf = man.component("osf.io")
        self.assertTrue(osf.is_built)
        self.assertEqual(len(osf.sha12), 12)
        self.assertTrue(osf.local_image().startswith("grdm-dev/osf.io:"))
        self.assertEqual(man.component("postgres").image_reference(), "postgres:9.6")
        # dict compatibility for modules written against raw JSON
        self.assertEqual(osf["id"], "osf.io")
        self.assertEqual(osf.get("integration_repo"), "RDM-osf.io-dev2027")

    def test_load_accepts_path(self):
        man = manifest.load(REPO_ROOT / "manifest" / "upstreams.json")
        self.assertEqual(man.component_for_service("wb").id, "waterbutler")

    def test_build_sha_prefers_public_merged_upstream(self):
        man = manifest.load(self.ctx)
        wb = man.component("waterbutler")
        public = [u for u in wb.upstreams if u.kind == "public" and u.status == "merged"][0]
        self.assertEqual(wb.build_sha, public.sha)
        oasys = man.component("OASys")  # private only
        self.assertEqual(oasys.build_sha, oasys.upstreams[0].sha)

    def test_invalid_manifest_reports_exit_20(self):
        def bad(data):
            data["components"][0]["upstreams"][0]["sha"] = "not-a-sha"
        root = temp_root_with_manifest(bad)
        ctx = Context(root=root, yes=True)
        errors = manifest.validate(ctx)
        self.assertTrue(errors)
        self.assertTrue(any("MC-06" in e for e in errors), errors)
        with self.assertRaises(manifest.ManifestError) as cm:
            manifest.load_validated(ctx)
        self.assertEqual(cm.exception.exit_code, exit_codes.MANIFEST_INVALID)

    def test_broken_json_is_manifest_error(self):
        root = temp_root_with_manifest()
        (root / "manifest" / "upstreams.json").write_text("{not json", encoding="utf-8")
        ctx = Context(root=root, yes=True)
        with self.assertRaises(manifest.ManifestError) as cm:
            manifest.load(ctx)
        self.assertEqual(cm.exception.exit_code, 20)
        self.assertTrue(manifest.validate(ctx))


class ServicesForProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.man = manifest.load(Context(root=REPO_ROOT))

    def names(self, profile, auth="fakecas"):
        return {s.name for s in manifest.services_for_profile(self.man, profile, auth)}

    def test_templates_cover_every_manifest_service(self):
        templates = manifest.load_templates()
        for name in self.man.service_names:
            self.assertIn(name, templates, f"missing template for {name}")
            self.assertEqual(templates[name]["component"], self.man.component_for_service(name).id)

    def test_minimum(self):
        self.assertEqual(self.names("minimum"), MINIMUM)

    def test_core(self):
        self.assertEqual(self.names("core"), CORE)

    def test_full_default_keeps_fakecas(self):
        self.assertEqual(self.names("full"), FULL_FAKECAS)

    def test_full_shibboleth_swaps_fakecas(self):
        self.assertEqual(self.names("full", "shibboleth"), FULL_SHIBBOLETH)

    def test_service_fields(self):
        services = {s.name: s for s in manifest.services_for_profile(self.man, "core")}
        web = services["web"]
        self.assertEqual(web.component, "osf.io")
        self.assertEqual(web.role, "core")
        self.assertEqual(web.build.repo, "RDM-osf.io-dev2027")
        self.assertEqual(web.build.branch, "develop")
        self.assertEqual(web.image, f"grdm-dev/osf.io:{web.build.sha12}")
        self.assertEqual(services["admin"].profile, "core")
        pg = services["postgres"]
        self.assertIsNone(pg.build)
        self.assertEqual(pg.image, "postgres:9.6")
        self.assertEqual(pg.role, "infra")

    def test_image_tag_override_from_build_report(self):
        services = {s.name: s for s in manifest.services_for_profile(self.man, "minimum", image_tags={"osf.io": "abcdef123456"})}
        self.assertEqual(services["web"].image, "grdm-dev/osf.io:abcdef123456")
        self.assertEqual(services["web"].build.sha12, "abcdef123456")

    def test_unknown_profile_rejected(self):
        with self.assertRaises(ValueError):
            manifest.services_for_profile(self.man, "huge")


if __name__ == "__main__":
    unittest.main()
