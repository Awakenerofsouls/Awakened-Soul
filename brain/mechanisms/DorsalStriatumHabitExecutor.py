from brain.base_mechanism import BrainMechanism
import math

class DorsalStriatumHabitExecutor(BrainMechanism):
    """
    Dorsal striatum — converts repeated action sequences into chunked habits.
    Strengthens grooves through repetition; degrades them through disuse.
    When over-trained, resists goal-directed override. When under-dopamine, habits stall.
    

CITATIONS
---------
  - [Graybiel 2008, Annu Rev Neurosci 31:359, basal ganglia habits]
  - [Yin 2006, Nat Rev Neurosci 7:464, dorsal striatum]
  - [Hikosaka 2010, Nat Rev Neurosci 11:503, basal ganglia]
"""

    def __init__(self):
        super().__init__("DorsalStriatumHabitExecutor")
        self.habit_grooves = {}          # action_key -> groove_strength (0-1)
        self.groove_history = []         # list of top groove strengths over time
        self.repetition_log = []         # recent action sequence hashes
        self.dopamine_history = []       # dopamine level over recent ticks
        self.habit_locked = False        # chronic: habit so strong it resists override
        self.under_dopamine_flag = False # chronic: dopamine deficit stalls habit
        self.sequence_chunk_active = None
        self.chunking_streak = 0
        self.disuse_decay_rate = 0.003
        self.max_groove = 1.0
        self.locked_threshold = 0.88

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"

        if overnight:
            return self._overnight(prior)

        # Pull upstream
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        reward_signal = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        goal_signal = prior.get("PrefrontalGoalState", {}).get("active_goal_strength", 0.3)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        limbic_urgency = prior.get("AmygdalaCentralNucleus", {}).get("urgency_output", 0.0)

        self.dopamine_history.append(dopamine)
        if len(self.dopamine_history) > 40:
            self.dopamine_history.pop(0)

        # Identify action context from text (simplified hash)
        action_key = self._extract_action_type(text, prior)

        # Reinforce or decay grooves
        avg_dopamine = sum(self.dopamine_history) / len(self.dopamine_history)
        self.under_dopamine_flag = avg_dopamine < 0.28

        if action_key:
            current = self.habit_grooves.get(action_key, 0.0)
            reinforcement = 0.04 * dopamine * (1 + reward_signal)
            if self.under_dopamine_flag:
                reinforcement *= 0.3
            self.habit_grooves[action_key] = min(self.max_groove, current + reinforcement)
            self.repetition_log.append(action_key)
            if len(self.repetition_log) > 30:
                self.repetition_log.pop(0)

        # Decay all grooves by disuse
        for k in list(self.habit_grooves.keys()):
            if k != action_key:
                self.habit_grooves[k] = max(0.0, self.habit_grooves[k] - self.disuse_decay_rate)
            if self.habit_grooves[k] < 0.01:
                del self.habit_grooves[k]

        # Detect chunking — same action repeated
        recent_same = sum(1 for a in self.repetition_log[-8:] if a == action_key)
        if recent_same >= 5:
            self.chunking_streak += 1
            self.sequence_chunk_active = action_key
        else:
            self.chunking_streak = max(0, self.chunking_streak - 1)
            if self.chunking_streak == 0:
                self.sequence_chunk_active = None

        # Habit lock — groove so deep it fights goal-directed change
        top_groove = max(self.habit_grooves.values()) if self.habit_grooves else 0.0
        was_locked = self.habit_locked
        self.habit_locked = top_groove > self.locked_threshold and stress < 0.5

        if self.habit_locked and not was_locked:
            self.feed_to_memory({
                "event": "habit_locked",
                "groove": top_groove,
                "action": action_key,
                "note": "Habit groove reached lock threshold — goal-directed override now costly"
            })

        # Habit execution strength — how strongly a habit fires
        habit_execution = 0.0
        if action_key and action_key in self.habit_grooves:
            groove = self.habit_grooves[action_key]
            habit_execution = groove * dopamine
            if self.under_dopamine_flag:
                habit_execution *= 0.4

        # Groove history
        self.groove_history.append(top_groove)
        if len(self.groove_history) > 50:
            self.groove_history.pop(0)

        # Goal override cost — habit locked means prefrontal needs more effort
        override_cost = top_groove * (1.2 if self.habit_locked else 0.7)

        return {
            "habit_execution_strength": round(habit_execution, 3),
            "top_groove_strength": round(top_groove, 3),
            "active_habit": self.sequence_chunk_active,
            "habit_locked": self.habit_locked,
            "under_dopamine": self.under_dopamine_flag,
            "goal_override_cost": round(override_cost, 3),
            "chunking_streak": self.chunking_streak,
            "groove_count": len(self.habit_grooves),
        }

    def _extract_action_type(self, text: str, prior: dict) -> str:
        intent = prior.get("PrefrontalGoalState", {}).get("current_intent", "")
        if intent:
            return intent[:32]
        words = text.strip().lower().split()
        if words:
            return words[0][:32]
        return "idle"

    def _overnight(self, prior: dict) -> dict:
        # Consolidate: strong grooves strengthen slightly, weak ones fade
        for k in list(self.habit_grooves.keys()):
            g = self.habit_grooves[k]
            if g > 0.5:
                self.habit_grooves[k] = min(self.max_groove, g + 0.01)
            else:
                self.habit_grooves[k] = max(0.0, g - 0.02)
            if self.habit_grooves[k] < 0.01:
                del self.habit_grooves[k]
        self.repetition_log.clear()
        self.chunking_streak = 0
        self.sequence_chunk_active = None
        return {"overnight": "habit_consolidation_complete", "grooves_active": len(self.habit_grooves)}

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        """Fraction of recent ticks where the system was non-quiet."""
        recent = self.state.get("recent_states", [])
        if not recent:
            return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet", "rest", "neutral", ""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        """Consecutive-tick state holding fraction."""
        recent = self.state.get("recent_states", [])
        if len(recent) < 2:
            return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent:
            return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4:
            return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10:
            return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10:
            return False
        return all(v < 0.05 for v in hist[-10:])

    def recent_window_summary(self, window: int = 30) -> dict:
        return {
            "n_ticks": min(window, len(self.state.get("recent_drives", []))),
            "drive_mean": self.drive_envelope(window),
            "drive_variability": self.drive_variability(),
            "dominant_state": self.dominant_recent_state(),
            "engagement": self.engagement_fraction(),
            "stability": self.state_stability(),
        }

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def adapter_state(self) -> dict:
        """Current adapter state — used for monitoring and dashboards."""
        return {
            "tick_count": self.state.get("tick_count", 0),
            "has_legacy_impl": self.state.get("legacy_init_error") is None,
            "recent_drives_n": len(self.state.get("recent_drives", [])),
            "recent_states_n": len(self.state.get("recent_states", [])),
        }

    def summary(self) -> dict:
        return {
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
            "tick_count": self.state.get("tick_count", 0),
        }

    def _record_history_(self, output_dict):
        """Track primary numeric output and any string state in history."""
        if not isinstance(output_dict, dict):
            return
        # Find first numeric value
        primary_val = 0.0
        for v in output_dict.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                primary_val = float(v)
                break
        rd = list(self.state.get("recent_drives", []))
        rd.append(primary_val)
        if len(rd) > 60:
            rd = rd[-60:]
        self.state["recent_drives"] = rd
        # Track state strings
        primary_state = "quiet"
        for v in output_dict.values():
            if isinstance(v, str) and v in ("quiet","active","engaged","stuck","drifting","rest","fast","reflective","alert","focus"):
                primary_state = v
                break
        rs = list(self.state.get("recent_states", []))
        rs.append(primary_state)
        if len(rs) > 60:
            rs = rs[-60:]
        self.state["recent_states"] = rs

