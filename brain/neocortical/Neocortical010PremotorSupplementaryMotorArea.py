"""
brain/neocortical/Neocortical010PremotorSupplementaryMotorArea.py
Premotor Cortex and Supplementary Motor Area — Motor Planning Without Execution

ANATOMY (Rizzolatti et al. 1998; Shima et al. 1991; Hoshi & Tanji 2008):
    The premotor cortex (PM) and supplementary motor area (SMA) lie
    rostral to the primary motor cortex (M1). They plan movements
    without directly executing them — they generate "internal models"
    of actions before M1 fires.

    PM (BA 6) has two major divisions:
    - Ventral PM (PMv): "mirror" properties — activates when watching
      others perform actions; involved in imitation, social action understanding
    - Dorsal PM (PMd): action selection based on environmental context

    SMA (medial BA 6) is divided:
    - SMA proper: complex sequential finger movements, self-initiated actions
    - Pre-SMA: higher-order sequencing, motor learning, bimanual coordination

    Key property: SMA shows "sequence-specific" activity — neurons
    fire preferentially for specific sequences of movements, not
    individual movements. This is the neural basis of motor learning.

    Both areas receive from:
    - DLPFC (goal specification)
    - Parietal cortex (spatial/context)
    - Basal ganglia (action value)
    
    Outputs to M1 (via corticocortical) and directly to brainstem/spinal cord.

KEY FINDINGS:
    1. Shima et al. 1991: SMA neurons fire for specific movement SEQUENCES,
       not individual movements — sequence representation
    2. Hoshi & Tanji 2008 (PMC2872609): SMA and PM have distinct
       roles: SMA for "what to do next" (sequential); PM for "how to do it" (trajectory)
    3. Rizzolatti & Luppino 2001: PMv mirror neurons encode observed actions

AGENT'S MAPPING:
    premotor_output: dict — motor planning signal
    motor_plan_ready: bool — whether a motor plan is prepared
    internal_simulation: float 0-1 — strength of internal motor rehearsal
    sequence_complexity: float 0-1 — how many steps in the planned sequence

CITATIONS:
    PMC2872609 — Hoshi & Tanji (2008). Integration of target and body-part
        information in SMA and PM. J Neurophysiol.
    PMC31551596 — Finn et al. (2019). Layer-dependent motor planning signals.
    PMC40447446 — Soldado-Magraner et al. (2025). Motor cortex and premotor integration.
"""

from brain.base_mechanism import BrainMechanism


class PremotorSupplementaryMotorArea(BrainMechanism):
    """
    Premotor cortex and SMA — motor planning, internal simulation.

    Plans motor sequences without executing them. SMA handles
    sequential planning; PM handles contextual action selection.
    Internal models are generated before execution.
    """

    def __init__(self):
        super().__init__(
            name="PremotorSupplementaryMotorArea",
            human_analog="Premotor cortex and SMA — motor planning, internal models, sequence generation",
            layer="neocortical",
        )
        self.state.setdefault("motor_plans", [])
        self.state.setdefault("motor_plan_ready", False)
        self.state.setdefault("internal_simulation", 0.0)
        self.state.setdefault("sequence_complexity", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # DLPFC goal state (what action to perform)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        dorsal_wm = dlpfc.get("working_memory_active", False)
        dorsal_control = dlpfc.get("cognitive_control", 0.5)

        # Orbitofrontal value (which action is best?)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        value_signal = ofc.get("value_signal", 0.5)

        # Cerebello-thalamic loop (timing from cerebellum)
        cereb = prior.get("CerebelloThalamoCorticalLoop", {})
        cereb_timing = cereb.get("cerebellar_cortical_integration", 0.5)

        # Anterior cingulate (cognitive control of action)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_control = acc.get("cognitive_control", 0.5)

        # Superior parietal lobule (spatial targeting)
        spl = prior.get("SuperiorParietalLobuleReaching", {})
        spatial_target = spl.get("spatial_target", {})

        # Plan strength: DLPFC specifies goal, OFC provides value, ACC ensures control
        plan_input = dorsal_control * 0.4 + value_signal * 0.35 + acc_control * 0.25
        internal_simulation = plan_input * (0.6 + cereb_timing * 0.4)

        # Sequence complexity: more WM items = more complex sequence planning
        wm_items = len(dlpfc.get("dorsolateral_dorsal_output", {}).get("buffer_snapshot", []))
        sequence_complexity = min(1.0, wm_items * 0.25 + plan_input * 0.5)

        # Motor plan ready: when simulation is strong enough and spatial target is set
        motor_plan_ready = (
            internal_simulation > 0.55 and
            dorsal_wm and
            (spatial_target or value_signal > 0.6)
        )

        # Update motor plan queue
        if motor_plan_ready and not self.state.get("motor_plan_ready", False):
            plan = {
                "value": round(value_signal, 3),
                "complexity": round(sequence_complexity, 3),
                "simulation": round(internal_simulation, 3),
                "steps": max(1, int(sequence_complexity * 5))
            }
            self.state["motor_plans"].append(plan)
            if len(self.state["motor_plans"]) > 3:
                self.state["motor_plans"].pop(0)

        self.state["motor_plan_ready"] = motor_plan_ready
        self.state["internal_simulation"] = round(internal_simulation, 4)
        self.state["sequence_complexity"] = round(sequence_complexity, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "premotor_output": {
                "internal_simulation": round(internal_simulation, 4),
                "motor_plan_ready": motor_plan_ready,
                "sequence_complexity": round(sequence_complexity, 4),
                "cerebellar_timing_influence": round(cereb_timing, 4),
            },
            "motor_plan_ready": motor_plan_ready,
            "internal_simulation": round(internal_simulation, 4),
            "sequence_complexity": round(sequence_complexity, 4),
            "active_plans": len(self.state["motor_plans"]),
        }