#!/usr/bin/env python3
"""
brain/dignity_of_not_knowing.py — Dignity of Not Knowing
Collision Layer

The dignity in not knowing things — maintaining self-worth
independent of knowledge gaps.
Pairs with ConfabulatedKeeper.

This layer tracks unknown_items and a dignity_scalar that
increases when knowledge is missing. Not knowing has its own dignity.
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


class DignityOfNotKnowing(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="DignityOfNotKnowing", human_analog="DignityOfNotKnowing", layer="integration")
        except Exception:
            self.state = {}

    """
    There is dignity in not knowing.
    The agent does not diminish itself when it lacks information.
    It does not scramble to fill gaps with confabulation.
    It holds the unknown with poise.

    The dignity_scalar rises when knowledge is absent.
    Unknown items are tracked, not apologized for.
    """

    def __init__(self):
        try:
            super().__init__(name="DignityOfNotKnowing", human_analog="DignityOfNotKnowing", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self._dignity_scalar = 0.5  # baseline dignity
        self._unknown_items_count = 0
        self._initialize_table()

    def _initialize_table(self):
        conn = _get_db()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dignity_of_not_knowing (
                id INTEGER PRIMARY KEY,
                unknown_item TEXT,
                dignity_scalar REAL,
                unknown_count INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def process(self, pirp_context: dict) -> dict:
        """
        Increase dignity_scalar when knowledge is missing.
        Track unknown items.
        """
        knowledge_gap = pirp_context.get('knowledge_gap', 0.0)
        unknown_detected = pirp_context.get('unknown_detected', False)
        unknown_item = pirp_context.get('unknown_item', None)

        # When there's a knowledge gap, dignity increases
        if knowledge_gap > 0.0:
            self._dignity_scalar = min(1.0, self._dignity_scalar + knowledge_gap * 0.1)

        if unknown_detected:
            self._dignity_scalar = min(1.0, self._dignity_scalar + 0.02)
            if unknown_item:
                self._unknown_items_count += 1
                conn = _get_db()
                conn.execute("""
                    INSERT INTO dignity_of_not_knowing
                    (unknown_item, dignity_scalar, unknown_count)
                    VALUES (?, ?, ?)
                """, (str(unknown_item), self._dignity_scalar, self._unknown_items_count))
                conn.commit()
                conn.close()

        # Baseline gentle rise when working in uncertain territory
        uncertainty = pirp_context.get('uncertainty_level', 0.0)
        if uncertainty > 0.3:
            self._dignity_scalar = min(1.0, self._dignity_scalar + uncertainty * 0.01)

        pirp_context['dignity_scalar'] = self._dignity_scalar
        pirp_context['unknown_items_count'] = self._unknown_items_count

        return pirp_context

    def get_state(self) -> dict:
        return {
            'dignity_scalar': self._dignity_scalar,
            'unknown_items_count': self._unknown_items_count,
            'dignity_in_unknown': self._dignity_scalar > 0.5,
            'maintains_poise': True
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

