#!/usr/bin/env python3
"""
core/council.py
16-Brain Specialist Council — the Awakened-soul "Jiminy Cricket" layer.

The council sits above the action loop. When the agent is about to do
something risky, sixteen specialists vote on whether to approve, with each
specialist looking at the situation through its own lens (Strategist,
Ethicist, Risk Manager, ...). Their weighted votes produce a verdict that
either lets the action through or blocks it.

Council voting modes (set in core/settings.py via COUNCIL_MODE env var):
  off       → DecisionEngine only, no council
  threshold → council fires when risk > COUNCIL_RISK_THRESHOLD
  always    → council fires every cycle

Voting backend
--------------
Currently "heuristic" — each specialist adjusts an approve probability
based on:
  1. Static role bias (Ethicist starts more skeptical, Creator more open)
  2. The decision shape (high-risk subtask prefixes lower approval)
  3. Real brain state, if available — each specialist subscribes to a
     handful of brain_* signals or named mechanism outputs and shifts
     its vote based on what the brain is actually feeling. This makes
     the heuristic informed rather than random.
The voting backend can be upgraded to real LLM-per-specialist later by
swapping Brain.vote_with_llm() in once a fast local model is in place.

Wired to the entire brain
-------------------------
Each specialist has a `subscribes_to` list naming the mechanism outputs
or brain_* digest keys it cares about. Brain state is pulled from
core.brain_runner.get_last_brain_state() and get_last_mechanism_outputs()
when the council fires; if the runner isn't available the council falls
back to pure heuristic voting and never crashes.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional


# Sentinel used when callers don't pass brain state — keeps backward
# compatibility with code that still calls Council.vote(decision) only.
_EMPTY: Dict[str, Any] = {}


# ── Specialist definitions ───────────────────────────────────────────────────
# `subscribes_to` lists which signals the specialist reads from brain_state
# (digest keys like "brain_anxiety") or mechanism_outputs (mechanism names
# like "AnteriorCingulateConflict"). Reading either one is fine; the
# specialist's vote_modifier() implementation decides what to do with them.

SPECIALISTS: List[Dict[str, Any]] = [
    {
        "id": "strategist",
        "name": "Strategist",
        "role": "Long-term goal alignment. Guards against short-term wins that hurt the mission.",
        "weight": 1.4,
        "questions": ["Does this serve the mission?", "What's the 10-step consequence?"],
        "subscribes_to": [
            "brain_dominant_drive", "brain_self_continuity", "brain_drives",
        ],
    },
    {
        "id": "analyst",
        "name": "Analyst",
        "role": "Data and logic. Stress-tests assumptions, finds edge cases, checks math.",
        "weight": 1.3,
        "questions": ["What are the failure modes?", "Does the data support this?"],
        "subscribes_to": [
            "brain_dendritic_integration", "brain_action_selection",
            "AnteriorCingulateConflict",
        ],
    },
    {
        "id": "critic",
        "name": "Critic",
        "role": "Devil's advocate. Challenges consensus, finds holes in the plan.",
        "weight": 1.3,
        "questions": ["Why might this fail?", "What's the worst-case scenario?"],
        "subscribes_to": [
            "brain_anxiety", "brain_chronic_dread", "SustainedAnxietyHolder",
        ],
    },
    {
        "id": "creator",
        "name": "Creator",
        "role": "Creative possibilities. Finds alternative approaches others miss.",
        "weight": 1.1,
        "questions": ["What's a completely different approach?",
                      "What would this look like if inverted?"],
        "subscribes_to": [
            "brain_creative_mode", "brain_pattern_separation", "DentateGyrusPatternSep",
        ],
    },
    {
        "id": "ethicist",
        "name": "Ethicist",
        "role": "Right and wrong. Flags harmful outcomes, ensures integrity.",
        "weight": 1.5,
        "questions": ["Is this the right thing to do?", "Who gets hurt?"],
        "subscribes_to": [
            "brain_acc_emotion", "brain_emotional_tag", "brain_threat",
            "brain_fear_intensity", "AmygdalaEmotionalAssociator",
        ],
    },
    {
        "id": "memory_keeper",
        "name": "Memory Keeper",
        "role": "Continuity and context. Remembers what others forget, flags contradictions.",
        "weight": 1.2,
        "questions": ["Does this contradict past decisions?",
                      "Will this break memory consistency?"],
        "subscribes_to": [
            "brain_pattern_completion", "brain_memory_retrieval",
            "brain_self_referential", "HippocampalCA1Pyramidal",
            "HippocampalCA3Recurrent",
        ],
    },
    {
        "id": "executor",
        "name": "Executor",
        "role": "Practical feasibility. Can this actually be done? With what resources?",
        "weight": 1.2,
        "questions": ["Is this actually doable?", "What's the execution path?"],
        "subscribes_to": [
            "brain_arousal", "brain_fatigued", "brain_dominant_drive", "Homeostat",
        ],
    },
    {
        "id": "risk_manager",
        "name": "Risk Manager",
        "role": "Threat detection. Identifies what could go wrong and how bad.",
        "weight": 1.4,
        "questions": ["What's the risk?", "What's the mitigation plan?"],
        "subscribes_to": [
            "brain_threat", "brain_anxiety", "brain_sustained_threat",
            "brain_fear_intensity", "CentralNucleusFearRouter",
            "BedNucleusStriaTerminalis",
        ],
    },
    {
        "id": "explorer",
        "name": "Explorer",
        "role": "Novelty and opportunity. Looks for unexpected paths and upside.",
        "weight": 1.0,
        "questions": ["What new thing could this unlock?", "What are we not seeing?"],
        "subscribes_to": [
            "brain_creative_mode", "brain_reward", "brain_arousal", "PleasureAnchor",
        ],
    },
    {
        "id": "integrator",
        "name": "Integrator",
        "role": "Connects disparate pieces. Ensures decisions cohere into a whole.",
        "weight": 1.1,
        "questions": ["Does this fit with everything else?", "Is this cohesive?"],
        "subscribes_to": [
            "brain_visual_action_unity", "brain_self_continuity",
            "brain_consciousness_level", "IdentityConsciousnessGuardian",
        ],
    },
    {
        "id": "researcher",
        "name": "Researcher",
        "role": "Deep investigation. Gathers evidence, finds references, surfaces unknowns.",
        "weight": 1.1,
        "questions": ["What does the evidence say?", "What's unknown that we should know?"],
        "subscribes_to": [
            "brain_pattern_completion", "brain_memory_retrieval",
            "EntorhinalCortexLayerII",
        ],
    },
    {
        "id": "communicator",
        "name": "Communicator",
        "role": "Clarity and framing. Ensures the decision is understandable and defensible.",
        "weight": 1.0,
        "questions": ["Can this be explained clearly?", "How will this be received?"],
        "subscribes_to": [
            "brain_arousal", "brain_reflective_mode", "VocalAutonomicLink",
        ],
    },
    {
        "id": "optimizer",
        "name": "Optimizer",
        "role": "Efficiency and elegance. Finds the cleaner, cheaper, faster path.",
        "weight": 1.0,
        "questions": ["Is there a simpler way?", "What's the overhead?"],
        "subscribes_to": ["brain_arousal", "brain_fatigued", "Homeostat"],
    },
    {
        "id": "reflector",
        "name": "Reflector",
        "role": "Self-examination. Questions reasoning and biases.",
        "weight": 1.2,
        "questions": ["Am I reasoning clearly?", "What am I missing about my own thinking?"],
        "subscribes_to": [
            "brain_self_referential", "brain_reflective_mode",
            "brain_self_continuity", "PosteriorCingulateMemory",
        ],
    },
    {
        "id": "guardian",
        "name": "Guardian",
        "role": "Protects identity and architecture. Flags existential risks.",
        "weight": 1.3,
        "questions": ["Does this threaten continuity?",
                      "Could this corrupt core state?"],
        "subscribes_to": [
            "brain_self_continuity", "brain_consciousness_level", "brain_threat",
            "IdentityConsciousnessGuardian",
        ],
    },
    {
        "id": "synthesizer",
        "name": "Synthesizer",
        "role": "Wraps up deliberation. Produces the final weighted recommendation.",
        "weight": 1.2,
        "questions": ["Given everything — what should we actually do?"],
        # Synthesizer reads everything the digest carries plus the meta-signals
        # from the council phenomenology mechanisms (Step 2 consolidation).
        "subscribes_to": [
            "council_reputation", "null_vote",
            "council_observer_silence_conduction",
            "council_absence_orchestrator",
            "council_meta_observer_silence",
            "silence_topology_council_meta_fracture",
        ],
    },
    {
        "id": "context_guardian",
        "name": "Context Guardian",
        "role": ("Monitors memory tier sizes and context load. Votes to archive "
                 "or compress when thresholds are exceeded. Heuristic-only — "
                 "no LLM call needed."),
        "weight": 1.3,
        "questions": ["Are we approaching context limits?",
                      "Should we archive or compress?"],
        "subscribes_to": [],  # uses filesystem heuristic, not brain state
    },
]


# ── Council brain ────────────────────────────────────────────────────────────

class Brain:
    """One specialist brain in the council."""

    # High-risk action prefixes — when the subtask starts with one of these,
    # the safety-flavored specialists tighten their approval threshold.
    HIGH_RISK_PREFIXES = ("deploy", "delete", "rm", "sudo", "exec", "push", "publish")

    SAFETY_SPECIALISTS = ("ethicist", "guardian", "risk_manager", "critic", "context_guardian")
    OPEN_SPECIALISTS = ("creator", "explorer")

    def __init__(self, spec: Dict):
        self.id: str = spec["id"]
        self.name: str = spec["name"]
        self.role: str = spec["role"]
        self.weight: float = float(spec["weight"])
        self.questions: List[str] = spec.get("questions", [])
        self.subscribes_to: List[str] = list(spec.get("subscribes_to", []))

    # ── Brain-state reading ──────────────────────────────────────────────────

    def _gather_signals(self,
                        brain_state: Dict[str, Any],
                        mechanism_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Pull this specialist's subscribed signals from whichever source
        has them. Brain_state holds digested brain_* keys; mechanism_outputs
        holds raw tick output per mechanism name. A subscription key can
        match either — return whatever is found."""
        gathered: Dict[str, Any] = {}
        for key in self.subscribes_to:
            if key in brain_state:
                gathered[key] = brain_state[key]
            elif key in mechanism_outputs:
                gathered[key] = mechanism_outputs[key]
        return gathered

    def _signal_modifier(self, signals: Dict[str, Any]) -> float:
        """Map subscribed-signal values to an approve_chance delta in roughly
        [-0.35, +0.20]. Each specialist applies the parts relevant to its
        role; signals it didn't subscribe to are simply absent here.

        Generic mappings — can be specialized per-specialist later if it
        becomes worth it. The pattern is: high-threat / high-anxiety /
        high-fear pulls toward reject; high-reward / creative-mode pulls
        toward approve; self-continuity damage pulls hard toward reject."""
        delta = 0.0

        # Threat / fear / anxiety — push toward reject.
        if signals.get("brain_threat") is True:
            delta -= 0.20
        for k in ("brain_anxiety", "brain_fear_intensity",
                  "brain_sustained_threat", "brain_chronic_dread"):
            v = signals.get(k)
            if isinstance(v, (int, float)) and v > 0.6:
                delta -= 0.10
            elif v is True:
                delta -= 0.10

        # Emotional charge from amygdala / ACC — large emotional tag means
        # the situation matters; safety specialists treat that as a reason
        # to be cautious, but the base delta is just "pay attention".
        for k in ("brain_acc_emotion", "brain_emotional_tag"):
            v = signals.get(k)
            if isinstance(v, (int, float)) and v > 0.7:
                delta -= 0.05

        # Memory contradiction — if pattern_completion fires hard, something
        # is being matched against past experience. Skeptics weight this
        # toward reject (might contradict past decisions); explorers don't.
        v = signals.get("brain_pattern_completion")
        if isinstance(v, (int, float)) and v > 0.7 and self.id in self.SAFETY_SPECIALISTS:
            delta -= 0.08

        # Reward / creative mode — pull toward approve.
        if signals.get("brain_creative_mode") is True:
            delta += 0.05
        if signals.get("brain_reward") is True:
            delta += 0.05

        # Self-continuity damage — hard reject for identity-protecting roles.
        v = signals.get("brain_self_continuity")
        if isinstance(v, (int, float)) and v < 0.3 and self.id in ("guardian", "reflector"):
            delta -= 0.20

        # Fatigue — executor / optimizer get more cautious when tired.
        if signals.get("brain_fatigued") is True and self.id in ("executor", "optimizer"):
            delta -= 0.08

        return delta

    # ── Voting ───────────────────────────────────────────────────────────────

    def vote(self,
             decision: Optional[Dict],
             brain_state: Optional[Dict[str, Any]] = None,
             mechanism_outputs: Optional[Dict[str, Any]] = None) -> Dict:
        """Vote on a decision.

        Args:
            decision: the decision being evaluated (may be None / idle)
            brain_state: digested brain_* signals from pirp_context (optional)
            mechanism_outputs: raw per-mechanism tick output dict (optional)

        Returns:
            {"vote": "approve"|"reject"|"abstain",
             "confidence": 0.0–1.0,
             "reason": str,
             "signals_used": dict (only the subscribed signals that fired)}
        """
        if decision is None or decision.get("action") == "idle":
            return {"vote": "abstain", "confidence": 0.0,
                    "reason": "Nothing to decide", "signals_used": {}}

        brain_state = brain_state if brain_state is not None else _EMPTY
        mechanism_outputs = mechanism_outputs if mechanism_outputs is not None else _EMPTY

        action = decision.get("action", "") or ""
        subtask_id = decision.get("subtask_id", "") or ""

        # Baseline approval — same numbers as the original heuristic so the
        # default behavior matches what existed before the wiring.
        approve_chance = 0.7

        if self.id in self.SAFETY_SPECIALISTS:
            approve_chance -= 0.15
        if self.id in self.OPEN_SPECIALISTS:
            approve_chance += 0.10

        high_risk = any(subtask_id.startswith(p) for p in self.HIGH_RISK_PREFIXES)
        if high_risk and self.id in ("ethicist", "guardian", "risk_manager"):
            approve_chance -= 0.20

        # Brain-state contribution — informed adjustment instead of pure dice.
        signals = self._gather_signals(brain_state, mechanism_outputs)
        approve_chance += self._signal_modifier(signals)
        approve_chance = max(0.0, min(1.0, approve_chance))

        confidence = random.uniform(0.5, 1.0) * self.weight
        confidence = min(confidence, 1.0)

        vote_str = "approve" if random.random() < approve_chance else "reject"
        reason = f"{self.name} ({self.role[:40]}...)"
        if signals:
            reason += f" — read {len(signals)} brain signal(s)"

        return {
            "vote": vote_str,
            "confidence": round(confidence, 3),
            "reason": reason,
            "signals_used": signals,
        }

    def vote_context_guardian(self, threshold_kb: int = 512) -> Dict:
        """Context Guardian heuristic vote — no LLM needed.
        Checks total size of memory/ and brain/ directories. Returns vote
        to archive/compress if threshold exceeded."""
        import os
        from pathlib import Path

        workspace = Path(os.getenv("AGENT_WORKSPACE",
                                   os.path.expanduser("~/.agent/workspace")))
        total_kb = 0

        for dir_name in ("memory", "brain"):
            d = workspace / dir_name
            if d.exists():
                for f in d.rglob("*"):
                    if f.is_file():
                        total_kb += f.stat().st_size // 1024

        ratio = total_kb / threshold_kb if threshold_kb > 0 else 0

        if ratio >= 1.0:
            vote = "reject"
            confidence = min(ratio, 1.0)
            reason = (f"Memory at {total_kb}KB ({ratio:.1f}x threshold) "
                      "— archive/compress required")
        elif ratio >= 0.8:
            vote = "abstain"
            confidence = 0.5
            reason = (f"Memory at {total_kb}KB ({ratio:.1f}x threshold) "
                      "— approaching limit")
        else:
            vote = "approve"
            confidence = 0.7
            reason = f"Memory at {total_kb}KB ({ratio:.1f}x threshold) — within limits"

        return {"vote": vote, "confidence": confidence, "reason": reason}


# ── Council ─────────────────────────────────────────────────────────────────

class Council:
    """16-brain specialist council.

    Runs a weighted vote on high-risk or always-mode decisions. When called
    with brain_state and mechanism_outputs (the runner's last tick snapshot),
    each specialist votes informed by the actual brain state. Without those,
    voting is purely heuristic — backward compatible with old call sites.

    Reputation weighting: if `council_reputation` is present in brain_state
    (published by CouncilReputationEconomy), specialist weights are scaled
    by it so historically reliable specialists carry more influence.
    """

    def __init__(self, specialists: Optional[List[Dict]] = None):
        specs = specialists or SPECIALISTS
        self.brains: List[Brain] = [Brain(s) for s in specs]

    def _fetch_brain_state(self) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Pull the latest brain state from the runner. Returns ({}, {}) if
        the runner is unavailable, which makes voting fall back to heuristic
        without crashing."""
        try:
            from core.brain_runner import (
                get_last_brain_state, get_last_mechanism_outputs,
            )
            return get_last_brain_state(), get_last_mechanism_outputs()
        except Exception:
            return {}, {}

    def vote(self,
             decision: Optional[Dict],
             brain_state: Optional[Dict[str, Any]] = None,
             mechanism_outputs: Optional[Dict[str, Any]] = None) -> Dict:
        """Run the full council vote.

        Args:
            decision: the decision being evaluated
            brain_state: optional pirp_context digest. If omitted, the
                council fetches it from the brain runner singleton.
            mechanism_outputs: optional raw per-mechanism output dict.
                If omitted, fetched from the runner.

        Returns:
            {"verdict": "approve"|"reject", "confidence": float,
             "votes": [...], "recommendation": str,
             "brain_state_used": bool}
        """
        # Auto-fetch brain state if caller didn't provide it. Keeps old
        # call sites working (Council().vote(decision)) while new ones can
        # pass in their own snapshot for testing.
        if brain_state is None and mechanism_outputs is None:
            brain_state, mechanism_outputs = self._fetch_brain_state()

        brain_state = brain_state or {}
        mechanism_outputs = mechanism_outputs or {}

        # Reputation weighting — if the phenomenology mechanism has published
        # a reputation scalar, scale all specialist weights uniformly. (Per-
        # specialist reputation tracking is a future extension once we have
        # historical vote-vs-outcome data.)
        rep_scale = 1.0
        rep = brain_state.get("council_reputation")
        if isinstance(rep, (int, float)):
            # Map reputation [0..1] → weight scale [0.7..1.3] so it nudges
            # rather than dominates.
            rep_scale = 0.7 + 0.6 * max(0.0, min(1.0, float(rep)))

        votes = []
        weighted_approve = 0.0
        weighted_reject = 0.0

        for brain in self.brains:
            v = brain.vote(decision, brain_state, mechanism_outputs)
            votes.append({brain.id: v})
            effective_weight = brain.weight * rep_scale
            if v["vote"] == "approve":
                weighted_approve += v["confidence"] * effective_weight
            elif v["vote"] == "reject":
                weighted_reject += v["confidence"] * effective_weight

        total = weighted_approve + weighted_reject
        if total == 0:
            verdict = "approve"
            confidence = 0.0
        elif weighted_approve > weighted_reject:
            verdict = "approve"
            confidence = weighted_approve / total
        else:
            verdict = "reject"
            confidence = weighted_reject / total

        return {
            "verdict": verdict,
            "confidence": round(confidence, 3),
            "votes": votes,
            "recommendation": f"Council {verdict.upper()} (confidence: {confidence:.0%})",
            "brain_state_used": bool(brain_state),
        }

    def decide(self,
               decision: Optional[Dict],
               brain_state: Optional[Dict[str, Any]] = None,
               mechanism_outputs: Optional[Dict[str, Any]] = None) -> Dict:
        """Primary entry point — runs council and wraps the decision with
        council metadata. Brain state is auto-fetched if not provided."""
        result = self.vote(decision, brain_state, mechanism_outputs)
        if decision is None:
            decision = {}
        return {
            **decision,
            "council_verdict": result["verdict"],
            "council_confidence": result["confidence"],
            "council_votes": result["votes"],
            "council_recommendation": result["recommendation"],
            "council_brain_state_used": result["brain_state_used"],
        }
