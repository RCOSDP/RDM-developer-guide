"""S4 — OASys (SPEC-04 §5). Subsystem scenario; implemented at M3."""
import pytest

pytestmark = [pytest.mark.subsystem, pytest.mark.scenario("S4", "OASys"), pytest.mark.skip(reason="M3")]


@pytest.mark.case("success")
def test_s4_oasys_success():
    """OASys page loads and shows the run's project linked from GRDM."""
    raise NotImplementedError("M3")


@pytest.mark.case("rejection")
def test_s4_oasys_rejection():
    """unauthenticated OASys API call -> 401."""
    raise NotImplementedError("M3")
