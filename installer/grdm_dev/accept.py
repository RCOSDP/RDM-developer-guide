"""grdm-dev accept — run the Playwright Python acceptance suite (SPEC-02 §3, SPEC-04).

Flow: check that pytest + playwright are importable in this venv (exit 2 with an install hint
otherwise), refuse any base URL that is not loopback, optionally seed disposable users through the
`web` container (`--seed`), run pytest on installer/acceptance/ with JUnit output, then write
results.json + results.toon into docs/demo/runs/<run_id>/ and exit 60 if any test failed.

Standard library only. Every external call (pytest, docker compose) goes through an injectable
`runner(argv, env=None, cwd=None) -> (returncode, output)` so unit tests never need a browser,
Docker, or the application.
"""
from __future__ import annotations

import datetime as _dt
import importlib
import json
import os
import re
import secrets
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

from . import exit_codes, report, toon
from .context import Context

# SPEC-04 §4 / §5. Shared with installer/acceptance/conftest.py by convention (ids in file names).
SCENARIOS: dict[str, str] = {
    "C1": "Login via fakecas",
    "C2": "Create project",
    "C3": "Upload and download file",
    "C4": "Wiki collaborative edit",
    "C5": "File preview",
    "C6": "Institution admin screen",
    "S1": "y-websocket",
    "S2": "rdmcp (MCP endpoint)",
    "S3": "aipf_mcp_data_grdm",
    "S4": "OASys",
    "S5": "Shibboleth-SP via test IdP",
}

ACCEPTANCE_DIR = Path(__file__).resolve().parent.parent / "acceptance"
DEFAULT_WEB_PORT = 5000
# Browsers live inside the venv, never in the user's home (SPEC-04 §1). Relative to the repo root.
BROWSERS_PATH = Path(".venv") / ".playwright"
INSTALL_HINT = 'pip install -e "installer[accept]" && PLAYWRIGHT_BROWSERS_PATH=.venv/.playwright playwright install chromium'
REQUIRED_MODULES = ("pytest", "playwright", "pytest_playwright")
# Disposable-user mailbox domain. `.test` is reserved (RFC 2606): never a real person (POL-01).
SEED_DOMAIN = "acceptance.test"

# Django management call executed inside the `web` container by `--seed`.
# TODO(M2): confirm on the real app. OSFUser.create_confirmed(username, password, fullname) exists in
# osf/models/user.py upstream; the institution-admin flag for C6 (admin app permission / group) is
# unverified and may need `is_staff` plus an institution affiliation instead of `is_superuser`.
SEED_SNIPPET = (
    "from osf.models import OSFUser; "
    "u = OSFUser.create_confirmed(username={email!r}, password={email!r}, fullname={fullname!r}); "
    "u.is_staff = {admin}; u.is_superuser = {admin}; u.save(); print('seeded', u._id)"
)
CLEANUP_SNIPPET = (
    "from osf.models import OSFUser; "
    "n, _ = OSFUser.objects.filter(username__endswith='@{domain}', username__contains={run_id!r}).delete(); "
    "print('deleted', n)"
)


def register(subparsers) -> None:
    p = subparsers.add_parser("accept", help="run the Playwright acceptance suite in this venv; exit 60 on any failing test")
    p.add_argument("--only", metavar="SCENARIO", help="run one scenario (C1..C6, S1..S5, a name fragment like 'login', or a marker: core, subsystem)")
    p.add_argument("--seed", action="store_true", help="create disposable test users in the web container before running (removed afterwards)")
    p.add_argument("--base-url", dest="base_url", help="web URL; must be http://127.0.0.1:<port> (default: GRDM_PORT_WEB from runtime/.env, else 5000)")
    p.add_argument("--headed", action="store_true", help="show the browser window (debugging only)")
    p.set_defaults(_module=sys.modules[__name__])


# --- helpers -------------------------------------------------------------------------------------

def default_runner(argv: list[str], env: dict[str, str] | None = None, cwd: str | Path | None = None,
                   timeout: int = 1900) -> tuple[int, str]:
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, env=env, cwd=cwd, timeout=timeout)
    except FileNotFoundError as exc:
        return 127, str(exc)
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def missing_modules(importer=None) -> list[str]:
    importer = importer or importlib.import_module
    missing = []
    for name in REQUIRED_MODULES:
        try:
            importer(name)
        except ImportError:
            missing.append(name)
    return missing


def read_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def default_base_url(ctx: Context) -> str:
    port = read_env_file(ctx.runtime / ".env").get("GRDM_PORT_WEB", str(DEFAULT_WEB_PORT))
    return f"http://127.0.0.1:{port}"


def loopback_problem(url: str) -> str | None:
    """Return why `url` is not an acceptable loopback target, or None if it is (ADR-02 §3.5)."""
    u = urlparse(url)
    if u.scheme != "http":
        return f"scheme must be http, got {u.scheme!r}"
    if u.hostname != "127.0.0.1":
        return f"host must be 127.0.0.1, got {u.hostname!r} (tests never leave the machine)"
    if u.username or u.password:
        return "credentials in URL are not allowed"
    return None


def make_run_id(now: _dt.datetime | None = None) -> str:
    now = now or _dt.datetime.now(_dt.timezone.utc)
    return f"acc-{now.strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(3)}"


def seed_users(run_id: str) -> dict[str, dict[str, str]]:
    """Disposable identities for one run. With fakecas the password is the e-mail (upstream README)."""
    users = {}
    for key, admin in (("user_a", False), ("user_b", False), ("admin_user", True)):
        email = f"{key.replace('_', '-')}-{run_id}@{SEED_DOMAIN}"
        users[key] = {"email": email, "password": email, "fullname": f"Acceptance {key} {run_id}", "admin": admin}
    return users


def compose_exec(ctx: Context, service: str, *cmd: str) -> list[str]:
    argv = ["docker", "compose"]
    if (ctx.runtime / "docker-compose.yml").exists():
        argv += ["-f", str(ctx.runtime / "docker-compose.yml")]
    if (ctx.runtime / ".env").exists():
        argv += ["--env-file", str(ctx.runtime / ".env")]
    return argv + ["exec", "-T", service, *cmd]


def select_tests(only: str | None) -> tuple[list[str], list[str]] | None:
    """Translate --only into (paths, extra pytest args). None means the selection matched nothing."""
    if not only:
        return [str(ACCEPTANCE_DIR)], []
    key = only.strip().lower()
    if key in ("core", "subsystem"):
        return [str(ACCEPTANCE_DIR)], ["-m", key]
    files = sorted(ACCEPTANCE_DIR.glob("test_*.py"))
    hits = [str(f) for f in files if key in f.stem.lower()]
    if not hits and re.fullmatch(r"[cs][0-9]+", key):
        hits = [str(f) for f in files if f.stem.lower().startswith(f"test_{key}_")]
    return (hits, []) if hits else None


def pytest_argv(paths: list[str], extra: list[str], run_dir: Path, base_url: str, headed: bool) -> list[str]:
    argv = [sys.executable, "-m", "pytest", *paths, "-q", "--no-header",
            "-p", "no:cacheprovider",
            # pytest-playwright registers itself through its entry point; naming it again with -p would
            # register the same module twice and pluggy rejects that. Autoload stays on.
            "--base-url", base_url,
            "--junitxml", str(run_dir / "junit.xml"),
            "--screenshot", "only-on-failure",
            "--tracing", "retain-on-failure",
            "--output", str(run_dir / "artifacts"),
            "--browser", "chromium",
            *extra]
    if headed:
        argv.append("--headed")
    return argv


# --- result collection ---------------------------------------------------------------------------

def _classify(nodeid: str) -> tuple[str, str, str]:
    """(scenario id, scenario name, case) from a nodeid like .../test_c1_login.py::test_c1_login_success."""
    m = re.search(r"test_([cs][0-9]+)_", nodeid.lower())
    sid = m.group(1).upper() if m else "?"
    test = nodeid.rsplit("::", 1)[-1].lower()
    case = "success" if "success" in test else "rejection" if "reject" in test else "other"
    return sid, SCENARIOS.get(sid, sid), case


def _evidence_path(run_dir: Path, nodeid: str) -> str | None:
    """pytest-playwright writes <output>/<slug of test>/ on failure; return it relative to run_dir."""
    art = run_dir / "artifacts"
    if not art.is_dir():
        return None
    name = nodeid.rsplit("::", 1)[-1]
    for d in sorted(art.iterdir()):
        if d.is_dir() and name[:40].replace("_", "-") in d.name.replace("_", "-"):
            return str(d.relative_to(run_dir))
    return None


def collect_results(run_dir: Path) -> list[dict]:
    """Prefer the conftest collector file; fall back to junit.xml. Returns one row per test."""
    rows: list[dict] = []
    collector = run_dir / "collector.json"
    if collector.exists():
        try:
            for r in json.loads(collector.read_text(encoding="utf-8")):
                sid, name, case = _classify(r.get("nodeid", ""))
                rows.append({
                    "id": r.get("id") or sid, "name": r.get("name") or name, "case": r.get("case") or case,
                    "test": r.get("nodeid", "").rsplit("::", 1)[-1], "status": r.get("status", "error"),
                    "duration_ms": int(r.get("duration_ms", 0)), "http_status": r.get("http_status"),
                    "evidence": r.get("evidence") or _evidence_path(run_dir, r.get("nodeid", "")),
                })
            return rows
        except (ValueError, AttributeError):
            rows = []
    junit = run_dir / "junit.xml"
    if not junit.exists():
        return rows
    try:
        tree = ET.parse(junit)
    except ET.ParseError:
        return rows
    for tc in tree.iter("testcase"):
        nodeid = f"{tc.get('classname', '')}::{tc.get('name', '')}"
        sid, name, case = _classify(nodeid)
        status = "passed"
        for child in tc:
            if child.tag in ("failure",):
                status = "failed"
            elif child.tag == "error":
                status = "error"
            elif child.tag == "skipped":
                status = "skipped"
        http_status = None
        for prop in tc.iter("property"):
            if prop.get("name") == "http_status":
                try:
                    http_status = int(prop.get("value", ""))
                except ValueError:
                    http_status = prop.get("value")
        rows.append({"id": sid, "name": name, "case": case, "test": tc.get("name", ""), "status": status,
                     "duration_ms": int(float(tc.get("time", "0") or 0) * 1000), "http_status": http_status,
                     "evidence": _evidence_path(run_dir, nodeid)})
    return rows


def write_results(run_dir: Path, data: dict) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "results.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (run_dir / "results.toon").write_text(toon.encode(data, name="accept") + "\n", encoding="utf-8")


# --- entry point ---------------------------------------------------------------------------------

def run(ctx: Context, args, runner=None, importer=None, now=None) -> int:
    runner = runner or default_runner
    missing = missing_modules(importer)
    if missing:
        return report.error(ctx, exit_codes.USAGE, f"missing {', '.join(missing)}; run: {INSTALL_HINT}")

    base_url = (getattr(args, "base_url", None) or default_base_url(ctx)).rstrip("/")
    problem = loopback_problem(base_url)
    if problem:
        return report.error(ctx, exit_codes.USAGE, f"--base-url {base_url}: {problem}")

    browsers = ctx.root / BROWSERS_PATH
    if not browsers.is_dir() or not any(browsers.iterdir()):
        return report.error(ctx, exit_codes.USAGE, f"no Playwright browser under {browsers}; run: {INSTALL_HINT}")

    selection = select_tests(getattr(args, "only", None))
    if selection is None:
        return report.error(ctx, exit_codes.USAGE, f"--only {args.only!r} matches no scenario in {ACCEPTANCE_DIR}")
    paths, extra = selection

    started = now or _dt.datetime.now(_dt.timezone.utc)
    run_id = make_run_id(started)
    run_dir = ctx.root / "docs" / "demo" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    users = seed_users(run_id)

    env = dict(ctx.env)
    env.update({
        "PLAYWRIGHT_BROWSERS_PATH": str(browsers),
        "GRDM_BASE_URL": base_url,
        "GRDM_RUN_ID": run_id,
        "GRDM_ENV_FILE": str(ctx.runtime / ".env"),
        "GRDM_ACCEPT_RESULTS": str(run_dir / "collector.json"),
        "GRDM_ACCEPT_USER_A": users["user_a"]["email"],
        "GRDM_ACCEPT_USER_B": users["user_b"]["email"],
        "GRDM_ACCEPT_ADMIN": users["admin_user"]["email"],
    })

    seeded = False
    if getattr(args, "seed", False):
        for u in users.values():
            snippet = SEED_SNIPPET.format(email=u["email"], fullname=u["fullname"], admin=u["admin"])
            rc, out = runner(compose_exec(ctx, "web", "python3", "manage.py", "shell", "-c", snippet), env=env, cwd=ctx.root)
            if rc != 0:
                return report.error(ctx, exit_codes.SERVICES_UNHEALTHY, f"seed failed for {u['email']}: {out.strip()[-400:]}")
        seeded = True

    try:
        rc, out = runner(pytest_argv(paths, extra, run_dir, base_url, getattr(args, "headed", False)), env=env, cwd=ctx.root)
    finally:
        if seeded:
            cleanup = CLEANUP_SNIPPET.format(domain=SEED_DOMAIN, run_id=run_id)
            crc, cout = runner(compose_exec(ctx, "web", "python3", "manage.py", "shell", "-c", cleanup), env=env, cwd=ctx.root)
            if crc != 0:
                sys.stderr.write(f"warning: cleanup of seeded users failed: {cout.strip()[-200:]}\n")
    (run_dir / "pytest.log").write_text(out, encoding="utf-8")

    rows = collect_results(run_dir)
    finished = _dt.datetime.now(_dt.timezone.utc)
    summary = {s: sum(1 for r in rows if r["status"] == s) for s in ("passed", "failed", "error", "skipped")}
    summary["total"] = len(rows)
    data = {
        "run_id": run_id,
        "base_url": base_url,
        "started": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration_ms": int((finished - started).total_seconds() * 1000) if now is None else sum(r["duration_ms"] for r in rows),
        "only": getattr(args, "only", None),
        "seeded": seeded,
        "pytest_returncode": rc,
        "evidence_dir": str(run_dir.relative_to(ctx.root)) if run_dir.is_relative_to(ctx.root) else str(run_dir),
        "summary": summary,
        "tests": rows,
    }
    write_results(run_dir, data)
    report.emit(ctx, "accept", data)

    if rc == 5:  # pytest: no tests collected
        return report.error(ctx, exit_codes.USAGE, "pytest collected no tests")
    if rc != 0 or summary["failed"] or summary["error"]:
        return report.error(ctx, exit_codes.ACCEPTANCE_FAILED,
                            f"{summary['failed'] + summary['error']} failing test(s); see {run_dir}")
    return exit_codes.OK
