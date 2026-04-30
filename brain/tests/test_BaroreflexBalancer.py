"""Behavioral tests for BaroreflexBalancer."""
import asyncio
from brain.foundational.BaroreflexBalancer import BaroreflexBalancer


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_high_pressure_engages_reflex():
    """Andresen 1994: high BP → NTS firing → baroreflex engages."""
    m = BaroreflexBalancer()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "NucleusTractusSolitariusFull": {"nts_drive": 0.65},
            "C1AdrenergicRVLM": {"c1_drive": 0.55},
            "ArousalRegulator": {"tonic_level": 0.55},
        })
    assert out["baroreflex_drive"] > 0.30
    assert out["sympathetic_output_inhibition"] > 0.20


def test_high_bp_drives_parasympathetic():
    """Dampney 2016: elevated pressure → vagal cardiac slowing."""
    m = BaroreflexBalancer()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "NucleusTractusSolitariusFull": {"nts_drive": 0.85},
            "C1AdrenergicRVLM": {"c1_drive": 0.65},
            "ArousalRegulator": {"tonic_level": 0.55},
        })
    assert out["pressure_estimate"] > 0.55
    assert out["parasympathetic_output"] > 0.20


def test_vagal_tone_drives_hrv():
    """Thayer 2009: parasympathetic tone × low arousal = high HRV."""
    m = BaroreflexBalancer()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "NucleusTractusSolitariusFull": {"nts_drive": 0.55},
            "ArousalRegulator": {"tonic_level": 0.20},
        })
    # HRV should be present — arousal is low, parasympathetic engaged
    assert out["hrv_signal"] > 0.10


def test_quiet_no_input():
    m = BaroreflexBalancer()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["baroreflex_state"] in ("quiet", "rest_tone")
