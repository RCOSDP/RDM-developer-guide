"""grdm-dev db status / upgrade / rollback — move the PostgreSQL data directory to the major of the rendered image (ADR-12).

A PostgreSQL server refuses a data directory written by another major ("database files are incompatible with
server"), so a new image needs the data moved. The move is a dump and restore, never an in-place change:

status    prints the major of runtime/volumes/postgres_data (PG_VERSION) and the major of the rendered `postgres`
          service, and whether `db upgrade` is needed. Changes nothing.
upgrade   with every service of the project stopped (`grdm-dev down`) and after a confirmation (--yes skips):
          1. starts the OLD major (SOURCE_IMAGES, digest pinned) on the existing directory, with no network and no
             TCP listener; its socket lives in a throwaway Docker volume;
          2. dumps every database and role with the NEW major's pg_dumpall (the PostgreSQL rule: dump with the newer
             client), as the host user, into runtime/backups/postgres-<old>-to-<new>-<timestamp>/dumpall.sql;
          3. records per database every table's row count and every sequence's last value, and the extensions;
          4. initialises the NEW major in runtime/volumes/postgres_data.pg<new>-<timestamp>.new with the rendered
             environment (initdb arguments, PGDATA, command) and restores the dump with ON_ERROR_STOP; the only line
             removed is `CREATE ROLE postgres;`, the bootstrap role initdb has already made;
          5. records the same numbers on the new cluster and stops unless they are identical;
          6. renames runtime/volumes/postgres_data to postgres_data.pg<old>-<timestamp> and the new directory to
             postgres_data. Renames stay inside runtime/volumes/ because a host user may rename a directory it does
             not own there (on Linux the data belongs to uid 999) but may not move it to another parent.
          The old directory is never written by the new major. On any failure nothing is renamed, the containers are
          stopped and kept for `docker logs`, and the report names what to remove.
rollback  with every service stopped and after a confirmation: renames the current postgres_data aside
          (postgres_data.pg<new>-rolledback-<timestamp>) and the kept old directory back, using the newest
          runtime/backups/postgres-*/upgrade.json. The rendered image is still the new major, so the old revision
          of this repository must be checked out and `compose render` run again before `up`; until then `up` stops.

`up` calls preflight(): a data directory of another major stops `up` with exit 15 before Compose starts it.

Runner: `runner(argv) -> (rc, stdout)`; tests inject a fake and never need Docker. Every container runs with
cap_drop ALL and no-new-privileges; the two servers add back only the capabilities of the `postgres` hardening
exception (manifest/hardening.json), because the official entrypoint starts as root and drops to postgres.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable

from . import compose, exit_codes, health, report
from .context import Context
from .secrets import env_path, read_env

SERVICE = "postgres"
VOLUME = "postgres_data"
DATA_TARGET = "/var/lib/postgresql/data"
SOCKET_DIR = "/var/run/postgresql"
BACKUP_TARGET = "/backup"
BACKUPS_DIR = "backups"
# Majors this command can read. The image is the one the stack ran before ADR-12, pinned by its index digest.
SOURCE_IMAGES: dict[str, str] = {
    "9.6": "postgres:9.6@sha256:caddd35b05cdd56c614ab1f674e63be778e0abdf54e71a7507ff3e28d4902698",
}
SERVER_CAPS = ("CHOWN", "DAC_OVERRIDE", "FOWNER", "SETGID", "SETUID")  # = the postgres exception in manifest/hardening.json
POSTGRES_UID = "999:999"  # the postgres user of the Debian-based official images, 9.6 and 18 alike
BOOTSTRAP_ROLE_LINE = "CREATE ROLE postgres;"
READY_TIMEOUT = 600.0
# Every table's row count and every sequence's last value, by name; the same text on both majors (9.6 and 18).
# The casts matter: PostgreSQL 18 cannot choose an operator for text || "char" (measured), 9.6 could.
SNAPSHOT_SQL = (
    "SELECT n.nspname::text || '.' || c.relname::text || ' ' || c.relkind::text || ' ' || "
    "(xpath('/row/v/text()', query_to_xml(format(CASE c.relkind WHEN 'S' THEN 'SELECT last_value AS v FROM %I.%I' "
    "ELSE 'SELECT count(*) AS v FROM %I.%I' END, n.nspname, c.relname), false, true, '')))[1]::text "
    "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
    "WHERE c.relkind IN ('r', 'S') AND n.nspname NOT IN ('pg_catalog', 'information_schema') "
    "AND n.nspname NOT LIKE 'pg_toast%' "
    "UNION ALL SELECT 'extension ' || extname FROM pg_extension ORDER BY 1"
)
DATABASES_SQL = "SELECT datname FROM pg_database WHERE datallowconn AND NOT datistemplate ORDER BY 1"
ROLES_SQL = "SELECT rolname FROM pg_roles WHERE rolname !~ '^pg_' ORDER BY 1"

Runner = Callable[[list[str]], tuple[int, str]]


class UpgradeError(Exception):
    """A step failed; the message says which. Nothing has been renamed."""


def register(subparsers) -> None:
    p = subparsers.add_parser("db", help="PostgreSQL data directory: status, upgrade to the rendered major, rollback")
    sub = p.add_subparsers(dest="db_command", metavar="<action>")
    sub.add_parser("status", help="show the data directory's major and the rendered image's major; changes nothing")
    sub.add_parser("upgrade", help="dump and restore runtime/volumes/postgres_data into the rendered major; keeps the old directory; exit 15 on failure")
    sub.add_parser("rollback", help="put the directory kept by the last upgrade back in place; exit 15 on failure")
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


def rendered_service(ctx: Context) -> dict[str, Any] | None:
    try:
        data = health.load_compose(health.compose_path(ctx))
    except (OSError, ValueError):
        return None
    return (data.get("services") or {}).get(SERVICE)


def data_major(directory: Path, runner: Runner | None = None, image: str | None = None, platform: str | None = None) -> str | None:
    """The major written in PG_VERSION, "" when the directory holds no cluster, None when it cannot be read.

    On Linux the directory belongs to uid 999 with mode 0700, so the host user cannot read it; then the file is
    read by the postgres uid in a throwaway container of `image`, with no network and nothing writable."""
    try:
        if not directory.is_dir():
            return ""
        return (directory / "PG_VERSION").read_text(encoding="ascii").strip()
    except FileNotFoundError:
        return ""
    except PermissionError:
        if runner is None or not image:
            return None
    argv = ["docker", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges:true", "--user", POSTGRES_UID]
    if platform:
        argv += ["--platform", platform]
    argv += ["-v", f"{directory}:/data:ro", "--entrypoint", "sh", image, "-c",
             "if [ -e /data/PG_VERSION ]; then cat /data/PG_VERSION; else echo none; fi"]
    rc, out = runner(argv)
    if rc != 0:
        return None
    value = out.strip()
    return "" if value == "none" else value or None


def preflight(ctx: Context, runner: Runner | None = None) -> str | None:
    """Why `up` must not start postgres on the current data directory, or None."""
    svc = rendered_service(ctx)
    if not svc:
        return None
    want = image_major(svc.get("image"))
    have = data_major(data_dir(ctx), runner, svc.get("image"), svc.get("platform"))
    if not want or not have:
        return None
    if have != want:
        return (f"{data_dir(ctx)} was written by PostgreSQL {have} but the rendered image is PostgreSQL {want}; "
                f"run `grdm-dev db upgrade` (it keeps the old directory), or check out the revision that matches the data")
    return None


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
    # No TCP listener at all: the dump and the restore use the socket in the throwaway volume.
    return argv + [image, *command, "-c", "listen_addresses="]


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


# --------------------------------------------------------------------------- steps


def wait_ready(name: str, runner: Runner, sleep: Callable[[float], None], timeout: float = READY_TIMEOUT, interval: float = 2.0) -> None:
    """Ready = the final server is PID 1 (the entrypoint's temporary init server never is) and accepts connections."""
    probe = 'p=$(head -n1 "$PGDATA/postmaster.pid" 2>/dev/null); [ "$p" = 1 ] && pg_isready -q -h ' + SOCKET_DIR
    waited = 0.0
    while True:
        rc, out = runner(["docker", "inspect", "-f", "{{.State.Running}}", name])
        if rc != 0 or out.strip() != "true":
            raise UpgradeError(f"container {name} is not running; see `docker logs {name}`")
        rc, _ = runner(exec_argv(name, "sh", "-c", probe))
        if rc == 0:
            return
        if waited >= timeout:
            raise UpgradeError(f"container {name} not ready after {int(timeout)}s; see `docker logs {name}`")
        sleep(interval)
        waited += interval


def snapshot(name: str, runner: Runner) -> dict[str, list[str]]:
    """{database: sorted lines}, plus "roles"; equal on both sides means every row and sequence value moved."""
    rc, out = runner(psql_argv(name, "postgres", DATABASES_SQL))
    if rc != 0:
        raise UpgradeError(f"listing databases in {name} failed (psql exited {rc})")
    result: dict[str, list[str]] = {}
    for db in [line.strip() for line in out.splitlines() if line.strip()]:
        rc, rows = runner(psql_argv(name, db, SNAPSHOT_SQL))
        if rc != 0:
            raise UpgradeError(f"counting rows of {db} in {name} failed (psql exited {rc})")
        result[db] = [line for line in rows.splitlines() if line.strip()]
    rc, out = runner(psql_argv(name, "postgres", ROLES_SQL))
    if rc != 0:
        raise UpgradeError(f"listing roles in {name} failed (psql exited {rc})")
    result["roles"] = [line for line in out.splitlines() if line.strip()]
    return result


def snapshot_differences(old: dict[str, list[str]], new: dict[str, list[str]]) -> list[str]:
    diffs: list[str] = []
    for key in sorted(set(old) | set(new)):
        a, b = set(old.get(key, [])), set(new.get(key, []))
        if key not in new:
            diffs.append(f"{key}: missing after restore")
        elif key not in old:
            diffs.append(f"{key}: new after restore")
        else:
            diffs += [f"{key}: before `{x}`" for x in sorted(a - b)[:5]] + [f"{key}: after `{x}`" for x in sorted(b - a)[:5]]
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


def _stop(name: str, runner: Runner, remove: bool) -> None:
    runner(["docker", "stop", "-t", "60", name])
    if remove:
        runner(["docker", "rm", name])


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
    base = ctx.runtime / BACKUPS_DIR
    records = sorted(base.glob("postgres-*/upgrade.json")) if base.is_dir() else []
    for path in reversed(records):
        try:
            return path, json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
    return None


# --------------------------------------------------------------------------- commands


def run(ctx: Context, args, runner: Runner | None = None, sleep: Callable[[float], None] | None = None,
        user: str | None = None, stamp: str | None = None) -> int:
    action = getattr(args, "db_command", None)
    runner = runner or health.default_runner
    if action == "status":
        return run_status(ctx, runner)
    if action == "upgrade":
        return run_upgrade(ctx, runner, sleep or time.sleep, user=user, stamp=stamp)
    if action == "rollback":
        return run_rollback(ctx, runner, stamp=stamp)
    return report.error(ctx, exit_codes.USAGE, "choose status, upgrade or rollback")


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
    have = data_major(data_dir(ctx), runner, svc.get("image"), svc.get("platform"))
    state = "empty" if have == "" else "unknown" if have is None else "current" if have == want else "upgrade-needed"
    record = latest_record(ctx)
    report.emit(ctx, "db_status", {
        "data_dir": str(data_dir(ctx)), "data_major": have, "image": svc.get("image"), "image_major": want, "state": state,
        "upgradable": state == "upgrade-needed" and have in SOURCE_IMAGES,
        "last_upgrade": str(record[0].parent) if record else None,
    })
    return exit_codes.OK


def run_upgrade(ctx: Context, runner: Runner, sleep: Callable[[float], None], user: str | None = None, stamp: str | None = None) -> int:
    svc, problem = _target(ctx)
    if problem:
        return report.error(ctx, exit_codes.USAGE, problem)
    image, platform = str(svc["image"]), svc.get("platform")
    want = image_major(image)
    current = data_dir(ctx)
    bad = compose.volume_path_problems(ctx.root, ctx.runtime, [VOLUME])
    if bad:
        return report.error(ctx, exit_codes.DB_UPGRADE_FAILED, "unsafe volume path: " + "; ".join(bad))
    have = data_major(current, runner, image, platform)
    if have is None:
        return report.error(ctx, exit_codes.DB_UPGRADE_FAILED, f"cannot read {current}/PG_VERSION")
    if have in ("", want):
        report.emit(ctx, "db_upgrade", {"data_dir": str(current), "data_major": have or None, "image_major": want,
                                        "changed": False, "reason": "no cluster yet" if have == "" else "already current"})
        return exit_codes.OK
    source = SOURCE_IMAGES.get(have)
    if not source:
        return report.error(ctx, exit_codes.DB_UPGRADE_FAILED, f"no source image for PostgreSQL {have}; known: {', '.join(SOURCE_IMAGES)}")
    password = read_env(env_path(ctx)).get("POSTGRES_PASSWORD")
    if not password:
        return report.error(ctx, exit_codes.USAGE, f"{env_path(ctx)} has no POSTGRES_PASSWORD; run `grdm-dev secrets init` first")
    busy = _no_running_services(ctx, runner)
    if busy:
        return report.error(ctx, exit_codes.DB_UPGRADE_FAILED, busy)
    if not ctx.confirm(f"Dump {current} (PostgreSQL {have}) and restore it into PostgreSQL {want}? The old directory is kept.", default=False):
        if not ctx.yes and not ctx.stdin_is_tty:
            return report.error(ctx, exit_codes.USAGE, "db upgrade needs a confirmation; add --yes when no terminal is attached")
        sys.stderr.write("[grdm-dev] db upgrade cancelled\n")
        return exit_codes.OK

    ts = stamp or report.timestamp()
    backup = ctx.runtime / BACKUPS_DIR / f"postgres-{have}-to-{want}-{ts}"
    new_dir = current.with_name(f"{VOLUME}.pg{want}-{ts}.new")
    kept = current.with_name(f"{VOLUME}.pg{have}-{ts}")
    old_name, new_name = f"grdm-dev-dbupgrade-old-{ts}", f"grdm-dev-dbupgrade-new-{ts}"
    socket_volume = f"grdm-dev-dbupgrade-{ts}".lower()
    env = {k: str(v) for k, v in (svc.get("environment") or {}).items() if k in ("POSTGRES_INITDB_ARGS", "PGDATA")}
    command = [str(c) for c in (svc.get("command") or ["postgres"])]
    tmpfs = [str(t).split(":", 1)[0] for t in (svc.get("tmpfs") or []) if not str(t).startswith(SOCKET_DIR)]
    user = user or f"{os.getuid()}:{os.getgid()}"
    steps: list[dict[str, Any]] = []
    started: list[str] = []

    def step(name: str, **detail: Any) -> None:
        steps.append({"step": name, "status": "ok", **detail})
        sys.stderr.write(f"[grdm-dev] db upgrade: {name}\n")

    try:
        backup.mkdir(parents=True, mode=0o700)
        os.chmod(backup, 0o700)  # nosemgrep: python.lang.security.audit.insecure-file-permissions.insecure-file-permissions -- owner-only is the intended restriction
        new_dir.mkdir(mode=0o755)
        rc, _ = runner(["docker", "volume", "create", "--label", "org.gakunin-rdm.component=postgres-upgrade", socket_volume])
        if rc != 0:
            raise UpgradeError(f"docker volume create exited {rc}")
        rc, _ = runner(server_argv(old_name, source, current, socket_volume, platform=platform,
                                   env={"PGDATA": DATA_TARGET}, command=["postgres"], tmpfs=["/tmp"]))
        if rc != 0:
            raise UpgradeError(f"starting PostgreSQL {have} exited {rc}")
        started.append(old_name)
        wait_ready(old_name, runner, sleep)
        step("start-old", image=source)
        before = snapshot(old_name, runner)
        step("count-old", databases=sorted(k for k in before if k != "roles"))
        rc, _ = runner(dump_argv(image, socket_volume, backup, platform, user))
        if rc != 0 or not (backup / "dumpall.sql").is_file():
            raise UpgradeError(f"pg_dumpall exited {rc}")
        os.chmod(backup / "dumpall.sql", 0o600)  # it holds the roles' password hashes
        step("dump", file=str(backup / "dumpall.sql"), bytes=(backup / "dumpall.sql").stat().st_size)
        _stop(old_name, runner, remove=True)
        started.remove(old_name)
        write_restore_file(backup / "dumpall.sql", backup / "restore.sql")
        new_env = {**env, "POSTGRES_HOST_AUTH_METHOD": _auth_method(env)}
        # The entrypoint's initdb needs a superuser password; the restore then sets the dumped one (the same
        # value, as runtime/.env did not change). It goes through a 0600 file in the 0700 backup directory,
        # removed as soon as the container exists.
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
            raise UpgradeError(f"starting PostgreSQL {want} exited {rc}")
        started.append(new_name)
        wait_ready(new_name, runner, sleep)
        step("init-new", image=image, directory=str(new_dir))
        rc, _ = runner(exec_argv(new_name, "psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-h", SOCKET_DIR, "-U", "postgres",
                                 "-d", "postgres", "-f", f"{BACKUP_TARGET}/restore.sql"))
        if rc != 0:
            raise UpgradeError(f"restore exited {rc}; see `docker logs {new_name}`")
        rc, _ = runner(exec_argv(new_name, "vacuumdb", "-q", "-h", SOCKET_DIR, "-U", "postgres", "--all", "--analyze-only"))
        if rc != 0:
            raise UpgradeError(f"vacuumdb --analyze-only exited {rc}")
        step("restore")
        after = snapshot(new_name, runner)
        diffs = snapshot_differences(before, after)
        if diffs:
            raise UpgradeError("restored data differs: " + "; ".join(diffs[:10]))
        rows = sum(len(v) for k, v in after.items() if k != "roles")
        step("verify", objects_compared=rows, databases=sorted(k for k in after if k != "roles"), roles=after["roles"])
        _stop(new_name, runner, remove=True)
        started.remove(new_name)
        runner(["docker", "volume", "rm", socket_volume])
        os.rename(current, kept)
        os.rename(new_dir, current)
        step("swap", kept=str(kept))
    except (UpgradeError, OSError) as exc:
        for name in started:
            _stop(name, runner, remove=False)
        leftovers = [str(p) for p in (new_dir,) if p.exists()] + started
        if runner(["docker", "volume", "rm", socket_volume])[0] != 0:
            leftovers.append(f"volume {socket_volume}")
        report.emit(ctx, "db_upgrade", {"changed": False, "failed": str(exc), "steps": steps, "data_dir": str(current),
                                        "backup": str(backup), "leftovers": leftovers})
        return report.error(ctx, exit_codes.DB_UPGRADE_FAILED,
                            f"{exc}; {current} is unchanged; remove {', '.join(leftovers) or 'nothing'} when done "
                            f"(`docker rm`, and the directory with `grdm-dev reset` or as root)")
    record = {"from": have, "to": want, "source_image": source, "image": image, "data_dir": str(current),
              "kept": str(kept), "dump": str(backup / "dumpall.sql"), "at": ts, "steps": steps}
    (backup / "upgrade.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report.emit(ctx, "db_upgrade", {"changed": True, **record})
    sys.stderr.write(f"[grdm-dev] PostgreSQL {have} → {want} done; the old directory is {kept}; run `grdm-dev up`\n")
    return exit_codes.OK


def run_rollback(ctx: Context, runner: Runner, stamp: str | None = None) -> int:
    found = latest_record(ctx)
    if not found:
        return report.error(ctx, exit_codes.DB_UPGRADE_FAILED, f"no upgrade record under {ctx.runtime / BACKUPS_DIR}")
    path, record = found
    current = data_dir(ctx)
    kept = current.with_name(Path(str(record.get("kept", ""))).name)
    if not record.get("kept") or not kept.is_dir():
        return report.error(ctx, exit_codes.DB_UPGRADE_FAILED, f"the kept directory {kept} of {path} is gone")
    bad = compose.volume_path_problems(ctx.root, ctx.runtime, [VOLUME, kept.name])
    if bad:
        return report.error(ctx, exit_codes.DB_UPGRADE_FAILED, "unsafe volume path: " + "; ".join(bad))
    busy = _no_running_services(ctx, runner)
    if busy:
        return report.error(ctx, exit_codes.DB_UPGRADE_FAILED, busy)
    if not ctx.confirm(f"Put {kept} (PostgreSQL {record.get('from')}) back as {current}?", default=False):
        if not ctx.yes and not ctx.stdin_is_tty:
            return report.error(ctx, exit_codes.USAGE, "db rollback needs a confirmation; add --yes when no terminal is attached")
        sys.stderr.write("[grdm-dev] db rollback cancelled\n")
        return exit_codes.OK
    aside = current.with_name(f"{VOLUME}.pg{record.get('to')}-rolledback-{stamp or report.timestamp()}")
    try:
        if current.exists():
            os.rename(current, aside)
        os.rename(kept, current)
    except OSError as exc:
        return report.error(ctx, exit_codes.DB_UPGRADE_FAILED, f"rename failed: {exc}")
    report.emit(ctx, "db_rollback", {"data_dir": str(current), "restored_major": record.get("from"),
                                     "set_aside": str(aside), "record": str(path)})
    sys.stderr.write(f"[grdm-dev] {current} is PostgreSQL {record.get('from')} again; check out the revision that renders "
                     f"that major and run `grdm-dev compose render` before `up` (until then `up` stops with exit 15)\n")
    return exit_codes.OK
