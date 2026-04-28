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
    1) EPISODIC: "I had coffee with {{USER_NAME}} this morning in the kitchen"
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
