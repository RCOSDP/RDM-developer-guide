"""C3 — Upload and download file (SPEC-04 §4). Services: wb, wb_worker, osfstorage."""
import pytest

from acceptance import selectors as sel
from acceptance.conftest import api
from acceptance.netguard import same_origin

pytestmark = [pytest.mark.core, pytest.mark.scenario("C3", "Upload and download file")]


def upload(context, wb_url: str, node_id: str, name: str, data: bytes):
    """PUT bytes to waterbutler with the session cookie; returns the waterbutler file entity (dict).

    TODO(M2): confirm waterbutler accepts the `osf` session cookie forwarded by Playwright and that
    the response is 201 with data.attributes.path / links.download.
    """
    resp = api(context).put(wb_url + sel.WATERBUTLER["upload"].format(node_id=node_id, name=name),
                            data=data, headers={"Content-Type": "application/octet-stream"})
    assert resp.status in (200, 201), f"upload failed: {resp.status} {resp.text()[:300]}"
    return resp.json()["data"]


def download_link(entity: dict, wb_url: str, node_id: str) -> str:
    if "links" in entity and entity["links"].get("download"):
        return entity["links"]["download"]
    return wb_url + sel.WATERBUTLER["download"].format(node_id=node_id, path=entity["attributes"]["path"])


@pytest.mark.case("success")
def test_c3_file_upload_success(logged_in_page, project, service_url, tmp_txt, run_id, record_property):
    """Upload 1 MiB through waterbutler, download it back, bytes must be identical."""
    ctx = logged_in_page.context
    wb = service_url("wb")
    entity = upload(ctx, wb, project, f"c3-{run_id}.txt", tmp_txt)
    link = download_link(entity, wb, project)
    assert same_origin(link, wb), f"download link must be exactly the waterbutler origin {wb}: {link}"
    down = api(ctx).get(link)
    record_property("http_status", down.status)
    assert down.status == 200
    assert down.body() == tmp_txt, "downloaded bytes differ from uploaded bytes"


@pytest.mark.case("rejection")
def test_c3_file_upload_rejection(logged_in_page, project, context_b, service_url, tmp_txt, run_id, api_context,
                                  record_property):
    """Anonymous GET of a private file -> 401/403; a signed-in NON-contributor (user_b) PUT -> 403."""
    ctx = logged_in_page.context
    wb = service_url("wb")
    entity = upload(ctx, wb, project, f"c3-private-{run_id}.txt", tmp_txt[:1024])
    path = entity["attributes"]["path"]

    anon = api_context()
    get = anon.get(wb + sel.WATERBUTLER["download"].format(node_id=project, path=path))
    assert get.status in (401, 403), f"anonymous download returned {get.status}"

    # user_b is signed in but was never added to the project: the write must be forbidden, not unauthorised.
    put = api(context_b).put(wb + sel.WATERBUTLER["upload"].format(node_id=project, name=f"intruder-{run_id}.txt"),
                             data=b"x", headers={"Content-Type": "application/octet-stream"})
    record_property("http_status", put.status)
    assert put.status == 403, f"non-contributor upload returned {put.status}, expected 403"
