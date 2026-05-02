"""
Heartbeat activity: tavily_answer

Use Tavily's Q&A mode to get a direct answer to a specific question.
Picks a question from drift_identity_questions.json (or INTERESTS.md as fallback)
and asks Tavily to answer it.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "proactive": bool, "detail": str}
"""

import json
import urllib.request
import random
from pathlib import Path
from typing import Optional

from .keys import get_api_key
from .journal import write_to_journal
from .log import log_activity
from .interest_writer import try_append_new_interest
SIGNAL_AFFINITY = {'prediction_error': 0.5}


CATEGORY = "tavily_answer"
UNFINISHED_RATE = 0.15


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    tick = state.get("tick_count", 0)

    api_key = get_api_key("tavily")
    if not api_key:
        return _skip("no tavily key")

    # Pick a question to ask
    question = _pick_question(workspace, state)
    if not question:
        return _skip("no questions available")

    print(f"[heartbeat] tavily_answer: {question[:80]}")

    try:
        results = _call_tavily_answer(api_key, question)
    except Exception as e:
        log_activity("tavily_answer", f"API failed: {e}", salience=0.3, tags="error")
        return _skip(f"tavily error: {e}")

    # Format the answer
    content = _format_answer(question, results)

    write_to_journal(category="tavily_answer", content=content,
                    workspace=workspace, state=state)

    try_append_new_interest(content, state, source_activity="tavily_answer")

    status = "unfinished" if random.random() < UNFINISHED_RATE else "complete"
    # ── Brain-event posting ─────────────────────────────────────────
    # External fetch — outward_reach for the network call,
    # memory_encode for the finding (source=external).
    try:
        from ._brain_post import post_outward_reach_call, post_memory_encode
        backend = locals().get("backend") or (
            (locals().get("web") or {}).get("backend") if isinstance(locals().get("web"), dict) else None
        ) or "external"
        if backend and backend != "llm-only":
            post_outward_reach_call(
                provider=backend, intent="research",
                success=True,
                source="tavily_answer",
            )
        if content:
            post_memory_encode(
                content=content, intent="observation",
                source_kind="external" if backend != "llm-only" else "inference",
                content_confidence=0.7, source_confidence=0.75,
                source="tavily_answer",
            )
    except Exception:
        pass

    return {
        "ok": True,
        "status": status,
        "content": content,
        "category": CATEGORY,
        "proactive": random.random() < 0.08,
        "detail": f"Q: {question[:60]}",
    }


def _pick_question(workspace: Path, state: dict) -> Optional[str]:
    """Pick a question from drift_identity_questions.json or INTERESTS.md."""
    diqe_path = workspace / "drift_identity_questions.json"
    if diqe_path.exists():
        try:
            data = json.loads(diqe_path.read_text())
            # Track which questions have been answered recently
            last_answered = state.get("_tavily_answer_last", {})
            # Prefer questions not recently answered
            questions = []
            if isinstance(data, list):
                questions = data
            elif isinstance(data, dict):
                questions = data.get("questions", data.get("open", []))
            if questions:
                def debt(q):
                    q_text = q if isinstance(q, str) else q.get("question", "")
                    return state.get("tick_count", 0) - last_answered.get(q_text, 0)
                chosen = sorted(questions, key=debt, reverse=True)[0]
                q_text = chosen if isinstance(chosen, str) else chosen.get("question", "")
                return q_text
        except Exception:
            pass

    # Fallback: pick from INTERESTS.md
    interests_path = workspace / "INTERESTS.md"
    if interests_path.exists():
        interests = _parse_interests(interests_path)
        if interests:
            return random.choice(interests)["topic"]
    return None


def _call_tavily_answer(api_key: str, question: str) -> dict:
    payload = json.dumps({
        "api_key": api_key,
        "query": question,
        "max_results": 3,
        "include_answer": True,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _format_answer(question: str, results: dict) -> str:
    lines = [f"Question: {question}", ""]
    if results.get("answer"):
        lines.append(f"Answer: {results['answer']}")
        lines.append("")
    lines.append("Sources:")
    for r in results.get("results", [])[:3]:
        title = (r.get("title") or "").strip()
        url = (r.get("url") or "").strip()
        lines.append(f" - {title}: {url}")
    return "\n".join(lines)


def _parse_interests(path: Path) -> list[dict]:
    interests = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        topic = line.lstrip("-* ").split(" #")[0].strip()
        if topic:
            interests.append({"topic": topic})
    return interests


def _skip(detail: str) -> dict:
    return {"ok": False, "status": "complete", "content": "",
            "category": CATEGORY, "proactive": False, "detail": detail}