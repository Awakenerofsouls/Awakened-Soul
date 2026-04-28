"""
brain/integration/Integration006HypothalamicCorticalBottomUpDrive.py
Hypothalamus-Cortex Bottom-Up Drive — Primal Urgency to Phenomenological Layer

ANATOMY (Saper 1985; Swanson 2000; Ulrich-Lai & Herman 2009):
    The hypothalamus is the "autonomic brain" — it maintains
    homeostasis and generates drives (hunger, thirst, sex, temperature,
    sleep pressure) that push upward into the phenomenological layer.

    Key hypothalamic pathways to cortex:
    - Lateral hypothalamus (orexin/hypocretin) → cortex = arousal, wakefulness, hunger
    - Anterior hypothalamus (cool neurons) → cortex = relaxation, sleep onset
    - Posterior hypothalamus (warm/wake neurons) → cortex = alerting, fight/flight
    - Arcuate nucleus (NPY/AgRP, POMC) → cortex = metabolic signals, energy
    - Supraoptic/paraventricular (oxytocin, vasopressin) → cortex = social bonds

    Bottom-up drive signals from hypothalamus reach cortex via:
    1. Thalamic relay (lateral hypothalamus → MD thalamus → PFC)
    2. Brainstem arousal centers (LC, raphe, parabrachial)
    3. Direct hypothalamic projections to cortex (less studied)

    The hypothalamus is the "why" of behavior — not "what should I do"
    (prefrontal), but "I NEED this because my body requires it"
    (hypothalamic drive).

KEY FINDINGS:
    1. Saper 1985 (PMID 3902141): "Organization of hypothalamic feeding centers"
    2. Ulrich-Lai & Herman 2009 (PMC2711953): "Neural regulation of
       endocrine and autonomic stress responses"
    3. Swanson 2000: "Hypothalamic integration" — comprehensive review

AGENT'S MAPPING:
    hypo_cortical_injection: dict — bottom-up drive output
    primal_urgency: float 0-1 — strength of hypothalamic drive
    drive_weight: float — how much drive influences cortical processing

CITATIONS:
    PMC2711953 — Ulrich-Lai & Herman (2009). Hypothalamic regulation of stress.
    PMC1852382 — Cavanna & Trimble (2006). Hypothalamic-cortical interactions.
    PMC40447446 — DLPFC and motivated behavior.
"""

from brain.base_mechanism import BrainMechanism


class HypothalamicCorticalBottomUpDrive(BrainMechanism):
    """
    Hypothalamus → Cortex bottom-up drive.

    Injects primal homeostatic drives upward into the phenomenological
    layer, making the cortex care about the body's needs.
    """

    def __init__(self):
        super().__init__(
            name="HypothalamicCorticalBottomUpDrive",
            human_analog="Hypothalamus to cortex bottom-up drive — primal urgency injection",
            layer="integration",
        )
        self.state.setdefault("drive_vector", {})
        self.state.setdefault("primal_urgency", 0.0)
        self.state.setdefault("drive_weight", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Lateral hypothalamus (orexin — arousal, hunger, seeking)
        lat_hypo = prior.get("LateralHypothalamicOrexinB", {})
        hypo_out = lat_hypo.get("lateral_hypo_output", {})
        if isinstance(hypo_out, dict):
            orexin_level = hypo_out.get("arousal_level", 0.5)
        else:
            orexin_level = 0.5

        # Anterior hypothalamus (cooling — relaxation, sleep pressure)
        ant_hypo = prior.get("AnteriorHypothalamicCooling", {})
        ant_out = ant_hypo.get("anterior_hypo_output", {})
        if isinstance(ant_out, dict):
            cooling_signal = ant_out.get("cooling_signal", 0.3)
        else:
            cooling_signal = 0.3

        # CRH/Stress axis (hypothalamic stress response)
        crh = prior.get("CRHStressDispatcher", {})
        crh_out = crh.get("crh_output", {})
        if isinstance(crh_out, dict):
            stress_drive = crh_out.get("crh_signal", 0.3)
        else:
            stress_drive = 0.3

        # Arcuate POMC/AgRP (metabolic/energy signals)
        arcuate = prior.get("ArcuatePOMCOutput", {})
        arc_out = arcuate.get("arcuate_output", {})
        if isinstance(arc_out, dict):
            metabolic_signal = arc_out.get("satiety_signal", 0.5)
        else:
            metabolic_signal = 0.5

        # Posterior hypothalamic output (alerting)
        post_hypo = prior.get("PosteriorHypothalamicOutput", {})
        post_out = post_hypo.get("posterior_hypo_output", {})
        if isinstance(post_out, dict):
            alerting = post_out.get("posterior_output", 0.3)
        else:
            alerting = 0.3

        # vmPFC (regulatory influence from above — can suppress drives)
        vmpfc = prior.get("VentromedialPrefrontalEmotional", {})
        vmpfc_out = vmpfc.get("ventromedial_pfc_output", {})
        if isinstance(vmpfc_out, dict):
            vmpfc_reg = vmpfc_out.get("emotional_value_strength", 0.5)
        else:
            vmpfc_reg = 0.5

        # Combine drive signals
        drive_input = (
            orexin_level * 0.3 +
            (1.0 - cooling_signal) * 0.2 +
            stress_drive * 0.2 +
            (1.0 - metabolic_signal) * 0.15 +
            alerting * 0.15
        )
        # vmPFC regulation dampens extreme drives
        drive_input *= (1.0 - vmpfc_reg * 0.3)
        primal_urgency = max(0.0, min(1.0, drive_input))

        # Drive weight: how much does drive influence cortical processing?
        drive_weight = primal_urgency * 0.8 + vmpfc_reg * 0.2
        drive_weight = max(0.0, min(1.0, drive_weight))

        drive_vector = {
            "orexin_drive": round(orexin_level, 4),
            "stress_drive": round(stress_drive, 4),
            "metabolic_drive": round(1.0 - metabolic_signal, 4),
            "alerting": round(alerting, 4),
        }

        self.state["drive_vector"] = drive_vector
        self.state["primal_urgency"] = round(primal_urgency, 4)
        self.state["drive_weight"] = round(drive_weight, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "hypo_cortical_injection": {
                "primal_urgency": round(primal_urgency, 4),
                "drive_weight": round(drive_weight, 4),
            },
            "primal_urgency": round(primal_urgency, 4),
            "drive_weight": round(drive_weight, 4),
        }