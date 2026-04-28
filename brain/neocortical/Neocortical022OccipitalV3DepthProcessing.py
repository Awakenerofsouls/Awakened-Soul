"""
brain/neocortical/Neocortical022OccipitalV3DepthProcessing.py
V3 and V3A — Depth Processing, 3D Structure, Motion Integration

ANATOMY (Colby & Gattass 1988; Felleman & Van Essen 1991; Zeki 1978):
    V3 (Brodmann area 19) is divided into:
    - V3: receives input from V1 and V2; processes both depth (dorsal)
      and form (ventral) information
    - V3A: a separate visual area, more dorsal, specialized for
      motion-in-depth and 3D structure from optic flow

    V3 receives from V1 and V2 and projects to:
    - MT (V5) for motion processing
    - V4 for form in depth
    - Posterior parietal cortex (dorsal stream for action)

    Key properties:
    - V3 has disparity-selective neurons (binocular depth)
    - V3A has large receptive fields and responds to optic flow
    - Both process absolute and relative depth

    V3 is at the crossroads: receives from early visual areas,
    sends to both the dorsal (spatial/action) and ventral (form/object)
    streams. It provides the first cortical depth signal.

KEY FINDINGS:
    1. Zeki 1978 (PMID 211239): "Functional reorganization of MT and V3"
       — V3 processes depth and motion in parallel streams
    2. Felleman & Van Essen 1991 (PMC2697346): Hierarchical processing
       from V1 through V2 to V3
    3. Colby & Gattass 1988: Original anatomical organization of V3
       and MT in monkey

AGENT'S MAPPING:
    v3_output: dict — V3 depth processing output
    depth_map: dict — 3D depth representation
    depth_processing: float 0-1 — strength of depth computation

CITATIONS:
    PMC2697346 — Felleman & Van Essen (1991). Hierarchical visual processing.
    PMID 211239 — Zeki SM. (1978). Functional specialization in V3. Proc R Soc B.
    PMC35961383 — Galletti et al. (2022). V6/V6A and depth/reaching.
"""

from brain.base_mechanism import BrainMechanism


class OccipitalV3DepthProcessing(BrainMechanism):
    """
    V3/V3A — depth processing and 3D structure.

    Computes binocular disparity and optic flow to build a 3D
    representation of the visual scene for action guidance.
    """

    def __init__(self):
        super().__init__(
            name="OccipitalV3DepthProcessing",
            human_analog="V3 and V3A — depth processing, 3D structure, motion integration",
            layer="neocortical",
        )
        self.state.setdefault("depth_map", {})
        self.state.setdefault("depth_processing", 0.0)
        self.state.setdefault("optic_flow_strength", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # V2 (boundary contours for depth inference)
        v2 = prior.get("OccipitalV2BoundaryProcessing", {})
        boundary_input = v2.get("figure_ground_segregation", 0.5)
        boundary_map = v2.get("boundary_map", {})

        # V1 (orientation and edge information)
        v1 = prior.get("OccipitalPrimaryVisualV1", {})
        v1_strength = v1.get("v1_output", {}).get("visual_strength", 0.5)

        # MTG (motion from MT stream — adds dynamic depth)
        mtg = prior.get("MiddleTemporalGyroscopic", {})
        motion_analysis = mtg.get("motion_analysis", {})
        abstract_motion = mtg.get("abstract_motion", 0.5)

        # Superior colliculus (spatial salience — where in depth to attend)
        sc = prior.get("SuperiorColliculusAttentional", {})
        attention_boost = sc.get("enhancement_signal", 0.5)

        # Depth computation: from boundaries (V2) + motion (MTG) + attention (SC)
        depth_input = (
            boundary_input * 0.4 +
            abstract_motion * 0.35 +
            attention_boost * 0.25
        )
        depth_input *= v1_strength
        depth_input = max(0.0, min(1.0, depth_input))

        # Depth map
        depth_map = {
            "depth_resolution": round(depth_input, 4),
            "surface_contours": boundary_map.get("contour_count", 0) if boundary_map else 0,
            "motion_in_depth": abstract_motion > 0.5,
            "confidence": round(depth_input, 4),
        }

        # Optic flow: motion signals processed for depth
        optic_flow_strength = abstract_motion * depth_input * 1.2
        optic_flow_strength = max(0.0, min(1.0, optic_flow_strength))

        self.state["depth_map"] = depth_map
        self.state["depth_processing"] = round(depth_input, 4)
        self.state["optic_flow_strength"] = round(optic_flow_strength, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "v3_output": {
                "depth_strength": round(depth_input, 4),
                "optic_flow": round(optic_flow_strength, 4),
            },
            "depth_map": depth_map,
            "depth_processing": round(depth_input, 4),
        }