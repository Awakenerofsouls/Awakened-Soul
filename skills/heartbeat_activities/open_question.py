"""
Heartbeat activity: open_question

Hold a question open without answering it.
The anti-research activity — research pursues closure,
open_question refuses it.

Activity contract:
  Input:  state dict (WORKSPACE, OPEN_QUESTIONS_FILE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Batch B, Activity 7. Reads open_questions.md if present, else returns
ok:False cleanly. Does NOT read INTERESTS.md.
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
SIGNAL_AFFINITY = {'conflict': 0.3, 'prediction_error': 0.5, 'affective_reset': 0.3, 'rce_coherence': -0.3}


UNFINISHED_PROBABILITY = 0.45


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    questions_file = workspace / state.get("OPEN_QUESTIONS_FILE", "open_questions.md")
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "qwen2.5vl:7b")
    tick = state.get("tick_count", 0)

    # Read questions from open_questions.md if present
    question = _pick_question(questions_file)
    if not question:
        return {
            "ok": False,
            "status": "complete",
            "category": "open_question",
            "content": "",
            "detail": "No open_questions.md found",
            "proactive": False,
        }

    print(f"[heartbeat] Open question: {question[:50]}")

    continuation_of = state.get("continuation_of")
    if continuation_of == "open_question":
        prior = state.get("prior_open_question_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"Is the question still the same? Has it changed shape?"
        )
    else:
        prompt = (
            f"Hold this question open: '{question}'. "
            f"Don't answer it. Don't try to resolve it. "
            f"Describe what it's like to sit with it unanswered right now. "
            f"What does the question ask of you that you can't deliver. "
            f"Where does it touch — is it intellectual, emotional, structural. "
            f"4-8 sentences. If the question wants to become statement, "
            f"resist that — keep it a question."
        )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.8,
        num_predict=384,
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "open_question",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="open_question",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_open_question_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("open_question", content, salience=0.4, tags="heartbeat,question")

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
                source="open_question",
            )
            post_self_analysis(
                output=content, kind="answer",
                predicted_quality=0.6,
                source="open_question",
            )
    except Exception:
        pass

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "open_question",
        "detail": f"Question: {question[:40]}. {len(content)} chars.",
        "proactive": False,
    }


def _pick_question(path: Path) -> str:
    """
    Parse open_questions.md and return a random question.

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
