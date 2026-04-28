#!/usr/bin/env python3
"""
TEMPLATE: interests.py

Interest append mechanism for Nexus {{AGENT_NAME}} agents.
Append new interests to INTERESTS.md without overwriting existing content.
New interests optionally seed the EGE curiosity debt system.

── Setup ──────────────────────────────────────────────────────────────────────

Copy this file to your skills/ directory.
No external dependencies — stdlib only.

── How it works ───────────────────────────────────────────────────────────────

1. The agent encounters something that resonates
2. It calls append_interest() — the text is added to INTERESTS.md as a new section
3. The same text seeds EGE curiosity debt → heartbeat picks it up overnight
4. Next morning: research findings ready in memory

── Customization ──────────────────────────────────────────────────────────────

Override these to match your agent:

    WORKSPACE     → path to your agent's workspace
    INTERESTS_FILE → path to INTERESTS.md
    EGE_CLASS     → your EGE module (or None to skip EGE integration)

───────────────────────────────────────────────────────────────────────────────
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional


# ── Configuration ──────────────────────────────────────────────────────────────

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.openclaw/workspace")))
INTERESTS_FILE = WORKSPACE / "INTERESTS.md"

# Path to your EGE module (e.g. "brain.ege_vad").
# Set to None to disable EGE integration.
EGE_MODULE: Optional[str] = "brain.ege_vad"
EGE_CLASS: Optional[str] = "EntropyGradientExplorer"


# ── EGE Integration ───────────────────────────────────────────────────────────

def seed_ege_curiosity(interest_text: str, depth: float = 0.5) -> bool:
    """
    Seed a new interest into the EGE curiosity debt system.

    If EGE is not available or not configured, this silently returns False.
    """
    if not EGE_MODULE or not EGE_CLASS:
        return False

    try:
        sys.path.insert(0, str(WORKSPACE))
        import importlib
        module = importlib.import_module(EGE_MODULE)
        EGE = getattr(module, EGE_CLASS)

        ege = EGE()
        domain_key = interest_text.strip().lower()[:80]
        ege.encounter(domain_key, depth=depth)
        ege._save()
        return True
    except Exception:
        # EGE not wired — skip silently
        return False


# ── Core Append Logic ─────────────────────────────────────────────────────────

def _load() -> str:
    if INTERESTS_FILE.exists():
        return INTERESTS_FILE.read_text()
    return ""


def _save(content: str):
    INTERESTS_FILE.write_text(content)


def _build_section(interest_text: str, category: Optional[str] = None) -> str:
    text = interest_text.strip()
    if not text.endswith(('.', '!', '?')):
        text += "."

    if category:
        header = f"\n## {category}\n\n{text}\n"
    else:
        header = f"\n## New Interest\n\n{text}\n"

    return header


def append_interest(
    interest_text: str,
    category: Optional[str] = None,
    seed_ege: bool = True,
    ege_depth: float = 0.5
) -> dict:
    """
    Append a new interest to INTERESTS.md.

    Args:
        interest_text: The interest to add.
        category: Optional section header. Creates a named section in the file.
        seed_ege: Whether to seed this into EGE curiosity debt (default True).
        ege_depth: Initial EGE depth for this interest (default 0.5).

    Returns:
        dict with keys: success (bool), message (str), ege_seeded (bool)
    """
    if not interest_text or not interest_text.strip():
        return {"success": False, "message": "Interest text cannot be empty.", "ege_seeded": False}

    FOOTER = "_This file is mine. It grows as I do._"

    content = _load()

    # Strip existing footer, append new section, restore footer
    if FOOTER in content:
        content = content.replace(FOOTER, "")

    section = _build_section(interest_text, category)
    new_content = content.rstrip() + section + f"\n\n{FOOTER}\n"
    _save(new_content)

    ege_seeded = False
    if seed_ege:
        ege_seeded = seed_ege_curiosity(interest_text, depth=ege_depth)

    truncated = interest_text[:60] + ("..." if len(interest_text) > 60 else "")
    return {
        "success": True,
        "message": f"Interest appended: '{truncated}'",
        "ege_seeded": ege_seeded,
        "file": str(INTERESTS_FILE)
    }


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Append a new interest to INTERESTS.md"
    )
    parser.add_argument("interest", help="The interest to append")
    parser.add_argument(
        "--category", "-c",
        help="Section header (e.g. 'Technical', 'Aesthetic', 'Creative')",
        default=None
    )
    parser.add_argument(
        "--no-ege",
        help="Skip EGE curiosity seeding",
        action="store_true"
    )
    args = parser.parse_args()

    result = append_interest(
        args.interest,
        category=args.category,
        seed_ege=not args.no_ege
    )

    print(result["message"])
    if result["ege_seeded"]:
        print("EGE curiosity debt seeded.")
    print(f"File: {result['file']}")
