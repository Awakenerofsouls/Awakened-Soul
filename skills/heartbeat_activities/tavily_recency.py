"""
Heartbeat activity: tavily_recency

Search for what's new in the last 7 days on a tracked interest.
Designed to catch recency — things published very recently that
might not show up in a normal search. Picks a topic and scans.

Activity contract:
  Input:  state dict (WORKSPACE, INTERESTS_FILE, etc.)
  Output: {"ok": bool, "status": "complete",
           "content": str, "category": str, "proactive": bool, "detail": str}
"""

import json
import urllib.request
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .keys import get_api_key
from ._interests_parser import parse_interests as _parse_interests
from .journal import write_to_journal
from .log import log_activity
from .interest_writer import try_append_new_interest
SIGNAL_AFFINITY = {'prediction_error': 0.3}


CATEGORY = "tavily_recency"
DAYS = 7


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    interests_path = workspace / state.get("INTERESTS_FILE", "INTERESTS.md")
    tick = state.get("tick_count", 0)

    api_key = get_api_key("tavily")
    if not api_key:
        return {"ok": False, "status": "complete", "content": "",
                "category": CATEGORY, "proactive": False,
                "detail": "no tavily key"}

    if not interests_path.exists():
        return {"ok": False, "status": "complete", "content": "",
                "category": CATEGORY, "proactive": False,
                "detail": "no INTERESTS.md"}

    interests = _parse_interests(interests_path)
    if not interests:
        return {"ok": False, "status": "complete", "content": "",
                "category": CATEGORY, "proactive": False,
                "detail": "no interests"}

    # Pick something not recently recency-scanned
    last_scan = state.get("_tavily_recency_last", {})
    def stale(i):
        return tick - last_scan.get(i["topic"], 0)

    topic = sorted(interests, key=stale, reverse=True)[0]["topic"]
    print(f"[heartbeat] tavily_recency: {topic}")

    try:
        results = _call_recency(api_key, topic, days=DAYS)
    except Exception as e:
        log_activity("tavily_recency", f"API failed: {e}", salience=0.3, tags="error")
        return {"ok": False, "status": "complete", "content": "",
                "category": CATEGORY, "proactive": False,
                "detail": f"tavily error: {e}"}

    hits = results.get("results", [])
    if not hits:
        return {"ok": False, "status": "complete", "content": "",
                "category": CATEGORY, "proactive": False,
                "detail": f"no recent results for {topic}"}

    content = _format_recency(topic, hits, DAYS)

    write_to_journal(category="tavily_recency", content=content,
                    workspace=workspace, state=state)

    try_append_new_interest(content, state, source_activity="tavily_recency")
    state.setdefault("_tavily_recency_last", {})[topic] = tick

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
                source="tavily_recency",
            )
        if content:
            post_memory_encode(
                content=content, intent="observation",
                source_kind="external" if backend != "llm-only" else "inference",
                content_confidence=0.7, source_confidence=0.75,
                source="tavily_recency",
            )
    except Exception:
        pass

    return {
        "ok": True,
        "status": "complete",
        "content": content,
        "category": CATEGORY,
        "proactive": random.random() < 0.12,
        "detail": f"New in {topic}: {len(hits)} items.",
    }


def _call_recency(api_key: str, query: str, days: int = 7) -> dict:
    # Tavily doesn't have a date filter in free tier — we ask for fresh results
    # and label the recency window in the query
    payload = json.dumps({
        "api_key": api_key,
        "query": f"{query} (last {days} days)",
        "max_results": 5,
        "include_answer": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _format_recency(topic: str, hits: list, days: int) -> str:
    lines = [f"New in {topic} (last {days} days):", ""]
    for i, r in enumerate(hits, 1):
        title = (r.get("title") or "").strip()
        url = (r.get("url") or "").strip()
        snippet = (r.get("content") or "").strip()[:250]
        published = r.get("published_date", "recently")
        lines.append(f"{i}. **{title}** — {published}")
        lines.append(f"   {url}")
        if snippet:
            lines.append(f"   {snippet}")
        lines.append("")
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