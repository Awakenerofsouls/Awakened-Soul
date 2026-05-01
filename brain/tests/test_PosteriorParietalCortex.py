"""Behavioral tests for PosteriorParietalCortex (PPC)."""
import asyncio
from brain.mechanisms.PosteriorParietalCortex import PosteriorParietalCortex


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_multimodal_input_engages_ppc():
    """Multiple-modality input should boost PPC drive and integration."""
    m = PosteriorParietalCortex()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VisualCortexV1": {"v1_drive": 0.55, "salient_direction": "left"},
            "PrimarySomatosensoryCortex": {"s1_drive": 0.45},
            "PrimaryAuditoryCortex": {"a1_drive": 0.40},
        })
    assert out["ppc_drive"] > 0.30
    assert out["multimodal_integration"] > 0.20
    assert out["spatial_direction"] == "left"


def test_body_schema_from_s1_vestibular():
    """Somatosensory + vestibular drive should engage body schema (Andersen 1997)."""
    m = PosteriorParietalCortex()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "PrimarySomatosensoryCortex": {"s1_drive": 0.65},
            "VestibularNuclei": {"vestibular_drive": 0.55},
        })
    assert out["body_schema_signal"] > 0.25
    assert out["ppc_state"] in ("body_schema_active", "intention", "spatial_attention")


def test_neglect_index_with_asymmetric_hemifield():
    """Asymmetric hemifield drives produce non-zero neglect index."""
    m = PosteriorParietalCortex()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VisualCortexV1": {
                "v1_drive": 0.50,
                "left_hemifield": 0.10,
                "right_hemifield": 0.70,
            },
        })
    assert out["neglect_index"] > 0.30


def test_quiet_no_input():
    m = PosteriorParietalCortex()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["ppc_state"] == "quiet"
