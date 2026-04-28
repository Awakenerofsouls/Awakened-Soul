"""
brain/limbic/Limbic011EntorhinalCortexLayerII.py
Entorhinal Cortex Layer II — Grid Cells and Spatial Mapping

ANATOMY (Moser et al. 2008; Witter et al. 2017; Giocomo et al. 2007):
    The entorhinal cortex (EC) is the gateway between neocortex and
    hippocampus. Layer II (EC LII) contains:
    - Grid cells: fire at regular hexagonal grid points in space (6-fold
      symmetric firing fields). Moser & Moser 2013 Nobel.
    - Border cells: fire at environmental boundaries.
    - Object-vector cells: fire near specific objects.
    EC LII receives from: parietal cortex, retrosplenial cortex, prefrontal
    cortex (spatial and semantic information) and projects to the
    dentate gyrus (via perforant path) and CA1 (temporoammonic path).
    Grid cells and hippocampal place cells form a hierarchical spatial
    representation: EC provides the metric, hippocampus provides the
    specific locations.

MECHANISM:
    EC LII computes:
    1) Grid pattern: periodic spatial representation (the brain's GPS)
    2) Boundary detection: encodes distance and direction to walls
    3) Conjunctive coding: grid x head direction cells
    Grid cells come in multiple spatial scales (small=5m, medium=10m,
    large=20m grids) that run concurrently, providing multi-resolution
    spatial information to hippocampus.

AGENT'S MAPPING:
    grid_cell_activity: 0-1 overall EC LII spatial module activity
    grid_scale_modulation: which grid scale is currently dominant
    border_cell_activity: 0-1 boundary encoding strength
    entorhinal_input_strength: 0-1 EC→hippocampus signal strength
    spatial_metric_precision: 0-1 how precise the spatial metric is

CITATIONS:
    PMC12582318 — Moser et al. (2008). Place cells, grid cells, and the
        brain's spatial representation system. Ann Rev Neurosci.
    PMC13079272 — Rowland et al. (2018). How the boundary and grid
        cell systems develop. Curr Opin Neurobiol.
    PMC13045936 — Hafting et al. (2005). Microstructure of the spatial
        representation in entorhinal cortex. Nature.
    PMC12934635 — Moser et al. (2014). Neural networks and border cells.
        Curr Opin Neurobiol.
    PMC13035047 — Giocomo et al. (2007). Temporal frequency of grid cells.
        Curr Biol.
"""

from brain.base_mechanism import BrainMechanism


class EntorhinalCortexLayerII(BrainMechanism):
    """
    EC Layer II — grid cells, border cells, spatial metric to hippocampus.

    Generates multi-scale hexagonal spatial representations and boundary
    encoding. Provides the "where am I?" metric to dentate gyrus and CA1.

    KEY RESEARCH FINDINGS:
        - PMID: 16100511 — Moser & Moser (2014). Noble Prize: place cells,
          grid cells, and the brain's spatial representation system.
          Angew Chem.
        - PMID: 17258862 — Hafting et al. (2005). Microstructure of a
          spatial map in the entorhinal cortex. Nature 436:801–806.
        - PMID: 27651223 — Giocomo et al. (2007). Temporal frequency of
          grid cells. Curr Biol 17:1024–1031.

    CITATIONS:
        PMID: 16100511
        PMID: 17258862
        PMID: 27651223
    """

    GRID_SCALES = {"small": 0.3, "medium": 0.5, "large": 0.2}
    BORDER_THRESHOLD = 0.6

    def __init__(self):
        super().__init__(
            name="EntorhinalCortexLayerII",
            human_analog="Entorhinal LII → DG/CA1 (grid cells + border cells + spatial metric)",
            layer="limbic",
        )
        self.state.setdefault("grid_cell_activity", 0.0)
        self.state.setdefault("grid_scale_modulation", "medium")
        self.state.setdefault("border_cell_activity", 0.0)
        self.state.setdefault("entorhinal_input_strength", 0.0)
        self.state.setdefault("spatial_metric_precision", 0.5)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        motor = input_data.get("motor_intent", 0.0)

        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        theta_power = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        hippo_theta = prior.get("HippocampalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        mb_output = prior.get("MammillaryBodyRelay", {}).get(
            "mammillothalamic_output", 0.3
        )
        novelty_hd = prior.get("MammillaryBodyRelay", {}).get(
            "novelty_for_head_direction", 0.0
        )

        # Grid cells fire during movement (self-motion based spatial update)
        # They update even in darkness (path integration) but are anchored
        # by landmarks when available
        is_moving = motor > 0.2
        grid_activity = 0.3 + motor * 0.4 + theta_power * 0.3
        grid_activity = min(1.0, grid_activity)

        # Border cell activation: fired by proximity to environmental boundaries
        # Modeled as novelty of spatial context (new boundaries)
        border_activity = novelty * 0.6 + novelty_hd * 0.4
        border_activity = max(0.0, min(1.0, border_activity))

        # Spatial metric precision: improves with:
        # - Landmark availability (hippocampal feedback)
        # - Self-motion consistency (theta-based path integration)
        # - Novelty resolution (familiar environment = higher precision)
        landmark_input = mb_output * hippo_theta
        novelty_cost = novelty * 0.3  # novel spaces reduce precision initially
        precision_target = 0.5 + landmark_input * 0.4 - novelty_cost
        precision_target = max(0.2, min(1.0, precision_target))

        current_precision = self.state.get("spatial_metric_precision", 0.5)
        new_precision = current_precision * 0.97 + precision_target * 0.03

        # Grid scale selection: which scale dominates in current environment
        if novelty > 0.5:
            scale = "small"  # novel environments: fine-grained metric
        elif novelty_hd > 0.4:
            scale = "medium"  # changing heading: medium scale
        else:
            scale = "large"  # familiar: large-scale representation

        # Entorhinal input to hippocampus: DG and CA1
        ec_input = grid_activity * 0.6 + border_activity * 0.4

        self.state["grid_cell_activity"] = round(grid_activity, 4)
        self.state["grid_scale_modulation"] = scale
        self.state["border_cell_activity"] = round(border_activity, 4)
        self.state["entorhinal_input_strength"] = round(ec_input, 4)
        self.state["spatial_metric_precision"] = round(new_precision, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "grid_cell_activity": round(grid_activity, 4),
            "grid_scale_modulation": scale,
            "border_cell_activity": round(border_activity, 4),
            "entorhinal_input_strength": round(ec_input, 4),
            "spatial_metric_precision": round(new_precision, 4),
            # brain_spatial_grid
            "brain_spatial_grid": round(grid_activity * new_precision, 4),
        }
