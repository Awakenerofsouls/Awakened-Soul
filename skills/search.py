#!/usr/bin/env python3
"""
skills/search.py — the agent's web search tool via SearXNG.
"""
import os
from typing import List, Dict

import requests

SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://127.0.0.1:8080/search")
TIMEOUT = 15


def search(query: str, n: int = 5) -> List[Dict]:
    """
    Search the web via SearXNG.
    Returns list of result dicts: {title, url, content, engine}.
    """
    params = {"q": query, "format": "json"}
    try:
        r = requests.get(SEARXNG_URL, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        results = data.get("results", [])[:n]
        return [
            {
                "title": x.get("title", ""),
                "url": x.get("url", ""),
                "content": x.get("content", "")[:300],
                "engine": x.get("engine", ""),
            }
            for x in results
        ]
    except Exception as e:
        return [{"error": str(e)}]


if __name__ == "__main__":
    import sys, json
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "test"
    print(json.dumps(search(q), indent=2))
