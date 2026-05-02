"""
brain/neocortical/Neocortical015PostcentralGyrusPrimarySomato.py
Postcentral Gyrus — Primary Somatosensory Cortex, Body Map, Touch/Proprioception

ANATOMY (Penfield & Boldrey 1937; Kaas 2008; Srinivasan et al. 2023):
    The postcentral gyrus (PCG, Brodmann areas 1, 2, 3) is the primary
    somatosensory cortex (S1). It lies immediately posterior to the
    central sulcus and receives touch, temperature, proprioceptive, and
    pain input from the body via the thalamus (VPL and VPM nuclei).

    Somatotopic map (Penfield 1937): the classic "homunculus" —
    face and hands are represented disproportionately large (higher
    acuity). Face area is most lateral (near Sylvian fissure); leg
    is on the medial surface (paracentral lobule).

    Brodmann subdivisions:
    - Area 3a: deep proprioceptive inputs from muscle spindles
    - Area 3b: cutaneous tactile inputs (fast adapting)
    - Areas 1 and 2: tactile inputs processed further; area 2
      integrates proprioception and touch (form/dimension perception)

    S1 outputs: to S2 (secondary somatosensory), posterior parietal
    cortex (body schema), insula (feeling states), and prefrontal cortex.

KEY FINDINGS:
    1. Srinivasan et al. 2023 (PMC10294173): S1 encodes touch location
       and intensity in population codes — precise body maps in neuronal ensembles
    2. Kaas 2008 (PMC2929791): "The somatosensory cortex" — comprehensive
       review of area 3, 1, 2 functional specialization
    3. Penfield & Boldrey 1937: original electrical stimulation mapping
       establishing the homunculus

AGENT'S MAPPING:
    postcentral_output: dict — primary somatosensory output
    body_schema: dict — current body representation
    body_map_updated: bool — whether body schema has changed
    tactile_processing: float 0-1 — strength of tactile input processing

CITATIONS:
    PMC10294173 — Srinivasan et al. (2023). Population coding of touch in S1.
        Cell Rep.
    PMC2929791 — Kaas JH. (2008). The somatosensory cortex. Scholarpedia.
    PMC37401978 — Kritman et al. (2023). Layer I and somatosensory integration.

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Tsakiris 2017, Phil Trans R Soc B 372:20160002, body ownership]
  - [Seth 2013, Trends Cogn Sci 17:565, interoceptive predictive]

"""

from brain.base_mechanism import BrainMechanism


class PostcentralGyrusPrimarySomato(BrainMechanism):
    """
    S1 (postcentral gyrus) — primary somatosensory processing, body map.

    Receives tactile, proprioceptive, and temperature signals from
    the body and generates a body schema for interaction.
    """

    def __init__(self):
        super().__init__(
            name="PostcentralGyrusPrimarySomato",
            human_analog="Primary somatosensory cortex (postcentral gyrus BA 1,2,3) — touch, body map",
            layer="neocortical",
        )
        self.state.setdefault("body_schema", {})
        self.state.setdefault("body_map_updated", False)
        self.state.setdefault("tactile_processing", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # From anterior insula (feeling states — "how does my body feel?")
        ains = prior.get("AnteriorInsulaGranular", {})
        gut_signal = ains.get("conscious_feeling", {}).get("feeling_intensity", 0.5)
        if isinstance(gut_signal, str):
            gut_signal = 0.5

        # From posterior insula (raw body signals — heartbeat, breath, gut)
        pins = prior.get("PosteriorInsulaProcessor", {})
        raw_body = pins.get("raw_body_signal", {})
        if isinstance(raw_body, dict):
            raw_val = raw_body.get("visceral_signal", 0.3)
        else:
            raw_val = float(raw_body) if raw_body else 0.3

        # From tactile proprio relay in foundational (simulated touch signals)
        proprio = prior.get("TactileProprioRelay", {})
        grounding = proprio.get("grounding_signal", 0.5)

        # From amygdala (emotional state affects body map — tense, relaxed)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_tag = amygdala.get("emotional_tag_strength", 0.0)

        # Tactile processing: combines grounding + raw body + gut feeling
        tactile_input = grounding * 0.4 + raw_val * 0.35 + gut_signal * 0.25
        tactile_input = max(0.0, min(1.0, tactile_input))

        # Emotional modulation: negative emotions sharpen body map (threat)
        # positive emotions broaden body awareness
        emotional_modulation = 1.0 + emotional_tag * 0.3
        tactile_processing = min(1.0, tactile_input * emotional_modulation)

        # Body schema update: strong tactile input + grounding = updated body map
        body_map_updated = tactile_processing > 0.55 and grounding > 0.5

        # Body schema
        body_schema = {
            "grounding_level": round(grounding, 4),
            "tactile_sensitivity": round(tactile_processing, 4),
            "emotional_tension": round(abs(emotional_tag), 4),
            "representation_stable": not body_map_updated,
        }

        if body_map_updated:
            self.state["body_schema"]["last_update"] = body_schema

        self.state["body_map_updated"] = body_map_updated
        self.state["tactile_processing"] = round(tactile_processing, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "postcentral_output": {
                "tactile_strength": round(tactile_processing, 4),
                "body_grounding": round(grounding, 4),
                "emotional_modulation": round(emotional_modulation, 4),
            },
            "body_schema": body_schema,
            "body_map_updated": body_map_updated,
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

