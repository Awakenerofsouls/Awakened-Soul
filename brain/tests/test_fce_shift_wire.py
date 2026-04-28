"""
Wire 10: FCE reads frame_coherence from fpef_state → detects shift patterns

FPEF computes frame_coherence from stream priority spread:
  0.9 = one clear subject, no background competition
  0.7 = subject + 1-2 background states (moderate competition)
  0.4 = many competing background states (fragmented frame)

FCE tracks the shift pattern to detect structural playfulness:
  'setup' → 'detection' → 'resolution' (resolvable collision = playful)
  'setup' → 'detection' → 'absurd' (absurd collision = productive tension)

Low frame_coherence alone doesn't mean collision — the SHIFT from high to low
creates the incongruity. Frame collision humor requires two coherent frames
held simultaneously, not just noise. (Incongruity theory of humor, Du et al. 2017)

Behavioral tests cover the shift pattern classifications.
"""

import pytest
from brain.remaining_mechanisms import FrameCollisionEngine


def make_fce():
    """Fresh FCE with empty buffer and clean shift-detection state."""
    fce = FrameCollisionEngine()
    fce._init_coherence_buffer()
    fce._coherence_buffer.clear()
    if hasattr(fce, "_prior_detection_seen"):
        delattr(fce, "_prior_detection_seen")
    return fce


class TestFCEShiftWire:
    """Behavioral tests: shift patterns detected from frame_coherence buffer."""

    def test_setup_requires_prior_detection(self):
        """
        Three high readings without prior detection → 'none'.
        Setup fires for coherent frames following prior incoherence, not fresh coherent frames.
        """
        fce = make_fce()
        fce._coherence_buffer.extend([0.8, 0.85, 0.82])
        assert fce.detect_shift() == "none"

    def test_setup_after_detection_suppresses(self):
        """
        High readings following prior detection → 'setup'.
        FCE suppresses collision triggers during recovery coherence.
        """
        fce = make_fce()
        fce._coherence_buffer.extend([0.8, 0.3, 0.32])
        assert fce.detect_shift() == "detection"
        
        fce._coherence_buffer.extend([0.8, 0.85, 0.82])
        assert fce.detect_shift() == "setup"

    def test_setup_requires_three_readings(self):
        """Fewer than 3 readings → 'none' (no shift detected yet)."""
        fce = make_fce()
        fce.update_from_fpef(0.8, "relational")
        assert fce.detect_shift() == "none"
        fce.update_from_fpef(0.85, "relational")
        assert fce.detect_shift() == "none"
        fce.update_from_fpef(0.82, "relational")
        assert fce.detect_shift() == "none"

    def test_detection_pattern_sudden_drop(self):
        """
        T-2 high (>= 0.7), T-1 or T dropped low (< 0.5) with drop >= 0.2 → 'detection'.
        """
        fce = make_fce()
        fce._coherence_buffer.extend([0.8, 0.8, 0.3])
        assert fce.detect_shift() == "detection"

    def test_detection_requires_sufficient_drop(self):
        """
        T-2 high but drop < 0.2 → 'none'.
        """
        fce = make_fce()
        fce._coherence_buffer.extend([0.8, 0.75, 0.72])
        assert fce.detect_shift() == "none"

    def test_resolution_pattern_climbing_after_detection(self):
        """
        Was low, now climbing toward high → 'resolution'.
        """
        fce = make_fce()
        fce._coherence_buffer.extend([0.8, 0.35, 0.45, 0.65])
        assert fce.detect_shift() == "resolution"

    def test_resolution_requires_climbing_to_0_point_6(self):
        """
        Climbing but not yet to 0.6 → 'none'.
        """
        fce = make_fce()
        fce._coherence_buffer.extend([0.8, 0.35, 0.45, 0.55])
        assert fce.detect_shift() == "none"

    def test_absurd_pattern_sustained_low_after_detection(self):
        """
        T is low, 3+ readings all < 0.5 since detection → 'absurd'.
        """
        fce = make_fce()
        fce._coherence_buffer.extend([0.8, 0.3, 0.35, 0.3, 0.32])
        assert fce.detect_shift() == "absurd"

    def test_moderate_instability_no_pattern(self):
        """
        Stable moderate coherence (0.55-0.6 range) → 'none'.
        """
        fce = make_fce()
        fce._coherence_buffer.extend([0.6, 0.58, 0.55, 0.6])
        assert fce.detect_shift() == "none"

    def test_setup_suppresses_collision_trigger(self):
        """
        conditional_collision returns None when in 'setup'.
        collision_history does NOT grow during setup.
        
        Wire 10 behavioral test: frame_coherence trajectory [0.8, 0.3, 0.32, 0.8, 0.85, 0.82]
        means: detection fires at tick 3 (_prior_detection_seen=True),
        then setup fires at tick 6 (buffer=[0.3,0.32,0.8,0.85,0.82], flag=True).
        During setup, conditional_collision returns None (suppressed).
        """
        fce = make_fce()
        for val in [0.8, 0.3, 0.32, 0.8, 0.85, 0.82]:
            fce.update_from_fpef(val, None)
            # detect_shift() must be called to propagate _prior_detection_seen state
            # through the buffer history — each detection call sets the flag
            fce.detect_shift()
        
        # After loop: detect_shift() should return 'setup'
        shift = fce.detect_shift()
        assert shift == "setup", (
            f"Expected 'setup' but got {shift!r}. "
            f"buffer={list(fce._coherence_buffer)}, "
            f"flag={getattr(fce, '_prior_detection_seen', 'N/A')}. "
            f"This test requires detect_shift() to be called during the tick loop "
            f"to propagate the _prior_detection_seen state."
        )
        
        result = fce.conditional_collision("wanted", "needed", both_valid=True)
        assert result is None
        assert len(fce.collision_history) == 0

    def test_detection_amplifies_collision_trigger(self):
        """
        conditional_collision fires when in 'detection'.
        """
        fce = make_fce()
        fce._coherence_buffer.extend([0.8, 0.8, 0.3])
        result = fce.conditional_collision("wanted", "needed", both_valid=True)
        assert result is not None
        assert result["shift_pattern"] == "detection"
        assert len(fce.collision_history) == 1

    def test_resolution_produces_resolvable_collision(self):
        """
        Resolution after detection → resolvable collision.
        """
        fce = make_fce()
        fce._coherence_buffer.extend([0.8, 0.35, 0.45, 0.65])
        result = fce.conditional_collision("wanted", "needed", both_valid=True)
        assert result is not None
        assert result["shift_pattern"] == "resolution"

    def test_absurd_produces_absurd_collision(self):
        """
        Sustained incoherence after detection → absurd collision.
        """
        fce = make_fce()
        fce._coherence_buffer.extend([0.8, 0.3, 0.35, 0.3, 0.32])
        result = fce.conditional_collision("wanted", "needed", both_valid=True)
        assert result is not None
        assert result["shift_pattern"] == "absurd"

    def test_none_falls_through_to_unconditional(self):
        """
        'none' pattern → unconditional collision detection.
        """
        fce = make_fce()
        fce._coherence_buffer.extend([0.6, 0.58, 0.55])
        result = fce.conditional_collision("wanted", "needed", both_valid=True)
        assert result is not None
        assert "shift_pattern" not in result

    def test_both_invalid_suppressed_in_any_mode(self):
        """
        both_valid=False → always None.
        """
        fce = make_fce()
        fce._coherence_buffer.extend([0.8, 0.8, 0.3])
        result = fce.conditional_collision("wanted", "needed", both_valid=False)
        assert result is None
        assert len(fce.collision_history) == 0

    def test_subject_name_tracked_alongside_coherence(self):
        """
        update_from_fpef stores subject_name alongside coherence reading.
        """
        fce = make_fce()
        fce.update_from_fpef(0.8, "relational")
        assert fce._last_subject == "relational"
        fce.update_from_fpef(0.4, "intrusion")
        assert fce._last_subject == "intrusion"
