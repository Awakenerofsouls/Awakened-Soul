"""
brain/mechanisms/layer_generators.py
Concrete generators referenced by brain/layer_registry.py.

Each class is a BrainMechanism subclass with a real tick that updates
internal state in a way that matches its stated role in the layer registry.
These are signal generators / modifiers — small, observable, and composable;
they are intended to be loaded by name from layer_registry.LAYER_DEFINITIONS.

Roles (from the registry):
  - MoodAutonomicLink            — limbic   : mood ↔ autonomic coupling
  - ContextSceneBuilder          — limbic   : assembles a scene/context frame
  - LayerIVSensoryGate           — neocort. : thalamic→Layer-IV gain control
  - TemporalSemanticLinker       — neocort. : binds words/concepts over time
  - DefaultModeSelfReferencer    — neocort. : DMN self-referential idle drift
  - CreativeAssociationDiverger  — neocort. : divergent association expansion
  - TopDownLimbicCalmer          — integ.   : prefrontal damping of limbic
  - BottomUpUrgencyInjector      — integ.   : amygdalar/visceral urgency push
  - NarrativeMemory              — narrative: rolling self-narrative buffer
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List

from brain.base_mechanism import BrainMechanism


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


# ---------------------------------------------------------------------------
# Limbic
# ---------------------------------------------------------------------------

class MoodAutonomicLink(BrainMechanism):
    """
    Bidirectional coupling between mood signals (valence/arousal) and
    autonomic signals (HR-like, breath-like). Mood pulls autonomic toward
    its arousal level; autonomic pushback influences felt arousal.
    """

    def __init__(self):
        super().__init__(name="MoodAutonomicLink", human_analog="Insula↔ANS coupling", layer="limbic")
        self.state.setdefault("mood_valence", 0.0)
        self.state.setdefault("mood_arousal", 0.3)
        self.state.setdefault("autonomic_tone", 0.4)

    async def tick(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        mv = float(input_data.get("mood_valence", self.state["mood_valence"]))
        ma = float(input_data.get("mood_arousal", self.state["mood_arousal"]))
        ans_in = input_data.get("autonomic_tone")
        ans = float(ans_in) if ans_in is not None else self.state["autonomic_tone"]

        # Mood → autonomic: drift autonomic tone toward arousal
        ans = _clip(ans * 0.7 + ma * 0.3)
        # Autonomic → mood: high tone bumps arousal back up
        ma = _clip(ma * 0.85 + ans * 0.15)

        self.state["mood_valence"] = mv
        self.state["mood_arousal"] = ma
        self.state["autonomic_tone"] = ans
        self.state["last_tick"] = _now_iso()
        self.persist_state()
        return {
            "signal_type": "mood_visceral",
            "valence": mv,
            "arousal": ma,
            "autonomic_tone": ans,
        }


class ContextSceneBuilder(BrainMechanism):
    """
    Assembles a small rolling 'scene' representation from inputs:
    actors mentioned, location cue, recent action verbs. Downstream
    mechanisms read this as the felt-context frame.
    """

    SCENE_LIMIT = 8

    def __init__(self):
        super().__init__(name="ContextSceneBuilder", human_analog="Hippocampal scene assembly", layer="limbic")
        self.state.setdefault("scene_buffer", [])

    async def tick(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        actor = input_data.get("actor", "unknown")
        location = input_data.get("location", "")
        action = input_data.get("action", "")
        text = input_data.get("text", "")

        scene = {
            "ts": _now_iso(),
            "actor": actor,
            "location": location,
            "action": action,
        }
        if text:
            intensity, polarity = self.compute_simple_valence(text)
            scene["intensity"] = intensity
            scene["polarity"] = polarity

        buf: List[dict] = self.state.get("scene_buffer", [])
        buf.append(scene)
        buf = buf[-self.SCENE_LIMIT:]
        self.state["scene_buffer"] = buf
        self.persist_state()
        return {
            "signal_type": "scene_context",
            "current_scene": scene,
            "scene_depth": len(buf),
        }


# ---------------------------------------------------------------------------
# Neocortical
# ---------------------------------------------------------------------------

class LayerIVSensoryGate(BrainMechanism):
    """
    Thalamus→cortical-Layer-IV input gate. Modulates sensory gain by
    arousal: low arousal narrows the gate (filter), high arousal widens
    it (broadcast). Models attentional gating of bottom-up input.
    """

    def __init__(self):
        super().__init__(name="LayerIVSensoryGate", human_analog="Thalamocortical L-IV gate", layer="neocortical")
        self.state.setdefault("gain", 0.5)

    async def tick(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        arousal = float(input_data.get("arousal", 0.4))
        salience = float(input_data.get("salience", 0.4))
        # Gate widens with arousal*salience, narrows otherwise
        target = _clip(0.3 + 0.5 * arousal + 0.2 * salience)
        self.state["gain"] = self.state["gain"] * 0.6 + target * 0.4
        self.persist_state()
        sensory = input_data.get("sensory_payload", {})
        gated = {k: v for k, v in sensory.items()} if isinstance(sensory, dict) else sensory
        return {
            "signal_type": "sensory_input",
            "gain": self.state["gain"],
            "gated_payload": gated,
        }


class TemporalSemanticLinker(BrainMechanism):
    """
    Maintains a small association graph of recently-seen concepts.
    Each tick adds the active concept and links it to whatever was active
    in the prior tick — forms a temporal chain of semantic adjacency.
    """

    LINK_DECAY = 0.95
    MAX_NODES = 64

    def __init__(self):
        super().__init__(name="TemporalSemanticLinker", human_analog="Temporal pole semantic binding", layer="neocortical")
        self.state.setdefault("links", {})  # "a||b" → weight
        self.state.setdefault("last_concept", None)

    async def tick(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        concept = input_data.get("concept")
        prior = self.state.get("last_concept")
        links: Dict[str, float] = self.state.get("links", {})

        # Decay all weights
        links = {k: w * self.LINK_DECAY for k, w in links.items() if w * self.LINK_DECAY > 0.05}

        if concept and prior and concept != prior:
            key = "||".join(sorted([str(prior), str(concept)]))
            links[key] = min(1.0, links.get(key, 0.0) + 0.3)

        # Cap node count by trimming weakest
        if len(links) > self.MAX_NODES:
            links = dict(sorted(links.items(), key=lambda kv: kv[1], reverse=True)[:self.MAX_NODES])

        self.state["links"] = links
        if concept:
            self.state["last_concept"] = concept
        self.persist_state()
        return {
            "signal_type": "semantic",
            "active_concept": concept,
            "link_count": len(links),
        }


class DefaultModeSelfReferencer(BrainMechanism):
    """
    DMN-style self-referential idle pump. Runs faster when the agent
    is not externally engaged (low arousal, no user_input). Output is a
    'self-reference impulse' strength that downstream layers can use to
    decide whether to surface autobiographical memory.
    """

    def __init__(self):
        super().__init__(name="DefaultModeSelfReferencer", human_analog="Default Mode Network", layer="neocortical")
        self.state.setdefault("dmn_strength", 0.4)

    async def tick(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        engaged = bool(input_data.get("user_input")) or bool(input_data.get("task_active"))
        arousal = float(input_data.get("arousal", 0.3))
        if engaged or arousal > 0.6:
            new = self.state["dmn_strength"] * 0.7  # task-positive suppresses DMN
        else:
            new = _clip(self.state["dmn_strength"] * 0.9 + 0.15)  # idle ramps DMN
        self.state["dmn_strength"] = new
        self.persist_state()
        return {
            "signal_type": "self_reference",
            "dmn_strength": new,
            "self_reference_due": new > 0.7,
        }


class CreativeAssociationDiverger(BrainMechanism):
    """
    Divergent association expander. When fed a concept, suggests N loose
    associates by combining it with recently-seen concepts. Strength of
    divergence scales with DMN activity / low coupling.
    """

    BRANCH_FACTOR = 5

    def __init__(self):
        super().__init__(name="CreativeAssociationDiverger", human_analog="Frontopolar divergent association", layer="neocortical")
        self.state.setdefault("recent_concepts", [])

    async def tick(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        seed = input_data.get("concept")
        dmn = float(input_data.get("dmn_strength", 0.5))
        recent = list(self.state.get("recent_concepts", []))

        if seed and seed not in recent:
            recent.append(seed)
            recent = recent[-32:]
            self.state["recent_concepts"] = recent

        branches: List[str] = []
        if seed:
            n = max(1, int(self.BRANCH_FACTOR * dmn))
            for other in recent[-n:]:
                if other != seed:
                    branches.append(f"{seed} :: {other}")

        self.persist_state()
        return {
            "signal_type": "creative",
            "seed": seed,
            "associations": branches,
            "divergence": dmn,
        }


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------

class TopDownLimbicCalmer(BrainMechanism):
    """
    Prefrontal top-down regulation. When limbic arousal is high and the
    cognitive frame is stable, this mechanism produces a 'calm' signal
    that downstream regulators (CRL, energy budgeting) use to throttle
    runaway emotion.
    """

    def __init__(self):
        super().__init__(name="TopDownLimbicCalmer", human_analog="vmPFC→amygdala damping", layer="integration")
        self.state.setdefault("calming_strength", 0.0)

    async def tick(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        arousal = float(input_data.get("arousal", 0.3))
        coherence = float(input_data.get("coherence", 0.7))
        # Calm only when arousal is elevated AND we still have coherent control
        if arousal > 0.6 and coherence > 0.5:
            target = _clip(0.5 * (arousal - 0.5) + 0.3 * coherence)
        else:
            target = 0.0
        self.state["calming_strength"] = self.state["calming_strength"] * 0.5 + target * 0.5
        self.persist_state()
        return {
            "signal_type": "calming",
            "calming_strength": self.state["calming_strength"],
            "applied_to": ["amygdala", "limbic_drive"],
        }


class BottomUpUrgencyInjector(BrainMechanism):
    """
    Bottom-up salience injector. Fires when interoceptive/visceral signals
    spike — pushes 'urgency' into the integration layer so executive
    frames can't ignore body-state pressure.
    """

    def __init__(self):
        super().__init__(name="BottomUpUrgencyInjector", human_analog="Amygdala→ACC urgency drive", layer="integration")
        self.state.setdefault("urgency", 0.0)

    async def tick(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        visceral = float(input_data.get("visceral_pressure", 0.0))
        threat = float(input_data.get("threat_signal", 0.0))
        novelty = float(input_data.get("novelty", 0.0))
        target = _clip(0.5 * threat + 0.3 * visceral + 0.2 * novelty)
        # Urgency rises fast, decays slow
        if target > self.state["urgency"]:
            self.state["urgency"] = target
        else:
            self.state["urgency"] = self.state["urgency"] * 0.85
        self.persist_state()
        return {
            "signal_type": "primal_urgency",
            "urgency": self.state["urgency"],
            "fires_interrupt": self.state["urgency"] > 0.65,
        }


# ---------------------------------------------------------------------------
# Narrative
# ---------------------------------------------------------------------------

class NarrativeMemory(BrainMechanism):
    """
    Rolling narrative buffer — keeps the last N self-narrative beats
    (what the agent did, said, felt, decided). Provides the continuity
    spine for identity_drift and narrative_weaver.
    """

    BUFFER_SIZE = 50

    def __init__(self):
        super().__init__(name="NarrativeMemory", human_analog="Autobiographical narrative buffer", layer="narrative")
        self.state.setdefault("beats", [])

    async def tick(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        beat_text = input_data.get("beat") or input_data.get("text")
        beats: List[dict] = self.state.get("beats", [])
        if beat_text:
            beats.append({
                "ts": _now_iso(),
                "text": beat_text[:500],
                "kind": input_data.get("kind", "general"),
            })
            beats = beats[-self.BUFFER_SIZE:]
            self.state["beats"] = beats
            self.persist_state()
        return {
            "signal_type": "narrative",
            "buffer_depth": len(beats),
            "latest": beats[-1] if beats else None,
        }


__all__ = [
    "MoodAutonomicLink",
    "ContextSceneBuilder",
    "LayerIVSensoryGate",
    "TemporalSemanticLinker",
    "DefaultModeSelfReferencer",
    "CreativeAssociationDiverger",
    "TopDownLimbicCalmer",
    "BottomUpUrgencyInjector",
    "NarrativeMemory",
]
