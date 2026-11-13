"""S1 — y-websocket (SPEC-04 §5). Subsystem scenario; runs at M3.

Design (skip-marked "M3" until the subsystem is installed and the selectors below are verified):

* success — two guarded browser contexts (user_a owner, user_b write contributor) open the same Wiki
  page of a fresh project; a sentence typed in context A appears in context B within 5 s. The
  WebSocket the page opens is captured with `page.on("websocket")` so the test can prove the
  collaboration path really went through y-websocket (ws://127.0.0.1:<port>; the loopback guard
  in conftest already aborts anything else).
* rejection — the captured WebSocket URL is reopened from a logged-out context with the token
  removed. The server must close it with code 4401 (RDM-osf.io#797, RDM-wiki-frontend#15) and no
  document frame may arrive before the close.

Network rule: only `new_context`, `two_contexts`, `api(context)` from conftest are used.
"""
from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest

from acceptance import selectors as sel
from acceptance.conftest import scaled, user_id_of
from acceptance.netguard import WS_SCHEMES, is_loopback_origin

pytestmark = [pytest.mark.subsystem, pytest.mark.scenario("S1", "y-websocket"), pytest.mark.skip(reason="M3")]

CONVERGE_TIMEOUT_MS = 5_000           # SPEC-04 §5: "within 5 s"
TOKEN_CLOSE_CODE = 4401               # SPEC-04 §5 rejection; same code C4 asserts
TOKEN_QUERY_KEYS = ("token", "jwt", "access_token")   # TODO(M3): the exact query key the wiki client sends

# TODO(M3): move to selectors.py once verified on the real wiki page (README: locators live in one table).
_SEL = {
    "wiki_tab": sel.WEB["wiki_tab"],
    "wiki_edit": sel.WEB["wiki_edit_button"],
    "wiki_editor": sel.WEB["wiki_editor"],      # .CodeMirror textarea / textarea#editor
    "wiki_rendered": sel.WEB["wiki_rendered"],
}


def _wiki_url(base_url: str, node_id: str) -> str:
    return f"{base_url}/{node_id}/wiki/home/"   # TODO(M3): confirm the wiki home path of RDM-wiki-frontend


def _strip_token(ws_url: str) -> str:
    """The same WebSocket URL without its auth token (query or last path segment), still on loopback."""
    parts = urlsplit(ws_url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in TOKEN_QUERY_KEYS]
    stripped = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))
    assert is_loopback_origin(stripped, WS_SCHEMES), stripped
    return stripped


def _open_wiki(page, base_url: str, node_id: str) -> list:
    """Open the wiki editor and return the list that collects the WebSockets the page opens."""
    sockets: list = []
    page.on("websocket", sockets.append)
    page.goto(_wiki_url(base_url, node_id), wait_until="domcontentloaded")
    page.click(_SEL["wiki_edit"])
    page.wait_for_selector(_SEL["wiki_editor"], timeout=scaled(30_000))
    return sockets


@pytest.mark.case("success")
def test_s1_y_websocket_success(two_contexts, login, user_a, user_b, project, base_url, api_url, add_contributor, run_id, record_property):
    """Two contexts converge on the same Wiki document within 5 s through y-websocket."""
    page_a, page_b = two_contexts
    login(page_a, user_a)
    login(page_b, user_b)
    add_contributor(page_a.context, project, user_id_of(page_b.context, api_url), "write")

    sockets_a = _open_wiki(page_a, base_url, project)
    sockets_b = _open_wiki(page_b, base_url, project)
    sentence = f"s1 converge {run_id}"
    page_a.type(_SEL["wiki_editor"], sentence)

    # B must see A's text within the time box; polling the editor text is deterministic (SPEC-04 §3.2).
    page_b.wait_for_function(
        "([selector, text]) => (document.querySelector(selector)?.value ?? document.querySelector(selector)?.textContent ?? '').includes(text)",
        arg=[_SEL["wiki_editor"], sentence],
        timeout=CONVERGE_TIMEOUT_MS,
    )
    record_property("http_status", 101)   # the WebSocket upgrade
    ws_urls = [ws.url for ws in sockets_a + sockets_b]
    assert ws_urls, "the wiki page opened no WebSocket: collaboration did not go through y-websocket"
    assert all(is_loopback_origin(u, WS_SCHEMES) for u in ws_urls), ws_urls
    assert all(re.search(r"/(ws|yjs|y-websocket)", urlsplit(u).path) for u in ws_urls), f"unexpected ws path: {ws_urls}"  # TODO(M3): exact path


@pytest.mark.case("rejection")
def test_s1_y_websocket_rejection(logged_in_page, project, base_url, new_context, record_property):
    """A connection without a valid token is closed with 4401 and leaks no document state."""
    sockets = _open_wiki(logged_in_page, base_url, project)
    assert sockets, "no WebSocket captured from the editor page"
    anonymous_url = _strip_token(sockets[0].url)

    anon = new_context()                 # fresh cookies: a logged-out browser
    page = anon.new_page()
    page.goto(base_url + sel.PATHS["login"], wait_until="domcontentloaded")   # any loopback page as the script's origin
    outcome = page.evaluate(
        """(url) => new Promise((resolve) => {
             const ws = new WebSocket(url);
             let frames = 0;
             ws.binaryType = 'arraybuffer';
             ws.onmessage = () => { frames += 1; };
             ws.onclose = (ev) => resolve({code: ev.code, reason: ev.reason, frames});
             ws.onerror = () => {};
             setTimeout(() => { try { ws.close(); } catch (e) {} resolve({code: -1, reason: 'timeout', frames}); }, 10000);
           })""",
        anonymous_url,
    )
    record_property("http_status", outcome["code"])
    assert outcome["code"] == TOKEN_CLOSE_CODE, f"expected close code {TOKEN_CLOSE_CODE}, got {outcome}"
    assert outcome["frames"] == 0, f"document frames were sent before the close: {outcome}"
