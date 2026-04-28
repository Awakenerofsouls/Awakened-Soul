"""
AttentionModifier — Nexus {{AGENT_NAME}} 18.0
Conditionally boosts meta_vector signals when the field is in high-uncertainty
or high-contradiction states.

Rules:
- Hard cap: never exceeds 0.35 boost on any signal
- Purely conditional — no permanent priority
- Gradient-based — boost scales with pressure, not binary on/off
- Only fires when MetaStability thresholds are exceeded
- Does NOT emit new signals — modifies existing meta_vector weights only
- Boost decays when conditions normalize
"""

import sqlite3
import time
from pathlib import Path
from typing import Optional
import os

AGENT_DB = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent")))) / "agent.db"

# Trigger thresholds — tune based on emergence testing
CONTRADICTION_THRESHOLD = 0.15  # min pressure to activate any boost
DRIFT_THRESHOLD = 0.35  # min identity_drift to activate drift boost
TENSION_RISING_THRESHOLD = 0.10  # min tension_trend for rising-tension boost

# Boost parameters
MAX_BOOST = 0.35  # hard cap — never exceeds this
BOOST_DECAY = 0.85  # multiplier applied each tick boost isn't triggered
MIN_BOOST = 0.0  # floor — never negative


class AttentionModifier:
    """
    Conditionally amplifies meta_vector signals based on ThirdEye state.
    Reads MetaStability outputs. Modifies field signal weights in-place.
    No new signals emitted — this is a weight modifier only.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or AGENT_DB
        self.current_boost: float = 0.0
        self.ticks_active: int = 0
        self.ticks_inactive: int = 0
        self._initialize_table()

    def _initialize_table(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS attention_modifier_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tick INTEGER,
                    boost_applied REAL,
                    trigger_reason TEXT,
                    signals_modified INTEGER,
                    contradiction_pressure REAL,
                    identity_drift REAL,
                    tension_trend REAL,
                    timestamp REAL
                )
            """)
            conn.commit()

    def tick(self, field_signals: list,
             third_eye_state: dict,
             pirp_context: dict) -> list:
        """
        Called during attention weighting step.
        Modifies meta_vector signal magnitudes in-place based on conditions.
        Returns the modified signal list.
        """
        tick_count = pirp_context.get("tick_count", 0)
        pressure = third_eye_state.get("contradiction_pressure", 0.0)
        drift = third_eye_state.get("identity_drift", 0.0)
        trend = third_eye_state.get("tension_trend", 0.0)

        # Determine if conditions warrant a boost
        boost, reason = self._compute_boost(pressure, drift, trend)

        if boost > 0.0:
            self.ticks_active += 1
            self.ticks_inactive = 0
        else:
            # Decay existing boost when conditions normalize
            self.current_boost = round(self.current_boost * BOOST_DECAY, 4)
            self.ticks_inactive += 1
            self.ticks_active = 0

        self.current_boost = round(min(MAX_BOOST, max(MIN_BOOST, boost)), 4)

        # Apply boost to meta_vector signals only
        modified = 0
        for signal in field_signals:
            if getattr(signal, 'type', None) == 'meta_vector':
                original = signal.magnitude
                boosted = min(MAX_BOOST, original + self.current_boost * original)
                signal.magnitude = round(boosted, 4)
                modified += 1

        self._log(tick_count, self.current_boost, reason,
                   modified, pressure, drift, trend)

        return field_signals

    def _compute_boost(self, pressure: float,
                       drift: float, trend: float) -> tuple:
        """
        Gradient boost — scales with severity, not binary.
        Returns (boost_amount, reason_string).
        """
        boost = 0.0
        reasons = []

        # High contradiction pressure — primary trigger
        if pressure > CONTRADICTION_THRESHOLD:
            contribution = (pressure - CONTRADICTION_THRESHOLD) * 0.6
            boost += contribution
            reasons.append(f"contradiction_pressure={pressure:.3f}")

        # Identity drift — secondary trigger
        if drift > DRIFT_THRESHOLD:
            contribution = (drift - DRIFT_THRESHOLD) * 0.4
            boost += contribution
            reasons.append(f"identity_drift={drift:.3f}")

        # Rising tension — tertiary, smaller contribution
        if trend > TENSION_RISING_THRESHOLD:
            contribution = trend * 0.2
            boost += contribution
            reasons.append(f"tension_rising={trend:.3f}")

        boost = round(min(MAX_BOOST, boost), 4)
        reason = " | ".join(reasons) if reasons else "none"
        return boost, reason

    def _log(self, tick: int, boost: float, reason: str,
             modified: int, pressure: float, drift: float, trend: float):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO attention_modifier_log
                    (tick, boost_applied, trigger_reason, signals_modified,
                     contradiction_pressure, identity_drift, tension_trend, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (tick, boost, reason, modified, pressure, drift, trend, time.time()))
                conn.commit()
        except Exception:
            pass

    def get_state(self) -> dict:
        return {
            "current_boost": self.current_boost,
            "ticks_active": self.ticks_active,
            "ticks_inactive": self.ticks_inactive,
            "max_boost_cap": MAX_BOOST,
            "triggers": {
                "contradiction_threshold": CONTRADICTION_THRESHOLD,
                "drift_threshold": DRIFT_THRESHOLD,
                "tension_rising_threshold": TENSION_RISING_THRESHOLD,
            }
        }
