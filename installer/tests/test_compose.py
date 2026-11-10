import argparse
import ast
import io
import json
import os
import pathlib
import re
import shutil
import stat
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from grdm_dev import compose, exit_codes, plan
from grdm_dev.context import Context

REPO_ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = "192.168.168.167"


def fake_value(key: str) -> str:
    """A placeholder that `compose render` accepts for this key ("x" * 43 is not canonical base64url of 32 bytes)."""
    from grdm_dev import secrets as _secrets

    size = _secrets.CAS_KEY_RULES.get(key, (48, None))[0]
    return "A" * size if key == "TGC_ENCRYPTION_KEY" else "x" * size


def fake_secrets(**overrides) -> str:
    values = {k: fake_value(k) for k in compose.REQUIRED_SECRETS}
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


PUBLISHING = {"web", "api", "admin", "wb", "mfr", "ember_osf_web", "fakecas", "y_websocket", "sharejs"}


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
    def render_core_doc(self):
        root = make_root()
        rc, _, err, _ = render(root)
        self.assertEqual(rc, exit_codes.OK, err)
        return json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))

    def test_render_core_writes_valid_json_with_baseline_controls(self):
        root = make_root()
        rc, out, err, ctx = render(root)
        self.assertEqual(rc, exit_codes.OK, err)
        text = (root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8")
        doc = json.loads(text)  # Compose accepts JSON
        self.assertEqual(list(doc["networks"]), ["grdm", "grdm-edge", "grdm-convert"])  # grdm first: scan --dynamic attaches ZAP to it
        self.assertIs(doc["networks"]["grdm"]["internal"], True)
        self.assertNotIn("internal", doc["networks"]["grdm-edge"])
        self.assertNotIn(FORBIDDEN, text)
        exceptions = load_hardening()
        build_platforms = manifest_build_platforms()
        services = doc["services"]
        self.assertEqual(set(services), {s["service"] for s in json.loads(out)["services"]})
        self.assertEqual(len(services), 24)  # core profile (SPEC-02 §4), one-shots osf_init, volume_owner_init, volume_access_check_*, wiki_assets included
        self.assertNotIn("wiki", services)
        for name, svc in services.items():
            relaxed = exceptions.get(name, set())
            # grdm (internal) everywhere; grdm-edge only where a 127.0.0.1 port is published
            if name in PUBLISHING:
                expected = ["grdm", "grdm-convert", "grdm-edge"] if name == "mfr" else ["grdm", "grdm-edge"]
                self.assertEqual(svc["networks"], expected, name)
                self.assertEqual(svc["labels"]["org.gakunin-rdm.egress"], "published", name)
            else:
                self.assertEqual(svc["networks"], ["grdm-convert"] if name == "unoconv" else ["grdm"], name)
                self.assertEqual(svc["labels"]["org.gakunin-rdm.egress"], "none", name)
            self.assertEqual(svc["cap_drop"], ["ALL"], name)
            self.assertIn("no-new-privileges:true", svc["security_opt"], name)
            self.assertNotIn("privileged", svc, name)
            # host platform, unless the manifest component pins a build_platform (mfr etc. on linux/amd64)
            self.assertEqual(svc["platform"], build_platforms.get(name, "linux/arm64"), name)
            for key in ("mem_limit", "cpus", "pids_limit"):
                self.assertIn(key, svc, name)
            if "user" in relaxed:
                if name == "volume_owner_init":
                    self.assertEqual(svc["user"], "0:0", name)  # explicit root via template run_as (ADR-07, PR #34 r1 R1-01)
                else:
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
        self.assertEqual(set(published), set(plan.DEFAULT_PORTS) | {"y_websocket", "sharejs"})
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
        # website/views.py reads EXTERNAL_EMBER_APPS['preprints']['path'] at import (real install run 9)
        self.assertIn("'preprints': {'server': 'http://ember_osf_web:4201/', 'path': '/preprints/'}", local_py)
        self.assertIn("'reviews': {", local_py)
        self.assertIn("MFR_SERVER_URL = 'http://127.0.0.1:7778'", local_py)
        self.assertIn("CAS_SERVER_URL = 'http://127.0.0.1:8080'", local_py)
        mfr_env = (cfg / "mfr.env").read_text(encoding="utf-8")
        self.assertIn("OSF_PROVIDER_CONFIG_CREDENTIAL_SOURCE_ORIGINS=http://web:5000", mfr_env)
        self.assertIn("OSF_PROVIDER_CONFIG_CREDENTIAL_TARGET_ORIGINS=http://wb:7777", mfr_env)
        self.assertIn("SECRET_KEY = environ['SECRET_KEY']", local_py)
        self.assertIn("DEFAULT_HMAC_SECRET = environ['WATERBUTLER_HMAC_SECRET']", local_py)
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
        self.assertIn("-osfhost=127.0.0.1:5050", " ".join(doc["services"]["fakecas"]["command"]))  # one `sh -c` string
        self.assertEqual(doc["services"]["web"]["ports"], ["127.0.0.1:5050:5000"])

    def test_browser_collaboration_urls_use_only_published_loopback_ports(self):
        root = make_root("GRDM_PORT_Y_WEBSOCKET=1240\n" + fake_secrets())
        rc, _, _, _ = render(root)
        self.assertEqual(rc, 0)
        doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        self.assertEqual(doc["services"]["y_websocket"]["ports"], ["127.0.0.1:1240:1234"])
        self.assertEqual(doc["services"]["sharejs"]["ports"], ["127.0.0.1:7007:7007"])
        self.assertIn("./config/osf/wiki_local.py:/code/addons/wiki/settings/local.py:ro", doc["services"]["web"]["volumes"])
        wiki = (root / "runtime" / "config" / "osf" / "wiki_local.py").read_text(encoding="utf-8")
        self.assertIn("Y_WEBSOCKET_URL = '127.0.0.1:1240'", wiki)
        self.assertIn("SHAREJS_URL = '127.0.0.1:7007'", wiki)
        self.assertNotIn("localhost", wiki)
        self.assertNotIn("SHAREJS_HOST", wiki)  # server-side address; only the browser URL is rewritten

    def test_wiki_local_omits_services_that_are_not_published(self):
        wiki = compose.render_wiki_local_py({"sharejs": 7007})
        self.assertIn("SHAREJS_URL = '127.0.0.1:7007'", wiki)
        self.assertNotIn("Y_WEBSOCKET_URL", wiki)

    def test_only_web_opts_out_of_osf_debug_mode(self):
        root = make_root(fake_secrets())
        rc, _, _, _ = render(root)
        self.assertEqual(rc, 0)
        local_py = (root / "runtime" / "config" / "osf" / "local.py").read_text(encoding="utf-8")
        self.assertIn("DEBUG_MODE = environ.get('GRDM_OSF_DEBUG_MODE', 'True') == 'True'", local_py)
        doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        self.assertEqual(doc["services"]["web"]["environment"]["GRDM_OSF_DEBUG_MODE"], "False")
        for service in ("api", "admin", "worker", "osf_init"):
            self.assertNotIn("GRDM_OSF_DEBUG_MODE", doc["services"][service]["environment"], service)

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

    # ---- memory budget is capped by the Docker VM (real install run 10)

    def _render_with_vm(self, vm_bytes: int, memory_gib=None, host_gib: float = 128.0):
        """Render with a faked `docker info` VM size and a faked host memory (the real machine's size must
        not leak into the test: PR #33 review r2 R2-01 — CI runners have far less than the core floor)."""
        def runner(argv):
            if argv[:2] == ["docker", "info"]:
                return 0, f"{vm_bytes}\n"
            return ps_runner()(argv)
        root = make_root()
        try:
            ctx = Context(root=root, yes=True, json_output=True, profile="core")
            args = argparse.Namespace(compose_command="render", auth="fakecas", platform="linux/arm64", memory_gib=memory_gib, cpus=None, egress=None)
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err), mock.patch.object(compose, "detect_memory_gib", return_value=host_gib):
                rc = compose.run(ctx, args, cpus=4.0, port_checker=lambda port: True, platform_string="linux/arm64", runner=runner)
            report_path = root / "runtime" / "reports" / "compose_latest.json"
            report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
            doc_path = root / "runtime" / "docker-compose.yml"
            doc = json.loads(doc_path.read_text(encoding="utf-8")) if doc_path.exists() else {}
            return rc, err.getvalue(), report.get("data", report), doc
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_memory_budget_uses_docker_vm_when_smaller(self):
        rc, _, report, doc = self._render_with_vm(48 * 1024 ** 3, host_gib=128.0)  # 48 GiB VM on a 128 GiB host
        self.assertEqual(rc, exit_codes.OK)
        self.assertEqual(report["memory_gib"], 48.0)  # the smaller of host and engine VM
        total = sum(int(s["mem_limit"].rstrip("m")) for s in doc["services"].values())
        self.assertLessEqual(total, 48 * 1024 * compose.MEMORY_SHARE)  # floors fit, so the sum stays inside the budget

    def test_infeasible_memory_floors_are_exit_10_unless_overcommit_is_explicit(self):
        """PR #33 review r1 R1-04: an 8 GiB Docker VM cannot hold the core floors (ember alone needs 8 GiB)."""
        rc, err, _, _ = self._render_with_vm(8 * 1024 ** 3)
        self.assertEqual(rc, exit_codes.HOST_UNSUPPORTED)
        self.assertIn("memory floors", err)
        self.assertIn("--memory-gib", err)
        rc, _, _, doc = self._render_with_vm(8 * 1024 ** 3, memory_gib=8.0)  # explicit value = knowing overcommit
        self.assertEqual(rc, exit_codes.OK)
        self.assertGreater(sum(int(s["mem_limit"].rstrip("m")) for s in doc["services"].values()), 8 * 1024 * compose.MEMORY_SHARE)

    def test_sum_of_floors_fits_the_documented_minimum_vm(self):
        """SPEC-02 §8: the core profile needs a 24 GiB Docker VM on Apple Silicon (ember 8 GiB floor under emulation)."""
        rc, _, report, _ = self._render_with_vm(24 * 1024 ** 3, host_gib=64.0)
        self.assertEqual(rc, exit_codes.OK)
        self.assertEqual(report["memory_gib"], 24.0)

    def test_small_host_caps_the_budget_below_the_vm(self):
        """A 16 GiB laptop with a 48 GiB (misconfigured) VM: the host wins, the core floors do not fit, exit 10."""
        rc, err, _, _ = self._render_with_vm(48 * 1024 ** 3, host_gib=16.0)
        self.assertEqual(rc, exit_codes.HOST_UNSUPPORTED)
        self.assertIn("16.0 GiB", err)

    def test_detect_docker_memory_gib_tolerates_bad_output(self):
        self.assertIsNone(compose.detect_docker_memory_gib(lambda argv: (1, "")))
        self.assertIsNone(compose.detect_docker_memory_gib(lambda argv: (0, "not a number")))
        self.assertAlmostEqual(compose.detect_docker_memory_gib(lambda argv: (0, str(4 * 1024 ** 3))), 4.0)

    # ---- tmpfs mounts are world-writable (real install run 11)

    def test_converter_is_reachable_only_from_mfr_and_requires_a_credential(self):
        doc = self.render_core_doc()
        self.assertIs(doc["networks"]["grdm-convert"]["internal"], True)
        on_convert = sorted(n for n, svc in doc["services"].items() if "grdm-convert" in svc.get("networks", []))
        self.assertEqual(on_convert, ["mfr", "unoconv"])
        credential = doc["services"]["unoconv"]["environment"]["CONVERT_SECRET"]
        self.assertTrue(credential)
        self.assertEqual(doc["services"]["mfr"]["environment"]["UNOCONV_CONVERT_SECRET"], credential)

    def test_sharejs_trusts_only_the_public_mongo_certificate(self):
        doc = self.render_core_doc()
        sharejs, mongo = doc["services"]["sharejs"], doc["services"]["mongo"]
        self.assertEqual(sharejs["environment"]["MONGO_TLS_CA_FILE"], "/mongo-tls/mongodb.crt")
        self.assertIn("mongo_tls:/mongo-tls:ro", sharejs["volumes"])
        self.assertIn("mongo_tls:/mongo-tls", mongo["volumes"])
        # the private key lives in mongo_data, which sharejs does not mount
        self.assertNotIn("/mongo-tls/mongodb.pem", " ".join(mongo["command"]))
        self.assertFalse([v for v in sharejs["volumes"] if v.startswith("mongo_data")])

    def test_tmpfs_mounts_carry_mode_1777(self):
        root = make_root()
        try:
            rc, _, err, _ = render(root)
            self.assertEqual(rc, exit_codes.OK, err)
            compose_doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
            self.assertIn("/tmp:mode=1777", compose_doc["services"]["web"]["tmpfs"])
            self.assertIn("/code/website/static/built:mode=1777", compose_doc["services"]["web"]["tmpfs"])
            for svc in compose_doc["services"].values():
                for entry in svc.get("tmpfs", []):
                    self.assertIn(":mode=", entry, entry)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    # ---- native Elasticsearch image (ADR-07)

    def test_elasticsearch_uses_the_native_image_under_the_hardening_default(self):
        root = make_root()
        try:
            rc, _, err, _ = render(root)
            self.assertEqual(rc, exit_codes.OK, err)
            doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
            es = doc["services"]["elasticsearch"]
            self.assertEqual(es["image"], "grdm-dev/elasticsearch2:2.4.6-1")
            self.assertEqual(es["user"], "1000:1000"); self.assertTrue(es["read_only"])
            self.assertNotIn("cap_add", es); self.assertNotIn("platform", es.get("platform", "linux/amd64") == "linux/amd64" and "x" or "", "")
            self.assertEqual(es.get("platform"), "linux/arm64")  # native: the host platform, no amd64 pin
            self.assertIn("/usr/share/elasticsearch/logs:mode=1777", es["tmpfs"])
            init = doc["services"]["volume_owner_init"]  # owner step on the same native image, explicit root + CHOWN only (R1-01)
            self.assertEqual((init["image"], init["user"], init["cap_add"], init["restart"]), (doc["services"]["postgres"]["image"], "0:0", ["CHOWN"], "no"))
            self.assertEqual(es["depends_on"], {"volume_owner_init": {"condition": "service_completed_successfully"}, "volume_access_check_1000": {"condition": "service_completed_successfully"}})
            self.assertEqual(es["labels"]["org.gakunin-rdm.hardening-exception"], "none")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    # ---- invoke-based services keep stdin open (real install run 9)

    def test_invoke_services_keep_stdin_open(self):
        root = make_root()
        try:
            rc, _, err, _ = render(root)
            self.assertEqual(rc, exit_codes.OK, err)
            compose = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
            for name in ("web", "api", "admin", "worker"):
                self.assertIs(compose["services"][name].get("stdin_open"), True, name)
            for name in ("wb", "mfr", "postgres", "wiki_assets"):
                self.assertNotIn("stdin_open", compose["services"][name], name)
        finally:
            shutil.rmtree(root, ignore_errors=True)

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
        command = " ".join(svc["command"])
        self.assertLess(command.index("ember build"), command.index('node -e "$$1"'))  # /code is read-only: dist, after the build
        self.assertLess(command.index('node -e "$$1"'), command.index("ember serve"))   # and before every serve (test_ember_ga_guard)
        self.assertNotIn("config/environment.js", command)
        self.assertIn("GoogleAnalytics is still in the built page", command)
        self.assertEqual(svc["platform"], ember["build_platform"])
        self.assertEqual(svc["platform"], "linux/amd64")
        self.assertEqual(svc["cap_drop"], ["ALL"])  # hardening applies to a prebuilt service like any other
        rows = {r["service"]: r for r in json.loads(out)["services"]}
        self.assertEqual(rows["ember_osf_web"]["origin"], "prebuilt")
        self.assertEqual(rows["ember_osf_web"]["image"], ember["prebuilt_image"])
        self.assertEqual(rows["web"]["origin"], "built")
        self.assertEqual(rows["wiki_assets"]["origin"], "overlay")  # the wiki-frontend bundle builder (ADR-06)
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
        self.assertEqual(set(doc["services"]), {"osf_init", "volume_owner_init", "volume_access_check_1000", "web", "api", "postgres", "elasticsearch", "rabbitmq", "fakecas"})
        self.assertEqual(doc["services"]["web"]["depends_on"], {
            "postgres": {"condition": "service_started"}, "rabbitmq": {"condition": "service_started"},
            "elasticsearch": {"condition": "service_started"}, "osf_init": {"condition": "service_completed_successfully"},
            "volume_owner_init": {"condition": "service_completed_successfully"}, "volume_access_check_1000": {"condition": "service_completed_successfully"}})
        rc, _, _, _ = render(root, profile="full", auth="shibboleth")
        self.assertEqual(rc, 0)
        doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        self.assertIn("shibboleth_sp", doc["services"])
        self.assertNotIn("fakecas", doc["services"])
        self.assertEqual(len(doc["services"]), 28)  # full profile with shibboleth: core 24 - fakecas + rdmcp aipf_mcp_data_grdm oasys shibboleth_sp test_idp

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
        self.assertIn("/var/simplesamlphp/log:mode=1777", doc["services"]["test_idp"]["tmpfs"])
        self.assertIn("/var/simplesamlphp/data:mode=1777", doc["services"]["test_idp"]["tmpfs"])
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
            self.assertEqual("user" not in svc or svc.get("user") == "0:0", "user" in relaxed, name)
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

    def test_build_report_tag_that_matches_the_pin_is_used_without_warning(self):
        root = make_root()
        pins = {c["id"]: c["integration_sha"][:12] for c in json.loads((REPO_ROOT / "manifest" / "upstreams.json").read_text(encoding="utf-8"))["components"]
                if c.get("integration_sha")}
        reports = root / "runtime" / "reports"
        reports.mkdir(parents=True)
        (reports / "build_latest.json").write_text(json.dumps({"components": [
            {"component": "osf.io", "sha12": pins["osf.io"], "status": "built"},
            {"component": "waterbutler", "sha12": "000000000000", "status": "build-failed"},
        ]}), encoding="utf-8")
        rc, out, err, _ = render(root)
        self.assertEqual(rc, 0, err)
        doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        self.assertEqual(doc["services"]["web"]["image"], f"grdm-dev/osf.io:{pins['osf.io']}")
        self.assertTrue(doc["services"]["wb"]["image"].startswith("grdm-dev/waterbutler:"))
        self.assertNotEqual(doc["services"]["wb"]["image"], "grdm-dev/waterbutler:000000000000")  # a failed build is no record
        self.assertEqual(json.loads(out)["stale_build_tags"], [])
        self.assertNotIn("WARNING", err)

    def test_build_older_than_the_pin_renders_the_pin_and_warns_with_the_fix(self):
        """2026-11-10: the osf.io pin moved and `compose render` ran before `build`; the old image ran silently.
        A recorded build that differs from the pin is stale: the pinned tag is rendered, the report lists it and
        stderr names the fix (`grdm-dev build`, then `up`)."""
        root = make_root()
        comps = {c["id"]: c for c in json.loads((REPO_ROOT / "manifest" / "upstreams.json").read_text(encoding="utf-8"))["components"]}
        osf12, wiki12 = comps["osf.io"]["integration_sha"][:12], comps["wiki-frontend"]["integration_sha"][:12]
        reports = root / "runtime" / "reports"
        reports.mkdir(parents=True)
        (reports / "build_latest.json").write_text(json.dumps({"components": [
            {"component": "osf.io", "sha12": "feedfacecafe", "image_tag": "feedfacecafe", "status": "built"},
            {"component": "wiki-frontend", "sha12": wiki12, "image_tag": f"feedfacecafe-{wiki12}", "status": "built",
             "overlay_of": "osf.io", "base_sha12": "feedfacecafe"},
        ]}), encoding="utf-8")
        rc, out, err, _ = render(root)
        self.assertEqual(rc, 0, err)  # a warning, not a stop: `install` renders before it builds
        doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        for name in ("web", "api", "admin", "worker"):
            self.assertEqual(doc["services"][name]["image"], f"grdm-dev/osf.io:{osf12}", name)
        self.assertEqual(doc["services"]["wiki_assets"]["image"], f"grdm-dev/wiki-frontend:{osf12}-{wiki12}")
        self.assertFalse(any("feedfacecafe" in str(s.get("image")) for s in doc["services"].values()))
        stale = {r["component"]: r for r in json.loads(out)["stale_build_tags"]}
        self.assertEqual(stale["osf.io"], {"component": "osf.io", "pinned": osf12, "recorded": "feedfacecafe",
                                           "image": f"grdm-dev/osf.io:{osf12}"})
        self.assertEqual(stale["wiki-frontend"]["pinned"], f"{osf12}-{wiki12}")  # the base half moved
        self.assertEqual(stale["wiki-frontend"]["recorded"], f"feedfacecafe-{wiki12}")
        self.assertIn("WARNING: the last build does not match the manifest pin", err)
        self.assertIn(f"osf.io: manifest pins {osf12}, last build recorded feedfacecafe", err)
        self.assertIn("run `grdm-dev build` now, then `grdm-dev up`", err)

    def test_stale_split_keeps_the_record_for_an_unpinned_component_and_ignores_unrendered_ones(self):
        root = make_root()
        path = root / "manifest" / "upstreams.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for comp in data["components"]:
            if comp["id"] == "waterbutler":  # no pin at all: only the build record names the commit that was built
                comp.pop("integration_sha", None)
                for up in comp.get("upstreams", []):
                    up["status"] = "open"
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        from grdm_dev import manifest as _manifest
        man = _manifest.load(path)
        self.assertIsNone(man.component("waterbutler").sha12)
        usable, stale = compose.split_stale_build_tags(man, {"waterbutler": "abcdefabcdef", "no-such-component": "123456789012"})
        self.assertEqual(usable, {"waterbutler": "abcdefabcdef"})
        self.assertEqual(stale, [])
        osf12 = man.component("osf.io").sha12
        usable, stale = compose.split_stale_build_tags(man, {"osf.io": osf12})
        self.assertEqual((usable, stale), ({"osf.io": osf12}, []))
        usable, stale = compose.split_stale_build_tags(man, {"osf.io": "feedfacecafe"})
        self.assertEqual(usable, {})
        self.assertEqual([r["component"] for r in stale], ["osf.io"])

    def test_overlay_one_shot_copies_the_bundle_into_a_volume_that_osf_services_mount_read_only(self):
        """SPEC-01 §3 overlay_of (ADR-06): wiki_assets runs grdm-dev/wiki-frontend:<osf12>-<wiki12> once, fills `wiki_static`,
        and web/api/admin/worker mount it read-only at the bundle's output subpath and wait for it to complete."""
        root = make_root()
        data = json.loads((REPO_ROOT / "manifest" / "upstreams.json").read_text(encoding="utf-8"))
        comps = {c["id"]: c for c in data["components"]}
        osf12, wiki12 = comps["osf.io"]["integration_sha"][:12], comps["wiki-frontend"]["integration_sha"][:12]
        rc, out, err, _ = render(root)
        self.assertEqual(rc, 0, err)
        doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        self.assertNotIn("wiki", doc["services"])
        wa = doc["services"]["wiki_assets"]
        self.assertEqual(wa["image"], f"grdm-dev/wiki-frontend:{osf12}-{wiki12}")
        self.assertEqual(wa["restart"], "no")  # one-shot: runs to completion
        self.assertEqual(wa["command"][:2], ["sh", "-c"])
        self.assertIn("cp -R", wa["command"][2])  # no ownership preservation (cp -a as uid 1000 would fail on root-owned metadata)
        self.assertNotIn("cp -a", wa["command"][2])
        self.assertIn("/code/website/static/public/js", wa["command"][2])  # webpack output.path of the wiki-frontend config
        self.assertIn("webpack-assets.json", wa["command"][2])
        self.assertIn("wiki-edit-page.js", wa["command"][2])  # unhashed alias next to wiki-edit-page.<chunkhash>.js
        self.assertIn("exit 1", wa["command"][2])  # a missing bundle is a failure, not an empty success
        self.assertNotIn("-delete", wa["command"][2])  # copy first, prune after: never an empty directory for running consumers
        # R1-01: the shell variables reach the container shell; Compose must not interpolate them
        self.assertIn("$$src", wa["command"][2])
        self.assertIn("$$dst", wa["command"][2])
        self.assertNotRegex(wa["command"][2], r"(?<!\$)\$(?!\$)")  # every `$` is doubled
        self.assertEqual(wa["depends_on"], {"volume_owner_init": {"condition": "service_completed_successfully"}, "volume_access_check_1000": {"condition": "service_completed_successfully"}})
        self.assertEqual(wa["volumes"], ["wiki_static:/wiki_static"])
        # R1-02: a fresh bind volume is host-owned; the owner step chowns it with CAP_CHOWN only, then exits
        init = doc["services"]["volume_owner_init"]
        self.assertIn("wiki_static:/volumes/wiki_static", init["volumes"])
        self.assertIn("fix 1000:1000 /volumes/wiki_static", init["command"][2])
        # R2-01/R3: the container never chmods (CAP_CHOWN only cannot chmod a dir owned by another uid);
        # the host-side volume directory mode is set by compose render instead.
        self.assertNotIn("chmod", init["command"][2])
        vol_dir = root / "runtime" / "volumes" / "wiki_static"
        if vol_dir.exists():
            self.assertEqual(oct(vol_dir.stat().st_mode & 0o777), "0o755")
        self.assertEqual(wa["user"], "1000:1000")  # baseline controls apply to the one-shot like any service
        self.assertEqual(wa["cap_drop"], ["ALL"])
        self.assertIs(wa["read_only"], True)
        self.assertIn("no-new-privileges:true", wa["security_opt"])
        self.assertNotIn("ports", wa)
        self.assertEqual(wa["networks"], ["grdm"])
        self.assertEqual(wa["labels"]["org.gakunin-rdm.component"], "wiki-frontend")
        for name in ("web", "api", "admin", "worker"):
            svc = doc["services"][name]
            self.assertEqual(svc["image"], f"grdm-dev/osf.io:{osf12}", name)  # the base keeps its own image
            self.assertIn("wiki_static:/code/website/static/public/js/wiki:ro", svc["volumes"], name)
            self.assertIsInstance(svc["depends_on"], dict, name)  # Compose long form because of the condition
            self.assertEqual(svc["depends_on"]["wiki_assets"], {"condition": "service_completed_successfully"}, name)
            self.assertEqual(svc["depends_on"]["postgres"], {"condition": "service_started"}, name)
        self.assertIn("wiki_static", doc["volumes"])
        self.assertTrue((root / "runtime" / "volumes" / "wiki_static").is_dir())
        rows = {r["service"]: r for r in json.loads(out)["services"]}
        self.assertEqual(rows["wiki_assets"]["origin"], "overlay")
        self.assertEqual(rows["web"]["origin"], "built")
        # the build report's image_tag (what `grdm-dev build` actually tagged) is used when it matches the pin;
        # a record that differs from the pin is stale (test_build_older_than_the_pin_renders_the_pin_and_warns_with_the_fix)
        reports = root / "runtime" / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        (reports / "build_latest.json").write_text(json.dumps({"components": [
            {"component": "osf.io", "sha12": osf12, "image_tag": osf12, "status": "built"},
            {"component": "wiki-frontend", "sha12": wiki12, "image_tag": f"{osf12}-{wiki12}", "status": "built",
             "overlay_of": "osf.io", "base_sha12": osf12},
        ]}), encoding="utf-8")
        rc, out, _, _ = render(root)
        self.assertEqual(rc, 0)
        doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        self.assertEqual(doc["services"]["wiki_assets"]["image"], f"grdm-dev/wiki-frontend:{osf12}-{wiki12}")
        self.assertEqual(doc["services"]["web"]["image"], f"grdm-dev/osf.io:{osf12}")
        self.assertEqual(json.loads(out)["stale_build_tags"], [])

    def test_rendered_file_survives_compose_interpolation_with_the_full_env(self):
        """PR #30 review r1 R1-01: Compose interpolates `$VAR`/`${VAR}` in every string before the container shell runs.
        A minimal re-implementation of that pass over the rendered JSON (with every key `secrets init` writes) must
        resolve every reference and leave the one-shot's shell variables intact."""
        from grdm_dev import secrets as _secrets
        env = {k: fake_value(k) for k in _secrets.SECRET_KEYS}
        root = make_root("".join(f"{k}={v}\n" for k, v in env.items()))
        rc, _, err, _ = render(root)
        self.assertEqual(rc, 0, err)
        doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        unresolved: list[str] = []

        def interpolate(text: str, where: str) -> str:
            # `$$` -> `$`; `${NAME}`, `${NAME:-default}` (default may nest), `$NAME`; anything else is an error
            out, i = [], 0
            while i < len(text):
                c = text[i]
                if c != "$":
                    out.append(c); i += 1; continue
                if text.startswith("$$", i):
                    out.append("$"); i += 2; continue
                if text.startswith("${", i):
                    depth, j = 0, i
                    while j < len(text):
                        if text[j] == "{": depth += 1
                        elif text[j] == "}":
                            depth -= 1
                            if depth == 0: break
                        j += 1
                    body = text[i + 2:j]
                    name, sep, default = re.match(r"([A-Za-z_][A-Za-z0-9_]*)(:?[-?+])?(.*)", body, re.S).groups()
                    if name in env and env[name]:
                        out.append(env[name])
                    elif sep in (":-", "-"):
                        out.append(interpolate(default, where))
                    else:
                        unresolved.append(f"{where}: ${{{name}}}")
                    i = j + 1; continue
                m = re.match(r"\$([A-Za-z_][A-Za-z0-9_]*)", text[i:])
                if m:
                    name = m.group(1)
                    if name in env: out.append(env[name])
                    else: unresolved.append(f"{where}: ${name}")
                    i += m.end(); continue
                unresolved.append(f"{where}: bare $"); out.append(c); i += 1
            return "".join(out)

        def walk(node, where):
            if isinstance(node, str):
                return interpolate(node, where)
            if isinstance(node, list):
                return [walk(v, f"{where}[{i}]") for i, v in enumerate(node)]
            if isinstance(node, dict):
                return {k: walk(v, f"{where}.{k}") for k, v in node.items()}
            return node

        resolved = walk(doc, "$")
        self.assertEqual(unresolved, [])  # review r1 reproduced `ls "" >/dev/null; find "" ...` from $src/$dst/$f
        cmd = resolved["services"]["wiki_assets"]["command"][2]
        self.assertIn("src=/code/website/static/public/js", cmd)
        self.assertIn('cp -R "$src"/. "$dst"/', cmd)
        self.assertIn('"$dst"/wiki-edit-page.js', cmd)
        self.assertNotIn('""', cmd)
        self.assertEqual(resolved["services"]["web"]["environment"]["SECRET_KEY"], env["DJANGO_SECRET_KEY"])
        self.assertEqual(resolved["services"]["wb"]["environment"]["SERVER_CONFIG_HMAC_SECRET"], env["WATERBUTLER_HMAC_SECRET"])
        # OSF has one verifier (DEFAULT_HMAC_SECRET): every waterbutler signer and every service loading local.py must share one key.
        for service in ("wb", "wb_worker"):
            for key in ("SERVER_CONFIG_HMAC_SECRET", "OSFSTORAGE_PROVIDER_CONFIG_HMAC_SECRET"):
                self.assertEqual(resolved["services"][service]["environment"][key], env["WATERBUTLER_HMAC_SECRET"], f"{service}.{key}")
        # DEBUG=False runserver serves no static files without --insecure (loopback development only); admin pages need them.
        self.assertIn("--insecure", resolved["services"]["admin"]["command"])
        # osf.io mints wiki tokens from Y_WEBSOCKET_SECRET; y-websocket verifies them with JWT_SECRET.
        self.assertEqual(resolved["services"]["web"]["environment"]["Y_WEBSOCKET_SECRET"], resolved["services"]["y_websocket"]["environment"]["JWT_SECRET"])
        for service in ("web", "api", "admin", "worker", "osf_init"):
            self.assertEqual(resolved["services"][service]["environment"]["WATERBUTLER_HMAC_SECRET"], env["WATERBUTLER_HMAC_SECRET"], service)

    @unittest.skipUnless(shutil.which("docker"), "docker CLI not installed")
    def test_docker_compose_config_accepts_the_rendered_file(self):
        """Read-only: `docker compose config` parses and interpolates the rendered file without touching the daemon's state."""
        import subprocess
        from grdm_dev import secrets as _secrets
        root = make_root("".join(f"{k}={fake_value(k)}\n" for k in _secrets.SECRET_KEYS))  # every key secrets init writes
        rc, _, err, _ = render(root)
        self.assertEqual(rc, 0, err)
        try:
            proc = subprocess.run(["docker", "compose", "-f", str(root / "runtime" / "docker-compose.yml"), "--project-directory",
                                   str(root / "runtime"), "config", "--format", "json"],
                                  capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as exc:  # pragma: no cover - environment dependent
            self.skipTest(f"docker compose config unavailable: {exc}")
        if proc.returncode != 0 and "compose" in proc.stderr and "is not a docker command" in proc.stderr:  # pragma: no cover
            self.skipTest("docker compose plugin missing")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("variable is not set", proc.stderr)  # the warning review r1 reproduced for $src/$dst/$f
        parsed = json.loads(proc.stdout)
        cmd = parsed["services"]["wiki_assets"]["command"]
        self.assertIn('cp -R "$$src"/. "$$dst"/', cmd[2])  # `config` prints a round-trippable file, so `$$` stays escaped
        self.assertNotIn('""', cmd[2])  # review r1 saw `ls "" >/dev/null; find "" ...` here
        self.assertEqual(parsed["services"]["web"]["depends_on"]["wiki_assets"]["condition"], "service_completed_successfully")
        self.assertEqual(parsed["services"]["volume_owner_init"]["cap_add"], ["CHOWN"])

    def test_minimum_profile_keeps_the_short_depends_on_form_without_wiki_assets(self):
        root = make_root()
        rc, _, err, _ = render(root, profile="minimum")
        self.assertEqual(rc, 0, err)
        doc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        self.assertNotIn("wiki_assets", doc["services"])
        # wiki_assets is dropped (not in the profile); osf_init stays, so the long form remains with the
        # plain dependencies rendered as service_started (real install run 12: osf_init added)
        self.assertEqual(doc["services"]["web"]["depends_on"], {
            "postgres": {"condition": "service_started"}, "rabbitmq": {"condition": "service_started"},
            "elasticsearch": {"condition": "service_started"}, "osf_init": {"condition": "service_completed_successfully"},
            "volume_owner_init": {"condition": "service_completed_successfully"}, "volume_access_check_1000": {"condition": "service_completed_successfully"}})

    def test_escape_compose_dollar(self):
        self.assertEqual(compose.escape_compose_dollar('ls "$src"; echo ${X} $$'), 'ls "$$src"; echo $${X} $$$$')
        self.assertEqual(compose.escape_compose_dollar("plain"), "plain")

    def test_render_depends_on_forms(self):
        self.assertEqual(compose.render_depends_on(["a", "b"], {"a", "b"}), ["a", "b"])
        self.assertEqual(compose.render_depends_on(["a", {"service": "c", "condition": "service_completed_successfully"}], {"a"}), ["a"])
        self.assertEqual(compose.render_depends_on(["a", {"service": "c", "condition": "service_completed_successfully"}], {"a", "c"}),
                         {"a": {"condition": "service_started"}, "c": {"condition": "service_completed_successfully"}})
        self.assertEqual(compose.render_depends_on([], {"a"}), [])

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
        self.assertIn("ports[9]", out)

    def test_non_render_action_is_usage_error(self):
        ctx = Context(root=make_root(), yes=True)
        with redirect_stderr(io.StringIO()):
            rc = compose.run(ctx, argparse.Namespace(compose_command=None))
        self.assertEqual(rc, exit_codes.USAGE)


class CasNativeImageTests(unittest.TestCase):
    """ADR-07: the CAS built from the integration repository, its generated settings and its secrets."""

    @classmethod
    def setUpClass(cls):
        cls.root = make_root()
        rc, _, err, _ = render(cls.root)
        assert rc == 0, err
        cls.doc = json.loads((cls.root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))
        cls.cas = cls.doc["services"]["cas"]
        cls.config = cls.root / "runtime" / "config"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)

    def properties(self) -> dict[str, str]:
        text = (self.config / "cas" / "cas.properties").read_text(encoding="utf-8")
        return dict(line.split("=", 1) for line in text.splitlines() if line and not line.startswith("#"))

    def test_runs_the_built_image_natively(self):
        self.assertEqual(self.cas["image"], "grdm-dev/cas-overlay:22610b7681a2")
        self.assertEqual(self.cas["platform"], "linux/arm64")  # the render argument: no amd64 pin

    def test_hardening_default_with_no_recorded_exception(self):
        self.assertEqual(self.cas["user"], "1000:1000")
        self.assertIs(self.cas["read_only"], True)
        self.assertEqual(self.cas["cap_drop"], ["ALL"])
        self.assertNotIn("cap_add", self.cas)
        self.assertEqual(self.cas["security_opt"], ["no-new-privileges:true"])
        self.assertEqual(self.cas["tmpfs"], ["/tmp:mode=1777"])
        self.assertEqual(self.cas["labels"]["org.gakunin-rdm.hardening-exception"], "none")
        self.assertNotIn("cas", load_hardening())

    def test_starts_only_after_the_migrations_finish(self):
        self.assertEqual(self.cas["depends_on"]["osf_init"], {"condition": "service_completed_successfully"})

    def test_environment_is_exactly_what_the_image_reads(self):
        self.assertEqual(self.cas["environment"], {
            "DATABASE_PASSWORD": "${POSTGRES_PASSWORD}",
            "OSF_DATABASE_PASSWORD": "${POSTGRES_PASSWORD}",
            "TGC_ENCRYPTION_KEY": "${TGC_ENCRYPTION_KEY}",
            "TGC_SIGNING_KEY": "${TGC_SIGNING_KEY}",
            "OSF_API_INSTITUTIONS_AUTH_JWESECRET": "${OSF_API_INSTITUTIONS_AUTH_JWESECRET}",
            "OSF_API_INSTITUTIONS_AUTH_JWTSECRET": "${OSF_API_INSTITUTIONS_AUTH_JWTSECRET}",
        })

    def test_mounts_properties_and_services_read_only(self):
        self.assertEqual(self.cas["volumes"], ["./config/cas/cas.properties:/etc/cas/cas.properties:ro",
                                               "./config/cas/services:/etc/cas/services:ro"])

    def test_properties_point_at_the_migrated_database_over_plain_http(self):
        props = self.properties()
        self.assertEqual(props["osf.database.url"], "jdbc:postgresql://postgres:5432/osf")
        self.assertEqual(props["database.url"], "jdbc:postgresql://postgres:5432/cas")
        self.assertEqual(props["tgc.cookie.secure"], "false")
        self.assertEqual(props["jsession.cookie.secure"], "false")
        self.assertEqual(props["service.registry.config.location"], "file:/etc/cas/services")
        self.assertEqual(props["osf.url"], "http://127.0.0.1:5000/")
        for name in ("callutheran", "cord", "okstate"):
            for key in ("cas.protocol", "client.name", "login.url", "prefix.url"):
                self.assertIn(f"cas.{name}.{key}", props)

    def test_no_secret_is_written_to_the_properties(self):
        props = self.properties()
        for key in ("database.password", "osf.database.password", "tgc.encryption.key", "tgc.signing.key",
                    "osf.api.institutions.auth.jweSecret", "osf.api.institutions.auth.jwtSecret"):
            self.assertNotIn(key, props)

    def test_service_definition_allows_only_the_real_web_url(self):
        service = json.loads((self.config / "cas" / "services" / "grdm-web.json").read_text(encoding="utf-8"))
        self.assertEqual(service["@class"], "org.jasig.cas.services.RegexRegisteredService")
        pattern = re.compile(service["serviceId"])
        self.assertTrue(pattern.match("http://127.0.0.1:5000/login?next=/dashboard/"))
        for url in ("http://evil.example.invalid/", "http://127.0.0.1:50001/", "http://127.0.0.1:5000.evil.invalid/", "https://127.0.0.1:5000/"):
            self.assertIsNone(pattern.match(url), url)

    def test_service_definition_follows_a_remapped_web_port(self):
        root = make_root()
        try:
            rc, _, err, _ = render(root, checker=lambda port: port != 5000)
            self.assertEqual(rc, 0, err)
            service = json.loads((root / "runtime" / "config" / "cas" / "services" / "grdm-web.json").read_text(encoding="utf-8"))
            self.assertIn(":5001/", service["serviceId"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_osf_services_share_the_institution_keys_with_cas(self):
        local = (self.config / "osf" / "api_local.py").read_text(encoding="utf-8")
        self.assertIn("JWE_SECRET = environ['OSF_API_INSTITUTIONS_AUTH_JWESECRET'].encode('utf-8')", local)
        self.assertIn("JWT_SECRET = environ['OSF_API_INSTITUTIONS_AUTH_JWTSECRET'].encode('utf-8')", local)
        for name, svc in self.doc["services"].items():
            if any("osf/api_local.py" in mount for mount in svc.get("volumes", [])):
                self.assertEqual(svc["environment"]["OSF_API_INSTITUTIONS_AUTH_JWESECRET"], "${OSF_API_INSTITUTIONS_AUTH_JWESECRET}", name)
                self.assertEqual(svc["environment"]["OSF_API_INSTITUTIONS_AUTH_JWTSECRET"], "${OSF_API_INSTITUTIONS_AUTH_JWTSECRET}", name)

    def test_a_wrong_key_length_stops_the_render(self):
        root = make_root(fake_secrets(TGC_SIGNING_KEY="x" * 43))
        try:
            rc, _, err, _ = render(root)
            self.assertEqual(rc, exit_codes.USAGE)
            self.assertIn("TGC_SIGNING_KEY", err)
            self.assertNotIn("x" * 43, err)
            self.assertFalse((root / "runtime" / "docker-compose.yml").exists())
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_an_unusable_key_of_the_right_length_stops_the_render_by_name_only(self):
        """PR #39 review r1 R1-01: exit 2, no Compose file, the key name and never the value."""
        bad = {
            "TGC_ENCRYPTION_KEY": ["!" * 43, "A" * 42 + "B"],
            "TGC_SIGNING_KEY": ["!" * 86, " " * 86],
            "OSF_API_INSTITUTIONS_AUTH_JWESECRET": ['"' + " " * 30 + '"', " " * 32, "osf_api_cas_login_" + "jwe_secret_32b"],
            "OSF_API_INSTITUTIONS_AUTH_JWTSECRET": ["'" + " " * 30 + "'", " " * 40, "osf_api_cas_login_" + "jwt_secret_32b"],
        }
        for key, values in bad.items():
            for value in values:
                root = make_root(fake_secrets(**{key: value}))
                try:
                    rc, out, err, _ = render(root)
                    self.assertEqual(rc, exit_codes.USAGE, (key, value))
                    self.assertIn(key, err)
                    if value.strip(" '\""):
                        self.assertNotIn(value.strip(" '\""), err + out)
                    self.assertFalse((root / "runtime" / "docker-compose.yml").exists(), key)
                finally:
                    shutil.rmtree(root, ignore_errors=True)

    def test_a_runtime_env_from_before_the_switch_stops_the_render_by_name(self):
        env = fake_secrets().replace("TGC_ENCRYPTION_KEY=", "CAS_TGC_ENCRYPTION_KEY=")
        root = make_root(env)
        try:
            rc, _, err, _ = render(root)
            self.assertEqual(rc, exit_codes.USAGE)
            self.assertIn("TGC_ENCRYPTION_KEY", err)
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()


class VolumeDirOwnershipTests(unittest.TestCase):
    """PR #30 r4: re-rendering after an init container chowned the bind directory must not fail."""

    def test_existing_volume_dir_is_left_alone_even_if_chmod_would_be_denied(self):
        import tempfile
        from unittest import mock
        from grdm_dev import compose

        with tempfile.TemporaryDirectory() as td:
            vol = pathlib.Path(td) / "wiki_static"
            vol.mkdir()
            os.chmod(vol, 0o700)  # nosemgrep: python.lang.security.audit.insecure-file-permissions.insecure-file-permissions -- test fixture simulating a mode set by another uid after chown
            with mock.patch("grdm_dev.compose.os.chmod", side_effect=PermissionError("Operation not permitted")) as chmod:
                compose._ensure_volume_dir(vol)  # existing: must not even try
                chmod.assert_not_called()
            self.assertEqual(oct(vol.stat().st_mode & 0o777), "0o700")

    def test_fresh_volume_dir_gets_0755(self):
        import tempfile
        from grdm_dev import compose

        with tempfile.TemporaryDirectory() as td:
            vol = pathlib.Path(td) / "wiki_static"
            compose._ensure_volume_dir(vol)
            self.assertTrue(vol.is_dir())
            self.assertEqual(oct(vol.stat().st_mode & 0o777), "0o755")
