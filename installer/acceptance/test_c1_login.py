"""C1 — Login via fakecas (SPEC-04 §4). Services: web, api, fakecas."""
import pytest

from acceptance import selectors as sel
from acceptance.netguard import same_origin

pytestmark = [pytest.mark.core, pytest.mark.scenario("C1", "Login via fakecas")]


@pytest.mark.case("success")
def test_c1_login_success(page, login, user_a, base_url, record_property):
    """Test user signs in through fakecas and lands on the dashboard."""
    login(page, user_a)
    resp = page.goto(base_url + sel.PATHS["dashboard"], wait_until="domcontentloaded")
    record_property("http_status", resp.status if resp else None)
    page.wait_for_selector(sel.WEB["dashboard_heading"], timeout=30_000)
    assert same_origin(page.url, base_url), f"dashboard must be served by web ({base_url}), not fakecas: {page.url}"


@pytest.mark.case("rejection")
def test_c1_login_rejection(api_context, base_url, api_url, record_property):
    """Without a session: GET /dashboard -> 302 to login; API GET /v2/users/me/ -> 401."""
    anon = api_context()
    dash = anon.get(base_url + sel.PATHS["dashboard"], max_redirects=0, follow_redirects=False)  # the 302 itself, not the login page it points to
    me = anon.get(api_url + sel.API["me"])
    record_property("http_status", me.status)
    assert dash.status in (301, 302, 303, 307) and "login" in (dash.headers.get("location") or "").lower(), \
        f"expected redirect to login, got {dash.status} {dash.headers.get('location')}"
    assert me.status == 401, f"expected 401 from {sel.API['me']}, got {me.status}"
