"""S4 — OASys (SPEC-04 §5). Subsystem scenario; runs at M3.

Design (skip-marked "M3" until OASys is installed, published on 127.0.0.1 and its paths are verified).
OASys is a browser application beside GRDM (templates/oasys.json points it at OSF_URL on the host), so
the success case is a Playwright scenario and the rejection case an HTTP call.

* success — user_a, already signed in to GRDM in the same guarded context, opens the OASys page on
  http://127.0.0.1:<GRDM_PORT_OASYS>; the page loads (200) and the run's project appears with a link
  back to its GRDM project page (same origin as base_url).
* rejection — the anonymous `api_context()` calls an OASys API path that needs a session -> 401
  (not a 200 login page, not 404).

Prerequisite tracked as follow-up: no host_port yet (templates/oasys.json exposes 3100 internally).
"""
from __future__ import annotations

import re

import pytest

from acceptance.conftest import scaled
from acceptance.netguard import same_origin

pytestmark = [pytest.mark.subsystem, pytest.mark.scenario("S4", "OASys"), pytest.mark.skip(reason="M3")]

# TODO(M3): move to selectors.py once verified on the real OASys UI.
_PATHS = {
    "home": "/",
    "projects": "/projects",                      # TODO(M3): list of GRDM projects visible to the user
    "project": "/projects/{node_id}",             # TODO(M3)
    "api_me": "/api/v1/me",                       # TODO(M3): a session-protected OASys API path
}
_SEL = {
    "project_list": "[data-test-project-list], main",                 # TODO(M3)
    "project_link": "a[href*='{node_id}']",                           # link back to GRDM
    "signin_button": "button:has-text('Sign in'), a:has-text('Sign in with GRDM')",   # TODO(M3): OASys -> GRDM login
}


def _port_or_skip(ports: dict[str, int], key: str) -> int:
    if key not in ports:
        pytest.skip(f"GRDM_PORT_{key} is not in runtime/.env: the service is not published on 127.0.0.1 (follow-up: host_port in templates/{key.lower()}.json)")
    return ports[key]


@pytest.mark.case("success")
def test_s4_oasys_success(logged_in_page, project, base_url, ports, record_property):
    """The OASys page loads and shows the run's project linked from GRDM."""
    oasys = f"http://127.0.0.1:{_port_or_skip(ports, 'OASYS')}"
    page = logged_in_page                                   # same guarded context: GRDM session cookies on 127.0.0.1
    resp = page.goto(oasys + _PATHS["home"], wait_until="domcontentloaded")
    record_property("http_status", resp.status if resp else None)
    assert resp is not None and resp.status == 200, f"OASys home answered {resp and resp.status}"
    if page.locator(_SEL["signin_button"]).count():          # OASys hands off to GRDM and must come back to itself
        page.click(_SEL["signin_button"])
        page.wait_for_url(re.compile(re.escape(oasys) + r"/"), timeout=scaled(60_000))
    page.goto(oasys + _PATHS["projects"], wait_until="domcontentloaded")
    page.wait_for_selector(_SEL["project_list"], timeout=scaled(30_000))
    link = page.locator(_SEL["project_link"].format(node_id=project)).first
    link.wait_for(timeout=scaled(30_000))
    href = link.get_attribute("href") or ""
    target = href if href.startswith("http") else base_url + href
    assert same_origin(target, base_url) and project in target, f"project link does not point back to GRDM: {href}"


@pytest.mark.case("rejection")
def test_s4_oasys_rejection(api_context, ports, record_property):
    """An unauthenticated OASys API call -> 401."""
    oasys = f"http://127.0.0.1:{_port_or_skip(ports, 'OASYS')}"
    resp = api_context().get(oasys + _PATHS["api_me"], headers={"Accept": "application/json"})
    record_property("http_status", resp.status)
    assert resp.status == 401, f"expected 401 from {_PATHS['api_me']} without a session, got {resp.status} (a login page or 404 is not acceptable)"
