"""S5 — Shibboleth-SP via test IdP (SPEC-04 §5). Subsystem scenario; implemented at M3."""
import pytest

pytestmark = [pytest.mark.subsystem, pytest.mark.scenario("S5", "Shibboleth-SP via test IdP"), pytest.mark.skip(reason="M3")]


@pytest.mark.case("success")
def test_s5_shibboleth_success():
    """SP -> IdP login -> GRDM dashboard with institution attribute."""
    raise NotImplementedError("M3")


@pytest.mark.case("rejection")
def test_s5_shibboleth_rejection():
    """IdP user without the required eduPersonEntitlement -> SP error page, no GRDM session."""
    raise NotImplementedError("M3")
