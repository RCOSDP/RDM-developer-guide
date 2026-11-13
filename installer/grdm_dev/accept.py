"""grdm-dev accept — run the Playwright Python acceptance suite (SPEC-02 §3, SPEC-04).

Flow (SPEC-04 §2: integration before acceptance):
  1. pytest + playwright importable in this venv (exit 2 with an install hint otherwise);
  2. --base-url must be loopback (exit 2); Chromium's executable must exist under
     PLAYWRIGHT_BROWSERS_PATH=.venv/.playwright (exit 2);
  3. integration precheck: every Compose service running/healthy and every HTTP probe answering
     (`grdm_dev.health.check_services`, imported lazily) — exit 40 before any browser starts;
  4. optionally seed disposable users through the `web` container (`--seed`);
  5. pytest on the acceptance suite with JUnit output into docs/demo/runs/<run_id>/;
  6. results.json + results.toon; exit 60 if any test failed, if no result row was collected, or if a
     selected scenario lacks a success or a rejection row.

Evidence never contains secrets (SPEC-03 §3.1, SPEC-04 §7): every value of runtime/.env, every seeded
identity and credential of the run (PR #35 review r1 R1-01), and every token-like string is masked in every text artefact under the run directory (pytest.log, junit.xml,
collector.json, results.*, *.har/*.json/*.txt/*.log/*.md anywhere below it) and in anything printed;
ZIP archives that remain under the run directory are rewritten member by member (text-like members
masked, binary members other than images dropped); the run directory is 0700 and its files 0600.

Browser traces are off by default (`--tracing off`). `--trace` enables `retain-on-failure`, and the
resulting trace ZIPs are moved out of docs/demo/runs/ into runtime/reports/quarantine/<run_id>/
(0700, git-ignored, never part of a report bundle) before the run directory is sanitized; results.json
records the quarantine in `trace_quarantine`.

The suite is resolved from the installed `acceptance` package (importlib.resources) first and from
the repository checkout (installer/acceptance/) as a fallback, so a non-editable `pip install
./installer` carries its own tests.

Standard library only. Every external call (pytest, docker compose, health) goes through injectable
callables so unit tests never need a browser, Docker, or the application.
"""
from __future__ import annotations

import datetime as _dt
import html
import importlib
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Callable
from urllib.parse import quote, urlparse

from . import exit_codes, report, toon
from .context import Context

# SPEC-04 §4 / §5. Shared with acceptance/conftest.py by convention (ids in file names).
SCENARIOS: dict[str, str] = {
    "C1": "Login via fakecas",
    "C2": "Create project",
    "C3": "Upload and download file",
    "C4": "Wiki collaborative edit",
    "C5": "File preview",
    "C6": "Institution admin screen",
    "C7": "File page collaborative edit",
    "S1": "y-websocket",
    "S2": "rdmcp (MCP endpoint)",
    "S3": "aipf_mcp_data_grdm",
    "S4": "OASys",
    "S5": "Shibboleth-SP via test IdP",
}

ACCEPTANCE_PACKAGE = "acceptance"
REPO_ACCEPTANCE_DIR = Path(__file__).resolve().parent.parent / "acceptance"
DEFAULT_WEB_PORT = 5000
# Browsers live inside the venv, never in the user's home (SPEC-04 §1). Relative to the repo root.
BROWSERS_PATH = Path(".venv") / ".playwright"
# Where `playwright install chromium` puts the executable (macOS app bundle, Linux build, headless shell).
CHROMIUM_GLOBS = (
    "chromium*/chrome-*/Chromium.app/Contents/MacOS/Chromium",
    # Playwright >= 1.5x ships "Google Chrome for Testing" on macOS and a separate headless shell build
    # (real acceptance run 1 on the Mac Studio: only these two layouts were present under .venv/.playwright)
    "chromium*/chrome-*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
    "chromium*/chrome-linux*/chrome",
    "chromium*/chrome-*/chrome",
    "chromium*/chrome-*/headless_shell",
    "chromium_headless_shell*/chrome-headless-shell-*/chrome-headless-shell",
)
INSTALL_HINT = 'pip install -e "installer[accept]" && PLAYWRIGHT_BROWSERS_PATH=.venv/.playwright playwright install chromium'
# Linux also needs Chromium's system libraries (`install-deps`, which asks for sudo), and Playwright's own Node.js
# driver needs libatomic1, which the Ubuntu 24.04 cloud image lacks: without it even `playwright install` fails
# with "libatomic.so.1: cannot open shared object file" (DEMO-21, arm64).
LINUX_INSTALL_HINT = ("sudo apt-get install -y libatomic1 && " + INSTALL_HINT
                      + " && PLAYWRIGHT_BROWSERS_PATH=.venv/.playwright playwright install-deps chromium")


def install_hint(system: str | None = None) -> str:
    """The command that installs the [accept] extra and Chromium on this kind of host."""
    return LINUX_INSTALL_HINT if (system if system is not None else sys.platform).startswith("linux") else INSTALL_HINT
REQUIRED_MODULES = ("pytest", "playwright", "pytest_playwright")
# Disposable-user mailbox domain. `.test` is reserved (RFC 2606): never a real person (POL-01).
SEED_DOMAIN = "acceptance.test"
MASK = "***"
# .env keys whose values are configuration, not secrets, and must stay readable in evidence.
PUBLIC_ENV_KEY_PREFIXES = ("GRDM_PORT_", "GRDM_PROFILE", "GRDM_AUTH", "COMPOSE_PROJECT_NAME")
# Token-like strings masked even when they are not in .env (session cookies, bearer tokens, JWTs,
# long hex/base64 blobs, `password=` style assignments in tracebacks).
TOKEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(\bbearer\s+)[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}(?:\.[A-Za-z0-9_-]{8,})?"),  # JWT
    re.compile(r"(?i)((?:password|passwd|secret|token|api[_-]?key|csrf|cookie|sessionid|osf)\s*[=:]\s*[\"']?)[^\s\"';,&]{4,}"),
    re.compile(r"(?i)((?:x-csrftoken|authorization|set-cookie|cookie)\s*:\s*)[^\r\n]{4,}"),
    # a quoted key, as in the repr of a dict shown by a pytest failure ('password': 'value')
    re.compile(r"""(?i)(['"](?:password|passwd|osf_password)['"]\s*:\s*['"])[^'"\r\n]+"""),
    # any disposable mailbox: the fakecas identity, which is also its password. OSF lower-cases usernames.
    re.compile(r"(?i)[\w.+%-]+(?:@|%40)" + re.escape(SEED_DOMAIN) + r"\b"),
    re.compile(r"\b[A-Fa-f0-9]{32,}\b"),
    # long base64/urlsafe blobs with at least four digits (test slugs like test-c4-... have one)
    re.compile(r"\b(?=(?:[A-Za-z_-]*\d){4})[A-Za-z0-9_-]{40,}\b"),
)
# Text-like files under the run directory that are masked in place (suffix match, case-insensitive).
TEXT_SUFFIXES = (".har", ".json", ".jsonl", ".txt", ".log", ".md", ".xml")
# ZIP members (Playwright traces: trace.trace / trace.network / trace.stacks are JSON lines) whose
# bytes are masked; anything else is dropped unless it is an image (screenshots stay).
ZIP_TEXT_SUFFIXES = TEXT_SUFFIXES + (".trace", ".network", ".stacks", ".html", ".htm", ".css", ".js", ".csv", ".svg")
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")
IMAGE_MAGIC = (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"GIF87a", b"GIF89a", b"RIFF", b"BM")
# Members of a Playwright trace that carry response bodies (resources/<sha1>.<ext>); dropped unless image.
ZIP_BODY_PREFIX = "resources/"
QUARANTINE_SUBDIR = Path("reports") / "quarantine"

# Django management call executed inside the `web` container by `--seed`.
# Confirmed on the real app (acceptance run 3): OSFUser.create_confirmed(username, password, fullname)
# exists, and OSFUser.set_password refuses a password equal to the e-mail address
# ("Password cannot be the same as your email address"), so the OSF account gets an independent random
# password that nothing types: fakecas identifies the user by e-mail alone, and the login helper fills
# its password field only in the rare case that the field is visible.
# GRDM's OSFUser.have_email defaults to False and create_confirmed leaves it there; every @must_be_logged_in
# view then redirects to /settings/account/email, so the dashboard is never reached (acceptance run 8).
# C6's admin is what the admin app calls an institution administrator: is_staff, not superuser, with an
# affiliation (RdmPermissionMixin.is_admin, UserIdentificationAdminListView). `{institutions}` is a slice of the
# non-deleted institutions by id: "0:0" none, "0:1" the first (the admin's), "1:2" only the second (another one).
# RDM-osf.io-dev2027 PR #10 (admin two-step sign-in): the admin app sends every staff user to a TOTP step after the
# password, and an administrator without TOTP lands on the enrolment page. The seeded administrator is therefore
# enrolled and confirmed beforehand with a random secret that only the test receives (GRDM_ACCEPT_ADMIN_TOTP_SECRET),
# so C6 types a real code and nothing weakens the sign-in (ADMIN_2FA_GRACE_UNTIL stays unset).
TWO_FACTOR_SNIPPET = (
    "u.add_addon('twofactor'); a = u.get_addon('twofactor'); "
    "a.totp_secret = {totp_secret!r}; a.totp_drift = 0; a.is_confirmed = True; a.save(); "
)
SEED_SNIPPET = (
    "from osf.models import OSFUser; "
    "u = OSFUser.create_confirmed(username={email!r}, password={osf_password!r}, fullname={fullname!r}); "
    "u.have_email = True; u.is_staff = {admin}; u.is_superuser = False; u.save(); "
    "{two_factor}"
    "from osf.models import Institution; "
    "u.affiliated_institutions.add(*Institution.objects.filter(is_deleted=False).order_by('id')[{institutions}]); "
    "print('seeded', u._id)"
)
CLEANUP_SNIPPET = (
    "from osf.models import OSFUser; "
    "n, _ = OSFUser.objects.filter(username__endswith='@{domain}', username__icontains={run_id!r}).delete(); "
    "print('deleted', n)"
)


def register(subparsers) -> None:
    p = subparsers.add_parser("accept", help="run the Playwright acceptance suite in this venv; exit 60 on any failing test")
    p.add_argument("--only", metavar="SCENARIO", help="run one scenario (C1..C7, S1..S5, a name fragment like 'login', or a marker: core, subsystem)")
    p.add_argument("--seed", action="store_true", help="create disposable test users in the web container before running (removed afterwards)")
    p.add_argument("--base-url", dest="base_url", help="web URL; must be http://127.0.0.1:<port> (default: GRDM_PORT_WEB from runtime/.env, else 5000)")
    p.add_argument("--headed", action="store_true", help="show the browser window (debugging only)")
    p.add_argument("--trace", action="store_true",
                   help="record Playwright traces for failed tests; the ZIPs are quarantined under runtime/reports/quarantine/<run_id>/ (owner-only, git-ignored), never kept in docs/demo/runs/")
    p.set_defaults(_module=sys.modules[__name__])


# --- suite location ------------------------------------------------------------------------------

def resolve_acceptance_dir(repo_dir: Path | None = None, importer=None) -> Path:
    """Directory of the acceptance suite: the installed `acceptance` package first (a non-editable
    `pip install ./installer` carries it as package data), then the repository checkout."""
    repo_dir = REPO_ACCEPTANCE_DIR if repo_dir is None else repo_dir
    importer = importer or importlib.import_module
    try:
        mod = importer(ACCEPTANCE_PACKAGE)
        mod_file = getattr(mod, "__file__", None)
        if mod_file:
            pkg_dir = Path(mod_file).resolve().parent
            if (pkg_dir / "conftest.py").is_file():
                return pkg_dir
    except ImportError:
        pass
    return repo_dir


ACCEPTANCE_DIR = resolve_acceptance_dir()


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
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
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


def chromium_executable(browsers: Path) -> Path | None:
    """The Chromium binary `playwright install chromium` placed under `browsers`, or None."""
    if not browsers.is_dir():
        return None
    for pattern in CHROMIUM_GLOBS:
        for cand in sorted(browsers.glob(pattern)):
            if cand.is_file():
                return cand
    return None


def make_run_id(now: _dt.datetime | None = None) -> str:
    now = now or _dt.datetime.now(_dt.timezone.utc)
    return f"acc-{now.strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(3)}"


def seed_users(run_id: str) -> dict[str, dict[str, str]]:
    """Disposable identities for one run. With fakecas the password is the e-mail (upstream README); the
    OSF account gets an independent random password, because the identity is printed by failing tests and
    OSF refuses a password equal to the e-mail. All of them are secrets for evidence: `seed_secret_values`."""
    users = {}
    # institution_member shares admin_user's institution; other_institution_member belongs only to a different
    # one; user_a has none. Neither member signs in. C6 proves the list holds exactly the admin's institution:
    # the first is listed, the other two are not (PR #40 review r1 R1-01). user_a and user_b stay unaffiliated:
    # an affiliated user's login does not reach the dashboard that the `login` fixture waits for
    # (run acc-20261109T231841Z-50571f).
    for key, admin, institutions in (("user_a", False, "0:0"), ("user_b", False, "0:0"), ("institution_member", False, "0:1"),
                                     ("other_institution_member", False, "1:2"), ("admin_user", True, "0:1")):
        email = f"{key.replace('_', '-')}-{run_id}@{SEED_DOMAIN}"
        users[key] = {"email": email, "password": email, "osf_password": secrets.token_urlsafe(24),
                      "fullname": f"Acceptance {key} {run_id}", "admin": admin, "institutions": institutions}
        if admin:
            users[key]["totp_secret"] = secrets.token_hex(20)  # 160 bits, the hexadecimal form OSF stores
    return users


def seed_secret_values(users: dict[str, dict[str, str]]) -> list[str]:
    """Every credential of the seeded users, as written and lower-cased (OSF stores the lower-cased username)."""
    values: set[str] = set()
    for user in users.values():
        for field in ("email", "password", "osf_password", "totp_secret"):
            if user.get(field):
                values.update((user[field], user[field].lower()))
    return list(values)


def compose_exec(ctx: Context, service: str, *cmd: str) -> list[str]:
    argv = ["docker", "compose"]
    if (ctx.runtime / "docker-compose.yml").exists():
        argv += ["-f", str(ctx.runtime / "docker-compose.yml")]
    if (ctx.runtime / ".env").exists():
        argv += ["--env-file", str(ctx.runtime / ".env")]
    return argv + ["exec", "-T", service, *cmd]


def select_tests(only: str | None, suite_dir: Path | None = None) -> tuple[list[str], list[str]] | None:
    """Translate --only into (paths, extra pytest args). None means the selection matched nothing."""
    suite_dir = suite_dir or ACCEPTANCE_DIR
    if not only:
        return [str(suite_dir)], []
    key = only.strip().lower()
    if key in ("core", "subsystem"):
        return [str(suite_dir)], ["-m", key]
    files = sorted(suite_dir.glob("test_*.py"))
    hits = [str(f) for f in files if key in f.stem.lower()]
    if not hits and re.fullmatch(r"[cs][0-9]+", key):
        hits = [str(f) for f in files if f.stem.lower().startswith(f"test_{key}_")]
    return (hits, []) if hits else None


def expected_scenarios(paths: list[str], extra: list[str]) -> list[str]:
    """Scenario ids the selection is supposed to produce rows for (one file per scenario)."""
    ids: set[str] = set()
    for p in paths:
        path = Path(p)
        files = sorted(path.glob("test_*.py")) if path.is_dir() else [path]
        for f in files:
            m = re.match(r"test_([cs][0-9]+)_", f.stem.lower())
            if m:
                ids.add(m.group(1).upper())
    if "-m" in extra:
        marker = extra[extra.index("-m") + 1].lower()
        prefix = {"core": "C", "subsystem": "S"}.get(marker)
        if prefix:
            ids = {i for i in ids if i.startswith(prefix)}
    return sorted(ids)


def incomplete_scenarios(rows: list[dict], expected: list[str]) -> list[str]:
    """Scenarios of `expected` that lack a success row or a rejection row (SPEC-04 §3.1)."""
    seen: dict[str, set[str]] = {}
    for r in rows:
        seen.setdefault(str(r.get("id")), set()).add(str(r.get("case")))
    return [sid for sid in expected if not {"success", "rejection"} <= seen.get(sid, set())]


def pytest_argv(paths: list[str], extra: list[str], run_dir: Path, base_url: str, headed: bool,
                trace: bool = False) -> list[str]:
    argv = [sys.executable, "-m", "pytest", *paths, "-q", "--no-header",
            "-p", "no:cacheprovider",
            # pytest-playwright registers itself through its entry point; naming it again with -p would
            # register the same module twice and pluggy rejects that. Autoload stays on.
            "--base-url", base_url,
            "--junitxml", str(run_dir / "junit.xml"),
            "--screenshot", "only-on-failure",
            # Traces carry cookies, headers and response bodies: off unless --trace, and then quarantined.
            "--tracing", "retain-on-failure" if trace else "off",
            "--output", str(run_dir / "artifacts"),
            "--browser", "chromium",
            *extra]
    if headed:
        argv.append("--headed")
    return argv


# --- secret masking (SPEC-03 §3.1) ---------------------------------------------------------------

def env_secret_values(env_path: Path) -> list[str]:
    """Every value of runtime/.env that may be a secret: all values except public configuration keys
    (ports, profile) and values too short to be a credential. Longest first so partial overlaps are
    replaced whole."""
    vals: set[str] = set()
    for key, value in read_env_file(env_path).items():
        if not value or key.startswith(PUBLIC_ENV_KEY_PREFIXES):
            continue
        if value.isdigit() or value.lower() in ("true", "false", "yes", "no", "on", "off") or len(value) < 4:
            continue
        vals.add(value)
    return sorted(vals, key=len, reverse=True)


def mask_text(text: str, secret_values: list[str]) -> str:
    """Replace every secret value (raw, XML-escaped, JSON-escaped, URL-quoted) and every token-like string."""
    if not text:
        return text
    for s in secret_values:
        for variant in {s, html.escape(s, quote=True), json.dumps(s)[1:-1], quote(s, safe="")}:
            if variant and variant in text:
                text = text.replace(variant, MASK)
    for pat in TOKEN_PATTERNS:
        text = pat.sub(lambda m: (m.group(1) if m.groups() else "") + MASK, text)
    return text


def mask_env_values(text: str, env_path: Path) -> str:
    """mask_text with the secrets of the given .env file."""
    return mask_text(text, env_secret_values(env_path))


def mask_data(data, secret_values: list[str]):
    """Recursive mask_text over JSON-like data (dict keys are kept)."""
    if isinstance(data, str):
        return mask_text(data, secret_values)
    if isinstance(data, list):
        return [mask_data(x, secret_values) for x in data]
    if isinstance(data, dict):
        return {k: mask_data(v, secret_values) for k, v in data.items()}
    return data


# --- evidence directory --------------------------------------------------------------------------

def make_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path, 0o700)  # nosemgrep: python.lang.security.audit.insecure-file-permissions.insecure-file-permissions -- owner-only evidence folder (SPEC-04)


def write_private(path: Path, text: str) -> None:
    """Write text as a 0600 file (created private, then chmod in case it already existed)."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.chmod(path, 0o600)


def mask_file(path: Path, secret_values: list[str]) -> None:
    if path.is_file() and not path.is_symlink():
        write_private(path, mask_text(path.read_text(encoding="utf-8", errors="replace"), secret_values))


def _is_image(name: str, head: bytes) -> bool:
    return name.lower().endswith(IMAGE_SUFFIXES) or any(head.startswith(m) for m in IMAGE_MAGIC)


def sanitize_zip_member(name: str, data: bytes, secret_values: list[str]) -> bytes | None:
    """Masked bytes of one ZIP member, or None when the member must be dropped.

    Text-like members (trace.trace, trace.network, trace.stacks, *.json, *.har, ...) are masked like
    any text file. `resources/*` members are response bodies: only images survive. Any other binary
    member is dropped too, because its content cannot be inspected (fail closed)."""
    lower = name.lower()
    is_body = lower.startswith(ZIP_BODY_PREFIX) or f"/{ZIP_BODY_PREFIX}" in lower
    if is_body:
        return data if _is_image(lower, data[:16]) else None
    if lower.endswith(ZIP_TEXT_SUFFIXES):
        return mask_text(data.decode("utf-8", errors="replace"), secret_values).encode("utf-8")
    if _is_image(lower, data[:16]):
        return data
    return None


def sanitize_zip(path: Path, secret_values: list[str]) -> dict[str, int]:
    """Rewrite a ZIP in place with every member passed through `sanitize_zip_member`.
    Returns {"kept": n, "dropped": m}. An unreadable archive is removed (it cannot be sanitized)."""
    tmp = path.with_name(path.name + ".sanitizing")
    kept = dropped = 0
    try:
        with zipfile.ZipFile(path) as src:
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "wb") as fh, zipfile.ZipFile(fh, "w", compression=zipfile.ZIP_DEFLATED) as dst:
                for info in src.infolist():
                    if info.is_dir():
                        continue
                    masked = sanitize_zip_member(info.filename, src.read(info), secret_values)
                    if masked is None:
                        dropped += 1
                        continue
                    dst.writestr(info.filename, masked)
                    kept += 1
    except (zipfile.BadZipFile, OSError):
        tmp.unlink(missing_ok=True)
        path.unlink(missing_ok=True)
        return {"kept": 0, "dropped": -1}
    os.replace(tmp, path)
    os.chmod(path, 0o600)
    return {"kept": kept, "dropped": dropped}


def restrict_tree(run_dir: Path) -> None:
    """Directories 0700, files 0600 under the run directory (screenshots and traces included)."""
    for root, dirs, files in os.walk(run_dir):
        os.chmod(root, 0o700)  # nosemgrep: python.lang.security.audit.insecure-file-permissions.insecure-file-permissions -- owner-only evidence folder (SPEC-04)
        for f in files:
            p = Path(root) / f
            if not p.is_symlink():
                os.chmod(p, stat.S_IRUSR | stat.S_IWUSR)


def sanitize_run_dir(run_dir: Path, secret_values: list[str]) -> None:
    """Mask every retained artefact under the run directory and lock permissions (SPEC-04 §7):
    text files by suffix (junit.xml, collector.json, pytest.log, *.har, *.json, *.txt, *.log, *.md)
    anywhere below it, ZIP archives member by member (`sanitize_zip`), screenshots untouched."""
    for root, _dirs, files in os.walk(run_dir):
        for f in files:
            p = Path(root) / f
            if p.is_symlink():
                continue
            lower = f.lower()
            if lower.endswith(TEXT_SUFFIXES):
                mask_file(p, secret_values)
            elif lower.endswith(".zip"):
                sanitize_zip(p, secret_values)
    restrict_tree(run_dir)


def quarantine_traces(run_dir: Path, quarantine_dir: Path) -> list[str]:
    """Move every *.zip under `run_dir` (Playwright traces) into `quarantine_dir` (0700, files 0600),
    preserving the path relative to the run directory. Returns the moved paths relative to
    `quarantine_dir`. The quarantine lives under runtime/ (git-ignored) and is not evidence."""
    moved: list[str] = []
    for src in sorted(run_dir.rglob("*.zip")):
        if src.is_symlink() or not src.is_file():
            continue
        rel = src.relative_to(run_dir)
        dst = quarantine_dir / rel
        make_private_dir(dst.parent)
        shutil.move(str(src), str(dst))
        os.chmod(dst, 0o600)
        moved.append(str(rel))
    if moved:
        restrict_tree(quarantine_dir)
    return moved


# --- integration precheck (SPEC-04 §2) -----------------------------------------------------------

def default_health_check(ctx: Context) -> tuple[list[dict], bool, str]:
    """(rows, all_ok, problem) from grdm_dev.health.check_services; imported lazily so `accept` stays
    importable without the health module's dependencies in unit tests."""
    from . import health

    path = health.compose_path(ctx)
    if not path.exists():
        return [], False, f"{path} not found; run `grdm-dev install` (or `compose render` + `up`) first"
    try:
        rows, ok = health.check_services(ctx, health.default_runner, health.default_prober)
    except ValueError as exc:
        return [], False, f"cannot parse {path}: {exc}"
    problems = [f"{r['service']} ({r['state']}, {r['health']}{', ' + r['http'] if r['http'] else ''})" for r in rows if not r["ok"]]
    return rows, ok, "; ".join(problems)


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
                    "known_external_blocked": int(r.get("known_external_blocked", 0)),
                })
            return rows
        except (ValueError, AttributeError):
            rows = []
    junit = run_dir / "junit.xml"
    if not junit.exists():
        return rows
    try:
        # junit.xml is written by our own pytest run into runtime-owned docs/demo/runs/; no untrusted XML.
        tree = ET.parse(junit)  # nosemgrep: python.lang.security.use-defused-xml-parse.use-defused-xml-parse
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
                     "evidence": _evidence_path(run_dir, nodeid), "known_external_blocked": 0})
    return rows


def write_results(run_dir: Path, data: dict) -> None:
    make_private_dir(run_dir)
    write_private(run_dir / "results.json", json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    write_private(run_dir / "results.toon", toon.encode(data, name="accept") + "\n")


# --- entry point ---------------------------------------------------------------------------------

def run(ctx: Context, args, runner=None, importer=None, now=None,
        health_check: Callable[[Context], tuple[list[dict], bool, str]] | None = None) -> int:
    runner = runner or default_runner
    health_check = health_check or default_health_check
    env_file = ctx.runtime / ".env"
    secret_values = env_secret_values(env_file)

    def fail(code: int, detail: str) -> int:
        return report.error(ctx, code, mask_text(detail, secret_values))

    missing = missing_modules(importer)
    if missing:
        return fail(exit_codes.USAGE, f"missing {', '.join(missing)}; run: {install_hint()}")

    base_url = (getattr(args, "base_url", None) or default_base_url(ctx)).rstrip("/")
    problem = loopback_problem(base_url)
    if problem:
        return fail(exit_codes.USAGE, f"--base-url {base_url}: {problem}")

    browsers = ctx.root / BROWSERS_PATH
    if chromium_executable(browsers) is None:
        return fail(exit_codes.USAGE, f"no Chromium executable under {browsers}; run: {install_hint()}")

    suite_dir = ACCEPTANCE_DIR
    if not (suite_dir / "conftest.py").is_file():
        return fail(exit_codes.USAGE, f"acceptance suite not found at {suite_dir}; reinstall: {install_hint()}")
    selection = select_tests(getattr(args, "only", None), suite_dir)
    if selection is None:
        return fail(exit_codes.USAGE, f"--only {args.only!r} matches no scenario in {suite_dir}")
    paths, extra = selection
    expected = expected_scenarios(paths, extra)

    # SPEC-04 §2: integration first; a browser run against a half-started stack is noise, not evidence.
    health_rows, healthy, health_problem = health_check(ctx)
    if not healthy:
        return fail(exit_codes.HEALTH_FAILED, f"integration precheck failed, acceptance not started: {health_problem}")

    started = now or _dt.datetime.now(_dt.timezone.utc)
    run_id = make_run_id(started)
    run_dir = ctx.root / "docs" / "demo" / "runs" / run_id
    make_private_dir(run_dir)
    users = seed_users(run_id)
    # Before anything can print them: the seed snippets, a seed error, pytest's output, the report.
    secret_values = sorted(set(secret_values) | set(seed_secret_values(users)), key=len, reverse=True)

    env = dict(ctx.env)
    env.update({
        "PLAYWRIGHT_BROWSERS_PATH": str(browsers),
        "GRDM_BASE_URL": base_url,
        "GRDM_RUN_ID": run_id,
        "GRDM_ENV_FILE": str(env_file),
        "GRDM_ACCEPT_RESULTS": str(run_dir / "collector.json"),
        "GRDM_ACCEPT_USER_A": users["user_a"]["email"],
        "GRDM_ACCEPT_USER_B": users["user_b"]["email"],
        "GRDM_ACCEPT_INSTITUTION_MEMBER": users["institution_member"]["email"],
        "GRDM_ACCEPT_OTHER_INSTITUTION_MEMBER": users["other_institution_member"]["email"],
        "GRDM_ACCEPT_ADMIN": users["admin_user"]["email"],
        "GRDM_ACCEPT_ADMIN_OSF_PASSWORD": users["admin_user"]["osf_password"],  # masked with the other run secrets
        "GRDM_ACCEPT_ADMIN_TOTP_SECRET": users["admin_user"]["totp_secret"],
    })

    seeded = False
    if getattr(args, "seed", False):
        for u in users.values():
            two_factor = TWO_FACTOR_SNIPPET.format(totp_secret=u["totp_secret"]) if u.get("totp_secret") else ""
            snippet = SEED_SNIPPET.format(email=u["email"], osf_password=u["osf_password"], fullname=u["fullname"], admin=u["admin"], institutions=u["institutions"], two_factor=two_factor)
            rc, out = runner(compose_exec(ctx, "web", "python3", "manage.py", "shell", "-c", snippet), env=env, cwd=ctx.root)
            if rc != 0:
                return fail(exit_codes.SERVICES_UNHEALTHY, f"seed failed for {u['email']}: {out.strip()[-400:]}")
        seeded = True

    trace = bool(getattr(args, "trace", False))
    try:
        rc, out = runner(pytest_argv(paths, extra, run_dir, base_url, getattr(args, "headed", False), trace=trace), env=env, cwd=ctx.root)
    finally:
        if seeded:
            cleanup = CLEANUP_SNIPPET.format(domain=SEED_DOMAIN, run_id=run_id)
            crc, cout = runner(compose_exec(ctx, "web", "python3", "manage.py", "shell", "-c", cleanup), env=env, cwd=ctx.root)
            if crc != 0:
                sys.stderr.write(mask_text(f"warning: cleanup of seeded users failed: {cout.strip()[-200:]}\n", secret_values))
    # Traces (cookies, headers, bodies) never stay under docs/demo/runs/: quarantine first, then
    # sanitize whatever remains (any ZIP still present is rewritten member by member).
    quarantine_dir = ctx.runtime / QUARANTINE_SUBDIR / run_id
    quarantined = quarantine_traces(run_dir, quarantine_dir)
    write_private(run_dir / "pytest.log", mask_text(out, secret_values))
    sanitize_run_dir(run_dir, secret_values)

    rows = mask_data(collect_results(run_dir), secret_values)
    finished = _dt.datetime.now(_dt.timezone.utc)
    summary = {s: sum(1 for r in rows if r["status"] == s) for s in ("passed", "failed", "error", "skipped")}
    summary["total"] = len(rows)
    summary["known_external_blocked"] = sum(int(r.get("known_external_blocked", 0)) for r in rows)  # SPEC-04 §3 rule 4
    missing_cases = incomplete_scenarios(rows, expected)
    data = {
        "run_id": run_id,
        "base_url": base_url,
        "started": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration_ms": int((finished - started).total_seconds() * 1000) if now is None else sum(r["duration_ms"] for r in rows),
        "only": getattr(args, "only", None),
        "seeded": seeded,
        "precheck": {"healthy": healthy, "services": len(health_rows)},
        "pytest_returncode": rc,
        "evidence_dir": str(run_dir.relative_to(ctx.root)) if run_dir.is_relative_to(ctx.root) else str(run_dir),
        "tracing": "retain-on-failure" if trace else "off",
        "trace_quarantine": {
            "dir": str(quarantine_dir.relative_to(ctx.root)) if quarantine_dir.is_relative_to(ctx.root) else str(quarantine_dir),
            "files": quarantined,
            "note": "Playwright traces are not sanitized evidence: they stay under runtime/ (0700, git-ignored) and are never copied into docs/demo/runs/ or a report bundle.",
        } if quarantined else None,
        "expected_scenarios": expected,
        "incomplete_scenarios": missing_cases,
        "summary": summary,
        "tests": rows,
    }
    data = mask_data(data, secret_values)
    write_results(run_dir, data)
    restrict_tree(run_dir)
    report.emit(ctx, "accept", data)

    if rc == 5:  # pytest: no tests collected
        return fail(exit_codes.USAGE, "pytest collected no tests")
    if not rows:
        return fail(exit_codes.ACCEPTANCE_FAILED, f"no result rows were collected (pytest exit {rc}); see {run_dir}")
    if rc != 0 or summary["failed"] or summary["error"]:
        return fail(exit_codes.ACCEPTANCE_FAILED, f"{summary['failed'] + summary['error']} failing test(s); see {run_dir}")
    if missing_cases:
        return fail(exit_codes.ACCEPTANCE_FAILED,
                    f"scenario(s) without both a success and a rejection row: {', '.join(missing_cases)}; see {run_dir}")
    return exit_codes.OK
