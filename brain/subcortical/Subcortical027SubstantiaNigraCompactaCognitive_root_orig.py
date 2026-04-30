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
