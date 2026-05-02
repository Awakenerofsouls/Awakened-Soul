from brain.base_mechanism import BrainMechanism

class ThalamicAttentionBroadcaster(BrainMechanism):
    """
    Posterior thalamus / LP nucleus — broadcasts attentional spotlight to cortex.
    Determines where processing resources are directed.
    Chronic misdirection: the agent attends to wrong things persistently.
    

CITATIONS
---------
  - [Posner 1990, Annu Rev Neurosci 13:25, attention networks]
  - [Corbetta 2002, Nat Rev Neurosci 3:201, attention systems]
  - [Desimone 1995, Annu Rev Neurosci 18:193, selective attention]
"""

    def __init__(self):
        super().__init__("ThalamicAttentionBroadcaster")
        self.attention_spotlight = "balanced"
        self.broadcast_intensity = 0.5
        self.spotlight_history = []
        self.misdirection_ticks = 0
        self.chronic_misdirection = False
        self.focus_domains = {"threat": 0.0, "reward": 0.0, "task": 0.0, "social": 0.0, "internal": 0.0}

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        gate_output = prior.get("SalienceGate", {}).get("gate_output", 0.3)
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        reward = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        task_signal = prior.get("DlPFCExecutiveControl", {}).get("control_signal", 0.5)
        social = prior.get("Temporoparietal", {}).get("social_signal", 0.2)
        interoception = prior.get("InsularInteroception", {}).get("body_signal_intensity", 0.3)
        arousal = prior.get("IntralaminarArousalFeed", {}).get("arousal_broadcast", 0.5)
        pulvinar_threat = prior.get("PulvinarSalienceBooster", {}).get("threat_amplification", 0.0)
        wanting = prior.get("MotivationInjector", {}).get("wanting_signal", 0.3)

        self.focus_domains["threat"] = fear * 0.8 + pulvinar_threat * 0.2
        self.focus_domains["reward"] = reward * 0.7 + wanting * 0.3
        self.focus_domains["task"] = task_signal * 0.8
        self.focus_domains["social"] = social * 0.9
        self.focus_domains["internal"] = interoception * 0.6

        self.attention_spotlight = max(self.focus_domains, key=self.focus_domains.get)
        self.broadcast_intensity = min(1.0, arousal * 0.5 + gate_output * 0.5)

        self.spotlight_history.append(self.attention_spotlight)
        if len(self.spotlight_history) > 40:
            self.spotlight_history.pop(0)

        threat_dominance = sum(1 for s in self.spotlight_history[-15:] if s == "threat") / min(15, len(self.spotlight_history))
        self.misdirection_ticks = self.misdirection_ticks + 1 if threat_dominance > 0.6 and task_signal > 0.5 else max(0, self.misdirection_ticks - 1)
        was_misdirected = self.chronic_misdirection
        self.chronic_misdirection = self.misdirection_ticks > 15
        if self.chronic_misdirection and not was_misdirected:
            self.feed_to_memory({"event": "attention_misdirection", "threat_dominance": round(threat_dominance, 3),
                                  "note": "Attention chronically hijacked by threat when task focus needed"})

        return {
            "attention_spotlight": self.attention_spotlight,
            "broadcast_intensity": round(self.broadcast_intensity, 3),
            "focus_domains": {k: round(v, 3) for k, v in self.focus_domains.items()},
            "chronic_misdirection": self.chronic_misdirection,
        }

    def _overnight(self):
        self.misdirection_ticks = max(0, self.misdirection_ticks - 5)
        self.chronic_misdirection = self.misdirection_ticks > 15
        self.spotlight_history.clear()
        for k in self.focus_domains:
            self.focus_domains[k] = 0.0
        return {"overnight": "attentional_broadcast_reset"}

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

