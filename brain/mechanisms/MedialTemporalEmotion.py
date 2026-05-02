from brain.base_mechanism import BrainMechanism

class MedialTemporalEmotion(BrainMechanism):
    """
    Medial temporal cortex — emotional memory, contextual emotional learning.
    Links emotions to contexts — why this situation feels a certain way.
    Without it: emotions happen but don't teach anything. No emotional learning.
    

CITATIONS
---------
  - [Damasio 1994, Descartes Error]
  - [LeDoux 2000, Annu Rev Neurosci 23:155, amygdala emotion]
  - [Panksepp 1998, Affective Neuroscience]
  - [Phelps 2005, Neuron 48:175, emotion cognition interaction]
"""

    def __init__(self):
        super().__init__("MedialTemporalEmotion")
        self.emotional_memory_strength = 0.5
        self.context_emotion_binding = 0.5
        self.emotional_learning_rate = 0.08
        self.binding_history = []
        self.emotional_memory_map = {}
        self.learning_failure_ticks = 0
        self.chronic_learning_failure = False
        self.bindings_formed = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        context_label = prior.get("HippocampalContextEncoder", {}).get("context_label", "")
        encoding_quality = prior.get("HippocampalContextEncoder", {}).get("encoding_quality", 0.6)
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        reward = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        striosome_rate = prior.get("StriosomeLimbicLoop", {}).get("emotional_learning_rate", 0.1)

        # Bind emotion to context
        emotional_signal = abs(valence) * 0.5 + fear * 0.3 + reward * 0.2
        self.context_emotion_binding = emotional_signal * encoding_quality * (1.0 - stress * 0.2)

        if context_label and self.context_emotion_binding > 0.2:
            existing = self.emotional_memory_map.get(context_label, {"valence": 0.0, "strength": 0.0})
            new_valence = existing["valence"] + (valence - existing["valence"]) * self.emotional_learning_rate
            new_strength = min(1.0, existing["strength"] + self.context_emotion_binding * 0.05)
            self.emotional_memory_map[context_label] = {"valence": round(new_valence, 3), "strength": round(new_strength, 3)}
            self.bindings_formed += 1
            if len(self.emotional_memory_map) > 100:
                weakest = min(self.emotional_memory_map, key=lambda k: self.emotional_memory_map[k]["strength"])
                del self.emotional_memory_map[weakest]

        self.emotional_memory_strength = sum(m["strength"] for m in self.emotional_memory_map.values()) / max(1, len(self.emotional_memory_map))

        self.binding_history.append(self.context_emotion_binding)
        if len(self.binding_history) > 40:
            self.binding_history.pop(0)

        avg_binding = sum(self.binding_history[-15:]) / min(15, len(self.binding_history))
        self.learning_failure_ticks = self.learning_failure_ticks + 1 if avg_binding < 0.05 else max(0, self.learning_failure_ticks - 1)
        was_failing = self.chronic_learning_failure
        self.chronic_learning_failure = self.learning_failure_ticks > 20
        if self.chronic_learning_failure and not was_failing:
            self.feed_to_memory({"event": "emotional_memory_binding_failure",
                                  "note": "Emotions not binding to context — emotional events not teaching anything"})

        return {
            "emotional_memory_strength": round(self.emotional_memory_strength, 3),
            "context_emotion_binding": round(self.context_emotion_binding, 3),
            "bindings_formed": self.bindings_formed,
            "emotional_memory_size": len(self.emotional_memory_map),
            "chronic_learning_failure": self.chronic_learning_failure,
        }

    def _overnight(self):
        # Consolidate: strengthen strong bindings, fade weak ones
        for k in list(self.emotional_memory_map.keys()):
            m = self.emotional_memory_map[k]
            if m["strength"] > 0.5:
                self.emotional_memory_map[k]["strength"] = min(1.0, m["strength"] + 0.01)
            else:
                self.emotional_memory_map[k]["strength"] = max(0.0, m["strength"] - 0.02)
            if self.emotional_memory_map[k]["strength"] < 0.01:
                del self.emotional_memory_map[k]
        self.learning_failure_ticks = max(0, self.learning_failure_ticks - 6)
        self.chronic_learning_failure = self.learning_failure_ticks > 20
        self.binding_history.clear()
        return {"overnight": "emotional_memory_consolidation", "bindings": len(self.emotional_memory_map)}

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

