"""C4 — Wiki collaborative edit with two browser contexts (SPEC-04 §4). Services: web, y_websocket, sharejs.

Never skipped: y_websocket belongs to the `core` profile (SPEC-02 §4).
"""
import pytest

from acceptance import selectors as sel
from acceptance.conftest import scaled, user_id_of
from acceptance.netguard import WS_SCHEMES, is_loopback_origin

pytestmark = [pytest.mark.core, pytest.mark.scenario("C4", "Wiki collaborative edit")]

CONVERGE_MS = 5_000  # SPEC-04 §5 S1 budget, reused for the M2 case
COLLAB_BOUND_MS = scaled(30_000)  # editor load + websocket sync + binding; not the convergence budget

# Document text of the editor. Another user's caret is a y-prosemirror widget placed inside the text (it can
# split a word, measured: "mark-A-xy<caret>z"), so it is removed first; it is presence, not content.
_SEES_MARKER = """([marker, editor, caret]) => {
    const root = document.querySelector(editor);
    if (!root) return false;
    const copy = root.cloneNode(true);
    copy.querySelectorAll(caret).forEach(n => n.remove());
    return copy.textContent.includes(marker);
}"""


def _wiki_edit_url(base_url: str, node_id: str) -> str:
    return f"{base_url}/{node_id}/wiki/home/?edit&view&menu"


def _open_editor(page, base_url: str, node_id: str):
    resp = page.goto(_wiki_edit_url(base_url, node_id), wait_until="domcontentloaded")
    page.click(sel.WEB["wiki_edit_button"], timeout=scaled(60_000))
    page.wait_for_selector(sel.WEB["wiki_editor"], timeout=scaled(60_000))
    return resp


def _sees(marker: str) -> list:
    return [marker, sel.WEB["wiki_editor"], sel.WEB["wiki_cursor_widget"]]


def _propagates(writer, reader, marker: str) -> None:
    """`writer` types `marker`; it must appear in `reader` through y-websocket within the budget.

    The editor is visible before collaboration is bound: text typed in that window is dropped when the binding
    rebuilds the editor state (measured: "Position 11 out of range", nothing sent). The writer's caret on the
    reader's page needs both bindings, so it is the deterministic signal that typing will be shared.
    """
    writer.click(sel.WEB["wiki_editor"])
    reader.wait_for_selector(sel.WEB["wiki_remote_cursor"], state="attached", timeout=COLLAB_BOUND_MS)
    writer.keyboard.type(marker)
    reader.wait_for_function(_SEES_MARKER, arg=_sees(marker), timeout=CONVERGE_MS)


@pytest.mark.case("success")
def test_c4_wiki_collab_success(two_contexts, login, user_a, user_b, base_url, api_url, api_write, add_contributor,
                                run_id, record_property):
    """Both users open the same wiki page; text typed by B appears in A's editor and text typed by A in B's."""
    page_a, page_b = two_contexts
    login(page_a, user_a)
    login(page_b, user_b)

    created = api_write(page_a.context, "POST", api_url + sel.API["nodes"], {
        "data": {"type": "nodes", "attributes": {"title": "acceptance C4", "category": "project", "public": False}}
    })
    assert created.status == 201, created.text()[:200]
    node_id = created.json()["data"]["id"]
    try:
        add_contributor(page_a.context, node_id, user_id_of(page_b.context, api_url), "write")

        resp_a = _open_editor(page_a, base_url, node_id)
        record_property("http_status", resp_a.status if resp_a else None)
        _open_editor(page_b, base_url, node_id)

        # Both directions must converge: B -> A, then A -> B (SPEC-04 §4: "both see merged text").
        _propagates(page_b, page_a, f"collab-b-{run_id}")
        _propagates(page_a, page_b, f"collab-a-{run_id}")
        for page, who in ((page_a, "A"), (page_b, "B")):
            for marker in (f"collab-b-{run_id}", f"collab-a-{run_id}"):
                assert page.evaluate(_SEES_MARKER, _sees(marker)), f"{who} does not show {marker} after both edits"
    finally:
        api_write(page_a.context, "DELETE", api_url + sel.API["node"].format(node_id=node_id))


@pytest.mark.case("rejection")
def test_c4_wiki_collab_rejection(two_contexts, login, user_a, base_url, project, record_property):
    """A logged-out context connecting to the wiki websocket is closed with code 4401."""
    page_a, page_anon = two_contexts
    login(page_a, user_a)
    page_a.goto(_wiki_edit_url(base_url, project), wait_until="domcontentloaded")
    # The web page tells the browser where the socket is: `host:port` without a scheme; the room is the document
    # id (wikiPageMilkdown.js: new WebsocketProvider('ws://' + urls.y_websocket, metadata.docId, ...)).  # nosemgrep: javascript.lang.security.detect-insecure-websocket.detect-insecure-websocket -- comment quoting the app; no socket here
    endpoint = page_a.evaluate("() => { const w = window.contextVars && window.contextVars.wiki; "
                               "return w && w.urls.y_websocket && w.metadata.docId ? w.urls.y_websocket + '/' + w.metadata.docId : null; }")
    assert endpoint, "wiki page did not expose the websocket endpoint (window.contextVars.wiki)"
    ws_url = f"ws://{endpoint}"  # nosemgrep: javascript.lang.security.detect-insecure-websocket.detect-insecure-websocket -- loopback-only y-websocket of the dev stack, asserted on the next line
    assert is_loopback_origin(ws_url, WS_SCHEMES), f"websocket URL must be exactly ws://127.0.0.1:<port>: {ws_url}"

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
