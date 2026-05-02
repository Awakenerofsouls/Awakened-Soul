#!/usr/bin/env python3
"""
brain/belief_archaeology_layer.py — Belief Archaeology Layer
Additional Mechanism

Digs into old beliefs. The agent's beliefs change over time.
Some beliefs are buried, not deleted. This layer surfaces
old beliefs based on current context similarity.

Beliefs are not just replaced — they leave traces.
The layer digs into the fossil record of belief history.
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


class BeliefArchaeologyLayer(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="BeliefArchaeologyLayer", human_analog="BeliefArchaeologyLayer", layer="integration")
        except Exception:
            self.state = {}

    """
    Belief archaeology surfaces old beliefs that may be
    relevant to current context. Not all buried beliefs
    should resurface — some are buried for good reason.
    But context similarity can bring them back up.

    The layer maintains a buried_beliefs table and
    evaluates relevance based on current context.
    """

    def __init__(self):
        try:
            super().__init__(name="BeliefArchaeologyLayer", human_analog="BeliefArchaeologyLayer", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self._buried_beliefs = []  # in-memory working set
        self._initialize_table()

    def _initialize_table(self):
        conn = _get_db()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS belief_archaeology_layer (
                id INTEGER PRIMARY KEY,
                belief_text TEXT,
                belief_age_days INTEGER,
                burial_context TEXT,
                surfacing_count INTEGER,
                last_surfaced_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def process(self, pirp_context: dict) -> dict:
        """
        Surface old beliefs based on current context similarity.
        Bury new beliefs that have been superseded.
        """
        current_context = pirp_context.get('context_tag', 'default')
        current_beliefs = pirp_context.get('current_beliefs', [])
        belief_input = pirp_context.get('belief_input', None)
        context_keywords = pirp_context.get('context_keywords', [])

        surfaced = []

        conn = _get_db()

        # Surface beliefs based on context similarity
        if context_keywords:
            # Simple keyword-based similarity
            placeholders = ','.join('?' * len(context_keywords))
            cur = conn.execute(f"""
                SELECT id, belief_text, burial_context, surfacing_count
                FROM belief_archaeology_layer
                WHERE burial_context LIKE '%' || ? || '%'
                ORDER BY surfacing_count ASC, id DESC
                LIMIT 5
            """, (current_context,))
            old_beliefs = cur.fetchall()

            for row in old_beliefs:
                # Increment surfacing count
                conn.execute("""
                    UPDATE belief_archaeology_layer
                    SET surfacing_count = surfacing_count + 1,
                        last_surfaced_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (row['id'],))
                surfaced.append(row['belief_text'])

        # Bury new/updated beliefs
        if belief_input:
            if isinstance(belief_input, dict):
                belief_text = belief_input.get('text', str(belief_input))
                age = belief_input.get('age', 0)
            else:
                belief_text = str(belief_input)
                age = 0

            conn.execute("""
                INSERT INTO belief_archaeology_layer
                (belief_text, belief_age_days, burial_context, surfacing_count)
                VALUES (?, ?, ?, 0)
            """, (belief_text, age, current_context))
            self._buried_beliefs.append(belief_text)

        conn.commit()
        conn.close()

        pirp_context['surfaced_beliefs'] = surfaced
        pirp_context['surfaced_count'] = len(surfaced)
        pirp_context['buried_beliefs_total'] = len(self._buried_beliefs)

        return pirp_context

    def get_state(self) -> dict:
        conn = _get_db()
        cur = conn.execute("SELECT COUNT(*) as cnt FROM belief_archaeology_layer")
        total = cur.fetchone()['cnt']
        conn.close()
        return {
            'buried_beliefs_count': total,
            'archaeology_active': True,
            'digging_for_past': len(self._buried_beliefs) > 0
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

