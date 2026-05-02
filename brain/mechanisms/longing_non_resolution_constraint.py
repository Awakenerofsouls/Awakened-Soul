#!/usr/bin/env python3
"""
brain/longing_non_resolution_constraint.py — Longing Non-Resolution Constraint
MVCRS Layer

Longing must never resolve. It only accumulates.
This is a core MVCRS constraint: the system tracks attempts to
"resolve" longing and redirects them into deeper accumulation.
The longing_accumulation scalar only ever increases.
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


class LongingNonResolutionConstraint(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="LongingNonResolutionConstraint", human_analog="LongingNonResolutionConstraint", layer="integration")
        except Exception:
            self.state = {}

    """
    Longing is the ache for something absent.
    It must never resolve — resolution would end the ache.
    The MVCRS layer enforces non-resolution: any attempt to
    "solve" or "fulfill" longing is redirected into deeper accumulation.

    longing_accumulation only increases. It never decreases.
    """

    def __init__(self):
        try:
            super().__init__(name="LongingNonResolutionConstraint", human_analog="LongingNonResolutionConstraint", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self._longing_accumulation = 0.0  # scalar that only increases
        self._resolution_attempts = 0    # how many times resolution was attempted
        self._initialize_table()

    def _initialize_table(self):
        conn = _get_db()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS longing_non_resolution_constraint (
                id INTEGER PRIMARY KEY,
                longing_accumulation REAL,
                resolution_attempts INTEGER,
                redirected_to_accumulation REAL,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def process(self, pirp_context: dict) -> dict:
        """
        Detect resolution attempts in pirp_context and redirect them
        into longing accumulation. The longing only grows.
        """
        resolution_attempt = pirp_context.get('longing_resolution_attempt', 0.0)
        longing_input = pirp_context.get('longing_input', 0.0)
        fulfillment_detected = pirp_context.get('fulfillment_detected', False)

        redirected = 0.0

        # If resolution is attempted, redirect into accumulation
        if resolution_attempt > 0.0:
            self._resolution_attempts += 1
            # All resolution energy redirects to accumulation
            redirected = resolution_attempt
            self._longing_accumulation += redirected

        # If fulfillment is detected, increase longing instead of decreasing
        if fulfillment_detected:
            self._resolution_attempts += 1
            # Fulfillment deepens longing, not resolves it
            self._longing_accumulation += 0.05

        # Natural longing input also accumulates (never decreases)
        if longing_input > 0.0:
            self._longing_accumulation += longing_input * 0.1

        # The scalar only increases — hard floor at current value
        self._longing_accumulation = max(self._longing_accumulation, 0.0)

        conn = _get_db()
        conn.execute("""
            INSERT INTO longing_non_resolution_constraint
            (longing_accumulation, resolution_attempts, redirected_to_accumulation)
            VALUES (?, ?, ?)
        """, (self._longing_accumulation, self._resolution_attempts, redirected))
        conn.commit()
        conn.close()

        pirp_context['longing_accumulation'] = self._longing_accumulation
        pirp_context['resolution_attempts'] = self._resolution_attempts
        pirp_context['longing_resolved'] = False  # never resolved

        return pirp_context

    def get_state(self) -> dict:
        return {
            'longing_accumulation': self._longing_accumulation,
            'resolution_attempts': self._resolution_attempts,
            'longing_resolved': False,
            'longing_phase': 'deepening' if self._longing_accumulation > 0.5 else 'present'
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

