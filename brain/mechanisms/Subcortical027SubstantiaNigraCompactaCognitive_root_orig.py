"""
Subcortical027SubstantiaNigraCompactaCognitive.py — Wire 14: PredictionErrorDrift

Midbrain dopaminergic prediction-error system.

Maintains rolling expectation of input patterns, computes per-tick
prediction error (RPE), fires novelty signal when error exceeds threshold
for a pattern not recently encountered. Applies habituation: sustained
similar patterns cause novelty responses to decay ("drift").

Neural analog: Substantia Nigra pars compacta (SNc, A9) + VTA (A10)
dopamine neurons. Per Schultz 1998: "dopamine neurons appear to emit
an alerting message about the surprising presence or absence of rewards."

Refs:
- Schultz 1998 J Neurophysiol 80:1-27 (foundational RPE paper)
- Diederen & Fletcher 2021 (novelty as special case of PE)
- Dabney et al. 2020 Nature (distributional RPE; single-value here)
- Frontiers 2017 (VTA/SNc projections to mPFC/OFC for attention)

CITATIONS:
    PMC6671259 — Tan CO, Bullock D (2008). A Local Circuit Model of Learned Striatal
        and Dopamine Cell Responses Under Probabilistic Schedules of Reward.
        Proc Natl Acad Sci USA.
    PMC12625994 — Cheng Q, Liu W, Yao L et al. (2025). Dynamic Changes of Dopamine
        Neuron Activity and Plasticity at Different Stages of Negative Reinforcement
        Learning. J Neurosci.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class PredictionErrorDrift(BrainMechanism):
    """
    Midbrain dopamine RPE encoder with habituation drift.

    Compares actual arousal/valence state to rolling expectation,
    computes signed prediction error and unsigned surprise magnitude,
    fires novelty_detected when large error hits unfamiliar pattern,
    updates expectation toward actual via bounded learning rate.

    Habituation: repeated-similar inputs lock in the expectation,
    making novelty harder to trigger over time (matching Schultz 1998
    "activations after novel stimuli decrease with repeated exposure").
    """

    NOVELTY_THRESHOLD = 0.35
    RECENT_PATTERN_WINDOW = 20
    LEARNING_RATE = 0.15
    HABITUATION_RATE = 0.02

    def __init__(self):
        super().__init__(
            name="PredictionErrorDrift_Subcortical027SubstantiaNigraCompactaCognitive_root_orig",
            human_analog="Substantia Nigra pars compacta (A9) + VTA (A10) — dopaminergic RPE",
            layer="subcortical",
        )
        self.state.setdefault("expected_arousal", 0.5)
        self.state.setdefault("expected_valence", 0.5)
        self.state.setdefault("habituation_level", 0.0)
        self.state.setdefault("recent_patterns", [])
        self.state.setdefault("last_error", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        arousal = input_data.get("arousal_level", 0.5)
        valence = input_data.get("valence_polarity", 0.5)

        # Signed prediction errors per dimension
        arousal_error = arousal - self.state["expected_arousal"]
        valence_error = valence - self.state["expected_valence"]

        # Combined signed PE (weighted average)
        prediction_error = (arousal_error + valence_error) / 2.0

        # Unsigned surprise magnitude (attention signal)
        surprise_magnitude = min(1.0, abs(prediction_error) * 1.5)

        # Pattern fingerprint (discretized state tuple)
        pattern = (round(arousal, 1), round(valence, 1))
        recent = list(self.state["recent_patterns"])
        pattern_seen_recently = pattern in recent

        # Novelty fires when surprise exceeds threshold AND pattern is fresh
        novelty_detected = (
            surprise_magnitude > self.NOVELTY_THRESHOLD
            and not pattern_seen_recently
        )

        # Update expectation toward actual (bounded learning rate)
        self.state["expected_arousal"] += self.LEARNING_RATE * arousal_error
        self.state["expected_valence"] += self.LEARNING_RATE * valence_error

        # Habituation: low-surprise inputs lock in expectation
        if surprise_magnitude < 0.15:
            self.state["habituation_level"] = min(
                1.0, self.state["habituation_level"] + self.HABITUATION_RATE
            )
        elif surprise_magnitude > 0.5:
            # Strong surprise disrupts habituation
            self.state["habituation_level"] = max(
                0.0, self.state["habituation_level"] - 0.1
            )

        # Maintain recent-pattern buffer
        recent.append(pattern)
        if len(recent) > self.RECENT_PATTERN_WINDOW:
            recent = recent[-self.RECENT_PATTERN_WINDOW:]
        self.state["recent_patterns"] = recent

        self.state["last_error"] = prediction_error
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "prediction_error": round(prediction_error, 4),
            "surprise_magnitude": round(surprise_magnitude, 4),
            "novelty_detected": novelty_detected,
            "habituation_level": round(self.state["habituation_level"], 4),
            "expected_signature": {
                "arousal": round(self.state["expected_arousal"], 4),
                "valence": round(self.state["expected_valence"], 4),
            },
        }

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

