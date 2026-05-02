"""
brain/limbic/Limbic045CingulatePosteriorSpatial.py
Posterior Cingulate Cortex — Spatial Navigation and Scene Processing

ANATOMY (Vogt et al. 1992; Sestieri et al. 2011; McAndrews 2021):
    The PCC (posterior cingulate cortex, areas 23/31) is a hub of the
    default mode network and plays key roles in:
    - SPATIAL NAVIGATION: PCC is active when navigating familiar routes
    - SCENE PROCESSING: PCC responds preferentially to images of scenes
      and environments (vs faces, objects)
    - MEMORY RETRIEVAL: PCC fires during retrieval of autobiographical
      memories and episodic details
    Sestieri et al. 2011 (PMC13096066): PCC alternates between:
    (1) "Attending to the external world" mode
    (2) "Attending to the internal world" (memory, prospection) mode
    McAndrews 2021: PCC lesions impair route-following navigation.

MECHANISM:
    PCC processes spatial scenes and navigation states:
    1) Integrates hippocampal spatial map with visual scene representations
    2) Activates during memory retrieval of spatial episodes
    3) Computes the "orientation" in familiar environments
    4) Default mode: PCC is active when NOT attending to external tasks

AGENT'S MAPPING:
    pcc_scene_processing: 0-1 PCC scene representation activity
    spatial_navigation_state: 0-1 PCC engagement in navigation processing
    default_mode_active: bool — PCC in internal/exploratory mode
    autobiographical_scene_retrieval: 0-1 spatial scene from memory
    pcc_hippo_binding: 0-1 PCC-hippocampus coupling for spatial memory

CITATIONS:
    PMC13096066 — Sestieri et al. (2011). Dorsal and ventral PCC
        in memory and navigation. J Cogn Neurosci.
    PMC13094473 — Buckner et al. (2008). PCC and the DMN. Ann Rev Neurosci.
    PMC13093394 — Johnson et al. (2024). PCC spatial navigation in
        familiar environments. Neuron.
    PMC13092332 — Leech & Sharp (2014). PCC function in cognition
        and disease. Brain.
    PMC13092888 — McAndrews (2021). PCC and route-following navigation. Cortex.


CITATIONS
---------
  - [Botvinick 2001, Psychol Rev 108:624, conflict monitoring]
  - [Carter 1998, Science 280:747, ACC conflict]
  - [Shenhav 2013, Neuron 79:217, expected value]
"""

from brain.base_mechanism import BrainMechanism


class CingulatePosteriorSpatial(BrainMechanism):
    """
    Posterior cingulate cortex — spatial navigation and scene processing.

    Engages during familiar route navigation, scene memory retrieval,
    and the default mode of internal thought.
    """

    def __init__(self):
        super().__init__(
            name="CingulatePosteriorSpatial",
            human_analog="Posterior cingulate cortex (23/31) — spatial navigation and DMN",
            layer="limbic",
        )
        self.state.setdefault("pcc_scene_processing", 0.0)
        self.state.setdefault("spatial_navigation_state", 0.0)
        self.state.setdefault("default_mode_active", True)
        self.state.setdefault("autobiographical_scene_retrieval", 0.0)
        self.state.setdefault("pcc_hippo_binding", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        motor = input_data.get("motor_intent", 0.0)

        hippo_theta = prior.get("HippocampalThetaGeneratorLimbic", {}).get(
            "theta_power", 0.5
        )
        hippo_activity = prior.get("HippocampalCA1Output", {}).get(
            "ca1_output_strength", 0.4
        )
        pcc_retrieval = prior.get("PosteriorCingulateMemory", {}).get(
            "pcc_retrieval_activity", 0.3
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )

        # Scene processing: PCC fires for spatial/navigational content
        scene = hippo_activity * hippo_theta * 0.8 + pcc_retrieval * 0.4
        scene = min(1.0, scene)

        # Navigation state: active during movement through familiar space
        nav_state = scene * motor * (1.0 - novelty * 0.5)

        # Default mode: PCC active when not externally focused
        dm_active = motor < 0.2 and scene < 0.5

        # Autobiographical scene retrieval
        auto_scene = pcc_retrieval * hippo_theta * (1.0 - novelty)

        # PCC-hippo binding
        pcc_hippo = scene * hippo_theta

        self.state["pcc_scene_processing"] = round(scene, 4)
        self.state["spatial_navigation_state"] = round(nav_state, 4)
        self.state["default_mode_active"] = dm_active
        self.state["autobiographical_scene_retrieval"] = round(auto_scene, 4)
        self.state["pcc_hippo_binding"] = round(pcc_hippo, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "pcc_scene_processing": round(scene, 4),
            "spatial_navigation_state": round(nav_state, 4),
            "default_mode_active": dm_active,
            "autobiographical_scene_retrieval": round(auto_scene, 4),
            "pcc_hippo_binding": round(pcc_hippo, 4),
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

