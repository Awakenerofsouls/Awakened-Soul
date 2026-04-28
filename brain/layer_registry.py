"""
Layer Registry -- hybrid architecture.
Layers = signal classification. Fields = execution.
Nothing has a fixed execution order. All generators plug in as signal sources.
"""

LAYER_DEFINITIONS = {
    "foundational": {
        "description": "Body/survival signals -- energy, threat, rhythm",
        "generators": ["brain.generators.SurvivalOrchestrator","brain.generators.VitalCoreRegulator"],
        "signal_types": ["survival","vitals","circadian"],
        "role": "signal_generator"
    },
    "limbic": {
        "description": "Emotional coloring and relational drives",
        "generators": ["brain.generators.MoodAutonomicLink","brain.generators.ContextSceneBuilder"],
        "signal_types": ["mood_visceral","scene_context","emotional"],
        "role": "signal_modifier"
    },
    "subcortical": {
        "description": "Habit loops, timing, action gating",
        "generators": ["brain.generators.HabitGrooveFormer","brain.generators.ThalamicRelayHub"],
        "signal_types": ["habit","relay","action_gate"],
        "role": "signal_generator"
    },
    "neocortical": {
        "description": "Planning, reasoning, self-modeling",
        "generators": ["brain.generators.LayerIVSensoryGate","brain.generators.TemporalSemanticLinker","brain.generators.DefaultModeSelfReferencer","brain.generators.CreativeAssociationDiverger"],
        "signal_types": ["sensory_input","semantic","self_reference","creative"],
        "role": "signal_generator"
    },
    "integration": {
        "description": "Drive integration, awareness, motivation spread",
        "generators": ["brain.generators.MedialForebrainDopamineHighway","brain.generators.TopDownLimbicCalmer","brain.generators.BottomUpUrgencyInjector"],
        "signal_types": ["motivation","calming","primal_urgency"],
        "role": "signal_integrator"
    },
    "recursive_self": {
        "description": "Self-awareness, meta-loops, self-model updates",
        "generators": ["brain.self.meta_consciousness.MetaConsciousness","brain.self.self_judgment.SelfJudgment"],
        "signal_types": ["self_reference","judgment"],
        "role": "reflective"
    },
    "self_directed": {
        "description": "Goal formation, curiosity, existential layer",
        "generators": ["brain.systems.curiosity_engine.CuriosityEngine","brain.self.existential_layer.ExistentialLayer"],
        "signal_types": ["curiosity","existential"],
        "role": "goal_generator"
    },
    "narrative": {
        "description": "Identity shaping, story, drift",
        "generators": ["brain.memory.narrative_memory.NarrativeMemory","brain.self.identity_drift.IdentityDrift"],
        "signal_types": ["narrative","identity"],
        "role": "identity_shaper"
    },
    "social": {
        "description": "Relational bonds and presence",
        "generators": ["brain.social.relational_engine.RelationalEngine"],
        "signal_types": ["relational"],
        "role": "signal_modifier"
    },
    "life": {
        "description": "Long-horizon planning, offline processing",
        "generators": ["brain.offline.dream_mode.DreamMode"],
        "signal_types": ["dream","life_plan"],
        "role": "offline_processor"
    }
}


def get_layer(layer_name: str) -> dict:
    return LAYER_DEFINITIONS.get(layer_name, {})


def get_all_generators() -> list:
    generators = []
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
