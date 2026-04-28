"""
brain/neocortical/Neocortical048PosteriorParietalCortexIntegration.py
Posterior Parietal Cortex — Full Sensorimotor Integration, Body-in-Space Planning

ANATOMY (Colby & Goldberg 1999; Andersen et al. 1997; Buneat et al. 2013):
    The posterior parietal cortex (PPC) is the "sensorimotor integration"
    hub — where sensory information is transformed into motor plans.
    It sits at the crown of the brain, at the junction of visual,
    auditory, somatosensory, and vestibular inputs.

    PPC has multiple subregions with different functions:
    - SPL (superior parietal lobule): reaching, spatial attention
    - IPL (inferior parietal lobule): grasping, tool use
    - MIP (medial intraparietal): visual guidance of reaching
    - AIP (anterior intraparietal): grasp formation
    - VIP (ventral intraparietal): vestibular, self-motion
    - PIP (posterior intraparietal): depth perception

    PPC is the "where and how" pathway endpoint:
    - WHERE: spatially directed actions (reaching, looking)
    - HOW: object-directed actions (grasping, manipulating)

    PPC connects to:
    - M1 (motor execution via premotor)
    - FEF (frontal eye fields, eye movement control)
    - LIP (lateral intraparietal, saccade planning)
    - Thalamus (sensory relay)
    - Cerebellum (sensorimotor learning)

KEY FINDINGS:
    1. Colby & Goldberg 1999 (PMC18279991): "Space and attention
       in PPC" — PPC as sensorimotor integration hub
    2. Andersen et al. 1997: PPC parietal reach region (PRR) and
       LIP for eye movements
    3. Buneat et al. 2013 (PMC37572972): PPC and reach-to-grasp planning

AGENT'S MAPPING:
    ppc_output: dict — PPC full integration output
    body_target_integration: float 0-1 — body position + target binding
    spatial_plan: dict — motor plan in spatial coordinates

CITATIONS:
    PMC18279991 — Colby & Goldberg (1999). PPC and attention.
    PMC37572972 — Sulpizio et al. (2023). SPL functional organization.
    PMC35961383 — Galletti et al. (2022). V6/V6A and reaching.
    PMC10437391 — Binkofski et al. (1999). Action representation in IPL.
"""

from brain.base_mechanism import BrainMechanism


class PosteriorParietalCortexIntegration(BrainMechanism):
    """
    PPC — full sensorimotor integration for motor planning.

    Integrates body position, spatial target, and action context
    into a complete motor plan for the body's movement in space.
    """

    def __init__(self):
        super().__init__(
            name="PosteriorParietalCortexIntegration",
            human_analog="Posterior parietal cortex — sensorimotor integration, body-in-space, motor planning",
            layer="neocortical",
        )
        self.state.setdefault("body_schema", {})
        self.state.setdefault("body_target_integration", 0.0)
        self.state.setdefault("spatial_plan", {})
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # S1 (body schema — where is my body right now?)
        s1 = prior.get("PostcentralGyrusPrimarySomato", {})
        body_schema = s1.get("body_schema", {})
        body_grounding = s1.get("tactile_processing", 0.5)

        # SPL (reaching signal — where to reach?)
        spl = prior.get("SuperiorParietalLobuleReaching", {})
        reaching_sig = spl.get("reaching_signal", 0.5)
        spatial_target = spl.get("spatial_target", {})

        # IPL (grasp planning — how to grasp?)
        ipl = prior.get("InferiorParietalLobuleSensorimotor", {})
        ipl_int = ipl.get("sensorimotor_integration", 0.5)
        grasp_plan = ipl.get("grasp_planning", 0.5)

        # TPJ (multisensory body location — where am I in space?)
        tpj = prior.get("TemporoParietoOccipitalJunction", {})
        spatial_awareness = tpj.get("spatial_awareness", 0.5)
        multimodal_conv = tpj.get("multisensory_converged", False)

        # DLPFC (goal context — what am I trying to achieve?)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # V3 (depth — how far is the target?)
        v3 = prior.get("OccipitalV3DepthProcessing", {})
        depth_map = v3.get("depth_map", {})
        depth_strength = v3.get("depth_processing", 0.5)

        # Body-target integration: body schema + spatial target + depth
        body_target_integration = (
            body_grounding * 0.25 +
            spatial_awareness * 0.2 +
            reaching_sig * 0.25 +
            ipl_int * 0.2 +
            depth_strength * 0.1
        )
        if cognitive_ctrl > 0.6:
            body_target_integration *= (1.0 + (cognitive_ctrl - 0.6) * 0.3)
        body_target_integration = max(0.0, min(1.0, body_target_integration))

        # Spatial plan: reaching + grasping + depth + goal
        spatial_plan = {
            "reach_intended": reaching_sig > 0.5,
            "grasp_intended": grasp_plan > 0.5,
            "depth_resolved": depth_strength > 0.5,
            "goal_directed": cognitive_ctrl > 0.6,
            "confidence": round(body_target_integration, 4),
        }

        self.state["body_schema"] = body_schema
        self.state["body_target_integration"] = round(body_target_integration, 4)
        self.state["spatial_plan"] = spatial_plan
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ppc_output": {
                "body_target_integration": round(body_target_integration, 4),
                "spatial_plan": spatial_plan,
            },
            "body_target_integration": round(body_target_integration, 4),
            "spatial_plan": spatial_plan,
        }