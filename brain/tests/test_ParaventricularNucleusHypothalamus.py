"""Behavioral tests for ParaventricularNucleusHypothalamus."""
import asyncio
from brain.subcortical.ParaventricularNucleusHypothalamus import ParaventricularNucleusHypothalamus


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_threat_drives_crh_release():
    m = ParaventricularNucleusHypothalamus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "BNSTAnterolateral": {"bnst_anxiety_drive": 0.65},
            "BasolateralAmygdala": {"bla_drive": 0.55},
            "ValenceTagger": {"aversive_signal": 0.65, "valence_intensity": 0.65,
                                "valence_sign": -1},
        })
    assert out["pvn_drive"] > 0.30
    assert out["crh_release"] > 0.30
    assert out["hpa_axis_state"] == "stress_active"


def test_safe_context_inhibits_via_vsub():
    """vSub disinhibition: with high vSub safe input, PVN drive should be lower
    than the same threat input WITHOUT vSub."""
    m_threat_only = ParaventricularNucleusHypothalamus()
    out_unbounded = None
    for _ in range(15):
        out_unbounded = _tick(m_threat_only, {
            "BNSTAnterolateral": {"bnst_anxiety_drive": 0.65},
            "BasolateralAmygdala": {"bla_drive": 0.55},
            "ValenceTagger": {"aversive_signal": 0.55, "valence_intensity": 0.55,
                                "valence_sign": -1},
        })

    m_with_safe = ParaventricularNucleusHypothalamus()
    out_dampened = None
    for _ in range(15):
        out_dampened = _tick(m_with_safe, {
            "BNSTAnterolateral": {"bnst_anxiety_drive": 0.65},
            "BasolateralAmygdala": {"bla_drive": 0.55},
            "HippocampalCA1Ventral": {"vca1_drive": 0.85},  # safe context signal
            "ValenceTagger": {"aversive_signal": 0.55, "valence_intensity": 0.55,
                                "valence_sign": -1},
        })

    assert out_dampened["pvn_drive"] < out_unbounded["pvn_drive"]


def test_sustained_stress_builds_gr_feedback():
    """Sustained stress → GR feedback load accumulates → CRH attenuation."""
    m = ParaventricularNucleusHypothalamus()
    out = None
    crh_history = []
    for _ in range(60):
        out = _tick(m, {
            "BNSTAnterolateral": {"bnst_anxiety_drive": 0.75},
            "BasolateralAmygdala": {"bla_drive": 0.65},
            "ValenceTagger": {"aversive_signal": 0.75, "valence_intensity": 0.75,
                                "valence_sign": -1},
        })
        crh_history.append(out["crh_release"])
    assert out["gr_feedback_load"] > 0.15
    # Late CRH should be attenuated relative to early CRH due to GR feedback
    early_avg = sum(crh_history[5:15]) / 10
    late_avg = sum(crh_history[-10:]) / 10
    assert late_avg <= early_avg


def test_safe_social_drives_oxytocin():
    m = ParaventricularNucleusHypothalamus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "BasolateralAmygdala": {"bla_drive": 0.30},
            "ValenceTagger": {"valence_intensity": 0.55, "valence_sign": 1},
        })
    assert out["oxytocin_release"] > 0.10


def test_quiet_no_input():
    m = ParaventricularNucleusHypothalamus()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["hpa_axis_state"] == "quiet"
