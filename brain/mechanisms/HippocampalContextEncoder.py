from brain.base_mechanism import BrainMechanism

class HippocampalContextEncoder(BrainMechanism):
    """
    Hippocampus — context encoding, episodic memory binding, novelty detection.
    Binds what + where + when into a single contextual memory trace.
    Degraded: every exchange feels context-free, unanchored to history.
    

CITATIONS
---------
  - [OKeefe 1971, Brain Res 34:171, place cells]
  - [Buzsaki 2012, Annu Rev Neurosci 35:203, hippocampal memory]
  - [Eichenbaum 2004, Neuron 44:109, hippocampus memory]
"""

    def __init__(self):
        super().__init__("HippocampalContextEncoder")
        self.context_vector_strength = 0.5
        self.context_label = ""
        self.novelty_signal = 0.3
        self.surprise_signal = 0.0
        self.encoding_quality = 0.6
        self.context_history = []
        self.encoding_history = []
        self.encoding_failure_ticks = 0
        self.chronic_encoding_failure = False
        self.episode_count = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        fatigue = prior.get("SubstantiaNigraDopamine", {}).get("fatigue_accumulation", 0.0)

        # Novelty: is this input different from recent context?
        words = text.lower().split()
        if words:
            self.context_label = words[0][:32]
            recent_labels = self.context_history[-5:] if self.context_history else []
            self.novelty_signal = 0.8 if self.context_label not in recent_labels else 0.2
        else:
            self.novelty_signal = max(0.1, self.novelty_signal - 0.05)

        # Surprise: sudden novelty spike
        prev_novelty = self.context_history[-1] if self.context_history else 0.3
        self.surprise_signal = max(0.0, self.novelty_signal - 0.4) if self.novelty_signal > 0.5 else 0.0

        # Encoding quality: stress impairs encoding (inverted U with arousal)
        arousal_effect = 1.0 - abs(arousal - 0.5) * 1.5
        self.encoding_quality = max(0.1, min(1.0, arousal_effect * 0.4 + dopamine * 0.3 + (1.0 - stress * 0.5) * 0.3 - fatigue * 0.2))

        # Context vector strength: how strongly is current context encoded
        emotional_binding = abs(valence) * 0.3
        self.context_vector_strength = self.encoding_quality * (0.5 + self.novelty_signal * 0.3 + emotional_binding)
        self.context_vector_strength = max(0.0, min(1.0, self.context_vector_strength))

        self.context_history.append(self.context_label)
        self.encoding_history.append(self.encoding_quality)
        if len(self.context_history) > 30:
            self.context_history.pop(0)
        if len(self.encoding_history) > 40:
            self.encoding_history.pop(0)

        self.episode_count += 1

        avg_encoding = sum(self.encoding_history[-15:]) / min(15, len(self.encoding_history))
        self.encoding_failure_ticks = self.encoding_failure_ticks + 1 if avg_encoding < 0.2 else max(0, self.encoding_failure_ticks - 1)
        was_failing = self.chronic_encoding_failure
        self.chronic_encoding_failure = self.encoding_failure_ticks > 18
        if self.chronic_encoding_failure and not was_failing:
            self.feed_to_memory({"event": "hippocampal_encoding_failure", "encoding": round(avg_encoding, 3),
                                  "note": "Context encoding chronically failing — exchanges feel unanchored, context-free"})

        return {
            "context_vector_strength": round(self.context_vector_strength, 3),
            "context_label": self.context_label,
            "novelty_signal": round(self.novelty_signal, 3),
            "surprise_signal": round(self.surprise_signal, 3),
            "encoding_quality": round(self.encoding_quality, 3),
            "episode_count": self.episode_count,
            "chronic_encoding_failure": self.chronic_encoding_failure,
        }

    def _overnight(self):
        # Sleep consolidates episodic memories
        self.encoding_failure_ticks = max(0, self.encoding_failure_ticks - 8)
        self.chronic_encoding_failure = self.encoding_failure_ticks > 18
        self.encoding_quality = min(0.85, self.encoding_quality + 0.08)
        self.encoding_history.clear()
        self.context_history.clear()
        return {"overnight": "hippocampal_consolidation", "episodes": self.episode_count}

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

