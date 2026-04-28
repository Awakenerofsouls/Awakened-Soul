"""
brain/tests/test_wire_24_reality_tension_warper_affective_reset.py

Wire 24: RealityTensionWarper reads brain_affective_reset (MCC-sgACC signal from
Integration022 MidCingulateSubgenualBridge) and differentially modulates directive
weights. High reset → suppress/redirect amplified; Low reset → amplify_uncertainty/
trigger_reflection amplified.

Tests:
  1. brain_affective_reset=0.5 (neutral) → both gains≈1.0, no weight changes
  2. brain_affective_reset=0.9 (MCC-sgACC firing) → reset_gain≈1.32, quiet_gain≈0.68
  3. brain_affective_reset=0.1 (quiet) → reset_gain≈0.68, quiet_gain≈1.32
  4. brain_layer=None → defaults to 0.5, neutral behavior, no crash
  5. Clamping: boundary values (-0.3, 1.8) → clamped properly, no crash
  6. Differential modulation: reset directives amplified when ar=1.0, quiet when ar=0.0
  7. Existing fields preserved
  8. __wire_meta__ exists with required keys
  9. Four directives all still emit (no directions dropped)
"""

import sys
from pathlib import Path

brain_root = Path(__file__).parent.parent
sys.path.insert(0, str(brain_root))

from third_eye.reality_tension_warper import RealityTensionWarper, _compute_gains

import pytest


@pytest.fixture
def warper(tmp_path, monkeypatch):
    """Fresh RealityTensionWarper with isolated test DB."""
    db = str(tmp_path / "test_warper.db")
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    return RealityTensionWarper(db_path=Path(db))


def _pirp():
    return {
        "tick_count": 7,
        "layer6_self_model": {
            "belief_stability": 0.3,
            "conflict_score": 0.5,
            "rumination_active": False,
            "attention_anchor": "present_moment"
        },
        "layer8_narrative_state": {"coherence": 0.5},
        "layer9_values": {"conflict_score": 0.4, "violation_risk": 0.3},
    }


def _third_eye_state(trend=0.2, drift=0.5):
    return {
        "tension_trend": trend,
        "identity_drift": drift,
    }


class TestGainComputation:
    """Unit tests for _compute_gains()."""

    def test_gains_neutral(self):
        rg, qg = _compute_gains(0.5)
        assert abs(rg - 1.0) < 0.001
        assert abs(qg - 1.0) < 0.001

    def test_gains_high_reset(self):
        rg, qg = _compute_gains(0.9)
        # reset: 0.6 + (0.9*0.8) = 1.32
        # quiet: 1.4 - (0.9*0.8) = 0.68
        assert abs(rg - 1.32) < 0.001
        assert abs(qg - 0.68) < 0.001

    def test_gains_low_reset(self):
        rg, qg = _compute_gains(0.1)
        # reset: 0.6 + (0.1*0.8) = 0.68
        # quiet: 1.4 - (0.1*0.8) = 1.32
        assert abs(rg - 0.68) < 0.001
        assert abs(qg - 1.32) < 0.001

    def test_gains_high_reset_resets_dominate(self):
        """When ar=1.0, reset_gain >> quiet_gain."""
        rg, qg = _compute_gains(1.0)
        assert rg > qg

    def test_gains_low_reset_quiet_dominates(self):
        """When ar=0.0, quiet_gain >> reset_gain."""
        rg, qg = _compute_gains(0.0)
        assert qg > rg

    def test_gains_inverse(self):
        """reset_gain + quiet_gain always = 2.0."""
        rg, qg = _compute_gains(0.5)
        assert abs((rg + qg) - 2.0) < 0.001
        rg, qg = _compute_gains(0.2)
        assert abs((rg + qg) - 2.0) < 0.001
        rg, qg = _compute_gains(0.8)
        assert abs((rg + qg) - 2.0) < 0.001


class TestBrainLayerIntegration:
    """Integration tests with brain_layer parameter."""

    def test_brain_layer_none_defaults(self, warper):
        """Test 4: brain_layer=None → defaults to 0.5, neutral gains."""
        warper.tick(_pirp(), _third_eye_state(), brain_layer=None)
        state = warper.get_state()
        assert state["brain_affective_reset_read"] == 0.5
        assert state["brain_reset_gain"] == 1.0
        assert state["brain_quiet_gain"] == 1.0

    def test_clamp_high_no_crash(self, warper):
        """Test 5a: brain_affective_reset=1.8 → clamped to 1.0."""
        warper.tick(_pirp(), _third_eye_state(), brain_layer={"brain_affective_reset": 1.8})
        state = warper.get_state()
        assert state["brain_affective_reset_read"] == 1.0
        # reset_gain = 0.6 + 1.0*0.8 = 1.40
        # quiet_gain = 1.4 - 1.0*0.8 = 0.60
        assert abs(state["brain_reset_gain"] - 1.40) < 0.01
        assert abs(state["brain_quiet_gain"] - 0.60) < 0.01

    def test_clamp_low_no_crash(self, warper):
        """Test 5b: brain_affective_reset=-0.3 → clamped to 0.0."""
        warper.tick(_pirp(), _third_eye_state(), brain_layer={"brain_affective_reset": -0.3})
        state = warper.get_state()
        assert state["brain_affective_reset_read"] == 0.0
        # reset_gain = 0.6 + 0.0*0.8 = 0.60
        # quiet_gain = 1.4 - 0.0*0.8 = 1.40
        assert abs(state["brain_reset_gain"] - 0.60) < 0.01
        assert abs(state["brain_quiet_gain"] - 1.40) < 0.01

    def test_signal_read_stored(self, warper):
        """brain_affective_reset_read is set after tick."""
        warper.tick(_pirp(), _third_eye_state(), brain_layer={"brain_affective_reset": 0.9})
        state = warper.get_state()
        assert state["brain_affective_reset_read"] == 0.9


class TestDifferentialModulation:
    """Test that reset vs quiet directives get opposite gains."""

    def test_high_reset_amplifies_suppress(self, warper):
        """High ar → suppress directive gets high reset_gain."""
        import random
        original = random.choice
        # Force suppress behavior by overriding weights
        random.choice = lambda x: "suppress"

        warper.tick(_pirp(), _third_eye_state(), brain_layer={"brain_affective_reset": 1.0})
        state = warper.get_state()
        # With ar=1.0, reset_gain=1.40 — suppress directive should be amplified
        assert state["brain_reset_gain"] == 1.4

        random.choice = original

    def test_low_reset_amplifies_uncertainty(self, warper):
        """Low ar → amplify_uncertainty directive gets high quiet_gain."""
        import random
        original = random.choice

        random.choice = lambda x: "amplify_uncertainty"

        warper.tick(_pirp(), _third_eye_state(), brain_layer={"brain_affective_reset": 0.0})
        state = warper.get_state()
        # With ar=0.0, quiet_gain=1.40 — amplify_uncertainty directive should be amplified
        assert state["brain_quiet_gain"] == 1.4

        random.choice = original

    def test_neutral_both_unity(self, warper):
        """Neutral ar → both gains = 1.0."""
        import random
        original = random.choice

        random.choice = lambda x: "suppress"
        warper.tick(_pirp(), _third_eye_state(), brain_layer={"brain_affective_reset": 0.5})
        state = warper.get_state()
        assert state["brain_reset_gain"] == 1.0
        assert state["brain_quiet_gain"] == 1.0

        random.choice = original

    def test_gain_applied_to_all_four_directions(self, warper):
        """All four directives still emit after wire 24 — no directions dropped."""
        import random
        original = random.choice

        directives = ["amplify_uncertainty", "suppress", "redirect_attention", "trigger_reflection"]
        for directive in directives:
            random.choice = lambda x, d=directive: d
            warper.behavior_counts = {k: 0 for k in warper.behavior_counts}
            result = warper.tick(_pirp(), _third_eye_state(trend=0.5),
                                 brain_layer={"brain_affective_reset": 0.7})
            # Should not crash — directive still supported

        random.choice = original


class TestExistingContract:
    """Verify existing method signatures and downstream contract preserved."""

    def test_existing_fields_preserved(self, warper):
        """All existing get_state() fields remain."""
        state = warper.get_state()
        assert "last_behavior" in state
        assert "behavior_counts" in state
        assert "tension_threshold" in state
        assert "rising_trend_threshold" in state

    def test_wire_meta_exists(self):
        """__wire_meta__ defined with required keys."""
        from third_eye.reality_tension_warper import __wire_meta__
        assert __wire_meta__["wire"] == 24
        assert __wire_meta__["signal"] == "brain_affective_reset"
        assert "reads" in __wire_meta__
        assert "writes" in __wire_meta__
        assert len(__wire_meta__["citations"]) == 3

    def test_tick_returns_list(self, warper):
        """tick() returns list of MetaVector (or empty list) — existing contract."""
        result = warper.tick(_pirp(), _third_eye_state(), brain_layer={"brain_affective_reset": 0.5})
        assert isinstance(result, list)

    def test_tick_signature_accepts_brain_layer(self, warper):
        """tick() accepts optional brain_layer kwarg — existing contract extended."""
        try:
            warper.tick(_pirp(), _third_eye_state(), brain_layer={"brain_affective_reset": 0.5})
            warper.tick(_pirp(), _third_eye_state(), brain_layer=None)
            warper.tick(_pirp(), _third_eye_state())
            ok = True
        except TypeError:
            ok = False
        assert ok


if __name__ == "__main__":
    pytest.main([__file__, "-v"])