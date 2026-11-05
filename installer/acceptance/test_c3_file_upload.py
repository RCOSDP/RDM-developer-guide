"""C3 — Upload and download file (SPEC-04 §4). Services: wb, wb_worker, osfstorage."""
import pytest

from acceptance import selectors as sel

pytestmark = [pytest.mark.core, pytest.mark.scenario("C3", "Upload and download file")]


def upload(context, wb_url: str, node_id: str, name: str, data: bytes):
    """PUT bytes to waterbutler with the session cookie; returns the waterbutler file entity (dict).

    TODO(M2): confirm waterbutler accepts the `osf` session cookie forwarded by Playwright and that
    the response is 201 with data.attributes.path / links.download.
    """
    resp = context.request.put(wb_url + sel.WATERBUTLER["upload"].format(node_id=node_id, name=name),
                               data=data, headers={"Content-Type": "application/octet-stream"})
    assert resp.status in (200, 201), f"upload failed: {resp.status} {resp.text()[:300]}"
    return resp.json()["data"]


@pytest.mark.case("success")
def test_c3_file_upload_success(logged_in_page, project, service_url, tmp_txt, run_id, record_property):
    """Upload 1 MiB through waterbutler, download it back, bytes must be identical."""
    ctx = logged_in_page.context
    entity = upload(ctx, service_url("wb"), project, f"c3-{run_id}.txt", tmp_txt)
    link = entity["links"]["download"] if "links" in entity else service_url("wb") + sel.WATERBUTLER["download"].format(
        node_id=project, path=entity["attributes"]["path"])
    assert link.startswith("http://127.0.0.1"), f"download link must stay on loopback: {link}"
    down = ctx.request.get(link)
    record_property("http_status", down.status)
    assert down.status == 200
    assert down.body() == tmp_txt, "downloaded bytes differ from uploaded bytes"


@pytest.mark.case("rejection")
def test_c3_file_upload_rejection(logged_in_page, project, service_url, tmp_txt, run_id, playwright, record_property):
    """Anonymous GET of a private file -> 401/403 (and the anonymous PUT -> 401/403)."""
    ctx = logged_in_page.context
    entity = upload(ctx, service_url("wb"), project, f"c3-private-{run_id}.txt", tmp_txt[:1024])
    path = entity["attributes"]["path"]
    anon = playwright.request.new_context()
    try:
        get = anon.get(service_url("wb") + sel.WATERBUTLER["download"].format(node_id=project, path=path))
        put = anon.put(service_url("wb") + sel.WATERBUTLER["upload"].format(node_id=project, name="intruder.txt"), data=b"x")
        record_property("http_status", get.status)
        assert get.status in (401, 403), f"anonymous download returned {get.status}"
        assert put.status in (401, 403), f"anonymous upload returned {put.status}"
    finally:
        anon.dispose()
