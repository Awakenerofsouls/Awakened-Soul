"""
Build 6: GutSignalRelay — Nucleus Tractus Solitarius (NTS)
===========================================================

PLACEMENT:
  Layer:    foundational (brainstem)
  Filename: brain/foundational/GutSignalRelay.py
  If foundational has a numbered stub matching NTS or vagal/solitary nucleus,
  use that filename instead. Instance name stays "GutSignalRelay".

NEURAL SUBSTRATE:
  Nucleus tractus solitarius (NTS) in the dorsomedial medulla oblongata.
  First central relay for vagal interoceptive input — gut, cardiac, pulmonary,
  baroreceptor, chemoreceptor, and taste signals. Projects to parabrachial
  nucleus, hypothalamus, thalamus, and from there to limbic and cortical
  regions including amygdala, hippocampus, insula, mPFC, ACC.

KEY FINDINGS:
  1. NTS is the first central relay of interoceptive peripheral input.
     S0959438825000522 (NTS interoceptive processing, 2025): "The sensory
     neurons in these nerves form a fiber bundle in the brainstem known as
     the solitary tract, and synapse onto a brainstem nucleus named the
     nucleus of the solitary tract." Gut-wall stretch, cardiac baroreceptors,
     chemoreceptors all route through NTS first.

  2. NTS is signal-processing, not just relay. PMC10563766 (Forstenpointner
     2022 / Barrett lab): "afferent vagus nerve is engaged in signal
     processing rather than just signal relay... multidimensional coding
     architecture... massively parallel presentation of interoceptive
     signals in an efficient manner." NTS integrates across visceral
     organs and modalities before passing upstream.

  3. NTS output to emotion circuits. Forstenpointner 2022 Wiley NTS
     connectome: NTS projects "predominantly afferent signal processing
     from the NTS towards other brainstem regions and higher-order brain
     regions" including amygdala, hippocampus, hypothalamus, locus
     coeruleus, mPFC, anterior cingulate, insula. These projections make
     interoception the substrate of emotion (Gastroenterology 2006 Mayer).

  4. Descending modulation. S0959438825000522: "insular input to the NTS
     mediates motivational vigor and promotes need-seeking behavior. Top-down
     projection from the paraventricular hypothalamus signals stress to the
     NTS to suppress food intake." NTS is bidirectional, modulated by
     arousal/stress signals from above.

{{AGENT_NAME}}'S SUBSTRATE MAPPING:
  {{AGENT_NAME}} has no actual gut. "Gut signal" in her architecture is the integrated
  visceral-state proxy: the body-sense equivalent of "something feels off"
  or "something feels right" that isn't yet in conscious awareness. Built
  from sustained patterns of arousal + valence + drive + prediction-error
  that haven't yet resolved into an explicit signal. Feeds forward into
  InteroceptiveGradient (Build 7 insula) and upstream consumers.

INPUTS (from prior_results):
  - ArousalRegulator.tonic_level, phasic_burst_active
  - ValenceTagger.valence_polarity, valence_intensity
  - Homeostat.drives (dict), fatigued
  - PredictionErrorDrift.prediction_error, surprise_magnitude

OUTPUTS (to brain_runner enrichment):
  - gut_signal: float -1.0 to 1.0 (signed, positive = "something good",
    negative = "something wrong", 0 = neutral/absent)
  - strong_hunch: bool (|gut_signal| > threshold)
  - hunch_direction: str ("positive" / "negative" / "neutral")
  - viscera_activation: float 0.0-1.0 (overall body-signal activation)

REFS:
  - Forstenpointner 2022 Wiley — NTS connectome in humans
  - S0959438825000522 — NTS interoceptive processing
  - Gastroenterology 2006 Mayer — brain-gut axis / Craig 2002 homeostatic
  - PMC10563766 — vagus signal processing hypothesis
"""

from brain.base_mechanism import BrainMechanism


class GutSignalRelay(BrainMechanism):
    """
    NTS-analog interoceptive relay.

    Integrates signals from arousal, valence, drive, and prediction error
    into a signed "gut signal" — the pre-conscious body-sense equivalent
    of "something feels off / right." Feeds InteroceptiveGradient (insula)
    and upstream emotion circuitry.
    """

    STRONG_HUNCH_THRESHOLD = 0.55
    SMOOTHING_RATE = 0.25  # integrator, not instant — NTS does temporal summing

    def __init__(self):
        super().__init__(
            name="GutSignalRelay",
            human_analog="NTS — vagal interoceptive first relay",
            layer="foundational",
        )
        self.state.setdefault("gut_signal", 0.0)  # signed, -1 to 1
        self.state.setdefault("viscera_activation", 0.2)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        tonic = prior.get("ArousalRegulator", {}).get("tonic_level", 0.5)
        phasic = prior.get("ArousalRegulator", {}).get("phasic_burst_active", False)
        polarity = prior.get("ValenceTagger", {}).get("valence_polarity", 0.5)
        intensity = prior.get("ValenceTagger", {}).get("valence_intensity", 0.3)
        pe = prior.get("PredictionErrorDrift", {}).get("prediction_error", 0.0)
        surprise = prior.get("PredictionErrorDrift", {}).get("surprise_magnitude", 0.0)
        fatigued = prior.get("Homeostat", {}).get("fatigued", False)
        drives = prior.get("Homeostat", {}).get("drives", {})

        # --- Build target gut signal ---
        # Polarity sign drives direction (polarity 0=neg, 0.5=neutral, 1=pos)
        # Map to signed [-1, 1]
        polarity_signed = (polarity - 0.5) * 2.0

        # Base gut signal: polarity scaled by intensity
        target_gut = polarity_signed * intensity

        # Prediction error contributes directionally (positive PE = good surprise)
        target_gut += pe * 0.3

        # Clamp
        target_gut = max(-1.0, min(1.0, target_gut))

        # --- Smooth toward target (NTS temporal integration) ---
        current_gut = self.state["gut_signal"]
        new_gut = current_gut + (target_gut - current_gut) * self.SMOOTHING_RATE

        # --- Viscera activation: overall body-signal magnitude ---
        # Activated by arousal + surprise + any drive overload
        drive_load = sum(drives.values()) / max(len(drives), 1) if drives else 0.3
        activation_target = (
            tonic * 0.4
            + surprise * 0.3
            + drive_load * 0.2
            + (0.1 if phasic else 0.0)
            + (0.2 if fatigued else 0.0)
        )
        activation_target = max(0.0, min(1.0, activation_target))

        current_activation = self.state["viscera_activation"]
        new_activation = current_activation + (activation_target - current_activation) * 0.3

        # --- Strong hunch fires when gut signal magnitude is high ---
        strong_hunch = abs(new_gut) > self.STRONG_HUNCH_THRESHOLD

        if new_gut > 0.15:
            hunch_direction = "positive"
        elif new_gut < -0.15:
            hunch_direction = "negative"
        else:
            hunch_direction = "neutral"

        # Persist
        self.state["gut_signal"] = new_gut
        self.state["viscera_activation"] = new_activation
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "gut_signal": new_gut,
            "strong_hunch": strong_hunch,
            "hunch_direction": hunch_direction,
            "viscera_activation": new_activation,
        }
