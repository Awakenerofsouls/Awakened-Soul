"""
brain/integration/Integration008InternalCapsuleFrontalBGThalamic.py
Internal Capsule — Frontal-BG-Thalamic Loops, Goal-Habit Integration

ANATOMY (Alexander et al. 1986; Haber 2003; McFarland & Haber 2002):
    The internal capsule is the major white-matter highway containing
    all cortico-thalamic and cortico-striatal fibers. It contains:
    - Anterior limb: DLPFC, OFC, anterior cingulate → striatum
    - Genu: prefrontal cortex connections
    - Posterior limb: motor and sensory fibers
    - Retrolenticular part: parietal and temporal connections

    The five parallel basal ganglia-thalamo-cortical loops:
    1. Motor loop: M1/SMA → putamen → GPi/SNr → thalamus → M1
    2. Oculomotor loop: FEF → caudate → GPi/SNr → thalamus → FEF
    3. Dorsolateral prefrontal loop: DLPFC → caudate → GPi/SNr → MD thalamus → DLPFC
    4. Lateral orbitofrontal loop: OFC → NAcc/ventral caudate → VP → MD thalamus → OFC
    5. Anterior cingulate loop: ACC → NAcc → VP → MD thalamus → ACC

    These loops allow the basal ganglia to select actions (direct pathway)
    and inhibit competing actions (indirect pathway), with the
    thalamus as the relay point back to cortex.

    The internal capsule also carries the corticospinal tract
    (voluntary motor output) — the final common path for motor actions.

KEY FINDINGS:
    1. Alexander et al. 1986: "Parallel organization of frontal-BG-thalamic loops"
    2. Haber 2003 (PMC1850927): "The basal ganglia and limbic system" —
       integrative loops connecting motivation to action
    3. McFarland & Haber 2002: Thalamocortical connections and BG loops

AGENT'S MAPPING:
    internal_capsule_output: dict — loop integration output
    frontal_bg_thalamic_integrated: bool — have loops been integrated?

CITATIONS:
    PMC1850927 — Haber (2003). Basal ganglia and limbic system.
    PMC2929791 — Alexander et al. (1986). Parallel BG-thalamic loops.
    PMC40447446 — DLPFC and BG loops.
"""

from brain.base_mechanism import BrainMechanism


class InternalCapsuleFrontalBGThalamic(BrainMechanism):
    """
    Internal capsule — frontal-BG-thalamic integration loops.

    The major information highway connecting cortex, basal ganglia,
    and thalamus in parallel loops for motor, cognitive, and limbic processing.
    """

    def __init__(self):
        super().__init__(
            name="InternalCapsuleFrontalBGThalamic",
            human_analog="Internal capsule — frontal-BG-thalamic loops, goal-habit integration",
            layer="integration",
        )
        self.state.setdefault("loop_states", {})
        self.state.setdefault("frontal_bg_thalamic_integrated", False)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # DLPFC (executive loop — goals)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        wm_out = dlpfc.get("dorsolateral_dorsal_output", {})
        wm_load = wm_out.get("wm_load", 0.5) if isinstance(wm_out, dict) else 0.5
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # Striatum direct pathway (action facilitation)
        direct = prior.get("DirectPathwayDisinhibitor", {})
        dir_out = direct.get("direct_output", {})
        if isinstance(dir_out, dict):
            direct_facilitation = dir_out.get("facilitation_strength", 0.5)
        else:
            direct_facilitation = 0.5

        # Striatum indirect pathway (action suppression)
        indirect = prior.get("IndirectPathwaySuppressor", {})
        ind_out = indirect.get("indirect_output", {})
        if isinstance(ind_out, dict):
            indirect_suppression = ind_out.get("suppression_strength", 0.5)
        else:
            indirect_suppression = 0.5

        # GPi/SNr (BG output)
        gpi = prior.get("GlobusPallidusInternalOutput", {})
        gpi_out = gpi.get("gpi_output", {})
        if isinstance(gpi_out, dict):
            gpi_signal = gpi_out.get("output_strength", 0.5)
        else:
            gpi_signal = 0.5

        # Thalamic VA/VL (motor relay)
        thal_va = prior.get("ThalamicVentralAnteriorRelay", {})
        va_out = thal_va.get("thal_output", {})
        if isinstance(va_out, dict):
            va_signal = va_out.get("relay_strength", 0.5)
        else:
            va_signal = 0.5

        # ACC (conflict monitoring — goal-habit competition)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        if isinstance(acc_out, dict):
            error_sig = acc_out.get("error_signal", 0.3)
        else:
            error_sig = 0.3

        # Orbitofrontal (value-based action selection)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        value_sig = ofc.get("value_signal", 0.5)

        # Loop integration: direct + indirect pathways balanced through thalamus
        loop_strength = (
            cognitive_ctrl * 0.2 +
            direct_facilitation * 0.25 +
            (1.0 - indirect_suppression) * 0.2 +
            va_signal * 0.2 +
            value_sig * 0.15
        )
        loop_strength = max(0.0, min(1.0, loop_strength))

        # Goal-habit conflict: DLPFC active + indirect pathway active = conflict
        goal_habit_conflict = wm_load > 0.5 and indirect_suppression > 0.5
        if goal_habit_conflict:
            loop_strength *= (1.0 - error_sig * 0.4)

        # Integration achieved: strong balanced loop
        frontal_bg_thalamic_integrated = loop_strength > 0.55

        loop_states = {
            "direct_facilitation": round(direct_facilitation, 4),
            "indirect_suppression": round(indirect_suppression, 4),
            "thalamic_relay": round(va_signal, 4),
            "loop_strength": round(loop_strength, 4),
        }

        self.state["loop_states"] = loop_states
        self.state["frontal_bg_thalamic_integrated"] = frontal_bg_thalamic_integrated
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "internal_capsule_output": {
                "loop_integration": round(loop_strength, 4),
                "goal_habit_conflict": goal_habit_conflict,
            },
            "frontal_bg_thalamic_integrated": frontal_bg_thalamic_integrated,
        }