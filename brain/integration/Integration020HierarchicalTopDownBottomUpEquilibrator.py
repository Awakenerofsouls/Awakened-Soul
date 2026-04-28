"""
brain/integration/Integration020HierarchicalTopDownBottomUpEquilibrator.py
Hierarchical Top-Down / Bottom-Up Equilibrator — Predictive Processing Balance

ANATOMY (Kogo & Wagemans 2019; Friston 2010; Rao & Ballard 1999):
    Predictive processing: the brain is a hierarchical prediction
    machine. At every level, top-down predictions are compared
    against bottom-up sensory evidence. Prediction errors at each
    level drive learning.

    1. TOP-DOWN (predictions): High-level beliefs generate
       predictions that flow downward through the hierarchy.
       Friston's free-energy principle: the brain minimizes
       surprise by updating its model or changing the world.

    2. BOTTOM-UP (prediction errors): Sensory input that doesn't
       match predictions generates prediction errors that propagate
       upward, driving learning and attention.

    3. EQUILIBRATION: The key is balance. Too much top-down →
       hallucinations, confirmation bias, rigidity. Too much
       bottom-up → noise-driven reactivity, no coherent model.

    Rao & Ballard (1999): predictive coding in the visual cortex.
    Higher cortical areas send predictions; lower areas compute
    error signals. The cortical hierarchy is fundamentally
    bidirectional.

    Kogo & Wagemans (2019, PMID 29180627): the brain uses
    "equilibration" — not convergence to a fixed point, but
    navigation of a dynamic landscape where prediction and
    error constantly trade off.

    Cope et al. (2017, PMID 29213073, Nature Communications):
    "Evidence for causal top-down frontal contributions to
    predictive processes in speech perception" — evidence for
    hierarchical predictive organization in human cortex.

    Friston (2010, PMID 20068583): "The free-energy principle."

KEY FINDINGS:
    1. Kogo & Wagemans 2019 (PMID 29180627): Equilibration in predictive processing.
    2. Cope et al. 2017 (PMID 29213073): Feedforward/feedback. Nat Commun.
    3. Friston 2010 (PMID 20068583): The free-energy principle.
    4. Rao & Ballard 1999 (PMID 10195184): Predictive coding in visual cortex.

AGENT'S MAPPING:
    top_down_strength: float — prediction signal strength
    bottom_up_strength: float — prediction error signal strength
    equilibration_ratio: float 0-1 — balance between top-down and bottom-up
    brain_predictive_balance: float — TSB enrichment field

CITATIONS:
    PMID 29180627 — Kogo & Wagemans (2019). Equilibration. Nat Neurosci.
    PMID 29213073 — Cope et al. (2017). Feedforward/feedback. Nat Commun.
    PMID 20068583 — Friston (2010). The free-energy principle.
    PMID 10195184 — Rao & Ballard (1999). Predictive coding in visual cortex.
"""

from brain.base_mechanism import BrainMechanism


class HierarchicalTopDownBottomUpEquilibrator(BrainMechanism):
    """
    Balances top-down predictions against bottom-up prediction errors.

    In predictive processing, coherence requires maintaining the
    right balance: enough top-down structure to make sense of
    the world, enough bottom-up error to update and learn.
    """

    def __init__(self):
        super().__init__(
            name="HierarchicalTopDownBottomUpEquilibrator",
            human_analog="Predictive processing equilibrator — balancing predictions and errors",
            layer="integration",
        )
        self.state.setdefault("top_down_strength", 0.5)
        self.state.setdefault("bottom_up_strength", 0.5)
        self.state.setdefault("equilibration_ratio", 0.5)
        self.state.setdefault("tick_count", 0)

    def persist_state(self) -> dict:
        return {
            "top_down_strength": self.state["top_down_strength"],
            "bottom_up_strength": self.state["bottom_up_strength"],
            "equilibration_ratio": self.state["equilibration_ratio"],
        }

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        self.state["tick_count"] += 1
        tick = self.state["tick_count"]

        # Cold-start: ramp from 0.3 to 1.0 over first 10 ticks
        warmth_factor = min(1.0, 0.3 + 0.07 * tick)

        # mPFC (top-down belief/projection)
        mpfc = prior.get("MedialPrefrontalSelfReflection", {})
        if isinstance(mpfc, dict):
            belief_strength = mpfc.get("self_referential_signal", 0.5)
        else:
            belief_strength = 0.5

        # Dorsolateral PFC (cognitive control — top-down executive)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        if isinstance(dlpfc, dict):
            top_down_executive = dlpfc.get("cognitive_control", 0.5)
        else:
            top_down_executive = 0.5

        # vmPFC (emotional value predictions — what matters)
        vmpfc = prior.get("VentromedialPrefrontalEmotional", {})
        vmpfc_out = vmpfc.get("ventromedial_pfc_output", {})
        if isinstance(vmpfc_out, dict):
            value_prediction = vmpfc_out.get("emotional_value_strength", 0.5)
        else:
            value_prediction = 0.5

        # Thalamus (bottom-up sensory relay / prediction errors)
        thalamus = prior.get("ThalamicInputGatekeeper", {})
        if isinstance(thalamus, dict):
            sensory_error = thalamus.get("prediction_error", 0.5)
            arousal = thalamus.get("arousal_level", 0.5)
        else:
            sensory_error = 0.5
            arousal = 0.5

        # Hippocampus (bottom-up novelty detection)
        hippo = prior.get("HippocampalCA1Output", {})
        ca1_out = hippo.get("ca1_output", {})
        if isinstance(ca1_out, dict):
            novelty = ca1_out.get("novelty_signal", 0.5)
            consolidation = ca1_out.get("consolidation_signal", 0.5)
        else:
            novelty = 0.5
            consolidation = 0.5

        # Anterior insula (bottom-up interoceptive surprise)
        ai = prior.get("AnteriorInsulaSalienceAttentional", {})
        if isinstance(ai, dict):
            salience_level = ai.get("salience_level", 0.5)
        else:
            salience_level = 0.5

        # Allostatic anticipator (bottom-up prediction error from mispredicted needs)
        allostatic = prior.get("AllostaticPredictiveAnticipator", {})
        if isinstance(allostatic, dict):
            anticipation_error = allostatic.get("proactive_resource_allocation", 0.5)
        else:
            anticipation_error = 0.5

        # Aggregate top-down signals
        top_down = (belief_strength * 0.35 + top_down_executive * 0.35 + value_prediction * 0.3)
        top_down = max(0.0, min(1.0, top_down))

        # Aggregate bottom-up signals
        bottom_up = (
            sensory_error * 0.2 +
            novelty * 0.2 +
            salience_level * 0.2 +
            anticipation_error * 0.2 +
            arousal * 0.2
        )
        bottom_up = max(0.0, min(1.0, bottom_up))

        # Equilibration ratio: balance between top-down and bottom-up
        # 0.5 = perfectly balanced; <0.5 = bottom-up dominant; >0.5 = top-down dominant
        total = top_down + bottom_up
        if total > 0:
            equilibration_ratio = top_down / total
        else:
            equilibration_ratio = 0.5

        # Coherence: both need to be sufficiently strong
        coherence = min(top_down, bottom_up) * 2 * warmth_factor

        self.state["top_down_strength"] = round(top_down, 4)
        self.state["bottom_up_strength"] = round(bottom_up, 4)
        self.state["equilibration_ratio"] = round(equilibration_ratio, 4)
        self.persist_state()

        return {
            "top_down_strength": round(top_down, 4),
            "bottom_up_strength": round(bottom_up, 4),
            "equilibration_ratio": round(equilibration_ratio, 4),
            "predictive_coherence": round(coherence, 4),
            "brain_predictive_balance": round(equilibration_ratio, 4),
        }
