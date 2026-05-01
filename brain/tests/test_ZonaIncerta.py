"""Behavioral tests for ZonaIncerta."""
import asyncio
from brain.mechanisms.ZonaIncerta import ZonaIncerta


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_cea_drive_engages_defensive_gate():
    """Central amygdala drives ZI defensive PAG gating
    (Hormigo 2020, Zhao 2019)."""
    m = ZonaIncerta()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "CentralAmygdalaMedial": {"cea_drive": 0.85},
            "PrimarySomatosensoryCortex": {"s1_output": 0.45},
        })
    assert out["zi_drive"] > 0.30
    assert out["pag_drive"] > 0.30
    assert out["zi_state"] in ("defensive_gate", "thalamic_gate", "tonic_active")


def test_thalamic_gating_with_sensory_drive():
    """High sensory drive without CeA → ZI tonic / thalamic gating
    (Trageser 2006)."""
    m = ZonaIncerta()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "PrimarySomatosensoryCortex": {"s1_output": 0.85},
            "SubstantiaNigraReticulata": {"snr_drive": 0.45},
        })
    assert out["thalamic_gating"] > 0.20
    assert out["zi_state"] in ("thalamic_gate", "tonic_active")


def test_no_cea_no_pag_drive():
    """Without CeA defensive context, PAG drive should remain low
    (Zhao 2019)."""
    m = ZonaIncerta()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "CentralAmygdalaMedial": {"cea_drive": 0.0},
            "PrimarySomatosensoryCortex": {"s1_output": 0.45},
        })
    assert out["pag_drive"] < 0.20


def test_quiet_no_input():
    m = ZonaIncerta()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["zi_state"] == "quiet"
