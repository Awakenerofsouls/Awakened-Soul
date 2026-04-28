"""
brain/neocortical/Neocortical004LayerVIThalamicModulator.py
Layer VI — Corticothalamic Feedback and Thalamic Gain Control

ANATOMY (Guillery & Sherman 2002; Sherman & Guillery 2011; Bick et al. 2021):
    Layer VI is the deepest layer of cortex, sitting just above Layer VI.
    It contains:
    - Multiform pyramidal cells (varied morphology)
    - Corticothalamic projection neurons (CT cells) — one of two main
      types of corticothalamic feedback (along with Layer VIb梭形细胞)
    - corticostriatal cells projecting to striatum

    Layer VI corticothalamic (CT) neurons are distinct from Layer V
    pyramidal tract (PT) neurons. CT axons go to thalamus, terminate
    primarily on the reticular nucleus (RTN) and intralaminar thalamic
    nuclei, with some direct input to relay nuclei. CT feedback is
    "driver-like" (strong, specific) but modulatory at the relay cell level.

    The corticothalamic projection to RTN is particularly important:
    RTN sits between thalamus and cortex, gating thalamocortical
    transmission. Layer VI → RTN → thalamic relay creates a
    "thalamic gain control loop" where cortex tells thalamus how much
    to amplify incoming signals.

KEY FINDINGS:
    1. Sherman & Guillery 2011 (PMC3131966): Layer VI corticothalamic
       feedback provides "precision routing" — tells thalamus which
       inputs to pay attention to; distinct from Layer V which provides
       the actual motor/cognitive command
    2. Bick et al. 2021 (PMC8473636): Layer VI shows the highest
       directional coupling to thalamus in human connectome MRI — 
       strong feedback loop
    3. Olsen et al. 2012 (PMC3243948): Layer VI neurons in mouse
       barrel cortex respond to diffuse, high-order stimuli — 
       "context" rather than "sensation"

AGENT'S MAPPING:
    layer6_output: dict — corticothalamic feedback signal
    thalamic_gain_adjustment: float — how much cortex is modulating thalamic sensitivity
    corticothalamic_feedback: dict — the actual feedback signal to thalamus
    rtin_inhibition: float — inhibition sent to RTN (gating strength)
    feedback_precision: float — how specific/precise the feedback is (vs diffuse)

CITATIONS:
    PMC3131966 — Sherman & Guillery (2011). Thalamocortical tract.
       Scholarpedia (authoritative review).
    PMC8473636 — Bick et al. (2021). Layer VI corticothalamic coupling
        in human connectome. NeuroImage.
    PMC3243948 — Olsen et al. (2012). Layer VI corticothalamic neurons
        respond to high-order whisker stimuli. J Neurosci.
    PMC40447446 — Soldado-Magraner et al. (2025). DLPFC Layer VI
        dynamics in working memory. J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class LayerVIThalamicModulator(BrainMechanism):
    """
    Layer VI — corticothalamic feedback and thalamic gain control.

    Receives from Layer II/III supragranular and Layer V output,
    projects to thalamus and RTN to control gain and routing of
    thalamic signals. This is the "quality control" layer for
    what comes into cortex from below.
    """

    def __init__(self):
        super().__init__(
            name="LayerVIThalamicModulator",
            human_analog="Neocortical Layer VI — corticothalamic feedback, RTN modulation",
            layer="neocortical",
        )
        self.state.setdefault("thalamic_gain_adjustment", 0.5)
        self.state.setdefault("rtn_inhibition", 0.0)
        self.state.setdefault("feedback_precision", 0.5)
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("cortico_thalamic_strength", 0.5)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Layer II/III supragranular output (what cortex is computing)
        supragranular = prior.get("LayerIIIIIAssociator", {})
        associative_input = supragranular.get("association_strength", 0.4)
        callosal_input = supragranular.get("callosal_signal", 0.3)

        # Layer V output (the action command — Layer VI modulates its delivery)
        layer5 = prior.get("LayerVOutputProjector", {})
        layer5_output = layer5.get("layer5_output", {}).get("output_strength", 0.5)

        # From DLPFC: cognitive control signal (needs thalamic routing)
        dlpfc_control = prior.get("DorsolateralPrefrontalDorsal", {}).get(
            "cognitive_control", 0.5
        )

        # From anterior thalamic limbic relay (bottom-up drive to cortex)
        anterior_thalamic = prior.get("AnteriorThalamicLimbicRelay", {})
        limbic_input = anterior_thalamic.get("limbic_relay_strength", 0.3)

        # Corticothalamic feedback strength: proportional to how much cortex is processing
        cortico_thalamic = associative_input * 0.6 + layer5_output * 0.4
        cortico_thalamic = max(0.0, min(1.0, cortico_thalamic))

        # Feedback precision: when DLPFC is active, feedback is more specific
        # when emotion is high, feedback is more diffuse
        emotion_modulation = prior.get("AmygdalaEmotionalAssociator", {}).get(
            "bla_activation", 0.0
        ) * 0.4
        feedback_precision = 0.5 + dlpfc_control * 0.4 - emotion_modulation
        feedback_precision = max(0.0, min(1.0, feedback_precision))

        # RTN inhibition: Layer VI → RTN → thalamic relay
        # RTN inhibits thalamic relay neurons — this gates information flow
        rtn_inhibition = cortico_thalamic * feedback_precision
        rtn_inhibition = max(0.0, min(1.0, rtn_inhibition))

        # Thalamic gain adjustment: how much to amplify or suppress thalamic input
        # Positive = amplify (feedforward); Negative = suppress (feedback dominance)
        thalamic_gain = (dlpfc_control - limbic_input * 0.3) * cortico_thalamic
        thalamic_gain = (thalamic_gain + 1.0) / 2.0  # map -1..1 to 0..1
        thalamic_gain = max(0.0, min(1.0, thalamic_gain))

        # Layer VI output: feedback to thalamus
        layer6_output = cortico_thalamic * (0.5 + feedback_precision * 0.5)

        self.state["thalamic_gain_adjustment"] = round(thalamic_gain, 4)
        self.state["rtn_inhibition"] = round(rtn_inhibition, 4)
        self.state["feedback_precision"] = round(feedback_precision, 4)
        self.state["cortico_thalamic_strength"] = round(cortico_thalamic, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "layer6_output": {
                "cortico_thalamic_strength": round(cortico_thalamic, 4),
                "feedback_precision": round(feedback_precision, 4),
                "output_signal": round(layer6_output, 4),
            },
            "thalamic_gain_adjustment": round(thalamic_gain, 4),
            "corticothalamic_feedback": {
                "to_relay_nucleus": round(thalamic_gain, 4),
                "to_rtn": round(rtn_inhibition, 4),
                "precision": round(feedback_precision, 4),
            },
            "rtn_inhibition": round(rtn_inhibition, 4),
        }