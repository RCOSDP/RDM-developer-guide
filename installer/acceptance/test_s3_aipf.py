"""S3 — aipf_mcp_data_grdm (SPEC-04 §5). Subsystem scenario; implemented at M3."""
import pytest

pytestmark = [pytest.mark.subsystem, pytest.mark.scenario("S3", "aipf_mcp_data_grdm"), pytest.mark.skip(reason="M3")]


@pytest.mark.case("success")
def test_s3_aipf_success():
    """MCP data query returns the run's project metadata."""
    raise NotImplementedError("M3")


@pytest.mark.case("rejection")
def test_s3_aipf_rejection():
    """query for a project id the user cannot see -> 403 or empty with explicit code."""
    raise NotImplementedError("M3")
