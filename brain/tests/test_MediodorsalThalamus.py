"""Behavioral tests for MediodorsalThalamus."""
import asyncio
from brain.subcortical.MediodorsalThalamus import MediodorsalThalamus


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_mpfc_md_engages_working_memory():
    """Reciprocal mPFC-MD activity should engage working memory state."""
    m = MediodorsalThalamus()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "PrelimbicCortex": {"cortical_drive": 0.55},
            "BasalAmygdala": {"amyg_drive": 0.40},
        })
    assert out["md_drive"] > 0.30
    assert out["working_memory_signal"] > 0.15
    assert out["pfc_layer1_signal"] > 0.20
    assert out["md_state"] in ("wm_maintain", "rule_amplify", "relay")


def test_high_bg_suppression_reduces_md():
    """Strong VP/SNr GABA should suppress MD versus same cortical drive."""
    m_supp = MediodorsalThalamus()
    m_free = MediodorsalThalamus()
    out_s = None
    out_f = None
    for _ in range(15):
        out_s = _tick(m_supp, {
            "PrelimbicCortex": {"cortical_drive": 0.60},
            "VentralPallidum": {"vp_output": 0.80},
            "SubstantiaNigraReticulata": {"snr_output": 0.80},
        })
        out_f = _tick(m_free, {
            "PrelimbicCortex": {"cortical_drive": 0.60},
            "VentralPallidum": {"vp_output": 0.05},
            "SubstantiaNigraReticulata": {"snr_output": 0.05},
        })
    assert out_f["md_drive"] > out_s["md_drive"] + 0.05
    assert out_f["working_memory_signal"] >= out_s["working_memory_signal"]


def test_rule_amplification_with_strong_pfc():
    """MD should amplify cortico-cortical (Schmitt 2017) when ctx high."""
    m = MediodorsalThalamus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PrelimbicCortex": {"cortical_drive": 0.65},
        })
    assert out["rule_amplification_signal"] > 0.20


def test_quiet_no_input():
    m = MediodorsalThalamus()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["md_state"] == "quiet"
