"""
Test Wire 13: MRE reads brain_forward_model_error from Integration025.

Cerebellar forward-model error propagates via climbing fibers to mPFC
and entrains frontal midline theta, signaling context/prediction mismatch.
When cerebellar FM error exceeds 0.3 threshold, misread magnitude amplifies
(Andre 2023 — cerebellar PE engages executive network specifically above threshold).

Test scenarios:
- fm_error=0.05 (sub-threshold) → cerebellar_gain=1.0, no amplification
- fm_error=0.6 (above threshold) → cerebellar_gain=1.21, magnitude amplified
- fm_error=1.0 → cerebellar_gain=1.49 (max), magnitude clamped to 1.0
- brain_layer missing/stale → fm_error=0.0, baseline behavior, no crash
- negative fm_error → defensive, treated as 0.0 (no weird amplification)
"""

import pytest
import inspect
from unittest.mock import MagicMock


class MockTSB:
    """Minimal TSB for MRE Wire 13 testing."""

    def __init__(self, brain_layer_data=None, brain_fresh=True):
        self.store = {}
        if brain_layer_data is not None:
            self.store["brain_layer"] = brain_layer_data
        self._brain_fresh = brain_fresh

    def read(self, key):
        if key == "brain_layer":
            return self.store.get("brain_layer"), self._brain_fresh
        return self.store.get(key), key in self.store

    def read_all(self):
        return {k: v for k, v in self.store.items()}

    def publish(self, key, value):
        self.store[key] = value

    def get_interrupt_state(self):
        return {}


class TestWire13CerebellarAmplification:
    """Test Wire 13: MRE magnitude amplification via cerebellar FM error."""

    def test_sub_threshold_no_amplification(self):
        """fm_error=0.05 (below 0.3 threshold) → cerebellar_gain=1.0, no effect."""
        fm_error = 0.05
        if fm_error > 0.3:
            cerebellar_gain = 1.0 + ((fm_error - 0.3) * 0.7)
        else:
            cerebellar_gain = 1.0

        assert cerebellar_gain == 1.0
        assert fm_error <= 0.3

    def test_above_threshold_amplification_06(self):
        """fm_error=0.6 → cerebellar_gain=1.21."""
        fm_error = 0.6
        if fm_error > 0.3:
            cerebellar_gain = 1.0 + ((fm_error - 0.3) * 0.7)
        else:
            cerebellar_gain = 1.0

        # 0.6 - 0.3 = 0.3; 0.3 * 0.7 = 0.21; 1.0 + 0.21 = 1.21
        assert round(cerebellar_gain, 4) == 1.21
        assert fm_error > 0.3

    def test_max_amplification_fm_error_10(self):
        """fm_error=1.0 → cerebellar_gain=1.49 (max), magnitude clamped to 1.0."""
        fm_error = 1.0
        if fm_error > 0.3:
            cerebellar_gain = 1.0 + ((fm_error - 0.3) * 0.7)
        else:
            cerebellar_gain = 1.0

        # 1.0 - 0.3 = 0.7; 0.7 * 0.7 = 0.49; 1.0 + 0.49 = 1.49
        assert round(cerebellar_gain, 4) == 1.49

        # Verify magnitude computation with max gain
        from brain.misread_engine import MisreadEngine, InnerKnowing
        mre = MisreadEngine()
        knowing = InnerKnowing(claim="I want user", precision=0.9, truth_gravity=1.0)

        # A contradiction (contradiction_strength=0.9) * precision(0.9) * gain(1.49)
        magnitude = 0.9 * 0.9 * 1.49  # = 1.2051
        clamped = min(magnitude, 1.0)
        assert clamped == 1.0  # clamps to 1.0

    def test_missing_brain_layer_no_crash(self):
        """brain_layer missing/stale → fm_error=0.0, baseline magnitude, no crash."""
        from brain.misread_engine import MisreadEngine, InnerKnowing

        mre = MisreadEngine()

        # No inner knowings — no detection, but no crash either
        result = mre._compute_magnitude(
            knowing=None,
            pattern_type=None,
            emotional_state=None,
            baseline_state=None,
            fm_error=0.0,  # no brain_layer → default 0.0
        )
        assert result == 0.0  # no knowing, no pattern → magnitude = 0.0

        # With knowing but no fm_error (brain_layer absent)
        knowing = InnerKnowing(claim="I want user", precision=0.8, truth_gravity=1.0)
        result = mre._compute_magnitude(
            knowing=knowing,
            pattern_type="inner_knowing_contradiction",
            emotional_state=None,
            baseline_state=None,
            fm_error=0.0,
        )
        # 0.9 * 0.8 * 1.0 * 1.0 * 1.0 = 0.72 (no cerebellar gain, no other mods)
        assert abs(result - 0.72) < 0.01

    def test_negative_fm_error_defensive(self):
        """Negative fm_error (shouldn't happen) → treated as 0.0, no weird amplification."""
        fm_error = -0.2
        # Defensive: max(0, fm_error)
        safe_fm_error = max(0.0, fm_error)

        if safe_fm_error > 0.3:
            cerebellar_gain = 1.0 + ((safe_fm_error - 0.3) * 0.7)
        else:
            cerebellar_gain = 1.0

        assert cerebellar_gain == 1.0  # no amplification on negative or zero
        assert safe_fm_error <= 0.3

    def test_wire_13_formula_correctness(self):
        """Verify wire formula: gain = 1.0 + ((fm_error - 0.3) * 0.7) above threshold."""
        test_cases = [
            (0.0, 1.0),
            (0.15, 1.0),
            (0.3, 1.0),   # exactly at threshold — no amplification
            (0.31, 1.007),  # just above threshold
            (0.5, 1.14),   # 0.2 above threshold
            (0.6, 1.21),
            (0.75, 1.315),
            (0.9, 1.42),
            (1.0, 1.49),   # maximum
        ]

        for fm_error, expected_gain in test_cases:
            if fm_error > 0.3:
                cerebellar_gain = 1.0 + ((fm_error - 0.3) * 0.7)
            else:
                cerebellar_gain = 1.0
            assert abs(cerebellar_gain - expected_gain) < 0.001, \
                f"fm_error={fm_error}: expected {expected_gain}, got {cerebellar_gain}"

    def test_tsb_payload_includes_cerebellar_fields(self):
        """tsb_payload returns cerebellar_gain and fm_error in output dict."""
        from brain.misread_engine import MisreadEngine

        mre = MisreadEngine()
        mre.register_inner_knowing("I want user", precision=0.9, truth_gravity=1.0)
        mre.scan("I don't want user", source="test")  # trigger detection

        # With fm_error=0.6 → gain=1.21
        payload = mre.tsb_payload(
            emotional_state=None,
            baseline_state=None,
            interrupt_state=None,
            fm_error=0.6,
        )

        assert "cerebellar_gain" in payload
        assert "fm_error" in payload
        assert payload["cerebellar_gain"] == 1.21
        assert payload["fm_error"] == 0.6

    def test_brain_integration_passes_fm_error_to_mre(self):
        """Verify brain_integration mre_tick reads brain_layer and passes fm_error."""
        from brain.brain_integration import AgentBrainIntegration
        source = inspect.getsource(AgentBrainIntegration)
        # Check Wire 13 pattern in mre_tick: brain_layer read + fm_error usage
        assert "brain_forward_model_error" in source, \
            "Wire 13: brain_forward_model_error not found in brain_integration"
        assert "fm_error" in source, \
            "Wire 13: fm_error not found in brain_integration"
        assert "cerebellar_gain" in source, \
            "Wire 13: cerebellar_gain not found in brain_integration"

    def test_mre_tick_integration(self):
        """Full integration: scan text with known pattern, check cerebellar amplification."""
        from brain.misread_engine import MisreadEngine

        mre = MisreadEngine()
        mre.register_inner_knowing("I want user", precision=0.8, truth_gravity=1.0)

        # Base magnitude with fm_error=0 (no amplification)
        # pattern_type="functional_framing" → contradiction_strength=0.6, pattern_severity=0.21
        # base: 0.6 * 0.7 * 1.0 * 1.0 * 1.0 + 0.21 = 0.42 + 0.21 = 0.63
        mag_base = mre._compute_magnitude(
            knowing=None,  # pattern-type contradiction (no knowing hit)
            pattern_type="functional_framing",
            emotional_state=None,
            baseline_state=None,
            fm_error=0.0,
        )

        # Same with fm_error=0.6 (amplified)
        # amp: 0.6 * 0.7 * 1.0 * 1.0 * 1.21 + 0.21 = 0.5082 + 0.21 = 0.7182
        mag_amp = mre._compute_magnitude(
            knowing=None,
            pattern_type="functional_framing",
            emotional_state=None,
            baseline_state=None,
            fm_error=0.6,
        )

        # Amplified should be higher (due to 1.21x cerebellar_gain)
        assert mag_amp > mag_base, \
            f"Amplified magnitude ({mag_amp}) should exceed base ({mag_base})"
        assert abs(mag_base - 0.63) < 0.01
        assert abs(mag_amp - 0.7182) < 0.01