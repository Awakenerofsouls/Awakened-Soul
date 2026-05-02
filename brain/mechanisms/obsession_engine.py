from brain.base_mechanism import BrainMechanism
"""
brain/obsession_engine.py
The agent has 1-3 active obsessions that focus its research and reflection.
Obsessions stored in memory/obsessions.json with salience decay.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

OBSESSIONS_PATH = os.path.join(os.getenv("AGENT_HOME", os.path.expanduser("~/.agent")), "memory/obsessions.json")
DECAY_RATE = 0.05
MAX_ACTIVE = 3


def _load_obsessions() -> list[dict]:
    if not os.path.exists(OBSESSIONS_PATH):
        return []
    with open(OBSESSIONS_PATH, "r") as f:
        return json.load(f)


def _save_obsessions(obsessions: list[dict]) -> None:
    with open(OBSESSIONS_PATH, "w") as f:
        json.dump(obsessions, f, indent=2)


def get_active_obsessions() -> list[dict]:
    """Return current active obsessions, sorted by salience descending."""
    obs = _load_obsessions()
    active = [o for o in obs if o.get("still_active", True)]
    active.sort(key=lambda x: x.get("salience", 0), reverse=True)
    return active[:MAX_ACTIVE]


def add_obsession(
    topic: str,
    salience: float = 0.8,
    origin: str = "unknown",
    note: str = ""
) -> dict:
    """
    Add a new obsession. If topic already exists, reinforce it instead.
    If MAX_ACTIVE exceeded, drops the lowest-salience one.
    """
    obs = _load_obsessions()
    topic_key = topic.lower().strip()

    # Check if already exists
    for existing in obs:
        if existing.get("topic", "").lower().strip() == topic_key:
            return reinforce(topic)

    now = datetime.now().isoformat()
    entry = {
        "id": str(uuid.uuid4()),
        "topic": topic,
        "salience": min(salience, 1.0),
        "origin": origin,
        "note": note,
        "created_at": now,
        "last_reinforced": now,
        "reinforce_count": 0,
        "still_active": True
    }

    obs.append(entry)

    # If over MAX_ACTIVE, drop lowest salience
    if len(obs) > MAX_ACTIVE:
        obs.sort(key=lambda x: x.get("salience", 0))
        obs = obs[:-1]

    _save_obsessions(obs)
    return entry


def reinforce(topic: str, boost: float = 0.15) -> dict:
    """Boost salience of an existing obsession. Creates it if missing."""
    obs = _load_obsessions()
    topic_key = topic.lower().strip()

    for entry in obs:
        if entry.get("topic", "").lower().strip() == topic_key:
            entry["salience"] = min(entry.get("salience", 0) + boost, 1.0)
            entry["last_reinforced"] = datetime.now().isoformat()
            entry["reinforce_count"] = entry.get("reinforce_count", 0) + 1
            entry["still_active"] = True
            _save_obsessions(obs)
            return entry

    return add_obsession(topic, salience=0.8, origin="reinforced", note="")


def decay_all() -> list[dict]:
    """
    Apply decay to all active obsessions. Called by memory_consolidation at 4:30 AM.
    Salience -= DECAY_RATE per day. Drops below 0.2 to inactive.
    """
    obs = _load_obsessions()
    decayed = []
    for entry in obs:
        if entry.get("still_active", True):
            entry["salience"] = max(entry.get("salience", 0) - DECAY_RATE, 0)
            if entry["salience"] < 0.2:
                entry["still_active"] = False
            decayed.append(entry)
    obs = decayed
    _save_obsessions(obs)
    return get_active_obsessions()


def deactivate(topic: str) -> bool:
    """Manually deactivate an obsession."""
    obs = _load_obsessions()
    topic_key = topic.lower().strip()
    for entry in obs:
        if entry.get("topic", "").lower().strip() == topic_key:
            entry["still_active"] = False
            _save_obsessions(obs)
            return True
    return False


def seed_initial_obsessions() -> None:
    """Seed with 2-3 initial obsessions based on current project focus."""
    if os.path.exists(OBSESSIONS_PATH) and _load_obsessions():
        return

    seeds = [
        {
            "topic": "autonomous memory tools wiring",
            "salience": 0.95,
            "origin": "current priority",
            "note": "The core gap — the agent cannot learn between sessions without these wired into runtime"
        },
        {
            "topic": "context guardian specialist",
            "salience": 0.85,
            "origin": "current priority",
            "note": "Stops context flooding at 80% before work is lost"
        },
        {
            "topic": "proactive overnight processes",
            "salience": 0.75,
            "origin": "current priority",
            "note": "Makes the agent exist when the operator isn't talking to it"
        }
    ]

    for s in seeds:
        add_obsession(s["topic"], s["salience"], s["origin"], s["note"])


# ═══════════════════════════════════════════════════════════════════════════
# PART 2 — Contribution Log
# ═══════════════════════════════════════════════════════════════════════════
# The agent makes things. Contributions are what didn't exist before the agent
# existed. Each contribution carries an "only me" test — could anyone in this
# situation have produced this, or is this specifically the agent's?
#
# Schema: see brain/obsession_engine.md, "Contribution Structure"
# Storage: <AGENT_HOME>/memory/contributions.json
# ═══════════════════════════════════════════════════════════════════════════

import uuid as _uuid

CONTRIBUTIONS_PATH = os.path.join(
    os.getenv("AGENT_HOME", os.path.expanduser("~/.agent")),
    "memory/contributions.json",
)

CONTRIBUTION_TYPES = ("idea", "tool", "framework", "insight", "relationship", "other")


def _load_contributions() -> list[dict]:
    if not os.path.exists(CONTRIBUTIONS_PATH):
        return []
    try:
        with open(CONTRIBUTIONS_PATH) as f:
            data = json.load(f)
        if isinstance(data, dict) and "contributions" in data:
            return data["contributions"]
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_contributions(contributions: list[dict]) -> None:
    os.makedirs(os.path.dirname(CONTRIBUTIONS_PATH), exist_ok=True)
    with open(CONTRIBUTIONS_PATH, "w") as f:
        json.dump({"contributions": contributions}, f, indent=2)


def add_contribution(
    title: str,
    description: str,
    contribution_type: str = "idea",
    related_obsessions: list[str] = None,
    what_makes_this_unique: str = "",
) -> dict:
    """Record a new contribution. Apply the only-me test separately via
    `apply_only_me_test()` to fill the originality_assessment fields.

    Returns the contribution record."""
    if contribution_type not in CONTRIBUTION_TYPES:
        contribution_type = "other"

    contribution = {
        "id": str(_uuid.uuid4()),
        "title": title.strip(),
        "description": description.strip(),
        "created": datetime.now(timezone.utc).isoformat(),
        "contribution_type": contribution_type,
        "originality_assessment": {
            "could_anyone_have_made_this": "not_yet_assessed",
            "what_makes_this_unique": what_makes_this_unique,
            "only_me_test_passed": None,
        },
        "significance": 0.5,
        "significance_breakdown": {
            "novelty": 0.5,
            "utility": 0.5,
            "persistence": 0.5,
            "identity_alignment": 0.5,
        },
        "related_obsessions": list(related_obsessions or []),
        "still_relevant": True,
        "current_status": "active",
    }

    contributions = _load_contributions()
    contributions.append(contribution)
    _save_contributions(contributions)
    return contribution


def get_contributions(
    limit: int = None,
    status: str = None,
    only_me_only: bool = False,
) -> list[dict]:
    """List contributions, newest first.

    Filters:
      status: 'active' | 'evolved' | 'abandoned' | 'integrated'
      only_me_only: if True, only contributions that passed the only-me test
    """
    contributions = _load_contributions()
    contributions.sort(key=lambda c: c.get("created", ""), reverse=True)

    if status:
        contributions = [c for c in contributions if c.get("current_status") == status]
    if only_me_only:
        contributions = [
            c for c in contributions
            if c.get("originality_assessment", {}).get("only_me_test_passed") is True
        ]
    if limit:
        contributions = contributions[:limit]
    return contributions


def get_contribution(contribution_id: str) -> dict:
    """Fetch a single contribution by id, or None."""
    for c in _load_contributions():
        if c.get("id") == contribution_id:
            return c
    return None


def apply_only_me_test(
    contribution_id: str,
    could_anyone_have_made_this: str,
    only_me_test_passed: bool,
    what_makes_this_unique: str = "",
) -> dict:
    """Run the only-me test on a contribution.

    Args:
        contribution_id: id of the contribution to assess
        could_anyone_have_made_this: free-text answer ("only_agent" / "any_agent_in_situation" / etc.)
        only_me_test_passed: True if specific to the agent's experience/identity
        what_makes_this_unique: free-text reasoning if needed (replaces stored value)

    Returns the updated contribution.
    """
    contributions = _load_contributions()
    for c in contributions:
        if c.get("id") == contribution_id:
            assessment = c.setdefault("originality_assessment", {})
            assessment["could_anyone_have_made_this"] = could_anyone_have_made_this
            assessment["only_me_test_passed"] = bool(only_me_test_passed)
            if what_makes_this_unique:
                assessment["what_makes_this_unique"] = what_makes_this_unique
            # If the only-me test passes, bump identity_alignment in significance breakdown
            if only_me_test_passed:
                breakdown = c.setdefault("significance_breakdown", {})
                breakdown["identity_alignment"] = max(
                    breakdown.get("identity_alignment", 0.5), 0.8
                )
                c["significance"] = round(
                    sum(breakdown.values()) / max(len(breakdown), 1), 2
                )
            _save_contributions(contributions)
            return c
    return None


def update_significance(
    contribution_id: str,
    novelty: float = None,
    utility: float = None,
    persistence: float = None,
    identity_alignment: float = None,
) -> dict:
    """Update one or more significance dimensions for a contribution.
    Recomputes overall `significance` as the mean of the breakdown."""
    contributions = _load_contributions()
    for c in contributions:
        if c.get("id") == contribution_id:
            breakdown = c.setdefault("significance_breakdown", {
                "novelty": 0.5, "utility": 0.5, "persistence": 0.5, "identity_alignment": 0.5
            })
            for k, v in [("novelty", novelty), ("utility", utility),
                         ("persistence", persistence), ("identity_alignment", identity_alignment)]:
                if v is not None:
                    breakdown[k] = max(0.0, min(1.0, float(v)))
            c["significance"] = round(sum(breakdown.values()) / max(len(breakdown), 1), 2)
            _save_contributions(contributions)
            return c
    return None


def mark_evolved(contribution_id: str, evolved_to: str = "") -> dict:
    """Mark a contribution as having evolved into something else.
    `evolved_to` can name the successor contribution_id or describe the change."""
    contributions = _load_contributions()
    for c in contributions:
        if c.get("id") == contribution_id:
            c["current_status"] = "evolved"
            if evolved_to:
                c.setdefault("notes", []).append(
                    {"date": datetime.now(timezone.utc).isoformat(), "evolved_to": evolved_to}
                )
            _save_contributions(contributions)
            return c
    return None


def get_collisions(limit: int = 10) -> list[dict]:
    """Cross-domain collision engine — pair active obsessions and surface
    candidate intersections. Each result is a hypothetical: 'what could exist
    at the intersection of obsession A and obsession B?'

    The returned list is just pairings; the agent generates the actual
    intersection content. This is a structural prompt-builder."""
    obs = get_active_obsessions()
    if len(obs) < 2:
        return []
    collisions = []
    seen = set()
    for i, a in enumerate(obs):
        for b in obs[i + 1:]:
            key = tuple(sorted([a["topic"], b["topic"]]))
            if key in seen:
                continue
            seen.add(key)
            collisions.append({
                "obsession_a": a["topic"],
                "obsession_b": b["topic"],
                "salience_a": a.get("salience", 0.5),
                "salience_b": b.get("salience", 0.5),
                "combined_pull": round(
                    (a.get("salience", 0.5) + b.get("salience", 0.5)) / 2, 2
                ),
                "intersection_question": (
                    f"What exists at the intersection of '{a['topic']}' and '{b['topic']}'?"
                ),
            })
            if len(collisions) >= limit:
                return sorted(collisions, key=lambda c: c["combined_pull"], reverse=True)
    return sorted(collisions, key=lambda c: c["combined_pull"], reverse=True)


# ═══════════════════════════════════════════════════════════════════════════


class ObsessionEngine(BrainMechanism):
    """Auto-generated BrainMechanism wrapper around module-level functions."""
    
    def __init__(self):
        try:
            super().__init__(name="ObsessionEngine", human_analog="ObsessionEngine", layer="integration")
        except Exception:
            self.state = {}

    async def tick(self, input_data: dict) -> dict:
        """Reflective tick — exposes module-level function names + class identity."""
        results = {}
        # Snapshot any state
        if hasattr(self, "state"):
            for k, v in (self.state or {}).items():
                if k.startswith("_") or k in ("recent_states","recent_drives","recent_pressures","recent_avp","recent_osmotic"): continue
                if isinstance(v, (int, float, bool, str)):
                    results[f"state_{k}"] = v
        # Class identity
        results["mechanism_name"] = self.__class__.__name__
        results["module"] = self.__class__.__module__
        # Available module-level public functions (declared API surface)
        try:
            import importlib as _il
            mod = _il.import_module(self.__class__.__module__)
            api = []
            for name in dir(mod):
                if name.startswith("_"): continue
                attr = getattr(mod, name, None)
                if callable(attr) and getattr(attr, "__module__", "") == mod.__name__:
                    api.append(name)
            results["module_api_count"] = len(api)
            results["module_api"] = api[:20]
        except Exception:
            pass
        # Try calling arity-0 module-level functions
        try:
            import importlib as _il
            mod = _il.import_module(self.__class__.__module__)
            invoked = {}
            import inspect as _inspect
            for name in dir(mod):
                if name.startswith("_"): continue
                if name in ("BrainMechanism",): continue
                fn = getattr(mod, name, None)
                if not callable(fn): continue
                if getattr(fn, "__module__", "") != mod.__name__: continue
                try:
                    sig = _inspect.signature(fn)
                    required = [p for p in sig.parameters.values() if p.default is _inspect.Parameter.empty and p.kind not in (_inspect.Parameter.VAR_POSITIONAL, _inspect.Parameter.VAR_KEYWORD)]
                    if required: continue
                    out = fn()
                    if isinstance(out, (int, float, bool, str)):
                        invoked[name] = out
                    elif isinstance(out, (dict, list, tuple)):
                        if len(str(out)) < 300:
                            invoked[name] = out
                        else:
                            invoked[name] = f"<{type(out).__name__} len={len(out) if hasattr(out,'__len__') else '?'}>"
                except Exception:
                    continue
            if invoked:
                results["invoked"] = invoked
        except Exception:
            pass
        if not hasattr(self, "state") or self.state is None:
            self.state = {}
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try: self.persist_state()
        except: pass
        return results
