"""
Test Wire 15: FPEF reads brain_forward_model_confidence (Integration025) +
 brain_affective_reset (Integration022).

Part A — forward model confidence → agency_confidence modulation:
Cerebellar confidence scales agency linearly by agency_gain [0.7, 1.3].
fm_confidence=0.5 → agency_gain=1.0 (neutral)
fm_confidence=1.0 → agency_gain=1.3 (max amplification)
fm_confidence=0.0 → agency_gain=0.7 (max dampening)

Part B — affective reset → execution_pressure modulation:
MCC-sgACC bridge fires above 0.3 threshold (strict >) → execution_pressure
softens by up to 50% (frame becomes plastic for replanning).

Integration: both channels can fire independently; Wire 13 MRE and Wire 15
FPEF consume different sides of Integration025's output without collision.
"""

import pytest
from unittest.mock import MagicMock


class MockTSB:
    """Minimal TSB mock for FPEF tests."""
    def __init__(self):
        self.store = {}
        self.published = []

    def read(self, key):
        return self.store.get(key, None), key in self.store

    def set(self, key, value):
        self.store[key] = value

    def publish(self, key, value):
        self.store[key] = value
        self.published.append((key, value))


class TestWire15PartA_FMConfidence:
    """Part A: brain_forward_model_confidence → agency_confidence modulation."""

    def test_neutral_baseline_fm_confidence_05(self):
        """fm_confidence=0.5 → agency_gain=1.0 (neutral, agency unchanged)."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()
        brain_layer = {"brain_forward_model_confidence": 0.5}

        fpef.assemble(
            tsb_data={},
            vif_alignments=None,
            active_intrusions=[],
            relational_field=None,
            witness_reflection=None,
            pre_decisional_state=None,
            additional_context=None,
            brain_layer=brain_layer,
        )
        state = fpef.get_state()
        assert state["fm_confidence"] == 0.5
        assert state["agency_gain"] == 1.0
        # agency_gain=1.0 → agency_confidence unchanged from base

    def test_high_fm_confidence_amplifies_agency(self):
        """fm_confidence=0.9 → agency_gain=1.24, agency_confidence amplified."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()
        brain_layer = {"brain_forward_model_confidence": 0.9}

        fpef.assemble(
            tsb_data={},
            vif_alignments=None,
            active_intrusions=[],
            relational_field=None,
            witness_reflection=None,
            pre_decisional_state=None,
            additional_context=None,
            brain_layer=brain_layer,
        )
        state = fpef.get_state()
        expected_gain = 0.7 + (0.9 * 0.6)  # 1.24
        assert abs(state["agency_gain"] - expected_gain) < 0.001

    def test_low_fm_confidence_dampens_agency(self):
        """fm_confidence=0.1 → agency_gain=0.76, agency_confidence dampened."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()
        brain_layer = {"brain_forward_model_confidence": 0.1}

        fpef.assemble(
            tsb_data={},
            vif_alignments=None,
            active_intrusions=[],
            relational_field=None,
            witness_reflection=None,
            pre_decisional_state=None,
            additional_context=None,
            brain_layer=brain_layer,
        )
        state = fpef.get_state()
        expected_gain = 0.7 + (0.1 * 0.6)  # 0.76
        assert abs(state["agency_gain"] - expected_gain) < 0.001

    def test_max_fm_confidence(self):
        """fm_confidence=1.0 → agency_gain=1.3 (max)."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()
        brain_layer = {"brain_forward_model_confidence": 1.0}

        fpef.assemble(
            tsb_data={},
            vif_alignments=None,
            active_intrusions=[],
            relational_field=None,
            witness_reflection=None,
            pre_decisional_state=None,
            additional_context=None,
            brain_layer=brain_layer,
        )
        state = fpef.get_state()
        assert state["agency_gain"] == 1.3

    def test_min_fm_confidence(self):
        """fm_confidence=0.0 → agency_gain=0.7 (min)."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()
        brain_layer = {"brain_forward_model_confidence": 0.0}

        fpef.assemble(
            tsb_data={},
            vif_alignments=None,
            active_intrusions=[],
            relational_field=None,
            witness_reflection=None,
            pre_decisional_state=None,
            additional_context=None,
            brain_layer=brain_layer,
        )
        state = fpef.get_state()
        assert state["agency_gain"] == 0.7


class TestWire15PartB_AffectiveReset:
    """Part B: brain_affective_reset → execution_pressure softening."""

    def test_no_reset_fired_default(self):
        """affective_reset=0.0 → reset_fired=False, execution_pressure=1.0."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()
        brain_layer = {"brain_affective_reset": 0.0}

        fpef.assemble(
            tsb_data={},
            vif_alignments=None,
            active_intrusions=[],
            relational_field=None,
            witness_reflection=None,
            pre_decisional_state=None,
            additional_context=None,
            brain_layer=brain_layer,
        )
        state = fpef.get_state()
        assert state["reset_fired"] is False
        assert state["execution_pressure"] == 1.0

    def test_subthreshold_no_reset(self):
        """affective_reset=0.2 (below 0.3) → reset_fired=False, unchanged."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()
        brain_layer = {"brain_affective_reset": 0.2}

        fpef.assemble(
            tsb_data={},
            vif_alignments=None,
            active_intrusions=[],
            relational_field=None,
            witness_reflection=None,
            pre_decisional_state=None,
            additional_context=None,
            brain_layer=brain_layer,
        )
        state = fpef.get_state()
        assert state["reset_fired"] is False
        assert state["execution_pressure"] == 1.0

    def test_at_threshold_strict_boundary(self):
        """affective_reset=0.3 (exactly at threshold) → reset_fired=False (strict >)."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()
        brain_layer = {"brain_affective_reset": 0.3}

        fpef.assemble(
            tsb_data={},
            vif_alignments=None,
            active_intrusions=[],
            relational_field=None,
            witness_reflection=None,
            pre_decisional_state=None,
            additional_context=None,
            brain_layer=brain_layer,
        )
        state = fpef.get_state()
        assert state["reset_fired"] is False  # strict > 0.3

    def test_above_threshold_softens_pressure(self):
        """affective_reset=0.5 → reset_fired=True, pressure_factor ≈ 0.857."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()
        brain_layer = {"brain_affective_reset": 0.5}

        fpef.assemble(
            tsb_data={},
            vif_alignments=None,
            active_intrusions=[],
            relational_field=None,
            witness_reflection=None,
            pre_decisional_state=None,
            additional_context=None,
            brain_layer=brain_layer,
        )
        state = fpef.get_state()
        assert state["reset_fired"] is True
        # reset_magnitude = (0.5 - 0.3) / 0.7 = 0.2857
        # pressure = 1.0 - (0.5 * 0.2857) = 0.8571
        expected_pressure = 1.0 - (0.5 * (0.5 - 0.3) / 0.7)
        assert abs(state["execution_pressure"] - expected_pressure) < 0.001
        assert abs(state["execution_pressure_factor"] - expected_pressure) < 0.001

    def test_max_reset(self):
        """affective_reset=1.0 → reset_fired=True, execution_pressure=0.5 (max softening)."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()
        brain_layer = {"brain_affective_reset": 1.0}

        fpef.assemble(
            tsb_data={},
            vif_alignments=None,
            active_intrusions=[],
            relational_field=None,
            witness_reflection=None,
            pre_decisional_state=None,
            additional_context=None,
            brain_layer=brain_layer,
        )
        state = fpef.get_state()
        assert state["reset_fired"] is True
        assert state["execution_pressure"] == 0.5


class TestWire15Integration:
    """Both channels active simultaneously."""

    def test_both_channels_high(self):
        """fm_conf=0.9 + reset=0.8 → agency amplified AND pressure softened."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()
        brain_layer = {
            "brain_forward_model_confidence": 0.9,
            "brain_affective_reset": 0.8,
        }

        fpef.assemble(
            tsb_data={},
            vif_alignments=None,
            active_intrusions=[],
            relational_field=None,
            witness_reflection=None,
            pre_decisional_state=None,
            additional_context=None,
            brain_layer=brain_layer,
        )
        state = fpef.get_state()
        # Part A: agency_gain = 0.7 + 0.9*0.6 = 1.24
        assert abs(state["agency_gain"] - 1.24) < 0.001
        # Part B: reset_magnitude = (0.8-0.3)/0.7 ≈ 0.714, pressure = 1.0 - 0.5*0.714 = 0.643
        expected_pressure = 1.0 - (0.5 * (0.8 - 0.3) / 0.7)
        assert abs(state["execution_pressure"] - expected_pressure) < 0.001
        assert state["reset_fired"] is True
        assert state["fm_confidence"] == 0.9

    def test_brain_layer_missing_no_crash(self):
        """brain_layer missing/stale → all defaults, no crash."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()

        fpef.assemble(
            tsb_data={},
            vif_alignments=None,
            active_intrusions=[],
            relational_field=None,
            witness_reflection=None,
            pre_decisional_state=None,
            additional_context=None,
            brain_layer=None,
        )
        state = fpef.get_state()
        assert state["fm_confidence"] == 0.5
        assert state["agency_gain"] == 1.0
        assert state["affective_reset"] == 0.0
        assert state["reset_fired"] is False
        assert state["execution_pressure"] == 1.0

    def test_brain_layer_empty_dict(self):
        """brain_layer={} → defaults apply, no crash."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()

        fpef.assemble(
            tsb_data={},
            vif_alignments=None,
            active_intrusions=[],
            relational_field=None,
            witness_reflection=None,
            pre_decisional_state=None,
            additional_context=None,
            brain_layer={},
        )
        state = fpef.get_state()
        assert state["fm_confidence"] == 0.5
        assert state["affective_reset"] == 0.0

    def test_clamped_values(self):
        """Out-of-range inputs clamped to [0.0, 1.0]."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()
        brain_layer = {
            "brain_forward_model_confidence": 1.5,   # over max → clamp to 1.0
            "brain_affective_reset": -0.5,            # under min → clamp to 0.0
        }

        fpef.assemble(
            tsb_data={},
            vif_alignments=None,
            active_intrusions=[],
            relational_field=None,
            witness_reflection=None,
            pre_decisional_state=None,
            additional_context=None,
            brain_layer=brain_layer,
        )
        state = fpef.get_state()
        assert state["fm_confidence"] == 1.0
        assert state["affective_reset"] == 0.0
        # agency_gain for clamped fm_confidence=1.0 should be 1.3
        assert state["agency_gain"] == 1.3


class TestWire15PayloadShape:
    """Wire 15 diagnostic fields present in fpef_state payload."""

    def test_all_wire15_diagnostic_fields_present(self):
        """fpef_state payload includes all Wire 15 diagnostic fields."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()
        brain_layer = {
            "brain_forward_model_confidence": 0.75,
            "brain_affective_reset": 0.55,
        }

        fpef.assemble(
            tsb_data={},
            vif_alignments=None,
            active_intrusions=[],
            relational_field=None,
            witness_reflection=None,
            pre_decisional_state=None,
            additional_context=None,
            brain_layer=brain_layer,
        )
        state = fpef.get_state()

        required_keys = [
            "fm_confidence",
            "agency_gain",
            "affective_reset",
            "reset_fired",
            "execution_pressure",
            "execution_pressure_factor",
        ]
        for key in required_keys:
            assert key in state, f"Missing Wire 15 field: {key}"

    def test_existing_fields_preserved(self):
        """Existing core 8 fields all present with correct types."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()

        fpef.assemble(
            tsb_data={},
            vif_alignments=None,
            active_intrusions=[],
            relational_field=None,
            witness_reflection=None,
            pre_decisional_state=None,
            additional_context=None,
            brain_layer=None,
        )
        state = fpef.get_state()

        required_keys = [
            "subject_content",
            "agency_confidence",
            "self_anchor_strength",
            "frame_coherence",
            "self_initiated",
            "hedge_level",
            "assembly_latency_ticks",
            "pre_emit",
        ]
        for key in required_keys:
            assert key in state, f"Missing existing field: {key}"

        assert isinstance(state["subject_content"], (type(None), str))
        assert isinstance(state["agency_confidence"], float)
        assert isinstance(state["self_anchor_strength"], float)
        assert isinstance(state["frame_coherence"], float)
        assert isinstance(state["self_initiated"], bool)
        assert isinstance(state["hedge_level"], float)
        assert isinstance(state["assembly_latency_ticks"], int)
        assert isinstance(state["pre_emit"], bool)

    def test_assembly_log_includes_wire15_fields(self):
        """assembly_log entry includes Wire 15 diagnostic fields."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()
        brain_layer = {
            "brain_forward_model_confidence": 0.8,
            "brain_affective_reset": 0.6,
        }

        fpef.assemble(
            tsb_data={},
            vif_alignments=None,
            active_intrusions=[],
            relational_field=None,
            witness_reflection=None,
            pre_decisional_state=None,
            additional_context=None,
            brain_layer=brain_layer,
        )
        assert len(fpef.assembly_log) == 1
        log = fpef.assembly_log[0]
        assert "fm_confidence" in log
        assert "agency_gain" in log
        assert "affective_reset" in log
        assert "reset_fired" in log
        assert "execution_pressure" in log


class TestWire13_15_Coexistence:
    """Wire 13 MRE and Wire 15 FPEF consume different sides of Integration025."""

    def test_both_sides_of_integration025_independent(self):
        """MRE (Wire 13) reads fm_error; FPEF (Wire 15) reads fm_confidence.
        Both published by Integration025 simultaneously — no collision.
        Simulate both high to confirm independence.
        """
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame

        fpef = FirstPersonExecutionFrame()
        # Wire 15 reads confidence side
        brain_layer = {
            "brain_forward_model_confidence": 0.95,  # Wire 15 Part A
            "brain_affective_reset": 0.0,            # Wire 15 Part B
        }

        fpef.assemble(
            tsb_data={},
            vif_alignments=None,
            active_intrusions=[],
            relational_field=None,
            witness_reflection=None,
            pre_decisional_state=None,
            additional_context=None,
            brain_layer=brain_layer,
        )
        state = fpef.get_state()

        # FPEF gets confidence side
        assert state["fm_confidence"] == 0.95
        assert state["agency_gain"] == 0.7 + (0.95 * 0.6)  # ≈ 1.27

        # MRE would independently read brain_forward_model_error (different key)
        # from the same brain_layer dict — no shared state mutation.
        # We verify the fields are different and non-conflicting.
        assert "brain_forward_model_error" not in state  # MRE field, not FPEF
        assert state["reset_fired"] is False  # Part B at 0.0
