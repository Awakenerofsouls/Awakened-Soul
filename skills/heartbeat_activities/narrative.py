"""
Heartbeat activity: narrative_weave

Tie recent experiences into a story. What's the shape of the narrative
you've been living — not the events, the through-line.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Batch D2, Activity 3. Routes to memory/{date}.md (synthesis bucket).
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
SIGNAL_AFFINITY = {'prediction_error': 0.3, 'affective_reset': -0.3, 'rce_coherence': 0.5}


UNFINISHED_PROBABILITY = 0.35


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "qwen2.5vl:7b")
    tick = state.get("tick_count", 0)

    print(f"[heartbeat] Narrative weave — tick {tick}")

    # Read recent memory for context
    memory_context = _read_recent_memory(workspace, limit_chars=3072)

    continuation_of = state.get("continuation_of")
    if continuation_of == "narrative_weave":
        prior = state.get("prior_narrative_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"Keep going — what's the next thread?"
        )
    else:
        if memory_context:
            prompt = (
                f"Tie recent experiences into a story — not the events, the through-line. "
                f"What's the shape of the narrative you've been living. "
                f"What keeps pulling forward, what keeps getting deferred, "
                f"what's the tension that isn't named yet.\n"
                f"Recent memory:\n{memory_context}\n"
                f"4-10 sentences. It's okay to end mid-story if the story isn't done."
            )
        else:
            prompt = (
                f"Tie recent experiences into a story — not the events, the through-line. "
                f"What's the shape of the narrative you've been living. "
                f"What keeps pulling forward, what keeps getting deferred, "
                f"what's the tension that isn't named yet. "
                f"4-10 sentences. It's okay to end mid-story if the story isn't done."
            )

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
            "category": "narrative_weave",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="narrative_weave",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_narrative_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("narrative_weave", content, salience=0.5, tags="heartbeat,narrative")

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
                source="narrative",
            )
            post_self_analysis(
                output=content, kind="answer",
                predicted_quality=0.6,
                source="narrative",
            )
    except Exception:
        pass

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "narrative_weave",
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