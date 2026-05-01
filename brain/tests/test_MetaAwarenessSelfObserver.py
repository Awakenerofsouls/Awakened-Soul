"""Behavioral tests for MetaAwarenessSelfObserver."""
import asyncio
from brain.mechanisms.MetaAwarenessSelfObserver import MetaAwarenessSelfObserver


def _tick(m, prior):
    return asyncio.run(m.tick({"prior_results": prior}))


def test_dmn_engagement_drives_self_observation():
    """Buckner 2008: DMN (vmPFC + PCC) supports self-referential."""
    m = MetaAwarenessSelfObserver()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VentromedialPrefrontalCortex": {"vmpfc_drive": 0.65,
                                                  "self_reference_signal": 0.55},
            "CingulatePosterior": {"pcc_drive": 0.55},
            "InsulaAnterior": {"aic_drive": 0.50},
            "FrontalPole": {"metacognitive_confidence": 0.40},
            "GlobalWorkspaceIntegrator": {"ignition_strength": 0.55},
        })
    assert out["meta_awareness_drive"] > 0.30
    assert out["self_observation_signal"] > 0.30
    assert out["meta_state"] in ("self_observing", "internally_focused")


def test_introspective_confidence_builds_with_sustained_engagement():
    """Fleming 2010: metacognitive accuracy is slow-integrating."""
    m = MetaAwarenessSelfObserver()
    out = None
    for _ in range(80):
        out = _tick(m, {
            "VentromedialPrefrontalCortex": {"vmpfc_drive": 0.65},
            "FrontalPole": {"metacognitive_confidence": 0.55},
            "GlobalWorkspaceIntegrator": {"ignition_strength": 0.65},
        })
    assert out["introspective_confidence"] > 0.10


def test_external_task_blocks_mind_wandering_state():
    """High external load → task_focused, not mind_wandering."""
    m = MetaAwarenessSelfObserver()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VentromedialPrefrontalCortex": {"vmpfc_drive": 0.55},
            "DorsolateralPrefrontalCortex": {"dlpfc_drive": 0.85},  # task load
            "CingulatePosterior": {"pcc_drive": 0.45},
        })
    assert out["meta_state"] == "task_focused"
    assert out["mind_wandering_index"] < 0.30


def test_low_load_with_ignition_can_wander():
    """Low external load + ignited cognition + DMN → mind-wandering."""
    m = MetaAwarenessSelfObserver()
    out = None
    for _ in range(15):
        out = _tick(m, {
            "VentromedialPrefrontalCortex": {"vmpfc_drive": 0.65},
            "CingulatePosterior": {"pcc_drive": 0.55},
            "GlobalWorkspaceIntegrator": {"ignition_strength": 0.55},
            # No DLPFC load
        })
    # Should be in some internal state
    assert out["meta_state"] in ("self_observing", "internally_focused",
                                     "mind_wandering")


def test_quiet_no_input():
    m = MetaAwarenessSelfObserver()
    out = None
    for _ in range(10):
        out = _tick(m, {})
    assert out["meta_state"] == "quiet"
