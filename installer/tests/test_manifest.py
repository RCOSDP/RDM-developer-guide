import json
import shutil
import tempfile
import unittest
from pathlib import Path

from grdm_dev import exit_codes, manifest
from grdm_dev.context import Context

REPO_ROOT = Path(__file__).resolve().parents[2]

# SPEC-02 §4 profiles table
MINIMUM = {"osf_init", "volume_owner_init", "volume_access_check_1000", "web", "api", "postgres", "elasticsearch8", "elasticsearch8_setup", "rabbitmq", "fakecas"}
# `wiki_assets` is the one-shot service of the wiki-frontend overlay (SPEC-01 §3 overlay_of, ADR-06); there is no `wiki` server.
CORE = MINIMUM | {"admin", "worker", "wb", "wb_worker", "mfr", "unoconv", "ember_osf_web", "cas", "wiki_assets", "volume_access_check_999",
                  "elasticsearch6", "redis", "y_websocket"}
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
        self.assertEqual(man.component("postgres").image_reference(), "postgres:18.6@sha256:e3d24f6906d0760bf4da0dae872415391ededefad23fd471c47dc53b0ddf3c42")  # ADR-12
        # dict compatibility for modules written against raw JSON
        self.assertEqual(osf["id"], "osf.io")
        self.assertEqual(osf.get("integration_repo"), "RDM-osf.io-dev2027")

    def test_load_accepts_path(self):
        man = manifest.load(REPO_ROOT / "manifest" / "upstreams.json")
        self.assertEqual(man.component_for_service("wb").id, "waterbutler")

    def test_build_sha_precedence_integration_sha_then_public_then_private(self):
        """SPEC-01: integration_sha (the pinned develop tip) wins; without it the merged public
        upstream, then the private upstream. Checked on the real manifest and on a synthetic copy."""
        man = manifest.load(self.ctx)
        wb = man.component("waterbutler")
        self.assertRegex(wb.build_sha, r"^[0-9a-f]{40}$")
        if wb.get("integration_sha"):
            self.assertEqual(wb.build_sha, wb.get("integration_sha"))
        else:
            public = [u for u in wb.upstreams if u.kind == "public" and u.status == "merged"][0]
            self.assertEqual(wb.build_sha, public.sha)
        oasys = man.component("OASys")  # private only
        self.assertEqual(oasys.build_sha, oasys.get("integration_sha") or oasys.upstreams[0].sha)
        # synthetic: strip integration_sha and the precedence falls back to the merged public upstream
        import copy, json, tempfile, pathlib
        data = json.loads((REPO_ROOT / "manifest" / "upstreams.json").read_text(encoding="utf-8"))
        for comp in data["components"]:
            comp["integration_sha"] = None
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td); (root / "manifest").mkdir()
            (root / "manifest" / "upstreams.json").write_text(json.dumps(data), encoding="utf-8")
            man2 = manifest.load(root / "manifest" / "upstreams.json")
            wb2 = man2.component("waterbutler")
            public2 = [u for u in wb2.upstreams if u.kind == "public" and u.status == "merged"][0]
            self.assertEqual(wb2.build_sha, public2.sha)
            # private-only component without integration_sha falls back to its merged private upstream
            oasys2 = man2.component("OASys")
            private2 = [u for u in oasys2.upstreams if u.kind == "private" and u.status == "merged"][0]
            self.assertEqual(oasys2.build_sha, private2.sha)
            self.assertNotEqual(oasys2.build_sha, wb2.build_sha)

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

    def test_native_image_build_component_has_image_origin(self):
        """ADR-07, ADR-14: elasticsearch8 runs grdm-dev/elasticsearch8:<tag> built from installer/images/, origin `image`."""
        services = {s.name: s for s in manifest.services_for_profile(self.man, "minimum")}
        for name in ("elasticsearch8", "elasticsearch8_setup"):  # the node and its one-shot share the image
            es = services[name]
            self.assertEqual(es.image, "grdm-dev/elasticsearch8:8.19.24-1")
            self.assertEqual(es.origin, "image")
            self.assertFalse(es.is_built); self.assertFalse(es.is_prebuilt)
        self.assertTrue(self.man.component("elasticsearch8").is_image_build)

    def test_retired_components_are_gone(self):
        """ADR-13/ADR-14: Elasticsearch 2, MongoDB and ShareJS are not components any more."""
        ids = {c.id for c in self.man.components}
        self.assertFalse(ids & {"elasticsearch2", "mongo", "sharejs"}, ids)
        self.assertFalse({"elasticsearch", "mongo", "sharejs"} & set(self.man.service_names))

    def test_cas_is_built_from_the_pinned_merge_commit(self):
        """ADR-07: no prebuilt image and no emulated platform; the image tag is the commit that carries the fixes."""
        cas = self.man.component("cas-overlay")
        self.assertFalse(cas.is_prebuilt)
        self.assertTrue(cas.is_built)
        self.assertIsNone(cas.get("build_platform"))
        self.assertIsNone(cas.get("build_dockerfile"))  # the integration repository's own Dockerfile is the native one
        self.assertEqual(cas.get("integration_sha"), "22610b7681a29241365108e5129bcd43ade4610e")
        services = {s.name: s for s in manifest.services_for_profile(self.man, "core")}
        self.assertEqual(services["cas"].image, "grdm-dev/cas-overlay:22610b7681a2")

    def test_rebuilt_infra_images_are_native_and_unexcepted(self):
        """ADR-07 §5: the recipes replace the emulated images, and elasticsearch6 needs no hardening entry."""
        services = {s.name: s for s in manifest.services_for_profile(self.man, "core")}
        self.assertEqual(services["elasticsearch6"].image, "grdm-dev/elasticsearch6:6.8.23-1")
        self.assertEqual(services["fakecas"].image, "grdm-dev/fakecas:9a9ddd73b225-2")
        for cid in ("elasticsearch6", "fakecas"):
            self.assertIsNone(self.man.component(cid).get("build_platform"), cid)
        self.assertTrue(services["rabbitmq"].image.startswith("rabbitmq:3-management@sha256:"))
        # PR #37 review r1 R1-01: the image must be built from the commit that enforces JWT authentication
        self.assertEqual(services["y_websocket"].image, "grdm-dev/y-websocket:97252369cf7e")
        hardening = json.loads((REPO_ROOT / "manifest" / "hardening.json").read_text(encoding="utf-8"))
        self.assertNotIn("elasticsearch6", {e["service"] for e in hardening["exceptions"]})

    def test_empty_image_build_is_a_manifest_error(self):
        """PR #34 review r1 R1-02: `image_build: {}` must not degrade into the plain base image."""
        data = json.loads(json.dumps(self.man_data)) if hasattr(self, "man_data") else json.loads((REPO_ROOT / "manifest" / "upstreams.json").read_text(encoding="utf-8"))
        es = [c for c in data["components"] if c["id"] == "elasticsearch8"][0]
        es["image_build"] = {}
        with self.assertRaises(manifest.ManifestError):
            manifest.parse(data)

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
        self.assertEqual(web.build.sha12, self.man.component("osf.io").sha12)  # the base keeps its own tag (ADR-06)
        self.assertEqual(services["admin"].profile, "core")
        pg = services["postgres"]
        self.assertIsNone(pg.build)
        self.assertEqual(pg.image, "postgres:18.6@sha256:e3d24f6906d0760bf4da0dae872415391ededefad23fd471c47dc53b0ddf3c42")
        self.assertEqual(pg.role, "infra")

    def test_image_tag_override_from_build_report(self):
        services = {s.name: s for s in manifest.services_for_profile(self.man, "minimum", image_tags={"osf.io": "abcdef123456"})}
        self.assertEqual(services["web"].image, "grdm-dev/osf.io:abcdef123456")
        self.assertEqual(services["web"].build.sha12, "abcdef123456")

    def test_unknown_profile_rejected(self):
        with self.assertRaises(ValueError):
            manifest.services_for_profile(self.man, "huge")


PREBUILT_REF = "registry.example.invalid/rdm-ember-osf-web@sha256:" + "e" * 64
EMBER_PR2_HEAD = "4d505f000f8dfb8648955054c76d7a6374204b93"  # RDM-ember-osf-web-dev2027 develop after PR #2, #3 and #4 (merge commits); name kept from the PR-head pin


def with_prebuilt_ember(data):
    """The former fallback, put back on a copy: the `prebuilt_image` mechanism stays for any component."""
    for c in data["components"]:
        if c["id"] == "ember-osf-web":
            c["prebuilt_image"] = PREBUILT_REF
            c["build_platform"] = "linux/amd64"


class EmberStaticBuildTests(unittest.TestCase):
    """PR #2 review r1 R1-03: ember-osf-web is built from RDM-ember-osf-web-dev2027 as a static nginx image."""

    def test_real_manifest_builds_ember_osf_web_from_source(self):
        man = manifest.load(Context(root=REPO_ROOT))
        ember = man.component("ember-osf-web")
        self.assertFalse(ember.is_prebuilt)
        self.assertIsNone(ember.prebuilt_image)
        self.assertIsNone(ember.get("build_platform"))  # the Node stage runs on the build platform; nginx is multi-arch
        self.assertTrue(ember.is_built)
        self.assertEqual(ember.integration_repo, "RDM-ember-osf-web-dev2027")
        self.assertEqual(ember.integration_branch, "develop")
        self.assertEqual(ember.build_sha, EMBER_PR2_HEAD)
        self.assertEqual(ember.image_reference(), f"grdm-dev/ember-osf-web:{EMBER_PR2_HEAD[:12]}")
        self.assertEqual(ember.base_image, "nginxinc/nginx-unprivileged:1.29-alpine")
        self.assertRegex(ember.base_image_digest, r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(ember.platforms, ["linux/arm64", "linux/amd64"])
        self.assertNotIn("must move to the merge commit", ember.note)  # the PR-head pin is gone: the pin is develop
        svc = {s.name: s for s in manifest.services_for_profile(man, "core")}["ember_osf_web"]
        self.assertEqual(svc.origin, "built")
        self.assertEqual(svc.build.repo, "RDM-ember-osf-web-dev2027")
        self.assertEqual(svc.build.sha, EMBER_PR2_HEAD)
        self.assertEqual(manifest.validate(Context(root=REPO_ROOT)), [])

    def test_template_is_the_static_image_contract(self):
        tpl = manifest.load_templates()["ember_osf_web"]
        self.assertNotIn("command", tpl)  # the image's entrypoint renders index.html and runs the GA guard
        self.assertEqual(set(tpl["environment"]), {"OSF_URL", "OSF_API_URL", "OSF_RENDER_URL", "OSF_FILE_URL", "OSF_HELP_URL",
                                                   "CAS_URL", "OSF_COOKIE_DOMAIN", "CSP_MODE"})
        self.assertEqual(tpl["user"], "101:101")
        self.assertEqual(tpl["container_port"], 4200)
        self.assertEqual(tpl["tmpfs"], ["/tmp"])
        self.assertNotIn("volumes", tpl)
        self.assertNotIn("depends_on", tpl)
        self.assertEqual(tpl["mem_min_mb"], 128)


class PrebuiltImageTests(unittest.TestCase):
    """SPEC-01 §3 `prebuilt_image`: the component is not built; the reference is the image. No component uses it
    now (ember-osf-web did until its static image); the tests put it back on a copy of the manifest."""

    def setUp(self):
        self.root = temp_root_with_manifest(with_prebuilt_ember)
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.man = manifest.load(Context(root=self.root))

    def test_prebuilt_component_is_not_built(self):
        ember = self.man.component("ember-osf-web")
        self.assertTrue(ember.is_prebuilt)
        self.assertFalse(ember.is_built)  # still has an integration_repo, but the build is bypassed
        self.assertEqual(ember.integration_repo, "RDM-ember-osf-web-dev2027")
        self.assertEqual(ember.image_reference(), PREBUILT_REF)
        self.assertEqual(ember.image_reference("feedfacecafe"), PREBUILT_REF)  # a build-report tag cannot apply
        services = {s.name: s for s in manifest.services_for_profile(self.man, "core")}
        svc = services["ember_osf_web"]
        self.assertEqual(svc.image, PREBUILT_REF)
        self.assertIsNone(svc.build)
        self.assertTrue(svc.is_prebuilt)
        self.assertFalse(svc.is_built)
        self.assertEqual(svc.origin, "prebuilt")
        self.assertEqual(services["web"].origin, "built")
        self.assertEqual(services["wiki_assets"].origin, "overlay")  # the wiki-frontend bundle builder (ADR-06)
        self.assertEqual(services["postgres"].origin, "pinned")

    def test_image_tags_do_not_override_a_prebuilt_reference(self):
        services = {s.name: s for s in manifest.services_for_profile(self.man, "core", image_tags={"ember-osf-web": "abcdef123456"})}
        self.assertEqual(services["ember_osf_web"].image, PREBUILT_REF)

    def test_prebuilt_without_note_is_rejected_by_validate(self):
        def bad(data):
            with_prebuilt_ember(data)
            for c in data["components"]:
                if c["id"] == "ember-osf-web":
                    c["note"] = None
        root = temp_root_with_manifest(bad)
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        errors = manifest.validate(Context(root=root))
        self.assertTrue(any("MC-06" in e and "note" in e for e in errors), errors)


class OverlayTests(unittest.TestCase):
    """SPEC-01 §3 `overlay_of` (ADR-06): wiki-frontend's image is built from the osf.io checkout + its files and run once by `wiki_assets`."""

    def setUp(self):
        self.man = manifest.load(Context(root=REPO_ROOT))

    def test_real_manifest_wiki_frontend_is_an_overlay_of_osf_io(self):
        wiki = self.man.component("wiki-frontend")
        self.assertTrue(wiki.is_overlay)
        self.assertEqual(wiki.overlay_of, "osf.io")
        self.assertEqual(wiki.services, ["wiki_assets"])
        self.assertEqual(wiki.integration_repo, "RDM-wiki-frontend-dev2027")
        self.assertRegex(wiki.sha12, r"^[0-9a-f]{12}$")  # keeps its own pinned commit
        self.assertIs(self.man.overlay_for("osf.io"), wiki)
        self.assertIsNone(self.man.overlay_for("waterbutler"))
        self.assertFalse(self.man.component("osf.io").is_overlay)
        self.assertNotIn("wiki", self.man.service_names)
        self.assertEqual(manifest.validate(Context(root=REPO_ROOT)), [])

    def test_overlay_service_uses_the_combined_tag_and_is_one_shot_while_the_base_is_untouched(self):
        osf, wiki = self.man.component("osf.io"), self.man.component("wiki-frontend")
        tag = manifest.overlay_tag(osf.sha12, wiki.sha12)
        self.assertEqual(tag, f"{osf.sha12}-{wiki.sha12}")
        services = {s.name: s for s in manifest.services_for_profile(self.man, "core")}
        svc = services["wiki_assets"]
        self.assertEqual(svc.image, f"grdm-dev/wiki-frontend:{tag}")
        self.assertEqual(svc.origin, "overlay")
        self.assertTrue(svc.is_built)
        self.assertTrue(svc.is_overlay_build)
        self.assertTrue(svc.is_one_shot)
        self.assertEqual(svc.build.repo, "RDM-wiki-frontend-dev2027")
        self.assertEqual(svc.build.sha, wiki.build_sha)
        self.assertEqual(svc.build.overlay_of, "osf.io")
        self.assertEqual(svc.build.base_repo, "RDM-osf.io-dev2027")
        self.assertEqual(svc.build.base_sha12, osf.sha12)
        for name in ("web", "api", "admin", "worker"):
            self.assertEqual(services[name].image, f"grdm-dev/osf.io:{osf.sha12}", name)
            self.assertEqual(services[name].origin, "built", name)
            self.assertIsNone(services[name].build.overlay_of)
            self.assertFalse(services[name].is_one_shot)
        self.assertNotIn("wiki_assets", {s.name for s in manifest.services_for_profile(self.man, "minimum")})

    def test_build_report_tag_overrides_the_combined_tag(self):
        services = {s.name: s for s in manifest.services_for_profile(self.man, "core", image_tags={"wiki-frontend": "aaaaaaaaaaaa-bbbbbbbbbbbb"})}
        self.assertEqual(services["wiki_assets"].image, "grdm-dev/wiki-frontend:aaaaaaaaaaaa-bbbbbbbbbbbb")
        self.assertEqual(services["wiki_assets"].origin, "overlay")

    def test_overlay_tag_falls_back_to_develop(self):
        self.assertEqual(manifest.overlay_tag(None, "b" * 12), "develop-" + "b" * 12)
        self.assertEqual(manifest.overlay_tag("a" * 12, None), "a" * 12 + "-develop")

    def test_overlay_service_without_one_shot_template_is_mc14(self):
        templates = manifest.load_templates()
        templates["wiki_assets"] = {k: v for k, v in templates["wiki_assets"].items() if k != "one_shot"}
        with self.assertRaises(manifest.ManifestError) as cm:
            manifest.services_for_profile(self.man, "core", templates=templates)
        self.assertIn("MC-14", cm.exception.errors[0])
        self.assertIn("one-shot", cm.exception.errors[0])

    def test_overlay_of_unknown_base_is_rejected_by_validate(self):
        def bad(data):
            for c in data["components"]:
                if c["id"] == "wiki-frontend":
                    c["overlay_of"] = "nope"
        errors = manifest.validate(Context(root=temp_root_with_manifest(bad)))
        self.assertTrue(any("MC-14" in e and "unknown component" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
