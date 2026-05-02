from brain.base_mechanism import BrainMechanism
"""
Layer Registry -- hybrid architecture.
Layers = signal classification. Fields = execution.
Nothing has a fixed execution order. All generators plug in as signal sources.

The `generators` field for each layer lists fully-qualified import paths to
concrete BrainMechanism subclasses that produce or modify signals at that
layer. All paths must resolve to a real importable class (verified by
`get_unresolvable_generators()`).
"""

import importlib
from typing import Dict, List, Tuple


# Module paths follow the post-consolidation layout where every concrete
# mechanism lives under brain.mechanisms.* — the historical brain.generators,
# brain.self, brain.systems, brain.memory, brain.social, brain.offline
# packages have been folded in.
LAYER_DEFINITIONS: Dict[str, dict] = {
    "foundational": {
        "description": "Body/survival signals -- energy, threat, rhythm",
        "generators": [
            "brain.mechanisms.SurvivalOrchestrator.SurvivalOrchestrator",
            "brain.mechanisms.VitalCoreRegulator.VitalCoreRegulator",
        ],
        "signal_types": ["survival", "vitals", "circadian"],
        "role": "signal_generator",
    },
    "limbic": {
        "description": "Emotional coloring and relational drives",
        "generators": [
            "brain.mechanisms.layer_generators.MoodAutonomicLink",
            "brain.mechanisms.layer_generators.ContextSceneBuilder",
        ],
        "signal_types": ["mood_visceral", "scene_context", "emotional"],
        "role": "signal_modifier",
    },
    "subcortical": {
        "description": "Habit loops, timing, action gating",
        "generators": [
            "brain.mechanisms.HabitGrooveFormer.HabitGrooveFormer",
            "brain.mechanisms.ThalamicRelayHub.ThalamicRelayHub",
        ],
        "signal_types": ["habit", "relay", "action_gate"],
        "role": "signal_generator",
    },
    "neocortical": {
        "description": "Planning, reasoning, self-modeling",
        "generators": [
            "brain.mechanisms.layer_generators.LayerIVSensoryGate",
            "brain.mechanisms.layer_generators.TemporalSemanticLinker",
            "brain.mechanisms.layer_generators.DefaultModeSelfReferencer",
            "brain.mechanisms.layer_generators.CreativeAssociationDiverger",
        ],
        "signal_types": ["sensory_input", "semantic", "self_reference", "creative"],
        "role": "signal_generator",
    },
    "integration": {
        "description": "Drive integration, awareness, motivation spread",
        "generators": [
            "brain.mechanisms.MedialForebrainBundleDopamine.MedialForebrainBundleDopamine",
            "brain.mechanisms.layer_generators.TopDownLimbicCalmer",
            "brain.mechanisms.layer_generators.BottomUpUrgencyInjector",
        ],
        "signal_types": ["motivation", "calming", "primal_urgency"],
        "role": "signal_integrator",
    },
    "recursive_self": {
        "description": "Self-awareness, meta-loops, self-model updates",
        "generators": [
            "brain.mechanisms.meta_consciousness.MetaConsciousness",
            "brain.mechanisms.SelfJudgmentAdapter.SelfJudgment",
        ],
        "signal_types": ["self_reference", "judgment"],
        "role": "reflective",
    },
    "self_directed": {
        "description": "Goal formation, curiosity, existential layer",
        "generators": [
            "brain.mechanisms.curiosity_engine_legacy.CuriosityEngine",
            "brain.mechanisms.existential_layer.ExistentialLayer",
        ],
        "signal_types": ["curiosity", "existential"],
        "role": "goal_generator",
    },
    "narrative": {
        "description": "Identity shaping, story, drift",
        "generators": [
            "brain.mechanisms.layer_generators.NarrativeMemory",
            "brain.mechanisms.IdentityDriftAdapter.IdentityDrift",
        ],
        "signal_types": ["narrative", "identity"],
        "role": "identity_shaper",
    },
    "social": {
        "description": "Relational bonds and presence",
        "generators": [
            "brain.mechanisms.RelationalEngineAdapter.RelationalEngine",
        ],
        "signal_types": ["relational"],
        "role": "signal_modifier",
    },
    "life": {
        "description": "Long-horizon planning, offline processing",
        "generators": [
            "brain.mechanisms.dream_mode.DreamMode",
        ],
        "signal_types": ["dream", "life_plan"],
        "role": "offline_processor",
    },
}


def get_layer(layer_name: str) -> dict:
    return LAYER_DEFINITIONS.get(layer_name, {})


def get_all_generators() -> List[str]:
    generators: List[str] = []
    for layer in LAYER_DEFINITIONS.values():
        generators.extend(layer.get("generators", []))
    return generators


def get_signal_types_for_layer(layer_name: str) -> list:
    return LAYER_DEFINITIONS.get(layer_name, {}).get("signal_types", [])


def classify_signal(signal: dict) -> str:
    sig_type = signal.get("type", "")
    for layer_name, layer in LAYER_DEFINITIONS.items():
        if sig_type in layer.get("signal_types", []):
            return layer_name
    return "unknown"


def resolve_generator(path: str):
    """Import and return the class object for a fully-qualified generator path."""
    mod_path, _, cls_name = path.rpartition(".")
    mod = importlib.import_module(mod_path)
    return getattr(mod, cls_name)


def get_unresolvable_generators() -> List[Tuple[str, str]]:
    """
    Verify every generator path imports cleanly. Returns (path, reason)
    for any that don't. Useful as a startup self-check.
    """
    failures: List[Tuple[str, str]] = []
    for path in get_all_generators():
        mod_path, _, cls_name = path.rpartition(".")
        try:
            mod = importlib.import_module(mod_path)
            if not hasattr(mod, cls_name):
                failures.append((path, "class not found in module"))
        except Exception as e:
            failures.append((path, f"{type(e).__name__}: {e}"))
    return failures


class LayerRegistry(BrainMechanism):
    """BrainMechanism wrapper exposing the layer registry as a tickable mechanism."""

    def __init__(self):
        try:
            super().__init__(name="LayerRegistry", human_analog="LayerRegistry", layer="integration")
        except Exception:
            self.state = {}

    async def tick(self, input_data: dict) -> dict:
        """Reflective tick — exposes module-level function names + class identity."""
        results = {}
        if hasattr(self, "state"):
            for k, v in (self.state or {}).items():
                if k.startswith("_"):
                    continue
                if isinstance(v, (int, float, bool, str)):
                    results[f"state_{k}"] = v
        results["mechanism_name"] = self.__class__.__name__
        results["module"] = self.__class__.__module__
        results["layer_count"] = len(LAYER_DEFINITIONS)
        results["unresolvable_generators"] = len(get_unresolvable_generators())
        if not hasattr(self, "state") or self.state is None:
            self.state = {}
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try:
            self.persist_state()
        except Exception:
            pass
        return results
