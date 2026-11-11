"""C7 — File page co-editing on y-websocket (SPEC-04 §4). Services: web, y_websocket.

RDM-osf.io-dev2027 PR #12 moved the Edit panel of the file page from ShareJS and MongoDB to y-websocket (ADR-13 §6),
so this scenario is the proof that sharejs and mongo are not needed: two users edit one text file and see each
other's text, and a socket without a token is refused. Never skipped: y_websocket belongs to the `core` profile.
"""
import pytest

from acceptance import selectors as sel
from acceptance.conftest import api, user_id_of
from acceptance.netguard import WS_SCHEMES, is_loopback_origin
from acceptance.test_c3_file_upload import upload

pytestmark = [pytest.mark.core, pytest.mark.scenario("C7", "File page collaborative edit")]

CONVERGE_MS = 5_000       # SPEC-04 §5 S1 budget, reused
COLLAB_BOUND_MS = 30_000  # panel load + token + websocket sync; not the convergence budget

_EDITOR_HAS = "(marker) => { const e = window.ace && ace.edit('editor'); return !!e && e.getValue().includes(marker); }"


def _file_page(base_url: str, node_id: str, entity: dict) -> str:
    return f"{base_url}/{node_id}/files/osfstorage/{entity['attributes']['path'].strip('/')}/"


def _open_editor(page, url: str) -> None:
    resp = page.goto(url, wait_until="domcontentloaded")
    assert resp is not None and resp.status == 200, f"file page answered {resp and resp.status}"
    page.click(sel.WEB["file_edit_tab"], timeout=60_000)
    page.wait_for_selector(sel.WEB["file_editor"], timeout=60_000)


def _connected(page) -> None:
    """The panel header turns green ("Live editing mode") only after the websocket is bound and the room synced;
    text typed before that is dropped when the binding replaces the editor content."""
    page.wait_for_selector(sel.WEB["file_editor_connected"], state="visible", timeout=COLLAB_BOUND_MS)


def _propagates(writer, reader, marker: str) -> None:
    writer.click(sel.WEB["file_editor"])
    writer.keyboard.type(marker)
    reader.wait_for_function(_EDITOR_HAS, arg=marker, timeout=CONVERGE_MS)


@pytest.mark.case("success")
def test_c7_file_editor_success(two_contexts, login, user_a, user_b, base_url, api_url, service_url, api_write, add_contributor,
                                run_id, record_property):
    """Both users open the Edit panel of the same text file; the text typed by one appears in the other's editor."""
    page_a, page_b = two_contexts
    login(page_a, user_a)
    login(page_b, user_b)
    created = api_write(page_a.context, "POST", api_url + sel.API["nodes"], {
        "data": {"type": "nodes", "attributes": {"title": "acceptance C7", "category": "project", "public": False}}
    })
    assert created.status == 201, created.text()[:200]
    node_id = created.json()["data"]["id"]
    try:
        add_contributor(page_a.context, node_id, user_id_of(page_b.context, api_url), "write")
        entity = upload(page_a.context, service_url("wb"), node_id, f"c7-{run_id}.txt", b"c7 file editor\n")
        url = _file_page(base_url, node_id, entity)
        _open_editor(page_a, url)
        _open_editor(page_b, url)
        _connected(page_a)
        _connected(page_b)
        record_property("http_status", 200)
        _propagates(page_b, page_a, f"c7-b-{run_id}")
        _propagates(page_a, page_b, f"c7-a-{run_id}")
        for page, who in ((page_a, "A"), (page_b, "B")):
            for marker in (f"c7-b-{run_id}", f"c7-a-{run_id}"):
                assert page.evaluate(_EDITOR_HAS, marker), f"{who} does not show {marker} after both edits"
    finally:
        api_write(page_a.context, "DELETE", api_url + sel.API["node"].format(node_id=node_id))


@pytest.mark.case("rejection")
def test_c7_file_editor_rejection(two_contexts, login, user_a, user_b, base_url, api_url, service_url, project, record_property):
    """A logged-out context's socket to the file room is closed with 4401 (no token); a signed-in user who is not a
    contributor is refused a token (403)."""
    page_a, page_other = two_contexts
    login(page_a, user_a)
    entity = upload(page_a.context, service_url("wb"), project, "c7-private.txt", b"private\n")
    page_a.goto(_file_page(base_url, project, entity), wait_until="domcontentloaded")
    room = page_a.evaluate(sel.WEB["file_editor_room_js"])
    assert room and room.get("endpoint"), "the file page did not expose the websocket endpoint and room"
    ws_url = f"ws://{room['endpoint']}/{room['doc_id']}"  # nosemgrep: javascript.lang.security.detect-insecure-websocket.detect-insecure-websocket -- loopback-only y-websocket of the dev stack, asserted on the next line
    assert is_loopback_origin(ws_url, WS_SCHEMES), f"websocket URL must be exactly ws://127.0.0.1:<port>: {ws_url}"

    page_other.goto(base_url + sel.PATHS["login"], wait_until="domcontentloaded")  # same origin, no session
    close_code = page_other.evaluate(
        """url => new Promise(resolve => {
            const ws = new WebSocket(url);
            const timer = setTimeout(() => { ws.close(); resolve('timeout'); }, 10000);
            ws.onclose = ev => { clearTimeout(timer); resolve(ev.code); };
            ws.onerror = () => {};
        })""", ws_url)
    record_property("http_status", close_code)
    assert close_code == 4401, f"expected websocket close code 4401, got {close_code!r}"

    login(page_other, user_b)  # signed in, never added to the project
    token = api(page_other.context).post(
        base_url + room["token_path"], data='{"doc_id": "%s"}' % room["doc_id"], headers={"Content-Type": "application/json"})
    assert token.status == 403, f"a non-contributor's token request answered {token.status}, expected 403"
