"""C5 — File preview (SPEC-04 §4). Services: mfr, unoconv."""
import pytest

from acceptance import selectors as sel
from acceptance.conftest import scaled
from acceptance.netguard import same_origin
from acceptance.test_c3_file_upload import upload

pytestmark = [pytest.mark.core, pytest.mark.scenario("C5", "File preview")]


def _file_page_url(base_url: str, node_id: str, path: str) -> str:
    # osfstorage paths are "/<file id>"; the web file page is /<node>/files/osfstorage/<file id>/
    return f"{base_url}/{node_id}/files/osfstorage{path.rstrip('/')}/"


@pytest.mark.case("success")
def test_c5_file_preview_success(logged_in_page, project, base_url, service_url, tmp_pdf, run_id, record_property):
    """An uploaded PDF renders inside the mfr iframe (mfr answers 200 for the render request)."""
    page = logged_in_page
    entity = upload(page.context, service_url("wb"), project, f"c5-{run_id}.pdf", tmp_pdf)
    mfr = service_url("mfr")
    with page.expect_response(lambda r: same_origin(r.url, mfr) and "/render" in r.url, timeout=scaled(90_000)) as render:
        page.goto(_file_page_url(base_url, project, entity["attributes"]["path"]), wait_until="domcontentloaded")
        page.wait_for_selector(sel.WEB["file_preview_iframe"], timeout=scaled(60_000))
    record_property("http_status", render.value.status)
    assert render.value.status == 200, f"mfr render returned {render.value.status}"


@pytest.mark.case("rejection")
def test_c5_file_preview_rejection(logged_in_page, project, base_url, service_url, tmp_pdf, run_id, api_context, record_property):
    """The preview URL the web app embeds for a private file, requested without a session -> 401/403."""
    page = logged_in_page
    mfr = service_url("mfr")
    entity = upload(page.context, service_url("wb"), project, f"c5-private-{run_id}.pdf", tmp_pdf)
    # Its `url=` is the web app's container-internal address, the only one mfr can reach; a host-only URL such as
    # http://127.0.0.1:7777/... is mfr's own loopback inside its container and answers 400 before any permission check.
    page.goto(_file_page_url(base_url, project, entity["attributes"]["path"]), wait_until="domcontentloaded")
    render_url = page.evaluate("() => window.contextVars.file.urls.render")
    assert same_origin(render_url, mfr), f"render URL must be the mfr origin {mfr}: {render_url}"
    resp = api_context().get(render_url)
    record_property("http_status", resp.status)
    assert resp.status in (401, 403), f"anonymous preview returned {resp.status}"
