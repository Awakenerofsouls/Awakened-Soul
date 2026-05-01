"""Behavioral tests for ClaustrumDorsal."""
import asyncio
from brain.mechanisms.ClaustrumDorsal import ClaustrumDorsal


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_cortical_input_engages_binding():
    m = ClaustrumDorsal()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PrelimbicCortex": {"pl_drive": 0.65},
            "CingulateAnterior": {"acc_drive": 0.65},
            "InsulaAnterior": {"aic_drive": 0.55},
            "ArousalRegulator": {"tonic_level": 0.65},
        })
    assert out["claustrum_drive"] > 0.30
    assert out["consciousness_binding_signal"] > 0.20


def test_arousal_drives_attention_gain():
    m = ClaustrumDorsal()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "ArousalRegulator": {"tonic_level": 0.85},
            "PrelimbicCortex": {"pl_drive": 0.50},
        })
    assert out["attention_gain_signal"] > 0.20


def test_cross_cortical_sync_active():
    m = ClaustrumDorsal()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PrelimbicCortex": {"pl_drive": 0.55},
            "InsulaAnterior": {"aic_drive": 0.55},
            "ArousalRegulator": {"tonic_level": 0.55},
        })
    assert out["cross_cortical_sync"] > 0.20


def test_quiet_no_input():
    m = ClaustrumDorsal()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    # Baseline activity (low) but state should be quiet/rest
    assert out["claustrum_state"] in ("quiet", "rest")
