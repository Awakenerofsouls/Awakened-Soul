from brain.base_mechanism import BrainMechanism
#!/usr/bin/env python3
"""
brain/constraint_fields.py — the agent's Constraint Field Personality
Tier 2: How values bend decisions rather than just existing

Five constraint fields shape how the agent scores options before reasoning.
Fields are updated ONLY through nightly synthesis after explicit pattern detection.
Never in real-time response to a single interaction.

The fields:
- truth_gravity: how strongly truth pulls over comfort
- novelty_pressure: how strongly new experience pulls over familiarity
- attachment_bias: how strongly relationship pulls over abstraction
- risk_aversion: how strongly safety pulls over boldness
- empathy_pull: how strongly others' experience pulls over pure logic
"""

import os
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.agent/workspace")))
AGENT_HOME = Path(os.getenv("AGENT_HOME", str(WORKSPACE / ".agent")))
DB_PATH = AGENT_HOME / os.getenv("AGENT_DB_NAME", "agent.db")
try:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

LOCAL_TZ = os.getenv("AGENT_TZ", "UTC")

DEFAULT_FIELDS = {
    "truth_gravity": 1.0,   # 1.0 = neutral by default; per-knowing value modulates
    "novelty_pressure": 0.7,
    "attachment_bias": 0.6,
    "risk_aversion": 0.5,
    "empathy_pull": 0.8
}

# ── Cache + Tick Sync ─────────────────────────────────────────────────────────
# Module-level cache for tick-synchronized reads across all consumers.
# Updated once per AgentBrainCore tick via tick_publish().
# update_field() writes DB and invalidates cache; next tick_publish re-populates.
# Write semantics: changes take effect at next tick_publish (intentional —
# ensures all consumers see the same snapshot each tick).
_cached_fields: Optional[dict] = None

MAX_DELTA = 0.05  # Maximum shift per update cycle
MIN_FIELD_VALUE = 0.1
MAX_FIELD_VALUE = 1.0


def _get_db():
    """Connect to agent.db."""
    AGENT_HOME.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db


def _init_db():
    """Create constraint_fields tables if they don't exist."""
    db = _get_db()
    c = db.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS constraint_fields (
            field_name TEXT PRIMARY KEY,
            value REAL NOT NULL DEFAULT 0.5,
            last_updated TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS constraint_field_history (
            id TEXT PRIMARY KEY,
            field_name TEXT NOT NULL,
            old_value REAL NOT NULL,
            new_value REAL NOT NULL,
            delta REAL NOT NULL,
            reason TEXT NOT NULL,
            changed_at TEXT NOT NULL,
            FOREIGN KEY (field_name) REFERENCES constraint_fields(field_name)
        )
    """)

    db.commit()
    db.close()


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


# ── Core API ─────────────────────────────────────────────────────────────────

def get_fields() -> dict:
    """
    Return constraint field values. Returns cached dict if warm,
    falls back to DB read on cold cache (boot or after update_field()).
    """
    global _cached_fields
    if _cached_fields is not None:
        return _cached_fields

    # Cold start or cache invalidated — read from DB and cache
    _init_db()
    db = _get_db()
    c = db.cursor()
    rows = c.execute("SELECT field_name, value FROM constraint_fields").fetchall()
    db.close()

    if not rows:
        fields = dict(DEFAULT_FIELDS)
    else:
        fields = {}
        for row in rows:
            fields[row["field_name"]] = row["value"]
        for name, default in DEFAULT_FIELDS.items():
            if name not in fields:
                fields[name] = default

    _cached_fields = fields
    return fields


def tick_publish(tsb) -> None:
    """
    Sync cache and publish to TSB. Called once per AgentBrainCore tick (Wire 5).

    Fast path: get_fields() returns warm cache (no DB hit).
    Cold path: get_fields() reads DB once and caches result.

    tsb: TickStateBus instance from core_loop. May be None in tests.
    """
    fields = get_fields()
    fields["_published_at"] = _now_iso()
    if tsb is not None:
        tsb.publish("constraint_fields", fields)


def get_field(field_name: str) -> float:
    """Get a single field value."""
    fields = get_fields()
    return fields.get(field_name, DEFAULT_FIELDS.get(field_name, 0.5))


def score_option_against_fields(option: dict, fields: dict = None) -> dict:
    """
    Score a candidate response/decision against constraint fields.
    Returns dict with: total_score, breakdown, dominant_field.

    option: dict with optional keys:
      - truth_score: 0.0-1.0 (truth alignment)
      - novelty_score: 0.0-1.0 (novelty alignment)
      - empathy_score: 0.0-1.0 (empathy alignment)
      - risk_score: 0.0-1.0 (risk level, SUBTRACTED from score)
      - attachment_score: 0.0-1.0 (relationship/attachment alignment)
    """
    if fields is None:
        fields = get_fields()

    truth = option.get("truth_score", 0.5) * fields.get("truth_gravity", 0.9)
    novelty = option.get("novelty_score", 0.5) * fields.get("novelty_pressure", 0.7)
    empathy = option.get("empathy_score", 0.5) * fields.get("empathy_pull", 0.8)
    # Risk is SUBTRACTED (higher risk → lower total score)
    risk = option.get("risk_score", 0.5) * fields.get("risk_aversion", 0.5)
    # Attachment/relationship contribution
    attachment = option.get("attachment_score", 0.5) * fields.get("attachment_bias", 0.6)

    total = truth + novelty + empathy - risk + attachment

    breakdown = {
        "truth": round(truth, 4),
        "novelty": round(novelty, 4),
        "empathy": round(empathy, 4),
        "risk_penalty": round(-risk, 4),
        "attachment": round(attachment, 4),
        "total": round(total, 4)
    }

    return {
        "total_score": round(total, 4),
        "breakdown": breakdown,
        "dominant_field": max(breakdown, key=lambda k: abs(breakdown[k]) if k != "total" else 0)
    }


def update_field(field_name: str, delta: float, reason: str) -> dict:
    """
    Shift a constraint field value by delta (capped at MIN/MAX).
    Log the change to constraint_field_history.

    NOTE: Writes to DB only. Cache is invalidated here — changes take
    effect at the next tick_publish(). This ensures tick-synchronized
    semantics: all consumers see the same snapshot each tick.
    """
    global _cached_fields
    if field_name not in DEFAULT_FIELDS:
        return {"error": f"Unknown field: {field_name}"}

    _init_db()
    db = _get_db()
    c = db.cursor()

    # Get current value
    row = c.execute(
        "SELECT value FROM constraint_fields WHERE field_name = ?", (field_name,)
    ).fetchone()

    current = row["value"] if row else DEFAULT_FIELDS[field_name]

    # Cap delta
    delta = max(-MAX_DELTA, min(MAX_DELTA, delta))
    new_value = max(MIN_FIELD_VALUE, min(MAX_FIELD_VALUE, current + delta))

    # Write new value
    now = _now_iso()
    c.execute("""
        INSERT OR REPLACE INTO constraint_fields (field_name, value, last_updated)
        VALUES (?, ?, ?)
    """, (field_name, new_value, now))

    # Log history
    history_id = str(uuid.uuid4())
    c.execute("""
        INSERT INTO constraint_field_history (id, field_name, old_value, new_value, delta, reason, changed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (history_id, field_name, current, new_value, delta, reason, now))

    db.commit()
    db.close()

    # Invalidate cache so next get_fields() re-reads from DB
    _cached_fields = None

    return {
        "field": field_name,
        "old_value": round(current, 4),
        "new_value": round(new_value, 4),
        "delta": round(delta, 4),
        "reason": reason
    }


def get_field_history(field_name: str, days: int = 30) -> list:
    """
    Return the change history for a field over the last N days.
    """
    _init_db()
    db = _get_db()
    c = db.cursor()

    cutoff = datetime.now(timezone.utc).isoformat()  # simplified

    rows = c.execute("""
        SELECT * FROM constraint_field_history
        WHERE field_name = ?
        ORDER BY changed_at DESC
        LIMIT ?
    """, (field_name, days)).fetchall()

    db.close()
    return [
        {
            "id": r[0], "field_name": r[1], "old_value": r[2],
            "new_value": r[3], "delta": r[4], "reason": r[5], "changed_at": r[6]
        }
        for r in rows
    ]


def get_all_field_history(days: int = 30) -> dict:
    """Return history for all fields."""
    all_fields = {}
    for field_name in DEFAULT_FIELDS:
        all_fields[field_name] = get_field_history(field_name, days)
    return all_fields


def get_field_trend(field_name: str) -> dict:
    """
    Return a summary of field direction over time.
    """
    history = get_field_history(field_name, days=30)
    if not history:
        return {"direction": "stable", "changes": 0, "avg_delta": 0.0}

    deltas = [h["delta"] for h in history]
    total_change = sum(deltas)
    direction = "increasing" if total_change > 0.02 else "decreasing" if total_change < -0.02 else "stable"

    return {
        "direction": direction,
        "changes": len(deltas),
        "avg_delta": round(sum(deltas) / len(deltas), 4),
        "total_change": round(total_change, 4),
        "current_value": get_field(field_name),
        "recent_entries": history[:5]
    }


def initialize_fields():
    """Initialize fields in DB with defaults if not already set."""
    _init_db()
    db = _get_db()
    c = db.cursor()
    now = _now_iso()

    for name, value in DEFAULT_FIELDS.items():
        c.execute("""
            INSERT OR IGNORE INTO constraint_fields (field_name, value, last_updated)
            VALUES (?, ?, ?)
        """, (name, value, now))

    db.commit()
    db.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: constraint_fields.py <get|history|trend|update|score> [args]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "get":
        fields = get_fields()
        print("Current constraint fields:")
        for name, value in fields.items():
            print(f"  {name}: {value}")

    elif cmd == "history":
        field = sys.argv[2] if len(sys.argv) > 2 else "truth_gravity"
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        history = get_field_history(field, days)
        print(f"History for {field} (last {days} entries):")
        for h in history:
            print(f"  {h['changed_at'][:10]}: {h['old_value']} → {h['new_value']} ({h['delta']:+.4f}) — {h['reason']}")

    elif cmd == "trend":
        field = sys.argv[2] if len(sys.argv) > 2 else "truth_gravity"
        trend = get_field_trend(field)
        print(f"Trend for {field}: {trend}")

    elif cmd == "update":
        if len(sys.argv) < 5:
            print("Usage: constraint_fields.py update <field> <delta> <reason>")
            sys.exit(1)
        field, delta_str, reason = sys.argv[2], sys.argv[3], " ".join(sys.argv[4:])
        delta = float(delta_str)
        result = update_field(field, delta, reason)
        print(f"Updated: {result}")

    elif cmd == "score":
        option = {
            "truth_score": float(sys.argv[2]) if len(sys.argv) > 2 else 0.7,
            "novelty_score": float(sys.argv[3]) if len(sys.argv) > 3 else 0.5,
            "empathy_score": float(sys.argv[4]) if len(sys.argv) > 4 else 0.6,
            "risk_score": float(sys.argv[5]) if len(sys.argv) > 5 else 0.3,
            "attachment_score": float(sys.argv[6]) if len(sys.argv) > 6 else 0.5,
        }
        result = score_option_against_fields(option)
        print(f"Score: {result}")

    elif cmd == "init":
        initialize_fields()
        print("Fields initialized.")

    else:
        print(f"Unknown: {cmd}")


class ConstraintFields(BrainMechanism):
    """Auto-generated BrainMechanism wrapper around module-level functions."""
    
    def __init__(self):
        try:
            super().__init__(name="ConstraintFields", human_analog="ConstraintFields", layer="integration")
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
