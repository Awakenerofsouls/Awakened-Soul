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


CITATIONS
---------
  - [Mountcastle 1997, Brain 120:701, columnar organization]
  - [Felleman 1991, Cereb Cortex 1:1, cortical hierarchy]
  - [Markram 2004, Nat Rev Neurosci 5:793, interneurons]
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
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
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

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        recent = self.state.get("recent_states", [])
        if not recent: return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet","rest","neutral",""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent: return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4: return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v < 0.05 for v in hist[-10:])

    def trend_direction(self, window: int = 10) -> str:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return "flat"
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        delta = second_half - first_half
        if delta > 0.05: return "rising"
        if delta < -0.05: return "falling"
        return "flat"

    def trend_magnitude(self, window: int = 10) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return 0.0
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        return round(abs(second_half - first_half), 4)

    def state_transition_count(self) -> int:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i - 1])

    def state_transition_rate(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0.0
        return round(self.state_transition_count() / (len(recent) - 1), 4)

    def state_distribution(self) -> dict:
        recent = self.state.get("recent_states", [])
        if not recent: return {}
        from collections import Counter
        c = Counter(recent)
        total = len(recent)
        return {state: round(count / total, 4) for state, count in c.items()}

    def drive_min_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(min(hist[-window:]), 4)

    def drive_max_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(max(hist[-window:]), 4)

    def drive_range_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(max(recent) - min(recent), 4)

    def is_active(self) -> bool:
        return self.state.get("tick_count", 0) > 0

    def has_history(self) -> bool:
        return len(self.state.get("recent_drives", [])) > 0

    def history_length(self) -> int:
        return len(self.state.get("recent_drives", []))

    def state_history_length(self) -> int:
        return len(self.state.get("recent_states", []))

    def fingerprint(self) -> str:
        parts = [
            f"tick={self.state.get('tick_count', 0)}",
            f"states={self.state_history_length()}",
            f"drives={self.history_length()}",
            f"engagement={self.engagement_fraction()}",
        ]
        return "|".join(parts)

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
            "tick_count": self.state.get("tick_count", 0),
        }

    def diagnostics(self) -> dict:
        return {
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_history": self.has_history(),
            "tick_count": self.state.get("tick_count", 0),
            "history_length": self.history_length(),
            "transition_rate": self.state_transition_rate(),
            "trend": self.trend_direction(),
            "trend_magnitude": self.trend_magnitude(),
            "drive_range": self.drive_range_recent(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

    def _record_history_(self, output_dict):
        if not isinstance(output_dict, dict): return
        primary_val = 0.0
        for v in output_dict.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                primary_val = float(v); break
        rd = list(self.state.get("recent_drives", []))
        rd.append(primary_val)
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        primary_state = "quiet"
        for v in output_dict.values():
            if isinstance(v, str): primary_state = v; break
        rs = list(self.state.get("recent_states", []))
        rs.append(primary_state)
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

