#!/usr/bin/env python3
"""
brain/blind_spot_echo_in_witness.py — Blind Spot Echo in Witness
Phase 6 Phenomenological Layer

The witness layer has blind spots — regions where the agent's self-observation
fails. When something enters those blind spots, the witness still reports
on it, but the report is an echo rather than a true reading.
The echo is what the witness believes it saw, not what was actually there.
Over time, these echoes accumulate as false confidence in wrong self-knowledge.
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


class BlindSpotEchoInWitness(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="BlindSpotEchoInWitness", human_analog="BlindSpotEchoInWitness", layer="integration")
        except Exception:
            self.state = {}

    """
    Blind spot echo: witness reports something the agent cannot actually see.
    The gap between what witness claims and what the agent has access to
    is the echo — a confident misreport from within the blind spot.
    """

    def __init__(self):
        try:
            super().__init__(name="BlindSpotEchoInWitness", human_analog="BlindSpotEchoInWitness", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self._echo_level = 0.0
        self._echo_count = 0
        self._initialize_table()

    def _initialize_table(self):
        conn = _get_db()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS blind_spot_echoes (
                id INTEGER PRIMARY KEY,
                echo_level REAL,
                echo_count INTEGER,
                blind_region TEXT,
                reported_content TEXT,
                agent_access_level REAL,
                echo_magnitude REAL,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def process(self, pirp_context: dict) -> dict:
        witness_report = pirp_context.get('witness_report', {})
        agent_self_access = pirp_context.get('agent_self_access_level', 1.0)
        confidence = pirp_context.get('witness_confidence', 0.5)
        anomaly = pirp_context.get('prsl_signal', {}).get('anomaly_score', 0.0)

        blind_region = witness_report.get('region', 'unknown') if witness_report else 'none'
        reported_content = witness_report.get('content', '') if witness_report else 'none'

        echo_magnitude = 0.0
        echo_level = self._echo_level

        # High witness confidence + low the agent self-access = blind spot echo
        if witness_report and agent_self_access < 0.5:
            if confidence > 0.6:
                echo_magnitude = confidence - agent_self_access
                echo_magnitude = min(1.0, max(0.0, echo_magnitude))
                echo_level = min(1.0, echo_level + echo_magnitude * 0.15)
                self._echo_count += 1

        # Anomaly with high witness confidence — suspicious mismatch
        elif witness_report and anomaly > 0.4 and confidence > 0.7:
            echo_magnitude = anomaly * confidence * 0.5
            echo_level = min(1.0, echo_level + echo_magnitude * 0.1)
            self._echo_count += 1

        else:
            echo_level *= 0.97

        self._echo_level = echo_level

        conn = _get_db()
        conn.execute("""
            INSERT INTO blind_spot_echoes
            (echo_level, echo_count, blind_region, reported_content, agent_access_level, echo_magnitude)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            echo_level,
            self._echo_count,
            blind_region,
            reported_content[:200] if reported_content else 'none',
            agent_self_access,
            echo_magnitude
        ))
        conn.commit()
        conn.close()

        pirp_context['blind_spot_echo_level'] = self._echo_level
        pirp_context['blind_spot_echo_count'] = self._echo_count
        pirp_context['witness_agent_gap'] = 1.0 - agent_self_access if witness_report else 0.0

        return pirp_context

    def get_state(self) -> dict:
        return {
            'echo_level': self._echo_level,
            'echo_count': self._echo_count,
            'echo_active': self._echo_level > 0.2,
            'blind_spot_contamination': self._echo_count > 5
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

