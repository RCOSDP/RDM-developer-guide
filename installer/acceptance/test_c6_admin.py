"""C6 — Institution admin screen (SPEC-04 §4). Services: admin, api."""
import pytest

from acceptance import selectors as sel
from acceptance.conftest import api

pytestmark = [pytest.mark.core, pytest.mark.scenario("C6", "Institution admin screen")]


def _admin_login(page, admin_url: str, user: dict[str, str]) -> None:
    """The admin app (port ADMIN) has its own Django login form. TODO(M2): confirm path and field names."""
    page.goto(admin_url + sel.ADMIN["login"], wait_until="domcontentloaded")
    page.fill(sel.ADMIN_UI["login_user"], user["email"])
    page.fill(sel.ADMIN_UI["login_pass"], user["password"])
    page.click(sel.ADMIN_UI["login_submit"])
    page.wait_for_load_state("domcontentloaded")


@pytest.mark.case("success")
def test_c6_admin_success(page, service_url, admin_user, record_property):
    """The institution admin signs in to the admin app and sees the institution's user list."""
    admin_url = service_url("admin")
    _admin_login(page, admin_url, admin_user)
    # TODO(M2): the institution id of the seeded admin; "1" assumes the first institution created by --seed.
    resp = page.goto(admin_url + sel.ADMIN["institution_users"].format(institution_id="1"), wait_until="domcontentloaded")
    record_property("http_status", resp.status if resp else None)
    assert resp is not None and resp.status == 200, f"institution users page returned {resp and resp.status}"
    page.wait_for_selector(sel.ADMIN_UI["institution_user_table"], timeout=30_000)


@pytest.mark.case("rejection")
def test_c6_admin_rejection(logged_in_page, service_url, api_url, record_property):
    """An ordinary user opening the admin URL -> 403 or redirect to login; the API answers exactly 403."""
    client = api(logged_in_page.context)
    admin_url = service_url("admin")
    screen = client.get(admin_url + sel.ADMIN["institution_users"].format(institution_id="1"), max_redirects=0)
    assert screen.status in (301, 302, 303, 307, 403), f"admin screen answered {screen.status} to an ordinary user"
    # TODO(M2): confirm the exact admin-only API path (institution users listing) on the real app.
    api_resp = client.get(api_url + sel.API["institution_users"].format(institution_id="1"))
    record_property("http_status", api_resp.status)
    assert api_resp.status == 403, f"expected 403 from the institution users API, got {api_resp.status} (404 is not acceptable)"
