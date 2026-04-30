"""Behavioral tests for InteroExteroceptiveMerger."""
import asyncio
from brain.integration.InteroExteroceptiveMerger import InteroExteroceptiveMerger


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_balanced_streams_balanced_merger():
    """When intero + extero streams are equal, balance is ~0.5."""
    m = InteroExteroceptiveMerger()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "InsulaAnterior": {"aic_drive": 0.55},
            "InsulaPosterior": {"posterior_insula_drive": 0.55},
            "PrimaryVisualCortex": {"v1_drive": 0.55},
            "PrimaryAuditoryCortex": {"a1_drive": 0.55},
            "PrimarySomatosensoryCortex": {"s1_drive": 0.55},
            "VentromedialPrefrontalCortex": {"vmpfc_drive": 0.45},
        })
    assert out["interoceptive_stream_strength"] > 0.20
    assert out["exteroceptive_stream_strength"] > 0.20
    assert 0.30 < out["precision_balance"] < 0.70


def test_high_intero_dominant():
    """Strong interoception with weak exteroception → intero-dominant."""
    m = InteroExteroceptiveMerger()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "InsulaAnterior": {"aic_drive": 0.85},
            "InsulaPosterior": {"posterior_insula_drive": 0.75},
            "VentromedialPrefrontalCortex": {"vmpfc_drive": 0.65},
            "AllostaticPredictiveAnticipator": {"prediction_error": 0.45},
        })
    assert out["precision_balance"] < 0.40
    assert out["merger_state"] == "intero_dominant"


def test_extero_only_with_no_intero_alexithymic():
    """Extero strong, intero absent → alexithymic-like state."""
    m = InteroExteroceptiveMerger()
    out = None
    for _ in range(20):
        out = _tick(m, {
            "PrimaryVisualCortex": {"v1_drive": 0.75},
            "PrimaryAuditoryCortex": {"a1_drive": 0.65},
            "PrimarySomatosensoryCortex": {"s1_drive": 0.55},
            # No interoceptive input at all
        })
    assert out["interoceptive_stream_strength"] < 0.15
    assert out["merger_state"] in ("alexithymic", "extero_dominant")


def test_quiet_no_input():
    m = InteroExteroceptiveMerger()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["merger_state"] == "quiet"
