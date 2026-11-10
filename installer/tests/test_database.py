import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from grdm_dev import database, exit_codes, lifecycle
from grdm_dev.context import Context

TARGET = "postgres:18.6@sha256:e3d24f6906d0760bf4da0dae872415391ededefad23fd471c47dc53b0ddf3c42"
COMPOSE = {"services": {"postgres": {
    "image": TARGET,
    "platform": "linux/arm64",
    "command": ["postgres", "-c", "max_connections=500"],
    "environment": {"POSTGRES_DB": "osf", "POSTGRES_PASSWORD": "${POSTGRES_PASSWORD}", "PGDATA": "/var/lib/postgresql/data",
                    "POSTGRES_INITDB_ARGS": "--auth-host=md5 --auth-local=trust"},
    "tmpfs": ["/tmp:mode=1777", "/var/run/postgresql:mode=1777", "/var/lib/postgresql:mode=1777"],
}, "web": {"image": "grdm-dev/osf.io:abc"}}}
ROWS = {"osf": ["public.osf_osfuser r 3", "public.osf_osfuser_id_seq S 3", "extension plpgsql"],
        "cas": ["public.ticket r 0"], "postgres": ["extension plpgsql"]}
DUMP = "--\nSET default_transaction_read_only = off;\nCREATE ROLE postgres;\nALTER ROLE postgres WITH SUPERUSER PASSWORD 'md5x';\nCREATE DATABASE osf;\n"


class FakeDocker:
    """`runner(argv) -> (rc, stdout)` for the docker calls of `db upgrade`; the new server returns `after` rows."""

    def __init__(self, running=(), after=None, dump=DUMP, restore_rc=0):
        self.calls, self.running, self.dump, self.restore_rc = [], list(running), dump, restore_rc
        self.rows = {"old": ROWS, "new": after if after is not None else ROWS}

    def __call__(self, argv):
        self.calls.append(argv)
        if argv[:2] == ["docker", "compose"] and "ps" in argv:
            return 0, json.dumps([{"Service": s, "State": "running"} for s in self.running])
        if argv[:3] == ["docker", "run", "--rm"] and "pg_dumpall" in argv:
            backup = next(v.split(":")[0] for v in argv if v.endswith(":/backup"))
            Path(backup, "dumpall.sql").write_text(self.dump, encoding="utf-8")
            return 0, ""
        if argv[:2] == ["docker", "inspect"]:
            return 0, "true\n"
        if argv[:2] == ["docker", "exec"]:
            side = "old" if "-old-" in argv[4] else "new"
            if "-f" in argv:
                return self.restore_rc, ""
            if "-c" in argv and "psql" in argv:
                sql, db = argv[-1], argv[argv.index("-d") + 1]
                if sql == database.DATABASES_SQL:
                    return 0, "\n".join(sorted(self.rows[side])) + "\n"
                if sql == database.ROLES_SQL:
                    return 0, "postgres\n"
                return 0, "\n".join(self.rows[side][db]) + "\n"
            return 0, ""
        return 0, ""

    def runs(self):
        return [c for c in self.calls if c[:3] == ["docker", "run", "-d"]]


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "runtime").mkdir()
        (self.root / "runtime" / "docker-compose.yml").write_text(json.dumps(COMPOSE))
        (self.root / "runtime" / ".env").write_text("POSTGRES_PASSWORD=s3cret-value\n")
        self.data = self.root / "runtime" / "volumes" / "postgres_data"
        self.data.mkdir(parents=True)
        (self.data / "PG_VERSION").write_text("9.6\n")
        self.out, self.err = io.StringIO(), io.StringIO()

    def tearDown(self):
        self.tmp.cleanup()

    def run_db(self, action, runner, yes=True, **ctx_kw):
        ctx = Context(root=self.root, yes=yes, stdin_is_tty=False, **ctx_kw)
        with redirect_stdout(self.out), redirect_stderr(self.err):
            return database.run(ctx, argparse.Namespace(db_command=action), runner=runner, sleep=lambda s: None,
                                user="501:20", stamp="20261110T000000Z")

    # ------------------------------------------------------------------ facts

    def test_image_major_reads_one_part_from_10_and_two_before(self):
        self.assertEqual(database.image_major(TARGET), "18")
        self.assertEqual(database.image_major("postgres:9.6"), "9.6")
        self.assertEqual(database.image_major("postgres:15-alpine"), "15")
        self.assertEqual(database.image_major(database.SOURCE_IMAGES["9.6"]), "9.6")
        self.assertIsNone(database.image_major("postgres"))
        self.assertIsNone(database.image_major("postgres:latest"))
        self.assertIsNone(database.image_major("localhost:5000/postgres"))

    def test_status_reports_upgrade_needed_without_changing_anything(self):
        runner = FakeDocker()
        self.assertEqual(self.run_db("status", runner), exit_codes.OK)
        self.assertIn("upgrade-needed", self.out.getvalue())
        self.assertEqual(runner.calls, [])
        self.assertEqual((self.data / "PG_VERSION").read_text(), "9.6\n")

    def test_unreadable_pg_version_is_read_by_the_postgres_uid_in_a_container(self):
        calls = []

        def runner(argv):
            calls.append(argv)
            return 0, "9.6\n"

        self.data.chmod(0o000)
        try:
            if (self.data / "PG_VERSION").exists():  # running as root: permissions do not apply
                self.skipTest("permissions are not enforced for this user")
        except PermissionError:
            pass
        try:
            self.assertEqual(database.data_major(self.data, runner, TARGET, "linux/arm64"), "9.6")
        finally:
            self.data.chmod(0o755)
        argv = calls[0]
        self.assertEqual(argv[argv.index("--user") + 1], "999:999")
        self.assertIn("--read-only", argv)
        self.assertEqual(argv[argv.index("--network") + 1], "none")
        self.assertIn(f"{self.data}:/data:ro", argv)

    # ------------------------------------------------------------------ upgrade

    def test_upgrade_dumps_restores_verifies_and_keeps_the_old_directory(self):
        runner = FakeDocker()
        self.assertEqual(self.run_db("upgrade", runner), exit_codes.OK, self.err.getvalue())
        kept = self.data.with_name("postgres_data.pg9.6-20261110T000000Z")
        self.assertEqual((kept / "PG_VERSION").read_text(), "9.6\n")  # untouched, set aside
        self.assertTrue(self.data.is_dir())
        self.assertFalse((self.data / "PG_VERSION").exists())  # the new cluster (fake initdb wrote nothing)
        backup = self.root / "runtime" / "backups" / "postgres-9.6-to-18-20261110T000000Z"
        self.assertEqual(backup.stat().st_mode & 0o777, 0o700)
        self.assertEqual((backup / "dumpall.sql").stat().st_mode & 0o777, 0o600)
        self.assertEqual((backup / "restore.sql").stat().st_mode & 0o777, 0o600)
        restore = (backup / "restore.sql").read_text()
        self.assertNotIn("CREATE ROLE postgres;", restore)
        self.assertIn("ALTER ROLE postgres WITH SUPERUSER PASSWORD 'md5x';", restore)
        record = json.loads((backup / "upgrade.json").read_text())
        self.assertEqual((record["from"], record["to"], record["kept"]), ("9.6", "18", str(kept)))
        old, new = runner.runs()
        self.assertIn(database.SOURCE_IMAGES["9.6"], old)
        self.assertIn(TARGET, new)
        for argv in (old, new):
            self.assertEqual(argv[argv.index("--network") + 1], "none")
            self.assertEqual(argv[-2:], ["-c", "listen_addresses="])  # no TCP listener
            self.assertEqual([argv[i + 1] for i, a in enumerate(argv) if a == "--cap-add"], list(database.SERVER_CAPS))
            self.assertIn("--read-only", argv)
            self.assertNotIn("s3cret-value", " ".join(argv))
        self.assertNotIn("--env-file", old)
        secret = Path(new[new.index("--env-file") + 1])
        self.assertEqual(secret.parent, backup)
        self.assertFalse(secret.exists())  # removed once the container exists
        self.assertIn("POSTGRES_HOST_AUTH_METHOD=md5", new)  # same pg_hba as a fresh install with --auth-host=md5
        self.assertIn("POSTGRES_INITDB_ARGS=--auth-host=md5 --auth-local=trust", new)
        self.assertIn("max_connections=500", new)
        self.assertIn("/var/lib/postgresql", new)  # the rendered tmpfs; the socket directory is the throwaway volume
        self.assertNotIn("/var/run/postgresql:mode=1777", new)
        dump = next(c for c in runner.calls if "pg_dumpall" in c)
        self.assertIn(TARGET, dump)  # dumped with the newer client
        self.assertEqual(dump[dump.index("--user") + 1], "501:20")
        restore_call = next(c for c in runner.calls if c[:2] == ["docker", "exec"] and "-f" in c)
        self.assertIn("ON_ERROR_STOP=1", restore_call)

    def test_upgrade_refuses_while_services_run(self):
        runner = FakeDocker(running=["postgres", "web"])
        self.assertEqual(self.run_db("upgrade", runner), exit_codes.DB_UPGRADE_FAILED)
        self.assertIn("grdm-dev down", self.err.getvalue())
        self.assertEqual(runner.runs(), [])
        self.assertEqual(sorted(p.name for p in self.data.parent.iterdir()), ["postgres_data"])

    def test_upgrade_stops_without_renaming_when_the_restored_data_differs(self):
        after = {**ROWS, "osf": ["public.osf_osfuser r 2", "public.osf_osfuser_id_seq S 3", "extension plpgsql"]}
        runner = FakeDocker(after=after)
        self.assertEqual(self.run_db("upgrade", runner), exit_codes.DB_UPGRADE_FAILED)
        self.assertIn("restored data differs", self.err.getvalue())
        self.assertEqual((self.data / "PG_VERSION").read_text(), "9.6\n")
        self.assertFalse(self.data.with_name("postgres_data.pg9.6-20261110T000000Z").exists())
        self.assertTrue(self.data.with_name("postgres_data.pg18-20261110T000000Z.new").exists())  # left for inspection
        removed = [c[2] for c in runner.calls if c[:2] == ["docker", "rm"]]
        self.assertEqual(removed, ["grdm-dev-dbupgrade-old-20261110T000000Z"])  # the new server is stopped, kept for docker logs
        self.assertIn(["docker", "stop", "-t", "60", "grdm-dev-dbupgrade-new-20261110T000000Z"], runner.calls)

    def test_upgrade_stops_when_the_restore_fails(self):
        runner = FakeDocker(restore_rc=3)
        self.assertEqual(self.run_db("upgrade", runner), exit_codes.DB_UPGRADE_FAILED)
        self.assertIn("restore exited 3", self.err.getvalue())
        self.assertEqual((self.data / "PG_VERSION").read_text(), "9.6\n")

    def test_upgrade_refuses_a_dump_without_exactly_one_bootstrap_role(self):
        runner = FakeDocker(dump="CREATE DATABASE osf;\n")
        self.assertEqual(self.run_db("upgrade", runner), exit_codes.DB_UPGRADE_FAILED)
        self.assertIn("CREATE ROLE postgres;", self.err.getvalue())
        self.assertEqual((self.data / "PG_VERSION").read_text(), "9.6\n")

    def test_upgrade_needs_the_database_password(self):
        (self.root / "runtime" / ".env").write_text("OTHER=1\n")
        runner = FakeDocker()
        self.assertEqual(self.run_db("upgrade", runner), exit_codes.USAGE)
        self.assertIn("secrets init", self.err.getvalue())
        self.assertEqual(runner.runs(), [])

    def test_upgrade_needs_a_confirmation_without_a_terminal(self):
        runner = FakeDocker()
        self.assertEqual(self.run_db("upgrade", runner, yes=False), exit_codes.USAGE)
        self.assertEqual(runner.runs(), [])

    def test_upgrade_refuses_an_unknown_source_major(self):
        (self.data / "PG_VERSION").write_text("12\n")
        runner = FakeDocker()
        self.assertEqual(self.run_db("upgrade", runner), exit_codes.DB_UPGRADE_FAILED)
        self.assertIn("no source image for PostgreSQL 12", self.err.getvalue())
        self.assertEqual(runner.calls, [])

    def test_upgrade_is_a_no_op_when_current_or_empty(self):
        (self.data / "PG_VERSION").write_text("18\n")
        self.assertEqual(self.run_db("upgrade", FakeDocker()), exit_codes.OK)
        self.assertIn("already current", self.out.getvalue())
        (self.data / "PG_VERSION").unlink()
        self.assertEqual(self.run_db("upgrade", FakeDocker()), exit_codes.OK)
        self.assertIn("no cluster yet", self.out.getvalue())

    # ------------------------------------------------------------------ rollback and up

    def test_rollback_puts_the_kept_directory_back(self):
        self.assertEqual(self.run_db("upgrade", FakeDocker()), exit_codes.OK)
        (self.data / "PG_VERSION").write_text("18\n")
        self.assertEqual(self.run_db("rollback", FakeDocker()), exit_codes.OK, self.err.getvalue())
        self.assertEqual((self.data / "PG_VERSION").read_text(), "9.6\n")
        aside = [p.name for p in self.data.parent.iterdir() if "rolledback" in p.name]
        self.assertEqual(aside, ["postgres_data.pg18-rolledback-20261110T000000Z"])
        self.assertIn("compose render", self.err.getvalue())

    def test_rollback_without_a_record_fails(self):
        self.assertEqual(self.run_db("rollback", FakeDocker()), exit_codes.DB_UPGRADE_FAILED)
        self.assertIn("no upgrade record", self.err.getvalue())

    def test_rollback_refuses_while_services_run(self):
        self.assertEqual(self.run_db("upgrade", FakeDocker()), exit_codes.OK)
        self.assertEqual(self.run_db("rollback", FakeDocker(running=["postgres"])), exit_codes.DB_UPGRADE_FAILED)
        self.assertFalse((self.data / "PG_VERSION").exists())

    def test_up_stops_before_compose_on_a_data_directory_of_another_major(self):
        calls = []

        def runner(argv):
            calls.append(argv)
            return 0, ""

        ctx = Context(root=self.root, stdin_is_tty=False)
        with redirect_stdout(self.out), redirect_stderr(self.err):
            code = lifecycle.run(ctx, argparse.Namespace(lifecycle_action="up", no_open=True, timeout=1.0), runner=runner,
                                 prober=lambda url: (True, "HTTP 200"), sleep=lambda s: None)
        self.assertEqual(code, exit_codes.DB_UPGRADE_FAILED)
        self.assertIn("grdm-dev db upgrade", self.err.getvalue())
        self.assertEqual(calls, [])

    def test_preflight_accepts_matching_and_empty_directories(self):
        ctx = Context(root=self.root, stdin_is_tty=False)
        (self.data / "PG_VERSION").write_text("18\n")
        self.assertIsNone(database.preflight(ctx))
        (self.data / "PG_VERSION").unlink()
        self.assertIsNone(database.preflight(ctx))


if __name__ == "__main__":
    unittest.main()
