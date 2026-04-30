"""Behavioral tests for InferotemporalCortex (IT)."""
import asyncio
from brain.neocortical.InferotemporalCortex import InferotemporalCortex


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_v4_input_drives_it_engagement():
    m = InferotemporalCortex()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VisualAreaV4": {
                "it_input_signal": 0.65,
                "color_signal": 0.45,
                "form_signal": 0.55,
                "attention_gain": 0.30,
            },
        })
    assert out["it_drive"] > 0.25
    assert out["object_signal"] > 0.20
    assert out["it_state"] != "quiet"


def test_strong_form_yields_face_or_object_state():
    m = InferotemporalCortex()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "VisualAreaV4": {
                "it_input_signal": 0.80,
                "color_signal": 0.40,
                "form_signal": 0.85,
                "attention_gain": 0.55,
            },
        })
    assert out["face_signal"] > 0.30
    assert out["it_state"] in ("face_active", "object_active")


def test_view_invariance_grows_with_sustained_drive():
    m = InferotemporalCortex()
    invars = []
    for _ in range(20):
        out = _tick(m, {
            "VisualAreaV4": {
                "it_input_signal": 0.70,
                "color_signal": 0.40,
                "form_signal": 0.65,
                "attention_gain": 0.40,
            },
        })
        invars.append(out["view_invariance"])
    # Should ramp up rather than stay at zero
    assert max(invars) > 0.20
    assert invars[-1] > invars[0]


def test_quiet_no_input():
    m = InferotemporalCortex()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["it_state"] == "quiet"
