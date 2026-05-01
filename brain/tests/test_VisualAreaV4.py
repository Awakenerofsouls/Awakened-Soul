"""Behavioral tests for VisualAreaV4."""
import asyncio
from brain.mechanisms.VisualAreaV4 import VisualAreaV4


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_v2_drives_v4_engagement():
    m = VisualAreaV4()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "SecondaryVisualCortex": {
                "v4_input_signal": 0.65,
                "thin_stripe_signal": 0.55,
                "pale_stripe_signal": 0.55,
            },
        })
    assert out["v4_drive"] > 0.25
    assert out["v4_state"] != "quiet"


def test_attention_amplifies_v4():
    """FEF and LIP top-down attention should multiplicatively boost V4."""
    no_att = VisualAreaV4()
    with_att = VisualAreaV4()
    base = {
        "SecondaryVisualCortex": {
            "v4_input_signal": 0.50,
            "thin_stripe_signal": 0.40,
            "pale_stripe_signal": 0.40,
        },
    }
    boosted = dict(base)
    boosted["FrontalEyeFields"] = {"attention_map": 0.80}
    boosted["LateralIntraparietalArea"] = {"priority_signal": 0.70}

    a = b = None
    for _ in range(15):
        a = _tick(no_att, base)
        b = _tick(with_att, boosted)
    assert b["v4_drive"] > a["v4_drive"]
    assert b["attention_gain"] > a["attention_gain"]


def test_color_vs_form_dominance():
    """Thin-stripe-dominated input → color_dominant state."""
    color_m = VisualAreaV4()
    out = None
    for _ in range(15):
        out = _tick(color_m, {
            "SecondaryVisualCortex": {
                "v4_input_signal": 0.55,
                "thin_stripe_signal": 0.85,
                "pale_stripe_signal": 0.10,
            },
        })
    assert out["color_signal"] > out["form_signal"]


def test_quiet_no_input():
    m = VisualAreaV4()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["v4_state"] == "quiet"
