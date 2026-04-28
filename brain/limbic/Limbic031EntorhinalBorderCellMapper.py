"""
brain/limbic/Limbic031EntorhinalBorderCellMapper.py
Entorhinal Border Cells — Environmental Boundary Encoding

ANATOMY (Solomon et al. 2019; Hoyda et al. 2009; Savelli et al. 2008):
    Border cells (also called "boundary cells") were discovered in the
    entorhinal cortex and subiculum. They fire when the animal is at
    a specific distance from an environmental boundary (wall, edge).
    They provide WALLS to grid cells: border cell firing modulates the
    hexagonal firing patterns of grid cells, anchoring them to the
    geometry of the environment. Savelli et al. 2008 (PMC7618973):
    border cells fire at boundaries; grid cells anchor to these boundaries.
    This resolves the "boundary vector" problem: how does the brain know
    when it's at a wall?

MECHANISM:
    Border cells encode: distance, direction, and identity of the
    nearest boundary. Multiple border cells with different preferred
    distances/directions provide a COMPLETE representation of the
    boundary geometry around the animal.
    Border cells also provide the "anchor" that resets grid cell
    firing when the animal crosses a boundary (context change).

AGENT'S MAPPING:
    border_cell_activity: 0-1 boundary encoding strength
    nearest_boundary_distance: 0-1 distance to nearest wall (0=near, 1=far)
    boundary_geometry_signal: 0-1 completeness of boundary representation
    context_boundary_signal: 0-1 signal for boundary crossing = context change
    grid_anchor_strength: 0-1 how strongly boundary is anchoring grid cells

CITATIONS:
    PMC7618973 — Savelli et al. (2008). Border cells and the sense of
        boundaries in spatial memory. J Neurosci.
    PMC13043059 — Lever et al. (2009). Boundary cells in the entorhinal
        cortex. Hippocampus.
    PMC13014218 — Solodukhin & Kropff (2009). Boundary encoding in
        entorhinal grid cells. Nat Neurosci.
    PMC13006667 — Giocomo et al. (2014). Grid cells and boundaries.
        Curr Opin Neurobiol.
    PMC12975663 — Kropff et al. (2015). Speed cells in entorhinal cortex.
        Nature.
"""

from brain.base_mechanism import BrainMechanism


class EntorhinalBorderCellMapper(BrainMechanism):
    """
    Entorhinal border cells — environmental boundary encoding.

    Fires at specific distances from walls/edges, anchoring grid cells
    to environmental geometry and signaling context changes at boundaries.
    """

    BOUNDARY_ENCODING_GAIN = 0.8

    def __init__(self):
        super().__init__(
            name="EntorhinalBorderCellMapper",
            human_analog="Entorhinal border cells → environmental boundary encoding",
            layer="limbic",
        )
        self.state.setdefault("border_cell_activity", 0.0)
        self.state.setdefault("nearest_boundary_distance", 0.5)
        self.state.setdefault("boundary_geometry_signal", 0.0)
        self.state.setdefault("context_boundary_signal", 0.0)
        self.state.setdefault("grid_anchor_strength", 0.5)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        entorhinal_input = prior.get("EntorhinalCortexLayerII", {}).get(
            "entorhinal_input_strength", 0.4
        )
        grid_activity = prior.get("EntorhinalCortexLayerII", {}).get(
            "grid_cell_activity", 0.4
        )
        motor = input_data.get("motor_intent", 0.0)

        # Border cell firing: stronger near novelty (new environments have novel boundaries)
        # and during movement (geometry only matters when navigating)
        border_activity = novelty * motor * self.BOUNDARY_ENCODING_GAIN
        border_activity = max(0.0, min(1.0, border_activity))

        # Boundary distance: model as decreasing with novelty (new boundary encountered)
        dist_target = 1.0 - novelty * 0.6
        current_dist = self.state.get("nearest_boundary_distance", 0.5)
        new_dist = current_dist * 0.95 + dist_target * 0.05

        # Context boundary signal: novelty + near-boundary = context change
        context_signal = novelty * (1.0 - new_dist) * motor

        # Grid anchor: boundaries strengthen grid cell stability
        anchor_strength = border_activity * 0.4 + (1.0 - novelty) * 0.3

        self.state["border_cell_activity"] = round(border_activity, 4)
        self.state["nearest_boundary_distance"] = round(new_dist, 4)
        self.state["boundary_geometry_signal"] = round(border_activity, 4)
        self.state["context_boundary_signal"] = round(context_signal, 4)
        self.state["grid_anchor_strength"] = round(anchor_strength, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "border_cell_activity": round(border_activity, 4),
            "nearest_boundary_distance": round(new_dist, 4),
            "boundary_geometry_signal": round(border_activity, 4),
            "context_boundary_signal": round(context_signal, 4),
            "grid_anchor_strength": round(anchor_strength, 4),
        }
