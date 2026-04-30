"""Behavioral tests for SubiculumVentral."""
import asyncio
from brain.limbic.SubiculumVentral import SubiculumVentral


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_aversive_engages_hpa_and_bnst():
    m = SubiculumVentral()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HippocampalCA1Ventral": {"vca1_drive": 0.65},
            "LateralEntorhinalCortex": {"lec_drive": 0.45},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": -1},
        })
    assert out["bnst_drive_signal"] > 0.20
    assert out["hpa_axis_drive"] > 0.20
    assert out["vsub_state"] == "stress_active"


def test_appetitive_drives_nac():
    m = SubiculumVentral()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HippocampalCA1Ventral": {"vca1_drive": 0.65},
            "LateralEntorhinalCortex": {"lec_drive": 0.45},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": 1},
        })
    assert out["nac_drive_signal"] > 0.30
    assert out["vsub_state"] == "reward_drive"


def test_aversive_engages_mpfc_extinction():
    m = SubiculumVentral()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HippocampalCA1Ventral": {"vca1_drive": 0.65},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": -1},
        })
    assert out["mpfc_extinction_signal"] > 0.20


def test_quiet_no_input():
    m = SubiculumVentral()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["vsub_state"] == "quiet"
