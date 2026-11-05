"""C5 — File preview (SPEC-04 §4). Services: mfr, unoconv."""
import pytest

from acceptance import selectors as sel
from acceptance.test_c3_file_upload import upload

pytestmark = [pytest.mark.core, pytest.mark.scenario("C5", "File preview")]


def _file_page_url(base_url: str, node_id: str, path: str) -> str:
    # osfstorage paths are "/<file id>"; the web file page is /<node>/files/osfstorage/<file id>/
    return f"{base_url}/{node_id}/files/osfstorage{path.rstrip('/')}/"  # TODO(M2): confirm


@pytest.mark.case("success")
def test_c5_file_preview_success(logged_in_page, project, base_url, service_url, tmp_pdf, run_id, record_property):
    """An uploaded PDF renders inside the mfr iframe (mfr answers 200 for the render request)."""
    page = logged_in_page
    entity = upload(page.context, service_url("wb"), project, f"c5-{run_id}.pdf", tmp_pdf)
    mfr_origin = service_url("mfr")
    with page.expect_response(lambda r: r.url.startswith(mfr_origin) and "/render" in r.url, timeout=90_000) as render:
        page.goto(_file_page_url(base_url, project, entity["attributes"]["path"]), wait_until="domcontentloaded")
        page.wait_for_selector(sel.WEB["file_preview_iframe"], timeout=60_000)
    record_property("http_status", render.value.status)
    assert render.value.status == 200, f"mfr render returned {render.value.status}"


@pytest.mark.case("rejection")
def test_c5_file_preview_rejection(logged_in_page, project, service_url, tmp_pdf, run_id, playwright, record_property):
    """The preview URL of a private file without a session -> 401/403."""
    page = logged_in_page
    entity = upload(page.context, service_url("wb"), project, f"c5-private-{run_id}.pdf", tmp_pdf)
    file_url = entity["links"]["download"] if "links" in entity else service_url("wb") + sel.WATERBUTLER["download"].format(
        node_id=project, path=entity["attributes"]["path"])
    anon = playwright.request.new_context()
    try:
        resp = anon.get(service_url("mfr") + sel.MFR["render"].format(file_url=file_url))
        record_property("http_status", resp.status)
        assert resp.status in (401, 403), f"anonymous preview returned {resp.status}"
    finally:
        anon.dispose()
