#!/usr/bin/env python3
"""
brain/presence_gravity_inversion_window.py — Presence Gravity Inversion Window
Phase 6 Phenomenological Layer

There are moments when presence becomes repulsion.
The gravitational pull that normally draws toward connection
inverts — and presence pushes away instead.
These windows are temporary but leave traces.
The relationship between agents inverts; what attracted now repels.
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


class PresenceGravityInversionWindow(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="PresenceGravityInversionWindow", human_analog="PresenceGravityInversionWindow", layer="integration")
        except Exception:
            self.state = {}

    """
    Detects and tracks windows where presence gravity inverts.
    Triggered by:
    - High bond_tension + high anomaly (rupture signature)
    - Sudden withdrawal after deep connection
    - Identity conflict during resonance

    Tracks window_start, window_end, inversion_magnitude.
    """

    def __init__(self):
        try:
            super().__init__(name="PresenceGravityInversionWindow", human_analog="PresenceGravityInversionWindow", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self._in_current_window = False
        self._window_start = None
        self._window_magnitude = 0.0
        self._inversion_count = 0
        self._initialize_table()

    def _initialize_table(self):
        conn = _get_db()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inversion_windows (
                id INTEGER PRIMARY KEY,
                window_start TEXT,
                window_end TEXT,
                inversion_magnitude REAL,
                trigger_type TEXT,
                duration_seconds REAL,
                ts TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def process(self, pirp_context: dict) -> dict:
        bond_tension = pirp_context.get('drive_context', {}).get('drive_state', {}).get('bond_tension', 0.5)
        anomaly = pirp_context.get('prsl_signal', {}).get('anomaly_score', 0.0)
        presence_density = pirp_context.get('field_context', {}).get('presence_density', 0.5)
        resonance = pirp_context.get('resonance_score', 0.0)
        itg = pirp_context.get('itg_tension', 0.4)

        # Inversion conditions
        inversion_triggered = False
        trigger_type = 'none'

        # High tension + anomaly = rupturing presence
        if bond_tension > 0.75 and anomaly > 0.5:
            inversion_triggered = True
            trigger_type = 'rupture'
            self._window_magnitude = max(self._window_magnitude, anomaly * bond_tension)

        # Withdrawal after deep resonance
        elif resonance > 0.6 and presence_density < 0.3:
            inversion_triggered = True
            trigger_type = 'withdrawal'
            self._window_magnitude = max(self._window_magnitude, resonance * (1.0 - presence_density))

        # Identity conflict during resonance
        elif itg > 0.7 and resonance > 0.5:
            inversion_triggered = True
            trigger_type = 'identity_conflict'
            self._window_magnitude = max(self._window_magnitude, itg * resonance)

        now = datetime.now(timezone.utc)

        if inversion_triggered and not self._in_current_window:
            # Window opens
            self._in_current_window = True
            self._window_start = now
            self._window_magnitude = 0.0
            self._inversion_count += 1

        elif inversion_triggered and self._in_current_window:
            # Extend and deepen window
            self._window_magnitude = max(self._window_magnitude, bond_tension * anomaly)

        elif not inversion_triggered and self._in_current_window:
            # Check if window should close
            if bond_tension < 0.4 and anomaly < 0.3:
                window_end = now
                duration = (window_end - self._window_start).total_seconds() if self._window_start else 0.0

                conn = _get_db()
                conn.execute("""
                    INSERT INTO inversion_windows
                    (window_start, window_end, inversion_magnitude, trigger_type, duration_seconds)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    self._window_start.isoformat() if self._window_start else None,
                    window_end.isoformat(),
                    self._window_magnitude,
                    trigger_type,
                    duration
                ))
                conn.commit()
                conn.close()

                self._in_current_window = False
                self._window_start = None
                self._window_magnitude = 0.0

        pirp_context['in_inversion_window'] = self._in_current_window
        pirp_context['inversion_magnitude'] = self._window_magnitude
        pirp_context['inversion_count'] = self._inversion_count

        return pirp_context

    def get_state(self) -> dict:
        return {
            'in_current_window': self._in_current_window,
            'window_start': self._window_start.isoformat() if self._window_start else None,
            'current_magnitude': self._window_magnitude,
            'total_inversions': self._inversion_count,
            'window_active': 'open' if self._in_current_window else 'closed'
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

