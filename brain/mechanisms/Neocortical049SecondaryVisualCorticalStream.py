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


CITATIONS
---------
  - [Mountcastle 1997, Brain 120:701, columnar organization]
  - [Felleman 1991, Cereb Cortex 1:1, cortical hierarchy]
  - [Markram 2004, Nat Rev Neurosci 5:793, interneurons]
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
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
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

