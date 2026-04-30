"""Behavioral tests for HierarchicalTopDownBottomUpEquilibrator."""
import asyncio
from brain.integration.HierarchicalTopDownBottomUpEquilibrator import HierarchicalTopDownBottomUpEquilibrator


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_balanced_streams_balanced_state():
    """Equal top-down and bottom-up → balanced state."""
    m = HierarchicalTopDownBottomUpEquilibrator()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "NetworkOscillationGlobalBalancer": {
                "top_down_signal": 0.55,
                "bottom_up_signal": 0.55,
            },
            "DorsolateralPrefrontalCortex": {"dlpfc_drive": 0.50},
        })
    assert 0.30 < out["equilibrium_signal"] < 0.70
    assert out["equilibrium_state"] == "balanced"


def test_strong_top_down_locks_priors():
    """Friston 2017: strong top-down with weak bottom-up = priors lock."""
    m = HierarchicalTopDownBottomUpEquilibrator()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "NetworkOscillationGlobalBalancer": {
                "top_down_signal": 0.85,
                "bottom_up_signal": 0.05,
            },
            "DorsolateralPrefrontalCortex": {"dlpfc_drive": 0.85},
        })
    assert out["equilibrium_signal"] < 0.35
    assert out["equilibrium_state"] == "top_down_locked"


def test_strong_bottom_up_overload():
    """Bastos 2015: strong bottom-up with weak prediction = overload."""
    m = HierarchicalTopDownBottomUpEquilibrator()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "NetworkOscillationGlobalBalancer": {
                "top_down_signal": 0.05,
                "bottom_up_signal": 0.85,
            },
            "ValenceTagger": {"valence_intensity": 0.65},
        })
    assert out["equilibrium_signal"] > 0.65
    assert out["equilibrium_state"] in ("bottom_up_overload", "updating")


def test_quiet_no_input():
    m = HierarchicalTopDownBottomUpEquilibrator()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["equilibrium_state"] == "quiet"
