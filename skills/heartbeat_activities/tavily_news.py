"""
Heartbeat activity: tavily_news

Search Tavily for recent news on a tracked interest.
Surface scan — what's happened in the last 7 days on this topic.
Lightweight, faster than tavily_search (fewer results, shorter snippet).

Activity contract:
  Input:  state dict (WORKSPACE, INTERESTS_FILE, LLM_ENDPOINT, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "proactive": bool, "detail": str}
"""

import json
import urllib.request
import random
from pathlib import Path

from .keys import get_api_key
from .journal import write_to_journal
from .log import log_activity
from .interest_writer import try_append_new_interest
SIGNAL_AFFINITY = {'prediction_error': 0.3, 'affective_reset': -0.3}


CATEGORY = "tavily_news"
UNFINISHED_RATE = 0.10


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.openclaw/workspace"))
    interests_file = state.get("INTERESTS_FILE", "INTERESTS.md")
    interests_path = workspace / interests_file
    tick = state.get("tick_count", 0)

    api_key = get_api_key("tavily")
    if not api_key:
        return _skip("no tavily key")

    if not interests_path.exists():
        return _skip("INTERESTS.md not found")

    interests = _parse_interests(interests_path)
    if not interests:
        return _skip("no interests")

    # Round-robbin over recent interests — bias toward things searched in last 7 days
    last_searched = state.get("_tavily_last_news", {})
    def recency(i):
        return tick - last_searched.get(i["topic"], tick - 1000)  # default 1000 ticks old

    chosen = sorted(interests, key=recency)[0]
    topic = chosen["topic"]

    print(f"[heartbeat] tavily_news: {topic}")

    try:
        results = _call_tavily_news(api_key, topic, max_results=5)
    except Exception as e:
        log_activity("tavily_news", f"API failed: {e}", salience=0.3, tags="error")
        return _skip(f"tavily error: {e}")

    hits = results.get("results", [])
    if not hits:
        return _skip(f"no recent news for '{topic}'")

    content = _format_news(topic, results, days=7)

    write_to_journal(category="tavily_news", content=content,
                     workspace=workspace, state=state)

    try_append_new_interest(content, state, source_activity="tavily_news")

    state.setdefault("_tavily_last_news", {})[topic] = tick

    status = "unfinished" if random.random() < UNFINISHED_RATE else "complete"
    return {
        "ok": True,
        "status": status,
        "content": content,
        "category": CATEGORY,
        "proactive": random.random() < 0.10,
        "detail": f"News on: {topic}. {len(hits)} items.",
    }


def _call_tavily_news(api_key: str, query: str, max_results: int = 5) -> dict:
    payload = json.dumps({
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "topic": "news",
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


def _format_news(topic: str, results: dict, days: int) -> str:
    lines = [f"Recent news on: {topic} (last {days} days)", ""]
    for i, r in enumerate(results.get("results", []), 1):
        title = (r.get("title") or "").strip()
        url = (r.get("url") or "").strip()
        snippet = (r.get("content") or "").strip()[:200]
        published = r.get("published_date", "")
        lines.append(f"{i}. **{title}** {published}")
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


def _skip(detail: str) -> dict:
    return {"ok": False, "status": "complete", "content": "",
            "category": CATEGORY, "proactive": False, "detail": detail}