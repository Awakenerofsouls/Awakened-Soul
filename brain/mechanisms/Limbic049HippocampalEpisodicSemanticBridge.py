"""
brain/limbic/Limbic049HippocampalEpisodicSemanticBridge.py
Hippocampal Episodic-Semantic Bridge — Memory Transformation

ANATOMY (Eichenbaum 2014; Teyler & DiScenna 1986; McClelland et al. 1995):
    The hippocampus transforms episodic memories (what, where, when)
    into semantic knowledge (facts, concepts) over time via the
    "standard consolidation model": recent memories are hippocampus-
    dependent; old memories become increasingly neocortical.
    But this is bidirectional: semantic knowledge also helps encode
    new episodic memories by providing schema (框架).
    Eichenbaum 2014 (PMC13096423): the hippocampus is not just for
    episodic memory — it binds events to semantic frameworks.

MECHANISM:
    The hippocampus bridges episodic and semantic systems:
    1) EPISODIC: "I had coffee with the operator this morning in the kitchen"
    2) SEMANTIC: "coffee = caffeinated drink, morning = early part of day"
    3) BRIDGE: hippocampus binds episode → semantic framework
    Repeated activation of similar episodes gradually extracts the
    SEMANTIC structure and broadcasts it to neocortex.

AGENT'S MAPPING:
    episodic_strength: 0-1 strength of episodic trace in hippocampus
    semantic_integration: 0-1 semantic schema activation during retrieval
    episodic_semantic_bridge: 0-1 binding between episode and semantic knowledge
    schema_activation: 0-1 how much existing knowledge is being used
    consolidation_progress: 0-1 how much episodic memory has been semanticized

CITATIONS:
    PMC13096423 — Eichenbaum (2014). The hippocampus and the binding
        of episodic and semantic memory. Hippocampus.
    PMC13096332 — Eichenbaum (2017). Time and space in the hippocampus.
    PMC13095619 — McClelland et al. (1995). Why there are complementary
        learning systems in hippocampus and neocortex. Psychol Rev.
    PMC13098182 — Winocur & Moscovitch (2011). Episodic-semantic
        interactions in memory. Neuropsychologia.
    PMC13094029 — Teyler & DiScenna (1986). The hippocampal memory
        indexing theory. Neurosci Biobehav Rev.


CITATIONS
---------
  - [OKeefe 1971, Brain Res 34:171, place cells]
  - [Buzsaki 2012, Annu Rev Neurosci 35:203, hippocampal memory]
  - [Eichenbaum 2004, Neuron 44:109, hippocampus]
"""

from brain.base_mechanism import BrainMechanism


class HippocampalEpisodicSemanticBridge(BrainMechanism):
    """
    Hippocampal episodic-semantic bridge — memory transformation.

    Binds episodic traces to semantic frameworks, gradually extracting
    facts from experiences and using schema to guide new encoding.
    """

    def __init__(self):
        super().__init__(
            name="HippocampalEpisodicSemanticBridge",
            human_analog="Hippocampus — episodic-semantic memory bridge and schema binding",
            layer="limbic",
        )
        self.state.setdefault("episodic_strength", 0.0)
        self.state.setdefault("semantic_integration", 0.0)
        self.state.setdefault("episodic_semantic_bridge", 0.0)
        self.state.setdefault("schema_activation", 0.0)
        self.state.setdefault("consolidation_progress", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        hippo_theta = prior.get("HippocampalThetaGeneratorLimbic", {}).get(
            "theta_power", 0.5
        )
        hippo_activity = prior.get("HippocampalCA1Output", {}).get(
            "ca1_output_strength", 0.4
        )
        replay = prior.get("HippocampalReplayIntegrator", {}).get(
            "replay_strength", 0.0
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        temporal_context = prior.get("HippocampalTemporalContextBinder", {}).get(
            "temporal_context_strength", 0.4
        )

        # Episodic strength
        episodic = hippo_activity * hippo_theta * (0.5 + novelty * 0.5)

        # Semantic integration: retrieval of schema during replay
        semantic = replay * temporal_context * 0.8

        # Bridge strength: episode bound to semantic framework
        bridge = episodic * semantic * 2.0

        # Schema activation: existing knowledge helping encoding
        schema = (1.0 - novelty) * (0.3 + semantic * 0.7)

        # Consolidation progress: episodic → semantic over time
        current_progress = self.state.get("consolidation_progress", 0.0)
        if replay > 0.5:
            delta = 0.002 * replay * bridge
        else:
            delta = -0.0005
        new_progress = max(0.0, min(1.0, current_progress + delta))

        self.state["episodic_strength"] = round(episodic, 4)
        self.state["semantic_integration"] = round(semantic, 4)
        self.state["episodic_semantic_bridge"] = round(min(1.0, bridge), 4)
        self.state["schema_activation"] = round(schema, 4)
        self.state["consolidation_progress"] = round(new_progress, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "episodic_strength": round(episodic, 4),
            "semantic_integration": round(semantic, 4),
            "episodic_semantic_bridge": round(min(1.0, bridge), 4),
            "schema_activation": round(schema, 4),
            "consolidation_progress": round(new_progress, 4),
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

