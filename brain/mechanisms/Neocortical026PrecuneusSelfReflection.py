"""
brain/neocortical/Neocortical026PrecuneusSelfReflection.py
Precuneus — Self-Reflection, Mental Imagery, Egocentric Spatial

ANATOMY (Cavanna & Trimble 2006; Freton et al. 2014; Brewer et al. 2013):
    The precuneus (PC, medial parietal cortex, BA 7m) is one of the
    most highly connected regions in the brain. It sits at the vertex
    of the medial surface, between the postcentral gyrus (sensory) and
    the marginal ramus of the cingulate. It is a core node of the
    DMN (Default Mode Network) and is active during:
    - Self-referential processing (thinking about yourself)
    - Mental imagery (visualizing scenes, events, actions)
    - Egocentric spatial processing (where am I in space relative to objects)
    - Episodic memory retrieval (autobiographical memory)
    - Theory of mind (thinking about others' mental states)

    The precuneus has a somatotopic organization:
    - Anterior PC: motor imagery (planning movements)
    - Central PC: spatial imagery (where things are)
    - Posterior PC: visual mental imagery (what things look like)

    Key finding: The precuneus shows "default mode" activity — it's
    active when you're not doing anything externally focused, like
    during mind-wandering, daydreaming, or thinking about the future.

    Connectivity: PCC (cingulate), mPFC, angular gyrus (semantic),
    hippocampus (memory), SPL (spatial), DLPFC (executive).

KEY FINDINGS:
    1. Cavanna & Trimble 2006 (PMC1852382): "The precuneus: a review"
       — comprehensive review of precuneus functions
    2. Freton et al. 2014 (PMC4108564): "The DMN and self-projection"
       — precuneus generates self-models from memory and imagination
    3. Easton et al. 2009 (PMID 19058798): Precuneus and fronto-parietal
       connectivity in out-of-body experiences — fronto-parietal network
       for embodied vs disembodied self

AGENT'S MAPPING:
    precuneus_output: dict — precuneus self/imagery output
    self_representation: dict — current self-model
    mental_imagery: float 0-1 — strength of internal imagery

CITATIONS:
    PMC1852382 — Cavanna & Trimble (2006). Precuneus review. Brain.
    PMC4108564 — Freton et al. (2014). DMN and self-projection.
    PMID 19058798 — Easton et al. (2009). Precuneus and OBE. Cortex.

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Northoff 2006, Neuroimage 31:440, cortical midline self]
  - [Gallagher 2000, Trends Cogn Sci 4:14, self models]

"""

from brain.base_mechanism import BrainMechanism


class PrecuneusSelfReflection(BrainMechanism):
    """
    Precuneus — self-reflection, mental imagery, egocentric spatial.

    Generates internal representations of self and world through
    imagery, supported by default mode and memory networks.
    """

    def __init__(self):
        super().__init__(
            name="PrecuneusSelfReflection",
            human_analog="Precuneus (BA 7m) — self-reflection, mental imagery, egocentric spatial",
            layer="neocortical",
        )
        self.state.setdefault("self_model", {})
        self.state.setdefault("self_representation", {})
        self.state.setdefault("mental_imagery", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # PCC (default mode + memory retrieval)
        pcc = prior.get("PosteriorCingulateMemoryAttention", {})
        pcc_out = pcc.get("posterior_cingulate_output", {})
        if isinstance(pcc_out, dict):
            self_ref = pcc_out.get("self_referential", 0.5)
            dmn = pcc_out.get("default_mode", True)
        else:
            self_ref = 0.5
            dmn = True

        # Hippocampus (autobiographical memory for self-representation)
        hippo = prior.get("HippocampalCA1Output", {})
        ca1_out = hippo.get("ca1_output", {})
        if isinstance(ca1_out, dict):
            consolidation = ca1_out.get("consolidation_signal", 0.3)
        else:
            consolidation = 0.3

        # Angular gyrus (semantic self-knowledge)
        angular = prior.get("AngularGyrusMultimodal", {})
        sem_access = angular.get("semantic_access", {})
        if isinstance(sem_access, dict):
            sem_depth = sem_access.get("semantic_depth", 0.5)
        else:
            sem_depth = 0.5

        # SPL (egocentric spatial — where am I relative to the world)
        spl = prior.get("SuperiorParietalLobuleReaching", {})
        spatial_target = spl.get("reaching_signal", 0.5)

        # mPFC (self-narrative and social self)
        mpfc = prior.get("MedialPrefrontalSelfReflection", {})
        mpfc_out = mpfc.get("medial_pfc_output", {})
        if isinstance(mpfc_out, dict):
            self_narr = mpfc_out.get("self_referential_signal", 0.5)
        else:
            self_narr = 0.5

        # Mental imagery: strongest when DMN is active and memory is rich
        mental_imagery = (
            self_ref * 0.25 +
            consolidation * 0.3 +
            sem_depth * 0.2 +
            spatial_target * 0.25
        )
        if dmn:
            mental_imagery *= 1.3
        mental_imagery = max(0.0, min(1.0, mental_imagery))

        # Self-representation: narrative + memory + spatial
        self_representation = {
            "self_clarity": round(mental_imagery, 4),
            "narrative_strength": round(self_narr, 4),
            "spatial_self": round(spatial_target, 4),
            "memory_self": round(consolidation, 4),
        }

        self.state["self_model"] = self_representation
        self.state["self_representation"] = self_representation
        self.state["mental_imagery"] = round(mental_imagery, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "precuneus_output": {
                "self_representation": self_representation,
                "imagery_strength": round(mental_imagery, 4),
            },
            "self_representation": self_representation,
            "mental_imagery": round(mental_imagery, 4),
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

