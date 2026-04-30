"""Behavioral tests for GlobalWorkspaceIntegrator."""
import asyncio
from brain.integration.GlobalWorkspaceIntegrator import GlobalWorkspaceIntegrator


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_strong_input_crosses_ignition_threshold():
    """Dehaene 2011: above-threshold input produces all-or-nothing ignition."""
    m = GlobalWorkspaceIntegrator()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "ClaustrumGlobalConsciousness": {"broadcast_strength": 0.75,
                                                  "coherence_index": 0.65},
            "DorsolateralPrefrontalCortex": {"dlpfc_drive": 0.65},
            "PosteriorParietalCortex": {"ppc_drive": 0.55},
            "ArousalRegulator": {"tonic_level": 0.65},
            "BasolateralAmygdala": {"bla_drive": 0.65},
        })
    assert out["ignition_strength"] > 0.50
    assert out["ignition_threshold_crossed"] is True
    assert out["workspace_state"] == "ignited"


def test_weak_input_stays_subliminal():
    """Below-threshold input should NOT ignite (subliminal/preconscious)."""
    m = GlobalWorkspaceIntegrator()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "ClaustrumGlobalConsciousness": {"broadcast_strength": 0.10,
                                                  "coherence_index": 0.10},
            "DorsolateralPrefrontalCortex": {"dlpfc_drive": 0.20},
            "ArousalRegulator": {"tonic_level": 0.55},
            "PrimaryVisualCortex": {"v1_drive": 0.15},
        })
    assert out["ignition_strength"] < 0.50
    assert out["ignition_threshold_crossed"] is False
    assert out["workspace_state"] in ("subliminal", "preconscious", "quiet")


def test_p3b_signature_builds_with_sustained_ignition():
    """Sergent 2005: late P3b ERP signature appears with sustained access."""
    m = GlobalWorkspaceIntegrator()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "ClaustrumGlobalConsciousness": {"broadcast_strength": 0.85,
                                                  "coherence_index": 0.75},
            "DorsolateralPrefrontalCortex": {"dlpfc_drive": 0.75},
            "PosteriorParietalCortex": {"ppc_drive": 0.65},
            "ArousalRegulator": {"tonic_level": 0.70},
            "BasolateralAmygdala": {"bla_drive": 0.65},
        })
    assert out["p3b_signature"] > 0.30


def test_low_arousal_no_ignition():
    """Mashour 2020: anesthesia/coma → loss of workspace ignition."""
    m = GlobalWorkspaceIntegrator()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "ClaustrumGlobalConsciousness": {"broadcast_strength": 0.55,
                                                  "coherence_index": 0.45},
            "DorsolateralPrefrontalCortex": {"dlpfc_drive": 0.55},
            "ArousalRegulator": {"tonic_level": 0.05},  # unconscious
        })
    # Even with cortical input, very low arousal blocks workspace ignition
    assert out["workspace_state"] == "quiet"


def test_quiet_no_input():
    m = GlobalWorkspaceIntegrator()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["workspace_state"] == "quiet"
