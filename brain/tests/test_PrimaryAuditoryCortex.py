"""Behavioral tests for PrimaryAuditoryCortex (A1)."""
import asyncio
from brain.mechanisms.PrimaryAuditoryCortex import PrimaryAuditoryCortex


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_mgv_drives_a1_engagement():
    """MGv lemniscal drive should engage A1 above quiet."""
    m = PrimaryAuditoryCortex()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "MedialGeniculateNucleus": {"mgv_drive": 0.65},
            "InferiorColliculusAuditory": {"ic_drive": 0.50},
        })
    assert out["a1_drive"] > 0.30
    assert out["a1_state"] != "quiet"
    assert out["tonotopic_band"] in ("low", "mid", "high")


def test_cholinergic_sharpens_tuning():
    """Cholinergic input should sharpen frequency tuning (Bao 2001)."""
    m1 = PrimaryAuditoryCortex()
    m2 = PrimaryAuditoryCortex()
    no_ach = None
    with_ach = None
    for _ in range(15):
        no_ach = _tick(m1, {
            "MedialGeniculateNucleus": {"mgv_drive": 0.50},
        })
        with_ach = _tick(m2, {
            "MedialGeniculateNucleus": {"mgv_drive": 0.50},
            "NucleusBasalis": {"cholinergic_drive": 0.70},
        })
    assert with_ach["frequency_tuning"] > no_ach["frequency_tuning"]


def test_dorsal_vs_ventral_streams():
    """Both streams should activate but lc-dominant input shifts toward dorsal."""
    m = PrimaryAuditoryCortex()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "MedialGeniculateNucleus": {"mgv_drive": 0.55},
            "LocusCoeruleusCore": {"lc_drive": 0.55},
        })
    assert out["dorsal_stream_drive"] > 0.20
    assert out["ventral_stream_drive"] > 0.10


def test_quiet_no_input():
    m = PrimaryAuditoryCortex()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["a1_state"] == "quiet"
