import argparse
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from grdm_dev import exit_codes, plan
from grdm_dev.context import Context

REPO_ROOT = Path(__file__).resolve().parents[2]


def make_root(dotenv: str | None = None, mutate=None) -> Path:
    root = Path(tempfile.mkdtemp(prefix="grdm-plan-"))
    (root / "manifest").mkdir()
    data = json.loads((REPO_ROOT / "manifest" / "upstreams.json").read_text(encoding="utf-8"))
    if mutate:
        mutate(data)
    (root / "manifest" / "upstreams.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    shutil.copy(REPO_ROOT / "manifest" / "upstreams.toon", root / "manifest" / "upstreams.toon")
    if dotenv is not None:
        (root / "runtime").mkdir()
        (root / "runtime" / ".env").write_text(dotenv, encoding="utf-8")
    return root


def run_plan(root: Path, profile=None, auth="fakecas", json_output=True):
    ctx = Context(root=root, yes=True, json_output=json_output, profile=profile)
    args = argparse.Namespace(auth=auth)
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = plan.run(ctx, args, platform_string="linux/arm64")
    return rc, out.getvalue(), err.getvalue()


class PlanTests(unittest.TestCase):
    def test_default_profile_is_core_and_report_lists_spec_ports(self):
        rc, out, _ = run_plan(make_root())
        self.assertEqual(rc, exit_codes.OK)
        data = json.loads(out)
        self.assertEqual(data["profile"], "core")
        self.assertEqual(data["platform"], "linux/arm64")
        self.assertEqual(data["network"], "grdm")
        ports = {r["service"]: r for r in data["ports"]}
        self.assertEqual(set(ports), set(plan.DEFAULT_PORTS))
        for name, port in plan.DEFAULT_PORTS.items():
            self.assertEqual(ports[name]["host_port"], port)
            self.assertEqual(ports[name]["url"], f"http://127.0.0.1:{port}")
            self.assertEqual(ports[name]["source"], "default")
        services = {r["service"]: r for r in data["services"]}
        self.assertIn("y_websocket", services)
        self.assertTrue(services["web"]["build_from"].startswith("RDM-osf.io-dev2027@"))
        self.assertEqual(services["postgres"]["build_from"], "pinned image")
        self.assertTrue(any(i.startswith("grdm-dev/waterbutler:") for i in data["images_to_build"]))
        self.assertIn("postgres_data", data["volumes"])

    def test_profile_from_dotenv_and_port_override(self):
        root = make_root("GRDM_PROFILE=minimum\nGRDM_PORT_WEB=5050\nGRDM_PORT_API=abc\n")
        rc, out, _ = run_plan(root)
        data = json.loads(out)
        self.assertEqual(rc, 0)
        self.assertEqual(data["profile"], "minimum")
        ports = {r["service"]: r for r in data["ports"]}
        self.assertEqual(set(ports), {"web", "api", "fakecas"})  # minimum publishes only these
        self.assertEqual(ports["web"]["host_port"], 5050)
        self.assertEqual(ports["web"]["source"], "env")
        self.assertEqual(ports["web"]["url"], "http://127.0.0.1:5050")
        self.assertEqual(ports["api"]["host_port"], 8000)  # invalid override ignored

    def test_flag_beats_dotenv(self):
        root = make_root("GRDM_PROFILE=minimum\n")
        rc, out, _ = run_plan(root, profile="full", auth="shibboleth")
        data = json.loads(out)
        names = {r["service"] for r in data["services"]}
        self.assertEqual(data["profile"], "full")
        self.assertIn("shibboleth_sp", names)
        self.assertNotIn("fakecas", names)
        self.assertNotIn("fakecas", {r["service"] for r in data["ports"]})

    def test_invalid_manifest_exits_20(self):
        def bad(data):
            data["components"][0]["integration_repo"] = "RDM-osf.io"  # MC-04: must end in -dev2027
        rc, out, err = run_plan(make_root(mutate=bad))
        self.assertEqual(rc, exit_codes.MANIFEST_INVALID)
        self.assertIn("MC-04", err)
        self.assertEqual(out, "")

    def test_toon_output_and_no_docker_files(self):
        root = make_root()
        rc, out, _ = run_plan(root, json_output=False)
        self.assertEqual(rc, 0)
        self.assertIn("plan:", out)
        self.assertIn("ports[7]{service,host_port,container_port,url,source}:", out)
        self.assertFalse((root / "runtime" / "docker-compose.yml").exists())
        self.assertTrue((root / "runtime" / "reports" / "plan_latest.json").exists())

    def test_prebuilt_component_is_shown_with_its_reference_and_not_built(self):
        """SPEC-01 §3 prebuilt_image: ember-osf-web runs a digest-pinned registry image until M4."""
        rc, out, _ = run_plan(make_root())
        self.assertEqual(rc, exit_codes.OK)
        data = json.loads(out)
        services = {r["service"]: r for r in data["services"]}
        ember = services["ember_osf_web"]
        self.assertRegex(ember["image"], r"^niicloudoperation/rdm-ember-osf-web@sha256:[0-9a-f]{64}$")
        self.assertEqual(ember["build_from"], "prebuilt " + ember["image"])
        self.assertEqual(ember["origin"], "prebuilt")
        self.assertEqual(services["web"]["origin"], "built")
        self.assertEqual(services["postgres"]["origin"], "pinned")
        self.assertEqual(data["prebuilt_images"], [ember["image"]])
        self.assertFalse(any("ember-osf-web" in i for i in data["images_to_build"]))

    def test_without_prebuilt_image_ember_is_built_again(self):
        def strip(data):
            for c in data["components"]:
                if c["id"] == "ember-osf-web":
                    del c["prebuilt_image"]
        rc, out, _ = run_plan(make_root(mutate=strip))
        self.assertEqual(rc, exit_codes.OK)
        data = json.loads(out)
        ember = {r["service"]: r for r in data["services"]}["ember_osf_web"]
        self.assertTrue(ember["image"].startswith("grdm-dev/ember-osf-web:"))
        self.assertTrue(ember["build_from"].startswith("RDM-ember-osf-web-dev2027@"))
        self.assertEqual(data["prebuilt_images"], [])

    def test_read_dotenv_and_resolve_profile(self):
        root = make_root("# comment\nGRDM_PROFILE='full'\nX=\"1\"\n\nbad line\n")
        env = plan.read_dotenv(root / "runtime" / ".env")
        self.assertEqual(env, {"GRDM_PROFILE": "full", "X": "1"})
        self.assertEqual(plan.resolve_profile(Context(root=root), env), "full")
        self.assertEqual(plan.resolve_profile(Context(root=root), {"GRDM_PROFILE": "nonsense"}), "core")


if __name__ == "__main__":
    unittest.main()
