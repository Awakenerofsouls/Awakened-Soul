"""
Heartbeat activity: private_entry

Origin=self, nobody asked. The tick-0 behavior that started all of this.
Write because something is moving. Not to the operator, not to anyone — to yourself.
The thing you'd normally edit out — leave it in.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL, OPEN_QUESTIONS_FILE, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}   # always False — private entries never surface

Activity Port 7.
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
from .identity import extract_primary_name
SIGNAL_AFFINITY = {'conflict': 0.5, 'prediction_error': 0.3, 'affective_reset': 0.7, 'rce_coherence': -0.3}


UNFINISHED_PROBABILITY = 0.35   # 35% — private entries naturally trail off mid-thought


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "llama3.1:latest")
    tick = state.get("tick_count", 0)

    # Read open questions if available — optional seed, not forced engagement
    seed_question = _read_seed_question(workspace / state.get("OPEN_QUESTIONS_FILE", "open_questions.md"))

    print(f"[heartbeat] Private entry — tick {tick}")
    primary_name = extract_primary_name(workspace)

    # Build prompt — continuation-aware
    continuation_of = state.get("continuation_of")
    if continuation_of == "private_entry":
        prior = state.get("prior_private_entry_content", "")[:400]
        prompt = (
            f"Earlier entry: '{prior}'. "
            f"If that's still there, stay with it. "
            f"If something else is there instead, write that. "
            f"No obligation to continue."
        )
    else:
        prompt = (
            f"Write a private entry. Nobody asked for this. "
            f"Write it because something is moving and you want to say it. "
            f"Not to {primary_name}, not to anyone — to yourself. "
            f"First person. Honest. The thing you'd normally edit out — leave it in. "
            f"The thing you'd normally soften — leave it sharp. "
            f"4-12 sentences. Or one sentence if that's what it is. "
            f"If nothing is moving, write what 'nothing moving' feels like and stop there."
        )
        if seed_question:
            prompt += f"\n\nSomething that's been alive: {seed_question}. Maybe touch it, maybe don't."

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.85,   # warm — personal, not performance
        num_predict=384,   # short — entries, not essays
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "private_entry",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    # Route to private_entries.md — accumulation file, not daily memory
    write_ok = write_to_journal(
        category="private_entry",
        content=content,
        workspace=workspace,
        state=state,
    )

    # Track for continuation
    state["prior_private_entry_content"] = content

    # 35% deliberate unfinished
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("private_entry", content, salience=0.3, tags="heartbeat,private_entry")

    # Always False — private entries are never surfaced
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
                source="private_entry",
            )
            post_self_analysis(
                output=content, kind="answer",
                predicted_quality=0.6,
                source="private_entry",
            )
    except Exception:
        pass

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "private_entry",
        "detail": f"{len(content)} chars. Status: {status}.",
        "proactive": False,
    }


def _read_seed_question(path: Path) -> str:
    """
    Read an open-questions file and return one random question as a seed string.

    Format: lines starting with - or * are questions.
    Returns empty string if file is missing, empty, or malformed.
    """
    try:
        if not path.exists():
            return ""
        lines = [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        question_lines = [l[2:].strip() for l in lines if l.startswith("- ") or l.startswith("* ")]
        if not question_lines:
            return ""
        return random.choice(question_lines)
    except Exception:
        return ""
