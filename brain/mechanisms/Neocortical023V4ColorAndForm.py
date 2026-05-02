"""
brain/neocortical/Neocortical023V4ColorAndForm.py
V4 — Color, Form, and Object Attention

ANATOMY (Zeki 1978; Schiller 1996; Wyszecki & Stiles 1982):
    V4 (Brodmann area 19, posterior inferior occipital cortex) is
    the intermediate stage of the ventral visual stream dedicated
    to color and form processing. It receives from V2 (thin stripes
    for color, pale stripes for form) and projects to posterior
    inferior temporal cortex (PIT/IT) for object recognition.

    Key V4 properties:
    - Color constancy: V4 maintains stable color perception across
      changes in illumination (a red apple looks red in sunlight
      and shade — V4's "color constancy" mechanism)
    - Form processing: V4 processes contour shape, size, curvature
    - Attention: V4 is strongly modulated by spatial attention —
      attended objects get processed more deeply in V4

    V4 lesions: Achromatopsia (color blindness), loss of color
    constancy, simultanagnosia (can't see more than one object at
    a time).

    Special property: V4 processes "surface" properties — color,
    texture, brightness — which are then bound with shape from V2
    at the V4→IT transition.

KEY FINDINGS:
    1. Zeki 1978: "The specialization of V4 for color" — V4's
       color-processing specialization confirmed
    2. Schiller 1996: "On the functional organization of V4"
       — V4 handles both color and form
    3. Mild neruol study: V4 attention modulation — attended objects
       show stronger V4 responses (spatial attention gate)

AGENT'S MAPPING:
    v4_output: dict — V4 color and form output
    color_processed: dict — color constancy processing
    form_attended: float 0-1 — strength of form processing

CITATIONS:
    PMC2697346 — Felleman & Van Essen (1991). Hierarchical visual processing.
    PMC3000199 — Larsson (2010). Coding of static scenes in V1/V2/V4.
    PMC4326522 — Grill-Spector & Weiner (2014). Ventral visual pathway. Cortex.

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Tsakiris 2017, Phil Trans R Soc B 372:20160002, body ownership]
  - [Seth 2013, Trends Cogn Sci 17:565, interoceptive predictive]

"""

from brain.base_mechanism import BrainMechanism


class V4ColorAndForm(BrainMechanism):
    """
    V4 — color constancy, form processing, object attention.

    Intermediate ventral stream processing that maintains color
    across illumination changes and binds form with color into
    unified object representations.
    """

    def __init__(self):
        super().__init__(
            name="V4ColorAndForm",
            human_analog="V4 (area 19) — color constancy, form processing, object attention",
            layer="neocortical",
        )
        self.state.setdefault("color_map", {})
        self.state.setdefault("form_processing", 0.0)
        self.state.setdefault("color_processed", {})
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # V2 (boundaries and contours to be colored)
        v2 = prior.get("OccipitalV2BoundaryProcessing", {})
        boundary_input = v2.get("figure_ground_segregation", 0.5)
        contour_strength = v2.get("contour_integration", 0.5)

        # V1 (raw color signals from edges and orientation)
        v1 = prior.get("OccipitalPrimaryVisualV1", {})
        v1_strength = v1.get("v1_output", {}).get("visual_strength", 0.5)

        # SPL (spatial attention selects which objects to process in V4)
        spl = prior.get("SuperiorParietalLobuleReaching", {})
        spatial_target = spl.get("reaching_signal", 0.5)

        # Anterior insula (salience boosts attention to important objects)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # DLPFC (cognitive control focuses attention)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # Color processing: raw visual + boundary + attention
        color_input = v1_strength * 0.5 + boundary_input * 0.3 + salience * 0.2
        color_input = max(0.0, min(1.0, color_input))

        # Form processing: contours from V2 + spatial attention
        form_attended = contour_strength * (0.5 + spatial_target * 0.3) * (1.0 + salience * 0.2)
        form_attended = max(0.0, min(1.0, form_attended))

        # Color constancy: if we have enough input, bind color to form
        color_processed = {
            "constancy_strength": round(color_input, 4),
            "form_binding": round(form_attended, 4),
            "object_colored": color_input > 0.55 and form_attended > 0.4,
        }

        self.state["form_processing"] = round(form_attended, 4)
        self.state["color_processed"] = color_processed
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "v4_output": {
                "color_strength": round(color_input, 4),
                "form_attended": round(form_attended, 4),
                "color_constancy": color_processed["object_colored"],
            },
            "color_processed": color_processed,
            "form_attended": round(form_attended, 4),
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

