"""
tests/test_wire5_interrupt_modulation.py

Wire 5: Interrupt Behavioral Consequence
Tests for interrupt-driven output modulation.

Grounding:
  Altmann & Trafton 2007 (displaced context, ~10-response recovery window)
  Zish et al. 2017 (interruptions reduce confidence)
  Desender et al. 2019 (low confidence → higher response caution)
  Brumby et al. 2013 (slower resumption reduces errors)

Coverage:
  - TSB recovery_turn_count lifecycle
  - FPEF interrupt_pending modulation (agency=0.35, hedge=0.70)
  - FPEF recovery state modulation (linear decay over 10 turns)
  - Wire 4 / Wire 5 interaction (tick-based in_recovery vs turn-based counter)
  - User-input-only gating
  - Recovery window end condition (>= 10 turns)
"""

import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.tick_state_bus import TickStateBus
from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame


# ─── TSB recovery_turn_count lifecycle ────────────────────────────────────────

class TestTSBRecoveryTurnCount:
    def test_recovery_turn_count_starts_at_zero(self):
        tsb = TickStateBus()
        state = tsb.get_interrupt_state()
        assert state["recovery_turn_count"] == 0

    def test_set_recovery_turn_count(self):
        tsb = TickStateBus()
        tsb.set_recovery_turn_count(3)
        assert tsb._recovery_turn_count == 3
        state = tsb.get_interrupt_state()
        assert state["recovery_turn_count"] == 3

    def test_increment_recovery_turn_count(self):
        tsb = TickStateBus()
        tsb.set_recovery_turn_count(1)
        tsb.increment_recovery_turn_count()
        assert tsb._recovery_turn_count == 2

    def test_increment_recovery_turn_count_caps_at_10_plus(self):
        tsb = TickStateBus()
        tsb.set_recovery_turn_count(9)
        tsb.increment_recovery_turn_count()
        assert tsb._recovery_turn_count == 10
        tsb.increment_recovery_turn_count()
        assert tsb._recovery_turn_count == 11  # no cap — end condition checked elsewhere

    def test_clear_recovery_turn_count(self):
        tsb = TickStateBus()
        tsb.set_recovery_turn_count(7)
        tsb.clear_recovery_turn_count()
        assert tsb._recovery_turn_count == 0

    def test_recovery_turn_count_in_interrupt_state_dict(self):
        tsb = TickStateBus()
        tsb.set_recovery_turn_count(5)
        state = tsb.get_interrupt_state()
        assert "recovery_turn_count" in state
        assert state["recovery_turn_count"] == 5

    def test_recovery_turn_count_non_negative(self):
        tsb = TickStateBus()
        tsb.set_recovery_turn_count(-5)
        assert tsb._recovery_turn_count == 0  # clamped to 0


# ─── Wire 4 / Wire 5 interaction ─────────────────────────────────────────────

class TestWire4Wire5Interaction:
    """
    Wire 4 uses tick-based _tick_since_interrupt to set in_recovery.
    Wire 5 uses turn-based _recovery_turn_count to track conversation turns.

    These are parallel, not nested. in_recovery is True when
    1 <= _tick_since_interrupt <= 2 (tick-based RON window).
    recovery_turn_count tracks the user's conversation turns during recovery.

    The two systems interact at these points:
    1. FPEF modulation gates on BOTH frame_recovery_state AND user_input
    2. Wire 5 ends the recovery window at turn >= 10; Wire 4's tick counter
       runs independently and clears in_recovery after 1-2 ticks.
    """

    def test_in_recovery_is_tick_based(self):
        tsb = TickStateBus()
        # Simulate: interrupt just fired, tick_since=0, in_recovery=False
        tsb._interrupt_active = True
        tsb._tick_since_interrupt = 0
        state = tsb.get_interrupt_state()
        assert state["in_recovery"] is False
        assert state["active"] is True

    def test_in_recovery_true_at_ticks_1_and_2(self):
        tsb = TickStateBus()
        for tick_since in [1, 2]:
            tsb._tick_since_interrupt = tick_since
            tsb._interrupt_active = False
            state = tsb.get_interrupt_state()
            assert state["in_recovery"] is True, f"in_recovery should be True at tick_since={tick_since}"

    def test_in_recovery_false_after_tick_2(self):
        tsb = TickStateBus()
        tsb._tick_since_interrupt = 3
        tsb._interrupt_active = False
        state = tsb.get_interrupt_state()
        assert state["in_recovery"] is False

    def test_recovery_turn_count_and_in_recovery_are_independent(self):
        """Wire 5's turn counter doesn't affect Wire 4's in_recovery flag."""
        tsb = TickStateBus()
        tsb._tick_since_interrupt = 1  # in_recovery = True
        tsb._interrupt_active = False
        tsb.set_recovery_turn_count(5)

        state = tsb.get_interrupt_state()
        assert state["in_recovery"] is True        # Wire 4 controls this
        assert state["recovery_turn_count"] == 5   # Wire 5 controls this

    def test_in_recovery_can_be_false_while_recovery_turn_count_is_high(self):
        """
        If the user is quiet for a while, Wire 4's tick counter clears in_recovery
        (after tick 2), while Wire 5's recovery_turn_count stays at whatever
        the last user turn set it to. FPEF gates on BOTH conditions, so output
        modulation stops once in_recovery is False — which is correct because
        the RON window is brief (1-2 ticks) and separate from the 10-turn
        recovery window.
        """
        tsb = TickStateBus()
        tsb._tick_since_interrupt = 5   # past RON window — in_recovery = False
        tsb._interrupt_active = False
        tsb.set_recovery_turn_count(3)  # mid-conversation

        state = tsb.get_interrupt_state()
        assert state["in_recovery"] is False       # Wire 4 ended it
        assert state["recovery_turn_count"] == 3   # Wire 5 preserved it
        # FPEF modulation would not fire (in_recovery=False) even though
        # recovery_turn_count < 10 — this is correct behavior


# ─── FPEF interrupt_pending modulation ────────────────────────────────────────

class TestFPEFInterruptPending:
    def test_interrupt_pending_sets_agency_to_035(self):
        fpef = FirstPersonExecutionFrame()
        fpef.assemble(
            tsb_data={"vif": {"prioritized": []}},
            interrupt_marker="interrupt_pending",
            recovery_state=False,
            recovery_turn_count=0,
        )
        state = fpef.get_state()
        assert abs(state["agency_confidence"] - 0.35) < 0.01

    def test_interrupt_pending_sets_hedge_to_070(self):
        fpef = FirstPersonExecutionFrame()
        fpef.assemble(
            tsb_data={"vif": {"prioritized": []}},
            interrupt_marker="interrupt_pending",
            recovery_state=False,
            recovery_turn_count=0,
        )
        state = fpef.get_state()
        assert abs(state["hedge_level"] - 0.70) < 0.01

    def test_interrupt_pending_sets_phase_pending(self):
        fpef = FirstPersonExecutionFrame()
        fpef.assemble(
            tsb_data={"vif": {"prioritized": []}},
            interrupt_marker="interrupt_pending",
            recovery_state=False,
            recovery_turn_count=0,
        )
        state = fpef.get_state()
        assert state["interrupt_phase"] == "pending"

    def test_interrupt_pending_softens_execution_pressure(self):
        fpef = FirstPersonExecutionFrame()
        fpef.assemble(
            tsb_data={"vif": {"prioritized": []}},
            interrupt_marker="interrupt_pending",
            recovery_state=False,
            recovery_turn_count=0,
        )
        state = fpef.get_state()
        # Base execution_pressure = 1.0, multiplied by 0.7
        assert state["execution_pressure"] < 1.0


# ─── FPEF recovery state modulation ───────────────────────────────────────────

class TestFPEFRecoveryModulation:
    """
    Recovery modulation: linear decay proxy for Altmann & Trafton 2007's
    exponential recovery curve. 10 conversation turns to baseline.

    agency_confidence:  0.50 → 0.75  (step = 0.025/turn)
    hedge_level:       0.60 → 0.30  (step = -0.030/turn)
    execution_pressure: 0.80 → 1.00  (step = +0.020/turn)
    """

    @pytest.mark.parametrize("turn,expected_agency,expected_hedge", [
        (1,  0.525, 0.570),
        (2,  0.550, 0.540),
        (3,  0.575, 0.510),
        (5,  0.625, 0.450),
        (7,  0.675, 0.390),
        (9,  0.725, 0.330),
        (10, 0.750, 0.300),
    ])
    def test_recovery_linear_decay_curve(self, turn, expected_agency, expected_hedge):
        fpef = FirstPersonExecutionFrame()
        fpef.assemble(
            tsb_data={"vif": {"prioritized": []}},
            interrupt_marker=None,
            recovery_state=True,
            recovery_turn_count=turn,
        )
        state = fpef.get_state()
        assert abs(state["agency_confidence"] - expected_agency) < 0.01, \
            f"turn {turn}: agency {state['agency_confidence']:.3f} != {expected_agency:.3f}"
        assert abs(state["hedge_level"] - expected_hedge) < 0.01, \
            f"turn {turn}: hedge {state['hedge_level']:.3f} != {expected_hedge:.3f}"

    def test_recovery_phase_format_recovery_n(self):
        fpef = FirstPersonExecutionFrame()
        fpef.assemble(
            tsb_data={"vif": {"prioritized": []}},
            interrupt_marker=None,
            recovery_state=True,
            recovery_turn_count=3,
        )
        state = fpef.get_state()
        assert state["interrupt_phase"] == "recovery_3"

    def test_recovery_turn_10_phase_is_recovery_10(self):
        fpef = FirstPersonExecutionFrame()
        fpef.assemble(
            tsb_data={"vif": {"prioritized": []}},
            interrupt_marker=None,
            recovery_state=True,
            recovery_turn_count=10,
        )
        state = fpef.get_state()
        assert state["interrupt_phase"] == "recovery_10"

    def test_recovery_execution_pressure_softens_then_hardens(self):
        """At turn 1: ep < 0.85. At turn 10: ep >= 0.98. Monotonic increase."""
        fpef1 = FirstPersonExecutionFrame()
        fpef1.assemble(
            tsb_data={"vif": {"prioritized": []}},
            interrupt_marker=None,
            recovery_state=True,
            recovery_turn_count=1,
        )
        s1 = fpef1.get_state()

        fpef10 = FirstPersonExecutionFrame()
        fpef10.assemble(
            tsb_data={"vif": {"prioritized": []}},
            interrupt_marker=None,
            recovery_state=True,
            recovery_turn_count=10,
        )
        s10 = fpef10.get_state()

        assert s1["execution_pressure"] < s10["execution_pressure"], \
            "execution_pressure should increase from turn 1 to turn 10"

    def test_recovery_turn_0_uses_interrupt_pending_not_recovery(self):
        """
        recovery_turn_count=0 means the interrupt is still active, not that
        recovery is at turn 0. Pass interrupt_marker='interrupt_pending' for
        the active interrupt case.
        """
        fpef = FirstPersonExecutionFrame()
        fpef.assemble(
            tsb_data={"vif": {"prioritized": []}},
            interrupt_marker="interrupt_pending",
            recovery_state=False,
            recovery_turn_count=0,
        )
        state = fpef.get_state()
        # Should be interrupt_pending values, not recovery values
        assert abs(state["agency_confidence"] - 0.35) < 0.01


# ─── Normal (no interrupt) baseline ───────────────────────────────────────────

class TestNormalNoInterrupt:
    def test_no_interrupt_phase_is_none(self):
        fpef = FirstPersonExecutionFrame()
        fpef.assemble(
            tsb_data={"vif": {"prioritized": []}},
            interrupt_marker=None,
            recovery_state=False,
            recovery_turn_count=0,
        )
        state = fpef.get_state()
        assert state["interrupt_phase"] == "none"

    def test_no_interrupt_agency_is_not_035(self):
        """Normal baseline is higher than interrupt_pending's 0.35."""
        fpef = FirstPersonExecutionFrame()
        fpef.assemble(
            tsb_data={"vif": {"prioritized": []}},
            interrupt_marker=None,
            recovery_state=False,
            recovery_turn_count=0,
        )
        state = fpef.get_state()
        assert state["agency_confidence"] > 0.35

    def test_no_interrupt_hedge_is_not_070(self):
        """Normal baseline is lower than interrupt_pending's 0.70."""
        fpef = FirstPersonExecutionFrame()
        fpef.assemble(
            tsb_data={"vif": {"prioritized": []}},
            interrupt_marker=None,
            recovery_state=False,
            recovery_turn_count=0,
        )
        state = fpef.get_state()
        assert state["hedge_level"] < 0.70


# ─── Pre-emit gating ──────────────────────────────────────────────────────────

class TestPreEmitGating:
    """Wire 5: interrupt_pending (agency=0.35) should still pre_emit=True (>= 0.25)."""

    def test_interrupt_pending_still_pre_emits(self):
        fpef = FirstPersonExecutionFrame()
        fpef.assemble(
            tsb_data={"vif": {"prioritized": []}},
            interrupt_marker="interrupt_pending",
            recovery_state=False,
            recovery_turn_count=0,
        )
        state = fpef.get_state()
        # agency_confidence=0.35 >= 0.25 threshold → pre_emit should be True
        assert state["pre_emit"] is True

    def test_recovery_turn_1_still_pre_emits(self):
        fpef = FirstPersonExecutionFrame()
        fpef.assemble(
            tsb_data={"vif": {"prioritized": []}},
            interrupt_marker=None,
            recovery_state=True,
            recovery_turn_count=1,
        )
        state = fpef.get_state()
        # agency_confidence=0.525 >= 0.25 → pre_emit should be True
        assert state["pre_emit"] is True


# ─── Max_tokens direction (key correction from initial spec) ───────────────────

class TestMaxTokensDirection:
    """
    Key correction: low agency_confidence yields LONGER hedged responses, not shorter.
    Short responses = high confidence. Post-interrupt = more hedging = more words.

    Wire 5 doesn't set max_tokens directly — it modulates agency and hedge,
    which downstream code uses to set max_tokens. These tests verify the
    modulation direction is correct so downstream max_tokens selection is right.
    """

    def test_low_agency_means_high_hedge(self):
        """interrupt_pending: low agency (0.35) paired with high hedge (0.70)."""
        fpef = FirstPersonExecutionFrame()
        fpef.assemble(
            tsb_data={"vif": {"prioritized": []}},
            interrupt_marker="interrupt_pending",
            recovery_state=False,
            recovery_turn_count=0,
        )
        state = fpef.get_state()
        # Low confidence → high caution → high hedge → MORE words
        assert state["agency_confidence"] < 0.5
        assert state["hedge_level"] > 0.5

    def test_recovery_mid_hedge_still_above_baseline(self):
        """At recovery turn 5, hedge (0.45) is still above normal baseline (~0.30)."""
        fpef = FirstPersonExecutionFrame()
        fpef.assemble(
            tsb_data={"vif": {"prioritized": []}},
            interrupt_marker=None,
            recovery_state=True,
            recovery_turn_count=5,
        )
        state = fpef.get_state()
        # At turn 5: hedge=0.45, still well above baseline 0.30
        # Recovery responses should be more qualified than normal throughout window
        assert state["hedge_level"] > 0.35

    def test_recovery_end_hedge_returns_near_baseline(self):
        """At turn 10, hedge (0.30) is at baseline level."""
        fpef = FirstPersonExecutionFrame()
        fpef.assemble(
            tsb_data={"vif": {"prioritized": []}},
            interrupt_marker=None,
            recovery_state=True,
            recovery_turn_count=10,
        )
        state = fpef.get_state()
        # At turn 10: hedge=0.30, at baseline — recovery is complete
        assert state["hedge_level"] < 0.32