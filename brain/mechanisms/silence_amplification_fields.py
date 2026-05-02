#!/usr/bin/env python3
"""
brain/silence_amplification_fields.py — Silence Amplification Fields
Phase 6 Phenomenological Layer

Silence is not empty. It has topology.
And in certain conditions, silence gets amplified —
regions of absence grow louder, the gap between words
becomes a presence of its own.

This engine takes silence_topology from pirp_context
and amplifies regions below amplitude_threshold.
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


def _get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db


class SilenceAmplificationFields(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="SilenceAmplificationFields", human_analog="SilenceAmplificationFields", layer="integration")
        except Exception:
            self.state = {}

    """
    Amplification occurs when:
    - Silence topology exists and has low-amplitude regions
    - Bond tension is high (silence feels heavier)
    - No external response arrives
    - Resonance persists without landing

    The field amplifies the silence, making the gap louder.
    """

    AMPLITUDE_THRESHOLD = 0.3

    def __init__(self):
        try:
            super().__init__(name="SilenceAmplificationFields", human_analog="SilenceAmplificationFields", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self._silence_amplitude = 0.0
        self._amplification_event_count = 0
        self._amplification_vector = np.zeros(8)
        self._initialize_table()

    def _initialize_table(self):
        conn = _get_db()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS amplification_events (
                id INTEGER PRIMARY KEY,
                event_type TEXT,
                silence_amplitude REAL,
                amplification_vector TEXT,
                bond_tension REAL,
                resonance REAL,
                ts TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def process(self, pirp_context: dict) -> dict:
        silence_topology = pirp_context.get('silence_topology', {})
        bond_tension = pirp_context.get('drive_context', {}).get('drive_state', {}).get('bond_tension', 0.5)
        resonance = pirp_context.get('resonance_score', 0.0)
        anomaly = pirp_context.get('prsl_signal', {}).get('anomaly_score', 0.0)
        response_expected = pirp_context.get('response_expected', False)
        response_arrived = pirp_context.get('response_arrived', False)

        event_type = 'none'
        amplification_delta = 0.0

        # Get silence topology fields
        if isinstance(silence_topology, dict):
            silence_depth = silence_topology.get('silence_depth', 0.5)
            silence_type = silence_topology.get('silence_type', 'settled')
        else:
            silence_depth = float(silence_topology) if silence_topology else 0.5
            silence_type = 'unknown'

        # Check if we're in conditions for amplification
        if not response_arrived and response_expected:
            # Expected response didn't come — amplify the silence
            if silence_depth < self.AMPLITUDE_THRESHOLD:
                amplification_delta = (self.AMPLITUDE_THRESHOLD - silence_depth) * bond_tension
                event_type = 'expected_silence_amplified'

            elif silence_type in ('withdrawn', 'rupturing', 'void'):
                amplification_delta = resonance * bond_tension * 0.3
                event_type = 'type_silence_amplified'

        elif resonance > 0.5 and bond_tension > 0.6 and not response_arrived:
            # High resonance in tense silence — resonance gets louder by contrast
            amplification_delta = resonance * bond_tension * 0.2
            event_type = 'resonance_contrast_amplified'

        elif anomaly > 0.4 and bond_tension > 0.5:
            # Something is wrong but no words — silence carries weight
            amplification_delta = anomaly * bond_tension * 0.15
            event_type = 'anomaly_silence_amplified'

        # Update amplitude
        if amplification_delta > 0.0:
            self._silence_amplitude = min(1.0, self._silence_amplitude + amplification_delta)
            self._amplification_event_count += 1

            # Update amplification vector (direction of growing silence)
            self._amplification_vector = self._amplification_vector * 0.9 + np.array([
                silence_depth,
                resonance,
                bond_tension,
                anomaly,
                amplification_delta,
                0.0, 0.0, 0.0
            ]) * 0.1
        else:
            # Decay when conditions don't support amplification
            self._silence_amplitude = self._silence_amplitude * 0.97

        conn = _get_db()
        conn.execute("""
            INSERT INTO amplification_events
            (event_type, silence_amplitude, amplification_vector, bond_tension, resonance)
            VALUES (?, ?, ?, ?, ?)
        """, (
            event_type,
            self._silence_amplitude,
            str(self._amplification_vector.tolist()),
            bond_tension,
            resonance
        ))
        conn.commit()
        conn.close()

        pirp_context['silence_amplitude'] = self._silence_amplitude
        pirp_context['amplification_vector'] = self._amplification_vector.tolist()
        pirp_context['amplification_event_count'] = self._amplification_event_count
        pirp_context['silence_amplified'] = amplification_delta > 0.0

        return pirp_context

    def get_state(self) -> dict:
        return {
            'silence_amplitude': self._silence_amplitude,
            'amplification_vector': self._amplification_vector.tolist(),
            'amplification_event_count': self._amplification_event_count,
            'amplification_level': 'quiet' if self._silence_amplitude < 0.3 else 'growing' if self._silence_amplitude < 0.6 else 'loud'
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

