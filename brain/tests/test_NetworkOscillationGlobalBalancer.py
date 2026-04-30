"""Behavioral tests for NetworkOscillationGlobalBalancer."""
import asyncio
from brain.integration.NetworkOscillationGlobalBalancer import NetworkOscillationGlobalBalancer


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_active_task_drives_gamma():
    """Buzsaki 2012: active processing → gamma elevation."""
    m = NetworkOscillationGlobalBalancer()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "ThetaGammaCrossFrequencyBinding": {"theta_phase_coherence": 0.65,
                                                       "gamma_amplitude": 0.65},
            "MedialSeptum": {"theta_signal": 0.55},
            "DorsolateralPrefrontalCortex": {"dlpfc_drive": 0.65},
            "ArousalRegulator": {"tonic_level": 0.65},
        })
    assert out["gamma_power"] > 0.30
    assert out["theta_power"] > 0.20
    assert out["oscillation_state"] == "task_engaged"


def test_low_arousal_drives_delta_deep_sleep():
    """Slow-wave modulation + low arousal → delta-dominant."""
    m = NetworkOscillationGlobalBalancer()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "ClaustrumGlobalConsciousness": {"slow_wave_modulation": 0.85},
            "ArousalRegulator": {"tonic_level": 0.05},
        })
    assert out["delta_power"] > 0.30
    assert out["oscillation_state"] == "deep_sleep"


def test_top_down_signal_with_pfc_engaged():
    """Bastos 2015: beta carries top-down. PFC engaged → top-down high."""
    m = NetworkOscillationGlobalBalancer()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "DorsolateralPrefrontalCortex": {"dlpfc_drive": 0.75},
            "CingulateAnterior": {"acc_drive": 0.65},
            "ArousalRegulator": {"tonic_level": 0.50},
        })
    assert out["beta_power"] > 0.30
    assert out["top_down_signal"] > 0.20


def test_quiet_no_input():
    m = NetworkOscillationGlobalBalancer()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["oscillation_state"] == "quiet"
