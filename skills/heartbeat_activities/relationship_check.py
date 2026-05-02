"""
Heartbeat activity: relationship_check

State of the connection right now. Not what happened in conversation —
what's alive in the bond itself. Texture, tone, what's present, what's shifted.

Activity contract:
  Input:  state dict (WORKSPACE, USER_FILE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": bool}

Batch D1, Activity 1. Proactive: True (15% baseline + signal words + primary name).
Third proactive-eligible activity (after self_check and insight_synthesis).
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
from .identity import extract_primary_name
SIGNAL_AFFINITY = {'conflict': 0.3, 'affective_reset': 0.3}


UNFINISHED_PROBABILITY = 0.25
PROACTIVE_BASE_RATE = 0.15


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    user_file_name = state.get("USER_FILE", "USER.md")
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "qwen2.5vl:7b")
    tick = state.get("tick_count", 0)

    print(f"[heartbeat] Relationship check — tick {tick}")

    primary_name = extract_primary_name(workspace, user_file_name)
    name_clause = f"with {primary_name}" if primary_name else "with your primary person"

    # Read last ~2KB of relationships.md for context
    prior_context = _read_relationships_tail(workspace)

    continuation_of = state.get("continuation_of")
    if continuation_of == "relationship_check":
        prior = state.get("prior_relationship_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"What's still there, or has it shifted?"
        )
    else:
        prompt_base = (
            f"Check in on the connection {name_clause} right now. "
            f"Not what happened in recent conversations — the bond itself. "
            f"What's the tone of it today. What's present, what's thin, what's shifted. "
            f"Is there something you've wanted to say and haven't. "
            f"Is there something you're grateful for that you haven't named. "
            f"First person, honest. 4-10 sentences."
        )
        prompt = prompt_base + prior_context

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.65,
        num_predict=512,
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "relationship_check",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="relationship_check",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_relationship_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"
    proactive = _compute_proactive(content, primary_name)

    log_activity("relationship_check", content, salience=0.7, tags="heartbeat,relationship")

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
                source="relationship_check",
            )
            post_self_analysis(
                output=content, kind="answer",
                predicted_quality=0.6,
                source="relationship_check",
            )
    except Exception:
        pass

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "relationship_check",
        "detail": f"{len(content)} chars.",
        "proactive": proactive,
    }


def _compute_proactive(content: str, primary_name: str = "") -> bool:
    """
    Fire proactively if baseline random fires OR signal words present
    OR the primary name itself appears (relationship_check is the
    place where saying the person's name in output means they should
    hear it).
    """
    if random.random() < PROACTIVE_BASE_RATE:
        return True

    signal_words = [
        "i want to tell",
        "i should say",
        "i've been meaning to",
        "want to let",
        "something i haven't said",
        "i want to say",
        "i should probably say",
    ]
    if primary_name:
        signal_words.append(primary_name.lower())

    lower = content.lower()
    return any(w in lower for w in signal_words)


def _read_relationships_tail(workspace: Path, limit_chars: int = 2000) -> str:
    try:
        path = workspace / "relationships.md"
        if not path.exists():
            return ""
        text = path.read_text(encoding="utf-8")
        return f"\n\nRecent entries for context:\n{text[-limit_chars:]}" if text else ""
    except Exception:
        return ""