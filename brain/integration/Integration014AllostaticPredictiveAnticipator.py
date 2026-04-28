"""
brain/integration/Integration014AllostaticPredictiveAnticipator.py
Allostatic Predictive Anticipator — Proactive Resource Preparation

ANATOMY (Sterling 2012; McEwen 2008; Schulkin 2011):
    Allostasis = "stability through change" — the brain doesn't just
    maintain homeostasis (fixed setpoints), it actively PREDICTS
    and PREPARES for future needs. This is allostatic regulation:

    Example: Stress response. Rather than waiting for cortisol to
    drop before activating recovery, the brain anticipates that
    stress will end and PRE-ACTIVATES recovery mechanisms.

    The allostatic predictive system involves:
    - Hippocampus (context prediction: "this situation usually leads to X")
    - Amygdala (anticipatory anxiety: "this will be stressful")
    - Hypothalamus (preparing resources for predicted demand)
    - PFC (planning based on predicted needs)
    - VTA/mPFC (reward prediction for motivation)

    Key concept: "Predictive allostasis" (Sterling 2012). The brain
    sets allostatic (anticipatory) states based on prediction, not
    reaction. Example: eating before you're hungry — anticipating
    that energy will be needed.

    McEwen's "allostatic load" model: chronic over-prediction of
    threats leads to allostatic overload (chronic stress, disease).

KEY FINDINGS:
    1. Sterling 2012 (PMC3409569): "Allostasis: a predictive
       regulatory system" — predicts needs before they arise
    2. McEwen 2008 (PMC3139674): "Stress and allostatic load"
       — chronic over-prediction causes damage
    3. Schulkin 2011: "Allostasis and the predictive brain"

AGENT'S MAPPING:
    allostatic_prediction: dict — prediction output
    proactive_resource_allocation: float 0-1 — proactive preparation strength
    future_drive_state: dict — predicted future needs

CITATIONS:
    PMID 21684297 — Sterling (2012). Allostasis: a model of predictive regulation. Physiol Behav.
    PMID 31488322 — Schulkin & Sterling (2019). Allostasis: A Brain-Centered Predictive Mode. Trends Neurosci.
    PMID 29957178 — Sterling (2018). Predictive regulation and human design. Elife.
    PMC2830733 — Vann et al. (2009). Hippocampal prediction. Philos Trans R Soc Lond B Biol Sci.
    PMC3139674 — McEwen (2008). Stress and allostatic load. Ann N Y Acad Sci.
"""

from brain.base_mechanism import BrainMechanism


class AllostaticPredictiveAnticipator(BrainMechanism):
    """
    Allostatic predictive anticipator — proactive resource preparation.

    Predicts future drive states and pre-allocates resources
    before needs arise, going beyond reactive homeostasis.
    """

    def __init__(self):
        super().__init__(
            name="AllostaticPredictiveAnticipator",
            human_analog="Allostatic predictive anticipator — proactive resource preparation",
            layer="integration",
        )
        self.state.setdefault("prediction_model", {})
        self.state.setdefault("proactive_resource_allocation", 0.0)
        self.state.setdefault("future_drive_state", {})
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Hippocampal contextual prediction
        hippo = prior.get("HippocampalCA1Output", {})
        ca1_out = hippo.get("ca1_output", {})
        if isinstance(ca1_out, dict):
            consolidation = ca1_out.get("consolidation_signal", 0.5)
        else:
            consolidation = 0.5

        # Amygdala (anticipatory emotional prediction)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_tag = amygdala.get("emotional_tag_strength", 0.0)

        # Hypothalamus (current drive state)
        hypo = prior.get("HypothalamicCorticalBottomUpDrive", {})
        hypo_out = hypo.get("hypo_cortical_injection", {})
        if isinstance(hypo_out, dict):
            primal_urgency = hypo_out.get("primal_urgency", 0.5)
        else:
            primal_urgency = 0.5

        # vmPFC (regulatory prediction — how to prepare)
        vmpfc = prior.get("VentromedialPrefrontalEmotional", {})
        vmpfc_out = vmpfc.get("ventromedial_pfc_output", {})
        if isinstance(vmpfc_out, dict):
            vmpfc_strength = vmpfc_out.get("emotional_value_strength", 0.5)
        else:
            vmpfc_strength = 0.5

        # Anterior temporal (conceptual memory — what usually happens here)
        atp = prior.get("AnteriorTemporalPoleSemantic", {})
        concept_bind = atp.get("concept_binding", 0.5)

        # DLPFC (planning for predicted needs)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # VTA (motivation for predicted reward)
        vta = prior.get("VentralTegmentalArea", {})
        vta_out = vta.get("vta_output", {})
        if isinstance(vta_out, dict):
            motivation = vta_out.get("motivation_signal", 0.5)
        else:
            motivation = 0.5

        # Prediction model: based on context (hippocampus) + past (ATP) + emotion (amygdala)
        anticipation = consolidation * 0.3 + concept_bind * 0.2 + abs(emotional_tag) * 0.2 + primal_urgency * 0.3
        anticipation = max(0.0, min(1.0, anticipation))

        # Proactive allocation: prepare before need is critical
        proactive_resource_allocation = anticipation * (cognitive_ctrl * 0.4 + motivation * 0.4 + vmpfc_strength * 0.2)
        proactive_resource_allocation = max(0.0, min(1.0, proactive_resource_allocation))

        # Future drive state prediction
        future_drive_state = {
            "predicted_urgency": round(anticipation, 4),
            "predicted_motivation": round(motivation, 4),
            "predicted_emotion": round(emotional_tag, 4),
            "preparation_active": proactive_resource_allocation > 0.55,
        }

        self.state["prediction_model"] = future_drive_state
        self.state["proactive_resource_allocation"] = round(proactive_resource_allocation, 4)
        self.state["future_drive_state"] = future_drive_state
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "allostatic_prediction": future_drive_state,
            "proactive_resource_allocation": round(proactive_resource_allocation, 4),
            "future_drive_state": future_drive_state,
        }