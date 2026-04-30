"""Behavioral tests for FrontalPole."""
import asyncio
from brain.neocortical.FrontalPole import FrontalPole


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_branching_engages_with_acc_conflict():
    m = FrontalPole()
    out = None
    for _ in range(25):
        out = _tick(m, {
            "DorsolateralPrefrontalCortex": {"dlpfc_drive": 0.65},
            "CingulateAnterior": {"acc_drive": 0.65},
            "VentromedialPrefrontalCortex": {"vmpfc_drive": 0.45},
        })
    assert out["fp_drive"] > 0.30
    assert out["branching_signal"] > 0.20
    assert out["fp_state"] in ("branching", "metacog")


def test_prospection_with_hpc_and_vmpfc():
    m = FrontalPole()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "DorsolateralPrefrontalCortex": {"dlpfc_drive": 0.45},
            "HippocampalCA1Ventral": {"vca1_drive": 0.65},
            "VentromedialPrefrontalCortex": {"vmpfc_drive": 0.55},
        })
    assert out["prospection_signal"] > 0.20


def test_metacognition_builds_with_sustained_engagement():
    m = FrontalPole()
    out = None
    for _ in range(80):
        out = _tick(m, {
            "DorsolateralPrefrontalCortex": {"dlpfc_drive": 0.75},
            "CingulateAnterior": {"acc_drive": 0.45},
        })
    assert out["metacognitive_confidence"] > 0.20


def test_quiet_no_input():
    m = FrontalPole()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["fp_state"] == "quiet"
