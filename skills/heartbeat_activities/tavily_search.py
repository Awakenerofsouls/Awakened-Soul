"""
Heartbeat activity: tavily_search

Real web search via Tavily API. Picks a tracked interest, searches for
current information, writes findings to journal with source URLs.

Does NOT use the LLM for the search itself — talks directly to Tavily.
Uses interest_writer hook to grow INTERESTS.md if new topics surface.

Activity contract:
  Input:  state dict (WORKSPACE, INTERESTS_FILE, LLM_ENDPOINT, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "proactive": bool, "detail": str}
"""

import json
import urllib.request
import urllib.error
import random
from pathlib import Path
from typing import Optional

from .keys import get_api_key, KeyMissing
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
from .interest_writer import try_append_new_interest
SIGNAL_AFFINITY = {'prediction_error': 0.5, 'affective_reset': -0.3}


CATEGORY = "tavily_search"
UNFINISHED_RATE = 0.20


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    interests_file = state.get("INTERESTS_FILE", "INTERESTS.md")
    interests_path = workspace / interests_file
    tick = state.get("tick_count", 0)

    # Check for Tavily key
    api_key = get_api_key("tavily")
    if not api_key:
        return _skip("no tavily key in keys.json")

    if not interests_path.exists():
        return _skip("INTERESTS.md not found")

    interests = _parse_interests(interests_path)
    if not interests:
        return _skip("no interests to search")

    # Pick least-recently-searched topic
    last_searched = state.get("_tavily_last_searched", {})
    def debt(i):
        return tick - last_searched.get(i["topic"], 0)
    chosen = sorted(interests, key=debt, reverse=True)[0]
    topic = chosen["topic"]

    print(f"[heartbeat] tavily_search: {topic}")

    # Real API call
    try:
        results = _call_tavily(api_key, topic, max_results=5)
    except Exception as e:
        log_activity("tavily_search", f"API call failed: {e}", salience=0.3, tags="error")
        return _skip(f"tavily api error: {e}")

    hits = results.get("results", [])
    if not hits:
        return _skip(f"no results for '{topic}'")

    # Build journal entry
    content = _format_findings(topic, results)

    write_ok = write_to_journal(
        category="tavily_search",
        content=content,
        workspace=workspace,
        state=state,
    )

    # Grow interests from search results
    try_append_new_interest(content, state, source_activity="tavily_search")

    # Update last-searched tracker
    state.setdefault("_tavily_last_searched", {})[topic] = tick

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
                source="tavily_search",
            )
        if content:
            post_memory_encode(
                content=content, intent="observation",
                source_kind="external" if backend != "llm-only" else "inference",
                content_confidence=0.7, source_confidence=0.75,
                source="tavily_search",
            )
    except Exception:
        pass

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": CATEGORY,
        "proactive": random.random() < 0.10,
        "detail": f"Topic: {topic}. {len(hits)} results, {len(content)} chars.",
    }


def _call_tavily(api_key: str, query: str, max_results: int = 5) -> dict:
    """POST to Tavily /search. Returns parsed JSON."""
    payload = json.dumps({
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "include_answer": True,
        "include_raw_content": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _format_findings(topic: str, results: dict) -> str:
    lines = [f"Searched: {topic}", ""]
    if results.get("answer"):
        lines.append(f"Summary: {results['answer']}")
        lines.append("")
    for i, r in enumerate(results.get("results", []), 1):
        title = (r.get("title") or "").strip()
        url = (r.get("url") or "").strip()
        snippet = (r.get("content") or "").strip()[:300]
        lines.append(f"{i}. **{title}**")
        lines.append(f"   {url}")
        if snippet:
            lines.append(f"   {snippet}")
        lines.append("")
    return "\n".join(lines)


def _parse_interests(path: Path) -> list[dict]:
    """Parse INTERESTS.md into list of dicts. Same parser as research.py."""
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
    return {
        "ok": False,
        "status": "complete",
        "content": "",
        "category": CATEGORY,
        "proactive": False,
        "detail": detail,
    }