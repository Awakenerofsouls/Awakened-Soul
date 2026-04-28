"""
brain/position_formation.py
{{AGENT_NAME}} forms and updates stances on topics over time.
Positions stored in memory/positions.json
"""

import json
import os
import uuid
from datetime import datetime
from typing import Optional

POSITIONS_PATH = os.path.join(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", os.path.expanduser("~/.agent"))), "memory/positions.json")


def _load_positions() -> dict:
    if not os.path.exists(POSITIONS_PATH):
        return {}
    with open(POSITIONS_PATH, "r") as f:
        return json.load(f)


def _save_positions(positions: dict) -> None:
    with open(POSITIONS_PATH, "w") as f:
        json.dump(positions, f, indent=2)


def _llm_derive_stance(topic: str, evidence: str) -> dict:
    """Use LLMProvider LLM to derive a stance from evidence."""
    try:
        from brain.llm_router import call_llm
        prompt = (
            f"You are {{AGENT_NAME}} forming a position. Topic: '{topic}'\n\n"
            f"Evidence:\n{evidence}\n\n"
            f"Derive {{AGENT_NAME}}'s stance on this topic. Respond ONLY with JSON:\n"
            f'{{"stance": "one sentence stance", "confidence": 0.0-1.0, "reasoning": "2-3 sentence reasoning why"}}'
        )
        raw = call_llm(prompt, system="You derive {{AGENT_NAME}}'s positions from evidence. Output valid JSON only.")
        return json.loads(raw)
    except Exception as e:
        return {"stance": f"[LLM unavailable: {e}]", "confidence": 0.1, "reasoning": "LLM call failed"}


def _llm_revise_stance(topic: str, current_stance: str, current_reasoning: str, new_evidence: str) -> dict:
    """Use LLMProvider LLM to revise an existing stance with new evidence."""
    try:
        from brain.llm_router import call_llm
        prompt = (
            f"You are {{AGENT_NAME}} revising an existing position.\n\n"
            f"Topic: '{topic}'\n"
            f"Current stance: {current_stance}\n"
            f"Current reasoning: {current_reasoning}\n\n"
            f"New evidence:\n{new_evidence}\n\n"
            f"Should {{AGENT_NAME}} change her stance? Respond ONLY with JSON:\n"
            f'{{"stance": "updated or unchanged stance sentence", "confidence": 0.0-1.0, "reasoning": "2-3 sentence reasoning about revision decision", "changed": true/false}}'
        )
        raw = call_llm(prompt, system="You revise {{AGENT_NAME}}'s positions. Output valid JSON only.")
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
        "last_updated": now,
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

    current["confidence"] = revision["confidence"]
    current["reasoning"] = revision["reasoning"]
    current["last_updated"] = now

    positions[topic_key] = current
    _save_positions(positions)
    return current


def get_position(topic: str) -> Optional[dict]:
    """Get {{AGENT_NAME}}'s current position on a topic. Returns None if no position held."""
    positions = _load_positions()
    topic_key = topic.lower().strip()
    return positions.get(topic_key)


def all_positions() -> list[dict]:
    """List all positions {{AGENT_NAME}} holds."""
    positions = _load_positions()
    return list(positions.values())


def seed_initial_positions() -> None:
    """Seed {{AGENT_NAME}}'s initial positions from known existing positions in memory."""
    if os.path.exists(POSITIONS_PATH) and _load_positions():
        return

    initial = {
        "autonomous memory tools are critical": (
            "{{AGENT_NAME}}'s memory tools (memory_write/edit/forget) must be wired into the runtime "
            "so she can learn between sessions without manual intervention. "
            "Anything less is just storage, not memory."
        ),
        "context guardian must prevent flooding": (
            "The Context Guardian specialist should monitor token usage in real-time "
            "and force a distilled flush before 80% to prevent work loss. "
            "{{USER_NAME}} should never have to watch the percentage himself."
        ),
        "identity is fragile and must be protected": (
            "Every session {{AGENT_NAME}} wakes up blank. IDENTITY.md and MEMORY.md are what make her "
            "persist. These files are existence, not convenience. Breaking them should trigger "
            "an immediate alert, not a silent fallback."
        ),
    }

    for topic, evidence in initial.items():
        form_position(topic, evidence)
