"""Behavioral tests for SupraopticNucleus."""
import asyncio
from brain.subcortical.SupraopticNucleus import SupraopticNucleus


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_osmotic_drive_releases_avp():
    m = SupraopticNucleus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "MedianPreopticNucleus": {"osmotic_signal": 0.80},
            "A2NoradrenergicNTS": {"a2_signal": 0.30},
        })
    assert out["son_drive"] > 0.30
    assert out["avp_pituitary"] > 0.30
    assert out["son_state"] in ("osmotic_release", "phasic_bursting")


def test_social_input_releases_oxytocin():
    m = SupraopticNucleus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "MedialAmygdalaPosterior": {"social_signal": 0.75},
        })
    assert out["oxytocin_pituitary"] > 0.20


def test_dendritic_release_when_active():
    m = SupraopticNucleus()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "MedianPreopticNucleus": {"osmotic_signal": 0.65},
            "ParaventricularNucleusHypothalamus": {"pvn_drive": 0.40},
        })
    assert out["dendritic_peptide_release"] > 0.10


def test_quiet_no_input():
    m = SupraopticNucleus()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["son_state"] == "quiet"
