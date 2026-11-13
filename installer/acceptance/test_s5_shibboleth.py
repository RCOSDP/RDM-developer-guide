"""S5 — Shibboleth-SP via the bundled test IdP (SPEC-04 §5.1, ADR-05). Subsystem scenario; runs at M3.

Design (skip-marked "M3" until `compose render --profile full --auth shibboleth` renders the IdP/SP
configuration of templates/idp/ and the selectors below are verified on the real pages). The whole
flow stays on 127.0.0.1 over plain HTTP, so the loopback guard of conftest sees every hop:

    browser -> web /login/?campaign=institution -> 302 -> shibboleth_sp /Shibboleth.sso/Login
            -> 302 (AuthnRequest) -> test_idp SSOService -> mock login form -> auto-POST SAML Response
            -> shibboleth_sp /Shibboleth.sso/SAML2/POST -> web with attributes -> /dashboard + osf cookie

* success — `mock-user-01` (eduPersonAffiliation member, faculty) lands on the GRDM dashboard served by
  web; the `osf` session cookie exists; the user's institutions (API) include the MOCK institution and
  the dashboard shows its name.
* rejection — `mock-user-noaff` (eduPersonAffiliation affiliate only) is refused by the SP RequestMap
  (`SP_REQUIRED_AFFILIATION=member` in templates/shibboleth_sp.json): HTTP 403 with the SP's error page,
  no `osf` cookie in the context, and API GET /v2/users/me/ -> 401 from that context.

Mock users come from installer/acceptance/fixtures/idp/mock_users.json (MOCK by construction, POL-05 §4);
fakecas is not in this profile, so the fakecas `login` fixture is not used here.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from acceptance import selectors as sel
from acceptance.conftest import api, scaled
from acceptance.netguard import same_origin

pytestmark = [pytest.mark.subsystem, pytest.mark.scenario("S5", "Shibboleth-SP via test IdP"), pytest.mark.skip(reason="M3")]

FIXTURE = Path(__file__).parent / "fixtures" / "idp" / "mock_users.json"
AUTH_ENV_KEY = "GRDM_AUTH"                 # written by compose render (follow-up F-1 in templates/idp/README.md)
INSTITUTION_NAME = "MOCK Institution"      # fixtures/idp/mock_users.json institution.o
SESSION_COOKIE = "osf"                     # website/settings COOKIE_NAME (compose.render_website_local_py)
SP_DENIED_STATUS = 403
# Default host ports of templates/test_idp.json and templates/shibboleth_sp.json; runtime/.env wins
# (follow-up F-2 adds both to conftest.DEFAULT_PORTS, after which these fallbacks go away).
DEFAULT_PORTS = {"TEST_IDP": 8081, "SHIBBOLETH_SP": 8082}

# TODO(M3): move to selectors.py once verified on the real pages (SimpleSAMLphp 2.x exampleauth form, Shibboleth SP 3 error page).
_SEL = {
    "idp_username": "input[name='username']",
    "idp_password": "input[name='password']",
    "idp_submit": "button[type='submit'], input[type='submit'], #submit_button",
    "idp_form_marker": "form[action*='simplesaml']",
    "sp_error_marker": "text=/Access Denied|Authorization Failed|shibboleth/i",   # SP accessError.html
    "dashboard_heading": sel.WEB["dashboard_heading"],
    "institution_name": f"text={INSTITUTION_NAME}",                                 # TODO(M3): where the dashboard shows the institution
}
PATH_INSTITUTION_LOGIN = "/login/?campaign=institution"      # TODO(M3): confirm RDM-osf.io's institution login entry (may pass through cas-overlay)
API_MY_INSTITUTIONS = "/v2/users/me/institutions/"


def _mock_users() -> dict[str, dict]:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert "MOCK" in data["_label"], "fixture must be labelled MOCK (POL-05 §4)"
    return {u["role"]: u for u in data["users"]}


def _auth_or_skip() -> None:
    env_file = os.environ.get("GRDM_ENV_FILE")
    auth = ""
    if env_file and Path(env_file).exists():
        for line in Path(env_file).read_text(encoding="utf-8").splitlines():
            if line.startswith(AUTH_ENV_KEY + "="):
                auth = line.partition("=")[2].strip()
    if auth != "shibboleth":
        pytest.skip(f"{AUTH_ENV_KEY} is {auth or 'unset'}: S5 runs only in the `--auth shibboleth` profile (SPEC-04 §8, separate run)")


def _port(ports: dict[str, int], key: str) -> int:
    return ports.get(key, DEFAULT_PORTS[key])


def _idp_login(page, base_url: str, ports: dict[str, int], user: dict) -> list:
    """Drive web -> SP -> IdP form -> SAML POST back to the SP; return every response seen on the way
    (main-frame navigations included) so the caller can assert on the SP's answer to the ACS POST."""
    idp_origin = f"http://127.0.0.1:{_port(ports, 'TEST_IDP')}"
    responses: list = []
    page.on("response", responses.append)
    page.goto(base_url + PATH_INSTITUTION_LOGIN, wait_until="domcontentloaded")
    page.wait_for_url(re.compile(re.escape(idp_origin) + r"/simplesaml/"), timeout=scaled(30_000))   # the SP redirected us to the test IdP
    page.wait_for_selector(_SEL["idp_form_marker"], timeout=scaled(30_000))
    page.fill(_SEL["idp_username"], user["username"])
    page.fill(_SEL["idp_password"], user["password"])
    with page.expect_response(lambda r: "/Shibboleth.sso/SAML2/POST" in r.url, timeout=scaled(30_000)):
        page.click(_SEL["idp_submit"])                 # SimpleSAMLphp returns an auto-submitting form to the SP's ACS
    page.wait_for_load_state("domcontentloaded")
    return responses


@pytest.mark.case("success")
def test_s5_shibboleth_success(page, base_url, api_url, ports, record_property):
    """SP -> IdP login as mock-user-01 -> GRDM dashboard with the MOCK institution attribute."""
    _auth_or_skip()
    user = _mock_users()["success"]
    assert user["username"].startswith("mock-"), user
    _idp_login(page, base_url, ports, user)

    page.wait_for_url(re.compile(re.escape(base_url) + r"/(dashboard|myprojects)"), timeout=scaled(60_000))
    resp = page.goto(base_url + sel.PATHS["dashboard"], wait_until="domcontentloaded")
    record_property("http_status", resp.status if resp else None)
    assert same_origin(page.url, base_url), f"dashboard must be served by web, not by the SP: {page.url}"
    page.wait_for_selector(_SEL["dashboard_heading"], timeout=scaled(30_000))

    cookies = {c["name"] for c in page.context.cookies(base_url)}
    assert SESSION_COOKIE in cookies, f"no GRDM session cookie after the SAML login: {sorted(cookies)}"
    me = api(page.context).get(api_url + sel.API["me"])
    assert me.status == 200, me.status
    institutions = api(page.context).get(api_url + API_MY_INSTITUTIONS).json()["data"]
    names = {i["attributes"]["name"] for i in institutions}
    assert INSTITUTION_NAME in names, f"institution attribute did not reach GRDM: {sorted(names)}"
    page.wait_for_selector(_SEL["institution_name"], timeout=scaled(30_000))


@pytest.mark.case("rejection")
def test_s5_shibboleth_rejection(new_context, base_url, api_url, ports, record_property):
    """mock-user-noaff lacks the `member` affiliation -> SP 403 error page, no GRDM session."""
    _auth_or_skip()
    user = _mock_users()["rejection"]
    assert "member" not in user["attributes"]["eduPersonAffiliation"], user
    ctx = new_context()
    page = ctx.new_page()
    responses = _idp_login(page, base_url, ports, user)

    sp_origin = f"http://127.0.0.1:{_port(ports, 'SHIBBOLETH_SP')}"
    final = page.url
    # The SP answers the ACS POST with its own error page, directly or after one redirect inside itself;
    # the first >= 400 answer from the SP origin is the verdict. No other origin may have answered >= 400.
    denied = [r for r in responses if same_origin(r.url, sp_origin) and r.status >= 400]
    assert denied, f"the SP never refused the user; responses: {[(r.status, r.url) for r in responses][-6:]}"
    status = denied[0].status
    record_property("http_status", status)
    assert status == SP_DENIED_STATUS, f"expected {SP_DENIED_STATUS} from the SP for a user without `member`, got {status} at {final}"
    assert same_origin(final, sp_origin), f"the browser must stop at the SP error page, it reached {final}"
    page.wait_for_selector(_SEL["sp_error_marker"], timeout=scaled(30_000))

    cookies = {c["name"] for c in ctx.cookies(base_url)}
    assert SESSION_COOKIE not in cookies, f"a GRDM session was created for a denied user: {sorted(cookies)}"
    me = api(ctx).get(api_url + sel.API["me"])
    assert me.status == 401, f"API must see no session for the denied user, got {me.status}"
