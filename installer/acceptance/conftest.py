"""Shared fixtures and hooks of the acceptance suite (SPEC-04 §3, §6, §7).

Everything the tests need to know about the environment arrives through environment variables that
`grdm-dev accept` sets (GRDM_BASE_URL, GRDM_RUN_ID, GRDM_ENV_FILE, GRDM_ACCEPT_RESULTS,
GRDM_ACCEPT_USER_A/B, GRDM_ACCEPT_ADMIN) or through pytest's own --base-url option. Nothing else on
the host is read (SPEC-04 §6). Hooks here enforce the per-test and per-suite time boxes, block every
request that would leave 127.0.0.1, and write collector.json for results.json.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import signal
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import pytest

from acceptance import selectors as sel

TEST_TIMEOUT_S = 120          # SPEC-04 §3.3
SUITE_TIMEOUT_S = 30 * 60
LOOPBACK_HOSTS = {"127.0.0.1"}
DEFAULT_PORTS = {"WEB": 5000, "API": 8000, "ADMIN": 8001, "WB": 7777, "MFR": 7778, "FAKECAS": 8080, "EMBER_OSF_WEB": 4200}

_SESSION_START = time.monotonic()
_RESULTS: dict[str, dict[str, Any]] = {}


# --- environment ---------------------------------------------------------------------------------

def _read_env_file(path: str | None) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path or not Path(path).exists():
        return env
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _assert_loopback(url: str) -> str:
    host = urlparse(url).hostname
    if host not in LOOPBACK_HOSTS:
        pytest.fail(f"refusing non-loopback URL {url!r}: acceptance tests never leave this machine (ADR-02)")
    return url.rstrip("/")


@pytest.fixture(scope="session")
def run_id() -> str:
    return os.environ.get("GRDM_RUN_ID") or f"acc-{_dt.datetime.now(_dt.timezone.utc):%Y%m%dT%H%M%SZ}-local"


@pytest.fixture(scope="session")
def ports() -> dict[str, int]:
    """Host ports from runtime/.env (GRDM_PORT_<SERVICE>), falling back to the SPEC-02 §4 defaults."""
    env = _read_env_file(os.environ.get("GRDM_ENV_FILE"))
    out = dict(DEFAULT_PORTS)
    for k, v in env.items():
        if k.startswith("GRDM_PORT_") and v.isdigit():
            out[k[len("GRDM_PORT_"):]] = int(v)
    return out


@pytest.fixture(scope="session")
def base_url(request, ports) -> str:
    """Overrides pytest-base-url's fixture: env GRDM_BASE_URL, then --base-url, then the web port."""
    url = os.environ.get("GRDM_BASE_URL") or request.config.getoption("base_url", default=None) or f"http://127.0.0.1:{ports['WEB']}"
    return _assert_loopback(url)


@pytest.fixture(scope="session")
def service_url(ports) -> Callable[[str], str]:
    def _url(service: str) -> str:
        return f"http://127.0.0.1:{ports[service.upper()]}"
    return _url


@pytest.fixture(scope="session")
def api_url(service_url) -> str:
    return service_url("api")


# --- disposable users (SPEC-04 §6; created by `grdm-dev accept --seed`) --------------------------

def _user(env_key: str, fallback: str, run_id: str) -> dict[str, str]:
    email = os.environ.get(env_key) or f"{fallback}-{run_id}@acceptance.test"
    # fakecas accepts any username; the password is the user's e-mail (upstream README-docker-compose).
    return {"email": email, "password": email}


@pytest.fixture(scope="session")
def user_a(run_id) -> dict[str, str]:
    return _user("GRDM_ACCEPT_USER_A", "user-a", run_id)


@pytest.fixture(scope="session")
def user_b(run_id) -> dict[str, str]:
    return _user("GRDM_ACCEPT_USER_B", "user-b", run_id)


@pytest.fixture(scope="session")
def admin_user(run_id) -> dict[str, str]:
    return _user("GRDM_ACCEPT_ADMIN", "admin-user", run_id)


# --- generated test files (never real files of real people) --------------------------------------

@pytest.fixture(scope="session")
def tmp_txt(run_id) -> bytes:
    line = f"grdm acceptance {run_id} mock data\n".encode()
    return (line * (1024 * 1024 // len(line) + 1))[: 1024 * 1024]


@pytest.fixture(scope="session")
def tmp_pdf(run_id) -> bytes:
    """A minimal single-page PDF padded to 1 KiB."""
    body = (
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]/Contents 4 0 R>>endobj\n"
        b"4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 10 50 Td (MOCK " + run_id.encode()[:12] + b") Tj ET\nendstream\nendobj\n"
        b"trailer<</Root 1 0 R>>\n%%EOF\n"
    )
    return body + b"%" * max(0, 1024 - len(body) - 1) + b"\n"


# --- browser helpers -----------------------------------------------------------------------------

def guard_context(context, offenders: list[str]) -> None:
    """Abort any request whose host is not loopback and remember it (SPEC-04 §3.4)."""
    def _route(route):
        host = urlparse(route.request.url).hostname
        if host in LOOPBACK_HOSTS:
            route.continue_()
        else:
            offenders.append(route.request.url)
            route.abort("blockedbyclient")
    context.route("**/*", _route)


@pytest.fixture(autouse=True)
def external_guard(request):
    """Attach the loopback guard to the default `context` fixture when a test uses it."""
    offenders: list[str] = []
    if "context" in request.fixturenames:
        guard_context(request.getfixturevalue("context"), offenders)
    yield offenders
    if offenders:
        pytest.fail(f"request(s) left the machine: {offenders[:5]}")


@pytest.fixture
def login(base_url, service_url):
    """login(page, user): fakecas flow — web /login -> fakecas form -> back to the dashboard."""
    def _login(page, user: dict[str, str]) -> None:
        page.goto(base_url + sel.PATHS["login"], wait_until="domcontentloaded")
        # web redirects to fakecas (port FAKECAS). TODO(M2): confirm the redirect lands on the form directly.
        page.wait_for_selector(sel.FAKECAS["username"], timeout=30_000)
        page.fill(sel.FAKECAS["username"], user["email"])
        page.fill(sel.FAKECAS["password"], user["password"])
        page.click(sel.FAKECAS["submit"])
        page.wait_for_url(re.compile(re.escape(base_url) + r"/(dashboard|myprojects)"), timeout=60_000)
    return _login


@pytest.fixture
def logged_in_page(page, login, user_a):
    login(page, user_a)
    return page


@pytest.fixture
def two_contexts(browser, external_guard):
    """Two independent browser contexts (own cookies) for C4; both guarded, both closed."""
    a = browser.new_context()
    b = browser.new_context()
    guard_context(a, external_guard)
    guard_context(b, external_guard)
    try:
        yield a.new_page(), b.new_page()
    finally:
        a.close()
        b.close()


def csrf_headers(context) -> dict[str, str]:
    """Session-cookie writes to the OSF API need the CSRF token. TODO(M2): confirm cookie/header names."""
    for c in context.cookies():
        if c["name"] in ("api-csrf", "csrftoken"):
            return {"X-CSRFToken": c["value"], "Referer": "http://127.0.0.1/"}
    return {}


@pytest.fixture
def api_write():
    """api_write(context, method, url, json) -> response, using the context's session cookies."""
    def _write(context, method: str, url: str, data: dict | None = None):
        headers = {"Content-Type": "application/vnd.api+json", **csrf_headers(context)}
        return getattr(context.request, method.lower())(url, data=json.dumps(data) if data is not None else None, headers=headers)
    return _write


@pytest.fixture
def project(logged_in_page, api_url, api_write):
    """A fresh private project owned by user_a, deleted in teardown. Yields the node id."""
    ctx = logged_in_page.context
    resp = api_write(ctx, "POST", f"{api_url}{sel.API['nodes']}", {
        "data": {"type": "nodes", "attributes": {"title": "acceptance project", "category": "project", "public": False}}
    })
    assert resp.status == 201, f"project create failed: {resp.status} {resp.text()[:300]}"
    node_id = resp.json()["data"]["id"]
    try:
        yield node_id
    finally:
        api_write(ctx, "DELETE", f"{api_url}{sel.API['node'].format(node_id=node_id)}")


# --- hooks: markers, time boxes, result collector ------------------------------------------------

def pytest_configure(config):
    for m in ("core: M2 core scenario", "subsystem: M3 subsystem scenario",
              "scenario(id, name): scenario id and name", "case(kind): success or rejection"):
        config.addinivalue_line("markers", m)


def pytest_runtest_setup(item):
    if time.monotonic() - _SESSION_START > SUITE_TIMEOUT_S:
        pytest.fail("suite time box of 30 minutes exceeded (SPEC-04 §3.3)")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    if hasattr(signal, "SIGALRM"):
        def _timeout(signum, frame):
            raise TimeoutError(f"test exceeded {TEST_TIMEOUT_S}s (SPEC-04 §3.3)")
        old = signal.signal(signal.SIGALRM, _timeout)
        signal.alarm(TEST_TIMEOUT_S)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)
    else:  # pragma: no cover - Windows is not a supported host
        yield


def _marker_arg(item, name: str, index: int = 0):
    m = item.get_closest_marker(name)
    return m.args[index] if m and len(m.args) > index else None


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    rec = _RESULTS.setdefault(item.nodeid, {
        "nodeid": item.nodeid,
        "id": _marker_arg(item, "scenario", 0),
        "name": _marker_arg(item, "scenario", 1),
        "case": _marker_arg(item, "case", 0),
        "status": "passed", "duration_ms": 0, "http_status": None, "evidence": None,
    })
    rec["duration_ms"] += int(rep.duration * 1000)
    for k, v in rep.user_properties:
        if k == "http_status":
            rec["http_status"] = v
    if rep.when == "call" or rep.outcome != "passed":
        if rep.skipped:
            rec["status"] = "skipped"
        elif rep.failed:
            rec["status"] = "failed" if rep.when == "call" else "error"


def pytest_sessionfinish(session, exitstatus):
    out = os.environ.get("GRDM_ACCEPT_RESULTS")
    if not out:
        return
    output_dir = session.config.getoption("--output", default=None)
    for rec in _RESULTS.values():
        if output_dir and rec["status"] in ("failed", "error"):
            slug = re.sub(r"[^a-zA-Z0-9]+", "-", rec["nodeid"]).strip("-")
            for cand in Path(output_dir).glob("*"):
                if cand.is_dir() and (cand.name == slug[: len(cand.name)] or slug.endswith(cand.name)):
                    rec["evidence"] = str(cand)
                    break
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(list(_RESULTS.values()), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
