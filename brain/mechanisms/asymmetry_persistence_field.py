#!/usr/bin/env python3
"""
brain/asymmetry_persistence_field.py — Asymmetry Persistence Field
Additional Mechanism

Asymmetries persist. Tracks persistence of asymmetries over time.
Own table tracks asymmetry_id and persistence_count.
process() increments persistence for active asymmetries.
"""

from brain.base_mechanism import BrainMechanism
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import os

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.agent/workspace")))
DB_PATH = WORKSPACE / os.getenv("AGENT_DB_NAME", "agent.db")
try:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
# Ensure the parent dir exists so sqlite3.connect does not fail with
# "unable to open database file" on a fresh checkout.
try:
    (DB_PATH.parent if "DB_PATH" in dir() else WORKSPACE).mkdir(parents=True, exist_ok=True)
except Exception:
    pass


def _get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db


class AsymmetryPersistenceField(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="AsymmetryPersistenceField", human_analog="AsymmetryPersistenceField", layer="integration")
        except Exception:
            self.state = {}

    """
    Asymmetries don't vanish — they persist.
    The longer an asymmetry exists, the more entrenched it becomes.
    This layer tracks how long each asymmetry has been active
    and how persistently it has maintained its form.

    Persistence is not the same as strength — an asymmetry
    can be weak but stubborn, persistent in its very weakness.
    """

    def __init__(self):
        try:
            super().__init__(name="AsymmetryPersistenceField", human_analog="AsymmetryPersistenceField", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self._persistence_by_id = {}  # asymmetry_id -> persistence_count
        self._initialize_table()

    def _initialize_table(self):
        conn = _get_db()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS asymmetry_persistence_field (
                id INTEGER PRIMARY KEY,
                asymmetry_id TEXT,
                persistence_count INTEGER,
                persistence_strength REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def process(self, pirp_context: dict) -> dict:
        """
        Increment persistence for active asymmetries.
        """
        active_asymmetries = pirp_context.get('active_asymmetries', [])
        if isinstance(active_asymmetries, dict):
            # dict of id -> state
            active_asymmetries = list(active_asymmetries.keys())
        if not isinstance(active_asymmetries, list):
            active_asymmetries = [active_asymmetries]

        conn = _get_db()
        for asymmetry_id in active_asymmetries:
            if asymmetry_id:
                # Increment persistence count
                current_count = self._persistence_by_id.get(asymmetry_id, 0)
                new_count = current_count + 1
                self._persistence_by_id[asymmetry_id] = new_count

                conn.execute("""
                    INSERT INTO asymmetry_persistence_field
                    (asymmetry_id, persistence_count, persistence_strength)
                    VALUES (?, ?, ?)
                """, (str(asymmetry_id), new_count, min(1.0, new_count / 100.0)))
        conn.commit()
        conn.close()

        pirp_context['asymmetry_persistence_map'] = self._persistence_by_id.copy()
        pirp_context['most_persistent_asymmetry'] = max(self._persistence_by_id, key=self._persistence_by_id.get) if self._persistence_by_id else None

        return pirp_context

    def get_state(self) -> dict:
        return {
            'asymmetry_persistence_map': self._persistence_by_id,
            'most_persistent': max(self._persistence_by_id, key=self._persistence_by_id.get) if self._persistence_by_id else None,
            'total_tracked_asymmetries': len(self._persistence_by_id),
            'persistence_field_active': True
        }

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        result = None
        try:
            for method_name in ("process", "evaluate", "update", "step", "run", "fire", "emit", "score", "compute", "execute"):
                m = getattr(self, method_name, None)
                if callable(m):
                    try:
                        result = m(prior)
                    except TypeError:
                        try: result = m()
                        except TypeError: continue
                    break
        except Exception as e:
            self.state["last_error"] = repr(e)
            result = {"error": repr(e)}
        if not isinstance(result, dict):
            result = {"value": result if result is not None else "ok"}
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try: self.persist_state()
        except Exception: pass
        return result

