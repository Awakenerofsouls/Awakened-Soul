"""Behavioral tests for SubstantiaNigraCompacta."""
import asyncio
from brain.mechanisms.SubstantiaNigraCompacta import SubstantiaNigraCompacta


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_unexpected_reward_drives_phasic_burst():
    """Schultz 1997: unexpected reward → positive PE → phasic DA burst."""
    m = SubstantiaNigraCompacta()
    out = None
    # First tick: positive outcome with no expectation → PE positive
    for _ in range(10):
        out = _tick(m, {
            "PedunculopontineCholinergic": {"ach_drive": 0.40},
            "ValenceTagger": {"valence_intensity": 0.85, "valence_sign": 1},
        })
    assert out["prediction_error"] >= 0.0
    assert out["snc_drive"] > 0.30
    assert out["da_release_dls"] > 0.20


def test_lhab_inhibition_pauses_da():
    """Hikosaka 2010: LHb activation pauses DA neurons (negative PE)."""
    m_no_lhab = SubstantiaNigraCompacta()
    out_no = None
    for _ in range(10):
        out_no = _tick(m_no_lhab, {
            "PedunculopontineCholinergic": {"ach_drive": 0.50},
        })

    m_lhab = SubstantiaNigraCompacta()
    out_lhab = None
    for _ in range(10):
        out_lhab = _tick(m_lhab, {
            "PedunculopontineCholinergic": {"ach_drive": 0.50},
            "LateralHabenula": {"lhab_drive": 0.85},
        })
    assert out_lhab["snc_drive"] < out_no["snc_drive"]


def test_expected_value_learns_with_repeated_reward():
    """Repeated reward should grow expected_value over many trials
    (Rescorla-Wagner learning, Reynolds 2002)."""
    m = SubstantiaNigraCompacta()
    out = None
    for _ in range(60):
        out = _tick(m, {
            "PedunculopontineCholinergic": {"ach_drive": 0.40},
            "ValenceTagger": {"valence_intensity": 0.80, "valence_sign": 1},
        })
    assert out["expected_value"] > 0.20
    # With expected_value high, PE should diminish (predicted reward → small PE)
    # Check this on a separate near-final tick
    near_final_pe = abs(out["prediction_error"])
    assert near_final_pe < 0.85  # not full magnitude — partially expected


def test_baseline_tonic_with_no_outcome():
    """SNc never goes silent — even at rest there's tonic firing."""
    m = SubstantiaNigraCompacta()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["snc_drive"] >= 0.10  # tonic baseline
    assert out["snc_state"] in ("tonic", "quiet")


def test_quiet_no_input():
    m = SubstantiaNigraCompacta()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["snc_state"] in ("tonic", "quiet")
