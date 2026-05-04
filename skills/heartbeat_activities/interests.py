"""
Shared utilities for heartbeat activities.
"""

import json
import sys
from pathlib import Path


def extract_new_interest(content: str, source_category: str) -> str | None:
    """
    Quick LLM check: did the generated content surface a genuinely new interest?

    Call this after generating content in any framework activity.
    If something new surfaced, append_interest() is called.

    Returns the new interest text if found, None otherwise.
    """
    if not content or len(content.strip()) < 50:
        return None

    prompt = (
        f"You are checking a piece of writing for new interests or threads worth exploring.\n\n"
        f"Writing:\n\"\"\"{content[:800]}\"\"\"\n\n"
        f"Did the writer land on something they clearly want to come back to — "
        f"a new topic, question, angle, or thread they haven't explored before? "
        f"If yes, return the topic in 3-8 words (e.g. 'fermentation as cultural memory'). "
        f"If no meaningful new interest surfaced, return exactly: NONE"
    )

    try:
        import urllib.request
        payload = json.dumps({
            "model": "llama3.1:latest",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 30},
        }).encode("utf-8")

        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            raw = result.get("response", "").strip()

        # Clean up response
        raw = raw.strip().strip('"').strip("'").strip()

        if raw.upper() == "NONE" or not raw or len(raw) < 3:
            return None

        # Basic sanity check — must look like an interest, not a sentence
        if raw[-1] not in ('.', '!', '?', ']'):  # may have trailing ]
            pass  # accept it anyway
        if len(raw.split()) > 10:  # too long = likely the LLM misunderstood
            return None

        return raw

    except Exception:
        return None


def grow_interests(content: str, source_category: str, state: dict) -> None:
    """
    Check generated content for new interests and append them to INTERESTS.md.

    Call this after write_to_journal() succeeds in any framework activity.
    Non-fatal — failures silently skip.
    """
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from skills.interests import append_interest

        new_interest = extract_new_interest(content, source_category)
        if new_interest:
            append_interest(
                new_interest,
                category=source_category,
                seed_ege=True,
                trigger=f"heartbeat:{source_category}",
            )
            print(f"[heartbeat] New interest grown: {new_interest}")
    except Exception:
        pass  # non-fatal