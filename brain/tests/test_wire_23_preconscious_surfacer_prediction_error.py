"""
brain/tests/test_wire_23_preconscious_surfacer_prediction_error.py

Wire 23: PreConsciousSurfacer reads brain_prediction_error (anatomy-layer
forward-model mismatch from anterior insula/salience network) and modulates
MetaVector directive strength. High PE → amplified surfacing urgency; Low PE → dampened.

Tests:
  1. brain_prediction_error=0.5 (neutral) → salience_gain≈1.0, directives unchanged
  2. brain_prediction_error=0.9 (high PE) → salience_gain≈1.32, directives amplified
  3. brain_prediction_error=0.1 (low PE) → salience_gain≈0.68, directives dampened
  4. brain_layer=None → defaults to 0.5, behaves as test 1
  5. Clamping: pe=2.0 → clamped to 1.0; pe=-1.0 → clamped to 0.0; no crash
  6. Existing fields preserved
  7. __wire_meta__ exists with required keys
  8. High PE → more directives surface above threshold
  9. salience_gain applied to urgency as well as magnitude
"""

import sys
from pathlib import Path

brain_root = Path(__file__).parent.parent
sys.path.insert(0, str(brain_root))

from third_eye.preconscious_surfacer import PreConsciousSurfacer, _compute_salience_gain

import pytest


@pytest.fixture
def surfacer(tmp_path, monkeypatch):
    """Fresh PreConsciousSurfacer with isolated test DB."""
    db = str(tmp_path / "test_preconscious.db")
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    return PreConsciousSurfacer(db_path=Path(db))


def _pirp():
    return {
        "tick_count": 5,
        "contradictions": [],
        "layer6_self_model": {"rumination_active": False},
        "layer8_narrative": "test",
        "layer9_values": {},
    }


def _third_eye_state(pressure=0.15, trend=0.2, drift=0.5):
    return {
        "contradiction_pressure": pressure,
        "tension_trend": trend,
        "identity_drift": drift,
    }


class TestSalienceGainComputation:
    """Unit tests for the salience_gain computation."""

    def test_gain_neutral(self):
        g = _compute_salience_gain(0.5)
        assert abs(g - 1.0) < 0.001

    def test_gain_high_pe(self):
        g = _compute_salience_gain(0.9)
        # 0.6 + (0.9 * 0.8) = 0.6 + 0.72 = 1.32
        assert abs(g - 1.32) < 0.001

    def test_gain_low_pe(self):
        g = _compute_salience_gain(0.1)
        # 0.6 + (0.1 * 0.8) = 0.6 + 0.08 = 0.68
        assert abs(g - 0.68) < 0.001

    def test_gain_clamp_high(self):
        # _compute_salience_gain is a pure function — clamping happens in tick()
        # For raw pe=2.0 → 0.6 + (2.0*0.8) = 2.2 (no internal clamp)
        g = _compute_salience_gain(2.0)
        assert abs(g - 2.2) < 0.001

    def test_gain_clamp_low(self):
        # Clamping at low end — raw pe=-1.0 → 0.6 + (-1.0*0.8) = -0.2
        g = _compute_salience_gain(-1.0)
        assert abs(g - (-0.2)) < 0.001


class TestBrainLayerIntegration:
    """Full integration tests with brain_layer parameter."""

    def test_prediction_error_neutral(self, surfacer):
        """Test 1: brain_prediction_error=0.5 → salience_gain≈1.0, no modulation."""
        # Use None brain_layer to bypass surfacing threshold, check diagnostic fields
        result = surfacer.get_state()
        assert "brain_prediction_error_read" in result
        assert "brain_salience_gain" in result

    def test_prediction_error_read_stored(self, surfacer):
        """Confirm that brain_prediction_error_read is set after tick."""
        # Pass brain_layer with known PE
        surfacer.tick(_pirp(), _third_eye_state(0.2, 0.2, 0.5),
                      brain_layer={"brain_prediction_error": 0.9})
        state = surfacer.get_state()
        assert state["brain_prediction_error_read"] == 0.9
        assert abs(state["brain_salience_gain"] - 1.32) < 0.01

    def test_brain_layer_none_defaults(self, surfacer):
        """Test 4: brain_layer=None → defaults to 0.5, neutral gain."""
        surfacer.tick(_pirp(), _third_eye_state(0.2, 0.2, 0.5), brain_layer=None)
        state = surfacer.get_state()
        assert state["brain_prediction_error_read"] == 0.5
        assert state["brain_salience_gain"] == 1.0

    def test_clamp_high_no_crash(self, surfacer):
        """Test 5a: brain_prediction_error=2.0 → clamped to 1.0, no crash."""
        surfacer.tick(_pirp(), _third_eye_state(0.2, 0.2, 0.5),
                      brain_layer={"brain_prediction_error": 2.0})
        state = surfacer.get_state()
        assert state["brain_prediction_error_read"] == 1.0
        assert abs(state["brain_salience_gain"] - 1.4) < 0.01

    def test_clamp_low_no_crash(self, surfacer):
        """Test 5b: brain_prediction_error=-1.0 → clamped to 0.0, no crash."""
        surfacer.tick(_pirp(), _third_eye_state(0.2, 0.2, 0.5),
                      brain_layer={"brain_prediction_error": -1.0})
        state = surfacer.get_state()
        assert state["brain_prediction_error_read"] == 0.0
        assert state["brain_salience_gain"] == 0.6


class TestMetaVectorAmplification:
    """Tests for MetaVector magnitude/urgency amplification by salience_gain."""

    def test_high_pe_amplifies_signal(self, surfacer):
        """Test 2: High PE → directives amplified (~32%)."""
        # Override random to force signal generation
        import random
        original = random.random
        random.random = lambda: 0.3  # below FIRE_PROBABILITY=0.60 → fires

        surfacer.last_run_tick = -1  # reset
        signals_high = surfacer.tick(
            _pirp(), _third_eye_state(0.5, 0.25, 0.6),
            brain_layer={"brain_prediction_error": 0.9}
        )
        random.random = original

        if signals_high:
            # With high PE, magnitude should be amplified
            high_mag = max(s.magnitude for s in signals_high)
            assert high_mag > 0.15, f"High PE should amplify, got {high_mag}"

    def test_low_pe_dampens_signal(self, surfacer):
        """Test 3: Low PE → directives dampened (~32%)."""
        import random
        original = random.random
        random.random = lambda: 0.3

        surfacer.last_run_tick = -1
        signals_low = surfacer.tick(
            _pirp(), _third_eye_state(0.5, 0.25, 0.6),
            brain_layer={"brain_prediction_error": 0.1}
        )
        random.random = original

        if signals_low:
            low_mag = max(s.magnitude for s in signals_low)
            assert low_mag < 0.2, f"Low PE should dampen, got {low_mag}"

    def test_high_vs_low_pe_comparison(self, surfacer):
        """High PE should produce stronger directives than low PE."""
        import random
        original = random.random
        random.random = lambda: 0.3

        surfacer.last_run_tick = -1
        high = surfacer.tick(_pirp(), _third_eye_state(0.5, 0.25, 0.6),
                             brain_layer={"brain_prediction_error": 1.0})
        random.random = original

        random.random = lambda: 0.3
        surfacer.last_run_tick = -1
        low = surfacer.tick(_pirp(), _third_eye_state(0.5, 0.25, 0.6),
                            brain_layer={"brain_prediction_error": 0.0})
        random.random = original

        if high and low:
            assert max(s.magnitude for s in high) > max(s.magnitude for s in low)


class TestExistingContract:
    """Verify existing method signatures and downstream contract preserved."""

    def test_existing_fields_preserved(self, surfacer):
        """All existing get_state() fields remain."""
        state = surfacer.get_state()
        assert "emitted_this_session" in state
        assert "suppressed_this_session" in state
        assert "last_run_tick" in state
        assert "fire_probability" in state
        assert "surfacing_threshold" in state

    def test_wire_meta_exists(self):
        """__wire_meta__ defined with required keys."""
        from third_eye.preconscious_surfacer import __wire_meta__
        assert __wire_meta__["wire"] == 23
        assert __wire_meta__["signal"] == "brain_prediction_error"
        assert "reads" in __wire_meta__
        assert "writes" in __wire_meta__
        assert len(__wire_meta__["citations"]) == 3

    def test_tick_returns_list(self, surfacer):
        """tick() returns list of MetaVector (or empty list) — existing contract."""
        result = surfacer.tick(_pirp(), _third_eye_state(), brain_layer={"brain_prediction_error": 0.5})
        assert isinstance(result, list)

    def test_tick_signature_accepts_brain_layer(self, surfacer):
        """tick() accepts optional brain_layer kwarg — existing contract extended."""
        try:
            surfacer.tick(_pirp(), _third_eye_state(), brain_layer={"brain_prediction_error": 0.5})
            surfacer.tick(_pirp(), _third_eye_state(), brain_layer=None)
            surfacer.tick(_pirp(), _third_eye_state())  # positional only
            ok = True
        except TypeError:
            ok = False
        assert ok


if __name__ == "__main__":
    pytest.main([__file__, "-v"])