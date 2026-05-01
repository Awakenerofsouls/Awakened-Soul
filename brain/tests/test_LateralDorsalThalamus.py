"""Behavioral tests for LateralDorsalThalamus."""
import asyncio
from brain.mechanisms.LateralDorsalThalamus import LateralDorsalThalamus


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_visual_landmark_engages_ld():
    """Visual SC + V1 with HD signal should engage LD landmark mode."""
    m = LateralDorsalThalamus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "SubiculumDorsal": {"subiculum_output": 0.50},
            "PrePresubiculum": {"head_direction_signal": 0.55},
            "SuperiorColliculus": {"visual_signal": 0.55},
            "V1": {"visual_signal": 0.50},
            "RetrosplenialCortex": {"cortical_drive": 0.40},
        })
    assert out["ld_drive"] > 0.30
    assert out["head_direction_signal"] > 0.30
    assert out["retrosplenial_signal"] > 0.20
    assert out["ld_state"] in ("landmark_active", "hd_active", "context_relay")


def test_dark_environment_disrupts_landmark():
    """No visual input → no landmark, even if HD is signaled."""
    m_dark = LateralDorsalThalamus()
    m_lit = LateralDorsalThalamus()
    out_d = None
    out_l = None
    for _ in range(15):
        out_d = _tick(m_dark, {
            "PrePresubiculum": {"head_direction_signal": 0.60},
            # No visual input — Mizumori 1993 disruption condition
        })
        out_l = _tick(m_lit, {
            "PrePresubiculum": {"head_direction_signal": 0.60},
            "SuperiorColliculus": {"visual_signal": 0.60},
            "V1": {"visual_signal": 0.55},
        })
    assert out_l["retrosplenial_signal"] > out_d["retrosplenial_signal"]
    assert out_l["ld_drive"] > out_d["ld_drive"] + 0.05


def test_subicular_input_drives_context_relay():
    """Subicular input alone should engage context relay mode."""
    m = LateralDorsalThalamus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "SubiculumDorsal": {"subiculum_output": 0.65},
        })
    assert out["spatial_context_signal"] > 0.15
    assert out["cingulate_signal"] > 0.10


def test_quiet_no_input():
    m = LateralDorsalThalamus()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["ld_state"] == "quiet"
