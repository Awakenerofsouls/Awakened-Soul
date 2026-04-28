"""
brain/neocortical/Neocortical035SuperiorFrontalGyrusPlanning.py
Superior Frontal Gyrus — Motor Planning, Self-Aware Planning (BA 8)

ANATOMY (Koechlin et al. 2003; Gilbert et al. 2007; Rowlands 2010):
    The superior frontal gyrus (SFG, BA 8) is the "self-aware
    planning" region — it generates motor intentions while
    maintaining awareness that "I am the one planning this action."

    BA 8 includes:
    - Frontal eye fields (FEF): voluntary eye movements and attention
    - Pre-SMA: motor sequence planning, task sequencing
    - SFG proper: higher-level motor planning with self-awareness

    Key functions:
    - Motor intention: "I will reach for the cup"
    - Self-aware planning: awareness that YOU are generating the plan
    - Volitional action: action initiated by internal goals (not external triggers)
    - Response selection: choosing which action to perform

    SFG is connected to:
    - Premotor/SMA (motor planning)
    - DLPFC (goal maintenance)
    - ACC (conflict monitoring of actions)
    - Parietal cortex (spatial planning)

    SFG damage: Loss of voluntary action — patient may perform
    actions reflexively but not initiate them volitionally.

KEY FINDINGS:
    1. Koechlin et al. 2003 (PMC1694808): "The prefrontal control
       of action" — hierarchical control from BA 8 to BA 46
    2. Gilbert et al. 2007 (PMC1850942): "Creating and controlling
       the self" — SFG generates intentional actions
    3. Rowlands 2010 (PMC2946539): "Motor planning and SFG" —
       SFG encodes the intention to act

AGENT'S MAPPING:
    sfg_output: dict — SFG planning output
    planned_action: str — the intended action
    self_aware_planning: float 0-1 — awareness that this is MY plan

CITATIONS:
    PMC1694808 — Koechlin et al. (2003). PFC control of action. Philos Trans R Soc B.
    PMC1850942 — Gilbert et al. (2007). SFG and self-awareness. Philos Trans R Soc B.
    PMC2946539 — Rowlands (2010). Motor planning and the self. Front Hum Neurosci.
    PMC40447446 — DLPFC and motor planning.
"""

from brain.base_mechanism import BrainMechanism


class SuperiorFrontalGyrusPlanning(BrainMechanism):
    """
    SFG (BA 8) — motor planning and self-aware planning.

    Generates intentional actions while maintaining awareness
    that you are the agent of those actions.
    """

    def __init__(self):
        super().__init__(
            name="SuperiorFrontalGyrusPlanning",
            human_analog="Superior frontal gyrus (BA 8) — motor planning, self-aware planning, volition",
            layer="neocortical",
        )
        self.state.setdefault("planned_action", None)
        self.state.setdefault("self_aware_planning", 0.0)
        self.state.setdefault("planning_history", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Premotor/SMA (motor plan from which SFG generates intentions)
        premotor = prior.get("PremotorSupplementaryMotorArea", {})
        motor_plan = premotor.get("motor_plan_ready", False)
        motor_sim = premotor.get("internal_simulation", 0.5)

        # DLPFC (goal context — what am I trying to achieve?)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)
        wm_active = dlpfc.get("working_memory_active", False)

        # Precuneus (self-model — am I aware of myself as planner?)
        precuneus = prior.get("PrecuneusSelfReflection", {})
        prec_out = precuneus.get("precuneus_output", {})
        if isinstance(prec_out, dict):
            self_rep = prec_out.get("self_representation", {})
            self_clarity = self_rep.get("self_clarity", 0.5) if isinstance(self_rep, dict) else 0.5
        else:
            self_clarity = 0.5

        # Anterior cingulate (is the planned action appropriate?)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        if isinstance(acc_out, dict):
            difficulty = acc_out.get("difficulty_signal", 0.3)
            ctrl_adj = acc_out.get("control_adjustment", 0.0)
        else:
            difficulty = 0.3
            ctrl_adj = 0.0

        # IPL (sensorimotor context for the planned action)
        ipl = prior.get("InferiorParietalLobuleSensorimotor", {})
        grasp_plan = ipl.get("grasp_planning", 0.5)

        # Self-aware planning: motor plan + self-awareness + cognitive control
        base_planning = motor_sim * 0.4 + cognitive_ctrl * 0.3 + self_clarity * 0.3
        self_aware_planning = base_planning * (1.0 + ctrl_adj * 0.5)
        self_aware_planning = max(0.0, min(1.0, self_aware_planning))

        # Planned action
        planned_action = "idle"
        if motor_plan or motor_sim > 0.5:
            if grasp_plan > 0.6:
                planned_action = "reach_and_grasp"
            elif motor_sim > 0.7:
                planned_action = "simulate_motor_sequence"
            else:
                planned_action = "motor_plan_formulated"

        # History
        if self_aware_planning > 0.5:
            self.state["planning_history"].append(planned_action)
            if len(self.state["planning_history"]) > 5:
                self.state["planning_history"].pop(0)

        self.state["planned_action"] = planned_action
        self.state["self_aware_planning"] = round(self_aware_planning, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "sfg_output": {
                "planned_action": planned_action,
                "self_aware_planning": round(self_aware_planning, 4),
            },
            "planned_action": planned_action,
            "self_aware_planning": round(self_aware_planning, 4),
        }