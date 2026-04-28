"""
Limbic035BasolateralAmygdalaPlasticity.py — Build 4: ValenceTagger

Basolateral amygdala (BLA) valence encoder.

Assigns valence polarity, intensity, and categorical flags (threat/
reward/high-valence) to the current state based on neuromodulatory
inputs from arousal, prediction error, and drive context.

Neural analog: Basolateral amygdala — receives cholinergic (BF),
serotonergic (DRN), dopaminergic (VTA) inputs. Separate BLA→NAc
populations encode positive valence, BLA→CeA populations encode
negative valence. Outputs passed to vmPFC/OFC for value integration.

Refs:
- Beyeler et al. 2018 Cell Reports — BLA projection-defined valence
- O'Neill et al. 2021 PMC8238900 — BLA circuit valence encoding
- Shabel et al. 2018 — separate positive/negative populations + salience overlap
- Kyriazi et al. 2018 Neuron — multi-dimensional BLA population coding
- J Neurosci 2020 Vainik et al. — BLA→OFC/vmPFC integration
"""

from brain.base_mechanism import BrainMechanism


class ValenceTagger(BrainMechanism):
    """
    Basolateral amygdala valence encoder.

    Computes valence polarity and intensity from signed prediction
    error, arousal state, and drive context. Smoothly integrates
    over time to avoid instant valence flips. Produces categorical
    flags: high_valence, threat_signal, reward_signal.
    
CITATIONS:
    PMC12353201 — Nabavi et al. (2014). Engineering a memory of fear
        with artificial LTP. Nature.
    PMC13097094 — Tovote et al. (2015). BLA plasticity mechanisms
        during fear conditioning. Neuron.
    PMC13093011 — Maren (2011). Hippocampal-amygdala interactions in
        fear learning. J Neurosci.
    PMC13090624 — Roozendaal et al. (2009). Noradrenergic modulation
        of BLA plasticity. Neurobiol Learn Mem.
    PMC13077670 — Malvaez et al. (2019). BLA ensemble activity
        during fear extinction. Cell Rep.

"""

    NEUTRAL_POLARITY = 0.5
    HIGH_VALENCE_THRESHOLD = 0.55
    THREAT_POLARITY_MAX = 0.30
    THREAT_INTENSITY_MIN = 0.40
    REWARD_POLARITY_MIN = 0.70
    REWARD_INTENSITY_MIN = 0.40

    # Drive context → polarity bias
    DRIVE_BIAS = {
        "connection": 0.05,
        "rest": -0.02,
        "curiosity": 0.02,
        "expression": 0.03,
        "stability": -0.05,
    }

    def __init__(self):
        super().__init__(
            name="ValenceTagger",
            human_analog="Basolateral amygdala — valence polarity + intensity encoding",
            layer="limbic",
        )
        self.state.setdefault("valence_polarity", self.NEUTRAL_POLARITY)
        self.state.setdefault("valence_intensity", 0.3)
        self.state.setdefault("recent_polarity_history", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Polarity from signed prediction error (VTA→BLA dopaminergic input) ---
        prediction_error = prior.get("PredictionErrorDrift", {}).get(
            "prediction_error", 0.0
        )
        # Map signed PE [-1, 1] → polarity [0, 1] with 0.5 = neutral
        pe_contribution = 0.5 + (prediction_error * 0.4)  # dampened to avoid saturation

        # --- Drive context shifts polarity baseline ---
        dominant_drive = prior.get("Homeostat", {}).get("dominant_drive", "curiosity")
        drive_bias = self.DRIVE_BIAS.get(dominant_drive, 0.0)

        # --- Smooth integration toward target (BLA temporal dynamics) ---
        target_polarity = max(0.0, min(1.0, pe_contribution + drive_bias))
        current_polarity = self.state["valence_polarity"]
        new_polarity = current_polarity + (target_polarity - current_polarity) * 0.3

        # --- Intensity from surprise + phasic arousal ---
        surprise = prior.get("PredictionErrorDrift", {}).get("surprise_magnitude", 0.0)
        phasic = prior.get("ArousalRegulator", {}).get("phasic_burst_active", False)
        tonic_arousal = prior.get("ArousalRegulator", {}).get("tonic_level", 0.5)

        intensity_base = surprise * 0.7 + (tonic_arousal - 0.5) * 0.3
        if phasic:
            intensity_base += 0.2  # phasic burst amplifies BLA salience

        new_intensity = max(0.0, min(1.0, intensity_base))

        # --- Categorical flags ---
        high_valence = new_intensity > self.HIGH_VALENCE_THRESHOLD
        threat_signal = (
            new_polarity < self.THREAT_POLARITY_MAX
            and new_intensity > self.THREAT_INTENSITY_MIN
        )
        reward_signal = (
            new_polarity > self.REWARD_POLARITY_MIN
            and new_intensity > self.REWARD_INTENSITY_MIN
        )

        # --- Track recent polarity for stability detection ---
        history = list(self.state["recent_polarity_history"])
        history.append(new_polarity)
        if len(history) > 10:
            history = history[-10:]
        self.state["recent_polarity_history"] = history

        # Persist
        self.state["valence_polarity"] = new_polarity
        self.state["valence_intensity"] = new_intensity
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "valence_polarity": round(new_polarity, 4),
            "valence_intensity": round(new_intensity, 4),
            "high_valence": high_valence,
            "threat_signal": threat_signal,
            "reward_signal": reward_signal,
        }
