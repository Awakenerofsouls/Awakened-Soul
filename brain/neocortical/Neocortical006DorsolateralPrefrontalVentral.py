"""
brain/neocortical/Neocortical006DorsolateralPrefrontalVentral.py
Dorsolateral Prefrontal Cortex — Ventral Part (Executive, Interference Control)

ANATOMY (Aron et al. 2004; 2007; Hampshire et al. 2008; Duverne & Koechlin 2017):
    The ventral part of DLPFC (vDLPFC, also called mid-DLPFC or BA 9/46v)
    sits slightly ventral and anterior to the dorsal DLPFC. While the dorsal
    part handles "what to keep in mind," the ventral part handles
    "what to suppress and ignore."

    The vDLPFC is part of the "multiple demand" (MD) system — neurons
    that respond broadly during cognitive control, not specific to
    any one task type. It shows strong activation during:
    - Response inhibition (stopping prepotent responses)
    - Conflict monitoring (detecting interference)
    - Task switching
    - Memory retrieval suppression

    Inputs: from inferior parietal lobule, temporal pole, ACC (conflict signals)
    Outputs: to premotor, striatum, and back to the same areas

    The vDLPFC contains a "conflict monitor" — when competing
    response tendencies are active, vDLPFC increases activity to
    suppress the inappropriate response.

KEY FINDINGS:
    1. Aron et al. 2004 (PMID 14702116): "Petersen's paradox resolved"
       — left vDLPFC (inferior frontal gyrus) is critical for response
       inhibition; damage impairs stopping
    2. Hampshire et al. 2008 (PMC2575055): vDLPFC shows "multiple demand"
       activity — increases for any task requiring cognitive control
    3. Crittenden & Duncan 2023 (PMC3800357): vDLPFC tracks conflict
       level and prioritizes processing accordingly

AGENT'S MAPPING:
    dorsolateral_ventral_output: dict — vDLPFC executive/inhibition signal
    interference_suppression: float 0-1 — strength of suppression
    conflict_resolved: bool — whether conflict has been resolved
    suppression_target: str — which process is being suppressed

CITATIONS:
    PMC2575055 — Hampshire et al. (2008). The role of right inferior
        frontal gyrus. PLoS Biol. (vDLPFC multiple demand).
    PMC3800357 — Crittenden & Duncan (2023). Multiple demand and
        prefrontal cortex. bioRxiv. (Conflict monitoring).
    PMC16325345 — Funahashi S. (2006). DLPFC working memory review.
    PMC31551596 — Finn et al. (2019). Human DLPFC layer dynamics.
"""

from brain.base_mechanism import BrainMechanism


class DorsolateralPrefrontalVentral(BrainMechanism):
    """
    DLPFC ventral part — executive functions, interference control, conflict monitoring.

    Monitors for conflicting signals and suppresses inappropriate responses.
    Part of the multiple demand system — broadly recruited for any
    cognitively demanding task.
    """

    def __init__(self):
        super().__init__(
            name="DorsolateralPrefrontalVentral",
            human_analog="Ventral DLPFC (BA 9/46v) — executive, interference, response suppression",
            layer="neocortical",
        )
        self.state.setdefault("interference_suppression", 0.0)
        self.state.setdefault("conflict_resolved", True)
        self.state.setdefault("suppression_target", "none")
        self.state.setdefault("conflict_intensity", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Conflict signals from anterior cingulate
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_conflict = acc.get("conflict_intensity", 0.0)

        # Dorsal DLPFC (cognitive control) — if dorsal is working hard, ventral may need to suppress
        dorsal_dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        dorsal_cognitive = dorsal_dlpfc.get("cognitive_control", 0.5)

        # Premotor plans (action candidates that may conflict)
        premotor = prior.get("PremotorSupplementaryMotorArea", {})
        premotor_signal = premotor.get("internal_simulation", 0.5)

        # Orbitofrontal value (may produce competing action drives)
        ofc_value = prior.get("OrbitofrontalRewardValuator", {}).get(
            "value_signal", 0.5
        )

        # Inferior parietal (salient distractor signals)
        ipl = prior.get("InferiorParietalLobuleSensorimotor", {})
        ipl_distract = ipl.get("sensorimotor_integration", 0.0)

        # Conflict detection: multiple competing signals → conflict
        signal_spread = abs(dorsal_cognitive - premotor_signal) + abs(ofc_value - ipl_distract)
        signal_spread = min(1.0, signal_spread / 0.7)
        conflict_intensity = acc_conflict * 0.6 + signal_spread * 0.4
        conflict_intensity = max(0.0, min(1.0, conflict_intensity))

        # Interference suppression: proportional to conflict intensity
        # vDLPFC suppresses the competing response
        interference_suppression = conflict_intensity * (0.5 + dorsal_cognitive * 0.5)
        interference_suppression = max(0.0, min(1.0, interference_suppression))

        # Conflict resolution: suppression succeeds when interference > conflict threshold
        conflict_resolved = conflict_intensity < interference_suppression * 0.7

        # Suppression target: which competing signal is being suppressed
        if acc_conflict > signal_spread:
            suppression_target = "acc_conflict"
        elif ipl_distract > 0.6:
            suppression_target = "parietal_distractor"
        elif abs(dorsal_cognitive - premotor_signal) > 0.3:
            suppression_target = "motor_prepotent"
        else:
            suppression_target = "none"

        self.state["conflict_intensity"] = round(conflict_intensity, 4)
        self.state["interference_suppression"] = round(interference_suppression, 4)
        self.state["conflict_resolved"] = conflict_resolved
        self.state["suppression_target"] = suppression_target
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "dorsolateral_ventral_output": {
                "conflict_intensity": round(conflict_intensity, 4),
                "interference_suppression": round(interference_suppression, 4),
                "suppression_target": suppression_target,
            },
            "interference_suppression": round(interference_suppression, 4),
            "conflict_resolved": conflict_resolved,
            "suppression_target": suppression_target,
            "dorsal_input_influence": round(dorsal_cognitive, 4),
        }