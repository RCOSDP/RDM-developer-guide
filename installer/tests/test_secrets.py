import argparse
import base64
import io
import json
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


class FakeDocker:
    """Fake `runner(argv, input=None)`: a postgres and a rabbitmq credential store behind `docker compose exec`."""

    def __init__(self, old_pg, old_rmq, running=("web", "postgres", "rabbitmq"), ps_rc=0,
                 fail_rmq_set=False, pg_accepts_everything=False, unhealthy_after_recreate=False):
        self.calls, self.inputs = [], []
        self.pg_password, self.rmq_password = old_pg, old_rmq
        self.running, self.ps_rc = list(running), ps_rc
        self.fail_rmq_set, self.pg_accepts_everything = fail_rmq_set, pg_accepts_everything
        self.unhealthy_after_recreate = unhealthy_after_recreate
        self.pg_auth_used, self.pg_checks_rejected, self.rmq_checks_rejected = [], [], []
        self.recreated = 0

    def sequence(self):
        out = []
        for argv in self.calls:
            if argv[:2] != ["docker", "compose"]:
                out.append(argv[0])
                continue
            sub = argv[6:]
            if sub[0] == "ps":
                out.append("ps --all" if "--all" in sub else "ps")
            elif sub[0] == "exec":
                kind = "set" if "change_password" in sub[5] or "ALTER USER" in sub[5] else "check"
                out.append(f"exec:{sub[2]}:{kind}")
            elif sub[0] == "up":
                out.append("up --force-recreate" if "--force-recreate" in sub else "up")
            else:
                out.append(sub[0])
        return out

    def __call__(self, argv, input=None):
        self.calls.append(list(argv))
        self.inputs.append(input)
        sub = argv[6:] if argv[:2] == ["docker", "compose"] else argv
        if sub[0] == "ps":
            if self.ps_rc:
                return self.ps_rc, ""
            healthy = not (self.unhealthy_after_recreate and self.recreated)
            return 0, json.dumps([{"Service": s, "State": "running", "Health": "healthy" if healthy else "unhealthy"} for s in self.running])
        if sub[0] == "up":
            self.recreated += 1
            return 0, ""
        if sub[0] == "exec":
            assert sub[1] == "-T" and sub[3:5] == ["sh", "-c"] and sub[6] == "sh", sub
            service, script, user = sub[2], sub[5], sub[7]
            lines = (input or "").splitlines()
            if service == "postgres":
                assert user == "postgres"
                if "ALTER USER" in script:
                    old, new = lines
                    self.pg_auth_used.append(old)
                    if old != self.pg_password:
                        return 2, ""  # psql: password authentication failed
                    self.pg_password = new
                    return 0, ""
                (pw,) = lines
                ok = self.pg_accepts_everything or pw == self.pg_password
                if not ok:
                    self.pg_checks_rejected.append(pw)
                return 0 if ok else 2, ""
            if service == "rabbitmq":
                assert user == "grdm"
                (pw,) = lines
                if "change_password" in script:
                    if self.fail_rmq_set:
                        return 69, ""
                    self.rmq_password = pw
                    return 0, ""
                ok = pw == self.rmq_password
                if not ok:
                    self.rmq_checks_rejected.append(pw)
                return 0 if ok else 70, ""
        return 1, ""


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

    # ----------------------------------------------------------------- rotate (review PR #21 finding 1)

    def _rendered(self, services=("web", "postgres", "rabbitmq")):
        """A rendered compose file so rotate treats the install as live."""
        compose = {"services": {s: ({"ports": ["127.0.0.1:5000:5000"]} if s == "web" else {}) for s in services}}
        (self.root / "runtime").mkdir(exist_ok=True)
        (self.root / "runtime" / "docker-compose.yml").write_text(json.dumps(compose))

    def _rotate(self, ctx, runner):
        return self.run_cmd(ctx, ns(secrets_action="rotate", timeout=0.0), runner=runner,
                            prober=lambda url: (True, "HTTP 200"), sleep=lambda s: None)

    def test_init_force_and_rotate_drop_obsolete_credentials_of_a_legacy_env(self):
        """PR #35 review r1 P3: a retired credential must not survive as a "non-secret" setting."""
        path = self.root / "runtime" / ".env"
        for action in ("init", "rotate"):
            ctx = make_ctx(self.root, profile="full")
            self.run_cmd(ctx, ns(secrets_action="init", force=True))
            legacy = secrets.read_env(path)
            legacy["OSFSTORAGE_HMAC_SECRET"] = "legacy-osfstorage-hmac-value-0123456789"
            legacy["GRDM_PORT_WEB"] = "5001"
            secrets.write_env(path, legacy)
            if action == "init":
                rc = self.run_cmd(ctx, ns(secrets_action="init", force=True))
            else:
                rc = self.run_cmd(ctx, ns(secrets_action="rotate", timeout=0.0), runner=FakeDocker(old_pg="x", old_rmq="y", running=()),
                                  running_services=lambda: [])
            self.assertEqual(rc, exit_codes.OK, self.err.getvalue())
            after = secrets.read_env(path)
            self.assertNotIn("OSFSTORAGE_HMAC_SECRET", after, action)
            self.assertNotIn("legacy-osfstorage-hmac-value", path.read_text(encoding="utf-8"), action)
            self.assertEqual(after["GRDM_PORT_WEB"], "5001", action)
            self.assertNotIn("OSFSTORAGE_HMAC_SECRET", self.out.getvalue(), action)

    def test_rotate_changes_live_passwords_rejects_old_and_recreates(self):
        ctx = make_ctx(self.root, profile="full")
        self.run_cmd(ctx, ns(secrets_action="init", force=False))
        path = self.root / "runtime" / ".env"
        before = secrets.read_env(path)
        before["GRDM_PORT_WEB"] = "5001"  # a remapped port must survive rotation
        secrets.write_env(path, before)
        self._rendered()
        runner = FakeDocker(old_pg=before["POSTGRES_PASSWORD"], old_rmq=before["RABBITMQ_DEFAULT_PASS"])
        rc = self._rotate(ctx, runner)
        self.assertEqual(rc, exit_codes.OK, self.err.getvalue())
        after = secrets.read_env(path)
        self.assertEqual(after["GRDM_PROFILE"], "full")
        self.assertEqual(after["GRDM_PORT_WEB"], "5001")
        for key in secrets.SECRET_KEYS:
            self.assertNotEqual(after[key], before[key], key)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertFalse((self.root / "runtime" / secrets.BACKUP_NAME).exists())  # old secrets do not linger
        # argv sequence: ps, ALTER with old password, old rejected, new accepted, rabbitmq same, force-recreate, health ps
        seq = runner.sequence()
        self.assertEqual(seq[:8], [
            "ps", "exec:postgres:set", "exec:postgres:check", "exec:postgres:check",
            "exec:rabbitmq:set", "exec:rabbitmq:check", "exec:rabbitmq:check", "up --force-recreate",
        ])
        self.assertIn("ps --all", seq[8:])  # health wait after recreation
        self.assertFalse(any("restart" in c for c in runner.calls))  # restart keeps the old environment
        # the fake store now holds the new passwords and the ALTER was authenticated with the OLD one
        self.assertEqual(runner.pg_password, after["POSTGRES_PASSWORD"])
        self.assertEqual(runner.rmq_password, after["RABBITMQ_DEFAULT_PASS"])
        self.assertEqual(runner.pg_auth_used[0], before["POSTGRES_PASSWORD"])
        # old credential was tried and rejected
        self.assertIn(before["POSTGRES_PASSWORD"], runner.pg_checks_rejected)
        self.assertIn(before["RABBITMQ_DEFAULT_PASS"], runner.rmq_checks_rejected)
        # no secret value anywhere in argv, stdout or stderr
        printed = self.out.getvalue() + self.err.getvalue()
        for key in secrets.SECRET_KEYS:
            self.assertNotIn(before[key], printed, key)
            self.assertNotIn(after[key], printed, key)
            for argv in runner.calls:
                self.assertNotIn(before[key], " ".join(argv), key)
                self.assertNotIn(after[key], " ".join(argv), key)

    def test_rotate_rolls_back_env_and_postgres_when_rabbitmq_fails(self):
        ctx = make_ctx(self.root)
        self.run_cmd(ctx, ns(secrets_action="init", force=False))
        path = self.root / "runtime" / ".env"
        before = secrets.read_env(path)
        self._rendered()
        runner = FakeDocker(old_pg=before["POSTGRES_PASSWORD"], old_rmq=before["RABBITMQ_DEFAULT_PASS"], fail_rmq_set=True)
        rc = self._rotate(ctx, runner)
        self.assertEqual(rc, exit_codes.HEALTH_FAILED)
        self.assertIn("rabbitmq-change-password", self.err.getvalue())
        self.assertIn("restored", self.err.getvalue())
        self.assertEqual(secrets.read_env(path), before)  # file restored
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(runner.pg_password, before["POSTGRES_PASSWORD"])  # postgres reverted to the old password
        self.assertNotIn("up --force-recreate", runner.sequence())  # never recreated with a half-rotated state
        for key in secrets.SECRET_KEYS:
            self.assertNotIn(before[key], self.out.getvalue() + self.err.getvalue())

    def test_rotate_fails_when_old_password_still_accepted(self):
        ctx = make_ctx(self.root)
        self.run_cmd(ctx, ns(secrets_action="init", force=False))
        path = self.root / "runtime" / ".env"
        before = secrets.read_env(path)
        self._rendered()
        runner = FakeDocker(old_pg=before["POSTGRES_PASSWORD"], old_rmq=before["RABBITMQ_DEFAULT_PASS"], pg_accepts_everything=True)
        self.assertEqual(self._rotate(ctx, runner), exit_codes.HEALTH_FAILED)
        self.assertIn("postgres-reject-old-password", self.err.getvalue())
        self.assertEqual(secrets.read_env(path), before)

    def test_rotate_rolls_back_and_recreates_when_health_fails_after_recreate(self):
        ctx = make_ctx(self.root)
        self.run_cmd(ctx, ns(secrets_action="init", force=False))
        path = self.root / "runtime" / ".env"
        before = secrets.read_env(path)
        self._rendered()
        runner = FakeDocker(old_pg=before["POSTGRES_PASSWORD"], old_rmq=before["RABBITMQ_DEFAULT_PASS"], unhealthy_after_recreate=True)
        self.assertEqual(self._rotate(ctx, runner), exit_codes.HEALTH_FAILED)
        self.assertIn("health-after-recreate", self.err.getvalue())
        self.assertEqual(secrets.read_env(path), before)
        self.assertEqual(runner.pg_password, before["POSTGRES_PASSWORD"])
        self.assertEqual(runner.rmq_password, before["RABBITMQ_DEFAULT_PASS"])
        self.assertEqual(runner.sequence().count("up --force-recreate"), 2)  # once with new env, once again after restore

    def test_rotate_without_compose_file_rotates_file_only(self):
        ctx = make_ctx(self.root)
        self.run_cmd(ctx, ns(secrets_action="init", force=False))
        before = secrets.read_env(self.root / "runtime" / ".env")
        runner = FakeDocker(old_pg="", old_rmq="")
        self.assertEqual(self._rotate(ctx, runner), exit_codes.OK)
        self.assertEqual(runner.calls, [])  # nothing is live yet: no Docker call at all
        self.assertNotEqual(secrets.read_env(self.root / "runtime" / ".env")["POSTGRES_PASSWORD"], before["POSTGRES_PASSWORD"])

    def test_rotate_refuses_when_database_has_data_but_is_not_running(self):
        ctx = make_ctx(self.root)
        self.run_cmd(ctx, ns(secrets_action="init", force=False))
        path = self.root / "runtime" / ".env"
        before = secrets.read_env(path)
        self._rendered()
        (self.root / "runtime" / "volumes" / "postgres_data").mkdir(parents=True)
        (self.root / "runtime" / "volumes" / "postgres_data" / "PG_VERSION").write_text("9.6")
        runner = FakeDocker(old_pg=before["POSTGRES_PASSWORD"], old_rmq="", running=("web",))
        self.assertEqual(self._rotate(ctx, runner), exit_codes.HEALTH_FAILED)
        self.assertIn("postgres", self.err.getvalue())
        self.assertIn("grdm-dev up", self.err.getvalue())
        self.assertEqual(secrets.read_env(path), before)  # untouched

    def test_rotate_fails_closed_when_docker_cannot_list_services(self):
        ctx = make_ctx(self.root)
        self.run_cmd(ctx, ns(secrets_action="init", force=False))
        before = secrets.read_env(self.root / "runtime" / ".env")
        self._rendered()
        runner = FakeDocker(old_pg="", old_rmq="", ps_rc=1)
        self.assertEqual(self._rotate(ctx, runner), exit_codes.HEALTH_FAILED)
        self.assertEqual(secrets.read_env(self.root / "runtime" / ".env"), before)

    def test_rotate_without_env_is_usage_error(self):
        ctx = make_ctx(self.root)
        self.assertEqual(self._rotate(ctx, FakeDocker(old_pg="", old_rmq="")), exit_codes.USAGE)

    def test_credential_users_match_templates(self):
        tpl_dir = Path(secrets.__file__).parent / "templates"
        pg = json.loads((tpl_dir / "postgres.json").read_text(encoding="utf-8"))
        rmq = json.loads((tpl_dir / "rabbitmq.json").read_text(encoding="utf-8"))
        self.assertEqual(pg["environment"]["POSTGRES_USER"], secrets.POSTGRES_USER)
        self.assertEqual(rmq["environment"]["RABBITMQ_DEFAULT_USER"], secrets.RABBITMQ_USER)
        self.assertEqual(pg["volumes"][0]["volume"], secrets.POSTGRES_VOLUME)
        self.assertEqual(rmq["volumes"][0]["volume"], secrets.RABBITMQ_VOLUME)

    def test_every_key_referenced_by_a_template_is_generated(self):
        import re
        tpl_dir = Path(secrets.__file__).parent / "templates"
        if not tpl_dir.exists():
            self.skipTest("templates/ not present")
        referenced = set()
        for f in tpl_dir.glob("*.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            data.pop("command", None)  # container-shell text; compose render escapes its `$` as `$$`
            data.pop("note", None)
            referenced.update(re.findall(r"\$\{?([A-Z][A-Z0-9_]*)", json.dumps(data)))
        generated = set(secrets.SECRET_KEYS) | set(secrets.default_non_secrets("core"))
        self.assertEqual(sorted(referenced - generated), [])

    def test_generated_cas_keys_satisfy_the_rules_of_the_image(self):
        """Every draw, because a length that is right on average still fails closed on the unlucky one."""
        for _ in range(200):
            values = secrets.fresh_secrets()
            self.assertEqual(secrets.cas_key_problems(values), [])
            self.assertEqual(secrets.check_no_defaults(values), [])
            self.assertEqual(len(values["TGC_ENCRYPTION_KEY"]), 43)
            self.assertEqual(len(values["TGC_SIGNING_KEY"]), 86)
            self.assertEqual(len(values["OSF_API_INSTITUTIONS_AUTH_JWESECRET"].encode("utf-8")), 32)
            self.assertGreaterEqual(len(values["OSF_API_INSTITUTIONS_AUTH_JWTSECRET"].encode("utf-8")), 32)
            self.assertEqual(len(base64.urlsafe_b64decode(values["TGC_ENCRYPTION_KEY"] + "=")), 32)
            self.assertEqual(len(base64.urlsafe_b64decode(values["TGC_SIGNING_KEY"] + "==")), 64)

    def test_every_cas_rule_names_a_generated_key(self):
        self.assertLessEqual(set(secrets.CAS_KEY_RULES), set(secrets.SECRET_KEYS))

    def test_a_wrong_cas_key_length_is_rejected_by_name_only(self):
        good = secrets.fresh_secrets()
        for key, size in (("TGC_ENCRYPTION_KEY", 42), ("TGC_ENCRYPTION_KEY", 44), ("TGC_SIGNING_KEY", 43),
                          ("OSF_API_INSTITUTIONS_AUTH_JWESECRET", 31), ("OSF_API_INSTITUTIONS_AUTH_JWESECRET", 33),
                          ("OSF_API_INSTITUTIONS_AUTH_JWTSECRET", 31)):
            values = {**good, key: "a" * size}
            self.assertEqual(secrets.cas_key_problems(values), [key], (key, size))
            self.assertIn(key, secrets.check_no_defaults(values))

    def test_a_long_jwt_key_is_accepted(self):
        values = {**secrets.fresh_secrets(), "OSF_API_INSTITUTIONS_AUTH_JWTSECRET": "a" * 200}
        self.assertEqual(secrets.cas_key_problems(values), [])

    def test_retired_cas_keys_are_not_generated_and_are_dropped_by_force(self):
        retired = {"CAS_TGC_ENCRYPTION_KEY", "CAS_TGC_SIGNING_KEY", "CAS_WEBFLOW_ENCRYPTION_KEY", "CAS_WEBFLOW_SIGNING_KEY"}
        self.assertEqual(retired & set(secrets.SECRET_KEYS), set())
        self.assertLessEqual(retired, set(secrets.OBSOLETE_SECRET_KEYS))
        ctx = make_ctx(self.root, profile="core")
        path = self.root / "runtime" / ".env"
        self.assertEqual(self.run_cmd(ctx, ns(secrets_action="init", force=False)), exit_codes.OK)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("".join(f"{k}=old-value\n" for k in sorted(retired)))
        self.assertEqual(self.run_cmd(ctx, ns(secrets_action="init", force=True)), exit_codes.OK)
        self.assertEqual(retired & set(secrets.read_env(path)), set())

    def test_no_action_is_usage_error(self):
        self.assertEqual(self.run_cmd(make_ctx(self.root), ns(secrets_action=None)), exit_codes.USAGE)


if __name__ == "__main__":
    unittest.main()
