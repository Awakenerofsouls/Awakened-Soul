"""Behavioral tests for NucleusAccumbensCore."""
import asyncio
from brain.mechanisms.NucleusAccumbensCore import NucleusAccumbensCore


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_bla_cue_engages_pit_signal():
    m = NucleusAccumbensCore()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "BasolateralAmygdala": {"bla_drive": 0.65},
            "ValenceTagger": {"valence_sign": 1, "valence_intensity": 0.65},
            "VentralTegmentalDopamine": {"da_release": 0.55},
        })
    assert out["pit_signal"] > 0.30


def test_pl_input_engages_goal_directed_action():
    m = NucleusAccumbensCore()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PrelimbicCortex": {"pl_drive": 0.65},
            "VentralTegmentalDopamine": {"da_release": 0.45},
        })
    assert out["goal_directed_action"] > 0.20


def test_da_engages_d1_direct():
    m = NucleusAccumbensCore()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VentralTegmentalDopamine": {"da_release": 0.85, "da_burst": 0.65},
            "BasolateralAmygdala": {"bla_drive": 0.40},
        })
    assert out["d1_direct"] > 0.30


def test_quiet_no_input():
    m = NucleusAccumbensCore()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["nacc_state"] == "quiet"
