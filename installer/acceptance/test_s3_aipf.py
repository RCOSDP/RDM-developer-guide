"""S3 — aipf_mcp_data_grdm (SPEC-04 §5). Subsystem scenario; runs at M3.

Design (skip-marked "M3" until the service is installed, published on 127.0.0.1 and its tool name is
verified). aipf_mcp_data_grdm is the AIPF (AI platform) data connector that answers MCP data queries
about GRDM projects; like S2 it is driven with the guarded `api_context()` fixture, no browser.

* success — user_a's token calls the data-query tool for the run's project and receives the project
  metadata (id, title, creator) that the OSF API also reports for the same node.
* rejection — user_b's token asks for user_a's private project id: the answer is HTTP 403, or an
  empty result that carries an explicit error code (`forbidden` / `not_permitted`); a silent empty
  list is a failure, because it would hide the permission check (SPEC-04 §5 S3).

Prerequisite tracked as follow-up: no host_port yet (templates/aipf_mcp_data_grdm.json exposes 8101
internally). The test skips with an explicit reason when GRDM_PORT_AIPF_MCP_DATA_GRDM is absent.
"""
from __future__ import annotations

import json

import pytest

from acceptance import selectors as sel
from acceptance.conftest import api

pytestmark = [pytest.mark.subsystem, pytest.mark.scenario("S3", "aipf_mcp_data_grdm"), pytest.mark.skip(reason="M3")]

MCP_PATH = "/mcp"                                   # TODO(M3): endpoint path of aipf_mcp_data_grdm
MCP_PROTOCOL = "2025-06-18"                         # TODO(M3)
QUERY_TOOL = "get_project_metadata"                 # TODO(M3): tool name; arguments {"project_id": "<guid>"}
EXPLICIT_DENIAL_CODES = {"forbidden", "not_permitted", "permission_denied"}   # TODO(M3): the service's code
TOKEN_SCOPES = ["osf.full_read"]                    # TODO(M3)
JSON_HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}


def _port_or_skip(ports: dict[str, int], key: str) -> int:
    if key not in ports:
        pytest.skip(f"GRDM_PORT_{key} is not in runtime/.env: the service is not published on 127.0.0.1 (follow-up: host_port in templates/{key.lower()}.json)")
    return ports[key]


def _rpc(client, url: str, method: str, params: dict | None = None, token: str | None = None, rpc_id: int = 1):
    headers = dict(JSON_HEADERS)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return client.post(url, data=json.dumps({"jsonrpc": "2.0", "id": rpc_id, "method": method, "params": params or {}}), headers=headers)


def _personal_token(api_write, context, api_url: str, name: str):
    resp = api_write(context, "POST", api_url + sel.API.get("tokens", "/v2/tokens/"), {
        "data": {"type": "tokens", "attributes": {"name": name, "scopes": " ".join(TOKEN_SCOPES)}}
    })
    assert resp.status == 201, f"token create failed: {resp.status} {resp.text()[:300]}"
    data = resp.json()["data"]
    return data["attributes"]["token_id"], data["id"]   # TODO(M3): attribute name of the secret


def _call_tool(client, url: str, token: str, project_id: str):
    assert _rpc(client, url, "initialize", {"protocolVersion": MCP_PROTOCOL, "capabilities": {},
                                            "clientInfo": {"name": "grdm-dev acceptance", "version": "S3"}}, token).status == 200
    return _rpc(client, url, "tools/call", {"name": QUERY_TOOL, "arguments": {"project_id": project_id}}, token, rpc_id=2)


def _tool_payload(resp) -> dict:
    """The structured content of a tools/call answer (or its first text block parsed as JSON)."""
    body = resp.json()
    result = body.get("result") or {}
    if result.get("structuredContent"):
        return result["structuredContent"]
    for block in result.get("content", []):
        if block.get("type") == "text":
            try:
                return json.loads(block["text"])
            except ValueError:
                return {"text": block["text"]}
    return {"error": body.get("error")}


@pytest.mark.case("success")
def test_s3_aipf_success(logged_in_page, project, api_url, api_context, api_write, ports, record_property):
    """The MCP data query returns the run's project metadata, consistent with the OSF API."""
    url = f"http://127.0.0.1:{_port_or_skip(ports, 'AIPF_MCP_DATA_GRDM')}{MCP_PATH}"
    secret, token_id = _personal_token(api_write, logged_in_page.context, api_url, "acceptance S3 user_a")
    client = api_context()
    try:
        resp = _call_tool(client, url, secret, project)
        record_property("http_status", resp.status)
        assert resp.status == 200, f"{resp.status} {resp.text()[:300]}"
        payload = _tool_payload(resp)
        node = api(logged_in_page.context).get(api_url + sel.API["node"].format(node_id=project)).json()["data"]
        assert payload.get("id") == project, payload
        assert payload.get("title") == node["attributes"]["title"] == "acceptance project", payload
    finally:
        api_write(logged_in_page.context, "DELETE", api_url + sel.API.get("token", "/v2/tokens/{token_id}/").format(token_id=token_id))


@pytest.mark.case("rejection")
def test_s3_aipf_rejection(context_b, project, api_url, api_context, api_write, ports, record_property):
    """A query for a project id user_b cannot see -> 403, or empty with an explicit denial code."""
    url = f"http://127.0.0.1:{_port_or_skip(ports, 'AIPF_MCP_DATA_GRDM')}{MCP_PATH}"
    secret, token_id = _personal_token(api_write, context_b, api_url, "acceptance S3 user_b")
    client = api_context()
    try:
        resp = _call_tool(client, url, secret, project)
        record_property("http_status", resp.status)
        if resp.status == 403:
            return
        assert resp.status == 200, f"unexpected {resp.status}: {resp.text()[:300]}"
        payload = _tool_payload(resp)
        code = str((payload.get("error") or {}).get("code") or payload.get("code") or "").lower()
        assert code in EXPLICIT_DENIAL_CODES, f"denial must be explicit (403 or one of {sorted(EXPLICIT_DENIAL_CODES)}), got {payload}"
        assert not payload.get("title") and not payload.get("contributors"), f"metadata of a private project leaked: {payload}"
    finally:
        api_write(context_b, "DELETE", api_url + sel.API.get("token", "/v2/tokens/{token_id}/").format(token_id=token_id))
