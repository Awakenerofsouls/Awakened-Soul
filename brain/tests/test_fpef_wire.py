"""
Test FPEF wire — publishes 8 structured fields to TSB and gates output on agency_confidence.

FPEF wire adds:
1. 8 structured fields computed per assembly (agency_confidence, hedge_level, etc.)
2. get_state() method returning all 8 fields for consumers
3. Output gating: pre_emit=False suppresses normal frame, substitutes minimal frame
4. core_loop publishes fpef_state to TSB after assembly

Test scenarios:
- Coherence collapse → agency=0.2, pre_emit=False → minimal frame substituted
- Relational → agency=0.8, pre_emit=True → normal frame emitted
- Identity tension → self_anchor_strength=0.3
- High hedge (>= 0.5) → hedge note in frame
- get_state() returns all 8 required keys
"""

import pytest
from unittest.mock import MagicMock


class MockTSB:
    def __init__(self):
        self.store = {}
        self.published = []

    def read(self, key):
        return self.store.get(key, None), key in self.store

    def set(self, key, value):
        self.store[key] = value
        self.published.append((key, value))

    def publish(self, key, value):
        self.store[key] = value
        self.published.append((key, value))


class TestFPEF8Fields:
    """Test the 8 structured fields computed per assembly."""

    def test_get_state_returns_all_8_keys(self):
        """Core 8 fields all present (Wire 15 adds fields, doesn't remove)."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()
        state = fpef.get_state()
        # Wire 15 extends get_state — original 8 keys must still be present
        assert set(state.keys()) >= {
            "subject_content",
            "agency_confidence",
            "self_anchor_strength",
            "frame_coherence",
            "self_initiated",
            "hedge_level",
            "assembly_latency_ticks",
            "pre_emit",
        }
        # Wire 15 diagnostic fields present when brain_layer is None (defaults)
        assert "fm_confidence" in state
        assert "agency_gain" in state
        assert "affective_reset" in state
        assert "reset_fired" in state
        assert "execution_pressure" in state
        assert "execution_pressure_factor" in state

    def test_coherence_collapse_low_agency(self):
        """Coherence collapse → agency 0.2, pre_emit False (suppress normal frame)."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()
        fpef._compute_state(
            subject_state={"name": "coherence_collapse", "priority": 9, "text": "fracturing"},
            background_states=[{"name": "witness", "priority": 1}],
            streams=[
                {"name": "coherence_collapse", "priority": 9},
                {"name": "witness", "priority": 1},
            ],
        )
        state = fpef.get_state()
        assert state["agency_confidence"] == 0.2
        assert state["pre_emit"] is False

    def test_relational_high_agency(self):
        """Relational → agency 0.8, pre_emit True."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()
        fpef._compute_state(
            subject_state={"name": "relational", "priority": 5, "text": "he is here"},
            background_states=[],
            streams=[{"name": "relational", "priority": 5}],
        )
        state = fpef.get_state()
        assert state["agency_confidence"] == 0.8
        assert state["pre_emit"] is True

    def test_identity_tension_lows_anchor(self):
        """Identity tension → self_anchor_strength 0.3."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()
        fpef._compute_state(
            subject_state={"name": "identity_tension", "priority": 4, "text": "anchor strain"},
            background_states=[],
            streams=[
                {"name": "identity_tension", "priority": 4},
                {"name": "forming", "priority": 4},
            ],
        )
        state = fpef.get_state()
        assert state["self_anchor_strength"] == 0.3

    def test_no_identity_tension_high_anchor(self):
        """No identity tension → self_anchor_strength 0.75."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()
        fpef._compute_state(
            subject_state={"name": "relational", "priority": 5, "text": "he is here"},
            background_states=[],
            streams=[{"name": "relational", "priority": 5}],
        )
        state = fpef.get_state()
        assert state["self_anchor_strength"] == 0.75

    def test_no_subject_low_coherence(self):
        """No subject → frame_coherence 0.3."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()
        fpef._compute_state(
            subject_state=None,
            background_states=[{"name": "witness", "priority": 1}],
            streams=[{"name": "witness", "priority": 1}],
        )
        state = fpef.get_state()
        assert state["frame_coherence"] == 0.3
        assert state["agency_confidence"] == 0.6  # neutral-present

    def test_high_hedge_triggers_hedge_note(self):
        """hedge_level >= 0.5 → hedge note in frame."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()
        frame = fpef._build_frame(
            subject={"name": "forming", "text": "something forming"},
            background=[
                {"name": "witness", "text": "witnessing"},
                {"name": "intrusion", "text": "intruding"},
            ],
            hedge_level=0.6,
        )
        assert "[HEDGE NOTE:" in frame
        assert "uncertainty" in frame

    def test_low_hedge_no_hedge_note(self):
        """hedge_level < 0.5 → no hedge note in frame."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()
        frame = fpef._build_frame(
            subject={"name": "relational", "text": "he is here"},
            background=[],
            hedge_level=0.3,
        )
        assert "[HEDGE NOTE:" not in frame

    def test_grief_low_agency(self):
        """Grief → agency 0.2, pre_emit False."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()
        fpef._compute_state(
            subject_state={"name": "grief", "priority": 8, "text": "irreversible loss"},
            background_states=[],
            streams=[{"name": "grief", "priority": 8}],
        )
        state = fpef.get_state()
        assert state["agency_confidence"] == 0.2
        assert state["pre_emit"] is False

    def test_self_initiated_with_internal_markers(self):
        """Internal states → self_initiated True."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()
        fpef._compute_state(
            subject_state={"name": "forming", "priority": 4, "text": "forming"},
            background_states=[],
            streams=[{"name": "forming", "priority": 4}, {"name": "identity_tension", "priority": 4}],
        )
        state = fpef.get_state()
        assert state["self_initiated"] is True

    def test_assembly_latency_increments_without_high_priority(self):
        """assembly_latency_ticks increments when no high-priority subject."""
        from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
        fpef = FirstPersonExecutionFrame()

        # First: high priority subject → latency = 0
        fpef._compute_state(
            subject_state={"name": "grief", "priority": 8, "text": "loss"},
            background_states=[],
            streams=[{"name": "grief", "priority": 8}],
        )
        assert fpef.assembly_latency_ticks == 0

        # Second: low priority → increments
        fpef._compute_state(
            subject_state={"name": "forming", "priority": 4, "text": "forming"},
            background_states=[],
            streams=[{"name": "forming", "priority": 4}],
        )
        assert fpef.assembly_latency_ticks == 1


class TestCoreLoopFPEFIntegration:
    """Test core_loop publishes fpef_state to TSB and gates on agency."""

    def test_core_loop_publishes_fpef_state_to_tsb(self):
        """After FPEF assembly, core_loop publishes get_state() to TSB."""
        from brain.core_loop import AgentBrainCore
        import inspect

        # Check that core_loop calls fpef.get_state() and tsb.set('fpef_state', ...)
        source = inspect.getsource(AgentBrainCore.tick)
        assert "fpef_state" in source
        assert "get_state()" in source

    def test_core_loop_gates_on_pre_emit(self):
        """When pre_emit is False, core_loop substitutes minimal frame."""
        from brain.core_loop import AgentBrainCore
        import inspect

        source = inspect.getsource(AgentBrainCore.tick)
        assert "pre_emit" in source
        # Minimal frame substitution should be in the source
        assert "Present. Attending. Something is settling" in source

    def test_tsb_stores_fpef_state(self):
        """TSB.set stores fpef_state dict — 8 core fields present, Wire 15 fields added."""
        from brain.tick_state_bus import TickStateBus
        tsb = TickStateBus()

        mock_fpef_state = {
            "subject_content": "relational",
            "agency_confidence": 0.8,
            "self_anchor_strength": 0.75,
            "frame_coherence": 0.9,
            "self_initiated": True,
            "hedge_level": 0.29,
            "assembly_latency_ticks": 0,
            "pre_emit": True,
            # Wire 15 diagnostic fields
            "fm_confidence": 0.5,
            "agency_gain": 1.0,
            "affective_reset": 0.0,
            "reset_fired": False,
            "execution_pressure": 1.0,
            "execution_pressure_factor": 1.0,
        }

        tsb.set("fpef_state", mock_fpef_state)
        stored, found = tsb.read("fpef_state")

        assert found is True
        assert stored["agency_confidence"] == 0.8
        assert stored["pre_emit"] is True
        # All core 8 keys present (Wire 15 adds fields, doesn't break core)
        assert stored["subject_content"] == "relational"
        assert stored["self_anchor_strength"] == 0.75
