"""C2 — Create project (SPEC-04 §4). Services: web, api."""
import pytest

from acceptance import selectors as sel
from acceptance.conftest import api, user_id_of
from acceptance.netguard import same_origin

pytestmark = [pytest.mark.core, pytest.mark.scenario("C2", "Create project")]


@pytest.mark.case("success")
def test_c2_create_project_success(logged_in_page, base_url, api_url, api_write, run_id, record_property):
    """A new project created in the UI appears with its title and the user as admin."""
    page = logged_in_page
    title = f"acceptance C2 {run_id}"
    page.goto(base_url + sel.PATHS["new_project"], wait_until="domcontentloaded")
    page.click(sel.WEB["create_project_button"])
    page.fill(sel.WEB["create_project_title"], title)
    page.click(sel.WEB["create_project_submit"])
    page.click(sel.WEB["create_project_go"])  # the modal stays on the dashboard and offers this link
    page.wait_for_url(lambda url: same_origin(url, base_url) and "/dashboard" not in url, timeout=60_000)
    page.wait_for_selector(f"text={title}", timeout=30_000)

    node_id = page.url.rstrip("/").rsplit("/", 1)[-1]
    me = api(page.context).get(api_url + sel.API["node"].format(node_id=node_id))
    record_property("http_status", me.status)
    try:
        assert me.status == 200
        attrs = me.json()["data"]["attributes"]
        assert attrs["title"] == title
        # Contract: the creator is admin. An API shape without current_user_permissions is a failure,
        # never a pass by default.
        assert "current_user_permissions" in attrs, f"node attributes lack current_user_permissions: {sorted(attrs)}"
        assert "admin" in attrs["current_user_permissions"], f"creator is not admin: {attrs['current_user_permissions']}"
    finally:
        api_write(page.context, "DELETE", api_url + sel.API["node"].format(node_id=node_id))


@pytest.mark.case("rejection")
def test_c2_create_project_rejection(logged_in_page, project, context_b, api_url, api_write, add_contributor, record_property):
    """A second user, read-only contributor (user_b), PATCHing the project -> 403."""
    a_ctx = logged_in_page.context
    # TODO(M2): confirm the contributors payload (users relationship by id) on the real API.
    add_contributor(a_ctx, project, user_id_of(context_b, api_url), "read")

    resp = api_write(context_b, "PATCH", api_url + sel.API["node"].format(node_id=project), {
        "data": {"type": "nodes", "id": project, "attributes": {"title": "renamed by read-only user"}}
    })
    record_property("http_status", resp.status)
    assert resp.status == 403, f"expected 403, got {resp.status}"
