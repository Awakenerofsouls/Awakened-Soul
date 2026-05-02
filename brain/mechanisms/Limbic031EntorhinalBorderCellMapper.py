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

CITATIONS
---------
  - [Hafting 2005, Nature 436:801, grid cells]
  - [Buzsaki 2013, Nat Neurosci 16:130, entorhinal-hippocampal]
  - [Witter 2017, Front Syst Neurosci 11:46, EC organization]

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
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
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

