"""Behavioral tests for AnteroVentralThalamus."""
import asyncio
from brain.mechanisms.AnteroVentralThalamus import AnteroVentralThalamus


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_mmn_subicular_input_engages_av():
    """MMN + subicular + theta should produce engaged Papez relay."""
    m = AnteroVentralThalamus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "MammillaryBodyMedial": {"mmn_drive": 0.55},
            "SubiculumDorsal": {"subiculum_output": 0.45},
            "MedialSeptum": {"theta_signal": 0.55},
            "RetrosplenialCortex": {"cortical_drive": 0.40},
        })
    assert out["av_drive"] > 0.30
    assert out["retrosplenial_signal"] > 0.20
    assert out["spatial_memory_signal"] > 0.20
    assert out["av_state"] in ("theta_active", "spatial_relay")


def test_theta_modulation_present_with_septal_input():
    """Theta input should produce non-zero theta modulation."""
    m = AnteroVentralThalamus()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "MammillaryBodyMedial": {"mmn_drive": 0.55},
            "MedialSeptum": {"theta_signal": 0.65},
        })
    assert out["theta_modulation"] > 0.15
    # No theta input should not trigger theta_active state alone
    m_no_theta = AnteroVentralThalamus()
    out_n = None
    for _ in range(15):
        out_n = _tick(m_no_theta, {
            "MammillaryBodyMedial": {"mmn_drive": 0.55},
        })
    assert out_n["theta_modulation"] < 0.10


def test_mmn_lesion_vs_intact():
    """No MMN input (mammillothalamic lesion) should reduce AV drive."""
    m_lesion = AnteroVentralThalamus()
    m_intact = AnteroVentralThalamus()
    out_l = None
    out_i = None
    for _ in range(15):
        out_l = _tick(m_lesion, {
            "SubiculumDorsal": {"subiculum_output": 0.40},
            "MedialSeptum": {"theta_signal": 0.40},
        })
        out_i = _tick(m_intact, {
            "MammillaryBodyMedial": {"mmn_drive": 0.65},
            "SubiculumDorsal": {"subiculum_output": 0.40},
            "MedialSeptum": {"theta_signal": 0.40},
        })
    assert out_i["av_drive"] > out_l["av_drive"] + 0.05
    assert out_i["spatial_memory_signal"] > out_l["spatial_memory_signal"]


def test_quiet_no_input():
    m = AnteroVentralThalamus()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["av_state"] == "quiet"
