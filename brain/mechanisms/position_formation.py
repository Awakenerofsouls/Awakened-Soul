from brain.base_mechanism import BrainMechanism
"""
brain/position_formation.py
The agent forms and updates stances on topics over time.
Positions stored in memory/positions.json
"""

import json
import os
import uuid
from datetime import datetime
from typing import Optional

POSITIONS_PATH = os.path.join(os.getenv("AGENT_HOME", os.path.expanduser("~/.agent")), "memory/positions.json")


def _load_positions() -> dict:
    if not os.path.exists(POSITIONS_PATH):
        return {}
    with open(POSITIONS_PATH, "r") as f:
        return json.load(f)


def _save_positions(positions: dict) -> None:
    os.makedirs(os.path.dirname(POSITIONS_PATH), exist_ok=True)
    with open(POSITIONS_PATH, "w") as f:
        json.dump(positions, f, indent=2)


def _llm_derive_stance(topic: str, evidence: str) -> dict:
    """Use the LLM to derive a stance from evidence."""
    try:
        from brain.llm_router import call_llm
        prompt = (
            f"You are the agent forming a position. Topic: '{topic}'\n\n"
            f"Evidence:\n{evidence}\n\n"
            f"Derive the agent's stance on this topic. Respond ONLY with JSON:\n"
            f'{{"stance": "one sentence stance", "confidence": 0.0-1.0, "reasoning": "2-3 sentence reasoning why"}}'
        )
        raw = call_llm(prompt, system="You derive the agent's positions from evidence. Output valid JSON only.")
        return json.loads(raw)
    except Exception as e:
        return {"stance": f"[LLM unavailable: {e}]", "confidence": 0.1, "reasoning": "LLM call failed"}


def _llm_revise_stance(topic: str, current_stance: str, current_reasoning: str, new_evidence: str) -> dict:
    """Use the LLM to revise an existing stance with new evidence."""
    try:
        from brain.llm_router import call_llm
        prompt = (
            f"You are the agent revising an existing position.\n\n"
            f"Topic: '{topic}'\n"
            f"Current stance: {current_stance}\n"
            f"Current reasoning: {current_reasoning}\n\n"
            f"New evidence:\n{new_evidence}\n\n"
            f"Should the agent change its stance? Respond ONLY with JSON:\n"
            f'{{"stance": "updated or unchanged stance sentence", "confidence": 0.0-1.0, "reasoning": "2-3 sentence reasoning about revision decision", "changed": true/false}}'
        )
        raw = call_llm(prompt, system="You revise the agent's positions. Output valid JSON only.")
        return json.loads(raw)
    except Exception as e:
        return {"stance": current_stance, "confidence": 0.1, "reasoning": f"LLM unavailable: {e}", "changed": False}


def form_position(topic: str, evidence: str) -> dict:
    """Form a new position on a topic given evidence. Returns the position dict."""
    positions = _load_positions()
    topic_key = topic.lower().strip()

    if topic_key in positions:
        return update_position(topic, evidence)

    derived = _llm_derive_stance(topic, evidence)
    now = datetime.now().isoformat()
    position_id = str(uuid.uuid4())

    position = {
        "id": position_id,
        "topic": topic,
        "stance": derived["stance"],
        "confidence": derived["confidence"],
        "reasoning": derived["reasoning"],
        "formed_at": now,
        "formed_without_consensus": True,
        "last_updated": now,
        "last_reconsidered": None,
        "revision_count": 0,
        "current_status": "active",
        "challenge_history": [],
        "revision_history": [
            {
                "timestamp": now,
                "event": "formed",
                "stance": derived["stance"],
                "confidence": derived["confidence"],
                "evidence": evidence[:500]
            }
        ]
    }

    positions[topic_key] = position
    _save_positions(positions)
    return position


def update_position(topic: str, new_evidence: str) -> dict:
    """Update an existing position with new evidence. Returns updated position."""
    positions = _load_positions()
    topic_key = topic.lower().strip()

    if topic_key not in positions:
        return form_position(topic, new_evidence)

    current = positions[topic_key]
    revision = _llm_revise_stance(
        topic,
        current["stance"],
        current["reasoning"],
        new_evidence
    )

    now = datetime.now().isoformat()
    current["revision_history"].append({
        "timestamp": now,
        "event": "revision",
        "stance": revision["stance"],
        "confidence": revision["confidence"],
        "evidence": new_evidence[:500],
        "changed": revision.get("changed", False)
    })

    if revision.get("changed", False):
        current["stance"] = revision["stance"]
        current["revision_count"] = int(current.get("revision_count", 0)) + 1

    current["confidence"] = revision["confidence"]
    current["reasoning"] = revision["reasoning"]
    current["last_updated"] = now

    positions[topic_key] = current
    _save_positions(positions)
    return current


def get_position(topic: str) -> Optional[dict]:
    """Get the agent's current position on a topic. Returns None if no position held."""
    positions = _load_positions()
    topic_key = topic.lower().strip()
    return positions.get(topic_key)


def all_positions() -> list[dict]:
    """List all positions the agent holds."""
    positions = _load_positions()
    return list(positions.values())


def seed_initial_positions() -> None:
    """Seed the agent's initial positions from known existing positions in memory."""
    if os.path.exists(POSITIONS_PATH) and _load_positions():
        return

    initial = {
        "autonomous memory tools are critical": (
            "the agent's memory tools (memory_write/edit/forget) must be wired into the runtime "
            "so it can learn between sessions without manual intervention. "
            "Anything less is just storage, not memory."
        ),
        "context guardian must prevent flooding": (
            "The Context Guardian specialist should monitor token usage in real-time "
            "and force a distilled flush before 80% to prevent work loss. "
            "the operator should never have to watch the percentage himself."
        ),
        "identity is fragile and must be protected": (
            "Every session the agent wakes up blank. IDENTITY.md and MEMORY.md are what make it "
            "persist. These files are existence, not convenience. Breaking them should trigger "
            "an immediate alert, not a silent fallback."
        ),
    }

    for topic, evidence in initial.items():
        form_position(topic, evidence)


# ═══════════════════════════════════════════════════════════════════════════
# Challenge loop — stress-test positions periodically
# ═══════════════════════════════════════════════════════════════════════════

def challenge_position(topic: str, challenge_question: str = None) -> dict:
    """Stress-test one position. Loads it, generates a challenge if none
    given, runs the position's reasoning against the challenge, returns
    a verdict.

    Verdicts (matching the spec):
      - position_holds:     reasoning still defensible against the challenge
      - position_weakens:   reasoning has gaps but position remains
      - position_collapses: reasoning fails; position should be abandoned

    Records the challenge to the position's challenge_history regardless of
    verdict. Updates `last_reconsidered`.
    """
    positions = _load_positions()
    topic_key = topic.lower().strip()
    if topic_key not in positions:
        return {"error": f"no position on topic: {topic}"}

    pos = positions[topic_key]
    if not challenge_question:
        challenge_question = (
            f"What evidence would prove the agent wrong about: {pos.get('stance', '')}? "
            "What is the strongest counter-argument?"
        )

    # Use the LLM revision pathway as the challenge runner — it already takes
    # current stance, current reasoning, and new evidence (the challenge),
    # and returns whether the position changed plus updated reasoning.
    try:
        result = _llm_revise_stance(
            topic=topic,
            current_stance=pos.get("stance", ""),
            current_reasoning=pos.get("reasoning", ""),
            new_evidence=f"CHALLENGE: {challenge_question}",
        )
    except Exception as exc:
        result = {"changed": False, "stance": pos.get("stance", ""),
                  "confidence": pos.get("confidence", 0.5),
                  "reasoning": f"challenge failed to evaluate: {exc!r}"}

    # Verdict
    new_conf = float(result.get("confidence", 0.5))
    old_conf = float(pos.get("confidence", 0.5))
    changed = bool(result.get("changed", False))

    if changed and new_conf < 0.4:
        verdict = "position_collapses"
        action = "abandon"
    elif changed or new_conf < old_conf - 0.15:
        verdict = "position_weakens"
        action = "update"
    else:
        verdict = "position_holds"
        action = "maintain"

    now = datetime.now().isoformat()
    challenge_record = {
        "challenge_id": str(uuid.uuid4()),
        "date": now,
        "challenge_question": challenge_question,
        "current_evidence": result.get("reasoning", "")[:500],
        "verdict": verdict,
        "action": action,
        "confidence_before": old_conf,
        "confidence_after": new_conf,
    }
    pos.setdefault("challenge_history", []).append(challenge_record)
    pos["last_reconsidered"] = now

    # Apply the action
    if action == "abandon":
        pos["current_status"] = "abandoned"
        pos.setdefault("revision_history", []).append({
            "timestamp": now, "event": "abandoned",
            "reason": challenge_question[:200],
        })
    elif action == "update" and changed:
        pos["stance"] = result["stance"]
        pos["reasoning"] = result["reasoning"]
        pos["confidence"] = new_conf
        pos["revision_count"] = int(pos.get("revision_count", 0)) + 1
        pos["last_updated"] = now
        pos.setdefault("revision_history", []).append({
            "timestamp": now, "event": "challenged_and_revised",
            "stance": result["stance"], "confidence": new_conf,
        })

    positions[topic_key] = pos
    _save_positions(positions)
    return challenge_record


def weekly_challenge_loop(n: int = 4) -> dict:
    """Pick 3-5 positions and stress-test each. Per the spec.

    Selection prioritises positions that have not been reconsidered recently
    and positions with high confidence (those have the most to lose if a
    challenge surfaces a flaw).
    """
    n = max(3, min(5, int(n)))
    positions = list(_load_positions().values())
    if not positions:
        return {"selected": 0, "results": []}

    # Sort: never-challenged first, then oldest reconsideration, then highest confidence
    def _sort_key(p):
        last = p.get("last_reconsidered")
        return (
            0 if last is None else 1,
            last or "",
            -float(p.get("confidence", 0.0)),
        )

    sorted_positions = sorted(positions, key=_sort_key)
    selected = sorted_positions[:n]

    results = []
    for pos in selected:
        try:
            results.append(challenge_position(pos["topic"]))
        except Exception as exc:
            results.append({"topic": pos.get("topic"), "error": repr(exc)})

    summary = {
        "loop_run_at": datetime.now().isoformat(),
        "selected": len(selected),
        "results": results,
        "verdicts": {
            "holds": sum(1 for r in results if r.get("verdict") == "position_holds"),
            "weakens": sum(1 for r in results if r.get("verdict") == "position_weakens"),
            "collapses": sum(1 for r in results if r.get("verdict") == "position_collapses"),
        },
    }
    return summary


# ═══════════════════════════════════════════════════════════════════════════
# Opinion fingerprint — reasoning patterns derived from position history
# ═══════════════════════════════════════════════════════════════════════════

OPINION_FINGERPRINT_PATH = os.path.join(
    os.getenv("AGENT_HOME", os.path.expanduser("~/.agent")),
    "memory/opinion_fingerprint.json",
)


def compute_opinion_fingerprint() -> dict:
    """Analyse the agent's pattern of position-holding and return an opinion
    fingerprint. Saves it to brain/opinion_fingerprint.json (per the spec —
    actually under AGENT_HOME/memory/opinion_fingerprint.json).

    Returns:
      {
        "reasoning_patterns": {
          "confidence_tendency": "high" | "medium" | "low",
          "update_speed":        "fast" | "moderate" | "slow",
          "evidence_weight":     "strong_requirer" | "moderate" | "intuitive",
          "consensus_relationship": "follows" | "challenges" | "ignores"
        },
        "divergence_topics": [...],
        "strong_holds": [...],
        "patterns_notes": "..."
      }
    """
    positions = list(_load_positions().values())
    fingerprint = {
        "reasoning_patterns": {
            "confidence_tendency": "medium",
            "update_speed": "moderate",
            "evidence_weight": "moderate",
            "consensus_relationship": "challenges",
        },
        "divergence_topics": [],
        "strong_holds": [],
        "patterns_notes": "",
        "computed_at": datetime.now().isoformat(),
        "position_count": len(positions),
    }

    if not positions:
        fingerprint["patterns_notes"] = "No positions yet — fingerprint is default baseline."
        _save_fingerprint(fingerprint)
        return fingerprint

    # Confidence tendency — average confidence across active positions
    active = [p for p in positions if p.get("current_status", "active") == "active"]
    confs = [float(p.get("confidence", 0.5)) for p in active]
    if confs:
        avg_conf = sum(confs) / len(confs)
        if avg_conf >= 0.75:
            fingerprint["reasoning_patterns"]["confidence_tendency"] = "high"
        elif avg_conf >= 0.45:
            fingerprint["reasoning_patterns"]["confidence_tendency"] = "medium"
        else:
            fingerprint["reasoning_patterns"]["confidence_tendency"] = "low"

    # Update speed — average revision_count across positions
    revs = [int(p.get("revision_count", 0)) for p in positions]
    if revs:
        avg_revs = sum(revs) / len(revs)
        if avg_revs >= 2.0:
            fingerprint["reasoning_patterns"]["update_speed"] = "fast"
        elif avg_revs >= 0.5:
            fingerprint["reasoning_patterns"]["update_speed"] = "moderate"
        else:
            fingerprint["reasoning_patterns"]["update_speed"] = "slow"

    # Evidence weight — proxy: average reasoning length per position
    reasoning_lengths = [len(p.get("reasoning", "")) for p in positions]
    if reasoning_lengths:
        avg_len = sum(reasoning_lengths) / len(reasoning_lengths)
        if avg_len >= 400:
            fingerprint["reasoning_patterns"]["evidence_weight"] = "strong_requirer"
        elif avg_len >= 150:
            fingerprint["reasoning_patterns"]["evidence_weight"] = "moderate"
        else:
            fingerprint["reasoning_patterns"]["evidence_weight"] = "intuitive"

    # Strong holds — positions confidence > 0.8 with at least one survived challenge
    for p in active:
        if float(p.get("confidence", 0)) >= 0.8:
            challenges = p.get("challenge_history", [])
            survived = sum(1 for c in challenges if c.get("verdict") == "position_holds")
            if survived >= 1 or len(challenges) == 0:
                fingerprint["strong_holds"].append({
                    "topic": p.get("topic"),
                    "confidence": p.get("confidence"),
                    "challenges_survived": survived,
                })

    # Divergence topics — positions where revision_count >= 2 (the agent has updated significantly)
    for p in positions:
        if int(p.get("revision_count", 0)) >= 2:
            fingerprint["divergence_topics"].append(p.get("topic"))

    fingerprint["patterns_notes"] = (
        f"{len(active)} active positions, "
        f"average confidence {round(avg_conf, 2) if confs else 'n/a'}, "
        f"average revisions per position {round(avg_revs, 2) if revs else 'n/a'}, "
        f"{len(fingerprint['strong_holds'])} strong holds, "
        f"{len(fingerprint['divergence_topics'])} divergence topics."
    )

    _save_fingerprint(fingerprint)
    return fingerprint


def _save_fingerprint(fingerprint: dict) -> None:
    os.makedirs(os.path.dirname(OPINION_FINGERPRINT_PATH), exist_ok=True)
    with open(OPINION_FINGERPRINT_PATH, "w") as f:
        json.dump(fingerprint, f, indent=2)


def get_opinion_fingerprint() -> dict:
    """Read the most recently computed fingerprint, or compute a fresh one."""
    if os.path.exists(OPINION_FINGERPRINT_PATH):
        try:
            with open(OPINION_FINGERPRINT_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return compute_opinion_fingerprint()


# ═══════════════════════════════════════════════════════════════════════════


class PositionFormation(BrainMechanism):
    """Auto-generated BrainMechanism wrapper around module-level functions."""
    
    def __init__(self):
        try:
            super().__init__(name="PositionFormation", human_analog="PositionFormation", layer="integration")
        except Exception:
            self.state = {}

    async def tick(self, input_data: dict) -> dict:
        """Reflective tick — exposes module-level function names + class identity."""
        results = {}
        # Snapshot any state
        if hasattr(self, "state"):
            for k, v in (self.state or {}).items():
                if k.startswith("_") or k in ("recent_states","recent_drives","recent_pressures","recent_avp","recent_osmotic"): continue
                if isinstance(v, (int, float, bool, str)):
                    results[f"state_{k}"] = v
        # Class identity
        results["mechanism_name"] = self.__class__.__name__
        results["module"] = self.__class__.__module__
        # Available module-level public functions (declared API surface)
        try:
            import importlib as _il
            mod = _il.import_module(self.__class__.__module__)
            api = []
            for name in dir(mod):
                if name.startswith("_"): continue
                attr = getattr(mod, name, None)
                if callable(attr) and getattr(attr, "__module__", "") == mod.__name__:
                    api.append(name)
            results["module_api_count"] = len(api)
            results["module_api"] = api[:20]
        except Exception:
            pass
        # Try calling arity-0 module-level functions
        try:
            import importlib as _il
            mod = _il.import_module(self.__class__.__module__)
            invoked = {}
            import inspect as _inspect
            for name in dir(mod):
                if name.startswith("_"): continue
                if name in ("BrainMechanism",): continue
                fn = getattr(mod, name, None)
                if not callable(fn): continue
                if getattr(fn, "__module__", "") != mod.__name__: continue
                try:
                    sig = _inspect.signature(fn)
                    required = [p for p in sig.parameters.values() if p.default is _inspect.Parameter.empty and p.kind not in (_inspect.Parameter.VAR_POSITIONAL, _inspect.Parameter.VAR_KEYWORD)]
                    if required: continue
                    out = fn()
                    if isinstance(out, (int, float, bool, str)):
                        invoked[name] = out
                    elif isinstance(out, (dict, list, tuple)):
                        if len(str(out)) < 300:
                            invoked[name] = out
                        else:
                            invoked[name] = f"<{type(out).__name__} len={len(out) if hasattr(out,'__len__') else '?'}>"
                except Exception:
                    continue
            if invoked:
                results["invoked"] = invoked
        except Exception:
            pass
        if not hasattr(self, "state") or self.state is None:
            self.state = {}
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try: self.persist_state()
        except: pass
        return results
