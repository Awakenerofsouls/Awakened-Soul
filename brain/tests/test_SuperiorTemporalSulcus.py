"""Behavioral tests for SuperiorTemporalSulcus."""
import asyncio
from brain.mechanisms.SuperiorTemporalSulcus import SuperiorTemporalSulcus


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_motion_plus_form_drives_biomotion():
    m = SuperiorTemporalSulcus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "MiddleTemporalArea": {"mt_drive": 0.65},
            "InferotemporalCortex": {"it_drive": 0.65},
            "TemporalPole": {"tp_drive": 0.45},
        })
    assert out["sts_drive"] > 0.30
    assert out["biological_motion_signal"] > 0.30
    assert out["sts_state"] in ("biomotion", "gaze_active", "mentalizing")


def test_motion_alone_does_not_drive_biomotion():
    """Pure object motion (no form) should NOT drive biological motion."""
    m = SuperiorTemporalSulcus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "MiddleTemporalArea": {"mt_drive": 0.85},
            # No IT input — no biological form binding
        })
    # Conjunction is mt * it; with it=0, biomotion should be near zero
    assert out["biological_motion_signal"] < 0.20


def test_audiovisual_binding_requires_both_modalities():
    m = SuperiorTemporalSulcus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "InferotemporalCortex": {"it_drive": 0.65},
            "PrimaryAuditoryCortex": {"a1_drive": 0.65},
        })
    assert out["audiovisual_binding_signal"] > 0.20


def test_tom_engages_with_vmpfc_and_gaze():
    m = SuperiorTemporalSulcus()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "InferotemporalCortex": {"it_drive": 0.65},
            "VentromedialPrefrontalCortex": {"vmpfc_drive": 0.65},
            "TemporalPole": {"tp_drive": 0.55},
        })
    assert out["tom_signal"] > 0.30


def test_quiet_no_input():
    m = SuperiorTemporalSulcus()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["sts_state"] == "quiet"
