import argparse
import io
import json
import os
import shutil
import stat
import tempfile
import unittest
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


def render(root: Path, profile="core", auth="fakecas", checker=lambda port: True, memory_gib=16.0, cpus=4.0, json_output=True):
    ctx = Context(root=root, yes=True, json_output=json_output, profile=profile)
    args = argparse.Namespace(compose_command="render", auth=auth, platform="linux/arm64", memory_gib=None, cpus=None)
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = compose.run(ctx, args, memory_gib=memory_gib, cpus=cpus, port_checker=checker, platform_string="linux/arm64")
    return rc, out.getvalue(), err.getvalue(), ctx


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
        self.assertEqual(set(doc["networks"]), {"grdm"})
        self.assertNotIn(FORBIDDEN, text)
        exceptions = load_hardening()
        services = doc["services"]
        self.assertEqual(set(services), {s["service"] for s in json.loads(out)["services"]})
        self.assertEqual(len(services), 20)  # core profile (SPEC-02 §4)
        for name, svc in services.items():
            relaxed = exceptions.get(name, set())
            self.assertEqual(svc["networks"], ["grdm"], name)
            self.assertEqual(svc["cap_drop"], ["ALL"], name)
            self.assertIn("no-new-privileges:true", svc["security_opt"], name)
            self.assertNotIn("privileged", svc, name)
            self.assertEqual(svc["platform"], "linux/arm64", name)
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
        self.assertIn("ports[7]", out)

    def test_non_render_action_is_usage_error(self):
        ctx = Context(root=make_root(), yes=True)
        with redirect_stderr(io.StringIO()):
            rc = compose.run(ctx, argparse.Namespace(compose_command=None))
        self.assertEqual(rc, exit_codes.USAGE)


if __name__ == "__main__":
    unittest.main()
