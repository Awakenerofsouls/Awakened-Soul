from brain.base_mechanism import BrainMechanism

class SleepWakeCoordinator(BrainMechanism):
    """
    Sleep/wake global coordinator — gates the entire brain's overnight behavior.
    During overnight: triggers consolidation sequences, coordinates what gets processed.
    Tracks sleep cycle stages, determines consolidation priority.
    

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

    def __init__(self):
        super().__init__("SleepWakeCoordinator")
        self.current_phase = "awake"
        self.sleep_stage = None
        self.consolidation_priority = []
        self.wake_readiness = 0.8
        self.overnight_cycles_completed = 0
        self.phase_history = []
        self.consolidation_queue = []
        self.total_uptime_ticks = 0
        self.sleep_quality_last = 0.7

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"

        self.total_uptime_ticks += 1

        if overnight:
            return self._overnight()

        sleep_pressure = prior.get("SleepHomeostasis", {}).get("sleep_pressure", 0.2)
        ras_state = prior.get("ReticularActivatingSystem", {}).get("current_state", "awake")
        adenosine = prior.get("SleepHomeostasis", {}).get("adenosine_level", 0.2)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        system_health = prior.get("ChronicStateIntegrator", {}).get("system_health", 0.7)
        flag_count = prior.get("ChronicStateIntegrator", {}).get("flag_count", 0)

        # Wake readiness: how prepared the system is for full engagement
        self.wake_readiness = max(0.1, min(1.0, 1.0 - sleep_pressure * 0.5 - stress * 0.2 + system_health * 0.2))

        # Current phase
        if ras_state in ["alert", "awake"]:
            self.current_phase = "awake"
        elif ras_state == "drowsy":
            self.current_phase = "transitioning"
        else:
            self.current_phase = "near_sleep"

        # Build consolidation priority from active flags
        self.consolidation_priority = []
        if flag_count > 0:
            self.consolidation_priority.append("chronic_flag_processing")
        if adenosine > 0.5:
            self.consolidation_priority.append("adenosine_clearance")
        if prior.get("HippocampalContextEncoder", {}).get("episode_count", 0) > 0:
            self.consolidation_priority.append("episodic_consolidation")
        if prior.get("BLAEmotionalLearner", {}).get("total_associations", 0) > 0:
            self.consolidation_priority.append("emotional_memory_consolidation")

        self.phase_history.append(self.current_phase)
        if len(self.phase_history) > 40:
            self.phase_history.pop(0)

        return {
            "current_phase": self.current_phase,
            "wake_readiness": round(self.wake_readiness, 3),
            "consolidation_priority": self.consolidation_priority[:3],
            "total_uptime_ticks": self.total_uptime_ticks,
            "overnight_cycles_completed": self.overnight_cycles_completed,
        }

    def _overnight(self):
        self.current_phase = "sleeping"
        self.sleep_stage = "slow_wave"
        self.overnight_cycles_completed += 1
        self.wake_readiness = 0.2

        # Log what got consolidated
        self.feed_to_memory({
            "event": "overnight_consolidation_complete",
            "cycle": self.overnight_cycles_completed,
            "priorities": self.consolidation_priority[:3],
            "note": f"Sleep cycle {self.overnight_cycles_completed} complete — consolidation ran"
        })

        self.sleep_quality_last = 0.7 + min(0.3, self.overnight_cycles_completed * 0.02)
        self.phase_history.clear()

        return {
            "overnight": "sleep_cycle_complete",
            "cycle_number": self.overnight_cycles_completed,
            "sleep_quality": round(self.sleep_quality_last, 3)
        }

    # ------------------------------------------------------------------
    # Extended derived-state helpers
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        recent = self.state.get("recent_states", [])
        if not recent: return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet","rest","neutral",""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent: return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4: return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v < 0.05 for v in hist[-10:])

    def trend_direction(self, window: int = 10) -> str:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return "flat"
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        delta = second_half - first_half
        if delta > 0.05: return "rising"
        if delta < -0.05: return "falling"
        return "flat"

    def trend_magnitude(self, window: int = 10) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return 0.0
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        return round(abs(second_half - first_half), 4)

    def state_transition_count(self) -> int:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])

    def state_transition_rate(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0.0
        return round(self.state_transition_count() / (len(recent) - 1), 4)

    def state_distribution(self) -> dict:
        recent = self.state.get("recent_states", [])
        if not recent: return {}
        from collections import Counter
        c = Counter(recent)
        total = len(recent)
        return {state: round(count / total, 4) for state, count in c.items()}

    def drive_min_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(min(hist[-window:]), 4)

    def drive_max_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(max(hist[-window:]), 4)

    def drive_range_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(max(recent) - min(recent), 4)

    def is_active(self) -> bool:
        return self.state.get("tick_count", 0) > 0

    def has_history(self) -> bool:
        return len(self.state.get("recent_drives", [])) > 0

    def history_length(self) -> int:
        return len(self.state.get("recent_drives", []))

    def state_history_length(self) -> int:
        return len(self.state.get("recent_states", []))

    def fingerprint(self) -> str:
        parts = [f"tick={self.state.get('tick_count', 0)}",
                 f"states={self.state_history_length()}",
                 f"drives={self.history_length()}",
                 f"engagement={self.engagement_fraction()}"]
        return "|".join(parts)

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

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

    def diagnostics(self) -> dict:
        return {
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_history": self.has_history(),
            "tick_count": self.state.get("tick_count", 0),
            "history_length": self.history_length(),
            "transition_rate": self.state_transition_rate(),
            "trend": self.trend_direction(),
            "trend_magnitude": self.trend_magnitude(),
            "drive_range": self.drive_range_recent(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

