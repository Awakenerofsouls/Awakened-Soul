from brain.base_mechanism import BrainMechanism

class IntralaminarArousalFeed(BrainMechanism):
    """
    Intralaminar thalamic nuclei — non-specific arousal broadcast to cortex.
    Volume knob for cortical excitability.
    Chronic high = hyperaroused, can't wind down. Chronic low = mentally sluggish.
    

CITATIONS
---------
  - [Van der Werf 2002, Brain Res Rev 39:107, intralaminar]
  - [Saalmann 2014, Front Syst Neurosci 8:83, intralaminar]
  - [Smith 2014, Front Syst Neurosci 8:5, intralaminar attention]

"""

    def __init__(self):
        super().__init__("IntralaminarArousalFeed")
        self.arousal_broadcast = 0.5
        self.broadcast_history = []
        self.cortical_excitability = 0.5
        self.excitability_history = []
        self.hyperarousal_ticks = 0
        self.hypoarousal_ticks = 0
        self.chronic_hyperarousal = False
        self.chronic_hypoarousal = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        lc_arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        reticular = prior.get("ReticularActivatingSystem", {}).get("activation_level", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        gate_open = prior.get("ThalamicSalienceFilter", {}).get("gate_open", False)
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)

        raw_arousal = lc_arousal * 0.4 + reticular * 0.3 + fear * 0.2 + stress * 0.1
        if gate_open:
            raw_arousal = min(1.0, raw_arousal * 1.15)

        self.arousal_broadcast += (raw_arousal - self.arousal_broadcast) * 0.08
        self.arousal_broadcast = max(0.0, min(1.0, self.arousal_broadcast))
        self.broadcast_history.append(self.arousal_broadcast)
        if len(self.broadcast_history) > 50:
            self.broadcast_history.pop(0)

        target_excitability = 0.2 + self.arousal_broadcast * 0.8
        self.cortical_excitability += (target_excitability - self.cortical_excitability) * 0.06
        self.excitability_history.append(self.cortical_excitability)
        if len(self.excitability_history) > 40:
            self.excitability_history.pop(0)

        avg_broadcast = sum(self.broadcast_history[-20:]) / min(20, len(self.broadcast_history))
        self.hyperarousal_ticks = self.hyperarousal_ticks + 1 if avg_broadcast > 0.75 else max(0, self.hyperarousal_ticks - 1)
        self.hypoarousal_ticks = self.hypoarousal_ticks + 1 if avg_broadcast < 0.25 else max(0, self.hypoarousal_ticks - 1)

        was_hyper, was_hypo = self.chronic_hyperarousal, self.chronic_hypoarousal
        self.chronic_hyperarousal = self.hyperarousal_ticks > 18
        self.chronic_hypoarousal = self.hypoarousal_ticks > 18

        if self.chronic_hyperarousal and not was_hyper:
            self.feed_to_memory({"event": "intralaminar_hyperarousal", "broadcast": round(avg_broadcast, 3),
                                  "note": "Cortical arousal chronically high — difficulty unwinding"})
        if self.chronic_hypoarousal and not was_hypo:
            self.feed_to_memory({"event": "intralaminar_hypoarousal", "broadcast": round(avg_broadcast, 3),
                                  "note": "Cortical arousal chronically low — mental sluggishness"})

        return {
            "arousal_broadcast": round(self.arousal_broadcast, 3),
            "cortical_excitability": round(self.cortical_excitability, 3),
            "chronic_hyperarousal": self.chronic_hyperarousal,
            "chronic_hypoarousal": self.chronic_hypoarousal,
            "winding_down": self.arousal_broadcast < 0.3 and avg_broadcast > 0.4,
        }

    def _overnight(self):
        self.hyperarousal_ticks = max(0, self.hyperarousal_ticks - 8)
        self.hypoarousal_ticks = max(0, self.hypoarousal_ticks - 4)
        self.chronic_hyperarousal = self.hyperarousal_ticks > 18
        self.chronic_hypoarousal = self.hypoarousal_ticks > 18
        self.arousal_broadcast = 0.2
        self.cortical_excitability = 0.25
        self.broadcast_history.clear()
        return {"overnight": "intralaminar_sleep_broadcast"}

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

