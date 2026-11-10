import argparse
import errno
import io
import json
import os
import tempfile
import unittest
from collections import namedtuple
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from grdm_dev import database, exit_codes, lifecycle
from grdm_dev.context import Context

TARGET = "postgres:18.6@sha256:e3d24f6906d0760bf4da0dae872415391ededefad23fd471c47dc53b0ddf3c42"
TS = "20261110T000000Z"
OLD, NEW = f"grdm-dev-dbupgrade-old-{TS}", f"grdm-dev-dbupgrade-new-{TS}"
COMPOSE = {"services": {"postgres": {
    "image": TARGET,
    "platform": "linux/arm64",
    "command": ["postgres", "-c", "max_connections=500"],
    "environment": {"POSTGRES_DB": "osf", "POSTGRES_PASSWORD": "${POSTGRES_PASSWORD}", "PGDATA": "/var/lib/postgresql/data",
                    "POSTGRES_INITDB_ARGS": "--auth-host=md5 --auth-local=trust"},
    "tmpfs": ["/tmp:mode=1777", "/var/run/postgresql:mode=1777", "/var/lib/postgresql:mode=1777"],
}, "web": {"image": "grdm-dev/osf.io:abc"}}}
ROWS = {"osf": ["public.osf_osfuser r 3", "public.osf_osfuser_id_seq S 3 true", "extension plpgsql"],
        "cas": ["public.ticket r 0"], "postgres": ["extension plpgsql"]}
ROLES = ["postgres true true true true true true true -1 0123abcd"]
DUMP = "--\nSET default_transaction_read_only = off;\nCREATE ROLE postgres;\nALTER ROLE postgres WITH SUPERUSER PASSWORD 'md5x';\nCREATE DATABASE osf;\n"
STEPS = ("start-old", "dump", "start-new", "restore", "verify", "stop-new")
Usage = namedtuple("Usage", "total used free")


class Crash(BaseException):
    """A kill the process cannot catch (SIGKILL, power loss): nothing after it runs in this process."""


class FakeDocker:
    """`runner(argv) -> (rc, stdout)` for the docker calls of `db`: containers exist until removed, the new server's
    initdb writes PG_VERSION, and `fail` makes one step return an error, raise KeyboardInterrupt or crash."""

    def __init__(self, running=(), after=None, roles_after=None, dump=DUMP, fail=None, mode="rc", sticky=()):
        self.calls, self.running, self.dump = [], list(running), dump
        self.fail, self.mode, self.sticky = fail, mode, set(sticky)
        self.present: set[str] = set()
        self.rows = {"old": ROWS, "new": after if after is not None else ROWS}
        self.roles = {"old": ROLES, "new": roles_after if roles_after is not None else ROLES}

    def hit(self, label):
        if self.fail != label:
            return False
        self.fail = None  # an interrupt, a crash or an error happens once
        if self.mode == "interrupt":
            raise KeyboardInterrupt
        if self.mode == "crash":
            raise Crash(label)
        return True

    def __call__(self, argv):
        self.calls.append(argv)
        if argv[:2] == ["docker", "compose"] and "ps" in argv:
            return 0, json.dumps([{"Service": s, "State": "running"} for s in self.running])
        if argv[:3] == ["docker", "ps", "-a"]:
            name = argv[argv.index("--filter") + 1][len("name=^/"):-1]
            return 0, name + "\n" if name in self.present else ""
        if argv[:3] == ["docker", "run", "-d"]:
            name = argv[argv.index("--name") + 1]
            if self.hit("start-old" if "-old-" in name else "start-new"):
                return 1, ""
            self.present.add(name)
            if TARGET in argv:  # the entrypoint's initdb
                data = next(v.split(":")[0] for v in argv if v.endswith(":/var/lib/postgresql/data"))
                Path(data, "PG_VERSION").write_text("18\n")
            return 0, "id\n"
        if argv[:3] == ["docker", "run", "--rm"] and "pg_dumpall" in argv:
            if self.hit("dump"):
                return 1, ""
            backup = next(v.split(":")[0] for v in argv if v.endswith(":/backup"))
            Path(backup, "dumpall.sql").write_text(self.dump, encoding="utf-8")
            return 0, ""
        if argv[:2] == ["docker", "inspect"]:
            return 0, "true\n" if argv[-1] in self.present else "false\n"
        if argv[:2] == ["docker", "exec"]:
            side = "old" if "-old-" in argv[4] else "new"
            if "-f" in argv:
                return (3 if self.hit("restore") else 0), ""
            if "psql" in argv and "-c" in argv:
                sql, db = argv[-1], argv[argv.index("-d") + 1]
                if sql == database.DATABASES_SQL:
                    if side == "new" and self.hit("verify"):
                        return 1, ""
                    return 0, "\n".join(sorted(self.rows[side])) + "\n"
                if sql == database.ROLES_SQL:
                    return 0, "\n".join(self.roles[side]) + "\n"
                return 0, "\n".join(self.rows[side][db]) + "\n"
            return 0, ""
        if argv[:2] == ["docker", "stop"]:
            if self.hit("stop-" + ("old" if "-old-" in argv[-1] else "new")):
                return 1, ""
            return 0, ""
        if argv[:2] == ["docker", "rm"]:
            if argv[-1] in self.sticky:
                return 1, ""
            self.present.discard(argv[-1])
            return 0, ""
        return 0, ""

    def runs(self):
        return [c for c in self.calls if c[:3] == ["docker", "run", "-d"]]


def roomy(path):
    return Usage(10 ** 12, 0, 10 ** 12)


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.runtime = self.root / "runtime"
        self.runtime.mkdir()
        (self.runtime / "docker-compose.yml").write_text(json.dumps(COMPOSE))
        (self.runtime / ".env").write_text("POSTGRES_PASSWORD=s3cret-value\n")
        self.data = self.runtime / "volumes" / "postgres_data"
        self.data.mkdir(parents=True)
        (self.data / "PG_VERSION").write_text("9.6\n")
        self.kept = self.data.with_name(f"postgres_data.pg9.6-{TS}")
        self.new = self.data.with_name(f"postgres_data.pg18-{TS}.new")
        self.backup = self.runtime / "backups" / f"postgres-9.6-to-18-{TS}"
        self.journal = self.runtime / database.JOURNAL
        self.out, self.err = io.StringIO(), io.StringIO()

    def fresh(self):
        self.tearDown()
        self.setUp()

    def tearDown(self):
        for path in self.root.rglob("*"):
            try:
                path.chmod(0o755)
            except OSError:
                pass
        self.tmp.cleanup()

    def run_db(self, action, runner, yes=True, disk_usage=roomy, stamp=TS):
        ctx = Context(root=self.root, yes=yes, stdin_is_tty=False)
        with redirect_stdout(self.out), redirect_stderr(self.err):
            return database.run(ctx, argparse.Namespace(db_command=action), runner=runner, sleep=lambda s: None,
                                user="501:20", stamp=stamp, disk_usage=disk_usage)

    def run_up(self, runner):
        ctx = Context(root=self.root, stdin_is_tty=False)
        with redirect_stdout(self.out), redirect_stderr(self.err):
            return lifecycle.run(ctx, argparse.Namespace(lifecycle_action="up", no_open=True, timeout=1.0), runner=runner,
                                 prober=lambda url: (True, "HTTP 200"), sleep=lambda s: None)

    def major(self, path=None):
        return ((path or self.data) / "PG_VERSION").read_text().strip()

    def assert_old_intact(self, runner):
        self.assertEqual(self.major(), "9.6")
        self.assertFalse(self.kept.exists())
        self.assertFalse(self.journal.exists())
        self.assertEqual(runner.present, set())  # every migration server proved gone

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
        self.assertEqual(self.major(), "9.6")

    def test_data_major_distinguishes_empty_from_unknown(self):
        self.assertEqual(database.data_major(self.data), "9.6")
        (self.data / "PG_VERSION").write_text("garbage\n")
        self.assertIsNone(database.data_major(self.data))
        (self.data / "PG_VERSION").unlink()
        (self.data / "base").mkdir()
        self.assertIsNone(database.data_major(self.data))  # a non-empty directory without PG_VERSION is not "no cluster"
        (self.data / "base").rmdir()
        self.assertEqual(database.data_major(self.data), "")
        self.assertEqual(database.data_major(self.root / "absent"), "")

    def _unreadable(self):
        self.data.chmod(0o000)
        try:
            os.listdir(self.data)
        except PermissionError:
            return
        self.skipTest("permissions are not enforced for this user")

    def test_unreadable_pg_version_is_read_by_the_postgres_uid_in_a_container(self):
        calls = []

        def runner(argv):
            calls.append(argv)
            return 0, "9.6\n"

        self._unreadable()
        self.assertEqual(database.data_major(self.data, runner, TARGET, "linux/arm64"), "9.6")
        argv = calls[0]
        self.assertEqual(argv[argv.index("--user") + 1], "999:999")
        self.assertIn("--read-only", argv)
        self.assertEqual(argv[argv.index("--network") + 1], "none")
        self.assertIn(f"{self.data}:/data:ro", argv)

    def test_up_refuses_when_the_container_read_fails(self):
        calls = []

        def runner(argv):
            calls.append(argv)
            return 125, ""  # the helper container cannot start

        self._unreadable()
        self.assertEqual(self.run_up(runner), exit_codes.DB_UPGRADE_FAILED)
        self.assertIn("cannot read the PostgreSQL major", self.err.getvalue())
        self.assertFalse([c for c in calls if c[:2] == ["docker", "compose"]])

    def test_up_refuses_an_unparseable_or_clusterless_directory(self):
        (self.data / "PG_VERSION").write_text("nonsense\n")
        self.assertEqual(self.run_up(FakeDocker()), exit_codes.DB_UPGRADE_FAILED)
        (self.data / "PG_VERSION").unlink()
        (self.data / "global").mkdir()
        self.assertEqual(self.run_up(FakeDocker()), exit_codes.DB_UPGRADE_FAILED)
        self.assertEqual(self.err.getvalue().count("cannot read the PostgreSQL major"), 2)

    def test_up_stops_before_compose_on_a_data_directory_of_another_major(self):
        runner = FakeDocker()
        self.assertEqual(self.run_up(runner), exit_codes.DB_UPGRADE_FAILED)
        self.assertIn("grdm-dev db upgrade", self.err.getvalue())
        self.assertFalse([c for c in runner.calls if c[:2] == ["docker", "compose"]])

    def test_preflight_accepts_matching_and_empty_directories(self):
        ctx = Context(root=self.root, stdin_is_tty=False)
        (self.data / "PG_VERSION").write_text("18\n")
        self.assertIsNone(database.preflight(ctx))
        (self.data / "PG_VERSION").unlink()
        self.assertIsNone(database.preflight(ctx))

    # ------------------------------------------------------------------ verification scope (R1-05)

    def test_snapshot_keeps_a_database_named_roles_apart_from_the_roles(self):
        rows = {**ROWS, "roles": ["public.t r 7"]}
        runner = FakeDocker()
        runner.rows["old"] = rows
        snap = database.snapshot(OLD, runner)
        self.assertEqual(snap["databases"]["roles"], ["public.t r 7"])
        self.assertEqual(snap["roles"], ROLES)
        changed = {**rows, "roles": ["public.t r 6"]}
        diffs = database.snapshot_differences(snap, {"databases": changed, "roles": ROLES})
        self.assertEqual(diffs, ["database roles: before `public.t r 7`", "database roles: after `public.t r 6`"])

    def test_a_sequence_with_another_is_called_is_a_difference(self):
        after = {**ROWS, "osf": ["public.osf_osfuser r 3", "public.osf_osfuser_id_seq S 3 false", "extension plpgsql"]}
        runner = FakeDocker(after=after)
        self.assertEqual(self.run_db("upgrade", runner), exit_codes.DB_UPGRADE_FAILED)
        self.assertIn("osf_osfuser_id_seq S 3 false", self.err.getvalue())
        self.assert_old_intact(runner)
        self.assertIn("is_called", database.SNAPSHOT_SQL)

    def test_a_changed_role_attribute_is_a_difference_without_printing_the_verifier(self):
        runner = FakeDocker(roles_after=["postgres true true true true true true true -1 ffff0000"])
        self.assertEqual(self.run_db("upgrade", runner), exit_codes.DB_UPGRADE_FAILED)
        self.assertIn("role before `postgres …`", self.err.getvalue())
        self.assertNotIn("0123abcd", self.err.getvalue() + self.out.getvalue())
        self.assert_old_intact(runner)

    # ------------------------------------------------------------------ upgrade

    def test_upgrade_dumps_restores_verifies_and_keeps_the_old_directory(self):
        runner = FakeDocker()
        self.assertEqual(self.run_db("upgrade", runner), exit_codes.OK, self.err.getvalue())
        self.assertEqual(self.major(self.kept), "9.6")
        self.assertEqual(self.major(), "18")
        self.assertFalse(self.journal.exists())
        self.assertEqual(runner.present, set())
        self.assertEqual(self.backup.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.backup / "dumpall.sql").stat().st_mode & 0o777, 0o600)
        self.assertFalse((self.backup / "restore.sql").exists())  # derived copy removed after the restore
        record = json.loads((self.backup / "upgrade.json").read_text())
        self.assertEqual((record["from"], record["to"], record["kept"]), ("9.6", "18", str(self.kept)))
        old, new = runner.runs()
        self.assertIn(database.SOURCE_IMAGES["9.6"], old)
        self.assertIn(TARGET, new)
        for argv in (old, new):
            self.assertEqual(argv[argv.index("--network") + 1], "none")
            self.assertEqual(argv[-4:], ["-c", "listen_addresses=", "-c", "log_min_error_statement=panic"])
            self.assertEqual([argv[i + 1] for i, a in enumerate(argv) if a == "--cap-add"], list(database.SERVER_CAPS))
            self.assertIn("--read-only", argv)
            self.assertNotIn("s3cret-value", " ".join(argv))
        secret = Path(new[new.index("--env-file") + 1])
        self.assertEqual(secret.parent, self.backup)
        self.assertFalse(secret.exists())
        self.assertIn("POSTGRES_HOST_AUTH_METHOD=md5", new)
        self.assertIn("max_connections=500", new)
        dump = next(c for c in runner.calls if "pg_dumpall" in c)
        self.assertIn(TARGET, dump)
        self.assertEqual(dump[dump.index("--user") + 1], "501:20")
        # the old server is proved gone before the new one starts
        first_new = runner.calls.index(new)
        self.assertIn(["docker", "rm", "-f", OLD], runner.calls[:first_new])

    def test_upgrade_refuses_while_services_run(self):
        runner = FakeDocker(running=["postgres", "web"])
        self.assertEqual(self.run_db("upgrade", runner), exit_codes.DB_UPGRADE_FAILED)
        self.assertIn("grdm-dev down", self.err.getvalue())
        self.assertEqual(runner.runs(), [])

    def test_upgrade_needs_the_database_password_and_a_confirmation(self):
        (self.runtime / ".env").write_text("OTHER=1\n")
        self.assertEqual(self.run_db("upgrade", FakeDocker()), exit_codes.USAGE)
        (self.runtime / ".env").write_text("POSTGRES_PASSWORD=x\n")
        runner = FakeDocker()
        self.assertEqual(self.run_db("upgrade", runner, yes=False), exit_codes.USAGE)
        self.assertEqual(runner.runs(), [])
        self.assertFalse(self.journal.exists())

    def test_upgrade_refuses_an_unknown_source_major_and_is_a_no_op_when_current(self):
        (self.data / "PG_VERSION").write_text("12\n")
        self.assertEqual(self.run_db("upgrade", FakeDocker()), exit_codes.DB_UPGRADE_FAILED)
        self.assertIn("no source image for PostgreSQL 12", self.err.getvalue())
        (self.data / "PG_VERSION").write_text("18\n")
        self.assertEqual(self.run_db("upgrade", FakeDocker()), exit_codes.OK)
        self.assertIn("already current", self.out.getvalue())

    def test_upgrade_refuses_a_dump_without_exactly_one_bootstrap_role(self):
        runner = FakeDocker(dump="CREATE DATABASE osf;\n")
        self.assertEqual(self.run_db("upgrade", runner), exit_codes.DB_UPGRADE_FAILED)
        self.assertIn("CREATE ROLE postgres;", self.err.getvalue())
        self.assert_old_intact(runner)

    # ------------------------------------------------------------------ failures, interruptions, crashes (R1-01, R1-02)

    def test_a_failure_at_each_step_leaves_the_old_cluster_and_no_server(self):
        for step in STEPS:
            with self.subTest(step=step):
                self.fresh()
                runner = FakeDocker(fail=step, mode="rc")
                code = self.run_db("upgrade", runner)
                if step == "stop-new":  # a failed `docker stop` is fine once removal is proved
                    self.assertEqual(code, exit_codes.OK, self.err.getvalue())
                    continue
                self.assertEqual(code, exit_codes.DB_UPGRADE_FAILED)
                self.assertEqual(self.major(), "9.6")
                self.assertFalse(self.journal.exists())
                self.assertEqual(runner.present, set())

    def test_an_interrupt_at_each_step_is_cleaned_up_in_process(self):
        for step in STEPS:
            with self.subTest(step=step):
                self.fresh()
                runner = FakeDocker(fail=step, mode="interrupt")
                self.assertEqual(self.run_db("upgrade", runner), exit_codes.DB_UPGRADE_FAILED)
                self.assertIn("interrupted", self.err.getvalue())
                self.assert_old_intact(runner)

    def test_sigterm_is_handled_like_an_interrupt(self):
        def term(argv):
            if "pg_dumpall" in argv:
                os.kill(os.getpid(), database.signal.SIGTERM)
            return runner_inner(argv)

        runner_inner = FakeDocker()
        self.assertEqual(self.run_db("upgrade", term), exit_codes.DB_UPGRADE_FAILED)
        self.assertIn("interrupted", self.err.getvalue())
        self.assert_old_intact(runner_inner)

    def test_a_crash_at_each_step_is_recovered_by_the_next_up_or_upgrade(self):
        for i, step in enumerate(STEPS):
            with self.subTest(step=step):
                self.fresh()
                runner = FakeDocker(fail=step, mode="crash")
                with self.assertRaises(Crash):
                    self.run_db("upgrade", runner)
                self.assertTrue(self.journal.exists())  # ownership survives the crash
                runner.fail = None
                if i % 2:
                    self.assertEqual(self.run_up(runner), exit_codes.DB_UPGRADE_FAILED)  # recovered, then 9.6 ≠ 18
                    self.assertIn("rolled back an interrupted upgrade", self.err.getvalue())
                    self.assert_old_intact(runner)
                else:
                    self.assertEqual(self.run_db("upgrade", runner, stamp=TS + "b"), exit_codes.OK, self.err.getvalue())
                    self.assertEqual(self.major(), "18")
                    self.assertEqual(runner.present, set())

    def test_a_crash_between_the_renames_is_finished_by_recover_even_after_render(self):
        real = os.rename
        calls = []

        def rename(a, b):
            calls.append((a, b))
            if len(calls) == 2:
                raise Crash("between renames")
            real(a, b)

        runner = FakeDocker()
        with mock.patch.object(database.os, "rename", side_effect=rename), self.assertRaises(Crash):
            self.run_db("upgrade", runner)
        self.assertFalse(self.data.exists())
        self.data.mkdir()  # what `compose render` does to a missing volume directory
        self.assertEqual(self.run_up(runner), exit_codes.HEALTH_FAILED)  # recovered, versions match, compose is fake
        self.assertIn("finished an interrupted upgrade", self.err.getvalue())
        self.assertEqual(self.major(), "18")
        self.assertEqual(self.major(self.kept), "9.6")
        self.assertTrue((self.backup / "upgrade.json").exists())
        self.assertFalse(self.journal.exists())

    def test_a_failed_second_rename_puts_the_old_cluster_back(self):
        real = os.rename

        def rename(a, b):
            if Path(a) == self.new:
                raise OSError(errno.EIO, "injected")
            real(a, b)

        runner = FakeDocker()
        with mock.patch.object(database.os, "rename", side_effect=rename):
            self.assertEqual(self.run_db("upgrade", runner), exit_codes.DB_UPGRADE_FAILED)
        self.assertIn("swap could not be done", self.err.getvalue())
        self.assert_old_intact(runner)
        self.assertTrue(self.new.exists())

    def test_a_crash_after_the_swap_before_the_record_is_finished(self):
        real = database._write_record
        runner = FakeDocker()
        with mock.patch.object(database, "_write_record", side_effect=Crash("record")), self.assertRaises(Crash):
            self.run_db("upgrade", runner)
        self.assertEqual(self.major(), "18")
        self.assertTrue(self.journal.exists())
        self.assertEqual(self.run_db("recover", runner), exit_codes.OK)
        self.assertTrue((self.backup / "upgrade.json").exists())
        self.assertFalse(self.journal.exists())
        self.assertIs(database._write_record, real)

    def test_a_server_that_cannot_be_removed_keeps_the_journal_and_blocks_up(self):
        runner = FakeDocker(sticky={OLD})
        self.assertEqual(self.run_db("upgrade", runner), exit_codes.DB_UPGRADE_FAILED)
        self.assertIn(f"docker rm -f {OLD}", self.err.getvalue())
        self.assertTrue(self.journal.exists())
        self.assertEqual(self.major(), "9.6")
        self.assertEqual(self.run_up(runner), exit_codes.DB_UPGRADE_FAILED)
        self.assertIn("could not be recovered", self.err.getvalue())
        self.assertFalse([c for c in runner.calls if c[:2] == ["docker", "compose"] and "up" in c])
        runner.sticky.clear()
        self.assertEqual(self.run_db("recover", runner), exit_codes.OK)
        self.assert_old_intact(runner)

    def test_an_unanswering_docker_is_not_taken_for_an_absent_server(self):
        runner = FakeDocker(fail="start-new", mode="crash")
        with self.assertRaises(Crash):
            self.run_db("upgrade", runner)
        self.assertEqual(self.run_db("recover", lambda argv: (1, "")), exit_codes.DB_UPGRADE_FAILED)
        self.assertTrue(self.journal.exists())

    def test_a_second_operation_waits_for_the_lock(self):
        ctx = Context(root=self.root, yes=True, stdin_is_tty=False)
        runner = FakeDocker()
        with database.operation_lock(ctx):
            pid = os.fork()
            if pid == 0:  # a separate process, as a second terminal would be
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    code = database.run(ctx, argparse.Namespace(db_command="upgrade"), runner=runner,
                                        sleep=lambda s: None, user="501:20", stamp=TS, disk_usage=roomy)
                os._exit(code)
            _, status = os.waitpid(pid, 0)
        self.assertEqual(os.WEXITSTATUS(status), exit_codes.DB_UPGRADE_FAILED)
        self.assertEqual(self.major(), "9.6")

    # ------------------------------------------------------------------ disk (R1-03)

    def test_disk_is_checked_before_any_server_starts(self):
        runner = FakeDocker()
        tight = lambda path: Usage(10 ** 9, 10 ** 9 - 100 * database.MIB, 100 * database.MIB)  # noqa: E731
        self.assertEqual(self.run_db("upgrade", runner, disk_usage=tight), exit_codes.DB_UPGRADE_FAILED)
        self.assertIn("not enough free disk", self.err.getvalue())
        self.assertEqual(runner.runs(), [])
        self.assertFalse(self.journal.exists())

    def test_disk_estimate_adds_up_on_one_filesystem_and_splits_on_two(self):
        size = 100 * database.MIB
        need_b, need_v = 2 * size + database.BACKUP_MARGIN, 2 * size + database.VOLUME_MARGIN
        free = lambda n: (lambda path: Usage(0, 0, n))  # noqa: E731
        backups, volumes = self.runtime, self.data.parent
        self.assertEqual(database.disk_problems(size, backups, volumes, free(need_b + need_v)), [])
        self.assertTrue(database.disk_problems(size, backups, volumes, free(need_b + need_v - 1)))
        other = mock.Mock(st_dev=1), mock.Mock(st_dev=2)
        with mock.patch.object(Path, "stat", side_effect=[other[0], other[1]]):
            self.assertEqual(database.disk_problems(size, backups, volumes, free(max(need_b, need_v))), [])

    def test_enospc_in_the_dump_the_filter_and_the_restore_leaves_the_old_cluster(self):
        cases = {
            "dump": lambda: FakeDocker(fail="dump"),
            "restore": lambda: FakeDocker(fail="restore"),
        }
        for name, make in cases.items():
            with self.subTest(step=name):
                self.fresh()
                runner = make()
                self.assertEqual(self.run_db("upgrade", runner), exit_codes.DB_UPGRADE_FAILED)
                self.assert_old_intact(runner)
        self.fresh()
        runner = FakeDocker()
        with mock.patch.object(database, "write_restore_file", side_effect=OSError(errno.ENOSPC, "No space left on device")):
            self.assertEqual(self.run_db("upgrade", runner), exit_codes.DB_UPGRADE_FAILED)
        self.assertIn("No space left", self.err.getvalue())
        self.assert_old_intact(runner)

    def test_enospc_in_each_journal_write(self):
        real = database.write_durable
        for nth in (1, 2, 3, 4):  # prepare, swap mark, after swap, record
            with self.subTest(write=nth):
                self.fresh()
                count = []

                def write(path, data, nth=nth):
                    count.append(path)
                    if len(count) == nth:
                        raise OSError(errno.ENOSPC, "No space left on device")
                    real(path, data)

                runner = FakeDocker()
                with mock.patch.object(database, "write_durable", side_effect=write):
                    code = self.run_db("upgrade", runner)
                self.assertEqual(code, exit_codes.DB_UPGRADE_FAILED)
                self.assertEqual(runner.present, set())
                if nth == 1:
                    self.assertEqual(runner.runs(), [])  # nothing started without a journal
                    self.assertEqual(self.major(), "9.6")
                elif nth == 2:
                    self.assert_old_intact(runner)  # the swap mark is written before any rename
                else:
                    self.assertEqual(self.major(), "18")  # swapped; the record write is retried by recovery
                    self.assertFalse(self.journal.exists())
                    self.assertTrue((self.backup / "upgrade.json").exists())

    # ------------------------------------------------------------------ rollback

    def _upgraded(self):
        self.assertEqual(self.run_db("upgrade", FakeDocker()), exit_codes.OK, self.err.getvalue())

    def test_rollback_puts_the_kept_directory_back_and_marks_the_record(self):
        self._upgraded()
        self.assertEqual(self.run_db("rollback", FakeDocker(), stamp=TS + "r"), exit_codes.OK, self.err.getvalue())
        self.assertEqual(self.major(), "9.6")
        self.assertTrue(json.loads((self.backup / "upgrade.json").read_text())["rolled_back_at"])
        self.assertEqual(self.run_db("rollback", FakeDocker()), exit_codes.DB_UPGRADE_FAILED)  # nothing left to roll back
        self.assertIn("no upgrade record", self.err.getvalue())

    def test_a_crash_between_the_rollback_renames_is_finished(self):
        self._upgraded()
        real = os.rename
        calls = []

        def rename(a, b):
            calls.append(a)
            if len(calls) == 2:
                raise Crash("between renames")
            real(a, b)

        with mock.patch.object(database.os, "rename", side_effect=rename), self.assertRaises(Crash):
            self.run_db("rollback", FakeDocker(), stamp=TS + "r")
        self.assertFalse(self.data.exists())
        self.assertEqual(self.run_db("recover", FakeDocker()), exit_codes.OK)
        self.assertEqual(self.major(), "9.6")
        self.assertFalse(self.journal.exists())

    def test_a_failed_second_rollback_rename_is_compensated(self):
        self._upgraded()
        real = os.rename

        def rename(a, b):
            if Path(a) == self.kept:
                raise OSError(errno.EIO, "injected")
            real(a, b)

        with mock.patch.object(database.os, "rename", side_effect=rename):
            self.assertEqual(self.run_db("rollback", FakeDocker(), stamp=TS + "r"), exit_codes.DB_UPGRADE_FAILED)
        self.assertEqual(self.major(), "18")
        self.assertFalse(self.journal.exists())

    def test_rollback_refuses_while_services_run(self):
        self._upgraded()
        self.assertEqual(self.run_db("rollback", FakeDocker(running=["postgres"])), exit_codes.DB_UPGRADE_FAILED)
        self.assertEqual(self.major(), "18")

    # ------------------------------------------------------------------ review r2

    def _crash_before_swap(self, action):
        runner = FakeDocker()
        if action == "rollback":
            self._upgraded()
        with mock.patch.object(database, "_swap", side_effect=Crash("before swap")), self.assertRaises(Crash):
            self.run_db(action, runner, stamp=TS + "r" if action == "rollback" else TS)
        self.assertTrue(self.journal.exists())
        return runner

    def _renames_failing_after(self, ok):
        real, count = os.rename, [0]

        def rename(a, b):
            count[0] += 1
            if count[0] > ok:
                raise OSError(errno.EIO, "replacement and compensation failed")
            real(a, b)

        return mock.patch.object(database.os, "rename", side_effect=rename)

    def test_r2_01_a_failed_compensation_during_recovery_keeps_the_journal(self):
        for action, final in (("upgrade", "18"), ("rollback", "9.6")):
            with self.subTest(action=action):
                self.fresh()
                runner = self._crash_before_swap(action)
                with self._renames_failing_after(1):
                    self.assertEqual(self.run_db("recover", runner), exit_codes.DB_UPGRADE_FAILED)
                self.assertFalse(self.data.exists())
                self.assertTrue(self.journal.exists())  # the only record of where the data went
                self.assertIn("so did putting", self.err.getvalue())
                with self._renames_failing_after(0):  # it keeps failing: `up` and `recover` refuse, the journal stays
                    self.assertEqual(self.run_up(runner), exit_codes.DB_UPGRADE_FAILED)  # never a fresh cluster
                    self.assertEqual(self.run_db("recover", runner), exit_codes.DB_UPGRADE_FAILED)
                self.assertFalse([c for c in runner.calls if c[:2] == ["docker", "compose"] and "up" in c])
                self.assertTrue(self.journal.exists())
                self.assertEqual(self.run_db("recover", runner), exit_codes.OK)
                self.assertEqual(self.major(), final)
                self.assertFalse(self.journal.exists())

    def test_r2_01_an_in_process_double_failure_keeps_the_journal(self):
        real, count = os.rename, [0]

        def rename(a, b):
            count[0] += 1
            if count[0] >= 2:  # the replacement and the compensation, then every retry
                raise OSError(errno.EIO, "injected")
            real(a, b)

        runner = FakeDocker()
        with mock.patch.object(database.os, "rename", side_effect=rename):
            self.assertEqual(self.run_db("upgrade", runner), exit_codes.DB_UPGRADE_FAILED)
        self.assertFalse(self.data.exists())
        self.assertTrue(self.journal.exists())
        self.assertIn("recovery failed", self.err.getvalue())
        self.assertEqual(self.run_db("recover", runner), exit_codes.OK)
        self.assertEqual(self.major(), "18")

    def test_r2_01_a_verified_compensation_retires_the_journal(self):
        real = os.rename

        def rename(a, b):
            if Path(a) == self.new:
                raise OSError(errno.EIO, "injected")
            real(a, b)

        runner = self._crash_before_swap("upgrade")
        with mock.patch.object(database.os, "rename", side_effect=rename):
            self.assertEqual(self.run_db("recover", runner), exit_codes.OK)
        self.assertEqual(self.major(), "9.6")
        self.assertFalse(self.journal.exists())

    def test_r2_02_up_refuses_while_any_db_command_holds_the_lock(self):
        (self.data / "PG_VERSION").write_text("18\n")
        runner = FakeDocker()
        with database.operation_lock(Context(root=self.root)):
            self.assertEqual(self.run_up(runner), exit_codes.DB_UPGRADE_FAILED)
        self.assertIn("db-operation.lock", self.err.getvalue())
        self.assertFalse([c for c in runner.calls if c[:2] == ["docker", "compose"]])

    def test_r2_02_up_cannot_start_between_the_checks_and_the_swap_of_a_rollback(self):
        self._upgraded()
        racer = FakeDocker()
        codes = []

        def confirm(ctx, *args, **kwargs):  # the moment after rollback checked that nothing runs
            codes.append(self.run_up(racer))
            return True

        with mock.patch.object(Context, "confirm", confirm):
            self.assertEqual(self.run_db("rollback", FakeDocker(), stamp=TS + "r"), exit_codes.OK)
        self.assertEqual(codes, [exit_codes.DB_UPGRADE_FAILED])
        self.assertFalse([c for c in racer.calls if c[:2] == ["docker", "compose"] and "up" in c])
        self.assertEqual(self.major(), "9.6")

    def test_r2_02_a_db_command_cannot_start_while_up_starts_compose(self):
        (self.data / "PG_VERSION").write_text("18\n")
        self._upgraded_record_only()
        codes = []
        inner = FakeDocker()

        def runner(argv):
            if argv[:2] == ["docker", "compose"] and "up" in argv:
                codes.append(self.run_db("rollback", FakeDocker()))
                codes.append(self.run_db("upgrade", FakeDocker()))
                codes.append(self.run_db("recover", FakeDocker()))
            return inner(argv)

        self.run_up(runner)
        self.assertEqual(codes, [exit_codes.DB_UPGRADE_FAILED] * 3)
        self.assertEqual(self.major(), "18")

    def _upgraded_record_only(self):
        self.kept.mkdir()
        (self.kept / "PG_VERSION").write_text("9.6\n")
        self.backup.mkdir(parents=True)
        (self.backup / "upgrade.json").write_text(json.dumps({"from": "9.6", "to": "18", "kept": str(self.kept), "image": TARGET}))

    def test_r2_02_reset_and_db_commands_exclude_each_other(self):
        ctx = Context(root=self.root, yes=True, stdin_is_tty=False)
        with database.operation_lock(ctx), redirect_stdout(self.out), redirect_stderr(self.err):
            self.assertEqual(lifecycle.run(ctx, argparse.Namespace(lifecycle_action="reset"), runner=FakeDocker(), rmtree=lambda p: None),
                             exit_codes.DB_UPGRADE_FAILED)
        self.assertEqual(self.major(), "9.6")
        codes = []

        def rmtree(path):  # a db command attempted while reset deletes
            codes.append(self.run_db("upgrade", FakeDocker()))
            import shutil
            shutil.rmtree(path)

        with redirect_stdout(self.out), redirect_stderr(self.err):
            self.assertEqual(lifecycle.run(ctx, argparse.Namespace(lifecycle_action="reset"), runner=FakeDocker(), rmtree=rmtree), exit_codes.OK)
        self.assertEqual(codes, [exit_codes.DB_UPGRADE_FAILED])

    def test_r2_03_recovery_syncs_the_renames_before_the_record_and_the_journal(self):
        for action in ("upgrade", "rollback"):
            with self.subTest(action=action):
                self.fresh()
                runner = FakeDocker()
                if action == "rollback":
                    self._upgraded()
                real, count = os.rename, [0]

                def rename(a, b):
                    count[0] += 1
                    if count[0] == 2:
                        raise Crash("gap")
                    real(a, b)

                with mock.patch.object(database.os, "rename", side_effect=rename), self.assertRaises(Crash):
                    self.run_db(action, runner, stamp=TS + "r" if action == "rollback" else TS)
                order = []
                real_sync, real_drop = database._fsync_dir, database._drop_journal
                with mock.patch.object(database, "_fsync_dir", side_effect=lambda p: (order.append(("sync", Path(p))), real_sync(p))), \
                        mock.patch.object(database, "_drop_journal", side_effect=lambda c: (order.append(("drop", None)), real_drop(c))):
                    self.assertEqual(self.run_db("recover", runner), exit_codes.OK)
                first_sync = order.index(("sync", self.data.parent))
                self.assertLess(first_sync, order.index(("drop", None)))

    def test_r2_03_a_failed_directory_sync_is_an_error_and_keeps_recovery_possible(self):
        with mock.patch.object(database.os, "fsync", side_effect=OSError(errno.EIO, "disk error")):
            with self.assertRaises(OSError):
                database._fsync_dir(self.runtime)
        with mock.patch.object(database.os, "fsync", side_effect=OSError(errno.EINVAL, "not supported")):
            database._fsync_dir(self.runtime)  # a filesystem that cannot sync directories is not a failure
        # the first journal sync fails: nothing starts
        runner = FakeDocker()
        with mock.patch.object(database, "_fsync_dir", side_effect=OSError(errno.EIO, "disk error")):
            self.assertEqual(self.run_db("upgrade", runner), exit_codes.DB_UPGRADE_FAILED)
        self.assertEqual(runner.runs(), [])
        self.assertFalse(self.journal.exists())
        # a sync fails during recovery after a rename: the journal stays, a later recovery completes
        runner = self._crash_before_swap("upgrade")
        real_sync = database._fsync_dir

        def sync(path):
            if Path(path) == self.data.parent:
                raise OSError(errno.EIO, "disk error")
            real_sync(path)

        with mock.patch.object(database, "_fsync_dir", side_effect=sync):
            self.assertEqual(self.run_db("recover", runner), exit_codes.DB_UPGRADE_FAILED)
        self.assertTrue(self.journal.exists())
        self.assertEqual(self.run_db("recover", runner), exit_codes.OK)
        self.assertEqual(self.major(), "18")
        self.assertTrue((self.backup / "upgrade.json").exists())

    def test_r2_04_a_non_ascii_pg_version_is_exit_15_not_a_traceback(self):
        (self.data / "PG_VERSION").write_bytes(b"\xff\n")
        self.assertIsNone(database.data_major(self.data))
        runner = FakeDocker()
        self.assertEqual(self.run_up(runner), exit_codes.DB_UPGRADE_FAILED)
        self.assertIn("cannot read the PostgreSQL major", self.err.getvalue())
        self.assertFalse([c for c in runner.calls if c[:2] == ["docker", "compose"]])
        self.assertEqual(self.run_db("upgrade", FakeDocker()), exit_codes.DB_UPGRADE_FAILED)
        self.assertEqual(self.run_db("status", FakeDocker()), exit_codes.OK)
        self.assertIn("unknown", self.out.getvalue())

        def undecodable(argv):
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

        self._unreadable()
        self.assertIsNone(database.data_major(self.data, undecodable, TARGET))


if __name__ == "__main__":
    unittest.main()
