"""
Heartbeat activity helper: shared web-fetch substrate.

Used by research.py / news.py / study.py so that autonomous activities
ACTUALLY look things up instead of pulling answers out of the LLM.

Contract:
    web_lookup(topic, intent="research", max_results=5, max_age_days=None)
        -> {
             "ok": bool,
             "backend": "tavily" | "searxng" | None,
             "hits": [{title, url, snippet, source_confidence}],
             "summary_text": str,         # short text to pass into the LLM
             "source_confidence": float,  # for MemoryIntegrityLayer encode
             "reason": str,               # populated when ok=False
           }

Backends:
    1. Tavily — preferred. Requires `tavily` key in keys.json.
    2. SearXNG — fallback. Reads SEARXNG_URL env (default 127.0.0.1:8080).
    3. None — neither reachable; caller falls back to LLM-only with
       source="inference" and reduced source_confidence.

This helper deliberately stays small. Rate-limiting, intent tagging, and
record-keeping are the caller's responsibility (the activity hook calls
OutwardReachLayer.record_call, MemoryIntegrityLayer.record_encode, etc.).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from .keys import get_api_key

TAVILY_ENDPOINT = "https://api.tavily.com/search"
SEARXNG_URL_ENV = "SEARXNG_URL"
DEFAULT_SEARXNG = "http://127.0.0.1:8080/search"

# Source-confidence per backend / result rank. Web hits never go above 0.85
# — the SKILL.md invariant for web-research.
TAVILY_ANSWER_SOURCE_CONFIDENCE = 0.85
TAVILY_HIT_SOURCE_CONFIDENCE = 0.70
SEARXNG_HIT_SOURCE_CONFIDENCE = 0.60
LOW_RANK_PENALTY = 0.05  # subtract per rank past first three


def web_lookup(
    topic: str,
    intent: str = "research",
    max_results: int = 5,
    max_age_days: Optional[int] = None,
    timeout: int = 20,
) -> Dict[str, Any]:
    """Try Tavily, then SearXNG. Return a normalized hit bundle."""
    if not topic or not topic.strip():
        return _empty("no topic given")

    # 1. Tavily
    tavily_key = get_api_key("tavily")
    if tavily_key:
        try:
            return _tavily(topic, intent, tavily_key, max_results, max_age_days, timeout)
        except Exception as e:
            # Fall through to SearXNG
            tavily_error = str(e)[:120]
        else:
            tavily_error = ""
    else:
        tavily_error = "no tavily key"

    # 2. SearXNG
    searxng_url = os.environ.get(SEARXNG_URL_ENV, DEFAULT_SEARXNG)
    try:
        return _searxng(topic, searxng_url, max_results, timeout)
    except Exception as e:
        return _empty(
            f"all backends failed (tavily: {tavily_error}; "
            f"searxng: {str(e)[:120]})"
        )


# ── Tavily ──────────────────────────────────────────────────────────────────


def _tavily(
    topic: str,
    intent: str,
    api_key: str,
    max_results: int,
    max_age_days: Optional[int],
    timeout: int,
) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "api_key": api_key,
        "query": topic,
        "max_results": max(1, min(10, int(max_results))),
        "include_answer": True,
        "include_raw_content": False,
    }
    # Recency hint for news intent.
    if intent == "news" or max_age_days is not None:
        days = max_age_days if max_age_days is not None else 7
        body["topic"] = "news"
        body["days"] = max(1, min(90, int(days)))

    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        TAVILY_ENDPOINT,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    raw_hits = data.get("results") or []
    answer = (data.get("answer") or "").strip()

    hits: List[Dict[str, Any]] = []
    for i, r in enumerate(raw_hits):
        url = (r.get("url") or "").strip()
        title = (r.get("title") or "").strip()
        snippet = (r.get("content") or "").strip()
        if not url:
            continue
        sc = TAVILY_HIT_SOURCE_CONFIDENCE - LOW_RANK_PENALTY * max(0, i - 2)
        sc = max(0.4, sc)
        hits.append({
            "title": title,
            "url": url,
            "snippet": snippet[:400],
            "source_confidence": round(sc, 3),
            "rank": i + 1,
        })

    if not hits and not answer:
        return _empty("tavily: no results")

    summary_text = _format_summary(topic, answer, hits)
    bundle_sc = (
        TAVILY_ANSWER_SOURCE_CONFIDENCE
        if answer
        else (hits[0]["source_confidence"] if hits else 0.5)
    )

    return {
        "ok": True,
        "backend": "tavily",
        "hits": hits,
        "answer": answer,
        "summary_text": summary_text,
        "source_confidence": round(bundle_sc, 3),
        "reason": "",
    }


# ── SearXNG ─────────────────────────────────────────────────────────────────


def _searxng(
    topic: str,
    url: str,
    max_results: int,
    timeout: int,
) -> Dict[str, Any]:
    params = urllib.parse.urlencode({"q": topic, "format": "json"})
    full_url = f"{url}?{params}"
    req = urllib.request.Request(full_url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    raw = (data.get("results") or [])[: max_results]
    if not raw:
        return _empty("searxng: no results")

    hits: List[Dict[str, Any]] = []
    for i, r in enumerate(raw):
        url_h = (r.get("url") or "").strip()
        if not url_h:
            continue
        sc = SEARXNG_HIT_SOURCE_CONFIDENCE - LOW_RANK_PENALTY * max(0, i - 2)
        sc = max(0.35, sc)
        hits.append({
            "title": (r.get("title") or "").strip(),
            "url": url_h,
            "snippet": (r.get("content") or "").strip()[:400],
            "source_confidence": round(sc, 3),
            "rank": i + 1,
        })

    if not hits:
        return _empty("searxng: parsed no usable hits")

    summary_text = _format_summary(topic, "", hits)
    return {
        "ok": True,
        "backend": "searxng",
        "hits": hits,
        "answer": "",
        "summary_text": summary_text,
        "source_confidence": hits[0]["source_confidence"],
        "reason": "",
    }


# ── helpers ─────────────────────────────────────────────────────────────────


def _format_summary(topic: str, answer: str, hits: List[Dict[str, Any]]) -> str:
    """Compact text representation for splicing into an LLM prompt or
    journal entry. Each hit cited with title + url so future-the-agent can
    audit provenance."""
    lines = [f"Looked up: {topic}"]
    if answer:
        lines.append("")
        lines.append(f"Answer (synthesized): {answer}")
    if hits:
        lines.append("")
        lines.append("Sources:")
        for h in hits:
            line = f"- {h['title']} — {h['url']}"
            if h.get("snippet"):
                line += f"\n    {h['snippet'][:200]}"
            lines.append(line)
    return "\n".join(lines)


def _empty(reason: str) -> Dict[str, Any]:
    return {
        "ok": False,
        "backend": None,
        "hits": [],
        "answer": "",
        "summary_text": "",
        "source_confidence": 0.0,
        "reason": reason,
    }
