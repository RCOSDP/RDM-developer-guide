import argparse
import io
import stat
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from grdm_dev import exit_codes, secrets
from grdm_dev.context import Context


def make_ctx(root: Path, **kw) -> Context:
    return Context(root=root, stdin_is_tty=False, **kw)


def ns(**kw):
    return argparse.Namespace(**kw)


class SecretsInitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.out, self.err = io.StringIO(), io.StringIO()

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, ctx, args, **kw):
        with redirect_stdout(self.out), redirect_stderr(self.err):
            return secrets.run(ctx, args, **kw)

    def test_init_writes_0600_random_values_without_defaults(self):
        ctx = make_ctx(self.root, profile="minimum")
        self.assertEqual(self.run_cmd(ctx, ns(secrets_action="init", force=False)), exit_codes.OK)
        path = self.root / "runtime" / ".env"
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
        values = secrets.read_env(path)
        for key in secrets.SECRET_KEYS:
            self.assertIn(key, values)
            self.assertNotIn(values[key].lower(), secrets.FORBIDDEN_DEFAULTS)
            self.assertGreaterEqual(len(values[key]), 32)
        self.assertGreaterEqual(len(values["DJANGO_SECRET_KEY"]), 50)
        self.assertEqual(values["GRDM_PROFILE"], "minimum")
        self.assertEqual(values["GRDM_PORT_WEB"], "5000")
        self.assertEqual(values["GRDM_PORT_EMBER_OSF_WEB"], "4200")
        self.assertEqual(secrets.check_no_defaults(values), [])
        # report prints key names only, never values
        printed = self.out.getvalue()
        self.assertIn("POSTGRES_PASSWORD", printed)
        for key in secrets.SECRET_KEYS:
            self.assertNotIn(values[key], printed)
        # two inits produce different secrets
        self.run_cmd(ctx, ns(secrets_action="init", force=True))
        self.assertNotEqual(secrets.read_env(path)["POSTGRES_PASSWORD"], values["POSTGRES_PASSWORD"])

    def test_init_refuses_overwrite_without_force(self):
        ctx = make_ctx(self.root)
        self.assertEqual(self.run_cmd(ctx, ns(secrets_action="init", force=False)), exit_codes.OK)
        before = secrets.read_env(self.root / "runtime" / ".env")
        self.assertEqual(self.run_cmd(ctx, ns(secrets_action="init", force=False)), exit_codes.USAGE)
        self.assertIn("--force", self.err.getvalue())
        self.assertEqual(secrets.read_env(self.root / "runtime" / ".env"), before)

    def test_rotate_changes_secrets_keeps_profile_and_restarts_running(self):
        ctx = make_ctx(self.root, profile="full")
        self.run_cmd(ctx, ns(secrets_action="init", force=False))
        path = self.root / "runtime" / ".env"
        before = secrets.read_env(path)
        # simulate compose render having remapped a port: must survive rotation
        before["GRDM_PORT_WEB"] = "5001"
        secrets.write_env(path, before)
        restarted = []
        rc = self.run_cmd(
            ctx, ns(secrets_action="rotate"),
            running_services=lambda: ["web", "api"],
            restart=lambda services: restarted.append(list(services)) or 0,
        )
        self.assertEqual(rc, exit_codes.OK)
        after = secrets.read_env(path)
        self.assertEqual(after["GRDM_PROFILE"], "full")
        self.assertEqual(after["GRDM_PORT_WEB"], "5001")
        for key in secrets.SECRET_KEYS:
            self.assertNotEqual(after[key], before[key], key)
        self.assertEqual(restarted, [["web", "api"]])
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_rotate_without_env_is_usage_error(self):
        ctx = make_ctx(self.root)
        rc = self.run_cmd(ctx, ns(secrets_action="rotate"), running_services=lambda: [], restart=lambda s: 0)
        self.assertEqual(rc, exit_codes.USAGE)

    def test_rotate_restart_failure_is_40(self):
        ctx = make_ctx(self.root)
        self.run_cmd(ctx, ns(secrets_action="init", force=False))
        rc = self.run_cmd(ctx, ns(secrets_action="rotate"), running_services=lambda: ["web"], restart=lambda s: 1)
        self.assertEqual(rc, exit_codes.HEALTH_FAILED)

    def test_every_key_referenced_by_a_template_is_generated(self):
        import re
        tpl_dir = Path(secrets.__file__).parent / "templates"
        if not tpl_dir.exists():
            self.skipTest("templates/ not present")
        referenced = set()
        for f in tpl_dir.glob("*.json"):
            referenced.update(re.findall(r"\$\{?([A-Z][A-Z0-9_]*)", f.read_text(encoding="utf-8")))
        generated = set(secrets.SECRET_KEYS) | set(secrets.default_non_secrets("core"))
        self.assertEqual(sorted(referenced - generated), [])

    def test_no_action_is_usage_error(self):
        self.assertEqual(self.run_cmd(make_ctx(self.root), ns(secrets_action=None)), exit_codes.USAGE)


if __name__ == "__main__":
    unittest.main()
