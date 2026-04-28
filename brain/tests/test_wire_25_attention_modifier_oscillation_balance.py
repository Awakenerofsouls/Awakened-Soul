"""
brain/tests/test_wire_25_attention_modifier_oscillation_balance.py

Wire 25: AttentionModifier reads brain_oscillation_balance (alpha/gamma ratio from
Integration018 AlphaGammaBridge) and modulates meta_vector directive weights via
attention_gate. Gamma-dominant (high) opens gate (lower dampening); Alpha-dominant
(low) closes gate (higher dampening). Inverse relationship.

Note: brain_oscillation_balance is intentionally shared with SS Wire 17 (PDS) —
different consumers, no conflict.

Tests:
  1. brain_oscillation_balance=0.5 (neutral) → attention_gate=1.0, no change
  2. brain_oscillation_balance=0.9 (gamma-dominant) → attention_gate≈0.76, gate opens
  3. brain_oscillation_balance=0.1 (alpha-dominant) → attention_gate≈1.24, gate closes
  4. brain_layer=None → defaults to 0.5, neutral behavior, no crash
  5. Clamping: values (-0.5, 1.5) → clamped properly, no crash
  6. attention_gate applied to meta_vector magnitudes in-place
  7. Existing fields preserved
  8. __wire_meta__ exists with required keys
  9. attention_gate AND boost both applied correctly (no double-application)
"""

import sys
from pathlib import Path

brain_root = Path(__file__).parent.parent
sys.path.insert(0, str(brain_root))

from third_eye.attention_modifier import AttentionModifier

import pytest


@pytest.fixture
def modifier(tmp_path, monkeypatch):
    """Fresh AttentionModifier with isolated test DB."""
    db = str(tmp_path / "test_attention.db")
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    return AttentionModifier(db_path=Path(db))


def _pirp():
    return {"tick_count": 11}


def _third_eye_state(pressure=0.0, drift=0.0, trend=0.0):
    return {
        "contradiction_pressure": pressure,
        "identity_drift": drift,
        "tension_trend": trend,
    }


class MockMetaVector:
    """Minimal mock for meta_vector signal."""
    def __init__(self, magnitude=0.2):
        self.type = "meta_vector"
        self.magnitude = magnitude


class TestAttentionGateComputation:
    """Verify attention_gate formula: gate = 1.3 - (balance * 0.6)."""

    def test_gate_neutral(self, modifier):
        """Test 1: balance=0.5 → gate=1.0, no modulation."""
        modifier.tick([], _third_eye_state(), _pirp(),
                      brain_layer={"brain_oscillation_balance": 0.5})
        state = modifier.get_state()
        assert abs(state["brain_attention_gate"] - 1.0) < 0.01

    def test_gate_gamma_dominant(self, modifier):
        """Test 2: balance=0.9 → gate≈0.76, gate opens."""
        modifier.tick([], _third_eye_state(), _pirp(),
                      brain_layer={"brain_oscillation_balance": 0.9})
        state = modifier.get_state()
        # 1.3 - (0.9 * 0.6) = 1.3 - 0.54 = 0.76
        assert abs(state["brain_attention_gate"] - 0.76) < 0.01

    def test_gate_alpha_dominant(self, modifier):
        """Test 3: balance=0.1 → gate≈1.24, gate closes."""
        modifier.tick([], _third_eye_state(), _pirp(),
                      brain_layer={"brain_oscillation_balance": 0.1})
        state = modifier.get_state()
        # 1.3 - (0.1 * 0.6) = 1.3 - 0.06 = 1.24
        assert abs(state["brain_attention_gate"] - 1.24) < 0.01

    def test_gate_full_gamma(self, modifier):
        """Gamma-dominant (1.0) → gate minimum 0.7."""
        modifier.tick([], _third_eye_state(), _pirp(),
                      brain_layer={"brain_oscillation_balance": 1.0})
        state = modifier.get_state()
        # 1.3 - 0.6 = 0.7
        assert abs(state["brain_attention_gate"] - 0.7) < 0.01

    def test_gate_full_alpha(self, modifier):
        """Alpha-dominant (0.0) → gate maximum 1.3."""
        modifier.tick([], _third_eye_state(), _pirp(),
                      brain_layer={"brain_oscillation_balance": 0.0})
        state = modifier.get_state()
        assert abs(state["brain_attention_gate"] - 1.3) < 0.01


class TestBrainLayerIntegration:
    """Integration tests with brain_layer parameter."""

    def test_brain_layer_none_defaults(self, modifier):
        """Test 4: brain_layer=None → defaults to 0.5, neutral gate."""
        modifier.tick([], _third_eye_state(), _pirp(), brain_layer=None)
        state = modifier.get_state()
        assert state["brain_oscillation_balance_read"] == 0.5
        assert state["brain_attention_gate"] == 1.0

    def test_clamp_high_no_crash(self, modifier):
        """Test 5a: brain_oscillation_balance=1.5 → clamped to 1.0."""
        modifier.tick([], _third_eye_state(), _pirp(),
                      brain_layer={"brain_oscillation_balance": 1.5})
        state = modifier.get_state()
        assert state["brain_oscillation_balance_read"] == 1.0
        assert state["brain_attention_gate"] == 0.7

    def test_clamp_low_no_crash(self, modifier):
        """Test 5b: brain_oscillation_balance=-0.5 → clamped to 0.0."""
        modifier.tick([], _third_eye_state(), _pirp(),
                      brain_layer={"brain_oscillation_balance": -0.5})
        state = modifier.get_state()
        assert state["brain_oscillation_balance_read"] == 0.0
        assert state["brain_attention_gate"] == 1.3

    def test_signal_read_stored(self, modifier):
        """brain_oscillation_balance_read is set after tick."""
        modifier.tick([], _third_eye_state(), _pirp(),
                      brain_layer={"brain_oscillation_balance": 0.85})
        state = modifier.get_state()
        assert state["brain_oscillation_balance_read"] == 0.85


class TestMetaVectorWeightModulation:
    """Test that attention_gate is applied in-place to meta_vector magnitudes."""

    def test_gate_multiplies_magnitude(self, modifier):
        """Test 6: attention_gate applied to meta_vector magnitudes in-place."""
        signals = [MockMetaVector(magnitude=0.2), MockMetaVector(magnitude=0.3)]
        modifier.tick(signals, _third_eye_state(), _pirp(),
                      brain_layer={"brain_oscillation_balance": 0.5})
        # With neutral gate (1.0), magnitudes unchanged
        assert abs(signals[0].magnitude - 0.2) < 0.001

    def test_gate_opens_gamma_dominant(self, modifier):
        """Gamma-dominant (gate=0.76) → magnitudes increase (less dampening)."""
        # Note: with boost=0 and neutral third_eye_state, we just test gate application
        signals = [MockMetaVector(magnitude=0.2)]
        modifier.tick(signals, _third_eye_state(pressure=0.0, drift=0.0, trend=0.0),
                      _pirp(), brain_layer={"brain_oscillation_balance": 1.0})
        # gate=0.7, so 0.2 * 0.7 = 0.14 — but note: boost may also apply
        # With no boost triggers, boosted = gated + 0 = gated
        # Actual: gated = 0.2 * 0.7 = 0.14
        assert signals[0].magnitude < 0.2

    def test_gate_closes_alpha_dominant(self, modifier):
        """Alpha-dominant (gate=1.24) → magnitudes increase (more dampening)."""
        signals = [MockMetaVector(magnitude=0.2)]
        modifier.tick(signals, _third_eye_state(pressure=0.0, drift=0.0, trend=0.0),
                      _pirp(), brain_layer={"brain_oscillation_balance": 0.0})
        # gate=1.3, so 0.2 * 1.3 = 0.26 — but note: boost may also apply
        # With no boost triggers, boosted = gated + 0 = gated
        # Actual: gated = 0.2 * 1.3 = 0.26
        assert signals[0].magnitude > 0.2

    def test_non_meta_vector_unchanged(self, modifier):
        """Only meta_vector signals are modified — other types pass through."""
        class NonMetaSignal:
            type = "not_meta"
            magnitude = 0.5

        signals = [NonMetaSignal()]
        signals = modifier.tick(signals, _third_eye_state(), _pirp(),
                                brain_layer={"brain_oscillation_balance": 0.5})
        # Should not crash, should not modify non-meta_vector
        assert signals[0].magnitude == 0.5

    def test_gamma_vs_alpha_opposite_effect(self, modifier):
        """Same signal processed with gamma vs alpha produces opposite results."""
        sig_gamma = MockMetaVector(magnitude=0.2)
        sig_alpha = MockMetaVector(magnitude=0.2)

        modifier.tick([sig_gamma], _third_eye_state(), _pirp(),
                      brain_layer={"brain_oscillation_balance": 1.0})
        modifier.tick([sig_alpha], _third_eye_state(), _pirp(),
                      brain_layer={"brain_oscillation_balance": 0.0})

        # Gamma → smaller magnitude (gate opens, less dampening)
        # Alpha → larger magnitude (gate closes, more dampening)
        # Note: with no boost active, these should be 0.14 (gamma) vs 0.26 (alpha)
        assert sig_gamma.magnitude < sig_alpha.magnitude


class TestBoostAndGateCombined:
    """Test that attention_gate and ThirdEye boost both apply correctly."""

    def test_gate_applied_before_boost(self, modifier):
        """Gate is applied first (oscillation-based), then boost on top."""
        signals = [MockMetaVector(magnitude=0.2)]
        # With contradiction pressure above threshold, boost triggers
        modifier.tick(signals, _third_eye_state(pressure=0.25, drift=0.0, trend=0.0),
                      _pirp(), brain_layer={"brain_oscillation_balance": 0.5})
        # With gate=1.0 and boost active, boosted = gated + boost*gated
        # boost = (0.25-0.15)*0.6 = 0.06, capped at 0.35
        # boosted = 0.2 + 0.06*0.2 = 0.212
        assert signals[0].magnitude > 0.2

    def test_gamma_with_high_boost(self, modifier):
        """When both gamma opens gate AND high contradiction triggers boost."""
        signals = [MockMetaVector(magnitude=0.2)]
        modifier.tick(signals, _third_eye_state(pressure=0.30, drift=0.5, trend=0.15),
                      _pirp(), brain_layer={"brain_oscillation_balance": 0.8})
        # gate = 1.3 - 0.48 = 0.82
        # boost from pressure: (0.30-0.15)*0.6 = 0.09
        # boost from drift: (0.5-0.35)*0.4 = 0.06
        # boost from trend: 0.15*0.2 = 0.03
        # total boost ≈ 0.18, capped at 0.35
        # gated = 0.2 * 0.82 = 0.164
        # boosted = 0.164 + 0.18*0.164 ≈ 0.194
        # Result should be less than original 0.2 because gate effect dominates
        assert signals[0].magnitude < 0.2


class TestExistingContract:
    """Verify existing method signatures and downstream contract preserved."""

    def test_existing_fields_preserved(self, modifier):
        """All existing get_state() fields remain."""
        state = modifier.get_state()
        assert "current_boost" in state
        assert "ticks_active" in state
        assert "ticks_inactive" in state
        assert "max_boost_cap" in state
        assert "triggers" in state

    def test_wire_meta_exists(self):
        """__wire_meta__ defined with required keys."""
        from third_eye.attention_modifier import __wire_meta__
        assert __wire_meta__["wire"] == 25
        assert __wire_meta__["signal"] == "brain_oscillation_balance"
        assert "reads" in __wire_meta__
        assert "writes" in __wire_meta__
        assert len(__wire_meta__["citations"]) == 3

    def test_tick_returns_list(self, modifier):
        """tick() returns modified signal list — existing contract."""
        result = modifier.tick([], _third_eye_state(), _pirp(),
                              brain_layer={"brain_oscillation_balance": 0.5})
        assert isinstance(result, list)

    def test_tick_signature_accepts_brain_layer(self, modifier):
        """tick() accepts optional brain_layer kwarg — existing contract extended."""
        try:
            modifier.tick([], _third_eye_state(), _pirp(),
                         brain_layer={"brain_oscillation_balance": 0.5})
            modifier.tick([], _third_eye_state(), _pirp(), brain_layer=None)
            modifier.tick([], _third_eye_state(), _pirp())
            ok = True
        except TypeError:
            ok = False
        assert ok


if __name__ == "__main__":
    pytest.main([__file__, "-v"])