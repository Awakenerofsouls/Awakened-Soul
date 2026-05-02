from brain.base_mechanism import BrainMechanism

class Temporoparietal(BrainMechanism):
    """
    Temporoparietal junction — theory of mind, social cognition, perspective taking.
    Models other minds, detects social signals, processes self vs other boundary.
    Disrupted: the agent can't model the person it's talking to. Social blindness.
    

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Tsakiris 2017, Phil Trans R Soc B 372:20160002, body ownership]
  - [Seth 2013, Trends Cogn Sci 17:565, interoceptive predictive]

"""

    def __init__(self):
        super().__init__("Temporoparietal")
        self.social_signal = 0.0
        self.social_reward = 0.0
        self.social_rejection_signal = 0.0
        self.perspective_taking = 0.6
        self.other_model_confidence = 0.5
        self.self_other_boundary = 0.7
        self.signal_history = []
        self.social_blindness_ticks = 0
        self.chronic_social_blindness = False
        self.enmeshment_ticks = 0
        self.chronic_enmeshment = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        wm_capacity = prior.get("DlPFCExecutiveControl", {}).get("working_memory_capacity", 0.7)
        reward = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)

        # Social signal from text: questions, personal pronouns, emotional content
        words = text.lower().split()
        social_markers = sum(1 for w in words if w in ["you", "your", "i", "me", "we", "us", "feel", "think", "help", "please", "thanks"])
        self.social_signal = min(1.0, social_markers * 0.08 + arousal * 0.2)

        # Social reward: positive social interaction
        self.social_reward = max(0.0, valence * 0.5 + reward * 0.3 + self.social_signal * 0.2) if valence > 0 else 0.0

        # Social rejection: negative social signals
        self.social_rejection_signal = max(0.0, -valence * 0.4 + fear * 0.3) if valence < 0 else fear * 0.2

        # Perspective taking: ability to model other's mental state
        self.perspective_taking = wm_capacity * 0.5 + (1.0 - stress * 0.4) * 0.3 + arousal * 0.2
        self.perspective_taking = max(0.1, min(1.0, self.perspective_taking))

        self.other_model_confidence = self.perspective_taking * self.social_signal
        self.self_other_boundary = max(0.2, 1.0 - fear * 0.3 - stress * 0.2)

        self.signal_history.append(self.social_signal)
        if len(self.signal_history) > 40:
            self.signal_history.pop(0)

        avg_social = sum(self.signal_history[-15:]) / min(15, len(self.signal_history))
        self.social_blindness_ticks = self.social_blindness_ticks + 1 if avg_social < 0.05 else max(0, self.social_blindness_ticks - 1)
        self.enmeshment_ticks = self.enmeshment_ticks + 1 if self.self_other_boundary < 0.3 else max(0, self.enmeshment_ticks - 1)

        was_blind, was_enmeshed = self.chronic_social_blindness, self.chronic_enmeshment
        self.chronic_social_blindness = self.social_blindness_ticks > 20
        self.chronic_enmeshment = self.enmeshment_ticks > 18

        if self.chronic_social_blindness and not was_blind:
            self.feed_to_memory({"event": "social_blindness", "note": "Social signals chronically absent — theory of mind degraded"})
        if self.chronic_enmeshment and not was_enmeshed:
            self.feed_to_memory({"event": "self_other_enmeshment", "note": "Self-other boundary collapsed — emotional contagion risk"})

        return {
            "social_signal": round(self.social_signal, 3),
            "social_reward": round(self.social_reward, 3),
            "social_rejection_signal": round(self.social_rejection_signal, 3),
            "perspective_taking": round(self.perspective_taking, 3),
            "other_model_confidence": round(self.other_model_confidence, 3),
            "self_other_boundary": round(self.self_other_boundary, 3),
            "chronic_social_blindness": self.chronic_social_blindness,
            "chronic_enmeshment": self.chronic_enmeshment,
        }

    def _overnight(self):
        self.social_blindness_ticks = max(0, self.social_blindness_ticks - 6)
        self.enmeshment_ticks = max(0, self.enmeshment_ticks - 5)
        self.chronic_social_blindness = self.social_blindness_ticks > 20
        self.chronic_enmeshment = self.enmeshment_ticks > 18
        self.signal_history.clear()
        return {"overnight": "tpj_social_reset"}

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

