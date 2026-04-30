"""Behavioral tests for TemporalPole."""
import asyncio
from brain.neocortical.TemporalPole import TemporalPole


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_multimodal_input_engages_semantic_hub():
    m = TemporalPole()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "InferotemporalCortex": {"it_drive": 0.55},
            "InsulaAnterior": {"aic_drive": 0.45},
            "HippocampalCA1Ventral": {"vca1_drive": 0.55},
        })
    assert out["tp_drive"] > 0.30
    assert out["semantic_hub_signal"] > 0.30
    assert out["tp_state"] in ("semantic_active", "social_active")


def test_face_plus_episodic_drives_person_identity():
    m = TemporalPole()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "InferotemporalCortex": {"it_drive": 0.65},
            "HippocampalCA1Ventral": {"vca1_drive": 0.65},
        })
    assert out["person_identity_signal"] > 0.30
    assert out["tom_signal"] > 0.20


def test_affective_semantic_with_amygdala():
    m = TemporalPole()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "InferotemporalCortex": {"it_drive": 0.55},
            "InsulaAnterior": {"aic_drive": 0.55},
            "HippocampalCA1Ventral": {"vca1_drive": 0.55},
            "BasolateralAmygdala": {"bla_drive": 0.65},
        })
    assert out["affective_semantic_signal"] > 0.30


def test_quiet_no_input():
    m = TemporalPole()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["tp_state"] == "quiet"
