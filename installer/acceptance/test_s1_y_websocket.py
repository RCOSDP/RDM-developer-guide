"""S1 — y-websocket (SPEC-04 §5). Subsystem scenario; implemented at M3."""
import pytest

pytestmark = [pytest.mark.subsystem, pytest.mark.scenario("S1", "y-websocket"), pytest.mark.skip(reason="M3")]


@pytest.mark.case("success")
def test_s1_y_websocket_success():
    """two contexts converge on the same Wiki document within 5 s."""
    raise NotImplementedError("M3")


@pytest.mark.case("rejection")
def test_s1_y_websocket_rejection():
    """connection without a valid token -> close code 4401, no document state leaked."""
    raise NotImplementedError("M3")
