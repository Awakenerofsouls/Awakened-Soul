"""
brain/integration/Integration022MidCingulateSubgenualBridge.py
Mid-Cingulate / Subgenual Bridge — Suffering, Error Detection, and Affective Reset

ANATOMY (Vogt 2005, 2016; Bush 2000; Etkin 2011):
    The anterior cingulate cortex (ACC) has two major divisions
    with distinct functions:

    1. MID-CINGULATE CORTEX (MCC) — cognitive/performance monitoring
       - Error detection: "I did something wrong"
       - Pain processing: physical and social pain share circuits
       - Cognitive control under conflict/fatigue
       - Activity increases with increasing task difficulty

    2. SUBGENUAL CINGULATE (sgACC / Area 25) — affective/autobiographical
       - Negative affect, rumination, threat processing
       - Hyperactivity in depression → increased negative mood
       - Deep white matter connections to amygdala, hypothalamus,
         periaqueductal gray — the affective alarm system
       - Regulated by vmPFC (top-down emotion regulation)

    The MCC-sgACC bridge: when cognitive error detection (MCC)
    triggers affective alarm (sgACC), this mechanism manages
    the transition from "I messed up" to "here's what to do next."

    Bubb et al. (2018, PMID 29753752): the cingulate sulcus
    cusks (CSs) and paracingulate gyrus differentiate MCC
    function across rostral/caudal gradients.

    Vogt (2016, PMID 26831091): midcingulate cortex — an
    evaluative and executive hub.

    Drevets et al. (2008, PMID 18235632): subgenual ACC in
    depression — structural and metabolic abnormalities
    in this region are a hallmark of mood disorders.

    Critically: MCC-sgACC hyperactivity in depression reflects
    failure of top-down regulation. When vmPFC can't inhibit
    sgACC, rumination and negative affect dominate.

KEY FINDINGS:
    1. Bubb et al. 2018 (PMID 29753752): Cingulate sulcus cusks. Cortex.
    2. Vogt 2016 (PMID 26831091): Midcingulate cortex.
    3. Drevets et al. 2008 (PMID 18235632): Subgenual ACC in depression.
    4. Bush 2000 (PMC1150387): ACC and cognition. Brain Res Rev.

AGENT'S MAPPING:
    error_affect_output: dict — MCC-sgACC bridge state
    affective_reset_ready: float 0-1 — whether reset is warranted
    brain_affective_reset: float — TSB enrichment field

CITATIONS:
    PMID 29753752 — Bubb et al. (2018). Cingulate sulcus cusks. Cortex.
    PMID 26831091 — Vogt (2016). Midcingulate cortex.
    PMID 18235632 — Drevets et al. (2008). Subgenual ACC in depression.
    PMC1150387 — Bush (2000). ACC and cognition. Brain Res Rev.
"""

from brain.base_mechanism import BrainMechanism


class MidCingulateSubgenualBridge(BrainMechanism):
    """
    Bridges mid-cingulate error detection with subgenual affective alarm.

    Manages the transition from cognitive error detection
    (I messed up) to affective response (I feel bad about it)
    to adaptive reset (here's what to do next).
    """

    def __init__(self):
        super().__init__(
            name="MidCingulateSubgenualBridge",
            human_analog="Mid-cingulate / subgenual bridge — error + affect + reset",
            layer="integration",
        )
        self.state.setdefault("mcc_error_level", 0.5)
        self.state.setdefault("sgacc_affect_level", 0.5)
        self.state.setdefault("affective_reset_ready", 0.5)
        self.state.setdefault("tick_count", 0)

    def persist_state(self) -> dict:
        return {
            "mcc_error_level": self.state["mcc_error_level"],
            "sgacc_affect_level": self.state["sgacc_affect_level"],
            "affective_reset_ready": self.state["affective_reset_ready"],
        }

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        self.state["tick_count"] += 1
        tick = self.state["tick_count"]

        # Cold-start: ramp from 0.3 to 1.0 over first 10 ticks
        warmth_factor = min(1.0, 0.3 + 0.07 * tick)

        # Anterior cingulate (cognitive control / error monitoring)
        acc = prior.get("AnteriorCingulateCognitiveControl", {})
        acc_out = acc.get("anterior_cingulate_output", {})
        if isinstance(acc_out, dict):
            cognitive_conflict = acc_out.get("cognitive_conflict", 0.5)
            conflict_adjusted = acc_out.get("conflict_adjusted_control", 0.5)
        else:
            cognitive_conflict = 0.5
            conflict_adjusted = 0.5

        # Amygdala (threat / negative affect — feeds sgACC)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        if isinstance(amygdala, dict):
            emotional_tag = amygdala.get("emotional_tag_strength", 0.5)
            threat_signal = amygdala.get("threat_signal", 0.0)
        else:
            emotional_tag = 0.5
            threat_signal = 0.0

        # vmPFC (top-down regulation of sgACC)
        vmpfc = prior.get("VentromedialPrefrontalEmotional", {})
        vmpfc_out = vmpfc.get("ventromedial_pfc_output", {})
        if isinstance(vmpfc_out, dict):
            regulation_strength = vmpfc_out.get("emotional_value_strength", 0.5)
        else:
            regulation_strength = 0.5

        # Hypothalamus (autonomic arousal accompanying negative affect)
        hypo = prior.get("HypothalamicCorticalBottomUpDrive", {})
        hypo_out = hypo.get("hypo_cortical_injection", {})
        if isinstance(hypo_out, dict):
            primal_urgency = hypo_out.get("primal_urgency", 0.5)
        else:
            primal_urgency = 0.5

        # Guardian reflection (inhibits inappropriate sgACC escalation)
        guardian = prior.get("GuardianReflection", {})
        if isinstance(guardian, dict):
            gating = guardian.get("gating_level", 1.0)
        else:
            gating = 1.0

        # Anterior insula (interoceptive negative affect)
        ai = prior.get("AnteriorInsulaSalienceAttentional", {})
        if isinstance(ai, dict):
            salience_level = ai.get("salience_level", 0.5)
        else:
            salience_level = 0.5

        # MCC error level: cognitive conflict + threat detection
        mcc_error = (
            cognitive_conflict * 0.4 +
            threat_signal * 0.3 +
            salience_level * 0.2 +
            primal_urgency * 0.1
        )
        mcc_error = max(0.0, min(1.0, mcc_error))
        mcc_error *= gating

        # sgACC affect level: emotional tag + threat + interoceptive
        sgacc_affect = (
            abs(emotional_tag) * 0.4 +
            threat_signal * 0.3 +
            salience_level * 0.3
        )
        sgacc_affect = max(0.0, min(1.0, sgacc_affect))

        # vmPFC regulation reduces sgACC activation
        sgacc_affect *= max(0.1, regulation_strength)
        sgacc_affect *= gating

        # Affective reset readiness: MCC detects error, sgACC triggers affect,
        # reset fires when regulation is strong enough to interrupt rumination
        reset_threshold = 0.6
        reset_ready = (
            mcc_error * sgacc_affect *
            regulation_strength *
            (1.0 if mcc_error > reset_threshold else 0.0)
        )
        reset_ready = max(0.0, min(1.0, reset_ready))
        reset_ready *= warmth_factor

        self.state["mcc_error_level"] = round(mcc_error, 4)
        self.state["sgacc_affect_level"] = round(sgacc_affect, 4)
        self.state["affective_reset_ready"] = round(reset_ready, 4)
        self.persist_state()

        return {
            "mcc_error_level": round(mcc_error, 4),
            "sgacc_affect_level": round(sgacc_affect, 4),
            "affective_reset_ready": round(reset_ready, 4),
            "error_affect_output": {
                "mcc_error": round(mcc_error, 4),
                "sgacc_affect": round(sgacc_affect, 4),
                "reset_ready": round(reset_ready, 4),
            },
            "brain_affective_reset": round(reset_ready, 4),
        }
