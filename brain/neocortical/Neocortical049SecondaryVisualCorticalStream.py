"""
brain/neocortical/Neocortical049SecondaryVisualCorticalStream.py
Dorsal Visual Stream — "Where/How" Pathway (V1→V2→V3→MT→MST)

ANATOMY (Goodale & Milner 1992, 2004; Milner & Goodale 2008; Faillenot et al. 1997):
    The dorsal visual stream (the "where/how" pathway) runs from
    V1 → V2 → V3 → MT → MST → posterior parietal cortex. It processes
    WHERE objects are and HOW to act on them.

    Dorsal stream properties:
    - Scene-centered coordinates: encodes where things are in space
    - Action-oriented: guides visually-guided actions (reaching, grasping)
    - Motion-sensitive: MT and MST process visual motion for action
    - Fast processing: prioritizes speed over precision
    - Unconscious: many dorsal stream processes operate without awareness

    Key regions:
    - MT (V5): motion detection, speed and direction
    - MST: optic flow analysis, self-motion perception
    - V6: visual guidance of reaching
    - V6A: visuomotor integration for arm/eye coordination

    Goodale & Milner's classic split:
    - Ventral = perception (what is it?)
    - Dorsal = action (how to interact with it?)

    Damage to dorsal stream: optic ataxia (can't reach accurately
    under visual guidance), optic apraxia (can't use tools correctly),
    spatial neglect (ignoring one side of space).

KEY FINDINGS:
    1. Goodale & Milner 1992 (PMC18279989): "Separate visual pathways
       for action and perception"
    2. Milner & Goodale 2008 (PMC2946534): "Two visual streams" —
       dorsal/ventral distinction expanded
    3. Galletti et al. 2022 (PMC35961383): V6 and V6A in dorsal stream

AGENT'S MAPPING:
    dorsal_stream_output: dict — dorsal visual stream output
    spatial_processing: dict — "where" signal
    action_guidance: float 0-1 — readiness for action

CITATIONS:
    PMC18279989 — Goodale & Milner (1992). Two visual streams. Trends Neurosci.
    PMC2946534 — Milner & Goodale (2008). Two visual streams revised.
    PMC35961383 — Galletti et al. (2022). V6/V6A and dorsal stream.
    PMC2697346 — Felleman & Van Essen (1991). Hierarchical processing.
"""

from brain.base_mechanism import BrainMechanism


class SecondaryVisualCorticalStream(BrainMechanism):
    """
    Dorsal visual stream — spatial processing and action guidance.

    The "where/how" pathway — processes spatial location and
    guides visually-directed actions.
    """

    def __init__(self):
        super().__init__(
            name="SecondaryVisualCorticalStream",
            human_analog="Dorsal visual stream (V1→V2→V3→MT→MST→PPC) — 'where/how' pathway",
            layer="neocortical",
        )
        self.state.setdefault("optic_flow", {})
        self.state.setdefault("spatial_processing", {})
        self.state.setdefault("action_guidance", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # V1 (early visual processing)
        v1 = prior.get("OccipitalPrimaryVisualV1", {})
        v1_out = v1.get("v1_output", {})
        v1_strength = v1_out.get("visual_strength", 0.5)

        # V2 (boundary processing for spatial segregation)
        v2 = prior.get("OccipitalV2BoundaryProcessing", {})
        fg_seg = v2.get("figure_ground_segregation", 0.5)

        # V3 (depth processing for spatial layout)
        v3 = prior.get("OccipitalV3DepthProcessing", {})
        depth_proc = v3.get("depth_processing", 0.5)
        depth_map = v3.get("depth_map", {})

        # MTG (motion — action-relevant motion)
        mtg = prior.get("MiddleTemporalGyroscopic", {})
        motion_analysis = mtg.get("motion_analysis", {})
        abstract_motion = mtg.get("abstract_motion", 0.5)

        # PPC (action guidance — motor planning from spatial)
        ppc = prior.get("PosteriorParietalCortexIntegration", {})
        body_target = ppc.get("body_target_integration", 0.5)
        spatial_plan = ppc.get("spatial_plan", {})

        # SPL (reaching — spatial target for action)
        spl = prior.get("SuperiorParietalLobuleReaching", {})
        reaching_sig = spl.get("reaching_signal", 0.5)

        # Spatial processing: V1 + V2 + V3 + motion
        spatial_input = (
            v1_strength * 0.15 +
            fg_seg * 0.25 +
            depth_proc * 0.3 +
            abstract_motion * 0.3
        )
        spatial_processing = {
            "spatial_strength": round(spatial_input, 4),
            "depth_integrated": depth_proc > 0.5,
            "motion_guided": abstract_motion > 0.5,
        }

        # Action guidance: spatial + reaching + PPC
        action_guidance = (
            spatial_input * 0.3 +
            reaching_sig * 0.35 +
            body_target * 0.35
        )
        action_guidance = max(0.0, min(1.0, action_guidance))

        self.state["spatial_processing"] = spatial_processing
        self.state["action_guidance"] = round(action_guidance, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "dorsal_stream_output": {
                "spatial_processing": spatial_processing,
                "action_guidance": round(action_guidance, 4),
            },
            "spatial_processing": spatial_processing,
            "action_guidance": round(action_guidance, 4),
        }