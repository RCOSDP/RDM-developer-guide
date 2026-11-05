"""S2 — rdmcp (MCP endpoint) (SPEC-04 §5). Subsystem scenario; implemented at M3."""
import pytest

pytestmark = [pytest.mark.subsystem, pytest.mark.scenario("S2", "rdmcp (MCP endpoint)"), pytest.mark.skip(reason="M3")]


@pytest.mark.case("success")
def test_s2_rdmcp_success():
    """authenticated MCP client lists tools and reads one project resource."""
    raise NotImplementedError("M3")


@pytest.mark.case("rejection")
def test_s2_rdmcp_rejection():
    """no token -> 401; token of user B reading project of user A -> 403."""
    raise NotImplementedError("M3")
