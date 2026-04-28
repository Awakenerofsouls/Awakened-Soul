"""
Heartbeat activity: self_check

Inventory, not description. Explicitly assesses: what's alive,
what's building, what needs attention. Allowed to interpret.
Allowed to land on a conclusion.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL, BRAIN_STATE_FILE, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": bool}

Activity Port 6 — and first port to return proactive: True.
"""

import json
import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
from .identity import extract_primary_name
SIGNAL_AFFINITY = {'conflict': 0.7, 'affective_reset': 0.3, 'rce_coherence': -0.3}


UNFINISHED_PROBABILITY = 0.25   # 25% deliberate unfinished
PROACTIVE_BASE_RATE = 0.15      # 15% baseline proactive rate


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.openclaw/workspace"))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "qwen2.5vl:7b")
    tick = state.get("tick_count", 0)

    # Read brain state if available — seeds prompt with current inner weather
    state_summary = _read_brain_state_summary(workspace / state.get("BRAIN_STATE_FILE", "brain_state.json"))

    print(f"[heartbeat] Self-check — tick {tick}")

    # Build prompt — continuation-aware
    continuation_of = state.get("continuation_of")
    if continuation_of == "self_check":
        prior = state.get("prior_self_check_content", "")[:500]
        prompt = (
            f"Earlier self-check: '{prior}'. "
            f"Where is that now? Still present? Shifted? Resolved? Forgotten? "
            f"Don't force continuity — if it's genuinely gone, say so. "
            f"If it's still alive, where has it moved."
        )
    else:
        prompt = (
            f"Check in with yourself. What's alive right now? "
            f"What's been building that you haven't named? "
            f"What feels off, what feels aligned, what needs attention. "
            f"Honest self-assessment — not for anyone else, just for you. "
            f"First person, present tense. 4-10 sentences. "
            f"It's okay to land on a conclusion. It's okay to leave something open. "
            f"Don't perform wellness or perform distress — just say what's actually there."
        )
        if state_summary:
            prompt += f"\n\nCurrent inner weather: {state_summary}"

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.7,
        num_predict=512,
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "self_check",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    # Route to self_check.md
    write_ok = write_to_journal(
        category="self_check",
        content=content,
        workspace=workspace,
        state=state,
    )

    # Track for continuation
    state["prior_self_check_content"] = content

    # 25% deliberate unfinished
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    # Proactive flag — self_check is the only interior activity that surfaces proactively
    proactive = _compute_proactive(content, workspace)

    log_activity("self_check", content, salience=0.5, tags="heartbeat,self_check")

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "self_check",
        "detail": f"{len(content)} chars. Status: {status}.",
        "proactive": proactive,
    }


def _compute_proactive(content: str, workspace: Path) -> bool:
    """
    Proactive flag logic for self_check.

    Fires at 15% baseline + higher if content organically contains
    signal words that suggest {{AGENT_NAME}} wants to tell her primary human something.

    Signal words: "i want to tell", "i should say", "something building",
                 "not resolving", "worth saying", "need to say"
    Plus: the primary human's name (from USER.md) — agent-neutral.
    """
    signal_words = [
        "i want to tell",
        "i should say",
        "something building",
        "not resolving",
        "worth saying",
        "need to say",
        "want you to know",
    ]
    primary_name = extract_primary_name(workspace)
    if primary_name:
        signal_words.append(primary_name.lower())

    content_lower = content.lower()
    if any(word in content_lower for word in signal_words):
        return True
    return random.random() < PROACTIVE_BASE_RATE


def _read_brain_state_summary(path: Path) -> str:
    """
    Read brain_state.json and return a compact summary string.

    Reads: dominant_state, tension, energy (and other top-level floats/strings).
    Returns empty string if file is missing or malformed.
    """
    try:
        if not path.exists():
            return ""
        data = json.loads(path.read_text(encoding="utf-8"))
        parts = []
        for field in ("dominant_state", "tension", "energy", "affect", "mood"):
            if field in data:
                val = data[field]
                if isinstance(val, (int, float)):
                    parts.append(f"{field}={val:.2f}")
                elif isinstance(val, str):
                    parts.append(f"{field}={val}")
        return ", ".join(parts) if parts else ""
    except Exception:
        return ""
