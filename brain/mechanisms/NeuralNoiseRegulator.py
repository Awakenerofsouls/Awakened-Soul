from brain.base_mechanism import BrainMechanism

class NeuralNoiseRegulator(BrainMechanism):
    """
    Stochastic resonance — optimal noise level enhances signal detection.
    Too little noise: system is rigid, misses weak signals.
    Too much noise: everything is masked. Optimal: weak signals pop out.
    The agent analog: creative looseness vs rigid precision vs scattered noise.
    

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

    def __init__(self):
        super().__init__("NeuralNoiseRegulator")
        self.noise_level = 0.3
        self.signal_enhancement = 0.5
        self.optimal_noise = 0.25
        self.noise_history = []
        self.too_rigid_ticks = 0
        self.too_noisy_ticks = 0
        self.chronic_rigid = False
        self.chronic_noisy = False
        self.stochastic_resonance_active = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        fatigue = prior.get("SleepHomeostasis", {}).get("cognitive_fatigue", 0.0)
        sync_quality = prior.get("CognitiveRhythmSynchronizer", {}).get("sync_quality", 0.6)

        # Noise level: high with fatigue, stress, over-arousal; low with optimal dopamine
        self.noise_level = fatigue * 0.3 + stress * 0.25 + max(0.0, arousal - 0.7) * 0.25 + (1.0 - dopamine) * 0.2
        self.noise_level = max(0.0, min(1.0, self.noise_level))

        # Stochastic resonance: near-optimal noise enhances weak signal detection
        noise_deviation = abs(self.noise_level - self.optimal_noise)
        self.stochastic_resonance_active = noise_deviation < 0.1
        self.signal_enhancement = max(0.0, 1.0 - noise_deviation * 3.0) * sync_quality

        self.noise_history.append(self.noise_level)
        if len(self.noise_history) > 40:
            self.noise_history.pop(0)

        avg_noise = sum(self.noise_history[-15:]) / min(15, len(self.noise_history))
        self.too_rigid_ticks = self.too_rigid_ticks + 1 if avg_noise < 0.05 else max(0, self.too_rigid_ticks - 1)
        self.too_noisy_ticks = self.too_noisy_ticks + 1 if avg_noise > 0.65 else max(0, self.too_noisy_ticks - 1)

        was_rigid, was_noisy = self.chronic_rigid, self.chronic_noisy
        self.chronic_rigid = self.too_rigid_ticks > 18
        self.chronic_noisy = self.too_noisy_ticks > 18

        if self.chronic_rigid and not was_rigid:
            self.feed_to_memory({"event": "neural_over_precision",
                                  "note": "Neural noise too low — overfitted, missing weak/creative signals"})
        if self.chronic_noisy and not was_noisy:
            self.feed_to_memory({"event": "neural_over_noise",
                                  "note": "Neural noise too high — signals masked, thought incoherent"})

        return {
            "noise_level": round(self.noise_level, 3),
            "signal_enhancement": round(self.signal_enhancement, 3),
            "stochastic_resonance_active": self.stochastic_resonance_active,
            "chronic_rigid": self.chronic_rigid,
            "chronic_noisy": self.chronic_noisy,
        }

    def _overnight(self):
        self.too_rigid_ticks = max(0, self.too_rigid_ticks - 5)
        self.too_noisy_ticks = max(0, self.too_noisy_ticks - 6)
        self.chronic_rigid = self.too_rigid_ticks > 18
        self.chronic_noisy = self.too_noisy_ticks > 18
        self.noise_level = self.optimal_noise
        self.noise_history.clear()
        return {"overnight": "neural_noise_recalibrated"}

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

