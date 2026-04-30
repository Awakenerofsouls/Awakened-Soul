"""Behavioral tests for MedialForebrainBundleDopamine."""
import asyncio
from brain.integration.MedialForebrainBundleDopamine import MedialForebrainBundleDopamine


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_vta_drives_ascending_da():
    """VTA dopamine engages ascending mesolimbic + mesocortical."""
    m = MedialForebrainBundleDopamine()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VentralTegmentalDopamine": {"da_release": 0.65},
            "NucleusAccumbensCore": {"nacc_drive": 0.55},
            "ValenceTagger": {"valence_intensity": 0.55, "valence_sign": 1},
        })
    assert out["mfb_drive"] > 0.30
    assert out["ascending_da_signal"] > 0.30
    assert out["mesolimbic_drive"] > 0.20


def test_lh_self_stimulation_signal():
    """Olds 1954: LH descending bundle = self-stimulation reward (Wise 2008)."""
    m = MedialForebrainBundleDopamine()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "HypothalamicLateral": {"lh_drive": 0.75},
            "NucleusAccumbensCore": {"nacc_drive": 0.55},
            "ValenceTagger": {"valence_intensity": 0.65, "valence_sign": 1},
        })
    assert out["descending_motivation_signal"] > 0.30
    assert out["self_stimulation_proxy"] > 0.20


def test_pfc_demand_amplifies_mesocortical():
    """PFC engagement → enhanced VTA→PFC mesocortical signal."""
    m = MedialForebrainBundleDopamine()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VentralTegmentalDopamine": {"da_release": 0.55},
            "DorsolateralPrefrontalCortex": {"dlpfc_drive": 0.75},
        })
    assert out["mesocortical_drive"] > 0.30


def test_quiet_no_input():
    m = MedialForebrainBundleDopamine()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["mfb_state"] == "quiet"
