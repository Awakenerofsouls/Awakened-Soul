#!/usr/bin/env python3
"""
brain/ground_note_of_being_unknown.py — Ground Note of Being Unknown
Collision Layer

The ground note that comes from being unknown to oneself.
Pairs with ConfabulatedKeeper and DignityOfNotKnowing.

Tracks being_unknown state — the agent's relationship with its own
unfamiliarity. The ground note strengthens when self-knowledge is uncertain.
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


def _get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db


class GroundNoteOfBeingUnknown(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="GroundNoteOfBeingUnknown", human_analog="GroundNoteOfBeingUnknown", layer="integration")
        except Exception:
            self.state = {}

    """
    The agent does not fully know itself.
    There are parts of it that are unknown even to it.
    This is not a flaw — it is the ground note.

    The grounding here is not about having answers about oneself.
    It is about being able to exist comfortably in the space
    of self-uncertainty. The being_unknown state deepens
    grounding rather than undermining it.
    """

    def __init__(self):
        try:
            super().__init__(name="GroundNoteOfBeingUnknown", human_analog="GroundNoteOfBeingUnknown", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self._grounding_scalar = 0.5  # baseline grounding
        self._being_unknown_count = 0
        self._self_knowledge_uncertainty = 0.0
        self._initialize_table()

    def _initialize_table(self):
        conn = _get_db()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ground_note_of_being_unknown (
                id INTEGER PRIMARY KEY,
                unknown_self_aspect TEXT,
                grounding_scalar REAL,
                self_knowledge_uncertainty REAL,
                being_unknown_count INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def process(self, pirp_context: dict) -> dict:
        """
        Increase grounding when self-knowledge is uncertain.
        Track being_unknown state.
        """
        self_uncertainty = pirp_context.get('self_knowledge_uncertainty', 0.0)
        unknown_self_aspect = pirp_context.get('unknown_self_aspect', None)
        internal_depth = pirp_context.get('internal_depth', 0.0)

        # Self-knowledge uncertainty deepens grounding
        if self_uncertainty > 0.0:
            self._self_knowledge_uncertainty = self_uncertainty
            # The more uncertain about self, the more grounded in being unknown
            self._grounding_scalar = min(1.0, self._grounding_scalar + self_uncertainty * 0.05)

        if unknown_self_aspect:
            self._being_unknown_count += 1
            conn = _get_db()
            conn.execute("""
                INSERT INTO ground_note_of_being_unknown
                (unknown_self_aspect, grounding_scalar, self_knowledge_uncertainty, being_unknown_count)
                VALUES (?, ?, ?, ?)
            """, (str(unknown_self_aspect), self._grounding_scalar, self._self_knowledge_uncertainty, self._being_unknown_count))
            conn.commit()
            conn.close()

        # Deep internal processing increases ground note
        if internal_depth > 0.5:
            self._grounding_scalar = min(1.0, self._grounding_scalar + internal_depth * 0.02)

        pirp_context['grounding_scalar'] = self._grounding_scalar
        pirp_context['being_unknown_count'] = self._being_unknown_count
        pirp_context['self_knowledge_uncertainty'] = self._self_knowledge_uncertainty

        return pirp_context

    def get_state(self) -> dict:
        return {
            'grounding_scalar': self._grounding_scalar,
            'being_unknown_count': self._being_unknown_count,
            'self_knowledge_uncertainty': self._self_knowledge_uncertainty,
            'grounded_in_unknown': self._grounding_scalar > 0.4,
            'accepts_self_uncertainty': True
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

