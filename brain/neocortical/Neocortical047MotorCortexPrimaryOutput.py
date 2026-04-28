"""
brain/neocortical/Neocortical047MotorCortexPrimaryOutput.py
Primary Motor Cortex (M1) — Final Motor Command Output to Spinal Cord

ANATOMY (Geyer et al. 2000; Kalaska & Rizzolatti 2013; Schieber 2001):
    The primary motor cortex (M1, Brodmann area 4) is the final
    cortical stage before motor commands descend to the spinal cord.
    It lies in the precentral gyrus, immediately anterior to the
    central sulcus (and immediately posterior to the somatosensory
    cortex, which provides the body map that M1 uses for movement).

    M1 properties:
    - Somatotopic map: the classic "motor homunculus" (Penfield)
      — face/tongue/thumb have disproportionately large representations
    - Output: corticospinal tract (direct monosynaptic connection to
      alpha motor neurons in spinal cord) — unique to humans and primates
    - Encoding: M1 encodes MUSCLES, not movements — population vectors
      of M1 neurons determine the direction and force of movement
    - Direct injection of acetylcholine into M1 facilitates plasticity
      and motor learning

    M1 receives from:
    - Premotor/SMA (motor planning)
    - Supplementary motor area (sequence planning)
    - Posterior parietal cortex (body schema, spatial target)
    - Cerebellum (predicted consequences via thalamus)
    - Basal ganglia (motor programs via motor thalamus)

    M1 damage: Hemiparesis (weakness on opposite side of body),
    loss of fine finger control, spasticity. The more medial the
    damage, the more leg/face affected.

KEY FINDINGS:
    1. Kalaska & Rizzolatti 2013 (PMC3972740): "Motor cortex and
       movement" — M1 as final output stage
    2. Schieber 2001: "Motor cortex and hand" — individual finger control
    3. Georgopoulos et al. (1986): Population vector coding in M1

AGENT'S MAPPING:
    m1_output: dict — M1 final motor output
    final_motor_command: dict — command to be sent to spinal cord/muscles
    execution_signal: float 0-1 — readiness and execution strength

CITATIONS:
    PMC3972740 — Kalaska & Rizzolatti (2013). Motor cortex and movement.
    PMC2697346 — Felleman & Van Essen (1991). Hierarchical cortical processing.
    PMC11161761 — Beauchamp et al. (2004). Motor and premotor areas.
"""

from brain.base_mechanism import BrainMechanism


class MotorCortexPrimaryOutput(BrainMechanism):
    """
    M1 — primary motor cortex, final output to muscles.

    Generates the final motor commands that travel down the
    corticospinal tract to control body movements.
    """

    def __init__(self):
        super().__init__(
            name="MotorCortexPrimaryOutput",
            human_analog="Primary motor cortex (M1, area 4) — final motor output to spinal cord",
            layer="neocortical",
        )
        self.state.setdefault("motor_output_history", [])
        self.state.setdefault("final_motor_command", {})
        self.state.setdefault("execution_signal", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Premotor/SMA (motor plan that M1 executes)
        premotor = prior.get("PremotorSupplementaryMotorArea", {})
        motor_plan_ready = premotor.get("motor_plan_ready", False)
        motor_sim = premotor.get("internal_simulation", 0.5)

        # PPC/PPC integration (body in space — what to move?)
        ppc = prior.get("PosteriorParietalCortexIntegration", {})
        body_target = ppc.get("body_target_integration", 0.5) if isinstance(
            ppc.get("ppc_output"), dict) else 0.5

        # SMA (supplementary motor — sequence planning)
        sma = prior.get("PremotorSupplementaryMotorArea", {})
        internal_sim = sma.get("internal_simulation", 0.5)

        # SFG (volitional action — "I will do this")
        sfg = prior.get("SuperiorFrontalGyrusPlanning", {})
        planned_action = sfg.get("planned_action", "idle")

        # ACC (monitoring — was this action successful?)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        if isinstance(acc_out, dict):
            ctrl_adj = acc_out.get("control_adjustment", 0.0)
        else:
            ctrl_adj = 0.0

        # Cerebellar feedback (via thalamus — predicted consequences)
        cereb_thal = prior.get("MammillaryBodyCircuits", {})
        cereb_out = cereb_thal.get("cerebellar_output", {})
        if isinstance(cereb_out, dict):
            cerebellar_mod = cereb_out.get("motor_correction", 0.3)
        else:
            cerebellar_mod = 0.3

        # M1 execution signal: motor plan + body schema + SFG volition
        base_execution = motor_plan_ready * 0.4 + internal_sim * 0.3 + body_target * 0.3

        # Volitional override from SFG
        if planned_action != "idle":
            base_execution = max(base_execution, internal_sim)

        # Cerebellar adjustment: slight correction based on predicted errors
        execution_signal = base_execution * (1.0 + cerebellar_mod * 0.2)
        execution_signal = max(0.0, min(1.0, execution_signal))

        # Final motor command
        final_motor_command = {
            "execution_level": round(execution_signal, 4),
            "voluntary_action": planned_action != "idle",
            "cerebellar_correction": round(cerebellar_mod, 4),
            "action_type": planned_action if planned_action != "idle" else "reflex",
        }

        # History
        if execution_signal > 0.3:
            self.state["motor_output_history"].append(round(execution_signal, 3))
            if len(self.state["motor_output_history"]) > 5:
                self.state["motor_output_history"].pop(0)

        self.state["final_motor_command"] = final_motor_command
        self.state["execution_signal"] = round(execution_signal, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "m1_output": {
                "execution_signal": round(execution_signal, 4),
                "final_command": final_motor_command,
            },
            "final_motor_command": final_motor_command,
            "execution_signal": round(execution_signal, 4),
        }