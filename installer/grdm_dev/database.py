"""grdm-dev db status / upgrade / rollback / recover — move the PostgreSQL data directory to the major of the
rendered image (ADR-12).

A PostgreSQL server refuses a data directory written by another major ("database files are incompatible with
server"), so a new image needs the data moved. The move is a dump and restore, never an in-place change.

status    prints the major of runtime/volumes/postgres_data, the major of the rendered `postgres` service, whether
          `db upgrade` is needed and whether an interrupted operation is pending. Changes nothing.
upgrade   with every service of the project stopped (`grdm-dev down`), enough free disk (disk_problems) and after a
          confirmation (--yes skips):
          1. writes the operation journal runtime/db-operation.json (fsynced) naming every container, volume and
             directory it will create, before creating any of them; an exclusive lock on runtime/db-operation.lock is
             held for the whole operation, and the kernel drops it when the process dies, however it dies;
          2. starts the OLD major (SOURCE_IMAGES, digest pinned) on the existing directory, with no network and no
             TCP listener; its socket lives in a throwaway Docker volume;
          3. dumps every database and role with the NEW major's pg_dumpall (the PostgreSQL rule: dump with the newer
             client), as the host user, into runtime/backups/postgres-<old>-to-<new>-<timestamp>/dumpall.sql;
          4. records, per database, every table's row count, every sequence's last_value and is_called, the
             extension names, and the roles with their attributes and a hash of their password verifier; then removes
             the old server and proves it is gone before going on;
          5. initialises the NEW major in runtime/volumes/postgres_data.pg<new>-<timestamp>.new and restores the
             dump with ON_ERROR_STOP (only `CREATE ROLE postgres;`, the role initdb made, is dropped); both servers
             run with log_min_error_statement=panic so a failing statement, which may carry data or a password
             hash, is not written to the container log;
          6. records the same facts on the new cluster and stops unless they are identical, then removes the new
             server and proves it is gone;
          7. marks the journal `swap`, renames postgres_data to postgres_data.pg<old>-<timestamp> and the new
             directory to postgres_data (a failed second rename is compensated by renaming the first back), writes
             runtime/backups/.../upgrade.json, and only then deletes the journal.
          Renames stay inside runtime/volumes/: on Linux the data belongs to uid 999, and a host user may rename such
          a directory within its parent but may not move it to another one.
rollback  same lock and journal: renames the current postgres_data aside (postgres_data.pg<new>-rolledback-<ts>)
          and the directory kept by the last upgrade back, then marks that upgrade record rolled back.
recover   finishes or rolls back an operation that a crash, a kill or a failure left in the journal (below).

Recovery (recover(), also run first by upgrade, rollback, reset and `up`): every container and volume named in the
journal is removed and proved gone (if that fails the journal stays and `up` refuses). Before the `swap` mark the
old directory was never touched, so the operation is rolled back: the journal is deleted and the half-built new
directory is left aside and named. After the mark the directories are inspected and the swap is finished
(roll-forward, the data was already verified); if it cannot be finished and the old directory is still in place,
it is rolled back instead. An empty postgres_data that `compose render` created during the gap is removed first.

The verification compares counts, sequence states, extension names and role attributes. It does not compare row
contents, and extensions are recreated at the new server's default version.

`up` calls recover_pending() and then preflight(): a pending operation is finished or rolled back, and a data
directory of another major, or one whose major cannot be read, stops `up` with exit 15 before Compose starts.

Runner: `runner(argv) -> (rc, stdout)`; tests inject a fake and never need Docker. Every container runs with
cap_drop ALL and no-new-privileges; the two servers add back only the capabilities of the `postgres` hardening
exception (manifest/hardening.json), because the official entrypoint starts as root and drops to postgres.
"""
from __future__ import annotations

import contextlib
import errno
import json
import os
import re
import shutil
import signal
import sys
import time
from pathlib import Path
from typing import Any, Callable, Iterator

from . import compose, exit_codes, health, report
from .context import Context
from .secrets import env_path, read_env

try:  # POSIX only; the supported hosts (macOS, Linux, WSL2) all have it
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]

SERVICE = "postgres"
VOLUME = "postgres_data"
DATA_TARGET = "/var/lib/postgresql/data"
SOCKET_DIR = "/var/run/postgresql"
BACKUP_TARGET = "/backup"
BACKUPS_DIR = "backups"
JOURNAL = "db-operation.json"
LOCK = "db-operation.lock"
# Majors this command can read. The image is the one the stack ran before ADR-12, pinned by its index digest.
SOURCE_IMAGES: dict[str, str] = {
    "9.6": "postgres:9.6@sha256:caddd35b05cdd56c614ab1f674e63be778e0abdf54e71a7507ff3e28d4902698",
}
SERVER_CAPS = ("CHOWN", "DAC_OVERRIDE", "FOWNER", "SETGID", "SETUID")  # = the postgres exception in manifest/hardening.json
POSTGRES_UID = "999:999"  # the postgres user of the Debian-based official images, 9.6 and 18 alike
BOOTSTRAP_ROLE_LINE = "CREATE ROLE postgres;"
READY_TIMEOUT = 600.0
MIB = 1024 * 1024
# Disk estimate (disk_problems). A logical dump is usually smaller than the cluster, but not always (bytea is written
# as hex, compressed TOAST values are written expanded), and dumpall.sql and restore.sql coexist until the restore
# ends: twice the cluster plus 64 MiB on the backups filesystem. The new cluster rebuilds every index and writes WAL
# up to max_wal_size (1 GiB by default): twice the cluster plus 1 GiB on the volumes filesystem. Both on one
# filesystem: the sum. This is an estimate, not a guarantee; a disk that fills anyway is a failure like any other.
BACKUP_FACTOR, BACKUP_MARGIN = 2, 64 * MIB
VOLUME_FACTOR, VOLUME_MARGIN = 2, 1024 * MIB
VERSION_RE = re.compile(r"^\d+(\.\d+)?$")
# Every table's row count, every sequence's last_value and is_called, and the extension names, by name; the same
# text on both majors (9.6 and 18). The casts matter: PostgreSQL 18 cannot choose an operator for text || "char"
# (measured), 9.6 could.
SNAPSHOT_SQL = (
    "SELECT n.nspname::text || '.' || c.relname::text || ' ' || c.relkind::text || ' ' || "
    "(xpath('/row/v/text()', query_to_xml(format(CASE c.relkind "
    "WHEN 'S' THEN 'SELECT last_value::text || '' '' || is_called::text AS v FROM %I.%I' "
    "ELSE 'SELECT count(*) AS v FROM %I.%I' END, n.nspname, c.relname), false, true, '')))[1]::text "
    "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
    "WHERE c.relkind IN ('r', 'S') AND n.nspname NOT IN ('pg_catalog', 'information_schema') "
    "AND n.nspname NOT LIKE 'pg_toast%' "
    "UNION ALL SELECT 'extension ' || extname::text FROM pg_extension ORDER BY 1"
)
DATABASES_SQL = "SELECT datname FROM pg_database WHERE datallowconn AND NOT datistemplate ORDER BY 1"
# Role attributes and a hash of the password verifier (the verifier itself is never printed).
ROLES_SQL = (
    "SELECT rolname::text || ' ' || rolsuper::text || ' ' || rolinherit::text || ' ' || rolcreaterole::text || ' ' || "
    "rolcreatedb::text || ' ' || rolcanlogin::text || ' ' || rolreplication::text || ' ' || rolbypassrls::text || ' ' || "
    "rolconnlimit::text || ' ' || md5(coalesce(rolpassword, '')) FROM pg_authid WHERE rolname !~ '^pg_' ORDER BY 1"
)
QUIET_SERVER = ("-c", "listen_addresses=", "-c", "log_min_error_statement=panic")

Runner = Callable[[list[str]], tuple[int, str]]


class UpgradeError(Exception):
    """A step failed; the message says which."""


def register(subparsers) -> None:
    p = subparsers.add_parser("db", help="PostgreSQL data directory: status, upgrade to the rendered major, rollback, recover")
    sub = p.add_subparsers(dest="db_command", metavar="<action>")
    sub.add_parser("status", help="show both majors and any pending operation; changes nothing")
    sub.add_parser("upgrade", help="dump and restore runtime/volumes/postgres_data into the rendered major; keeps the old directory; exit 15 on failure")
    sub.add_parser("rollback", help="put the directory kept by the last upgrade back in place; exit 15 on failure")
    sub.add_parser("recover", help="finish or roll back an interrupted upgrade or rollback; exit 15 if it cannot")
    p.set_defaults(_module=sys.modules[__name__])


# --------------------------------------------------------------------------- facts


def image_major(image: str | None) -> str | None:
    """`postgres:18.6@sha256:…` → "18", `postgres:9.6` → "9.6" (before 10 a major had two parts). None if no tag."""
    if not image:
        return None
    ref = image.split("@", 1)[0]
    name, _, tag = ref.rpartition(":")
    if not name or "/" in tag:
        return None
    m = re.match(r"^(\d+)(?:\.(\d+))?", tag)
    if not m:
        return None
    first = int(m.group(1))
    if first < 10:
        return f"{first}.{m.group(2)}" if m.group(2) is not None else None
    return str(first)


def data_dir(ctx: Context) -> Path:
    return ctx.runtime / compose.VOLUMES_DIR / VOLUME


def journal_path(ctx: Context) -> Path:
    return ctx.runtime / JOURNAL


def rendered_service(ctx: Context) -> dict[str, Any] | None:
    try:
        data = health.load_compose(health.compose_path(ctx))
    except (OSError, ValueError):
        return None
    return (data.get("services") or {}).get(SERVICE)


def data_major(directory: Path, runner: Runner | None = None, image: str | None = None, platform: str | None = None) -> str | None:
    """The major written in PG_VERSION; "" only when the directory is absent or empty (no cluster yet); None when
    it cannot be established (unreadable, a non-empty directory without PG_VERSION, or an unparseable value).

    On Linux the directory belongs to uid 999 with mode 0700, so the host user cannot read it; then it is read by the
    postgres uid in a throwaway container of `image`, with no network and nothing writable."""
    try:
        if not directory.exists():
            return ""
        value = (directory / "PG_VERSION").read_text(encoding="ascii").strip()
        return value if VERSION_RE.match(value) else None
    except ValueError:  # UnicodeDecodeError: bytes that are not ASCII are not a version (PR #42 review r2 R2-04)
        return None
    except FileNotFoundError:
        try:
            return "" if not any(directory.iterdir()) else None
        except OSError:
            pass
    except (PermissionError, NotADirectoryError):
        pass
    except OSError:
        return None
    if runner is None or not image:
        return None
    argv = ["docker", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges:true", "--user", POSTGRES_UID]
    if platform:
        argv += ["--platform", platform]
    argv += ["-v", f"{directory}:/data:ro", "--entrypoint", "sh", image, "-c",
             'if [ -e /data/PG_VERSION ]; then cat /data/PG_VERSION; elif [ -z "$(ls -A /data)" ]; then echo empty; '
             "else echo nocluster; fi"]
    try:
        rc, out = runner(argv)
    except ValueError:  # output that does not decode
        return None
    value = out.strip() if rc == 0 else ""
    if value == "empty":
        return ""
    return value if VERSION_RE.match(value) else None


def preflight(ctx: Context, runner: Runner | None = None) -> str | None:
    """Why `up` must not start postgres on the current data directory, or None. Fails closed: a major that cannot be
    read is a refusal, not a pass (PR #42 review r1 R1-04)."""
    svc = rendered_service(ctx)
    if not svc:
        return None
    want = image_major(svc.get("image"))
    if not want:
        return None  # not a postgres:<major> image; nothing to compare against
    have = data_major(data_dir(ctx), runner, svc.get("image"), svc.get("platform"))
    if have is None:
        return (f"cannot read the PostgreSQL major of {data_dir(ctx)} (PG_VERSION unreadable or missing in a non-empty "
                f"directory); refusing to start it with PostgreSQL {want}; see `grdm-dev db status`")
    if have and have != want:
        return (f"{data_dir(ctx)} was written by PostgreSQL {have} but the rendered image is PostgreSQL {want}; "
                f"run `grdm-dev db upgrade` (it keeps the old directory), or check out the revision that matches the data")
    return None


def tree_size(directory: Path, runner: Runner | None = None, image: str | None = None, platform: str | None = None) -> int | None:
    """Bytes allocated under `directory`; read by uid 999 in a container when the host user cannot walk it."""
    total = 0
    try:
        for root, dirs, files in os.walk(directory, onerror=_raise):
            for name in files + dirs:
                try:
                    total += os.lstat(os.path.join(root, name)).st_blocks * 512
                except FileNotFoundError:
                    continue
        return total
    except OSError:
        pass
    if runner is None or not image:
        return None
    argv = ["docker", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges:true", "--user", POSTGRES_UID]
    if platform:
        argv += ["--platform", platform]
    rc, out = runner(argv + ["-v", f"{directory}:/data:ro", "--entrypoint", "du", image, "-sk", "/data"])
    try:
        return int(out.split()[0]) * 1024 if rc == 0 else None
    except (IndexError, ValueError):
        return None


def _raise(exc: OSError) -> None:
    raise exc


def disk_problems(size: int, backups: Path, volumes: Path, disk_usage=shutil.disk_usage) -> list[str]:
    """Free space needed before anything starts (see the estimate at BACKUP_FACTOR)."""
    need_backup = BACKUP_FACTOR * size + BACKUP_MARGIN
    need_volume = VOLUME_FACTOR * size + VOLUME_MARGIN
    try:
        same = backups.stat().st_dev == volumes.stat().st_dev
        free_backup, free_volume = disk_usage(backups).free, disk_usage(volumes).free
    except OSError as exc:
        return [f"cannot measure free disk space: {exc}"]
    mib = lambda n: f"{n // MIB} MiB"  # noqa: E731
    if same and free_volume < need_backup + need_volume:
        return [f"{volumes} needs {mib(need_backup + need_volume)} free for the dump and the new cluster "
                f"(the cluster is {mib(size)}), has {mib(free_volume)}"]
    problems = []
    if not same and free_backup < need_backup:
        problems.append(f"{backups} needs {mib(need_backup)} free for the dump, has {mib(free_backup)}")
    if not same and free_volume < need_volume:
        problems.append(f"{volumes} needs {mib(need_volume)} free for the new cluster, has {mib(free_volume)}")
    return problems


# --------------------------------------------------------------------------- journal and lock


# A filesystem that cannot sync a directory says so with one of these; that is not a failed write.
UNSYNCABLE = {errno.EINVAL, getattr(errno, "ENOTSUP", errno.EINVAL), getattr(errno, "EOPNOTSUPP", errno.EINVAL)}


def _fsync_dir(path: Path) -> None:
    """Make renames and unlinks in `path` durable. Any other error propagates (PR #42 review r2 R2-03): an entry
    that may not be on disk must not be reported as done."""
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    except OSError as exc:
        if exc.errno not in UNSYNCABLE:
            raise
    finally:
        os.close(fd)


def write_durable(path: Path, data: dict[str, Any]) -> None:
    """Write JSON so that after a crash the file is either the old or the new version, complete (fsync + rename)."""
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    _fsync_dir(path.parent)


def read_journal(ctx: Context) -> dict[str, Any] | None:
    path = journal_path(ctx)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise UpgradeError(f"{path} cannot be read ({exc}); inspect it and runtime/volumes/ by hand") from exc
    if not isinstance(data, dict) or data.get("op") not in ("upgrade", "rollback"):
        raise UpgradeError(f"{path} is not a db operation journal; inspect it by hand")
    return data


def _drop_journal(ctx: Context) -> None:
    journal_path(ctx).unlink(missing_ok=True)
    _fsync_dir(ctx.runtime)


LOCK_HELD = "another grdm-dev command (db upgrade, rollback, recover, up or reset) holds runtime/db-operation.lock; wait for it"


def _acquire(ctx: Context) -> tuple[int | None, str | None]:
    """(fd, None) with the exclusive lock held, or (None, refusal). The lock is a flock on its own open file
    description, so it also excludes a second open in the same process, and the kernel drops it when the process
    ends, however it ends."""
    ctx.runtime.mkdir(parents=True, exist_ok=True)
    fd = os.open(ctx.runtime / LOCK, os.O_RDWR | os.O_CREAT, 0o600)
    if fcntl is not None:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            return None, LOCK_HELD
    return fd, None


@contextlib.contextmanager
def operation_lock(ctx: Context) -> Iterator[None]:
    """Exclusive, non-blocking; raises UpgradeError when held elsewhere."""
    fd, refusal = _acquire(ctx)
    if refusal:
        raise UpgradeError(refusal)
    try:
        yield
    finally:
        os.close(fd)


@contextlib.contextmanager
def signals_interrupt() -> Iterator[None]:
    """SIGTERM and SIGHUP raise KeyboardInterrupt like Ctrl-C, so the cleanup path runs for all three."""
    def handler(signum, frame):  # noqa: ARG001
        raise KeyboardInterrupt(f"signal {signum}")

    saved = {}
    for sig in (signal.SIGTERM, signal.SIGHUP):
        try:
            saved[sig] = signal.signal(sig, handler)
        except (ValueError, OSError):  # not the main thread
            pass
    try:
        yield
    finally:
        for sig, old in saved.items():
            signal.signal(sig, old)


# --------------------------------------------------------------------------- docker argv


def _auth_method(env: dict[str, str]) -> str:
    """The host auth method a fresh install gets: initdb's --auth-host (which also sets password_encryption)."""
    m = re.search(r"--auth-host[= ](\S+)", env.get("POSTGRES_INITDB_ARGS", ""))
    return m.group(1) if m else "scram-sha-256"


def server_argv(name: str, image: str, directory: Path, socket_volume: str, *, platform: str | None,
                env: dict[str, str], command: list[str], tmpfs: list[str], backup: Path | None = None,
                env_file: Path | None = None) -> list[str]:
    argv = ["docker", "run", "-d", "--name", name, "--network", "none", "--read-only",
            "--cap-drop", "ALL", *[x for cap in SERVER_CAPS for x in ("--cap-add", cap)],
            "--security-opt", "no-new-privileges:true", "--label", "org.gakunin-rdm.component=postgres-upgrade"]
    if platform:
        argv += ["--platform", platform]
    for path in tmpfs:
        argv += ["--tmpfs", path]
    argv += ["-v", f"{directory}:{DATA_TARGET}", "-v", f"{socket_volume}:{SOCKET_DIR}"]
    if backup is not None:
        argv += ["-v", f"{backup}:{BACKUP_TARGET}:ro"]
    for key, value in env.items():
        argv += ["-e", f"{key}={value}"]
    if env_file is not None:
        argv += ["--env-file", str(env_file)]  # the password never appears in argv
    # No TCP listener at all, and no failing statement (it may hold data or a password hash) in the server log.
    return argv + [image, *command, *QUIET_SERVER]


def exec_argv(name: str, *cmd: str) -> list[str]:
    # root in the container keeps DAC_OVERRIDE, so it reads a 0700 backup directory owned by the host user
    return ["docker", "exec", "-u", "0", name, *cmd]


def psql_argv(name: str, database: str, sql: str) -> list[str]:
    return exec_argv(name, "psql", "-X", "-q", "-A", "-t", "-v", "ON_ERROR_STOP=1", "-h", SOCKET_DIR, "-U", "postgres", "-d", database, "-c", sql)


def dump_argv(image: str, socket_volume: str, backup: Path, platform: str | None, user: str) -> list[str]:
    argv = ["docker", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges:true", "--user", user]
    if platform:
        argv += ["--platform", platform]
    return argv + ["-v", f"{socket_volume}:{SOCKET_DIR}", "-v", f"{backup}:{BACKUP_TARGET}",
                   "--entrypoint", "pg_dumpall", image, "-h", SOCKET_DIR, "-U", "postgres", "-f", f"{BACKUP_TARGET}/dumpall.sql"]


# --------------------------------------------------------------------------- containers


def container_present(name: str, runner: Runner) -> bool:
    """True if a container of that name exists (running or not). Raises when Docker cannot answer: unknown is not absent."""
    rc, out = runner(["docker", "ps", "-a", "--filter", f"name=^/{name}$", "--format", "{{.Names}}"])
    if rc != 0:
        raise UpgradeError(f"cannot list containers (docker ps exited {rc}); {name} may still run")
    return name in out.split()


def remove_container(name: str, runner: Runner) -> None:
    """Stop and remove, then prove it is gone (PR #42 review r1 R1-02); a server still holding a data directory
    must never be forgotten."""
    if not container_present(name, runner):
        return
    runner(["docker", "stop", "-t", "60", name])
    runner(["docker", "rm", "-f", name])
    if container_present(name, runner):
        raise UpgradeError(f"container {name} could not be stopped and removed; remove it with `docker rm -f {name}`, "
                           f"then run `grdm-dev db recover`")


def wait_ready(name: str, runner: Runner, sleep: Callable[[float], None], timeout: float = READY_TIMEOUT, interval: float = 2.0) -> None:
    """Ready = the final server is PID 1 (the entrypoint's temporary init server never is) and accepts connections."""
    probe = 'p=$(head -n1 "$PGDATA/postmaster.pid" 2>/dev/null); [ "$p" = 1 ] && pg_isready -q -h ' + SOCKET_DIR
    waited = 0.0
    while True:
        rc, out = runner(["docker", "inspect", "-f", "{{.State.Running}}", name])
        if rc != 0 or out.strip() != "true":
            raise UpgradeError(f"container {name} is not running")
        rc, _ = runner(exec_argv(name, "sh", "-c", probe))
        if rc == 0:
            return
        if waited >= timeout:
            raise UpgradeError(f"container {name} not ready after {int(timeout)}s")
        sleep(interval)
        waited += interval


def snapshot(name: str, runner: Runner) -> dict[str, Any]:
    """{"databases": {database: sorted lines}, "roles": [lines]}: two namespaces, so a database called `roles` keeps
    its own check (R1-05). Equal snapshots mean equal row counts, sequence states (last_value and is_called),
    extension names and role attributes; they do not prove equal row contents."""
    rc, out = runner(psql_argv(name, "postgres", DATABASES_SQL))
    if rc != 0:
        raise UpgradeError(f"listing databases in {name} failed (psql exited {rc})")
    databases: dict[str, list[str]] = {}
    for db in [line.strip() for line in out.splitlines() if line.strip()]:
        rc, rows = runner(psql_argv(name, db, SNAPSHOT_SQL))
        if rc != 0:
            raise UpgradeError(f"counting rows of {db} in {name} failed (psql exited {rc})")
        databases[db] = [line for line in rows.splitlines() if line.strip()]
    rc, out = runner(psql_argv(name, "postgres", ROLES_SQL))
    if rc != 0:
        raise UpgradeError(f"listing roles in {name} failed (psql exited {rc})")
    return {"databases": databases, "roles": [line for line in out.splitlines() if line.strip()]}


def snapshot_differences(old: dict[str, Any], new: dict[str, Any]) -> list[str]:
    diffs: list[str] = []
    od, nd = old.get("databases", {}), new.get("databases", {})
    for db in sorted(set(od) | set(nd)):
        if db not in nd:
            diffs.append(f"database {db}: missing after restore")
        elif db not in od:
            diffs.append(f"database {db}: new after restore")
        else:
            a, b = set(od[db]), set(nd[db])
            diffs += [f"database {db}: before `{x}`" for x in sorted(a - b)[:5]] + [f"database {db}: after `{x}`" for x in sorted(b - a)[:5]]
    ro, rn = set(old.get("roles", [])), set(new.get("roles", []))
    diffs += [f"role before `{x.split()[0]} …`" for x in sorted(ro - rn)[:5]] + [f"role after `{x.split()[0]} …`" for x in sorted(rn - ro)[:5]]
    return diffs


def write_restore_file(dump: Path, restore: Path) -> int:
    """Copy the dump without the bootstrap role's CREATE (initdb made it; its ALTER with the password stays)."""
    removed = 0
    fd = os.open(restore, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with dump.open(encoding="utf-8") as src, os.fdopen(fd, "w", encoding="utf-8") as dst:
        for line in src:
            if line.rstrip("\n") == BOOTSTRAP_ROLE_LINE:
                removed += 1
                continue
            dst.write(line)
    if removed != 1:
        raise UpgradeError(f"expected one `{BOOTSTRAP_ROLE_LINE}` in {dump}, found {removed}")
    return removed


def _no_running_services(ctx: Context, runner: Runner) -> str | None:
    from . import lifecycle

    try:
        running = lifecycle.running_services(ctx, runner)
    except RuntimeError as exc:
        return f"cannot tell whether the project is running ({exc})"
    if running:
        return f"services are running ({', '.join(sorted(running))}); run `grdm-dev down` first"
    return None


def latest_record(ctx: Context) -> tuple[Path, dict[str, Any]] | None:
    """The newest upgrade record that has not been rolled back."""
    base = ctx.runtime / BACKUPS_DIR
    records = sorted(base.glob("postgres-*/upgrade.json")) if base.is_dir() else []
    for path in reversed(records):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not data.get("rolled_back_at"):
            return path, data
    return None


# --------------------------------------------------------------------------- recovery


def _major_of(path: Path, runner: Runner, journal: dict[str, Any]) -> str | None:
    return data_major(path, runner, journal.get("image"), journal.get("platform"))


def _drop_empty_placeholder(current: Path, runner: Runner, journal: dict[str, Any]) -> None:
    """`compose render` creates a missing volume directory; while a swap is pending that empty directory is not data."""
    if current.is_dir() and _major_of(current, runner, journal) == "":
        try:
            current.rmdir()
        except OSError as exc:
            raise UpgradeError(f"{current} is an empty placeholder that cannot be removed ({exc})") from exc


def _write_record(journal: dict[str, Any]) -> Path:
    record = Path(journal["backup"]) / "upgrade.json"
    if not record.exists():
        write_durable(record, {k: journal[k] for k in ("from", "to", "source_image", "image", "data_dir", "kept", "dump", "at", "steps") if k in journal})
    return record


def recover(ctx: Context, runner: Runner) -> str | None:
    """Finish or roll back the journalled operation; None when nothing was pending. Raises UpgradeError (journal
    kept) when it can do neither safely. The caller holds the lock."""
    journal = read_journal(ctx)
    if journal is None:
        return None
    for name in journal.get("containers", []):
        remove_container(name, runner)
    if journal.get("volume"):
        runner(["docker", "volume", "rm", journal["volume"]])  # a leftover socket volume holds no data
    current = Path(journal["data_dir"])
    if journal["op"] == "upgrade":
        new_dir, kept = Path(journal["new_dir"]), Path(journal["kept"])
        if journal.get("phase") != "swap":
            if not current.is_dir() or kept.exists():
                raise UpgradeError(f"journal says the swap had not started, but {current} is missing or {kept} exists; inspect by hand")
            _drop_journal(ctx)
            left = f"; the unfinished {new_dir} can be deleted" if new_dir.exists() else ""
            return f"rolled back an interrupted upgrade before its swap: {current} is the untouched PostgreSQL {journal['from']} cluster{left}"
        _drop_empty_placeholder(current, runner, journal)
        if not current.exists() and kept.is_dir() and new_dir.is_dir():
            try:
                _rename_durably(new_dir, current)
            except OSError as exc:
                _rename_durably(kept, current)  # back to the old cluster; if this raises the journal stays
                _undone(ctx, runner, journal, current, journal["from"], exc)
                return f"the swap could not be finished; {current} is the old PostgreSQL {journal['from']} cluster again, {new_dir} is left aside"
        elif current.is_dir() and not kept.exists() and new_dir.is_dir() and _major_of(current, runner, journal) == journal["from"]:
            try:
                _swap(current, new_dir, kept)
            except OSError as exc:
                _undone(ctx, runner, journal, current, journal["from"], exc)
                return f"the swap could not be done ({exc}); {current} is the old PostgreSQL {journal['from']} cluster, {new_dir} is left aside"
        elif not (current.is_dir() and kept.is_dir() and not new_dir.exists() and _major_of(current, runner, journal) == journal["to"]):
            raise UpgradeError(f"cannot tell how far the swap went ({current}, {kept}, {new_dir}); inspect by hand")
        _fsync_dir(current.parent)  # the renames are on disk before the record and the journal say so
        _write_record(journal)
        _drop_journal(ctx)
        return f"finished an interrupted upgrade: {current} is PostgreSQL {journal['to']}, the old cluster is {kept}"
    aside, kept = Path(journal["aside"]), Path(journal["kept"])
    _drop_empty_placeholder(current, runner, journal)
    if current.is_dir() and kept.is_dir() and not aside.exists():
        try:
            _swap(current, kept, aside)
        except OSError as exc:
            _undone(ctx, runner, journal, current, journal["to"], exc)
            return f"the rollback could not be done ({exc}); {current} is unchanged"
    elif not current.exists() and aside.is_dir() and kept.is_dir():
        _rename_durably(kept, current)
    elif not (current.is_dir() and aside.is_dir() and not kept.exists()):
        raise UpgradeError(f"cannot tell how far the rollback went ({current}, {kept}, {aside}); inspect by hand")
    _fsync_dir(current.parent)
    _mark_rolled_back(journal)
    _drop_journal(ctx)
    return f"finished an interrupted rollback: {current} is PostgreSQL {journal['from']} again"


def _rename_durably(src: Path, dst: Path) -> None:
    os.rename(src, dst)
    _fsync_dir(dst.parent)


def _undone(ctx: Context, runner: Runner, journal: dict[str, Any], current: Path, major: str, exc: OSError) -> None:
    """A swap failed. Retire the journal only when the directory state proves the compensation worked: `current`
    is there, holds `major`, and is on disk. Otherwise the journal stays and the error propagates (R2-01)."""
    if current.is_dir() and _major_of(current, runner, journal) == major:
        _fsync_dir(current.parent)
        _drop_journal(ctx)
        return
    raise UpgradeError(f"a swap failed ({exc}) and so did putting {current} back; the journal is kept, "
                       f"`up` refuses, and `grdm-dev db recover` retries") from exc


def _swap(current: Path, replacement: Path, aside: Path) -> None:
    """current → aside, replacement → current; a failed second rename puts the first back."""
    os.rename(current, aside)
    try:
        os.rename(replacement, current)
    except OSError:
        os.rename(aside, current)  # if this raises too, `current` is missing and the caller must keep the journal
        _fsync_dir(current.parent)
        raise
    _fsync_dir(current.parent)


def _mark_rolled_back(journal: dict[str, Any]) -> None:
    record = Path(journal["record"])
    try:
        data = json.loads(record.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    data["rolled_back_at"] = journal["at"]
    write_durable(record, data)


def recover_pending(ctx: Context, runner: Runner) -> str | None:
    """For `up` and `reset`, called while they hold operation_lock: finish or roll back a pending operation.
    Returns a refusal, or None."""
    try:
        outcome = recover(ctx, runner)
    except (UpgradeError, OSError) as exc:
        return f"an interrupted `grdm-dev db` operation could not be recovered: {exc}"
    if outcome:
        sys.stderr.write(f"[grdm-dev] {outcome}\n")
    return None


@contextlib.contextmanager
def lifecycle_lock(ctx: Context) -> Iterator[str | None]:
    """`up` and `reset` hold the same lock as `db upgrade/rollback/recover` from their checks through starting or
    deleting (PR #42 review r2 R2-02), so neither can run between the other's checks and its action. Yields a
    refusal when another command holds it, else None while holding it."""
    fd, refusal = _acquire(ctx)
    try:
        yield refusal
    finally:
        if fd is not None:
            os.close(fd)


# --------------------------------------------------------------------------- commands


def run(ctx: Context, args, runner: Runner | None = None, sleep: Callable[[float], None] | None = None,
        user: str | None = None, stamp: str | None = None, disk_usage=shutil.disk_usage) -> int:
    action = getattr(args, "db_command", None)
    runner = runner or health.default_runner
    if action == "status":
        return run_status(ctx, runner)
    if action == "upgrade":
        return run_upgrade(ctx, runner, sleep or time.sleep, user=user, stamp=stamp, disk_usage=disk_usage)
    if action == "rollback":
        return run_rollback(ctx, runner, stamp=stamp)
    if action == "recover":
        return run_recover(ctx, runner)
    return report.error(ctx, exit_codes.USAGE, "choose status, upgrade, rollback or recover")


def _target(ctx: Context) -> tuple[dict[str, Any] | None, str | None]:
    svc = rendered_service(ctx)
    if svc is None:
        return None, f"{health.compose_path(ctx)} has no `{SERVICE}` service; run `grdm-dev compose render` first"
    if not image_major(svc.get("image")):
        return None, f"cannot tell the PostgreSQL major of the rendered image {svc.get('image')!r}"
    return svc, None


def run_status(ctx: Context, runner: Runner) -> int:
    svc, problem = _target(ctx)
    if problem:
        return report.error(ctx, exit_codes.USAGE, problem)
    want = image_major(svc.get("image"))
    try:
        pending = read_journal(ctx)
    except UpgradeError as exc:
        pending = {"op": "unreadable", "phase": str(exc)}
    have = data_major(data_dir(ctx), runner, svc.get("image"), svc.get("platform"))
    state = "empty" if have == "" else "unknown" if have is None else "current" if have == want else "upgrade-needed"
    record = latest_record(ctx)
    report.emit(ctx, "db_status", {
        "data_dir": str(data_dir(ctx)), "data_major": have, "image": svc.get("image"), "image_major": want, "state": state,
        "upgradable": state == "upgrade-needed" and have in SOURCE_IMAGES,
        "pending_operation": f"{pending['op']} ({pending.get('phase')})" if pending else None,
        "last_upgrade": str(record[0].parent) if record else None,
    })
    return exit_codes.OK


def run_recover(ctx: Context, runner: Runner) -> int:
    try:
        with operation_lock(ctx):
            outcome = recover(ctx, runner)
    except (UpgradeError, OSError) as exc:
        return report.error(ctx, exit_codes.DB_UPGRADE_FAILED, f"recovery failed: {exc}; the journal {journal_path(ctx)} is kept")
    report.emit(ctx, "db_recover", {"pending": outcome is not None, "outcome": outcome})
    return exit_codes.OK


def run_upgrade(ctx: Context, runner: Runner, sleep: Callable[[float], None], user: str | None = None,
                stamp: str | None = None, disk_usage=shutil.disk_usage) -> int:
    svc, problem = _target(ctx)
    if problem:
        return report.error(ctx, exit_codes.USAGE, problem)
    try:
        with operation_lock(ctx):
            return _upgrade_locked(ctx, svc, runner, sleep, user, stamp, disk_usage)
    except UpgradeError as exc:
        return report.error(ctx, exit_codes.DB_UPGRADE_FAILED, str(exc))


def _upgrade_locked(ctx: Context, svc: dict[str, Any], runner: Runner, sleep: Callable[[float], None],
                    user: str | None, stamp: str | None, disk_usage) -> int:
    recovered = recover(ctx, runner)
    if recovered:
        sys.stderr.write(f"[grdm-dev] {recovered}\n")
    image, platform = str(svc["image"]), svc.get("platform")
    want = image_major(image)
    current = data_dir(ctx)
    bad = compose.volume_path_problems(ctx.root, ctx.runtime, [VOLUME])
    if bad:
        raise UpgradeError("unsafe volume path: " + "; ".join(bad))
    have = data_major(current, runner, image, platform)
    if have is None:
        raise UpgradeError(f"cannot read the PostgreSQL major of {current}")
    if have in ("", want):
        report.emit(ctx, "db_upgrade", {"data_dir": str(current), "data_major": have or None, "image_major": want,
                                        "changed": False, "recovered": recovered,
                                        "reason": "no cluster yet" if have == "" else "already current"})
        return exit_codes.OK
    source = SOURCE_IMAGES.get(have)
    if not source:
        raise UpgradeError(f"no source image for PostgreSQL {have}; known: {', '.join(SOURCE_IMAGES)}")
    password = read_env(env_path(ctx)).get("POSTGRES_PASSWORD")
    if not password:
        return report.error(ctx, exit_codes.USAGE, f"{env_path(ctx)} has no POSTGRES_PASSWORD; run `grdm-dev secrets init` first")
    busy = _no_running_services(ctx, runner)
    if busy:
        raise UpgradeError(busy)
    backups = ctx.runtime / BACKUPS_DIR
    backups.mkdir(parents=True, exist_ok=True)
    size = tree_size(current, runner, image, platform)
    if size is None:
        raise UpgradeError(f"cannot measure the size of {current}")
    space = disk_problems(size, backups, current.parent, disk_usage)
    if space:
        raise UpgradeError("not enough free disk: " + "; ".join(space) + " (an estimate; see ADR-12 §5)")
    if not ctx.confirm(f"Dump {current} (PostgreSQL {have}) and restore it into PostgreSQL {want}? The old directory is kept.", default=False):
        if not ctx.yes and not ctx.stdin_is_tty:
            return report.error(ctx, exit_codes.USAGE, "db upgrade needs a confirmation; add --yes when no terminal is attached")
        sys.stderr.write("[grdm-dev] db upgrade cancelled\n")
        return exit_codes.OK

    ts = stamp or report.timestamp()
    backup = backups / f"postgres-{have}-to-{want}-{ts}"
    journal: dict[str, Any] = {
        "op": "upgrade", "phase": "prepare", "at": ts, "from": have, "to": want, "source_image": source, "image": image,
        "platform": platform, "data_dir": str(current), "new_dir": str(current.with_name(f"{VOLUME}.pg{want}-{ts}.new")),
        "kept": str(current.with_name(f"{VOLUME}.pg{have}-{ts}")), "backup": str(backup), "dump": str(backup / "dumpall.sql"),
        "containers": [f"grdm-dev-dbupgrade-old-{ts}", f"grdm-dev-dbupgrade-new-{ts}"],
        "volume": f"grdm-dev-dbupgrade-{ts}".lower(), "steps": [],
    }
    try:
        write_durable(journal_path(ctx), journal)
    except OSError as exc:
        journal_path(ctx).unlink(missing_ok=True)
        raise UpgradeError(f"cannot write the journal ({exc}); nothing was started") from exc
    try:
        with signals_interrupt():
            _upgrade_steps(ctx, svc, journal, runner, sleep, user or f"{os.getuid()}:{os.getgid()}", password)
    except (UpgradeError, OSError, KeyboardInterrupt) as exc:
        reason = "interrupted" if isinstance(exc, KeyboardInterrupt) else str(exc)
        try:
            outcome = recover(ctx, runner)
        except (UpgradeError, OSError) as again:
            report.emit(ctx, "db_upgrade", {"changed": False, "failed": reason, "steps": journal["steps"], "recovery": f"failed: {again}"})
            return report.error(ctx, exit_codes.DB_UPGRADE_FAILED,
                                f"{reason}; recovery failed ({again}); the journal {journal_path(ctx)} is kept and `up` refuses until "
                                f"`grdm-dev db recover` succeeds")
        report.emit(ctx, "db_upgrade", {"changed": False, "failed": reason, "steps": journal["steps"], "recovery": outcome})
        return report.error(ctx, exit_codes.DB_UPGRADE_FAILED, f"{reason}; {outcome}")
    report.emit(ctx, "db_upgrade", {"changed": True, **{k: journal[k] for k in ("from", "to", "source_image", "image", "data_dir", "kept", "dump", "at", "steps")}})
    sys.stderr.write(f"[grdm-dev] PostgreSQL {have} → {want} done; the old directory is {journal['kept']}; run `grdm-dev up`\n")
    return exit_codes.OK


def _upgrade_steps(ctx: Context, svc: dict[str, Any], journal: dict[str, Any], runner: Runner,
                   sleep: Callable[[float], None], user: str, password: str) -> None:
    image, platform = journal["image"], journal.get("platform")
    current, new_dir, kept = Path(journal["data_dir"]), Path(journal["new_dir"]), Path(journal["kept"])
    backup = Path(journal["backup"])
    old_name, new_name = journal["containers"]
    socket_volume = journal["volume"]
    env = {k: str(v) for k, v in (svc.get("environment") or {}).items() if k in ("POSTGRES_INITDB_ARGS", "PGDATA")}
    command = [str(c) for c in (svc.get("command") or ["postgres"])]
    tmpfs = [str(t).split(":", 1)[0] for t in (svc.get("tmpfs") or []) if not str(t).startswith(SOCKET_DIR)]

    def step(name: str, **detail: Any) -> None:
        journal["steps"].append({"step": name, "status": "ok", **detail})
        sys.stderr.write(f"[grdm-dev] db upgrade: {name}\n")

    backup.mkdir(mode=0o700)
    os.chmod(backup, 0o700)  # nosemgrep: python.lang.security.audit.insecure-file-permissions.insecure-file-permissions -- owner-only is the intended restriction
    new_dir.mkdir(mode=0o755)
    rc, _ = runner(["docker", "volume", "create", "--label", "org.gakunin-rdm.component=postgres-upgrade", socket_volume])
    if rc != 0:
        raise UpgradeError(f"docker volume create exited {rc}")
    rc, _ = runner(server_argv(old_name, journal["source_image"], current, socket_volume, platform=platform,
                               env={"PGDATA": DATA_TARGET}, command=["postgres"], tmpfs=["/tmp"]))
    if rc != 0:
        raise UpgradeError(f"starting PostgreSQL {journal['from']} exited {rc}")
    wait_ready(old_name, runner, sleep)
    step("start-old", image=journal["source_image"])
    before = snapshot(old_name, runner)
    step("count-old", databases=sorted(before["databases"]))
    rc, _ = runner(dump_argv(image, socket_volume, backup, platform, user))
    dump = backup / "dumpall.sql"
    if rc != 0 or not dump.is_file():
        raise UpgradeError(f"pg_dumpall exited {rc}")
    os.chmod(dump, 0o600)  # it holds the roles' password hashes
    step("dump", file=str(dump), bytes=dump.stat().st_size)
    remove_container(old_name, runner)
    step("stop-old")
    restore = backup / "restore.sql"
    write_restore_file(dump, restore)
    new_env = {**env, "POSTGRES_HOST_AUTH_METHOD": _auth_method(env)}
    # initdb needs a superuser password; the restore then sets the dumped verifier. It goes through a 0600 file in
    # the 0700 backup directory, removed as soon as the container exists.
    secret = backup / ".initdb.env"
    fd = os.open(secret, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(f"POSTGRES_PASSWORD={password}\n")
    try:
        rc, _ = runner(server_argv(new_name, image, new_dir, socket_volume, platform=platform, env=new_env,
                                   command=command, tmpfs=tmpfs, backup=backup, env_file=secret))
    finally:
        secret.unlink(missing_ok=True)
    if rc != 0:
        raise UpgradeError(f"starting PostgreSQL {journal['to']} exited {rc}")
    wait_ready(new_name, runner, sleep)
    step("init-new", image=image, directory=str(new_dir))
    rc, _ = runner(exec_argv(new_name, "psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-h", SOCKET_DIR, "-U", "postgres",
                             "-d", "postgres", "-f", f"{BACKUP_TARGET}/restore.sql"))
    if rc != 0:
        raise UpgradeError(f"restore exited {rc}")
    rc, _ = runner(exec_argv(new_name, "vacuumdb", "-q", "-h", SOCKET_DIR, "-U", "postgres", "--all", "--analyze-only"))
    if rc != 0:
        raise UpgradeError(f"vacuumdb --analyze-only exited {rc}")
    restore.unlink(missing_ok=True)  # derived from dumpall.sql, which stays
    step("restore")
    after = snapshot(new_name, runner)
    diffs = snapshot_differences(before, after)
    if diffs:
        raise UpgradeError("restored data differs: " + "; ".join(diffs[:10]))
    rows = sum(len(v) for v in after["databases"].values())
    step("verify", objects_compared=rows, databases=sorted(after["databases"]), roles=len(after["roles"]))
    remove_container(new_name, runner)
    runner(["docker", "volume", "rm", socket_volume])
    step("stop-new")
    journal["phase"] = "swap"
    write_durable(journal_path(ctx), journal)  # from here on, recovery finishes the swap
    _swap(current, new_dir, kept)
    step("swap", kept=str(kept))
    write_durable(journal_path(ctx), journal)
    _write_record(journal)
    _drop_journal(ctx)


def run_rollback(ctx: Context, runner: Runner, stamp: str | None = None) -> int:
    try:
        with operation_lock(ctx):
            return _rollback_locked(ctx, runner, stamp)
    except (UpgradeError, OSError) as exc:
        return report.error(ctx, exit_codes.DB_UPGRADE_FAILED, str(exc))


def _rollback_locked(ctx: Context, runner: Runner, stamp: str | None) -> int:
    recovered = recover(ctx, runner)
    if recovered:
        sys.stderr.write(f"[grdm-dev] {recovered}\n")
    found = latest_record(ctx)
    if not found:
        raise UpgradeError(f"no upgrade record under {ctx.runtime / BACKUPS_DIR}")
    path, record = found
    current = data_dir(ctx)
    kept = current.with_name(Path(str(record.get("kept", ""))).name)
    if not record.get("kept") or not kept.is_dir():
        raise UpgradeError(f"the kept directory {kept} of {path} is gone")
    bad = compose.volume_path_problems(ctx.root, ctx.runtime, [VOLUME, kept.name])
    if bad:
        raise UpgradeError("unsafe volume path: " + "; ".join(bad))
    busy = _no_running_services(ctx, runner)
    if busy:
        raise UpgradeError(busy)
    if not ctx.confirm(f"Put {kept} (PostgreSQL {record.get('from')}) back as {current}?", default=False):
        if not ctx.yes and not ctx.stdin_is_tty:
            return report.error(ctx, exit_codes.USAGE, "db rollback needs a confirmation; add --yes when no terminal is attached")
        sys.stderr.write("[grdm-dev] db rollback cancelled\n")
        return exit_codes.OK
    ts = stamp or report.timestamp()
    aside = current.with_name(f"{VOLUME}.pg{record.get('to')}-rolledback-{ts}")
    journal = {"op": "rollback", "phase": "swap", "at": ts, "from": record.get("from"), "to": record.get("to"),
               "image": record.get("image"), "data_dir": str(current), "kept": str(kept), "aside": str(aside),
               "record": str(path), "containers": []}
    write_durable(journal_path(ctx), journal)
    try:
        with signals_interrupt():
            _swap(current, kept, aside)
    except (OSError, KeyboardInterrupt) as exc:
        outcome = recover(ctx, runner)
        raise UpgradeError(f"rollback {'interrupted' if isinstance(exc, KeyboardInterrupt) else f'failed: {exc}'}; {outcome}") from None
    _mark_rolled_back(journal)
    _drop_journal(ctx)
    report.emit(ctx, "db_rollback", {"data_dir": str(current), "restored_major": record.get("from"),
                                     "set_aside": str(aside), "record": str(path), "recovered": recovered})
    sys.stderr.write(f"[grdm-dev] {current} is PostgreSQL {record.get('from')} again; check out the revision that renders "
                     f"that major and run `grdm-dev compose render` before `up` (until then `up` stops with exit 15)\n")
    return exit_codes.OK
