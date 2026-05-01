"""Behavioral tests for AnteroDorsalThalamus."""
import asyncio
from brain.mechanisms.AnteroDorsalThalamus import AnteroDorsalThalamus


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_lmn_drives_hd_signal():
    """LMN drive should produce sharp HD signal (Taube 1995, Bassett 2007)."""
    m = AnteroDorsalThalamus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "MammillaryBodyLateral": {"lmn_drive": 0.65},
            "PrePresubiculum": {"head_direction_signal": 0.50},
            "RetrosplenialCortex": {"cortical_drive": 0.45},
        })
    assert out["ad_drive"] > 0.30
    assert out["hd_signal"] > 0.40
    assert out["presubicular_signal"] > 0.20
    assert out["retrosplenial_signal"] > 0.20
    assert out["ad_state"] in ("hd_active", "anchored")


def test_lmn_lesion_abolishes_hd():
    """No LMN input — Bassett 2007 lesion abolishes HD signal."""
    m = AnteroDorsalThalamus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PrePresubiculum": {"head_direction_signal": 0.60},
            "RetrosplenialCortex": {"cortical_drive": 0.50},
            # NO LMN input — bilateral lesion condition
        })
    # HD signal should be near-zero without LMN, despite presubicular input
    assert out["hd_signal"] < 0.10
    assert out["ad_state"] in ("drift", "quiet")


def test_anchored_vs_drift_with_landmarks():
    """RSC + presubiculum (landmark anchoring) should produce 'anchored'."""
    m_anchor = AnteroDorsalThalamus()
    m_drift = AnteroDorsalThalamus()
    out_a = None
    out_d = None
    for _ in range(15):
        out_a = _tick(m_anchor, {
            "MammillaryBodyLateral": {"lmn_drive": 0.65},
            "PrePresubiculum": {"head_direction_signal": 0.55},
            "RetrosplenialCortex": {"cortical_drive": 0.55},
        })
        out_d = _tick(m_drift, {
            "MammillaryBodyLateral": {"lmn_drive": 0.65},
            # No presubiculum or RSC — landmark anchoring removed
        })
    # Anchored case should have stronger RSC signal and prefer 'anchored'
    assert out_a["retrosplenial_signal"] > out_d["retrosplenial_signal"]
    assert out_a["ad_state"] in ("anchored", "hd_active")


def test_quiet_no_input():
    m = AnteroDorsalThalamus()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["ad_state"] == "quiet"
