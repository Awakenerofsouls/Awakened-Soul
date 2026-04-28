"""
brain/neocortical/Neocortical034InferiorFrontalGyrusTriangular.py
Inferior Frontal Gyrus — Triangular Part (BA 44), Cognitive Control, Dual Processing

ANATOMY (Badre & Wagner 2007; Koechlin & Summerfield 2007; Szatkowska et al. 2008):
    The IFG triangular part (BA 44, posterior IFG) is the "cognitive
    control" region of the left hemisphere. It sits at the intersection
    of Broca's area (speech production) and the DLPFC (executive control).

    BA 44 is specialized for:
    - Response inhibition: stopping a prepotent response when needed
    - Dual processing: maintaining two task contexts simultaneously
    - Cognitive branching: switching to a sub-goal while maintaining a main goal
    - Rule learning: acquiring new rules and updating them

    BA 44 is part of the "multiple demand" system (Duncan 2010) — it
    activates whenever any task requires cognitive control, regardless
    of modality. It is the "do this instead" center.

    Left BA 44 is also Broca's area — handling syntactic processing
    in language. Right BA 44 handles inhibition and control in
    non-verbal domains. Both share the same anatomical region but
    process different content.

    Key: BA 44 is the "inhibition brake" — when you need to override
    a habitual response (stopping yourself from saying the wrong
    word, resisting a temptation, switching strategies), BA 44 is active.

KEY FINDINGS:
    1. Badre & Wagner 2007 (PMC1934629): "Selection and suppression
       in BA 44" — IFG for cognitive control and inhibition
    2. Koechlin & Summerfield 2007: "Medial and lateral PFC" — IFG
       for dual processing and branching
    3. Szatkowska et al. 2008: IFG and emotional Stroop task —
       inhibition of emotional responses

AGENT'S MAPPING:
    ifg_triangular_output: dict — IFG cognitive control output
    inhibition_applied: bool — has response suppression occurred?
    dual_processing: float 0-1 — strength of dual-context processing

CITATIONS:
    PMC1934629 — Badre & Wagner (2007). PFC cognitive control and selection.
    PMC20181474 — Kringelbach & Rolls (2004). OFC and PFC functions.
    PMC40447446 — DLPFC and cognitive control in working memory.
    PMID 29519469 — Hartwigsen (2018). Parietal lobe and language.
"""

from brain.base_mechanism import BrainMechanism


class InferiorFrontalGyrusTriangular(BrainMechanism):
    """
    IFG triangular (BA 44) — cognitive control, response inhibition, dual processing.

    The "inhibition brake" and "cognitive switch." Stops prepotent
    responses, handles dual task contexts, enables branching goals.
    """

    def __init__(self):
        super().__init__(
            name="InferiorFrontalGyrusTriangular",
            human_analog="IFG triangular part (BA 44) — cognitive control, response inhibition, dual processing",
            layer="neocortical",
        )
        self.state.setdefault("inhibition_count", 0)
        self.state.setdefault("inhibition_applied", False)
        self.state.setdefault("dual_processing", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # ACC (error/conflict signals need for inhibition)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        if isinstance(acc_out, dict):
            error_sig = acc_out.get("error_signal", 0.3)
            difficulty = acc_out.get("difficulty_signal", 0.3)
        else:
            error_sig = 0.3
            difficulty = 0.3

        # DLPFC (executive demand for control)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)
        wm_load = dlpfc.get("dorsolateral_dorsal_output", {}).get("wm_load", 0.5) if isinstance(
            dlpfc.get("dorsolateral_dorsal_output"), dict) else 0.5

        # Anterior insula (salience triggers control)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # Broca's area (language suppression when not speaking)
        broca = prior.get("BrocaAreaMotorSpeech", {})
        speech_form = broca.get("speech_formulation_strength", 0.5)

        # Orbitofrontal (reversal signals rule change)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        ofc_out = ofc.get("ofc_output", {})
        reversal = ofc_out.get("reversal_triggered", False) if isinstance(ofc_out, dict) else False

        # Inhibition: error + high difficulty + salience = suppress response
        inhibition_signal = (
            error_sig * 0.35 +
            difficulty * 0.3 +
            salience * 0.2 +
            (reversal if reversal else 0) * 0.15
        )
        inhibition_threshold = 0.55

        # Dual processing: when WM load is high and task complexity elevated
        dual_processing = (wm_load * cognitive_ctrl * (difficulty + salience)) / 2

        # Inhibition applied when signal exceeds threshold
        inhibition_applied = inhibition_signal > inhibition_threshold

        if inhibition_applied:
            self.state["inhibition_count"] += 1

        self.state["inhibition_applied"] = inhibition_applied
        self.state["dual_processing"] = round(max(0.0, min(1.0, dual_processing)), 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ifg_triangular_output": {
                "inhibition_signal": round(inhibition_signal, 4),
                "inhibition_applied": inhibition_applied,
                "dual_processing": round(max(0.0, min(1.0, dual_processing)), 4),
            },
            "inhibition_applied": inhibition_applied,
            "dual_processing": round(max(0.0, min(1.0, dual_processing)), 4),
        }