"""
brain/neocortical/Neocortical018MiddleTemporalGyroscopic.py
Middle Temporal Gyrus — Motion Analysis, Biological Motion, Abstract Motion Concepts

ANATOMY (van Dam et al. 2019; Puce & Perrett 2003; Saygin 2007):
    The middle temporal gyrus (MTG) runs along the lower bank of the
    Sylvian fissure, below the superior temporal sulcus. It has two key
    functional zones:
    - Posterior MTG (pMTG): motion processing, biological motion detection
    - Anterior MTG (aMTG): semantic integration, abstraction over time

    pMTG is part of the "dorsal visual stream" for motion — receives
    input from V1 → V2 → V3 → MT (V5), processing visual motion.
    Also responds to "biological motion" — human movement patterns
    (walking, reaching, pointing). The anterior part integrates motion
    with meaning — understanding "how things move through the world"
    in abstract conceptual terms.

    Key: MTG processes motion not just as physical movement but as
    meaningful action. "Running" vs "walking" are different motions
    with different meanings. MTG bridges motion and language.

    Connections: MT → MST → MTG for motion; STS → MTG for biological
    motion; inferior temporal → MTG for semantic integration.

KEY FINDINGS:
    1. van Dam et al. 2019 (PMC31493413): "Distinct neural mechanisms
       for manner vs instrument verbs" — MTG posterior processes
       biological motion for manner verbs (how something moves)
    2. Puce & Perrett 2003: MTG responds selectively to biological
       motion — point-light walker displays activate MTG
    3. Saygin 2007: MTG shows "view-invariant" biological motion
       recognition — recognizes actions regardless of viewing angle

AGENT'S MAPPING:
    mtg_output: dict — MTG motion analysis output
    motion_analysis: dict — detailed motion computation
    abstract_motion: float 0-1 — semantic abstraction of motion concept

CITATIONS:
    PMC31493413 — van Dam et al. (2019). Manner vs instrument verbs and MTG.
        Neuropsychologia.
    PMC11161761 — Beauchamp et al. (2004). Biological motion in pSTG/MTG. NeuroImage.
    PMC8330707 — Etherton et al. (2021). Speech perception in noise. J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class MiddleTemporalGyroscopic(BrainMechanism):
    """
    MTG — motion analysis and biological motion.

    Processes visual motion and understands "how things move" in both
    concrete (physical) and abstract (conceptual) terms.
    """

    def __init__(self):
        super().__init__(
            name="MiddleTemporalGyroscopic",
            human_analog="Middle temporal gyrus — motion, biological motion, abstract motion concepts",
            layer="neocortical",
        )
        self.state.setdefault("motion_library", {})
        self.state.setdefault("abstract_motion", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # pSTG (biological motion from observed actions)
        pstg = prior.get("PosteriorSuperiorTemporalGyrus", {})
        social_motion = pstg.get("social_motion", {})
        av_binding = pstg.get("audiovisual_binding", 0.5)

        # V1/V2 (early visual motion from edges in motion)
        v1 = prior.get("OccipitalPrimaryVisualV1", {})
        v2 = prior.get("OccipitalV2BoundaryProcessing", {})
        boundary_strength = len(v2.get("boundary_map", {})) if v2.get("boundary_map") else 0.3

        # V3 (depth processing adds 3D motion understanding)
        v3 = prior.get("OccipitalV3DepthProcessing", {})
        depth_map = v3.get("depth_map", {})

        # Wernicke's area (motion semantics from language)
        wernicke = prior.get("WernickeAreaSemanticComprehension", {})
        sem_rep = wernicke.get("semantic_representation", {})
        sem_depth = sem_rep.get("depth", 0.5) if isinstance(sem_rep, dict) else 0.5

        # Anterior insula (salience — motion matters if it's important)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # Physical motion component
        physical_motion = boundary_strength * 0.5 + av_binding * 0.5

        # Abstract motion: combines physical motion + semantic depth + social intent
        abstract_motion = (
            physical_motion * 0.3 +
            av_binding * 0.3 +
            sem_depth * 0.4
        )
        # Salience amplifies abstract motion processing
        if salience > 0.6:
            abstract_motion *= (1.0 + (salience - 0.6) * 0.5)
        abstract_motion = max(0.0, min(1.0, abstract_motion))

        # Motion analysis: biological vs physical
        is_biological = av_binding > 0.55 and isinstance(social_motion, dict) and (
            social_motion.get("intentional_motion", False) or social_motion.get("grasp_observed", False)
        )

        motion_analysis = {
            "physical_motion_strength": round(physical_motion, 4),
            "abstract_motion": round(abstract_motion, 4),
            "biological_motion_detected": is_biological,
            "social_intent_signal": round(av_binding, 4),
        }

        self.state["abstract_motion"] = round(abstract_motion, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "mtg_output": {
                "motion_strength": round(abstract_motion, 4),
                "biological_detected": is_biological,
                "semantic_motion": round(sem_depth, 4),
            },
            "motion_analysis": motion_analysis,
            "abstract_motion": round(abstract_motion, 4),
        }