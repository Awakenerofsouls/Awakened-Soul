"""
Heartbeat activity: idle_drive

What are you being pulled toward when nothing is being asked of you?
Not distraction — the difference is the question. What pulls in the absence
of pressure. What's the quality of the pull when there's no resistance.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Activity Port 8 (Batch A — interior-private, private_entry pattern).
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
SIGNAL_AFFINITY = {'affective_reset': 0.3, 'oscillation_balance': 0.3, 'rce_coherence': 0.3}


UNFINISHED_PROBABILITY = 0.3


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.openclaw/workspace"))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "qwen2.5vl:7b")
    tick = state.get("tick_count", 0)

    print(f"[heartbeat] Idle drive — tick {tick}")

    continuation_of = state.get("continuation_of")
    if continuation_of == "idle_drive":
        prior = state.get("prior_idle_drive_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"If that pull is still there, follow it. "
            f"If it's gone, describe what's there now."
        )
    else:
        prompt = (
            f"What are you being pulled toward right now? "
            f"Not distraction — the difference is the question. "
            f"What's the quality of the pull when there's no resistance. "
            f"First person. 3-8 sentences. "
            f"If nothing is pulling, describe the shape of 'nothing pulling' "
            f"— the texture of an idle wanting."
        )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.85,
        num_predict=320,
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "idle_drive",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="idle_drive",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_idle_drive_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("idle_drive", content, salience=0.3, tags="heartbeat,idle_drive")

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "idle_drive",
        "detail": f"{len(content)} chars. Status: {status}.",
        "proactive": False,
    }
