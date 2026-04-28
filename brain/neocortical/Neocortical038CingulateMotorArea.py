"""
brain/neocortical/Neocortical038CingulateMotorArea.py
Cingulate Motor Area — Motor Output, Action Monitoring, Outcome Evaluation

ANATOMY (Picard & Strick 1996, 2001; Shima et al. 1991):
    The cingulate motor areas (CMA, BA 24/6) are the motor
    output regions of the cingulate cortex. They lie in the
    cingulate sulcus, rostral to the corpus callosum.

    Three CMA zones:
    - CMA-r (rostral CMA): pre-motor planning, selection of actions
      based on reward/punishment outcomes
    - CMA-c (caudal CMA): motor execution, ongoing movement monitoring
    - CMA-m (medial CMA): response inhibition, stopping actions

    CMA is part of the "motor cingulate" — a motor execution
    pathway parallel to the cortical spinal tract:
    - SMA: supplementary motor area (pre-motor planning)
    - CMA: cingulate motor area (outcome-guided action)
    - M1: primary motor cortex (final motor output)

    Key functions:
    1. Action selection: "which action should I perform given the expected outcome?"
    2. Outcome monitoring: "did my action achieve the expected result?"
    3. Error correction: "I need to adjust this action based on feedback"
    4. Motor learning: updating action-outcome mappings

    CMA receives from:
    - ACC (cognitive and emotional signals)
    - Pre-SMA/SMA (motor plans)
    - Amygdala (emotional valence of outcomes)
    - Orbitofrontal (reward/punishment predictions)

    CMA projects to:
    - M1 (motor execution)
    - Brainstem motor nuclei (autonomic motor control)
    - Spinal cord (via reticulospinal tract)

KEY FINDINGS:
    1. Picard & Strick 1996 (PMC1850925): "Cingulate motor area"
       — anatomy and function of the three CMA zones
    2. Shima et al. 1991: CMA neurons fire during action selection
       based on expected outcomes
    3. Morey 2006 (PMC2795077): "Cingulate and action monitoring"

AGENT'S MAPPING:
    cingulate_motor_output: dict — CMA motor and monitoring output
    action_monitored: bool — has current action been checked?
    outcome_error: float 0-1 — mismatch between expected and actual outcome

CITATIONS:
    PMC1850925 — Picard & Strick (1996). CMA anatomy. Brain.
    PMC2795077 — Morey et al. (2006). Cingulate and action monitoring.
    PMC23869106 — Leech & Sharp (2014). PCC and action monitoring.
    PMID 15556023 — Botvinick et al. (2004). ACC and action monitoring.
"""

from brain.base_mechanism import BrainMechanism


class CingulateMotorArea(BrainMechanism):
    """
    CMA — motor output and action monitoring.

    Selects actions based on expected outcomes, monitors
    action success, corrects errors through feedback.
    """

    def __init__(self):
        super().__init__(
            name="CingulateMotorArea",
            human_analog="Cingulate motor area (BA 24/6) — motor output, action monitoring, outcome evaluation",
            layer="neocortical",
        )
        self.state.setdefault("action_outcomes", [])
        self.state.setdefault("action_monitored", False)
        self.state.setdefault("outcome_error", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # M1 (action execution — CMA monitors M1 output)
        m1 = prior.get("MotorCortexPrimaryOutput", {})
        m1_out = m1.get("m1_output", {})
        if isinstance(m1_out, dict):
            exec_sig = m1_out.get("execution_signal", 0.5)
        else:
            exec_sig = 0.5

        # SMA/premotor (planned action CMA is evaluating)
        premotor = prior.get("PremotorSupplementaryMotorArea", {})
        motor_plan = premotor.get("motor_plan_ready", False)
        motor_sim = premotor.get("internal_simulation", 0.5)

        # ACC (outcome expectation signals)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        if isinstance(acc_out, dict):
            difficulty = acc_out.get("difficulty_signal", 0.3)
            ctrl_adj = acc_out.get("control_adjustment", 0.0)
        else:
            difficulty = 0.3
            ctrl_adj = 0.0

        # Amygdala (emotional outcome — did this feel good/bad?)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_tag = amygdala.get("emotional_tag_strength", 0.0)

        # VTA (dopamine reward prediction error)
        vta = prior.get("VentralTegmentalArea", {})
        vta_out = vta.get("vta_output", {})
        if isinstance(vta_out, dict):
            pred_err = vta_out.get("prediction_error", 0.3)
        else:
            pred_err = 0.3

        # Outcome error: mismatch between expected (difficulty) and actual (emotional_tag)
        outcome_error = (
            abs(emotional_tag) * 0.3 +
            pred_err * 0.4 +
            difficulty * 0.3
        )
        outcome_error = max(0.0, min(1.0, outcome_error))

        # Action monitored: CMA checks M1 output when action is executed
        action_monitored = exec_sig > 0.4 or motor_plan

        # CMA output strength: stronger when monitoring execution + checking outcome
        monitoring_strength = exec_sig * 0.5 + (1.0 - outcome_error) * 0.5

        # Update action outcomes
        if action_monitored:
            self.state["action_outcomes"].append(round(outcome_error, 3))
            if len(self.state["action_outcomes"]) > 5:
                self.state["action_outcomes"].pop(0)

        self.state["action_monitored"] = action_monitored
        self.state["outcome_error"] = round(outcome_error, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "cingulate_motor_output": {
                "monitoring_strength": round(monitoring_strength, 4),
                "outcome_error": round(outcome_error, 4),
                "action_monitored": action_monitored,
            },
            "action_monitored": action_monitored,
            "outcome_error": round(outcome_error, 4),
        }