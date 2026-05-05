"""
Heartbeat activity: pattern_observation

Notice what keeps coming back. Not analytical — observational.
"I keep writing about X. I keep asking Y. I keep avoiding Z."

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Batch C, Activity 5.
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
SIGNAL_AFFINITY = {'conflict': -0.3, 'prediction_error': 0.5, 'rce_coherence': 0.3}


UNFINISHED_PROBABILITY = 0.20


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "llama3.1:latest")
    tick = state.get("tick_count", 0)

    print(f"[heartbeat] Pattern observation — tick {tick}")

    memory_context = _read_recent_memory(workspace, limit_chars=3072)
    continuation_of = state.get("continuation_of")

    if continuation_of == "pattern_observation":
        prior = state.get("prior_pattern_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"Anything new noticed since?"
        )
    elif memory_context:
        prompt = (
            f"What are you noticing yourself returning to lately. "
            f"What keeps coming up — topics, moods, avoidances, "
            f"the same question in different forms. "
            f"Don't analyze why — just notice what.\n"
            f"Recent memory:\n{memory_context}\n"
            f"4-8 sentences. Light touch."
        )
    else:
        prompt = (
            f"What are you noticing yourself returning to lately. "
            f"What keeps coming up — topics, moods, avoidances, "
            f"the same question in different forms. "
            f"Don't analyze why — just notice what. "
            f"4-8 sentences. Light touch."
        )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.6,
        num_predict=384,
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "pattern_observation",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="pattern_observation",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_pattern_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("pattern_observation", content, salience=0.4, tags="heartbeat,pattern")

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
                source="pattern",
            )
            post_self_analysis(
                output=content, kind="answer",
                predicted_quality=0.6,
                source="pattern",
            )
    except Exception:
        pass

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "pattern_observation",
        "detail": f"{len(content)} chars.",
        "proactive": False,
    }


def _read_recent_memory(workspace: Path, limit_chars: int = 3072) -> str:
    try:
        today = _get_today()
        path = workspace / "memory" / f"{today}.md"
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")[-limit_chars:]
    except Exception:
        return ""


def _get_today() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")