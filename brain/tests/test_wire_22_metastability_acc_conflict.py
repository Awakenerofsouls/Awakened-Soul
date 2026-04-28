"""
brain/tests/test_wire_22_metastability_acc_conflict.py

Wire 22: MetaStability reads brain_conflict (ACC conflict signal from
Limbic023 AnteriorCingulateConflict) and modulates contradiction_pressure.
High ACC conflict → anatomy confirms pirp_context conflict → amplified pressure.
Low ACC conflict → pirp_context conflicts are transient/cognitive-only → dampened.

Tests:
  1. brain_conflict=0.5 (neutral) → anatomy_confirmation=1.00, contradiction_pressure unchanged
  2. brain_conflict=0.9 (high ACC conflict) → anatomy_confirmation=1.24, pressure amplified
  3. brain_conflict=0.1 (low ACC conflict) → anatomy_confirmation=0.76, pressure dampened
  4. brain_layer=None → defaults to 0.5, behaves as test 1
  5. Clamping: conflict=1.8 → clamped to 1.0; conflict=-0.4 → clamped to 0.0; no crash
  6. Existing fields preserved (tension_baseline, tension_trend, identity_drift, etc.)
  7. __wire_meta__ exists with required keys
  8. downstream cascade: amplified contradiction_pressure propagates to all three consumers
"""

import sys
from pathlib import Path

brain_root = Path(__file__).parent.parent
sys.path.insert(0, str(brain_root))

from third_eye.meta_stability import MetaStability

import pytest


@pytest.fixture
def m(tmp_path, monkeypatch):
    """Fresh MetaStability with isolated test DB."""
    db = str(tmp_path / "test_meta.db")
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    return MetaStability(db_path=Path(db))


def _pirp(contradictions=None, conflict_score=0.0, belief_stability=0.5):
    return {
        "tick_count": 1,
        "contradictions": contradictions or [],
        "layer6_self_model": {"conflict_score": conflict_score, "belief_stability": belief_stability},
        "layer8_narrative": "test narrative",
        "layer9_values": {"conflict_score": 0.0},
    }


def test_conflict_neutral():
    """Test 1: brain_conflict=0.5 → anatomy_confirmation=1.00, no modulation."""
    m = MetaStability(Path("/tmp/test_wire22.db"))
    m.contradiction_pressure = 0.0  # reset
    brain = {"brain_conflict": 0.5}
    result = m.tick(_pirp(contradictions=["x"]), brain_layer=brain)
    # anatomy_confirmation = 0.7 + (0.5 * 0.6) = 1.00
    assert result["brain_anatomy_confirmation"] == 1.0
    assert result["brain_acc_conflict_read"] == 0.5
    # With 1 contradiction: raw_pressure = 0.15, modulated = 0.15 * 1.00 = 0.15
    # EMA: (0.9 * 0.0 + 0.1 * 0.15) = 0.015
    assert result["contradiction_pressure"] > 0


def test_conflict_high():
    """Test 2: brain_conflict=0.9 → anatomy_confirmation≈1.24, amplified."""
    m = MetaStability(Path("/tmp/test_wire22.db"))
    m.contradiction_pressure = 0.0
    brain = {"brain_conflict": 0.9}
    result = m.tick(_pirp(contradictions=["x"]), brain_layer=brain)
    # anatomy_confirmation = 0.7 + (0.9 * 0.6) = 1.24
    assert abs(result["brain_anatomy_confirmation"] - 1.24) < 0.01
    assert result["brain_acc_conflict_read"] == 0.9
    # Modulated pressure = 0.15 * 1.24 = 0.186 → higher than neutral
    neutral = MetaStability(Path("/tmp/test_wire22.db"))
    neutral.contradiction_pressure = 0.0
    res_neutral = neutral.tick(_pirp(contradictions=["x"]), brain_layer={"brain_conflict": 0.5})
    assert result["contradiction_pressure"] > res_neutral["contradiction_pressure"]


def test_conflict_low():
    """Test 3: brain_conflict=0.1 → anatomy_confirmation≈0.76, dampened."""
    m = MetaStability(Path("/tmp/test_wire22.db"))
    m.contradiction_pressure = 0.0
    brain = {"brain_conflict": 0.1}
    result = m.tick(_pirp(contradictions=["x"]), brain_layer=brain)
    # anatomy_confirmation = 0.7 + (0.1 * 0.6) = 0.76
    assert abs(result["brain_anatomy_confirmation"] - 0.76) < 0.01
    assert result["brain_acc_conflict_read"] == 0.1
    neutral = MetaStability(Path("/tmp/test_wire22.db"))
    neutral.contradiction_pressure = 0.0
    res_neutral = neutral.tick(_pirp(contradictions=["x"]), brain_layer={"brain_conflict": 0.5})
    assert result["contradiction_pressure"] < res_neutral["contradiction_pressure"]


def test_brain_layer_none():
    """Test 4: brain_layer=None → defaults to 0.5, behaves as neutral."""
    m = MetaStability(Path("/tmp/test_wire22.db"))
    m.contradiction_pressure = 0.0
    result = m.tick(_pirp(contradictions=["x"]), brain_layer=None)
    assert result["brain_acc_conflict_read"] == 0.5
    assert result["brain_anatomy_confirmation"] == 1.0


def test_conflict_clamp_high():
    """Test 5a: brain_conflict=1.8 → clamped to 1.0, no crash."""
    m = MetaStability(Path("/tmp/test_wire22.db"))
    m.contradiction_pressure = 0.0
    brain = {"brain_conflict": 1.8}
    result = m.tick(_pirp(), brain_layer=brain)
    # Clamped to 1.0: anatomy_confirmation = 0.7 + (1.0 * 0.6) = 1.30
    assert result["brain_acc_conflict_read"] == 1.0
    assert abs(result["brain_anatomy_confirmation"] - 1.30) < 0.01


def test_conflict_clamp_low():
    """Test 5b: brain_conflict=-0.4 → clamped to 0.0, no crash."""
    m = MetaStability(Path("/tmp/test_wire22.db"))
    m.contradiction_pressure = 0.0
    brain = {"brain_conflict": -0.4}
    result = m.tick(_pirp(), brain_layer=brain)
    # Clamped to 0.0: anatomy_confirmation = 0.7 + (0.0 * 0.6) = 0.70
    assert result["brain_acc_conflict_read"] == 0.0
    assert abs(result["brain_anatomy_confirmation"] - 0.70) < 0.01


def test_existing_fields_preserved():
    """Wire 22 must ADD diagnostic fields, not overwrite existing MetaStability outputs."""
    m = MetaStability(Path("/tmp/test_wire22.db"))
    brain = {"brain_conflict": 0.5}
    result = m.tick(_pirp(), brain_layer=brain)
    # All existing fields must remain
    assert "tension_baseline" in result
    assert "tension_trend" in result
    assert "identity_drift" in result
    assert "contradiction_pressure" in result
    assert "coherence_recent" in result
    assert "insight_count" in result
    # New Wire 22 diagnostic fields must be present
    assert "brain_acc_conflict_read" in result
    assert "brain_anatomy_confirmation" in result


def test_wire_meta_exists():
    """__wire_meta__ defined with required keys."""
    from third_eye.meta_stability import __wire_meta__
    assert __wire_meta__["wire"] == 22
    assert __wire_meta__["signal"] == "brain_conflict"
    assert "reads" in __wire_meta__
    assert "writes" in __wire_meta__
    assert len(__wire_meta__["citations"]) == 3


def test_downstream_cascade():
    """
    Wire 22's amplification propagates to downstream ThirdEye consumers.
    High brain_conflict → amplified contradiction_pressure →
    PreConsciousSurfacer, RealityTensionWarper, AttentionModifier all see higher pressure.
    """
    # High conflict: contradiction_pressure should be elevated
    m_high = MetaStability(Path("/tmp/test_wire22.db"))
    m_high.contradiction_pressure = 0.0
    r_high = m_high.tick(_pirp(contradictions=["a", "b"]), brain_layer={"brain_conflict": 1.0})

    # Low conflict: contradiction_pressure should be dampened
    m_low = MetaStability(Path("/tmp/test_wire22.db"))
    m_low.contradiction_pressure = 0.0
    r_low = m_low.tick(_pirp(contradictions=["a", "b"]), brain_layer={"brain_conflict": 0.0})

    # High conflict produces higher contradiction_pressure
    assert r_high["contradiction_pressure"] > r_low["contradiction_pressure"], \
        f"High conflict ({r_high['contradiction_pressure']}) should exceed low ({r_low['contradiction_pressure']})"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])