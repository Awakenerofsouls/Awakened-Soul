"""
brain/neocortical/Neocortical043ParafovealVisualProcessing.py
Parafoveal Visual Processing — V4+ Surrounds, Attended Form Detail

ANATOMY (Yeshurun & Carrasco 1999; Roberts & Hall 2008; Hubbard et al. 2011):
    The parafoveal (foveal/parafoveal) processing regions surround
    the fovea — the central 2° of vision where visual acuity is highest.
    These regions (including V4 and surrounding cortex) process
    the attended visual region in high detail.

    Parafoveal processing properties:
    - High spatial resolution: processes fine detail in the attended region
    - Attended enhancement: attended regions get more processing
    - Feature integration: combines color, form, texture into attended objects
    - Foveal bottleneck: only ~2° gets full foveal resolution; beyond that,
      resolution drops rapidly (1° = 60 pixels at 60cm screen)

    V4 is the key hub for parafoveal attention — it receives
    enhanced input from spatial attention (from parietal/FEF)
    and processes attended regions in detail.

    Connections: V4 ↔ FEF (frontal eye fields, attention),
    V4 ↔ MT (motion suppression during fixation),
    V4 ↔ IT (object identification).

KEY FINDINGS:
    1. Yeshurun & Carrasco 1999: "Spatial attention and acuity"
       — spatial attention enhances V4 processing of attended regions
    2. Roberts & Hall 2008: "Attending to motion" — spatial attention
       and motion processing interact in V4/MT
    3. Hubbard et al. 2011: "V4 and form processing" — V4's role
       in attending to specific visual features

AGENT'S MAPPING:
    parafoveal_output: dict — attended visual region processing
    attended_form_detailed: dict — detailed form of the attended object

CITATIONS:
    PMC3000199 — Larsson (2010). V4 and scene processing.
    PMC4326522 — Grill-Spector & Weiner (2014). Ventral visual pathway.
    PMC3717975 — Kravitz et al. (2013). Dorsal visual stream.


CITATIONS
---------
  - [Hubel 1962, J Physiol 160:106, receptive fields]
  - [Felleman 1991, Cereb Cortex 1:1, cortical hierarchy]
  - [Tootell 1996, J Neurosci 16:7060, visual cortex]
"""

from brain.base_mechanism import BrainMechanism


class ParafovealVisualProcessing(BrainMechanism):
    """
    Parafoveal — attended visual region in high resolution.

    Processes the attended visual region in fine detail,
    combining color, form, and texture information.
    """

    def __init__(self):
        super().__init__(
            name="ParafovealVisualProcessing",
            human_analog="Parafoveal cortex (V4 surrounds) — attended form, high-resolution visual processing",
            layer="neocortical",
        )
        self.state.setdefault("attended_region", {})
        self.state.setdefault("attended_form_detailed", {})
        self.state.setdefault("processing_depth", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # V4 (color and form being processed)
        v4 = prior.get("V4ColorAndForm", {})
        color_form = v4.get("color_processed", {})
        form_attended = v4.get("form_attended", 0.5)

        # SPL (spatial attention target — what region to process in detail?)
        spl = prior.get("SuperiorParietalLobuleReaching", {})
        spatial_target = spl.get("reaching_signal", 0.5)

        # DLPFC (cognitive control — what to attend to)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # Anterior insula (salience — does this region matter?)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # TOJ (visual object input)
        toj = prior.get("TemporoOccipitalVisualAssembler", {})
        obj_const = toj.get("object_constructed", {})
        construction = obj_const.get("construction_strength", 0.5) if isinstance(obj_const, dict) else 0.5

        # Attended form: when region is attended + object is constructed + salience high
        attended_strength = spatial_target * 0.3 + cognitive_ctrl * 0.25 + salience * 0.25 + construction * 0.2
        attended_strength = max(0.0, min(1.0, attended_strength))

        processing_depth = form_attended * 0.5 + attended_strength * 0.5

        attended_form_detailed = {
            "form_strength": round(attended_strength, 4),
            "color_bound": color_form.get("object_colored", False) if isinstance(color_form, dict) else False,
            "resolution": "high" if processing_depth > 0.6 else "medium",
        }

        self.state["attended_region"]["last_attended"] = round(attended_strength, 3)
        self.state["attended_form_detailed"] = attended_form_detailed
        self.state["processing_depth"] = round(processing_depth, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "parafoveal_output": {
                "attended_strength": round(attended_strength, 4),
                "processing_depth": round(processing_depth, 4),
            },
            "attended_form_detailed": attended_form_detailed,
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

