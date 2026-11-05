import argparse
import ast
import io
import json
import os
import re
import shutil
import stat
import tempfile
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from grdm_dev import compose, exit_codes, plan
from grdm_dev.context import Context

REPO_ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = "192.168.168.167"


def fake_secrets(**overrides) -> str:
    values = {k: "x" * 48 for k in compose.REQUIRED_SECRETS}
    values.update(overrides)
    return "".join(f"{k}={v}\n" for k, v in values.items())


def make_root(dotenv: str | None = fake_secrets(), hardening=True) -> Path:
    root = Path(tempfile.mkdtemp(prefix="grdm-compose-"))
    (root / "manifest").mkdir()
    for name in ("upstreams.json", "upstreams.toon"):
        shutil.copy(REPO_ROOT / "manifest" / name, root / "manifest" / name)
    if hardening:
        shutil.copy(REPO_ROOT / "manifest" / "hardening.json", root / "manifest" / "hardening.json")
    if dotenv is not None:
        (root / "runtime").mkdir()
        p = root / "runtime" / ".env"
        p.write_text(dotenv, encoding="utf-8")
        os.chmod(p, 0o600)
    return root


PUBLISHING = {"web", "api", "admin", "wb", "mfr", "ember_osf_web", "fakecas"}


def ps_runner(bindings: dict[str, int] | None = None, rc: int = 0):
    """Fake `docker compose ps --format json` listing our own running containers and their host ports."""
    rows = [{"Service": svc, "Name": f"grdm-dev-{svc}-1", "State": "running",
             "Publishers": [{"URL": "127.0.0.1", "TargetPort": port, "PublishedPort": port, "Protocol": "tcp"}]}
            for svc, port in (bindings or {}).items()]

    def runner(argv):
        runner.calls.append(argv)
        return rc, json.dumps(rows)

    runner.calls = []
    return runner


def render(root: Path, profile="core", auth="fakecas", checker=lambda port: True, memory_gib=16.0, cpus=4.0, json_output=True,
           egress=None, runner=None):
    ctx = Context(root=root, yes=True, json_output=json_output, profile=profile)
    args = argparse.Namespace(compose_command="render", auth=auth, platform="linux/arm64", memory_gib=None, cpus=None, egress=egress)
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = compose.run(ctx, args, memory_gib=memory_gib, cpus=cpus, port_checker=checker, platform_string="linux/arm64",
                         runner=runner or ps_runner())
    return rc, out.getvalue(), err.getvalue(), ctx


def manifest_build_platforms() -> dict[str, str]:
    """service -> build_platform for components that pin one in the repository manifest."""
    data = json.loads((REPO_ROOT / "manifest" / "upstreams.json").read_text(encoding="utf-8"))
    return {svc: comp["build_platform"] for comp in data["components"] if comp.get("build_platform") for svc in comp["services"]}


def load_hardening():
    data = json.loads((REPO_ROOT / "manifest" / "hardening.json").read_text(encoding="utf-8"))
    return {e["service"]: set(e["controls"]) for e in data["exceptions"]}


class ComposeRenderTests(unittest.TestCase):
    def test_render_core_writes_valid_json_with_baseline_controls(self):
        root = make_root()
        rc, out, err, ctx = render(root)
        self.assertEqual(rc, exit_codes.OK, err)
        text = (root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8")
        doc = json.loads(text)  # Compose accepts JSON
        self.assertEqual(list(doc["networks"]), ["grdm", "grdm-edge"])  # grdm first: scan --dynamic attaches ZAP to it
        self.assertIs(doc["networks"]["grdm"]["internal"], True)
        self.assertNotIn("internal", doc["networks"]["grdm-edge"])
        self.assertNotIn(FORBIDDEN, text)
        exceptions = load_hardening()
        build_platforms = manifest_build_platforms()
        services = doc["services"]
        self.assertEqual(set(services), {s["service"] for s in json.loads(out)["services"]})
        self.assertEqual(len(services), 20)  # core profile (SPEC-02 §4)
        for name, svc in services.items():
            relaxed = exceptions.get(name, set())
            # grdm (internal) everywhere; grdm-edge only where a 127.0.0.1 port is published
            if name in PUBLISHING:
                self.assertEqual(svc["networks"], ["grdm", "grdm-edge"], name)
                self.assertEqual(svc["labels"]["org.gakunin-rdm.egress"], "published", name)
            else:
                self.assertEqual(svc["networks"], ["grdm"], name)
                self.assertEqual(svc["labels"]["org.gakunin-rdm.egress"], "none", name)
            self.assertEqual(svc["cap_drop"], ["ALL"], name)
            self.assertIn("no-new-privileges:true", svc["security_opt"], name)
            self.assertNotIn("privileged", svc, name)
            # host platform, unless the manifest component pins a build_platform (mfr etc. on linux/amd64)
            self.assertEqual(svc["platform"], build_platforms.get(name, "linux/arm64"), name)
            for key in ("mem_limit", "cpus", "pids_limit"):
                self.assertIn(key, svc, name)
            if "user" in relaxed:
                self.assertNotIn("user", svc, name)
            else:
                uid = svc["user"].split(":")[0]
                self.assertNotEqual(uid, "0", name)
                self.assertTrue(uid.isdigit(), name)
            self.assertEqual(svc["read_only"], "read_only" not in relaxed, name)
            if "cap_add" in svc:
                self.assertIn("cap_add", relaxed, name)
            for port in svc.get("ports", []):
                self.assertTrue(port.startswith("127.0.0.1:"), port)
            for dep in svc.get("depends_on", []):
                self.assertIn(dep, services, f"{name} depends on {dep} outside the profile")
        published = {name: svc["ports"] for name, svc in services.items() if "ports" in svc}
        self.assertEqual(set(published), set(plan.DEFAULT_PORTS))
        self.assertEqual(published["web"], ["127.0.0.1:5000:5000"])
        # volumes map under runtime/volumes/<name> and the directories exist
        for name, vol in doc["volumes"].items():
            self.assertEqual(vol["driver_opts"]["device"], str(root / "runtime" / "volumes" / name))
            self.assertTrue((root / "runtime" / "volumes" / name).is_dir())

    def test_secrets_stay_out_of_generated_files(self):
        root = make_root(fake_secrets(POSTGRES_PASSWORD="S3cretPgValue" * 3))
        rc, _, _, _ = render(root)
        self.assertEqual(rc, 0)
        for path in (root / "runtime").rglob("*"):
            if path.is_file() and path.name != ".env":
                self.assertNotIn("S3cretPgValue", path.read_text(encoding="utf-8"), str(path))
        doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        self.assertEqual(doc["services"]["postgres"]["environment"]["POSTGRES_PASSWORD"], "${POSTGRES_PASSWORD}")

    def test_config_files_rewrite_upstream_settings(self):
        root = make_root("GRDM_PORT_WEB=5050\n" + fake_secrets())
        rc, _, _, _ = render(root)
        self.assertEqual(rc, 0)
        cfg = root / "runtime" / "config"
        local_py = (cfg / "osf" / "local.py").read_text(encoding="utf-8")
        self.assertIn("DOMAIN = 'http://127.0.0.1:5050/'", local_py)
        self.assertIn("INTERNAL_DOMAIN = 'http://web:5000/'", local_py)
        self.assertIn("WATERBUTLER_INTERNAL_URL = 'http://wb:7777'", local_py)
        self.assertIn("MFR_SERVER_URL = 'http://127.0.0.1:7778'", local_py)
        self.assertIn("CAS_SERVER_URL = 'http://127.0.0.1:8080'", local_py)
        self.assertIn("SECRET_KEY = environ['SECRET_KEY']", local_py)
        self.assertNotIn("CHANGEME", local_py)
        osf_env = plan.read_dotenv(cfg / "osf.env")
        self.assertEqual(osf_env["OSF_DB_HOST"], "postgres")
        self.assertEqual(osf_env["ELASTIC_URI"], "elasticsearch:9200")
        self.assertEqual(osf_env["DOMAIN"], "http://127.0.0.1:5050/")
        wb_env = plan.read_dotenv(cfg / "wb.env")
        self.assertEqual(wb_env["OSF_URL"], "http://web:5000")
        self.assertEqual(plan.read_dotenv(cfg / "mfr.env")["UNOCONV_PORT_2002_TCP_ADDR"], "unoconv")
        self.assertIn("mongodb://mongo:27017/sharejs", plan.read_dotenv(cfg / "sharejs.env")["SHAREJS_DB_URL"])
        for path in cfg.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                self.assertNotIn(FORBIDDEN, text, str(path))
                self.assertNotIn("changeme", text.lower(), str(path))
        # the compose file mounts the rewritten settings and the fakecas redirect uses the overridden port
        doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        self.assertIn("./config/osf/local.py:/code/website/settings/local.py:ro", doc["services"]["web"]["volumes"])
        self.assertIn("-osfhost=127.0.0.1:5050", doc["services"]["fakecas"]["command"])
        self.assertEqual(doc["services"]["web"]["ports"], ["127.0.0.1:5050:5000"])

    def test_missing_env_exits_2_with_hint(self):
        rc, _, err, _ = render(make_root(dotenv=None))
        self.assertEqual(rc, exit_codes.USAGE)
        self.assertIn("grdm-dev secrets init", err)

    def test_missing_secret_key_exits_2(self):
        env = "".join(f"{k}=v\n" for k in compose.REQUIRED_SECRETS if k != "RABBITMQ_DEFAULT_PASS")
        rc, _, err, _ = render(make_root(env))
        self.assertEqual(rc, exit_codes.USAGE)
        self.assertIn("RABBITMQ_DEFAULT_PASS", err)

    def test_invalid_manifest_exits_20(self):
        root = make_root()
        path = root / "manifest" / "upstreams.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["components"][0]["role"] = "weird"
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        rc, _, err, _ = render(root)
        self.assertEqual(rc, exit_codes.MANIFEST_INVALID)
        self.assertIn("MC-03", err)

    # ---- network isolation and egress (review PR #21 finding 8)

    def test_egress_flag_attaches_only_named_services_and_is_recorded_and_kept(self):
        root = make_root()
        rc, out, err, _ = render(root, egress="wb_worker,worker")
        self.assertEqual(rc, 0, err)
        doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        self.assertEqual(doc["services"]["wb_worker"]["networks"], ["grdm", "grdm-edge"])
        self.assertEqual(doc["services"]["wb_worker"]["labels"]["org.gakunin-rdm.egress"], "explicit")
        self.assertEqual(doc["services"]["worker"]["networks"], ["grdm", "grdm-edge"])
        self.assertEqual(doc["services"]["postgres"]["networks"], ["grdm"])
        self.assertEqual(doc["x-grdm-dev"]["egress_services"], ["wb_worker", "worker"])
        env = plan.read_dotenv(root / "runtime" / ".env")
        self.assertEqual(env["GRDM_EGRESS_SERVICES"], "wb_worker,worker")
        self.assertEqual(json.loads(out)["egress_services"], ["wb_worker", "worker"])
        # a later render without the flag keeps the recorded choice; `none` clears it
        rc, _, _, _ = render(root)
        doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        self.assertEqual(doc["services"]["worker"]["networks"], ["grdm", "grdm-edge"])
        rc, _, _, _ = render(root, egress="none")
        doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        self.assertEqual(doc["services"]["worker"]["networks"], ["grdm"])
        self.assertEqual(plan.read_dotenv(root / "runtime" / ".env")["GRDM_EGRESS_SERVICES"], "")

    def test_egress_unknown_service_is_usage_error(self):
        rc, _, err, _ = render(make_root(), egress="web,nothere")
        self.assertEqual(rc, exit_codes.USAGE)
        self.assertIn("nothere", err)

    def test_default_render_records_empty_egress(self):
        root = make_root()
        render(root)
        self.assertEqual(plan.read_dotenv(root / "runtime" / ".env")["GRDM_EGRESS_SERVICES"], "")

    # ---- ports: own running bindings are not collisions (review PR #21 finding 10)

    def test_own_running_service_keeps_its_port_even_though_it_is_busy(self):
        root = make_root()
        render(root)  # compose file exists, as during a re-run of install
        runner = ps_runner({"web": 5000, "api": 8000})
        busy = lambda port: port not in (5000, 8000)  # noqa: E731 - our own containers hold them
        rc, out, err, _ = render(root, checker=busy, runner=runner)
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["remapped_ports"], [])
        kept = {d["service"]: d for d in data["port_decisions"] if d["reason"] == "kept-own-binding"}
        self.assertEqual(set(kept), {"web", "api"})
        self.assertEqual(kept["web"]["chosen"], 5000)
        self.assertIn("web keeps port 5000", err)
        self.assertEqual(plan.read_dotenv(root / "runtime" / ".env")["GRDM_PORT_WEB"], "5000")
        doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        self.assertEqual(doc["services"]["web"]["ports"], ["127.0.0.1:5000:5000"])
        self.assertTrue(any(c[6:] == ["ps", "--format", "json"] for c in runner.calls))

    def test_foreign_listener_moves_the_port_and_rerender_is_idempotent(self):
        root = make_root()
        foreign = lambda port: port != 5000  # noqa: E731 - e.g. macOS AirPlay
        rc, out, err, _ = render(root, checker=foreign)
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["remapped_ports"], [{"service": "web", "wanted": 5000, "chosen": 5001}])
        self.assertEqual([d for d in data["port_decisions"] if d["service"] == "web"][0]["reason"], "remapped-foreign-listener")
        self.assertIn("held by another process", err)
        first = (root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8")
        # the install is now running on 5001; AirPlay still holds 5000: nothing moves again
        rc, out, _, _ = render(root, checker=lambda port: port not in (5000, 5001), runner=ps_runner({"web": 5001}))
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["remapped_ports"], [])
        self.assertEqual(json.loads(out)["written"], ["(unchanged)"])
        self.assertEqual(first, (root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))

    def test_docker_unavailable_falls_back_to_free_port_check(self):
        root = make_root()
        render(root)
        rc, out, _, _ = render(root, runner=ps_runner(rc=1))
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["remapped_ports"], [])

    # ---- per-component build_platform (coordinator addendum)

    def test_build_platform_from_manifest_overrides_host_platform(self):
        root = make_root()
        path = root / "manifest" / "upstreams.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for comp in data["components"]:
            if comp["id"] == "modular-file-renderer":
                comp["build_platform"] = "linux/amd64"
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        rc, out, err, _ = render(root)
        self.assertEqual(rc, 0, err)
        doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        self.assertEqual(doc["services"]["mfr"]["platform"], "linux/amd64")
        self.assertEqual(doc["services"]["web"]["platform"], "linux/arm64")
        rows = {r["service"]: r for r in json.loads(out)["services"]}
        self.assertEqual(rows["mfr"]["platform"], "linux/amd64")

    # ---- prebuilt_image (SPEC-01 §3): compose runs the digest-pinned reference as image:

    def test_prebuilt_image_is_the_compose_image_with_build_platform(self):
        root = make_root()
        data = json.loads((REPO_ROOT / "manifest" / "upstreams.json").read_text(encoding="utf-8"))
        ember = next(c for c in data["components"] if c["id"] == "ember-osf-web")
        reports = root / "runtime" / "reports"
        reports.mkdir(parents=True)
        (reports / "build_latest.json").write_text(json.dumps({"components": [
            {"component": "ember-osf-web", "sha12": "", "status": "prebuilt", "image": ember["prebuilt_image"]},
        ]}), encoding="utf-8")
        rc, out, err, _ = render(root)
        self.assertEqual(rc, 0, err)
        doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        svc = doc["services"]["ember_osf_web"]
        self.assertEqual(svc["image"], ember["prebuilt_image"])
        self.assertRegex(svc["image"], r"^niicloudoperation/rdm-ember-osf-web@sha256:[0-9a-f]{64}$")
        self.assertEqual(svc["platform"], ember["build_platform"])
        self.assertEqual(svc["platform"], "linux/amd64")
        self.assertEqual(svc["cap_drop"], ["ALL"])  # hardening applies to a prebuilt service like any other
        rows = {r["service"]: r for r in json.loads(out)["services"]}
        self.assertEqual(rows["ember_osf_web"]["origin"], "prebuilt")
        self.assertEqual(rows["ember_osf_web"]["image"], ember["prebuilt_image"])
        self.assertEqual(rows["web"]["origin"], "built")
        self.assertEqual(rows["postgres"]["origin"], "pinned")
        self.assertFalse(any(v["image"].startswith("grdm-dev/ember-osf-web") for v in doc["services"].values()))

    def test_removing_prebuilt_image_renders_the_local_build_tag(self):
        root = make_root()
        path = root / "manifest" / "upstreams.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for comp in data["components"]:
            if comp["id"] == "ember-osf-web":
                del comp["prebuilt_image"]
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        rc, out, err, _ = render(root)
        self.assertEqual(rc, 0, err)
        doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        self.assertTrue(doc["services"]["ember_osf_web"]["image"].startswith("grdm-dev/ember-osf-web:"))
        self.assertEqual({r["service"]: r for r in json.loads(out)["services"]}["ember_osf_web"]["origin"], "built")

    def test_prebuilt_without_note_is_rejected_at_render(self):
        root = make_root()
        path = root / "manifest" / "upstreams.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for comp in data["components"]:
            if comp["id"] == "ember-osf-web":
                comp["note"] = None
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        rc, out, err, _ = render(root)
        self.assertEqual(rc, exit_codes.MANIFEST_INVALID)
        self.assertIn("MC-06", err)
        self.assertFalse((root / "runtime" / "docker-compose.yml").exists())

    def test_port_collision_remaps_and_records_in_env(self):
        root = make_root()
        rc, out, _, _ = render(root, checker=lambda port: port not in (5000, 5001))
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["remapped_ports"], [{"service": "web", "wanted": 5000, "chosen": 5002}])
        env = plan.read_dotenv(root / "runtime" / ".env")
        self.assertEqual(env["GRDM_PORT_WEB"], "5002")
        self.assertEqual(env["GRDM_PORT_API"], "8000")
        self.assertEqual(env["GRDM_PROFILE"], "core")
        self.assertEqual(stat.S_IMODE((root / "runtime" / ".env").stat().st_mode), 0o600)
        self.assertEqual(env["POSTGRES_PASSWORD"], "x" * 48)  # secrets preserved
        doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        self.assertEqual(doc["services"]["web"]["ports"], ["127.0.0.1:5002:5000"])

    def test_no_free_port_exits_12(self):
        rc, _, err, _ = render(make_root(), checker=lambda port: port != 5000 and not (5000 <= port <= 5100))
        self.assertEqual(rc, exit_codes.PORT_IN_USE)
        self.assertIn("web", err)

    def test_idempotent_rerun_reports_unchanged(self):
        root = make_root()
        rc1, out1, _, _ = render(root)
        before = (root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8")
        rc2, out2, _, _ = render(root)
        self.assertEqual((rc1, rc2), (0, 0))
        self.assertEqual(before, (root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        self.assertEqual(json.loads(out2)["written"], ["(unchanged)"])

    def test_profiles_minimum_and_full_shibboleth(self):
        root = make_root()
        rc, _, _, _ = render(root, profile="minimum")
        self.assertEqual(rc, 0)
        doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        self.assertEqual(set(doc["services"]), {"web", "api", "postgres", "elasticsearch", "rabbitmq", "fakecas"})
        self.assertEqual(doc["services"]["web"]["depends_on"], ["postgres", "rabbitmq", "elasticsearch"])
        rc, _, _, _ = render(root, profile="full", auth="shibboleth")
        self.assertEqual(rc, 0)
        doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        self.assertIn("shibboleth_sp", doc["services"])
        self.assertNotIn("fakecas", doc["services"])
        self.assertEqual(len(doc["services"]), 24)

    # ---- `--auth shibboleth` profile (SPEC-02 §4, SPEC-04 §5 S5, ADR-05): test_idp and shibboleth_sp rendering

    def _render_shibboleth(self, dotenv: str = fake_secrets()):
        root = make_root(dotenv)
        rc, out, err, _ = render(root, profile="full", auth="shibboleth")
        self.assertEqual(rc, exit_codes.OK, err)
        doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        return root, doc, json.loads(out)

    def test_shibboleth_profile_publishes_idp_and_sp_on_loopback_and_drops_fakecas(self):
        root, doc, data = self._render_shibboleth()
        services = doc["services"]
        self.assertNotIn("fakecas", services)
        self.assertIn("test_idp", services)
        self.assertIn("shibboleth_sp", services)
        # the browser must reach both (SAML redirects and the ACS POST), so both publish on 127.0.0.1 and join grdm-edge
        self.assertEqual(services["test_idp"]["ports"], ["127.0.0.1:8081:8080"])
        self.assertEqual(services["shibboleth_sp"]["ports"], ["127.0.0.1:8082:80"])
        for name in ("test_idp", "shibboleth_sp"):
            self.assertEqual(services[name]["networks"], ["grdm", "grdm-edge"], name)
            self.assertEqual(services[name]["labels"]["org.gakunin-rdm.egress"], "published", name)
            self.assertEqual(services[name]["cap_drop"], ["ALL"], name)
            self.assertIn("no-new-privileges:true", services[name]["security_opt"], name)
            self.assertNotIn("privileged", services[name], name)
            self.assertNotIn("expose", services[name], name)   # published: nothing stays internal-only
        # 8080 stays reserved for fakecas in the ports table; the IdP must not take it even though fakecas is absent
        self.assertNotIn("127.0.0.1:8080", json.dumps(services))
        published = {r["service"]: r["host_port"] for r in data["ports"]}
        self.assertEqual(published["test_idp"], 8081)
        self.assertEqual(published["shibboleth_sp"], 8082)
        self.assertNotIn("fakecas", published)
        env = plan.read_dotenv(root / "runtime" / ".env")
        self.assertEqual(env["GRDM_PORT_TEST_IDP"], "8081")       # the acceptance suite reads these (S5)
        self.assertEqual(env["GRDM_PORT_SHIBBOLETH_SP"], "8082")
        self.assertEqual(env["GRDM_PROFILE"], "full")
        self.assertEqual(data["auth"], "shibboleth")

    def test_shibboleth_sp_environment_points_at_web_and_the_test_idp_by_rendered_ports(self):
        root, doc, _ = self._render_shibboleth("GRDM_PORT_WEB=5050\n" + fake_secrets())
        sp = doc["services"]["shibboleth_sp"]["environment"]
        idp = doc["services"]["test_idp"]["environment"]
        self.assertEqual(sp["OSF_INTERNAL_URL"], "http://web:5000/")                 # service name inside the network (ADR-02)
        self.assertEqual(sp["OSF_EXTERNAL_URL"], "http://127.0.0.1:5050/")            # browser-facing URL follows the override
        self.assertEqual(sp["SP_ENTITY_ID"], "http://127.0.0.1:8082/shibboleth")
        self.assertEqual(sp["IDP_ENTITY_ID"], "http://127.0.0.1:8081/simplesaml/saml2/idp/metadata.php")
        self.assertEqual(idp["TEST_IDP_ENTITY_ID"], sp["IDP_ENTITY_ID"])              # both sides name the same IdP
        self.assertEqual(idp["TEST_IDP_SP_ENTITY_ID"], sp["SP_ENTITY_ID"])            # and the same SP
        self.assertEqual(idp["TEST_IDP_SP_ACS_URL"], "http://127.0.0.1:8082/Shibboleth.sso/SAML2/POST")
        self.assertEqual(sp["SP_HANDLER_SSL"], "false")                               # plain HTTP on loopback (SPEC-04 §3.4)
        self.assertIn("HttpOnly", sp["SP_COOKIE_PROPS"])
        self.assertIn("SameSite=Lax", sp["SP_COOKIE_PROPS"])
        self.assertNotIn("Secure", sp["SP_COOKIE_PROPS"])
        self.assertEqual(sp["SP_REQUIRED_AFFILIATION"], "member")                     # S5 rejection rule
        for value in list(sp.values()) + list(idp.values()):
            self.assertNotIn("{{", value, value)                                      # every placeholder was substituted
            self.assertNotIn("https://", value, value)                                # nothing asks the browser for TLS
            self.assertNotIn("localhost", value, value)
        self.assertEqual(doc["services"]["shibboleth_sp"]["depends_on"], ["web", "test_idp"])
        self.assertNotIn("depends_on", doc["services"]["test_idp"])

    def test_shibboleth_services_mount_rendered_idp_and_sp_config_read_only(self):
        _, doc, _ = self._render_shibboleth()
        idp_mounts = doc["services"]["test_idp"]["volumes"]
        self.assertEqual(idp_mounts, [
            "./config/idp/config:/var/simplesamlphp/config:ro",
            "./config/idp/metadata:/var/simplesamlphp/metadata:ro",
            "./config/idp/cert:/var/simplesamlphp/cert:ro",
        ])
        sp_mounts = doc["services"]["shibboleth_sp"]["volumes"]
        self.assertIn("./config/shibboleth_sp/shibboleth2.xml:/etc/shibboleth/shibboleth2.xml:ro", sp_mounts)
        self.assertIn("./config/shibboleth_sp/attribute-map.xml:/etc/shibboleth/attribute-map.xml:ro", sp_mounts)
        self.assertIn("./config/shibboleth_sp/idp-metadata.xml:/etc/shibboleth/idp-metadata.xml:ro", sp_mounts)
        self.assertIn("./config/idp/cert/sp.key:/etc/shibboleth/sp-key.pem:ro", sp_mounts)
        self.assertTrue(all(m.endswith(":ro") for m in idp_mounts + sp_mounts))
        # writable paths are explicit tmpfs, so read_only can hold once the hardening exception goes (ADR-05)
        self.assertIn("/var/simplesamlphp/log", doc["services"]["test_idp"]["tmpfs"])
        self.assertIn("/var/simplesamlphp/data", doc["services"]["test_idp"]["tmpfs"])
        # every rendered file the two services mount has a template under templates/idp/ (follow-up F-1 renders them)
        tpl_dir = Path(compose.__file__).parent / "templates" / "idp"
        expected = {"config.php.tmpl", "authsources.php.tmpl", "saml20-idp-hosted.php.tmpl", "saml20-sp-remote.php.tmpl",
                    "sp-shibboleth2.xml.tmpl", "sp-attribute-map.xml", "sp-idp-metadata.xml.tmpl", "README.md"}
        self.assertEqual({p.name for p in tpl_dir.iterdir()}, expected)

    def test_shibboleth_hardening_follows_manifest_exceptions(self):
        _, doc, data = self._render_shibboleth()
        exceptions = load_hardening()
        rows = {r["service"]: r for r in data["services"]}
        for name in ("test_idp", "shibboleth_sp"):
            svc = doc["services"][name]
            relaxed = exceptions.get(name, set())
            self.assertEqual("user" not in svc, "user" in relaxed, name)
            self.assertEqual(svc["read_only"], "read_only" not in relaxed, name)
            self.assertEqual(rows[name]["exceptions"], ",".join(sorted(relaxed)) if relaxed else "none", name)
        # the SP binds port 80 as root and needs exactly the recorded capability for it; the IdP (uid 1000 on 8080) needs none
        self.assertIn("NET_BIND_SERVICE", doc["services"]["shibboleth_sp"].get("cap_add", []))
        self.assertNotIn("cap_add", doc["services"]["test_idp"])
        # the template itself asks for a non-root user, so the service becomes non-root the moment the exception is removed (F-3)
        tpl = json.loads((Path(compose.__file__).parent / "templates" / "test_idp.json").read_text(encoding="utf-8"))
        self.assertEqual(tpl["user"], "1000:1000")
        self.assertEqual(tpl["container_port"], 8080)   # unprivileged port: no NET_BIND_SERVICE needed

    # ---- mock users (ADR-05 §3.5) and the attribute contract between IdP and SP (ADR-05 §3.7)

    IDP_TEMPLATES = Path(compose.__file__).parent / "templates" / "idp"
    FIXTURE = REPO_ROOT / "installer" / "acceptance" / "fixtures" / "idp" / "mock_users.json"
    # The one documented exception to the all-values-mock rule: eduPersonAffiliation is a controlled vocabulary and
    # the SP rule (SP_REQUIRED_AFFILIATION=member) can only be exercised with real vocabulary values (ADR-05 §3.5).
    AFFILIATION_ALLOW_LIST = frozenset({"member", "faculty", "student", "affiliate"})
    # Verified GakuNin schema OIDs (学認技術運用基準 Ver. 2.6 別添; NII GakuNinShibInstall 属性リスト): friendlyName jao = .4, jaDisplayName = .3
    GAKUNIN_OIDS = {"jaOrganizationName": "urn:oid:1.3.6.1.4.1.32264.1.1.4", "jaDisplayName": "urn:oid:1.3.6.1.4.1.32264.1.1.3"}
    PAIRWISE_ID = "urn:oasis:names:tc:SAML:attribute:pairwise-id"

    @classmethod
    def looks_mock(cls, key: str, value: str) -> bool:
        """ADR-05 §3.5: visibly mock, except the eduPersonAffiliation vocabulary allow-list."""
        if key == "eduPersonAffiliation":
            return value in cls.AFFILIATION_ALLOW_LIST
        return value.startswith(("mock-", "MOCK", "モック", "https://idp.mock.test/")) or value.endswith("@idp.mock.test")

    @staticmethod
    def parse_authsources(text: str) -> dict[str, dict[str, list[str]]]:
        """'user:pass' => [ 'attr' => ['v1', 'v2'], ... ] blocks of authsources.php.tmpl -> {'user:pass': {attr: [values]}}."""
        users: dict[str, dict[str, list[str]]] = {}
        for m in re.finditer(r"^\s{8}'([^']+:[^']+)' => \[\n(.*?)^\s{8}\],", text, re.S | re.M):
            attrs: dict[str, list[str]] = {}
            for line in m.group(2).splitlines():
                am = re.match(r"^\s{12}'([^']+)' => \[(.*)\],$", line)
                if not am:
                    raise AssertionError(f"unparsed authsources line: {line!r}")
                attrs[am.group(1)] = re.findall(r"'([^']*)'", am.group(2))
            users[m.group(1)] = attrs
        return users

    @classmethod
    def parse_idp_wire_names(cls) -> tuple[dict[str, str], dict[str, str]]:
        """$gakuninWireNames (friendly -> wire) and attributeencodings (wire -> encoding) of saml20-idp-hosted.php.tmpl."""
        text = (cls.IDP_TEMPLATES / "saml20-idp-hosted.php.tmpl").read_text(encoding="utf-8")
        block = re.search(r"^\$gakuninWireNames = \[\n(.*?)^\];", text, re.S | re.M)
        assert block, "saml20-idp-hosted.php.tmpl must define $gakuninWireNames"
        names = dict(re.findall(r"^\s+'([^']+)' => '(urn:[^']+)',", block.group(1), re.M))
        enc_block = re.search(r"'attributeencodings' => \[\n(.*?)\n\s+\],", text, re.S)
        encodings = dict(re.findall(r"'([^']+)' => '([^']+)'", enc_block.group(1))) if enc_block else {}
        assert not re.search(r"""['"]name2oid['"]""", text), "the IdP must not load the generic name2oid map (no GakuNin names in it)"
        assert f"$pairwiseIdWireName = '{cls.PAIRWISE_ID}';" in text
        return names, encodings

    @classmethod
    def parse_sp_attribute_map(cls) -> dict[str, dict]:
        """attribute-map.xml -> {wire name: {'id': header id, 'decoder': xsi:type or None}}."""
        ns = {"am": "urn:mace:shibboleth:2.0:attribute-map", "xsi": "http://www.w3.org/2001/XMLSchema-instance"}
        root = ET.fromstring((cls.IDP_TEMPLATES / "sp-attribute-map.xml").read_text(encoding="utf-8"))
        out = {}
        for attr in root.findall("am:Attribute", ns):
            dec = attr.find("am:AttributeDecoder", ns)
            out[attr.get("name")] = {"id": attr.get("id"), "decoder": dec.get(f"{{{ns['xsi']}}}type") if dec is not None else None}
        return out

    def test_mock_users_fixture_and_idp_authsources_agree_per_user_and_attribute(self):
        """ADR-05 §3.5: one canonical MOCK list, mirrored in the IdP template; compared structurally, not by substring."""
        fixture = json.loads(self.FIXTURE.read_text(encoding="utf-8"))
        authsources = self.parse_authsources((self.IDP_TEMPLATES / "authsources.php.tmpl").read_text(encoding="utf-8"))
        self.assertIn("MOCK", fixture["_label"])
        expected = {}
        for user in fixture["users"]:
            self.assertTrue(user["username"].startswith("mock-") and user["password"].startswith("mock-"), user["username"])
            self.assertEqual(user["attributes"]["uid"], user["username"])
            expected[f"{user['username']}:{user['password']}"] = {
                k: (v if isinstance(v, list) else [v]) for k, v in user["attributes"].items()
            }
        self.assertEqual(authsources, expected)   # same users, same attributes, same values in the same order per user
        roles = {u["role"] for u in fixture["users"]}
        self.assertTrue({"success", "rejection"} <= roles, roles)
        # the derived identifiers are never stored per user (the authproc filters generate them from uid)
        for user in fixture["users"]:
            self.assertNotIn("eduPersonTargetedID", user["attributes"])
            self.assertNotIn("pairwise-id", user["attributes"])
        self.assertEqual(set(fixture["derived_identifiers"]), {"eduPersonTargetedID", "pairwise-id"})

    def test_mock_values_are_visibly_mock_except_the_affiliation_vocabulary(self):
        """ADR-05 §3.5 rule and its single documented exception, encoded as an allow-list of exactly the vocabulary values."""
        fixture = json.loads(self.FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(fixture["affiliation_vocabulary_exception"]["attribute"], "eduPersonAffiliation")
        self.assertEqual(set(fixture["affiliation_vocabulary_exception"]["allowed_values"]), self.AFFILIATION_ALLOW_LIST)
        for user in fixture["users"]:
            for key, value in user["attributes"].items():
                for v in (value if isinstance(value, list) else [value]):
                    self.assertTrue(self.looks_mock(key, v), f"{user['username']}.{key}={v!r} is not visibly mock (ADR-05 §3.5)")
        for key, value in fixture["institution"].items():
            if key != "entity_id_note":
                self.assertTrue(self.looks_mock(key, value), f"institution.{key}={value!r}")
        # the exception is exactly the vocabulary: a plausible name, a bare surname, a real-looking domain or a
        # non-vocabulary affiliation all fail
        self.assertFalse(self.looks_mock("sn", "USER"))
        self.assertFalse(self.looks_mock("givenName", "Taro"))
        self.assertFalse(self.looks_mock("mail", "user01@example.ac.jp"))
        self.assertFalse(self.looks_mock("eduPersonAffiliation", "mock-member"))
        self.assertFalse(self.looks_mock("eduPersonAffiliation", "staff"))
        self.assertFalse(self.looks_mock("o", "member"))          # the vocabulary is allowed only under eduPersonAffiliation
        self.assertTrue(self.looks_mock("eduPersonAffiliation", "member"))
        # the rejection user really lacks the affiliation the SP requires, and the success user has it
        by_role = {u["role"]: u for u in fixture["users"]}
        self.assertIn("member", by_role["success"]["attributes"]["eduPersonAffiliation"])
        self.assertNotIn("member", by_role["rejection"]["attributes"]["eduPersonAffiliation"])
        sp = json.loads((Path(compose.__file__).parent / "templates" / "shibboleth_sp.json").read_text(encoding="utf-8"))
        self.assertEqual(sp["environment"]["SP_REQUIRED_AFFILIATION"], "member")
        # no real-looking e-mail or institution anywhere in the mock material
        authsources = (self.IDP_TEMPLATES / "authsources.php.tmpl").read_text(encoding="utf-8")
        for text in (json.dumps(fixture, ensure_ascii=False), authsources):
            self.assertNotRegex(text, r"@[a-z0-9.-]+\.(ac\.jp|edu|com|org)\b")
            self.assertNotIn("Test User", text)

    def test_idp_emitted_wire_names_equal_sp_decoded_names_for_every_fixture_attribute(self):
        """ADR-05 §3.7: the IdP's explicit name map and the SP's attribute-map.xml agree for every attribute the mock users carry."""
        fixture = json.loads(self.FIXTURE.read_text(encoding="utf-8"))
        wire, encodings = self.parse_idp_wire_names()
        sp_map = self.parse_sp_attribute_map()
        fixture_attrs = set()
        for user in fixture["users"]:
            fixture_attrs |= set(user["attributes"])
        fixture_attrs.discard("uid")                                   # the login key: derived identifiers come from it, it is never released
        self.assertNotIn("uid", wire)
        emitted = set(fixture_attrs) | set(fixture["derived_identifiers"])
        # every emitted friendly name has an explicit wire name (pairwise-id is named by saml:PairwiseID itself)
        for name in emitted - {"pairwise-id"}:
            self.assertIn(name, wire, f"{name} has no entry in $gakuninWireNames")
        wire_names = {wire[n] for n in emitted - {"pairwise-id"}} | {self.PAIRWISE_ID}
        # IdP-side emitted names == SP-side decoded names (one-to-one; no SP entry without an IdP source and vice versa)
        self.assertEqual(wire_names, set(sp_map), "IdP wire names and SP attribute-map.xml names differ")
        self.assertEqual(len(set(wire.values())), len(wire), "two friendly names map to the same OID")
        self.assertTrue(all(v.startswith("urn:oid:") for v in wire.values()), wire)
        # verified GakuNin schema OIDs; the SP id keeps the full attribute name
        for friendly, oid in self.GAKUNIN_OIDS.items():
            self.assertEqual(wire[friendly], oid)
            self.assertEqual(sp_map[oid]["id"], friendly)
        self.assertNotIn("urn:oid:1.2.392.200453.100.20.1", set(wire.values()) | set(sp_map), "not a GakuNin OID (ADR-05 §3.7)")
        # eduPersonTargetedID: NameID-valued on both sides (TargetedID nameId => true + 'raw' encoding; NameIDAttributeDecoder)
        eptid = wire["eduPersonTargetedID"]
        self.assertEqual(eptid, "urn:oid:1.3.6.1.4.1.5923.1.1.1.10")
        self.assertEqual(encodings, {eptid: "raw"})
        self.assertEqual(sp_map[eptid]["decoder"], "NameIDAttributeDecoder")
        self.assertEqual(sp_map[self.PAIRWISE_ID]["decoder"], "ScopedAttributeDecoder")
        # scoped attributes are decoded as scoped on the SP side
        for scoped in ("eduPersonPrincipalName", "eduPersonScopedAffiliation"):
            self.assertEqual(sp_map[wire[scoped]]["decoder"], "ScopedAttributeDecoder", scoped)
        # the authproc chain generates the derived identifiers from uid, maps, then limits to the contract
        hosted = (self.IDP_TEMPLATES / "saml20-idp-hosted.php.tmpl").read_text(encoding="utf-8")
        self.assertRegex(hosted, r"'core:TargetedID', 'identifyingAttribute' => 'uid', 'nameId' => true")
        self.assertRegex(hosted, r"'saml:PairwiseID', 'identifyingAttribute' => 'uid', 'scopeAttribute' => 'eduPersonScopedAffiliation'")
        self.assertIn("['class' => 'core:AttributeMap'] + $gakuninWireNames", hosted)
        self.assertIn("'core:AttributeLimit', 'default' => false], array_values($gakuninWireNames), [$pairwiseIdWireName]", hosted)
        self.assertIn("'attributes.NameFormat' => 'urn:oasis:names:tc:SAML:2.0:attrname-format:uri'", hosted)

    def test_s2_rejection_requires_transport_status_not_embedded_json_status(self):
        """SPEC-04 §5 S2: 401 without a token and 403 for user_b are HTTP status lines; 200 + embedded 403 fails (review I3)."""
        src = (REPO_ROOT / "installer" / "acceptance" / "test_s2_rdmcp.py").read_text(encoding="utf-8")
        from acceptance.netguard import transport_status_must_be as check
        check(403, '{"jsonrpc":"2.0","id":3,"error":{"code":-32001,"message":"forbidden"}}', 403)
        check(401, "", 401)
        with self.assertRaisesRegex(AssertionError, "HTTP 200 carrying an embedded http_status 403"):
            check(200, '{"jsonrpc":"2.0","id":3,"error":{"code":-32001,"data":{"http_status":403}}}', 403)
        with self.assertRaisesRegex(AssertionError, "expected transport HTTP 403, got 200"):
            check(200, '{"jsonrpc":"2.0","id":3,"result":{}}', 403)
        with self.assertRaisesRegex(AssertionError, "404 is not acceptable"):
            check(404, "", 403)
        with self.assertRaisesRegex(AssertionError, "expected transport HTTP 401, got 200"):
            check(200, "not json", 401)
        # the test module no longer substitutes an embedded status for the transport status
        self.assertNotIn('.get("http_status") or 0', src)
        self.assertIn("transport_status_must_be(resp.status, resp.text(), 403)", src)
        self.assertIn("transport_status_must_be(anon.status, anon.text(), 401)", src)

    def test_resource_limits_scale_with_memory(self):
        root = make_root()
        render(root, memory_gib=8.0)
        small = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))["services"]
        render(root, memory_gib=64.0)
        big = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))["services"]
        mb = lambda s: int(s["mem_limit"].rstrip("m"))  # noqa: E731
        self.assertGreater(mb(big["web"]), mb(small["web"]))
        self.assertGreaterEqual(mb(small["web"]), 512)  # template minimum
        total = sum(mb(s) for s in big.values())
        self.assertLessEqual(total, 64 * 1024 * compose.MEMORY_SHARE + 2048)
        self.assertTrue(all(0.5 <= s["cpus"] <= 4.0 for s in big.values()))

    def test_build_report_tags_win_over_manifest(self):
        root = make_root()
        reports = root / "runtime" / "reports"
        reports.mkdir(parents=True)
        (reports / "build_latest.json").write_text(json.dumps({"components": [
            {"component": "osf.io", "sha12": "feedfacecafe", "status": "built"},
            {"component": "waterbutler", "sha12": "000000000000", "status": "build-failed"},
        ]}), encoding="utf-8")
        rc, _, _, _ = render(root)
        self.assertEqual(rc, 0)
        doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        self.assertEqual(doc["services"]["web"]["image"], "grdm-dev/osf.io:feedfacecafe")
        self.assertTrue(doc["services"]["wb"]["image"].startswith("grdm-dev/waterbutler:"))
        self.assertNotEqual(doc["services"]["wb"]["image"], "grdm-dev/waterbutler:000000000000")

    def test_hardening_file_is_well_formed(self):
        data = json.loads((REPO_ROOT / "manifest" / "hardening.json").read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], 1)
        for entry in data["exceptions"]:
            self.assertTrue(entry["reason"])
            self.assertRegex(entry["review"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertTrue(set(entry["controls"]) <= {"user", "read_only", "cap_add"}, entry["service"])
            if "cap_add" in entry["controls"]:
                self.assertTrue(entry.get("cap_add"), entry["service"])

    def test_toon_summary(self):
        rc, out, _, _ = render(make_root(), json_output=False)
        self.assertEqual(rc, 0)
        self.assertIn("compose:", out)
        self.assertIn("network: grdm", out)
        self.assertIn("grdm-edge", out)
        self.assertIn("ports[7]", out)

    def test_non_render_action_is_usage_error(self):
        ctx = Context(root=make_root(), yes=True)
        with redirect_stderr(io.StringIO()):
            rc = compose.run(ctx, argparse.Namespace(compose_command=None))
        self.assertEqual(rc, exit_codes.USAGE)


if __name__ == "__main__":
    unittest.main()
