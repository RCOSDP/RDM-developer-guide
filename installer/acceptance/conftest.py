"""Shared fixtures and hooks of the acceptance suite (SPEC-04 §3, §6, §7).

Everything the tests need to know about the environment arrives through environment variables that
`grdm-dev accept` sets (GRDM_BASE_URL, GRDM_RUN_ID, GRDM_ENV_FILE, GRDM_ACCEPT_RESULTS,
GRDM_ACCEPT_USER_A/B, GRDM_ACCEPT_ADMIN) or through pytest's own --base-url option. Nothing else on
the host is read (SPEC-04 §6). Hooks here enforce the per-test and per-suite time boxes, block every
request that would leave 127.0.0.1 (browser requests, WebSockets, service workers and API request
contexts alike), and write collector.json for results.json.

Network rule (SPEC-04 §3.4): a test never touches `playwright.request.new_context()`,
`browser.new_context()` or `<context>.request` directly. It asks for the `api_context`,
`new_context` fixtures or wraps a context with `api(context)`, so every URL is checked with
`netguard.is_loopback_origin` before it is sent and after it is answered.
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

import pytest

from acceptance import selectors as sel
from acceptance.netguard import (
    HTTP_SCHEMES,
    MAX_REDIRECT_HOPS,
    WEBSOCKET_ROUTE_REQUIREMENT,
    WS_SCHEMES,
    forced_redirect_kwargs,
    is_loopback_origin,
    known_external_asset_host,
    redirect_follow_up,
    redirect_target,
)

TEST_TIMEOUT_S = 120          # SPEC-04 §3.3
SUITE_TIMEOUT_S = 30 * 60
DEFAULT_PORTS = {"WEB": 5000, "API": 8000, "ADMIN": 8001, "WB": 7777, "MFR": 7778, "FAKECAS": 8080, "EMBER_OSF_WEB": 4200}

_SESSION_START = time.monotonic()
_RESULTS: dict[str, dict[str, Any]] = {}
# Every non-loopback URL any guard saw during the session; the autouse guard fails the test on it.
_OFFENDERS: list[str] = []
# Hosts of the KNOWN_EXTERNAL_ASSETS requests that were aborted (SPEC-04 §3 rule 4): counted, not failing.
_KNOWN_EXTERNAL: list[str] = []


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
    if not is_loopback_origin(url, HTTP_SCHEMES):
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
def institution_member(run_id) -> dict[str, str]:
    """Affiliated with admin_user's institution; only listed by C6, never signs in."""
    return _user("GRDM_ACCEPT_INSTITUTION_MEMBER", "institution-member", run_id)


@pytest.fixture(scope="session")
def other_institution_member(run_id) -> dict[str, str]:
    """Affiliated only with another institution than admin_user's; C6 must not list it. Never signs in."""
    return _user("GRDM_ACCEPT_OTHER_INSTITUTION_MEMBER", "other-institution-member", run_id)


@pytest.fixture(scope="session")
def admin_user(run_id) -> dict[str, str]:
    """The admin app has its own password form, checked against the OSF account, not fakecas's e-mail rule."""
    user = _user("GRDM_ACCEPT_ADMIN", "admin-user", run_id)
    # The admin app asks a second factor after the password (RDM-osf.io-dev2027 PR #10): `accept --seed` enrols the
    # seeded administrator with this secret (hexadecimal). Without it the second step cannot be answered.
    return {**user, "password": os.environ.get("GRDM_ACCEPT_ADMIN_OSF_PASSWORD", user["password"]),
            "totp_secret": os.environ.get("GRDM_ACCEPT_ADMIN_TOTP_SECRET", "")}


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


# --- network guard (SPEC-04 §3.4) ----------------------------------------------------------------

class GuardedRequest:
    """Wraps a Playwright APIRequestContext: every URL is checked before sending, Playwright never
    follows a redirect itself (`max_redirects` is forced to 0; a caller passing another value gets a
    ValueError), and the answered URL is checked as well. A 3xx answer is followed by the wrapper, at
    most MAX_REDIRECT_HOPS times, only while each resolved Location is a loopback origin; any hop that
    would leave the machine fails the test before it is sent.

    Attribute access other than the HTTP verbs is delegated (dispose, storage_state, ...).
    """

    VERBS = ("get", "post", "put", "patch", "delete", "head", "fetch")

    def __init__(self, request_context, offenders: list[str] | None = None):
        self._rc = request_context
        self._offenders = offenders if offenders is not None else _OFFENDERS

    def _refuse(self, url: str, why: str) -> None:
        self._offenders.append(url)
        pytest.fail(f"{why}: {url!r} is not http://127.0.0.1:<port> (SPEC-04 §3.4, ADR-02)")

    def _call(self, verb: str, url: str, **kwargs):
        # follow_redirects=False returns the first answer (a rejection test wants to see the 302 itself);
        # its Location is still checked to be a loopback origin before the response is handed back.
        follow = bool(kwargs.pop("follow_redirects", True))
        kwargs = forced_redirect_kwargs(kwargs)  # ValueError on a non-zero max_redirects
        hop_verb, hop_url, hop_kwargs = verb, url, kwargs
        for hop in range(MAX_REDIRECT_HOPS + 1):
            if not isinstance(hop_url, str) or not is_loopback_origin(hop_url, HTTP_SCHEMES):
                self._refuse(str(hop_url), f"refusing API {hop_verb.upper()}" + (f" (redirect hop {hop} of {url!r})" if hop else ""))
            resp = getattr(self._rc, hop_verb)(hop_url, **hop_kwargs)
            if not is_loopback_origin(resp.url, HTTP_SCHEMES):
                self._refuse(resp.url, f"API {hop_verb.upper()} {hop_url!r} was answered from another origin")
            target = redirect_target(resp.url, resp.status, getattr(resp, "headers", None))
            if target is None:
                return resp
            if not is_loopback_origin(target, HTTP_SCHEMES):
                self._refuse(target, f"API {hop_verb.upper()} {hop_url!r} redirects ({resp.status}) off the machine")
            if not follow:
                return resp
            hop_verb, hop_kwargs = redirect_follow_up(hop_verb, resp.status, hop_kwargs)
            hop_url = target
        pytest.fail(f"API {verb.upper()} {url!r}: more than {MAX_REDIRECT_HOPS} redirect hops (SPEC-04 §3.4)")

    def __getattr__(self, name: str):
        if name in self.VERBS:
            return lambda url, **kw: self._call(name, url, **kw)
        return getattr(self._rc, name)


def api(context) -> GuardedRequest:
    """api(browser_context) -> guarded view of `context.request` (session cookies included)."""
    if isinstance(context, GuardedRequest):
        return context
    return GuardedRequest(context.request)


def guard_context(context, offenders: list[str] | None = None) -> None:
    """Abort any browser request, WebSocket or service worker that would leave loopback and remember
    it (SPEC-04 §3.4). Installed on the context *and* on every page it opens.

    Fails closed: without `BrowserContext.route_web_socket` (Playwright < 1.48) WebSockets could not be
    intercepted, so the guard refuses to run at all instead of guarding silently less."""
    if not callable(getattr(context, "route_web_socket", None)):
        raise RuntimeError(WEBSOCKET_ROUTE_REQUIREMENT)
    seen = offenders if offenders is not None else _OFFENDERS

    def _route(route):
        if is_loopback_origin(route.request.url, HTTP_SCHEMES):
            route.continue_()
        else:
            host = known_external_asset_host(route.request.url, route.request.resource_type)
            if host:
                _KNOWN_EXTERNAL.append(host)
            else:
                seen.append(route.request.url)
            route.abort("blockedbyclient")

    def _ws_route(ws):
        if is_loopback_origin(ws.url, WS_SCHEMES):
            ws.connect_to_server()  # frames are forwarded unchanged when no handlers are installed
        else:
            seen.append(ws.url)
            ws.close(code=1008, reason="blocked: non-loopback websocket")

    def _network_url(url: str) -> bool:
        return url.split(":", 1)[0].lower() in ("http", "https", "ws", "wss")  # blob:/data: workers are local

    def _watch_page(page):
        page.route("**/*", _route)
        page.on("websocket", lambda ws: None if is_loopback_origin(ws.url, WS_SCHEMES) else seen.append(ws.url))
        page.on("worker", lambda w: seen.append(w.url) if _network_url(w.url) and not is_loopback_origin(w.url, HTTP_SCHEMES) else None)

    context.route("**/*", _route)
    context.route_web_socket("**/*", _ws_route)
    context.on("serviceworker", lambda w: seen.append(w.url))  # blocked by browser_context_args too
    context.on("page", _watch_page)
    for page in context.pages:
        _watch_page(page)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """pytest-playwright's context arguments plus: service workers never run (they could bypass routes)."""
    return {**browser_context_args, "service_workers": "block"}


@pytest.fixture(autouse=True)
def external_guard(request):
    """Collect the loopback-guard offenders of one test and fail it if any guard (browser, websocket,
    API) saw a URL that would have left the machine. Every browser context is created by our
    `new_context` below (pytest-playwright's default `context` fixture calls it too), which attaches
    the guard itself; requesting `context` from here created a fixture cycle
    (external_guard -> context -> new_context -> external_guard, first real acceptance run)."""
    offenders: list[str] = []
    before = len(_OFFENDERS)
    known_before = len(_KNOWN_EXTERNAL)
    yield offenders
    offenders.extend(_OFFENDERS[before:])
    request.node.user_properties.append(("known_external_blocked", len(_KNOWN_EXTERNAL) - known_before))
    if offenders:
        pytest.fail(f"request(s) would have left the machine: {offenders[:5]}")


@pytest.fixture
def new_context(browser, browser_context_args, external_guard):
    """new_context() -> a fresh, guarded browser context (own cookies); all are closed in teardown."""
    created = []

    def _new(**overrides):
        ctx = browser.new_context(**{**browser_context_args, **overrides, "service_workers": "block"})
        guard_context(ctx, external_guard)
        created.append(ctx)
        return ctx

    yield _new
    for ctx in created:
        ctx.close()


@pytest.fixture
def api_context(playwright, external_guard):
    """api_context() -> a guarded, cookie-less APIRequestContext (the anonymous caller); disposed in teardown."""
    created = []

    def _new(**kwargs) -> GuardedRequest:
        rc = playwright.request.new_context(**kwargs)
        created.append(rc)
        return GuardedRequest(rc, external_guard)

    yield _new
    for rc in created:
        rc.dispose()


# --- browser helpers -----------------------------------------------------------------------------

@pytest.fixture
def login(base_url, service_url):
    """login(page, user): fakecas flow — web /login -> fakecas form -> back to the dashboard."""
    def _login(page, user: dict[str, str]) -> None:
        page.goto(base_url + sel.PATHS["login"], wait_until="domcontentloaded")
        # web answers 302 to fakecas (/login?service=...), whose page is the form itself (confirmed on the
        # real stack, acceptance run 5). fakecas identifies the user by e-mail alone: its password field sits
        # inside a `<section hidden>` and is never shown, so it is filled only when a build makes it visible.
        page.wait_for_selector(sel.FAKECAS["username"], timeout=30_000)
        page.fill(sel.FAKECAS["username"], user["email"])
        pw = page.locator(sel.FAKECAS["password"])
        if pw.count() and pw.first.is_visible():
            pw.first.fill(user["password"])
        page.click(sel.FAKECAS["submit"])
        page.wait_for_url(re.compile(re.escape(base_url) + r"/(dashboard|myprojects)"), timeout=60_000)
    return _login


@pytest.fixture
def logged_in_page(page, login, user_a):
    login(page, user_a)
    return page


@pytest.fixture
def context_b(new_context, login, user_b):
    """A second guarded browser context signed in as user_b (the non-contributor / second person)."""
    ctx = new_context()
    login(ctx.new_page(), user_b)
    return ctx


@pytest.fixture
def two_contexts(new_context):
    """Two independent browser contexts (own cookies) for C4; both guarded, both closed."""
    return new_context().new_page(), new_context().new_page()


def csrf_headers(context) -> dict[str, str]:
    """Session-cookie writes to the OSF API need the CSRF token. TODO(M2): confirm cookie/header names."""
    for c in context.cookies():
        if c["name"] in ("api-csrf", "csrftoken"):
            return {"X-CSRFToken": c["value"], "Referer": "http://127.0.0.1/"}
    return {}


def user_id_of(context, api_url: str) -> str:
    """The API id of the user signed in to `context`."""
    me = api(context).get(api_url + sel.API["me"])
    assert me.status == 200, f"GET {sel.API['me']} answered {me.status}"
    return me.json()["data"]["id"]


@pytest.fixture
def api_write():
    """api_write(context, method, url, json) -> response, using the context's session cookies."""
    def _write(context, method: str, url: str, data: dict | None = None):
        headers = {"Content-Type": "application/vnd.api+json", **csrf_headers(context)}
        return getattr(api(context), method.lower())(url, data=json.dumps(data) if data is not None else None, headers=headers)
    return _write


@pytest.fixture
def add_contributor(api_url, api_write):
    """add_contributor(owner_context, node_id, user_id, permission) -> adds a contributor; asserts 201."""
    def _add(owner_ctx, node_id: str, user_id: str, permission: str):
        resp = api_write(owner_ctx, "POST", api_url + sel.API["node_contributors"].format(node_id=node_id), {
            "data": {"type": "contributors", "attributes": {"permission": permission, "bibliographic": False},
                     "relationships": {"users": {"data": {"type": "users", "id": user_id}}}}
        })
        assert resp.status == 201, f"adding {permission} contributor failed: {resp.status} {resp.text()[:200]}"
        return resp
    return _add


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
        "status": "passed", "duration_ms": 0, "http_status": None, "evidence": None, "known_external_blocked": 0,
    })
    rec["duration_ms"] += int(rep.duration * 1000)
    for k, v in rep.user_properties:
        if k == "http_status":
            rec["http_status"] = v
        elif k == "known_external_blocked":
            rec["known_external_blocked"] = v
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
