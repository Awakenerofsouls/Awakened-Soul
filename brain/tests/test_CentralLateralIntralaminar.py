"""Behavioral tests for CentralLateralIntralaminar."""
import asyncio
from brain.mechanisms.CentralLateralIntralaminar import CentralLateralIntralaminar


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_arousal_inputs_drive_cortex():
    m = CentralLateralIntralaminar()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PedunculopontineCholinergic": {"ppn_drive": 0.65},
            "LocusCoeruleusCore": {"lc_drive": 0.55},
        })
    assert out["cl_drive"] > 0.30
    assert out["cortical_arousal_signal"] > 0.30
    assert out["cl_state"] in ("high_arousal", "vigilant")


def test_striatum_drive_active():
    m = CentralLateralIntralaminar()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PedunculopontineCholinergic": {"ppn_drive": 0.55},
            "LocusCoeruleusCore": {"lc_drive": 0.35},
        })
    assert out["striatum_drive_signal"] > 0.20


def test_vigilance_with_strong_arousal():
    m = CentralLateralIntralaminar()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "PedunculopontineCholinergic": {"ppn_drive": 0.75},
            "LocusCoeruleusCore": {"lc_drive": 0.65},
            "DorsalRaphe": {"raphe_drive": 0.45},
        })
    assert out["vigilance_signal"] > 0.30


def test_quiet_no_input():
    m = CentralLateralIntralaminar()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["cl_state"] == "quiet"
