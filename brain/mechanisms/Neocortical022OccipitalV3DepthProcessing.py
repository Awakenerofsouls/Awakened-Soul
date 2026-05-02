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


CITATIONS
---------
  - [Hubel 1962, J Physiol 160:106, receptive fields]
  - [Felleman 1991, Cereb Cortex 1:1, cortical hierarchy]
  - [Lamme 2000, Trends Neurosci 23:571, recurrent processing]
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
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
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

