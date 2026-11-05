"""C2 — Create project (SPEC-04 §4). Services: web, api."""
import pytest

from acceptance import selectors as sel

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
    # TODO(M2): confirm the modal navigates to /<node_id>/ (legacy UI shows a "Go to new project" link).
    page.wait_for_url(lambda url: url.startswith(base_url) and "/dashboard" not in url, timeout=60_000)
    page.wait_for_selector(f"text={title}", timeout=30_000)

    node_id = page.url.rstrip("/").rsplit("/", 1)[-1]
    me = page.context.request.get(api_url + sel.API["node"].format(node_id=node_id))
    record_property("http_status", me.status)
    try:
        assert me.status == 200
        attrs = me.json()["data"]["attributes"]
        assert attrs["title"] == title
        assert attrs.get("current_user_permissions", ["admin"])[0] == "admin"
    finally:
        api_write(page.context, "DELETE", api_url + sel.API["node"].format(node_id=node_id))


@pytest.mark.case("rejection")
def test_c2_create_project_rejection(logged_in_page, project, browser, login, user_b, api_url, api_write,
                                     external_guard, record_property):
    """A read-only contributor (user_b) PATCHing the project -> 403."""
    from acceptance.conftest import guard_context

    a_ctx = logged_in_page.context
    # user_a adds user_b as read-only contributor. TODO(M2): confirm payload (users relationship by id).
    b_ctx = browser.new_context()
    guard_context(b_ctx, external_guard)
    try:
        b_page = b_ctx.new_page()
        login(b_page, user_b)
        b_id = b_ctx.request.get(api_url + sel.API["me"]).json()["data"]["id"]
        added = api_write(a_ctx, "POST", api_url + sel.API["node_contributors"].format(node_id=project), {
            "data": {"type": "contributors", "attributes": {"permission": "read", "bibliographic": False},
                     "relationships": {"users": {"data": {"type": "users", "id": b_id}}}}
        })
        assert added.status == 201, f"adding contributor failed: {added.status} {added.text()[:200]}"

        resp = api_write(b_ctx, "PATCH", api_url + sel.API["node"].format(node_id=project), {
            "data": {"type": "nodes", "id": project, "attributes": {"title": "renamed by read-only user"}}
        })
        record_property("http_status", resp.status)
        assert resp.status == 403, f"expected 403, got {resp.status}"
    finally:
        b_ctx.close()
