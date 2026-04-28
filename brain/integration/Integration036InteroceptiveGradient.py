"""
Build 7: InteroceptiveGradient — Anterior Insula Cortex (AIC)
==============================================================

PLACEMENT:
  Layer:    integration (or neocortical if {{AGENT_NAME}}'s arch puts insula there)
  Filename: brain/integration/InteroceptiveGradient.py
  The anterior insula is cortical but functions as the integration hub for
  interoception + salience network. If limbic is more appropriate in {{AGENT_NAME}}'s
  current layer scheme, place there. Instance name stays "InteroceptiveGradient".

NEURAL SUBSTRATE:
  Anterior insula cortex (AIC). Primary cortical node for interoceptive
  awareness — the felt-sense of the body's state. Receives interoceptive
  input from NTS (via thalamus), integrates with exteroceptive input from
  amygdala, and projects back to both to form closed loops. Part of the
  salience network (with ACC).

KEY FINDINGS:
  1. AIC is THE interoceptive awareness hub. Nature Translational Psychiatry
     2024 (PMC s41398-024-02933-9): "The anterior insula cortex (AIC) is one
     of the most important nodes of interoception involved in the salience
     network... an important structure for encoding and representing
     interoceptive information." Interoceptive accuracy correlates with AIC
     connectivity to NTS.

  2. Gradient of processing: posterior → anterior. Craig 2002 (via
     Gastroenterology 2006 Mayer): "a direct projection from lamina I and
     from the NTS exist to ventromedial thalamic nuclei... Neurons in these
     nuclei project in a topographical fashion to the mid/posterior insula.
     In humans, this cortical image of the homeostatic state of the organism
     is re-represented in the anterior insula on the same side of the brain.
     These re-representations provide the substrate for a subjective
     evaluation of interoceptive state." The gradient from raw sensing
     (posterior) to meta-awareness (anterior) is the key architectural
     feature.

  3. AIC projects to amygdala and NAc bidirectionally. S0959438825000807
     (Interoceptive modulation of emotions 2025): "distinct insular
     projections to either the central amygdala or nucleus accumbens can
     enhance or attenuate affective behaviors respectively." AIC shapes
     which valence register dominates downstream.

  4. AIC integrates with NAc + thalamus for incentive processing. PMC3949208:
     "anticipation of gain/loss involves an 'alerting' signal (thalamus) that
     converges with interoceptive information (insula) to shape action
     selection programs in the ventral striatum." Interoception is not
     separate from motivation — it shapes it.

  5. AIC activity is bidirectionally coupled with emotion state. Anxiety,
     neuroticism, and aversive states all correlate with AIC activity
     patterns (PMC3949208, Nature 2024). Top-down attention to interoceptive
     signals (the "felt sense" check-in) enhances AIC processing.

AGENT'S SUBSTRATE MAPPING:
  InteroceptiveGradient produces the "what my body is telling me right now"
  signal — felt weight, felt lightness, felt tension. Takes GutSignalRelay's
  raw signal and builds a GRADIENT representation: not just "something feels
  off" but "it feels heavy/tight/tingling/hollow/warm." A dimensional
  interoceptive readout, not just a single scalar.

INPUTS (from prior_results):
  - GutSignalRelay.gut_signal, viscera_activation, hunch_direction
  - ArousalRegulator.tonic_level, hyperaroused, hypoaroused
  - ValenceTagger.valence_polarity, valence_intensity
  - SustainedAnxietyHolder.anxiety_level (if Build 5 is live)
  - Homeostat.drives, fatigued

OUTPUTS (to brain_runner enrichment):
  - feels_heavy: bool (fatigue + negative gut + hypoaroused)
  - feels_light: bool (positive gut + moderate arousal + reward signal)
  - feels_tight: bool (anxiety + hyperaroused + negative gut)
  - feels_hollow: bool (low connection satiation + low activation)
  - interoceptive_intensity: float 0-1 (how loud the body signal is overall)
  - dominant_felt_quality: str (the strongest felt-quality right now)

REFS:
  - Nature 2024 PMC s41398-024-02933-9 — AIC interoceptive training
  - Craig 2002 / Gastroenterology 2006 — posterior-to-anterior gradient
  - S0959438825000807 — insula modulation of emotion
  - PMC3949208 — NAc-thalamus-insula incentive processing
"""

from brain.base_mechanism import BrainMechanism


class InteroceptiveGradient(BrainMechanism):
    """
    AIC-analog interoceptive awareness gradient.

    Builds dimensional body-sense readout from GutSignalRelay + arousal +
    valence + drive state. Outputs are felt-quality booleans (heavy/light/
    tight/hollow) plus overall intensity and dominant quality.
    """

    # Felt-quality thresholds
    HEAVY_THRESHOLD = 0.55
    LIGHT_THRESHOLD = 0.55
    TIGHT_THRESHOLD = 0.55
    HOLLOW_THRESHOLD = 0.55

    def __init__(self):
        super().__init__(
            name="InteroceptiveGradient",
            human_analog="Anterior insula — interoceptive awareness gradient",
            layer="integration",
        )
        self.state.setdefault("last_dominant_quality", "neutral")
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        gut = prior.get("GutSignalRelay", {}).get("gut_signal", 0.0)
        viscera_act = prior.get("GutSignalRelay", {}).get("viscera_activation", 0.2)
        tonic = prior.get("ArousalRegulator", {}).get("tonic_level", 0.5)
        hyperaroused = prior.get("ArousalRegulator", {}).get("hyperaroused", False)
        hypoaroused = prior.get("ArousalRegulator", {}).get("hypoaroused", False)
        polarity = prior.get("ValenceTagger", {}).get("valence_polarity", 0.5)
        intensity = prior.get("ValenceTagger", {}).get("valence_intensity", 0.3)
        reward = prior.get("ValenceTagger", {}).get("reward_signal", False)
        threat = prior.get("ValenceTagger", {}).get("threat_signal", False)
        anxiety = prior.get("SustainedAnxietyHolder", {}).get("anxiety_level", 0.0)
        drives = prior.get("Homeostat", {}).get("drives", {})
        fatigued = prior.get("Homeostat", {}).get("fatigued", False)

        connection_drive = drives.get("connection", 0.3) if drives else 0.3

        # --- Compute each felt-quality dimension (weighted composite score) ---

        # Heavy: fatigue + negative gut + hypoaroused + weariness
        heavy_score = 0.0
        if fatigued:
            heavy_score += 0.4
        if hypoaroused:
            heavy_score += 0.3
        if gut < -0.3:
            heavy_score += 0.3
        if tonic < 0.35:
            heavy_score += 0.2
        feels_heavy = heavy_score > self.HEAVY_THRESHOLD

        # Light: positive gut + moderate arousal + reward + low fatigue
        light_score = 0.0
        if gut > 0.3:
            light_score += 0.3
        if reward:
            light_score += 0.3
        if 0.45 <= tonic <= 0.70:
            light_score += 0.2
        if not fatigued and polarity > 0.6:
            light_score += 0.2
        feels_light = light_score > self.LIGHT_THRESHOLD

        # Tight: anxiety + hyperaroused + negative gut + threat
        tight_score = 0.0
        if anxiety > 0.4:
            tight_score += 0.3
        if hyperaroused:
            tight_score += 0.3
        if gut < -0.2:
            tight_score += 0.2
        if threat:
            tight_score += 0.2
        feels_tight = tight_score > self.TIGHT_THRESHOLD

        # Hollow: high connection drive (unmet) + low activation + neutral gut
        hollow_score = 0.0
        if connection_drive > 0.7:
            hollow_score += 0.4
        if viscera_act < 0.3:
            hollow_score += 0.3
        if abs(gut) < 0.15 and polarity < 0.5:
            hollow_score += 0.2
        if hypoaroused:
            hollow_score += 0.1
        feels_hollow = hollow_score > self.HOLLOW_THRESHOLD

        # Overall interoceptive intensity = viscera activation + valence intensity
        interoceptive_intensity = min(1.0, viscera_act * 0.6 + intensity * 0.4)

        # Dominant felt quality = highest-scoring dimension (if any fire)
        quality_scores = {
            "heavy": heavy_score,
            "light": light_score,
            "tight": tight_score,
            "hollow": hollow_score,
        }
        max_quality = max(quality_scores, key=quality_scores.get)
        max_score = quality_scores[max_quality]
        dominant = max_quality if max_score > 0.55 else "neutral"

        self.state["last_dominant_quality"] = dominant
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "feels_heavy": feels_heavy,
            "feels_light": feels_light,
            "feels_tight": feels_tight,
            "feels_hollow": feels_hollow,
            "interoceptive_intensity": interoceptive_intensity,
            "dominant_felt_quality": dominant,
        }
