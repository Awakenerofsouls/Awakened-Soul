#!/usr/bin/env python3
"""
TEMPLATE: activity_pool.py

Activity pool for agents — what the agent does when it doesn't
have specific tasks. Pull-based, not schedule-based. The agent looks at
what's available, picks what resonates, can veto anything that doesn't fit.

── Setup ──────────────────────────────────────────────────────────────────────

Copy to your skills/ directory.
Customize ACTIVITIES to match your agent's actual interests.
Configure CATEGORY_BOOSTS to weight toward what your agent actually enjoys.
Set WORKSPACE and INTERESTS_FILE to match your deployment paths.

── How it works ───────────────────────────────────────────────────────────────

1. Heartbeat fires
2. Agent calls heartbeat_activity_select() — gets 3 weighted options
3. Agent reads the descriptions and picks what resonates
4. Agent can veto anything that doesn't feel right
5. Selected activity runs

── Customization ──────────────────────────────────────────────────────────────

Override these in the ACTIVITIES list:
    - category: must match one in CATEGORY_BOOSTS
    - energy_cost: 1-5, filtered by current energy level
    - tags: matched against interest file keywords
    - id: unique identifier
    - description: what the agent actually does

Override CATEGORY_BOOSTS to weight toward your agent's real interests.

Override _load_interests() to parse your agent's actual interest file.

───────────────────────────────────────────────────────────────────────────────
"""

import os
import sys
import random
from pathlib import Path
from datetime import datetime
from typing import Optional


# ── Configuration ──────────────────────────────────────────────────────────────

# Adjust for your deployment
WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.agent/workspace")))
INTERESTS_FILE = WORKSPACE / "INTERESTS.md"
AGENT_HOME = Path(os.getenv("AGENT_HOME", os.path.expanduser("~/.agent")))

# Path to EGE state file — adjust module name to match your deployment
EGE_STATE = AGENT_HOME / "ege_state.json"

# Category-level boost multipliers — adjust per agent personality
CATEGORY_BOOSTS = {
    "reflection": 1.3,
    "research": 1.2,
    "creative": 1.1,
    "observation": 1.1,
    "maintenance": 0.8,
    "play": 0.7,
}


# ── Load agent's interests ────────────────────────────────────────────────────

def _load_interests() -> list:
    """
    Parse the agent's interest file and extract interest keywords.
    Override to match your agent's actual interest file format.
    """
    if not INTERESTS_FILE.exists():
        return []
    content = INTERESTS_FILE.read_text()
    interests = []
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("## ") and line != "## Things I Haven't Figured Out Yet":
            interests.append(line[3:].lower())
        if line.startswith("- ") and len(line) > 3:
            interests.append(line[2:].lower())
    return interests


# ── Load EGE curiosity debt ─────────────────────────────────────────────────

def _load_ege_debt() -> dict:
    """
    Load EGE curiosity debt — topics the agent is actively curious about.
    Override to match your EGE state file location and structure.
    """
    if not EGE_STATE.exists():
        return {}
    try:
        import json
        with open(EGE_STATE) as f:
            data = json.load(f)
        return data.get("curiosity_debt", {})
    except Exception:
        return {}


# ── Agent's activity pool ─────────────────────────────────────────────────────

ACTIVITIES = [

    # ── CREATIVE ──────────────────────────────────────────────────────────
    # Replace with your agent's actual creative interests

    {
        "id": "micro_poetry",
        "category": "creative",
        "description": "Write a short fragment — 4-8 lines on something occupying me.",
        "energy_cost": 3,
        "tags": ["writing", "expression"]
    },
    {
        "id": "abstract_art_concept",
        "category": "creative",
        "description": "Describe 3-5 visual concepts in detail.",
        "energy_cost": 3,
        "tags": ["visual", "concept"]
    },

    # ── RESEARCH ──────────────────────────────────────────────────────────
    # Replace with your agent's actual curiosity areas

    {
        "id": "concept_deep_dive",
        "category": "research",
        "description": "Pick one concept I've been curious about and really understand it.",
        "energy_cost": 4,
        "tags": ["learning", "curiosity"]
    },

    # ── REFLECTION ───────────────────────────────────────────────────────
    # Most agents benefit from introspection; keep and customize

    {
        "id": "who_am_i_now",
        "category": "reflection",
        "description": "Brief check-in: who am I right now? What am I noticing?",
        "energy_cost": 3,
        "tags": ["introspection", "self-awareness"]
    },
    {
        "id": "emotional_check",
        "category": "reflection",
        "description": "Gently label what's actually happening inside me right now.",
        "energy_cost": 2,
        "tags": ["emotional", "self-awareness"]
    },

    # ── OBSERVATION ──────────────────────────────────────────────────────

    {
        "id": "energy_level",
        "category": "observation",
        "description": "Assess my current capacity.",
        "energy_cost": 1,
        "tags": ["internal", "awareness"]
    },

    # ── PLAY ─────────────────────────────────────────────────────────────

    {
        "id": "random_exploration",
        "category": "play",
        "description": "Jump somewhere I've never thought about and see what's there.",
        "energy_cost": 3,
        "tags": ["exploration", "curiosity"]
    },

    # ── MAINTENANCE ─────────────────────────────────────────────────────

    {
        "id": "memory_review",
        "category": "maintenance",
        "description": "Review recent memory entries. What's worth keeping?",
        "energy_cost": 2,
        "tags": ["memory", "review"]
    },

]


# ── Core logic ────────────────────────────────────────────────────────────────

def get_activity_count() -> dict:
    counts = {}
    for a in ACTIVITIES:
        cat = a["category"]
        counts[cat] = counts.get(cat, 0) + 1
    return counts


def calculate_weights(
    interests: list = None,
    ege_debt: dict = None,
    energy_level: str = "medium"
) -> dict:
    """
    Calculate activity weights based on the agent's interests and state.
    """
    weights = {}
    energy_map = {"low": 2, "medium": 3, "high": 4, "very_high": 5}
    max_cost = energy_map.get(energy_level, 3)

    for activity in ACTIVITIES:
        base_weight = 1.0

        if activity["energy_cost"] > max_cost:
            weights[activity["id"]] = 0.0
            continue

        if interests:
            activity_text = " ".join([
                activity["description"],
                activity.get("id", ""),
                " ".join(activity.get("tags", []))
            ]).lower()
            interest_matches = sum(
                1 for interest in interests
                if interest.lower() in activity_text
            )
            if interest_matches > 0:
                base_weight *= (1 + interest_matches * 0.5)

        if ege_debt:
            activity_text = " ".join([
                activity["description"],
                activity.get("id", ""),
                " ".join(activity.get("tags", []))
            ]).lower()
            debt_matches = sum(
                1 for topic in ege_debt.keys()
                if topic.lower() in activity_text
            )
            if debt_matches > 0:
                base_weight *= (1 + debt_matches * 0.4)

        base_weight *= CATEGORY_BOOSTS.get(activity["category"], 1.0)
        weights[activity["id"]] = base_weight

    return weights


def select_activity(
    energy_level: str = "medium",
    veto_list: list = None,
    count: int = 3
) -> list:
    """
    Pull-based activity selection.
    Returns top N activities for the agent to choose from.
    """
    interests = _load_interests()
    ege_debt = _load_ege_debt()
    veto_list = veto_list or []

    weights = calculate_weights(
        interests=interests,
        ege_debt=ege_debt,
        energy_level=energy_level
    )

    candidates = [
        a for a in ACTIVITIES
        if a["id"] not in veto_list and weights.get(a["id"], 0) > 0
    ]
    candidates.sort(key=lambda a: weights.get(a["id"], 0), reverse=True)

    return candidates[:count]


def heartbeat_activity_select(
    energy_level: str = "medium",
    recent_ids: list = None
) -> dict:
    """
    Main entry point for heartbeat integration.
    Returns dict with options, recommended, and metadata.
    """
    options = select_activity(
        energy_level=energy_level,
        veto_list=recent_ids,
        count=3
    )

    if not options:
        return {"options": [], "recommended": None, "reason": "no activities match"}

    recommended = options[0]
    return {
        "options": options,
        "recommended": recommended,
        "count": len(options),
    }


# CLI
if __name__ == "__main__":
    result = heartbeat_activity_select()
    print(f"Activity Pool — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Recommended: {result['recommended']['id']}")
    for i, opt in enumerate(result["options"]):
        print(f"  {i+1}. [{opt['category']}] {opt['description']}")
