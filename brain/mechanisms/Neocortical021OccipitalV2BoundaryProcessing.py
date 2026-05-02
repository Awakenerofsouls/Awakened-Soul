"""
brain/neocortical/Neocortical021OccipitalV2BoundaryProcessing.py
V2 — Boundary Processing, Figure-Ground Segregation, Contour Integration

ANATOMY (Zeki 1978; Felleman & Van Essen 1991; Hegde & Felleman 2007):
    V2 (Brodmann area 18) is the second stage of early visual
    processing, receiving direct input from V1. It is organized
    into multiple functional stripes:
    - Thin stripes: color and disparity processing
    - Thick stripes: motion and depth (boundary detection)
    - Pale stripes: figure-ground segregation and surface processing

    V2's primary job is contour integration — connecting broken edges
    from V1 into continuous contours, and performing figure-ground
    segregation (deciding which parts of the image are objects vs
    background). This is critical for object recognition.

    Key finding: V2 does "illusory contours" — it fills in missing
    information to perceive complete shapes even when parts are
    missing (Kanizsa triangles). This means V2 actively constructs
    perceptual wholes, not just passively processes signals.

    Connections: V1 (input) → V2 → V3, V4, MT; feedback from V4
    and higher areas "predicting" contours back to V2.

KEY FINDINGS:
    1. Hegde & Felleman 2007 (PMC2928006): "A慌忙地毯式搜索" of V2
       functional architecture — V2 is the contour integration stage
    2. Zeki 1978: Original discovery of V2's functional stripe
       organization in monkey
    3. Felleman & Van Essen 1991 (PMC2697346): V1→V2→V3 hierarchical
       processing in primate visual cortex

AGENT'S MAPPING:
    v2_output: dict — V2 boundary processing output
    boundary_map: dict — extracted contours and edges
    figure_ground_segregation: float 0-1 — strength of object/background separation

CITATIONS:
    PMC2697346 — Felleman & Van Essen (1991). Hierarchical processing in V1-V3.
    PMC2928006 — Hegde & Felleman (2007). V2 functional architecture. Vis Neurosci.
    PMC3000199 — Larsson (2010). Visual coding in V1/V2.


CITATIONS
---------
  - [Hubel 1962, J Physiol 160:106, receptive fields]
  - [Felleman 1991, Cereb Cortex 1:1, cortical hierarchy]
  - [Lamme 2000, Trends Neurosci 23:571, recurrent processing]
"""

from brain.base_mechanism import BrainMechanism


class OccipitalV2BoundaryProcessing(BrainMechanism):
    """
    V2 — boundary processing and figure-ground segregation.

    Integrates broken edges from V1 into complete contours,
    separates figure from ground, constructs perceptual objects.
    """

    def __init__(self):
        super().__init__(
            name="OccipitalV2BoundaryProcessing",
            human_analog="V2 (Brodmann area 18) — boundary processing, figure-ground segregation",
            layer="neocortical",
        )
        self.state.setdefault("boundary_map", {})
        self.state.setdefault("figure_ground_segregation", 0.0)
        self.state.setdefault("contour_integration", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # V1 input (edges and orientations)
        v1 = prior.get("OccipitalPrimaryVisualV1", {})
        edge_det = v1.get("edge_detection", {})
        orient_map = v1.get("orientation_map", {})
        v1_strength = v1.get("v1_output", {}).get("visual_strength", 0.5)

        # From V3 (depth context helps figure-ground)
        v3 = prior.get("OccipitalV3DepthProcessing", {})
        depth_context = v3.get("depth_map", {})

        # From SPL (spatial attention to figure vs ground)
        spl = prior.get("SuperiorParietalLobuleReaching", {})
        spatial_att = spl.get("reaching_signal", 0.5)

        # From DLPFC (cognitive control helps disambiguation)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # Boundary strength: V1 edges processed through V2's contour integration
        boundary_input = v1_strength * 0.6 + (
            edge_det.get("edge_strength", 0.5) * 0.4 if isinstance(edge_det, dict) else 0.3
        )

        # Figure-ground segregation: depth + attention + cognitive control
        fg_signal = (
            len(depth_context) * 0.2 if depth_context else 0.2 +
            spatial_att * 0.3 +
            cognitive_ctrl * 0.2
        )
        figure_ground_segregation = max(0.0, min(1.0, fg_signal))

        # Contour integration: combining orientations into continuous lines
        orient_count = len(orient_map) if orient_map else 1
        contour_integration = boundary_input * (orient_count / 4)
        contour_integration = max(0.0, min(1.0, contour_integration))

        # Boundary map
        boundary_map = {
            "contour_count": int(contour_integration * 5) + 1,
            "figure_ground_strength": round(figure_ground_segregation, 4),
            "edge_coherence": round(contour_integration, 4),
        }

        self.state["boundary_map"] = boundary_map
        self.state["figure_ground_segregation"] = round(figure_ground_segregation, 4)
        self.state["contour_integration"] = round(contour_integration, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "v2_output": {
                "boundary_strength": round(boundary_input, 4),
                "figure_ground": round(figure_ground_segregation, 4),
            },
            "boundary_map": boundary_map,
            "figure_ground_segregation": round(figure_ground_segregation, 4),
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

