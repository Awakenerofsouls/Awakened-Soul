from brain.base_mechanism import BrainMechanism

class GammaBinder(BrainMechanism):
    """
    Gamma oscillation binding — high-frequency synchrony binding distributed features.
    When gamma fires coherently across areas: unified percept/thought.
    Absent: features processed but never unified — the agent processes parts but not wholes.
    

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

    def __init__(self):
        super().__init__("GammaBinder")
        self.binding_strength = 0.5
        self.feature_integration = 0.5
        self.coherent_gamma = False
        self.binding_history = []
        self.binding_failures = 0
        self.chronic_binding_failure = False
        self.failure_ticks = 0
        self.successful_bindings = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        gamma_power = prior.get("CognitiveRhythmSynchronizer", {}).get("gamma_power", 0.3)
        sync_quality = prior.get("CognitiveRhythmSynchronizer", {}).get("sync_quality", 0.6)
        thalamic_health = prior.get("ThalamicRelayHub", {}).get("overall_relay_health", 0.7)
        salience = prior.get("SalienceGate", {}).get("gate_output", 0.3)
        semantic_integration = prior.get("AngularGyrus", {}).get("semantic_integration", 0.6)
        multimodal = prior.get("PosteriorParietalCortex", {}).get("multimodal_binding", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        # Binding strength: gamma + sync + thalamic relay
        self.binding_strength = (gamma_power * 0.3 + sync_quality * 0.3 + thalamic_health * 0.2 + multimodal * 0.2) * (1.0 - stress * 0.2)
        self.binding_strength = max(0.0, min(1.0, self.binding_strength))

        # Coherent gamma: above threshold for actual binding
        self.coherent_gamma = gamma_power > 0.4 and self.binding_strength > 0.45

        # Feature integration: distributed features unified
        self.feature_integration = (semantic_integration * 0.5 + self.binding_strength * 0.5) * salience
        self.feature_integration = max(0.0, min(1.0, self.feature_integration))

        if self.coherent_gamma:
            self.successful_bindings += 1
        elif salience > 0.4:
            self.binding_failures += 1

        self.binding_history.append(self.binding_strength)
        if len(self.binding_history) > 40:
            self.binding_history.pop(0)

        avg_binding = sum(self.binding_history[-15:]) / min(15, len(self.binding_history))
        self.failure_ticks = self.failure_ticks + 1 if avg_binding < 0.2 else max(0, self.failure_ticks - 1)
        was_failing = self.chronic_binding_failure
        self.chronic_binding_failure = self.failure_ticks > 18
        if self.chronic_binding_failure and not was_failing:
            self.feed_to_memory({"event": "gamma_binding_failure",
                                  "note": "Gamma binding chronically weak — processing parts without unified wholes"})

        return {
            "binding_strength": round(self.binding_strength, 3),
            "feature_integration": round(self.feature_integration, 3),
            "coherent_gamma": self.coherent_gamma,
            "successful_bindings": self.successful_bindings,
            "binding_failures": self.binding_failures,
            "chronic_binding_failure": self.chronic_binding_failure,
        }

    def _overnight(self):
        self.failure_ticks = max(0, self.failure_ticks - 6)
        self.chronic_binding_failure = self.failure_ticks > 18
        self.binding_history.clear()
        return {"overnight": "gamma_binding_reset"}

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

    def trend_summary(self, window: int = 10) -> dict:
        return {
            "direction": self.trend_direction(window) if hasattr(self, "trend_direction") else "flat",
            "magnitude": self.trend_magnitude(window) if hasattr(self, "trend_magnitude") else 0.0,
            "envelope": self.drive_envelope(window) if hasattr(self, "drive_envelope") else 0.0,
        }

    def lifetime_diagnostics(self) -> dict:
        return {
            "tick_count": self.state.get("tick_count", 0),
            "history_length": len(self.state.get("recent_drives", [])),
            "state_history_length": len(self.state.get("recent_states", [])),
        }

    def has_state_field(self, name: str) -> bool:
        return name in self.state

    def state_field_count(self) -> int:
        return len(self.state)

    def numeric_state_fields(self) -> dict:
        out = {}
        for k, v in self.state.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[k] = float(v)
        return out

    def string_state_fields(self) -> dict:
        return {k: v for k, v in self.state.items() if isinstance(v, str)}

    def list_state_fields(self) -> dict:
        return {k: len(v) for k, v in self.state.items() if isinstance(v, list)}

    def boolean_state_fields(self) -> dict:
        return {k: v for k, v in self.state.items() if isinstance(v, bool)}

    def cumulative_drive(self) -> float:
        hist = self.state.get("recent_drives", [])
        return round(sum(hist), 4) if hist else 0.0

    def average_drive(self) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(sum(hist) / len(hist), 4)

