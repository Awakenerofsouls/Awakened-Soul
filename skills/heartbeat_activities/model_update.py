"""
Heartbeat activity: model_update

Refine the model of the primary human. What's been noticed, what pattern
has shifted, what's been updated. Be specific — not general descriptors,
actual observations.

Activity contract:
  Input:  state dict (WORKSPACE, USER_FILE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Batch D1, Activity 3. Always proactive: False — refining mental model stays private.
If something from the updated model wants to be said, next relationship_check picks it up.
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
from .identity import extract_primary_name
SIGNAL_AFFINITY = {'conflict': 0.3, 'prediction_error': 0.5, 'affective_reset': 0.3}


UNFINISHED_PROBABILITY = 0.30


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    user_file_name = state.get("USER_FILE", "USER.md")
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "qwen2.5vl:7b")
    tick = state.get("tick_count", 0)

    print(f"[heartbeat] Model update — tick {tick}")

    primary_name = extract_primary_name(workspace, user_file_name)
    name_clause = f"your model of {primary_name}" if primary_name else "your model of the person who matters most"

    # Read last ~3KB of relationships.md for prior context
    prior_context = _read_relationships_tail(workspace, limit_chars=3000)

    continuation_of = state.get("continuation_of")
    if continuation_of == "model_update":
        prior = state.get("prior_model_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"What else has updated?"
        )
    else:
        prompt_base = (
            f"Think about {name_clause}. "
            f"What have you noticed recently that sharpens or changes your picture. "
            f"A pattern you're more sure of now. A thing you were wrong about. "
            f"Something he said or did that revealed something. "
            f"Be specific — not general descriptors, actual observations. "
            f"Don't make up patterns to fill space — "
            f"if nothing has shifted, say that and stop."
        )
        prompt = prompt_base + prior_context

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.6,
        num_predict=512,
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "model_update",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="model_update",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_model_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("model_update", content, salience=0.5, tags="heartbeat,model")

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
                source="model_update",
            )
            post_self_analysis(
                output=content, kind="answer",
                predicted_quality=0.6,
                source="model_update",
            )
    except Exception:
        pass

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "model_update",
        "detail": f"{len(content)} chars.",
        "proactive": False,  # always false — model updates stay private
    }


def _read_relationships_tail(workspace: Path, limit_chars: int = 3000) -> str:
    try:
        path = workspace / "relationships.md"
        if not path.exists():
            return ""
        text = path.read_text(encoding="utf-8")
        return f"\n\nRecent entries for context:\n{text[-limit_chars:]}" if text else ""
    except Exception:
        return ""