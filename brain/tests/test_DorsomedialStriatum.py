"""Behavioral tests for DorsomedialStriatum."""
import asyncio
from brain.mechanisms.DorsomedialStriatum import DorsomedialStriatum


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_pfc_and_ofc_drive_goal_directed():
    """Gremel 2013: DMS goal-directed signal requires mPFC + OFC."""
    m = DorsomedialStriatum()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PrelimbicCortex": {"pl_drive": 0.65},
            "OrbitofrontalCortexLateral": {"lofc_drive": 0.60},
            "MediodorsalThalamus": {"md_drive": 0.40},
            "SubstantiaNigraCompacta": {"da_release_dms": 0.45},
            "ValenceTagger": {"valence_intensity": 0.55, "valence_sign": 1},
        })
    assert out["dms_drive"] > 0.30
    assert out["goal_directed_signal"] > 0.30
    assert out["dms_state"] == "goal_directed"


def test_strong_habit_cedes_control_to_dls():
    """Balleine 2010: when DLS habit is strong, DMS yields control."""
    m = DorsomedialStriatum()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PrelimbicCortex": {"pl_drive": 0.30},
            "OrbitofrontalCortexLateral": {"lofc_drive": 0.30},
            "DorsolateralStriatum": {"habit_strength_signal": 0.85},
        })
    assert out["arbitration_with_dls"] < 0.50
    assert out["dms_state"] == "ceding_to_habit"


def test_outcome_identity_drives_ao_value():
    """Hart 2014: OFC outcome-identity feeds DMS A-O value."""
    m = DorsomedialStriatum()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PrelimbicCortex": {"pl_drive": 0.55},
            "OrbitofrontalCortexLateral": {"lofc_drive": 0.75},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": 1},
        })
    assert out["action_outcome_value"] > 0.30


def test_quiet_no_input():
    m = DorsomedialStriatum()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["dms_state"] == "quiet"
