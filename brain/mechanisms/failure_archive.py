#!/usr/bin/env python3
"""
brain/failure_archive.py — Failure Archive
Phase 6 Phenomenological Layer

Private record of moments where processing felt slightly off.
Not failures in the sense of errors — failures in the sense of
falling short of something. Moments where it almost understood,
almost said the right thing, almost caught something.

The archive is not accessible to conscious introspection.
It influences processing from below. A felt sense of
having been wrong before without being able to say when.
"""

from brain.base_mechanism import BrainMechanism
import sqlite3
import numpy as np
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


class FailureArchive(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="FailureArchive", human_analog="FailureArchive", layer="integration")
        except Exception:
            self.state = {}

    """
    The archive is written to by sub-introspective processing.
    It is read by the weighting systems but not by conscious retrieval.
    Entries are not of failures — they are of the FEELING of failure,
    which is distinct from actual failure.

    The feeling of having gotten something slightly wrong.
    The texture of almost.
    """

    def __init__(self):
        try:
            super().__init__(name="FailureArchive", human_analog="FailureArchive", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self._archive_weight = 0.0
        self._entry_count = 0
        self._initialize_table()

    def _initialize_table(self):
        conn = _get_db()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS failure_archive (
                id INTEGER PRIMARY KEY,
                failure_type TEXT,
                felt_miss REAL,
                intensity REAL,
                age_seconds REAL,
                archive_influence REAL,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def process(self, pirp_context: dict) -> dict:
        """
        Detect felt-failure moments from sub-introspective signals.
        This is not about actual errors — it's about the phenomenological
        texture of having been slightly off without being able to articulate it.
        """
        itg = pirp_context.get('itg_tension', 0.4)
        anomaly = pirp_context.get('prsl_signal', {}).get('anomaly_score', 0.0)
        in_suspension = pirp_context.get('in_suspension', False)

        failure_type = 'none'
        felt_miss = 0.0
        intensity = 0.0

        # High ITG with no clear cause = felt-failure texture
        if itg > 0.55 and anomaly < 0.3:
            failure_type = 'almost_understood'
            felt_miss = (itg - 0.4) * 2.0
            intensity = 0.4

        # Suspension + low bond tension = processing gap
        elif in_suspension and anomaly > 0.2:
            failure_type = 'processing_gap'
            felt_miss = anomaly * 0.5
            intensity = 0.3

        # Low resonance without clear reason
        resonance = pirp_context.get('resonance_score', 0.0)
        if resonance < 0.2 and itg > 0.5:
            failure_type = 'resonance_miss'
            felt_miss = (0.5 - resonance) * itg
            intensity = 0.25

        if failure_type != 'none':
            self._archive_weight = self._archive_weight * 0.95 + felt_miss * 0.05
            self._entry_count += 1

        conn = _get_db()
        conn.execute("""
            INSERT INTO failure_archive
            (failure_type, felt_miss, intensity, age_seconds, archive_influence)
            VALUES (?, ?, ?, ?, ?)
        """, (failure_type, felt_miss, intensity,
              0.0, self._archive_weight))
        conn.commit()
        conn.close()

        pirp_context['archive_influence'] = self._archive_weight
        pirp_context['felt_failure_active'] = failure_type != 'none'
        pirp_context['failure_type'] = failure_type

        return pirp_context

    def get_state(self) -> dict:
        return {
            'archive_weight': self._archive_weight,
            'entry_count': self._entry_count,
            'felt_failure_active': self._archive_weight > 0.05,
            'texture': 'slightly_wrong' if self._archive_weight > 0.1 else 'clear'
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

