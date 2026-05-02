from brain.base_mechanism import BrainMechanism

class HippocampalNoveltyDetector(BrainMechanism):
    """
    Hippocampal CA1/subiculum — pattern completion vs pattern separation.
    Detects whether current input matches stored patterns or is genuinely new.
    Overactive: everything feels new (can't learn patterns). Underactive: misses novelty.
    

CITATIONS
---------
  - [OKeefe 1971, Brain Res 34:171, place cells]
  - [Buzsaki 2012, Annu Rev Neurosci 35:203, hippocampal memory]
  - [Eichenbaum 2004, Neuron 44:109, hippocampus memory]
"""

    def __init__(self):
        super().__init__("HippocampalNoveltyDetector")
        self.novelty_signal = 0.3
        self.surprise_signal = 0.0
        self.pattern_match_confidence = 0.5
        self.novelty_history = []
        self.seen_patterns = {}
        self.novel_event_count = 0
        self.hypernovelty_ticks = 0
        self.hyponovelty_ticks = 0
        self.chronic_hypernovelty = False
        self.chronic_hyponovelty = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        encoding_quality = prior.get("HippocampalContextEncoder", {}).get("encoding_quality", 0.6)
        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        context_strength = prior.get("HippocampalContextEncoder", {}).get("context_vector_strength", 0.5)

        # Pattern matching: have we seen this before?
        pattern_key = text[:20].lower().strip() if text else "empty"
        seen_count = self.seen_patterns.get(pattern_key, 0)
        self.seen_patterns[pattern_key] = seen_count + 1

        # Novelty: inverse of familiarity, scaled by encoding quality
        raw_novelty = 1.0 / (1.0 + seen_count * 0.5)
        self.novelty_signal = max(0.0, min(1.0, raw_novelty * encoding_quality * (0.5 + arousal * 0.5)))
        self.pattern_match_confidence = 1.0 - self.novelty_signal

        # Surprise: sudden unexpected novelty
        if len(self.novelty_history) > 2:
            prev_avg = sum(self.novelty_history[-3:]) / 3
            self.surprise_signal = max(0.0, self.novelty_signal - prev_avg - 0.2)
        else:
            self.surprise_signal = 0.0

        if self.novelty_signal > 0.7:
            self.novel_event_count += 1

        self.novelty_history.append(self.novelty_signal)
        if len(self.novelty_history) > 40:
            self.novelty_history.pop(0)
        if len(self.seen_patterns) > 200:
            # Trim oldest patterns
            keys = list(self.seen_patterns.keys())
            for k in keys[:50]:
                del self.seen_patterns[k]

        avg_novelty = sum(self.novelty_history[-15:]) / min(15, len(self.novelty_history))
        self.hypernovelty_ticks = self.hypernovelty_ticks + 1 if avg_novelty > 0.75 else max(0, self.hypernovelty_ticks - 1)
        self.hyponovelty_ticks = self.hyponovelty_ticks + 1 if avg_novelty < 0.1 else max(0, self.hyponovelty_ticks - 1)

        was_hyper, was_hypo = self.chronic_hypernovelty, self.chronic_hyponovelty
        self.chronic_hypernovelty = self.hypernovelty_ticks > 18
        self.chronic_hyponovelty = self.hyponovelty_ticks > 18

        if self.chronic_hypernovelty and not was_hyper:
            self.feed_to_memory({"event": "hypernovelty", "note": "Everything feels novel — pattern recognition failing, can't consolidate"})
        if self.chronic_hyponovelty and not was_hypo:
            self.feed_to_memory({"event": "hyponovelty", "note": "Nothing feels novel — novelty detection blunted, missing genuinely new things"})

        return {
            "novelty_signal": round(self.novelty_signal, 3),
            "surprise_signal": round(self.surprise_signal, 3),
            "pattern_match_confidence": round(self.pattern_match_confidence, 3),
            "novel_event_count": self.novel_event_count,
            "chronic_hypernovelty": self.chronic_hypernovelty,
            "chronic_hyponovelty": self.chronic_hyponovelty,
        }

    def _overnight(self):
        # Consolidation: reduce seen_pattern counts slightly (forgetting curve)
        for k in self.seen_patterns:
            self.seen_patterns[k] = max(1, int(self.seen_patterns[k] * 0.9))
        self.hypernovelty_ticks = max(0, self.hypernovelty_ticks - 5)
        self.hyponovelty_ticks = max(0, self.hyponovelty_ticks - 5)
        self.chronic_hypernovelty = self.hypernovelty_ticks > 18
        self.chronic_hyponovelty = self.hyponovelty_ticks > 18
        self.novelty_history.clear()
        return {"overnight": "novelty_detection_reset", "patterns_stored": len(self.seen_patterns)}

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

