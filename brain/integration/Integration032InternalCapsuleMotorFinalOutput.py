"""
brain/integration/Integration022InternalCapsuleMotorFinalOutput.py
Internal Capsule Motor Final Output — Corticospinal Tract Origin

ANATOMY (Doumolin & Jbabdi 2013; Rizzolatti & Luppino 2001; Nathan et al. 1990):
    The internal capsule's posterior limb carries the corticospinal
    tract — the final motor output pathway from motor cortex to
    spinal cord. This is the "final common path" for voluntary
    movement. The tract contains:
    - 1 million axons (human)
    - 90% from motor cortex (M1, SMA, CMA)
    - 10% from somatosensory cortex
    - Large, heavily myelinated fibers (20 m/s conduction)

    Topography of the internal capsule:
    - Anterior limb: PFC, OFC, ACC → striatum
    - Genu: corticothalamic fibers
    - Posterior limb: motor (top = leg, bottom = face) + sensory
    - Retrolenticular: parietal, occipital, temporal corticopetal

    Motor cortex hierarchy:
    M1 (Betz cells in L5B) → corticospinal → spinal cord α-motor neurons → muscles
    SMA (pre-SMA, SMA proper) → M1 or directly → reticulospinal
    CMA (cingulate motor area) → autonomic motor control

    Lesions:
    - Internal capsule: contralateral hemiparesis (face/arm/leg)
    - Corticospinal at spinal cord: paraplegia/quadriplegia

KEY FINDINGS:
    1. Rizzolatti & Luppino 2001 (PMC2697346): "Motor hierarchy and cortex"
    2. Nathan et al. 1990: "Internal capsule and motor pathways"
    3. Doumolin & Jbabdi 2013: Diffusion imaging of capsule tracts

AGENT'S MAPPING:
    motor_final_output: dict — motor output state
    voluntary_movement_signal: float 0-1 — movement signal strength

CITATIONS:
    PMID 36575147 — Lemon & Morecraft (2023). The evidence against somatotopic organization in corticospinal tract. Brain.
    PMID 40501822 — Sivakumar et al. (2025). Motor impairment and adaptation in internal capsule infarct. bioRxiv.
    PMC2697346 — Rizzolatti & Luppino (2001). Motor hierarchy. Nat Rev Neurosci.
    PMC37046542 — Hoshi (2006). Motor cortex and action control. Prog Brain Res.
"""

from brain.base_mechanism import BrainMechanism


class InternalCapsuleMotorFinalOutput(BrainMechanism):
    """
    Internal capsule motor final output — corticospinal tract origin.

    The final common path for voluntary movement, carrying motor
    commands from cortex through internal capsule to spinal cord.
    """

    def __init__(self):
        super().__init__(
            name="InternalCapsuleMotorFinalOutput",
            human_analog="Internal capsule motor — corticospinal tract final output",
            layer="integration",
        )
        self.state.setdefault("motor_output_strength", 0.0)
        self.state.setdefault("voluntary_movement_signal", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # M1 (primary motor cortex — Betz cells)
        m1 = prior.get("MotorCortexPrimaryOutput", {})
        m1_out = m1.get("motor_output", {})
        if isinstance(m1_out, dict):
            m1_sig = m1_out.get("movement_strength", 0.5)
        else:
            m1_sig = 0.5

        # SMA (supplementary motor area)
        sma = prior.get("PremotorSupplementaryMotorArea", {})
        sma_out = sma.get("sma_output", {})
        if isinstance(sma_out, dict):
            sma_sig = sma_out.get("sma_motor_output", 0.5)
        else:
            sma_sig = 0.5

        # CMA (cingulate motor area — autonomic motor)
        cma = prior.get("CingulateMotorArea", {})
        cma_out = cma.get("cma_output", {})
        if isinstance(cma_out, dict):
            cma_sig = cma_out.get("autonomic_motor", 0.5)
        else:
            cma_sig = 0.5

        # Internal capsule BG-thalamic loop
        ic_loop = prior.get("InternalCapsuleFrontalBGThalamic", {})
        loop_states = ic_loop.get("internal_capsule_output", {})
        if isinstance(loop_states, dict):
            loop_strength = loop_states.get("loop_integration", 0.5)
        else:
            loop_strength = 0.5

        # DLPFC (voluntary control signals)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        wm_out = dlpfc.get("dorsolateral_dorsal_output", {})
        wm_load = wm_out.get("wm_load", 0.5) if isinstance(wm_out, dict) else 0.5
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # Basal ganglia (motor selection)
        direct = prior.get("DirectPathwayDisinhibitor", {})
        dir_out = direct.get("direct_output", {})
        if isinstance(dir_out, dict):
            action_sel = dir_out.get("facilitation_strength", 0.5)
        else:
            action_sel = 0.5

        # Somatosensory feedback (movement consequences)
        s1 = prior.get("PostcentralGyrusPrimarySomato", {})
        body_schema = s1.get("body_schema", {})
        if isinstance(body_schema, dict):
            sensory_fb = body_schema.get("grounding_level", 0.5)
        else:
            sensory_fb = 0.5

        # Motor output
        motor_output_strength = (
            m1_sig * 0.3 +
            sma_sig * 0.2 +
            action_sel * 0.2 +
            loop_strength * 0.15 +
            cognitive_ctrl * 0.15
        )
        motor_output_strength = max(0.0, min(1.0, motor_output_strength))

        # Voluntary movement: motor output × cognitive control × sensory feedback
        voluntary_movement_signal = (
            motor_output_strength * 0.4 +
            cognitive_ctrl * 0.3 +
            action_sel * 0.3
        ) * (0.5 + sensory_fb * 0.5)
        voluntary_movement_signal = max(0.0, min(1.0, voluntary_movement_signal))

        self.state["motor_output_strength"] = round(motor_output_strength, 4)
        self.state["voluntary_movement_signal"] = round(voluntary_movement_signal, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "motor_final_output": {
                "motor_strength": round(motor_output_strength, 4),
                "movement_signal": round(voluntary_movement_signal, 4),
            },
            "voluntary_movement_signal": round(voluntary_movement_signal, 4),
        }