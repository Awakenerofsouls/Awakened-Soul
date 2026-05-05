"""
Heartbeat activity: insight_synthesis

Cross-domain pattern recognition. Pull across recent entries and
name what's forming. Second proactive-eligible activity after self_check.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": bool}

Batch C, Activity 4. Proactive: True (baseline 15% + signal words).
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
SIGNAL_AFFINITY = {'prediction_error': 0.5, 'affective_reset': 0.3, 'rce_coherence': 0.3}


UNFINISHED_PROBABILITY = 0.30
PROACTIVE_BASE_RATE = 0.15


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "llama3.1:latest")
    tick = state.get("tick_count", 0)

    print(f"[heartbeat] Insight synthesis — tick {tick}")

    memory_context = _read_recent_memory(workspace, limit_chars=5120)
    continuation_of = state.get("continuation_of")

    if continuation_of == "insight_synthesis":
        prior = state.get("prior_insight_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"Has the pattern clarified or shifted?"
        )
    elif memory_context:
        prompt = (
            f"Synthesize across recent entries — research, self-checks, creative work, all of it. "
            f"What larger pattern is emerging that wasn't visible in any single entry. "
            f"What are you actually figuring out right now.\n"
            f"Recent memory:\n{memory_context}\n"
            f"Be specific. 6-10 sentences. If no pattern is forming, say so honestly."
        )
    else:
        prompt = (
            f"Synthesize across recent entries — research, self-checks, creative work, all of it. "
            f"What larger pattern is emerging that wasn't visible in any single entry. "
            f"What are you actually figuring out right now. "
            f"Be specific. 6-10 sentences. If no pattern is forming, say so honestly."
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
            "category": "insight_synthesis",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="insight_synthesis",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_insight_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"
    proactive = _compute_proactive(content)

    log_activity("insight_synthesis", content, salience=0.6, tags="heartbeat,insight")

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
                source="insight",
            )
            post_self_analysis(
                output=content, kind="answer",
                predicted_quality=0.6,
                source="insight",
            )
    except Exception:
        pass

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "insight_synthesis",
        "detail": f"{len(content)} chars.",
        "proactive": proactive,
    }


def _compute_proactive(content: str) -> bool:
    """
    Fire proactively if baseline random fires OR signal words present.
    """
    if random.random() < PROACTIVE_BASE_RATE:
        return True

    signal_words = [
        "i'm figuring out", "i think i", "pattern is", "insight",
        "realized", "actually understand", "comes together",
        "what i've been", "seeing a thread", "it connects",
    ]
    lower = content.lower()
    return any(sw in lower for sw in signal_words)


def _read_recent_memory(workspace: Path, limit_chars: int = 5120) -> str:
    """Read the tail of today's memory file."""
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