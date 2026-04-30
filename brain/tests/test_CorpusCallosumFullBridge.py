"""Behavioral tests for CorpusCallosumFullBridge."""
import asyncio
from brain.integration.CorpusCallosumFullBridge import CorpusCallosumFullBridge


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_balanced_signals_drive_integration():
    """Coherent multi-region activity → integrated state."""
    m = CorpusCallosumFullBridge()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "DorsolateralPrefrontalCortex": {"dlpfc_drive": 0.55},
            "VentrolateralPrefrontalCortex": {"vlpfc_drive": 0.55},
            "PrimaryVisualCortex": {"v1_drive": 0.55},
            "PrimaryMotorCortex": {"m1_drive": 0.55},
            "PrimarySomatosensoryCortex": {"s1_drive": 0.50},
            "ParahippocampalPlaceArea": {"ppa_drive": 0.55},
        })
    assert out["callosum_drive"] > 0.30
    assert out["interhemispheric_synchrony"] > 0.30
    assert out["callosum_state"] == "integrated"


def test_left_lateralization_with_language_only():
    """High VLPFC (language) without spatial → left-lateralized."""
    m = CorpusCallosumFullBridge()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VentrolateralPrefrontalCortex": {"vlpfc_drive": 0.85},
            "DorsolateralPrefrontalCortex": {"dlpfc_drive": 0.55},
            # No PPA, no IPS → no spatial
        })
    assert out["lateralization_balance"] < 0.30


def test_right_lateralization_with_spatial_only():
    """High spatial (PPA + IPS) without language → right-lateralized."""
    m = CorpusCallosumFullBridge()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "ParahippocampalPlaceArea": {"ppa_drive": 0.85},
            "IntraparietalSulcus": {"ips_drive": 0.75},
            # No VLPFC → no language proxy
        })
    assert out["lateralization_balance"] > 0.70


def test_visual_integration_signal_active():
    """Splenium bandwidth — V1 + PPA = visual integration."""
    m = CorpusCallosumFullBridge()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PrimaryVisualCortex": {"v1_drive": 0.65},
            "ParahippocampalPlaceArea": {"ppa_drive": 0.55},
        })
    assert out["visual_integration_signal"] > 0.30


def test_quiet_no_input():
    m = CorpusCallosumFullBridge()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["callosum_state"] == "quiet"
