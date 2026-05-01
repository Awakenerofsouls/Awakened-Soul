"""Behavioral tests for AnteriorCommissureLimbicBridge."""
import asyncio
from brain.mechanisms.AnteriorCommissureLimbicBridge import AnteriorCommissureLimbicBridge


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_amygdala_olfactory_drive_unifies_limbic():
    """Both amygdala + olfactory active → limbic_unified."""
    m = AnteriorCommissureLimbicBridge()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "BasolateralAmygdala": {"bla_drive": 0.55},
            "AnteriorOlfactoryNucleus": {"aon_drive": 0.55},
            "OlfactoryBulb": {"ob_drive": 0.45},
            "PiriformLayer2": {"pir2_drive": 0.45},
            "ValenceTagger": {"valence_intensity": 0.45},
        })
    assert out["ac_drive"] > 0.30
    assert out["limbic_unification_signal"] > 0.30
    assert out["ac_state"] == "limbic_unified"


def test_olfactory_only_dominant():
    """Olfactory active without amygdala → olfactory_dominant."""
    m = AnteriorCommissureLimbicBridge()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "AnteriorOlfactoryNucleus": {"aon_drive": 0.75},
            "OlfactoryBulb": {"ob_drive": 0.65},
            "PiriformLayer2": {"pir2_drive": 0.55},
        })
    assert out["bilateral_olfactory_signal"] > 0.40


def test_amygdala_only_dominant():
    """Amygdala active without olfactory → amygdala_dominant."""
    m = AnteriorCommissureLimbicBridge()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "BasolateralAmygdala": {"bla_drive": 0.85},
            "ValenceTagger": {"valence_intensity": 0.65},
        })
    assert out["bilateral_amygdala_signal"] > 0.40


def test_quiet_no_input():
    m = AnteriorCommissureLimbicBridge()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["ac_state"] == "quiet"
