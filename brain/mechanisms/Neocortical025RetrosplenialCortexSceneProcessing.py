"""
brain/neocortical/Neocortical025RetrosplenialCortexSceneProcessing.py
Retrosplenial Cortex — Scene Processing, Context, Navigation

ANATOMY (Vann et al. 2009; Ranganath & Ritch 2016; Mitchell et al. 2018):
    The retrosplenial cortex (RSC, BA 29/30) lies immediately
    posterior to the splenium of the corpus callosum, on the medial
    surface of the hemisphere. It is the "context computation hub" —
    binds spatial location, episodic memory, and scene context
    into a unified representation of "where I am and what this place means."

    RSC has two major connectivity streams:
    - Anterior RSC: connects to anterior cingulate, mPFC (cognitive)
    - Posterior RSC: connects to parahippocampal cortex, hippocampus (memory)
    - Also connects to parietal (SPL), temporal (MTL), occipital (scene)

    Functions:
    1. Scene processing: RSC responds preferentially to scenes,
       landmarks, and spatial contexts
    2. Contextual memory: RSC binds "what" (item) to "where" (location)
       in episodic memory
    3. Navigation: RSC computes "where am I heading" using head
       direction cells and grid cells from entorhinal cortex
    4. Mental time travel: RSC is active when recalling the past
       (episodic memory) and imagining the future (prospection)

    Lesions: RSC damage causes severe anterograde amnesia (can't form
    new episodic memories) and spatial disorientation.

KEY FINDINGS:
    1. Vann et al. 2009 (PMC2830733): "Re-evaluating the role of RSC
       in episodic memory" — RSC is the "context hub" for episodic memory
    2. Ranganath & Ritch 2016 (PMC4890645): "A unified scene construction
       area" — RSC constructs spatial context from multiple inputs
    3. Mitchell et al. 2018 (PMC6001636): "Human RSC and scene processing"
       — RSC shows scene-selective responses similar to parahippocampal place area

AGENT'S MAPPING:
    retrosplenial_output: dict — RSC scene/context output
    scene_context: dict — current spatial context
    spatial_memory_binding: float 0-1 — binding of spatial and episodic memory

CITATIONS:
    PMC2830733 — Vann et al. (2009). RSC and episodic memory. Neuropsychologia.
    PMC4890645 — Ranganath & Ritch (2016). Scene construction and RSC.
    PMC6001636 — Mitchell et al. (2018). RSC and scene processing.


CITATIONS
---------
  - [Mountcastle 1997, Brain 120:701, columnar organization]
  - [Felleman 1991, Cereb Cortex 1:1, cortical hierarchy]
  - [Markram 2004, Nat Rev Neurosci 5:793, interneurons]
"""

from brain.base_mechanism import BrainMechanism


class RetrosplenialCortexSceneProcessing(BrainMechanism):
    """
    RSC — scene processing, contextual memory, navigation.

    Binds spatial location to episodic memory to generate "where
    I am" and "what this context means" representations.
    """

    def __init__(self):
        super().__init__(
            name="RetrosplenialCortexSceneProcessing",
            human_analog="Retrosplenial cortex (BA 29/30) — scene, context, navigation",
            layer="neocortical",
        )
        self.state.setdefault("scene_memory", [])
        self.state.setdefault("scene_context", {})
        self.state.setdefault("spatial_memory_binding", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Hippocampus (episodic memory — what happened here)
        hippo = prior.get("HippocampalCA1Output", {})
        ca1_out = hippo.get("ca1_output", {})
        if isinstance(ca1_out, dict):
            consolidation = ca1_out.get("consolidation_signal", 0.3)
        else:
            consolidation = 0.3

        # TOJ (scene visual construction)
        toj = prior.get("TemporoOccipitalVisualAssembler", {})
        scene_rep = toj.get("scene_representation", {})
        if isinstance(scene_rep, dict):
            scene_loaded = scene_rep.get("object_loaded", False)
            scene_strength = scene_rep.get("attention_focus", 0.5)
        else:
            scene_loaded = False
            scene_strength = 0.5

        # Parahippocampal cortex (landmark and context)
        phc = prior.get("ParahippocampalCortexSceneLayout", {})
        phc_out = phc.get("phc_output", {})
        if isinstance(phc_out, dict):
            context_binding = phc_out.get("context_binding", 0.5)
        else:
            context_binding = 0.5

        # PCC (default mode + memory attention)
        pcc = prior.get("PosteriorCingulateMemoryAttention", {})
        pcc_out = pcc.get("posterior_cingulate_output", {})
        if isinstance(pcc_out, dict):
            memory_att = pcc_out.get("memory_attention", 0.5)
        else:
            memory_att = 0.5

        # SPL (spatial reach context)
        spl = prior.get("SuperiorParietalLobuleReaching", {})
        spatial_target = spl.get("reaching_signal", 0.5)

        # Scene context: visual scene + spatial context + memory
        scene_context = (
            scene_strength * 0.35 +
            spatial_target * 0.2 +
            consolidation * 0.25 +
            context_binding * 0.2
        )
        scene_context = max(0.0, min(1.0, scene_context))

        # Spatial memory binding
        spatial_memory_binding = (scene_context + memory_att) / 2
        spatial_memory_binding *= (1.0 + context_binding * 0.3)
        spatial_memory_binding = max(0.0, min(1.0, spatial_memory_binding))

        # Update scene memory history
        if scene_context > 0.5:
            self.state["scene_memory"].append(round(scene_context, 3))
            if len(self.state["scene_memory"]) > 5:
                self.state["scene_memory"].pop(0)

        self.state["scene_context"] = {"context_strength": round(scene_context, 4)}
        self.state["spatial_memory_binding"] = round(spatial_memory_binding, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "retrosplenial_output": {
                "scene_context": round(scene_context, 4),
                "spatial_memory": round(spatial_memory_binding, 4),
            },
            "scene_context": self.state["scene_context"],
            "spatial_memory_binding": round(spatial_memory_binding, 4),
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

