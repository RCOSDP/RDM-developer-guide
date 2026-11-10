"""C6 — Institution admin screen (SPEC-04 §4). Services: admin, api."""
from urllib.parse import quote

import pytest

from acceptance import selectors as sel
from acceptance.conftest import api

pytestmark = [pytest.mark.core, pytest.mark.scenario("C6", "Institution admin screen")]


def _admin_login(page, admin_url: str, user: dict[str, str]) -> None:
    """The admin app (port ADMIN) has its own Django login form."""
    page.goto(admin_url + sel.ADMIN["login"], wait_until="domcontentloaded")
    page.fill(sel.ADMIN_UI["login_user"], user["email"])
    page.fill(sel.ADMIN_UI["login_pass"], user["password"])
    page.click(sel.ADMIN_UI["login_submit"])
    page.wait_for_load_state("domcontentloaded")


def _listed(page, admin_url: str, path: str) -> str:
    resp = page.goto(admin_url + path, wait_until="domcontentloaded")
    assert resp is not None and resp.status == 200, f"{path} returned {resp and resp.status}"
    page.wait_for_selector(sel.ADMIN_UI["institution_user_table"], timeout=30_000)
    return page.inner_text(sel.ADMIN_UI["institution_user_table"]).lower()  # OSF stores addresses in lower case


@pytest.mark.case("success")
def test_c6_admin_success(page, service_url, admin_user, user_a, institution_member, other_institution_member,
                          record_property):
    """An affiliated institution admin (staff, not superuser) sees the users of its institution, and only those:
    not a user of no institution, and not a user of another institution (seeded by `grdm-dev accept --seed`)."""
    admin_url = service_url("admin")
    _admin_login(page, admin_url, admin_user)
    table = _listed(page, admin_url, sel.ADMIN["institution_users"])
    record_property("http_status", 200)  # _listed asserted it
    member, other, none = (u["email"].lower() for u in (institution_member, other_institution_member, user_a))
    assert member in table, "a user of the admin's institution is missing from the list"
    assert none not in table, "a user of no institution is in the institution's list"
    assert other not in table, "a user of another institution is in the institution's list"
    # The same search must find the member and not the other institution's user (the search proves itself).
    search = sel.ADMIN["institution_users_search"]
    assert member in _listed(page, admin_url, search.format(email=quote(member))), "search does not find the member"
    assert other not in _listed(page, admin_url, search.format(email=quote(other))), \
        "searching for a user of another institution lists it"


@pytest.mark.case("rejection")
def test_c6_admin_rejection(logged_in_page, service_url, api_url, record_property):
    """An ordinary user opening the admin URL -> 403 or redirect to login; the API answers exactly 403."""
    client = api(logged_in_page.context)
    admin_url = service_url("admin")
    screen = client.get(admin_url + sel.ADMIN["institution_users"], max_redirects=0, follow_redirects=False)
    assert screen.status in (301, 302, 303, 307, 403), f"admin screen answered {screen.status} to an ordinary user"
    api_resp = client.get(api_url + sel.API["institution_users"].format(institution_id="1"))
    record_property("http_status", api_resp.status)
    assert api_resp.status == 403, f"expected 403 from the institution users API, got {api_resp.status} (404 is not acceptable)"
