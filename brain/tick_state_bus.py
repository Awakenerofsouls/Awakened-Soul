"""
Tick State Bus (TSB)
Core communication layer for all intra-tick state.
Components publish partial outputs and read each other mid-tick.
Includes staleness model: entries older than validity_window are flagged, not silently used.

Wire 4 adds: interrupt temporal state machine — pause-evaluate-resume cycle with habituation.
Real-brain equivalents: STN stop-signal + MMN→P3a→RON three-stage orienting + amygdala habituation.
"""

import time
from typing import Any, Dict, List, Optional, Tuple


class TickStateBus:
    def __init__(
        self,
        validity_window: float = 0.6,
        component_categories: Optional[Dict[str, List[str]]] = None,
        interrupt_history_decay_ticks: int = 5
    ):
        """
        validity_window: seconds before a published entry is considered stale.
        interrupt_history_decay_ticks: how many ticks an interrupt stays in habituation history
            before being removed. 5 ticks = ~10s at 2s/tick.
        """
        self._state: Dict[str, Dict[str, Any]] = {}
        self.validity_window = validity_window
        self.tick_start: float = time.time()
        self._tick_count: int = 0  # tracks ticks for interrupt history decay

        # Wire 3a: IOR tracking for inhibition-of-return
        self._ior_history: Dict[str, float] = {}  # component -> decay timer (ticks remaining)
        # Wire 3a: component-to-category mapping for direction matching
        self.component_categories = component_categories or {
            "inward": ["vif", "mre", "mre_fragment", "rce", "diqe", "diqe_fragment"],
            "outward": ["ss", "ss_fragment", "pds", "pds_fragment"],
            "neutral": ["fce", "fce_fragment", "fid", "fid_fragment", "baseline_state", "emotional_state"]
        }
        # Wire 3a: burst/tonic mode tracking
        self._mode: str = "tonic"  # "burst" or "tonic"

        # Wire 4: interrupt temporal state machine
        self._interrupt_active: bool = False
        self._tick_since_interrupt: int = 999  # 999 = no interrupt this session
        # List of (timestamp, tick_count) tuples for habituation
        self._interrupt_history: List[Tuple[float, int]] = []
        self._interrupt_history_decay_ticks: int = interrupt_history_decay_ticks
        # Snapshot of bus state captured at moment of interrupt — for RON recovery
        self._pre_interrupt_snapshot: Optional[Dict[str, Any]] = None
        # Wire 5: conversation-turn-based recovery counter
        # Tracks turns elapsed since recovery started (0 while active, 1..N during recovery)
        # Resets to 0 when recovery ends; increments per user-input turn in recovery window
        self._recovery_turn_count: int = 0

    def start_tick(self):
        """Call at the beginning of each tick. Resets tick clock, decays IOR, advances interrupt counter."""
        self.tick_start = time.time()
        self._tick_count += 1

        # Decay IOR history — entries not recently read recover priority
        for comp in list(self._ior_history.keys()):
            self._ior_history[comp] -= 0.5
            if self._ior_history[comp] <= 0:
                del self._ior_history[comp]

        # Wire 4: advance interrupt counter; clear active flag at tick end
        # (active flag gets set during publish(), cleared here at next tick start)
        if self._interrupt_active:
            # Interrupt was handled this tick — reset counter to 0 (at tick 1 of post-interrupt)
            self._tick_since_interrupt = 0
            self._interrupt_active = False
        else:
            # No interrupt this tick — count up if we've had one before
            if self._tick_since_interrupt < 999:
                self._tick_since_interrupt += 1

        # Decay interrupt history: remove entries older than decay_ticks
        self._interrupt_history = [
            entry for entry in self._interrupt_history
            if self._tick_count - entry[1] <= self._interrupt_history_decay_ticks
        ]

        # Reset mode to tonic; compute_burst_tonic() will set it on first prioritized read
        self._mode = "tonic"

    def _register_interrupt(self, snapshot: Dict[str, Any], tick: int):
        """
        Called when a component publishes with has_standing or priority:interrupt.
        Records the interrupt, captures pre-interrupt state for recovery, resets counter.
        """
        self._interrupt_active = True
        self._tick_since_interrupt = 0
        self._interrupt_history.append((time.time(), tick))
        self._pre_interrupt_snapshot = snapshot  # preserves what was being processed

    def publish(self, component: str, data: Dict[str, Any], priority_weight: Optional[float] = None):
        """
        Component publishes its partial output to the bus.
        Timestamp recorded so downstream readers know how fresh this is.
        priority_weight: optional 0.0-1.0. If not provided, inferred from data flags:
            has_standing: True → 0.9
            priority: "interrupt" → 1.0
            default → 0.5
        Wire 4: if has_standing or priority:interrupt, register interrupt in state machine.
        """
        if priority_weight is None:
            if data.get("has_standing"):
                priority_weight = 0.9
            elif data.get("priority") == "interrupt":
                priority_weight = 1.0
            else:
                priority_weight = 0.5

        self._state[component] = {
            "data": data,
            "timestamp": time.time(),
            "tick_age": time.time() - self.tick_start,
            "priority_weight": priority_weight
        }

        # Wire 4: register interrupt if this is an interrupt-class publication
        # AND we're not in the RON recovery window (don't let new interrupts
        # overwrite reorientation state — brain suppresses new salience during RON)
        if (data.get("has_standing") or data.get("priority") == "interrupt"):
            if not self.get_interrupt_state()["in_recovery"]:
                self._register_interrupt(self.snapshot(), self._tick_count)
            # else: suppress — we're reorienting, new interrupt queued but not processed

    def read(self, component: str) -> Tuple[Optional[Dict], bool]:
        """
        Read a component's published state.
        Returns (data, is_fresh) tuple.
        is_fresh=False means the data exists but is stale — caller decides whether to use it.
        Returns (None, False) if component hasn't published this tick.
        """
        if component not in self._state:
            return None, False

        entry = self._state[component]
        age = time.time() - entry["timestamp"]
        is_fresh = age <= self.validity_window

        return entry["data"], is_fresh

    def set(self, component: str, data: Dict[str, Any]) -> None:
        """
        Set a component's state directly (no priority weighting).
        Used for internal mechanism outputs that don't come from publish().
        E.g., core_loop sets fpef_state after FPEF assembly.
        """
        self._state[component] = {
            "data": data,
            "timestamp": time.time(),
            "priority": 0.5,  # neutral priority for set() values
        }

    def read_all_fresh(self) -> Dict[str, Dict]:
        """Return only fresh entries. Used for FPEF assembly."""
        result = {}
        for component, entry in self._state.items():
            age = time.time() - entry["timestamp"]
            if age <= self.validity_window:
                result[component] = entry["data"]
        return result

    def read_all(self) -> Dict[str, Dict]:
        """Return all entries with freshness metadata. Used by CRL and MR."""
        result = {}
        for component, entry in self._state.items():
            age = time.time() - entry["timestamp"]
            result[component] = {
                **entry["data"],
                "_fresh": age <= self.validity_window,
                "_age": age
            }
        return result

    def snapshot(self) -> Dict[str, Any]:
        """Full bus snapshot for PDFB and logging."""
        return {
            k: v["data"] for k, v in self._state.items()
        }

    def _compute_integrated_priority(self, component: str, entry: Dict) -> float:
        """
        Integrate bottom-up priority with top-down emotional salience and IOR penalty.
        Reads emotional_state from bus internally.
        Returns 0.0-1.0, higher = more priority.
        """
        base_weight = entry.get("priority_weight", 0.5)

        # Wire 4: suppress interrupt-class priority during recovery (RON window)
        # During recovery ticks (ticks_since in [1,2]), dampen interrupt priority
        interrupt_state = self.get_interrupt_state()
        if interrupt_state["in_recovery"] and interrupt_state["suppress_new_interrupts"]:
            if entry.get("has_standing") or entry.get("priority") == "interrupt":
                # Active dampening during RON: half the base weight
                base_weight = base_weight * 0.5

        # Top-down: emotional state's salience field contributes up to +0.2 bonus
        salience_bonus = 0.0
        em_state, _ = self.read("emotional_state")
        if em_state and isinstance(em_state, dict):
            salience = em_state.get("salience", 0.4)
            salience_bonus = salience * 0.2  # max +0.2

        # Direction match bonus: inward/outward matching scores +0.1
        direction_bonus = 0.0
        em_state, _ = self.read("emotional_state")
        if em_state and isinstance(em_state, dict):
            direction = em_state.get("direction", "neutral")
            if direction in self.component_categories:
                if component in self.component_categories[direction]:
                    direction_bonus = 0.1

        # IOR penalty: recently-read components get reduced priority
        ior_penalty = 0.0
        if component in self._ior_history:
            decay_ticks = self._ior_history[component]
            ior_penalty = min(0.3, decay_ticks * 0.1)  # max -0.3 for very recent reads

        integrated = base_weight + salience_bonus + direction_bonus - ior_penalty
        return max(0.0, min(1.0, integrated))

    def read_all_prioritized(self) -> List[Tuple[str, Dict, float]]:
        """
        Return entries sorted by integrated priority descending.
        Reads emotional_state from bus internally to compute top-down contribution.
        Applies Wire 4 recovery suppression to interrupt-class entries during RON.
        Updates IOR history — entries read this tick get penalized next tick.
        Also sets _mode to "burst" if max priority > 0.85, else "tonic".
        Returns list of (component_name, data, integrated_priority).
        """
        results = []
        max_priority = 0.0

        for component, entry in self._state.items():
            age = time.time() - entry["timestamp"]
            if age > self.validity_window:
                continue  # skip stale

            priority = self._compute_integrated_priority(component, entry)
            results.append((component, entry["data"], priority))
            if priority > max_priority:
                max_priority = priority

        # Sort by priority descending
        results.sort(key=lambda x: x[2], reverse=True)

        # Update IOR — entries read this tick get penalized next tick
        for component, _, _ in results:
            if component in self._ior_history:
                self._ior_history[component] = max(0.0, self._ior_history[component] - 1.0)
            else:
                self._ior_history[component] = 2.0  # fresh read starts at 2.0 penalty

        # Set burst/tonic mode
        self._mode = "burst" if max_priority > 0.85 else "tonic"

        return results

    def get_mode(self) -> str:
        """Return current mode: 'burst' (high-priority content demands immediate attention) or 'tonic' (sustained processing)."""
        return self._mode

    def get_interrupt_state(self) -> Dict[str, Any]:
        """
        Wire 4: Return the current interrupt state machine.
        MMN→P3a→RON model:
          - active=True + ticks_since=0: MMN just fired, interrupt being registered
          - active=False + ticks_since=1: P3a — interrupt is being evaluated/processed
          - in_recovery=True: RON — reorienting back to pre-interrupt task
        """
        recent_count = len(self._interrupt_history)
        # Habituation: 0.0 (no habituation) to 1.0 (fully habituated)
        # Builds as recent interrupts accumulate, decays with decay_ticks window
        habituation = min(1.0, recent_count / 5.0)  # 5+ interrupts in window → fully habituated
        # RON window: ticks 1-2 post-interrupt
        in_recovery = 1 <= self._tick_since_interrupt <= 2
        # Suppress new interrupts during RON (brain is reorienting, not ready for new interrupts)
        suppress_new_interrupts = in_recovery

        return {
            "active": self._interrupt_active,
            "ticks_since": self._tick_since_interrupt,
            "recent_count": recent_count,
            "habituation": habituation,
            "in_recovery": in_recovery,
            "suppress_new_interrupts": suppress_new_interrupts,
            "pre_interrupt_snapshot": self._pre_interrupt_snapshot,
            # Wire 5: turn-based recovery counter
            "recovery_turn_count": self._recovery_turn_count,
        }

    def set_recovery_turn_count(self, value: int):
        """Wire 5: set recovery_turn_count (resets on recovery end or tick start)."""
        self._recovery_turn_count = max(0, value)

    def increment_recovery_turn_count(self):
        """Wire 5: increment recovery_turn_count per user-input turn during recovery."""
        self._recovery_turn_count += 1

    def clear_recovery_turn_count(self):
        """Wire 5: reset recovery_turn_count when recovery window ends."""
        self._recovery_turn_count = 0

    def clear(self):
        """Called at tick end. Clears bus for next tick; preserves interrupt state machine."""
        self._state = {}
        # Wire 4: interrupt_active was already cleared in start_tick().
        # Preserve _tick_since_interrupt, _interrupt_history, _pre_interrupt_snapshot
        # Clear _pre_interrupt_snapshot once we've fully recovered (past RON window)
        if self._tick_since_interrupt > 2:
            self._pre_interrupt_snapshot = None