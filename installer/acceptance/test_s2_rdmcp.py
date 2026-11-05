"""S2 — rdmcp, the MCP endpoint of GRDM (SPEC-04 §5). Subsystem scenario; runs at M3.

Design (skip-marked "M3" until rdmcp is installed, published on 127.0.0.1 and its tool names are
verified): an *MCP* client is just HTTP with JSON-RPC bodies (Streamable HTTP transport), so the whole
scenario uses the guarded `api_context()` fixture, no browser.

* success — user_a's personal access token (created through the OSF API with the session of the
  logged-in page) initializes an MCP session, lists tools, and reads the resource of the run's project;
  the title in the resource equals the project fixture's title.
* rejection — (1) no Authorization header -> transport HTTP 401; (2) user_b's token reading user_a's
  private project -> transport HTTP 403. Exactly as SPEC-04 §5 states: the status is the HTTP status
  line, never a JSON-RPC error body that merely embeds `http_status`; an HTTP 200 carrying such a body
  fails (`transport_status_must_be`). 404 is not acceptable: it would hide the permission check (same
  rule as C6). If rdmcp turns out to answer 200 + JSON-RPC error, SPEC-04 §5 (both halves) is amended
  first and this test second.

Prerequisite tracked as follow-up: rdmcp has no host_port yet (templates/rdmcp.json exposes 8100
internally). The test skips with an explicit reason when GRDM_PORT_RDMCP is absent from runtime/.env.
"""
from __future__ import annotations

import json

import pytest

from acceptance import selectors as sel
from acceptance.conftest import api

pytestmark = [pytest.mark.subsystem, pytest.mark.scenario("S2", "rdmcp (MCP endpoint)"), pytest.mark.skip(reason="M3")]

MCP_PATH = "/mcp"                                  # TODO(M3): Streamable HTTP endpoint path of rdmcp
MCP_PROTOCOL = "2025-06-18"                        # TODO(M3): protocol version rdmcp negotiates
PROJECT_RESOURCE = "grdm://nodes/{node_id}"        # TODO(M3): resource URI scheme of rdmcp
TOKEN_SCOPES = ["osf.full_read"]                   # TODO(M3): scopes rdmcp requires
JSON_HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}


def _port_or_skip(ports: dict[str, int], key: str) -> int:
    if key not in ports:
        pytest.skip(f"GRDM_PORT_{key} is not in runtime/.env: the service is not published on 127.0.0.1 (follow-up: host_port in templates/{key.lower()}.json)")
    return ports[key]


def _rpc(client, url: str, method: str, params: dict | None = None, token: str | None = None, rpc_id: int = 1):
    headers = dict(JSON_HEADERS)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = {"jsonrpc": "2.0", "id": rpc_id, "method": method, "params": params or {}}
    return client.post(url, data=json.dumps(body), headers=headers)


def transport_status_must_be(status: int, body: str, expected: int) -> None:
    """SPEC-04 §5 S2 rejection contract: the *transport* HTTP status is `expected`.

    `status` is the HTTP status line; `body` the response text. A 200 whose JSON-RPC error embeds the
    expected code (`error.data.http_status`) is still a failure: it would let the client believe the
    request succeeded. Kept free of pytest/playwright so installer/tests can unit-test it.
    """
    if status == 200:
        embedded = None
        try:
            err = json.loads(body).get("error") or {}
            embedded = (err.get("data") or {}).get("http_status")
        except (ValueError, AttributeError):
            pass
        if embedded is not None:
            raise AssertionError(f"HTTP 200 carrying an embedded http_status {embedded}: SPEC-04 §5 requires transport HTTP {expected}")
    if status != expected:
        raise AssertionError(f"expected transport HTTP {expected}, got {status} (404 is not acceptable)" if expected == 403
                             else f"expected transport HTTP {expected}, got {status}")


def _result(resp) -> dict:
    assert resp.status == 200, f"{resp.status} {resp.text()[:300]}"
    payload = resp.json()
    assert "error" not in payload, payload
    return payload["result"]


def _personal_token(api_write, context, api_url: str, name: str):
    """A personal access token of the user signed in to `context` (deleted by the caller)."""
    resp = api_write(context, "POST", api_url + sel.API.get("tokens", "/v2/tokens/"), {
        "data": {"type": "tokens", "attributes": {"name": name, "scopes": " ".join(TOKEN_SCOPES)}}
    })
    assert resp.status == 201, f"token create failed: {resp.status} {resp.text()[:300]}"
    data = resp.json()["data"]
    return data["attributes"]["token_id"], data["id"]   # TODO(M3): attribute name of the secret in RDM-osf.io


def _initialize(client, url: str, token: str) -> None:
    _result(_rpc(client, url, "initialize", {
        "protocolVersion": MCP_PROTOCOL,
        "capabilities": {},
        "clientInfo": {"name": "grdm-dev acceptance", "version": "S2"},
    }, token))


@pytest.mark.case("success")
def test_s2_rdmcp_success(logged_in_page, project, api_url, api_context, api_write, ports, record_property):
    """An authenticated MCP client lists tools and reads the run's project resource."""
    url = f"http://127.0.0.1:{_port_or_skip(ports, 'RDMCP')}{MCP_PATH}"
    secret, token_id = _personal_token(api_write, logged_in_page.context, api_url, "acceptance S2 user_a")
    client = api_context()
    try:
        _initialize(client, url, secret)
        tools = _result(_rpc(client, url, "tools/list", token=secret, rpc_id=2))["tools"]
        assert tools and all("name" in t for t in tools), tools
        resp = _rpc(client, url, "resources/read", {"uri": PROJECT_RESOURCE.format(node_id=project)}, secret, rpc_id=3)
        record_property("http_status", resp.status)
        contents = _result(resp)["contents"]
        text = " ".join(c.get("text", "") for c in contents)
        assert project in text and "acceptance project" in text, f"project resource does not describe the run's project: {text[:300]}"
    finally:
        api_write(logged_in_page.context, "DELETE", api_url + sel.API.get("token", "/v2/tokens/{token_id}/").format(token_id=token_id))


@pytest.mark.case("rejection")
def test_s2_rdmcp_rejection(logged_in_page, context_b, project, api_url, api_context, api_write, ports, record_property):
    """No token -> transport 401; user_b's token reading user_a's private project -> transport 403 (never 404, never 200)."""
    url = f"http://127.0.0.1:{_port_or_skip(ports, 'RDMCP')}{MCP_PATH}"
    client = api_context()
    anon = _rpc(client, url, "tools/list")
    transport_status_must_be(anon.status, anon.text(), 401)

    secret, token_id = _personal_token(api_write, context_b, api_url, "acceptance S2 user_b")
    try:
        _initialize(client, url, secret)
        resp = _rpc(client, url, "resources/read", {"uri": PROJECT_RESOURCE.format(node_id=project)}, secret, rpc_id=3)
        record_property("http_status", resp.status)
        transport_status_must_be(resp.status, resp.text(), 403)   # SPEC-04 §5: transport 403, never 200 + embedded 403
    finally:
        api_write(context_b, "DELETE", api_url + sel.API.get("token", "/v2/tokens/{token_id}/").format(token_id=token_id))
        assert api(context_b).get(api_url + sel.API["node"].format(node_id=project)).status == 403  # the project really is private to user_a
