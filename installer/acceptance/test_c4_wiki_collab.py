"""C4 — Wiki collaborative edit with two browser contexts (SPEC-04 §4). Services: web, y_websocket, sharejs.

Never skipped: y_websocket belongs to the `core` profile (SPEC-02 §4).
"""
import pytest

from acceptance import selectors as sel
from acceptance.conftest import csrf_headers

pytestmark = [pytest.mark.core, pytest.mark.scenario("C4", "Wiki collaborative edit")]

CONVERGE_MS = 5_000  # SPEC-04 §5 S1 budget, reused for the M2 case


def _wiki_edit_url(base_url: str, node_id: str) -> str:
    return f"{base_url}/{node_id}/wiki/home/?edit&view&menu"  # TODO(M2): confirm the edit-mode query string


def _add_write_contributor(ctx_a, api_url: str, node_id: str, user_id: str) -> None:
    headers = {"Content-Type": "application/vnd.api+json", **csrf_headers(ctx_a)}
    resp = ctx_a.request.post(api_url + sel.API["node_contributors"].format(node_id=node_id), headers=headers, data=
        '{"data":{"type":"contributors","attributes":{"permission":"write","bibliographic":false},'
        '"relationships":{"users":{"data":{"type":"users","id":"%s"}}}}}' % user_id)
    assert resp.status == 201, f"adding write contributor failed: {resp.status} {resp.text()[:200]}"


@pytest.mark.case("success")
def test_c4_wiki_collab_success(two_contexts, login, user_a, user_b, base_url, api_url, run_id, record_property):
    """Both users open the same wiki page; text typed by B appears in A's editor."""
    page_a, page_b = two_contexts
    login(page_a, user_a)
    login(page_b, user_b)

    headers = {"Content-Type": "application/vnd.api+json", **csrf_headers(page_a.context)}
    created = page_a.context.request.post(api_url + sel.API["nodes"], headers=headers, data=
        '{"data":{"type":"nodes","attributes":{"title":"acceptance C4","category":"project","public":false}}}')
    assert created.status == 201, created.text()[:200]
    node_id = created.json()["data"]["id"]
    try:
        b_id = page_b.context.request.get(api_url + sel.API["me"]).json()["data"]["id"]
        _add_write_contributor(page_a.context, api_url, node_id, b_id)

        resp_a = page_a.goto(_wiki_edit_url(base_url, node_id), wait_until="domcontentloaded")
        record_property("http_status", resp_a.status if resp_a else None)
        page_a.wait_for_selector(sel.WEB["wiki_editor"], timeout=60_000)
        page_b.goto(_wiki_edit_url(base_url, node_id), wait_until="domcontentloaded")
        page_b.wait_for_selector(sel.WEB["wiki_editor"], timeout=60_000)

        marker = f"collab-{run_id}"
        page_b.click(sel.WEB["wiki_editor"])
        page_b.keyboard.type(marker)
        # Deterministic wait: the text must appear in A's editor through y-websocket within the budget.
        page_a.wait_for_function("m => document.body.innerText.includes(m) || "
                                 "[...document.querySelectorAll('textarea')].some(t => t.value.includes(m))",
                                 arg=marker, timeout=CONVERGE_MS)
    finally:
        page_a.context.request.delete(api_url + sel.API["node"].format(node_id=node_id),
                                      headers={"Content-Type": "application/vnd.api+json", **csrf_headers(page_a.context)})


@pytest.mark.case("rejection")
def test_c4_wiki_collab_rejection(two_contexts, login, user_a, base_url, api_url, project, record_property):
    """A logged-out context connecting to the wiki websocket is closed with code 4401."""
    page_a, page_anon = two_contexts
    login(page_a, user_a)
    page_a.goto(_wiki_edit_url(base_url, project), wait_until="domcontentloaded")
    page_a.wait_for_selector(sel.WEB["wiki_editor"], timeout=60_000)
    # The web page tells the browser where the collaboration socket is. TODO(M2): confirm contextVars key.
    ws_url = page_a.evaluate("() => (window.contextVars && window.contextVars.wiki && "
                             "(window.contextVars.wiki.urls.y_websocket || window.contextVars.wiki.urls.sharejs)) || null")
    assert ws_url, "wiki page did not expose the websocket URL (window.contextVars.wiki.urls)"
    assert "127.0.0.1" in ws_url, f"websocket URL must stay on loopback: {ws_url}"

    page_anon.goto(base_url + sel.PATHS["login"], wait_until="domcontentloaded")  # same origin, no session
    close_code = page_anon.evaluate(
        """url => new Promise(resolve => {
            const ws = new WebSocket(url);
            const timer = setTimeout(() => { ws.close(); resolve('timeout'); }, 10000);
            ws.onclose = ev => { clearTimeout(timer); resolve(ev.code); };
            ws.onerror = () => {};
        })""", ws_url)
    record_property("http_status", close_code)
    assert close_code == 4401, f"expected websocket close code 4401, got {close_code!r}"
