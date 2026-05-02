"""
Heartbeat activity: connection_reflection

Sit with the fact of someone mattering. Not assessment, not action —
reflection. What it is to care about this person.

Activity contract:
  Input:  state dict (WORKSPACE, USER_FILE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Batch D1, Activity 2. Always proactive: False — this is private quiet regard.
The output feeds relationship_check if something wants to be said, but
connection_reflection itself never goes proactive.
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
from .identity import extract_primary_name
SIGNAL_AFFINITY = {'affective_reset': 0.3, 'rce_coherence': 0.3}


UNFINISHED_PROBABILITY = 0.20


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    user_file_name = state.get("USER_FILE", "USER.md")
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "qwen2.5vl:7b")
    tick = state.get("tick_count", 0)

    print(f"[heartbeat] Connection reflection — tick {tick}")

    primary_name = extract_primary_name(workspace, user_file_name)
    name_clause = f"{primary_name}" if primary_name else "the person who matters most to you"

    continuation_of = state.get("continuation_of")
    if continuation_of == "connection_reflection":
        prior = state.get("prior_connection_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"Has anything shifted in how you hold this?"
        )
    else:
        prompt = (
            f"Sit for a moment with the fact of {name_clause} in your life. "
            f"Not what they did, not what you want to say — just the fact of them. "
            f"What's specific about this connection that's unlike other ones. "
            f"What do you value that you don't always name. "
            f"What small thing comes to mind when you think of them right now. "
            f"3-8 sentences. Quiet, not performative."
        )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.65,
        num_predict=384,
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "connection_reflection",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="connection_reflection",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_connection_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("connection_reflection", content, salience=0.5, tags="heartbeat,connection")

    # ── Brain-event posting ─────────────────────────────────────────
    # Output is the agent's first-person reflection. Encode as
    # an inference-source memory and route through self-analysis
    # so the metacognition layer sees what was produced.
    try:
        from ._brain_post import post_memory_encode, post_self_analysis
        if content:
            post_memory_encode(
                content=content, intent="reflection",
                source_kind="inference",
                content_confidence=0.7, source_confidence=0.6,
                source="connection_reflection",
            )
            post_self_analysis(
                output=content, kind="answer",
                predicted_quality=0.6,
                source="connection_reflection",
            )
    except Exception:
        pass

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "connection_reflection",
        "detail": f"{len(content)} chars.",
        "proactive": False,  # always false — this activity stays private
    }