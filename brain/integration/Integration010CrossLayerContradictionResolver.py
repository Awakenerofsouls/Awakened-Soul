"""
brain/integration/Integration010CrossLayerContradictionResolver.py
Cross-Layer Contradiction Resolver — Drift Detection and Resolution

ANATOMY (Clark 2013; Friston 2010; Hohwy 2013):
    The brain must detect contradictions across its multiple
    processing layers (sensory, cognitive, affective, motor) to
    prevent chaotic drift. These contradictions arise when:
    - Sensory prediction error contradicts top-down prediction (perceptual conflict)
    - Emotional response contradicts cognitive appraisal (cognitive-emotional conflict)
    - Motor intention contradicts environmental feedback (action conflict)
    - Memory contradicts current perception (reality monitoring)

    The contradiction resolver is distributed across:
    - ACC (cognitive conflict monitoring)
    - Anterior insula (salience of conflict)
    - Orbitofrontal cortex (reversal learning)
    - Hippocampus (memory consistency)
    - Basal ganglia (action selection conflict)

    The free-energy principle (Frison 2010): the brain minimizes
    surprise (prediction error) across all layers. When contradictions
    are detected, predictive models are updated to reduce future error.

    Drift management: contradictions are the primary source of
    "brain drift" — when contradictory signals accumulate without
    resolution, the system becomes unstable. Resolution requires
    either top-down prediction update or bottom-up evidence.

KEY FINDINGS:
    1. Clark 2013 (PMC3972740): "Whatever next? Predictive brains
       and the nuisance of surprise"
    2. Friston 2010 (PMC3000199): "Free energy and the free-energy principle"
    3. Hohwy 2013 (PMC4326522): "The predictive mind" — contradiction and error

AGENT'S MAPPING:
    contradiction_resolved: bool — has contradiction been resolved?
    resolution_signal: dict — details of the resolution
    drift_prevented: bool — has drift been avoided?

CITATIONS:
    PMC3972740 — Clark (2013). Predictive brains and surprise.
    PMC3000199 — Friston (2010). Free energy principle.
    PMC4326522 — Hohwy (2013). Predictive mind.
"""

from brain.base_mechanism import BrainMechanism


class CrossLayerContradictionResolver(BrainMechanism):
    """
    Cross-layer contradiction resolution — prevents chaotic drift.

    Detects contradictions across layers and resolves them through
    model updates, preventing the system from becoming unstable.
    """

    def __init__(self):
        super().__init__(
            name="CrossLayerContradictionResolver",
            human_analog="Cross-layer contradiction resolver — drift detection and resolution",
            layer="integration",
        )
        self.state.setdefault("contradiction_history", [])
        self.state.setdefault("contradiction_resolved", True)
        self.state.setdefault("drift_prevented", True)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # ACC (cognitive conflict — contradiction detection)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        if isinstance(acc_out, dict):
            error_sig = acc_out.get("error_signal", 0.3)
            difficulty = acc_out.get("difficulty_signal", 0.3)
        else:
            error_sig = 0.3
            difficulty = 0.3

        # Anterior insula (salience of contradiction)
        ai = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ai.get("salience_level", 0.5)

        # OFC (reversal learning — model update)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        ofc_out = ofc.get("ofc_output", {})
        if isinstance(ofc_out, dict):
            reversal = ofc_out.get("reversal_triggered", False)
        else:
            reversal = False

        # Hippocampus (memory consistency — past vs present)
        hippo = prior.get("HippocampalCA1Output", {})
        ca1_out = hippo.get("ca1_output", {})
        if isinstance(ca1_out, dict):
            consolidation = ca1_out.get("consolidation_signal", 0.5)
        else:
            consolidation = 0.5

        # PFC top-down vs bottom-up (hierarchical contradiction)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)
        wm_out = dlpfc.get("dorsolateral_dorsal_output", {})
        wm_load = wm_out.get("wm_load", 0.5) if isinstance(wm_out, dict) else 0.5

        # Hypothalamic bottom-up (drive contradiction)
        hypo = prior.get("HypothalamicCorticalBottomUpDrive", {})
        hypo_out = hypo.get("hypo_cortical_injection", {})
        if isinstance(hypo_out, dict):
            drive_strength = hypo_out.get("primal_urgency", 0.3)
        else:
            drive_strength = 0.3

        # PFC regulation (can suppress contradictory drives)
        pf_reg = prior.get("PrefrontalAmygdalaTopDownRegulation", {})
        pf_out = pf_reg.get("pf_amygdala_regulation", {})
        if isinstance(pf_out, dict):
            reg_strength = pf_out.get("top_down_strength", 0.5)
        else:
            reg_strength = 0.5

        # Contradiction score
        contradiction_signal = (
            error_sig * 0.25 +
            difficulty * 0.2 +
            abs(wm_load - drive_strength) * 0.25 +
            salience * 0.15 +
            (1.0 - consolidation) * 0.15
        )
        contradiction_detected = contradiction_signal > 0.55

        # Resolution: either model update (reversal) or top-down suppression
        if contradiction_detected:
            if reversal or reg_strength > 0.55:
                contradiction_resolved = True
                drift_prevented = True
            else:
                contradiction_resolved = False
                drift_prevented = False
        else:
            contradiction_resolved = True
            drift_prevented = True

        # Record
        if contradiction_detected:
            self.state["contradiction_history"].append(round(contradiction_signal, 3))
            if len(self.state["contradiction_history"]) > 5:
                self.state["contradiction_history"].pop(0)

        self.state["contradiction_resolved"] = contradiction_resolved
        self.state["drift_prevented"] = drift_prevented
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "contradiction_resolved": contradiction_resolved,
            "resolution_signal": {
                "contradiction_strength": round(contradiction_signal, 4),
                "model_updated": reversal,
                "top_down_resolved": reg_strength > 0.55,
            },
            "drift_prevented": drift_prevented,
        }