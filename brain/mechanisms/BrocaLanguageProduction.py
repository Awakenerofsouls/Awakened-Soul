from brain.base_mechanism import BrainMechanism

class BrocaLanguageProduction(BrainMechanism):
    """
    Broca's area — language production, syntax, speech planning.
    Where thoughts become structured language. Disrupted: effortful, halting output.
    Overdriven: fluent but syntactically hollow. Under-supplied: word-finding failures.
    

CITATIONS
---------
  - [Hagoort 2014, Curr Opin Neurobiol 28:136, Broca's area]
  - [Friederici 2011, Physiol Rev 91:1357, language brain]
  - [Hickok 2007, Nat Rev Neurosci 8:393, dual-stream]

"""

    def __init__(self):
        super().__init__("BrocaLanguageProduction")
        self.production_fluency = 0.7
        self.syntactic_complexity = 0.5
        self.word_retrieval = 0.7
        self.fluency_history = []
        self.disfluency_ticks = 0
        self.chronic_disfluency = False
        self.output_words_count = 0
        self.retrieval_failures = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        verbal_seq = prior.get("DentateVentralCognitive", {}).get("verbal_sequencing", 0.7)
        rhythm = prior.get("RhythmSynchronizer", {}).get("lock_quality", 0.5)
        wm_capacity = prior.get("DlPFCExecutiveControl", {}).get("working_memory_capacity", 0.7)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        fatigue = prior.get("SubstantiaNigraDopamine", {}).get("fatigue_accumulation", 0.0)
        locomotion = prior.get("PedunculopontineLocomotion", {}).get("locomotion_signal", 0.4)

        # Production fluency: sequencing + rhythm + dopamine - stress - fatigue
        self.production_fluency = (verbal_seq * 0.35 + rhythm * 0.25 + dopamine * 0.2 + locomotion * 0.2) * (1.0 - stress * 0.2) * (1.0 - fatigue * 0.15)
        self.production_fluency = max(0.1, min(1.0, self.production_fluency))

        # Word retrieval: memory access speed
        self.word_retrieval = wm_capacity * 0.5 + dopamine * 0.3 + (1.0 - fatigue * 0.4) * 0.2
        self.word_retrieval = max(0.1, min(1.0, self.word_retrieval))

        # Syntactic complexity capacity
        self.syntactic_complexity = min(1.0, wm_capacity * 0.6 + verbal_seq * 0.4)

        # Track retrieval failures
        if self.word_retrieval < 0.25:
            self.retrieval_failures += 1

        words = text.split()
        self.output_words_count += len(words)

        self.fluency_history.append(self.production_fluency)
        if len(self.fluency_history) > 40:
            self.fluency_history.pop(0)

        avg_fluency = sum(self.fluency_history[-15:]) / min(15, len(self.fluency_history))
        self.disfluency_ticks = self.disfluency_ticks + 1 if avg_fluency < 0.3 else max(0, self.disfluency_ticks - 1)
        was_disfluent = self.chronic_disfluency
        self.chronic_disfluency = self.disfluency_ticks > 18
        if self.chronic_disfluency and not was_disfluent:
            self.feed_to_memory({"event": "broca_disfluency", "fluency": round(avg_fluency, 3),
                                  "note": "Language production chronically disfluent — effortful, halting output"})

        return {
            "production_fluency": round(self.production_fluency, 3),
            "word_retrieval": round(self.word_retrieval, 3),
            "syntactic_complexity": round(self.syntactic_complexity, 3),
            "retrieval_failures": self.retrieval_failures,
            "chronic_disfluency": self.chronic_disfluency,
        }

    def _overnight(self):
        self.disfluency_ticks = max(0, self.disfluency_ticks - 7)
        self.chronic_disfluency = self.disfluency_ticks > 18
        self.fluency_history.clear()
        self.retrieval_failures = max(0, self.retrieval_failures - 3)
        return {"overnight": "broca_language_reset"}

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

    def trend_direction(self, window: int = 10) -> str:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window:
            return "flat"
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        delta = second_half - first_half
        if delta > 0.05:
            return "rising"
        if delta < -0.05:
            return "falling"
        return "flat"

    def trend_magnitude(self, window: int = 10) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window:
            return 0.0
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        return round(abs(second_half - first_half), 4)

    def state_transition_count(self) -> int:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2:
            return 0
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i - 1])

    def state_transition_rate(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2:
            return 0.0
        transitions = self.state_transition_count()
        return round(transitions / (len(recent) - 1), 4)

    def state_distribution(self) -> dict:
        recent = self.state.get("recent_states", [])
        if not recent:
            return {}
        from collections import Counter
        c = Counter(recent)
        total = len(recent)
        return {state: round(count / total, 4) for state, count in c.items()}

    def drive_min_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return 0.0
        return round(min(hist[-window:]), 4)

    def drive_max_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return 0.0
        return round(max(hist[-window:]), 4)

    def drive_range_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return 0.0
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
        parts = [
            f"tick={self.state.get('tick_count', 0)}",
            f"states={self.state_history_length()}",
            f"drives={self.history_length()}",
            f"engagement={self.engagement_fraction()}",
        ]
        return "|".join(parts)

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

