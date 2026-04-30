"""Behavioral tests for VentromedialPrefrontalCortex."""
import asyncio
from brain.neocortical.VentromedialPrefrontalCortex import VentromedialPrefrontalCortex


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_self_reference_engages():
    m = VentromedialPrefrontalCortex()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HippocampalCA1Ventral": {"vca1_drive": 0.65},
            "CingulatePosterior": {"pcc_drive": 0.55},
        })
    assert out["vmpfc_drive"] > 0.30
    assert out["self_reference_signal"] > 0.20
    assert out["vmpfc_state"] in ("self_focused", "default_mode")


def test_emotion_regulation_with_aversive():
    m = VentromedialPrefrontalCortex()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HippocampalCA1Ventral": {"vca1_drive": 0.55},
            "BasolateralAmygdala": {"bla_drive": 0.65},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": -1},
        })
    assert out["emotion_regulation_signal"] > 0.20
    assert out["amygdala_inhibition"] > 0.20


def test_external_load_suppresses_default():
    m = VentromedialPrefrontalCortex()
    out_no_load = None
    for _ in range(15):
        out_no_load = _tick(m, {
            "HippocampalCA1Ventral": {"vca1_drive": 0.55},
            "CingulatePosterior": {"pcc_drive": 0.55},
        })

    m2 = VentromedialPrefrontalCortex()
    out_load = None
    for _ in range(15):
        out_load = _tick(m2, {
            "HippocampalCA1Ventral": {"vca1_drive": 0.55},
            "CingulatePosterior": {"pcc_drive": 0.55},
            "DorsolateralPrefrontalCortex": {"dlpfc_drive": 0.85},
        })
    assert out_load["default_mode_engagement"] < out_no_load["default_mode_engagement"]


def test_quiet_no_input():
    m = VentromedialPrefrontalCortex()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["vmpfc_state"] == "quiet"
