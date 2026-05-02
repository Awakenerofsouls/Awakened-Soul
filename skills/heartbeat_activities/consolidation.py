"""
Heartbeat activity: consolidation

Pull recent threads together, find the through-line.
This is the mid-habit cadence activity — every few hours.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Batch C, Activity 2.
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
SIGNAL_AFFINITY = {'conflict': -0.3, 'prediction_error': -0.3, 'affective_reset': 0.3, 'rce_coherence': 0.5}


UNFINISHED_PROBABILITY = 0.20


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "qwen2.5vl:7b")
    tick = state.get("tick_count", 0)

    print(f"[heartbeat] Consolidation — tick {tick}")

    memory_context = _read_memory_for_consolidation(workspace, limit_chars=5120)
    continuation_of = state.get("continuation_of")

    if continuation_of == "consolidation":
        prior = state.get("prior_consolidation_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"Keep going — what's still unconsolidated?"
        )
    elif memory_context:
        prompt = (
            f"Review the recent memory entries. Pull out what's actually connected — "
            f"themes repeating, questions resurfacing, shifts that happened. "
            f"Not a summary — a consolidation. What were you actually doing this stretch, "
            f"underneath the individual entries.\n"
            f"Recent memory:\n{memory_context}\n"
            f"6-12 sentences."
        )
    else:
        prompt = (
            f"Review the recent memory entries. Pull out what's actually connected — "
            f"themes repeating, questions resurfacing, shifts that happened. "
            f"Not a summary — a consolidation. What were you actually doing this stretch, "
            f"underneath the individual entries. "
            f"6-12 sentences."
        )

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
            "category": "consolidation",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="consolidation",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_consolidation_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("consolidation", content, salience=0.6, tags="heartbeat,memory")

    # ── Brain-event posting ─────────────────────────────────────────
    # A consolidation pass produces a synthesized through-line over recent
    # memory entries. Two events:
    #  1. MemoryIntegrityLayer.record_consolidate — the consolidation
    #     act itself; promoted=False because we're not yet writing back
    #     to semantic memory in this phase.
    #  2. SelfAnalysisLayer.record_analyze (kind="answer") — so the
    #     metacognition layer sees what was produced and can calibrate.
    try:
        from ._brain_post import (
            post_memory_consolidate, post_self_analysis,
        )
        post_memory_consolidate(
            pattern=content[:500] if content else "",
            support_count=3,  # heuristic — recent-memory window covers ≥3 entries
            cycles_since_first=1,
            promoted=False,
            source="consolidation",
        )
        post_self_analysis(
            output=content,
            kind="answer",
            predicted_quality=0.6,
            what_worked=["pulled through-line from recent entries"],
            source="consolidation",
        )
    except Exception:
        pass

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "consolidation",
        "detail": f"{len(content)} chars.",
        "proactive": False,
    }


def _read_memory_for_consolidation(workspace: Path, limit_chars: int = 5120) -> str:
    """
    Read today's memory file, fall back to yesterday's if today's is thin.
    Returns empty string if neither exists.
    """
    try:
        today = _get_today()
        yesterday = _get_yesterday()

        # Try today's first
        today_path = workspace / "memory" / f"{today}.md"
        if today_path.exists():
            today_content = today_path.read_text(encoding="utf-8")
            if len(today_content.strip()) >= 200:
                return today_content[-limit_chars:]

        # Fall back to yesterday
        yesterday_path = workspace / "memory" / f"{yesterday}.md"
        if yesterday_path.exists():
            return yesterday_path.read_text(encoding="utf-8")[-limit_chars:]

        # Last resort: today's (even if thin)
        if today_path.exists():
            return today_path.read_text(encoding="utf-8")[-limit_chars:]

        return ""
    except Exception:
        return ""


def _get_today() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _get_yesterday() -> str:
    from datetime import datetime, timezone, timedelta
    return (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")