"""Behavioral tests for VagalRestPromoter."""
import asyncio
from brain.mechanisms.VagalRestPromoter import VagalRestPromoter


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_low_arousal_drives_rest_digest():
    """Loewy 1990: low arousal → DMV-mediated rest-and-digest."""
    m = VagalRestPromoter()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "NucleusTractusSolitariusFull": {"nts_drive": 0.55},
            "ArousalRegulator": {"tonic_level": 0.10},
            "BaroreflexBalancer": {"parasympathetic_output": 0.55},
        })
    assert out["dmv_drive"] > 0.30
    assert out["rest_digest_signal"] > 0.30
    assert out["dmv_state"] == "rest_digest"


def test_gi_motility_engaged_when_resting():
    """Berthoud 2008: brain-gut axis active during rest."""
    m = VagalRestPromoter()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "NucleusTractusSolitariusFull": {"nts_drive": 0.55},
            "ArousalRegulator": {"tonic_level": 0.20},
            "BaroreflexBalancer": {"parasympathetic_output": 0.45},
        })
    assert out["gi_motility_command"] > 0.20


def test_high_arousal_suppresses_dmv():
    """Stress/arousal should suppress parasympathetic DMV output."""
    m_calm = VagalRestPromoter()
    out_calm = None
    for _ in range(15):
        out_calm = _tick(m_calm, {
            "NucleusTractusSolitariusFull": {"nts_drive": 0.45},
            "ArousalRegulator": {"tonic_level": 0.10},
        })

    m_aroused = VagalRestPromoter()
    out_aroused = None
    for _ in range(15):
        out_aroused = _tick(m_aroused, {
            "NucleusTractusSolitariusFull": {"nts_drive": 0.45},
            "ArousalRegulator": {"tonic_level": 0.85},
        })
    assert out_aroused["dmv_drive"] < out_calm["dmv_drive"]


def test_quiet_no_input():
    m = VagalRestPromoter()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["dmv_state"] in ("quiet", "rest_digest", "mild_parasymp")
