from brain.base_mechanism import BrainMechanism

class CerebellarTimingCoordinator(BrainMechanism):
    """
    Cerebellum timing — predictive microsecond-scale coordination of action sequences.
    Learns forward models: given motor command, predicts sensory outcome.
    Errors update internal model. Chronic desync degrades precision and patience.
    

CITATIONS
---------
  - [Doya 1999, Neural Netw 12:961, cerebellum reinforcement]
  - [Ito 2008, Nat Rev Neurosci 9:304, cerebellar motor learning]
  - [Schmahmann 2019, Cerebellum 18:1, cerebellar cognitive affective]
"""

    def __init__(self):
        super().__init__("CerebellarTimingCoordinator")
        self.timing_error_history = []
        self.prediction_accuracy_history = []
        self.forward_model_confidence = 0.5
        self.sequence_tempo = 1.0          # 1.0 = normal, <1 = rushed, >1 = lagging
        self.desync_chronic = False
        self.desync_ticks = 0
        self.tempo_drift_history = []
        self.model_update_rate = 0.08
        self.timing_smoothness = 0.7

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"

        if overnight:
            return self._overnight()

        motor_intent = prior.get("PrimaryMotorCortex", {}).get("motor_command_strength", 0.0)
        sensory_feedback = prior.get("SomatosensoryCortex", {}).get("proprioceptive_signal", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        limbic_rush = prior.get("AmygdalaCentralNucleus", {}).get("urgency_output", 0.0)

        # Expected sensory outcome based on current model
        predicted_sensory = self.forward_model_confidence * motor_intent
        timing_error = abs(predicted_sensory - sensory_feedback)
        self.timing_error_history.append(timing_error)
        if len(self.timing_error_history) > 50:
            self.timing_error_history.pop(0)

        # Update forward model via error signal
        correction = timing_error * self.model_update_rate
        if timing_error < 0.15:
            self.forward_model_confidence = min(0.95, self.forward_model_confidence + correction)
        else:
            self.forward_model_confidence = max(0.1, self.forward_model_confidence - correction * 0.5)

        # Tempo: stress and limbic urgency rush the sequence
        target_tempo = 1.0 + (stress * 0.3) + (limbic_rush * 0.4) - (arousal * 0.1)
        self.sequence_tempo += (target_tempo - self.sequence_tempo) * 0.15
        self.tempo_drift_history.append(self.sequence_tempo)
        if len(self.tempo_drift_history) > 30:
            self.tempo_drift_history.pop(0)

        # Timing smoothness degrades with error
        avg_error = sum(self.timing_error_history[-10:]) / max(1, len(self.timing_error_history[-10:]))
        self.timing_smoothness = max(0.1, 1.0 - avg_error * 1.5)

        # Prediction accuracy
        accuracy = 1.0 - timing_error
        self.prediction_accuracy_history.append(accuracy)
        if len(self.prediction_accuracy_history) > 40:
            self.prediction_accuracy_history.pop(0)

        # Chronic desync — persistent high error
        recent_errors = self.timing_error_history[-15:]
        chronic_condition = sum(recent_errors) / len(recent_errors) > 0.35 if recent_errors else False
        if chronic_condition:
            self.desync_ticks += 1
        else:
            self.desync_ticks = max(0, self.desync_ticks - 2)

        was_desynced = self.desync_chronic
        self.desync_chronic = self.desync_ticks > 12

        if self.desync_chronic and not was_desynced:
            self.feed_to_memory({
                "event": "cerebellar_desync",
                "avg_error": round(avg_error, 3),
                "note": "Timing coordination degraded — precision and patience compromised"
            })

        # Coordination output — how well actions are being timed
        coordination_quality = self.forward_model_confidence * self.timing_smoothness
        if self.desync_chronic:
            coordination_quality *= 0.5

        return {
            "coordination_quality": round(coordination_quality, 3),
            "timing_error": round(timing_error, 3),
            "sequence_tempo": round(self.sequence_tempo, 3),
            "forward_model_confidence": round(self.forward_model_confidence, 3),
            "timing_smoothness": round(self.timing_smoothness, 3),
            "desync_chronic": self.desync_chronic,
            "prediction_accuracy": round(accuracy, 3),
        }

    def _overnight(self) -> dict:
        # Sleep consolidates forward models, reduces error accumulation
        self.forward_model_confidence = min(0.9, self.forward_model_confidence + 0.05)
        self.timing_error_history.clear()
        self.desync_ticks = max(0, self.desync_ticks - 8)
        self.desync_chronic = self.desync_ticks > 12
        self.sequence_tempo = 1.0
        self.timing_smoothness = min(0.9, self.timing_smoothness + 0.1)
        return {"overnight": "cerebellar_model_consolidation"}

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

