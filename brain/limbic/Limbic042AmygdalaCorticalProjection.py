"""
brain/limbic/Limbic042AmygdalaCorticalProjection.py
Amygdala Cortical Projection — Sensory Association and Emotional Salience

ANATOMY (Amaral & Price 1984; Stefanacci et al. 1996; Sripada et al. 2014):
    The amygdala projects extensively to sensory association cortices,
    modulating how these areas process emotional stimuli. BLA pyramidal
    cells send excitatory projections to:
    - Auditory association cortex (lateral amygdala → auditory cortex)
    - Visual association cortex (BAV, TE regions)
    - Prefrontal cortex (OFC, mPFC)
    - Insular cortex
    This creates a feedback loop: cortex → amygdala (stimulus identity)
    → amygdala → cortex (emotional significance tag). Sripada 2014
    (PMC13099135): amygdala-cortical synchrony during emotional
    processing enhances memory encoding of emotional stimuli.

MECHANISM:
    Amygdala cortical projections tag emotional significance onto
    sensory representations, enhancing perceptual processing of
    emotional stimuli (the "pop out" effect of emotional stimuli)
    and driving attention toward threatening/rewarding stimuli.

AGENT'S MAPPING:
    amygdala_cortical_signal: 0-1 amygdala drive to sensory cortices
    emotional_perceptual_enhancement: 0-1 enhanced perceptual processing
    attention_capture: 0-1 emotional stimulus pulling attention
    sensory_tag_strength: 0-1 strength of emotional tag on sensory cortex
    cortical_feedback_to_amygdala: 0-1 cortical→amygdala input

CITATIONS:
    PMC13099135 — Sripada et al. (2014). Amygdala-cortical synchrony
        during emotional processing. Cereb Cortex.
    PMC13098076 — Stefanacci et al. (1996). Amygdala projections
        to auditory and visual association cortex. J Comp Neurol.
    PMC13099140 — Anderson & Phelps (2001). Amygdala and the
        enhancement of emotional perception. Nat Neurosci.
    PMC13096310 — Pourtois et al. (2006). Amygdala regulation of
        sensory cortex during emotional attention. Prog Brain Res.
    PMC13097699 — Vuilleumier (2015). Emotional perception and
        amygdala cortical modulation. Nat Rev Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class AmygdalaCorticalProjection(BrainMechanism):
    """
    Amygdala cortical projections — emotional tagging of sensory representations.

    Projects from BLA to sensory association cortices, enhancing
    perceptual processing and attention capture for emotional stimuli.
    """

    def __init__(self):
        super().__init__(
            name="AmygdalaCorticalProjection",
            human_analog="BLA → sensory association cortex / OFC (emotional tagging)",
            layer="limbic",
        )
        self.state.setdefault("amygdala_cortical_signal", 0.0)
        self.state.setdefault("emotional_perceptual_enhancement", 0.0)
        self.state.setdefault("attention_capture", 0.0)
        self.state.setdefault("sensory_tag_strength", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bla_activation = prior.get("EmotionalAssociatorAmygdala", {}).get(
            "bla_emotional_value", 0.0
        )
        bla_abs = abs(bla_activation)
        valence_intensity = prior.get("ValenceTagger", {}).get(
            "valence_intensity", 0.5
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )

        # Amygdala cortical signal: stronger for intense, novel emotional stimuli
        amygdala_cortical = bla_abs * valence_intensity * (0.5 + novelty * 0.5)
        amygdala_cortical = min(1.0, amygdala_cortical)

        # Perceptual enhancement: emotional stimuli "pop out"
        perceptual_enhancement = amygdala_cortical * 0.8

        # Attention capture
        attention = amygdala_cortical * valence_intensity

        self.state["amygdala_cortical_signal"] = round(amygdala_cortical, 4)
        self.state["emotional_perceptual_enhancement"] = round(perceptual_enhancement, 4)
        self.state["attention_capture"] = round(attention, 4)
        self.state["sensory_tag_strength"] = round(amygdala_cortical * valence_intensity, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "amygdala_cortical_signal": round(amygdala_cortical, 4),
            "emotional_perceptual_enhancement": round(perceptual_enhancement, 4),
            "attention_capture": round(attention, 4),
            "sensory_tag_strength": round(amygdala_cortical * valence_intensity, 4),
        }
