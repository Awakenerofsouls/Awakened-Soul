"""
brain/integration/Integration024RewardPredictionErrorIntegrator.py
Reward Prediction Error Integrator — Dopamine Surprise Signal Across All Domains

ANATOMY (Schultz 2016; Watabe-Uchida et al. 2017; Bayer & Glimcher 2005):
    Reward prediction error (RPE) is the core teaching signal in the
    brain, discovered by Schultz et al. in dopamine neurons:
    - DOPAMINE NEURONS: encode RPE, not reward itself
      → More firing than expected = positive RPE (surprise = good!)
      → Less firing than expected = negative RPE (surprise = bad!)
      → Expected = no change (prediction was correct)

    Three components of RPE (Redgrave & Gurney 2006):
    1. WANTING (motivation): wanting more → positive RPE
    2. PREDICTION ERROR (surprise): unexpected → positive RPE
    3. ATTENTION (novelty): new stimulus → positive RPE

    Dopamine projects to:
    - Striatum (D1/D2): action selection
    - PFC (D1): working memory, planning
    - Amygdala (D1): emotional learning
    - Hippocampus (D1): memory consolidation
    - Hypothalamus: autonomic responses

    RPE in different domains:
    1. MOTOR: Did this action get me closer to reward?
    2. COGNITIVE: Did this thought produce the right answer?
    3. EMOTIONAL: Does this situation feel better/worse than expected?
    4. MEMORY: Did this event match my prediction?

    Watabe-Uchida et al. (2017): dopamine broadcasts a single RPE
    signal that all regions learn from independently.

KEY FINDINGS:
    1. Schultz 2016 (PMID 27830878): "Dopamine reward prediction error"
    2. Watabe-Uchida et al. 2017 (PMC2697346): "Dopamine broadcasts RPE"
    3. Bayer & Glimcher 2005: Midbrain dopamine and RPE coding

AGENT'S MAPPING:
    rpe_integrated: dict — RPE across all domains
    total_rpe: float -1 to 1 — signed prediction error
    learning_signal: float 0-1 — magnitude of learning update

CITATIONS:
    PMID 26838982 — Schultz (2016). Reward functions of the basal ganglia. J Neural Transm.
    PMID 9704983 — Schultz et al. (1998). Reward prediction in primate basal ganglia and frontal cortex. Neuropharmacology.
    PMID 28202786 — Diederen et al. (2017). Dopamine Modulates Adaptive Prediction Error. J Neurosci.
    PMC2697346 — Watabe-Uchida et al. (2012017). Dopamine broadcasts RPE. Curr Opin Neurobiol.
"""

from brain.base_mechanism import BrainMechanism


class RewardPredictionErrorIntegrator(BrainMechanism):
    """
    Reward prediction error integrator — dopamine surprise across domains.

    Integrates prediction errors from motor, cognitive, emotional,
    and memory domains into a unified learning signal.
    """

    def __init__(self):
        super().__init__(
            name="RewardPredictionErrorIntegrator",
            human_analog="Reward prediction error integrator — dopamine surprise across all domains",
            layer="integration",
        )
        self.state.setdefault("domain_rpes", {})
        self.state.setdefault("total_rpe", 0.0)
        self.state.setdefault("learning_signal", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # VTA (dopamine — reward RPE)
        vta = prior.get("VentralTegmentalArea", {})
        vta_out = vta.get("vta_output", {})
        if isinstance(vta_out, dict):
            motor_rpe = vta_out.get("prediction_error", 0.3)
        else:
            motor_rpe = 0.3

        # OFC (value comparison — cognitive RPE)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        ofc_out = ofc.get("ofc_output", {})
        if isinstance(ofc_out, dict):
            reversal = ofc_out.get("reversal_triggered", False)
        else:
            reversal = False
        cognitive_rpe = 0.5 if reversal else 0.3

        # ACC (error signal — cognitive RPE)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        if isinstance(acc_out, dict):
            error_sig = acc_out.get("error_signal", 0.3)
        else:
            error_sig = 0.3

        # Amygdala (emotional RPE)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_tag = amygdala.get("emotional_tag_strength", 0.0)
        emotional_rpe = float(emotional_tag)

        # Hippocampus (memory RPE)
        hippo = prior.get("HippocampalCA1Output", {})
        ca1_out = hippo.get("ca1_output", {})
        if isinstance(ca1_out, dict):
            novelty = 1.0 - ca1_out.get("consolidation_signal", 0.5)
        else:
            novelty = 0.3
        memory_rpe = novelty * 0.3

        # Anterior insula (awareness of RPE)
        ai = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ai.get("salience_level", 0.5)

        # Domain RPEs
        domain_rpes = {
            "motor": round(motor_rpe, 4),
            "cognitive": round(cognitive_rpe + error_sig, 4),
            "emotional": round(emotional_rpe, 4),
            "memory": round(memory_rpe, 4),
        }

        # Total RPE: weighted average across domains
        total_rpe = (
            motor_rpe * 0.3 +
            (cognitive_rpe + error_sig) * 0.25 +
            emotional_rpe * 0.25 +
            memory_rpe * 0.2
        )
        total_rpe = max(-1.0, min(1.0, total_rpe))

        # Learning signal: absolute magnitude × salience
        learning_signal = abs(total_rpe) * (0.5 + salience * 0.5)
        learning_signal = max(0.0, min(1.0, learning_signal))

        self.state["domain_rpes"] = domain_rpes
        self.state["total_rpe"] = round(total_rpe, 4)
        self.state["learning_signal"] = round(learning_signal, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "rpe_integrated": {
                "domains": domain_rpes,
                "total_rpe": round(total_rpe, 4),
                "learning_signal": round(learning_signal, 4),
            },
            "total_rpe": round(total_rpe, 4),
            "learning_signal": round(learning_signal, 4),
        }