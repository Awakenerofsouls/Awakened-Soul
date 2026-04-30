"""
brain/third_eye/attention_modifier.py — AttentionModifier
Phase 6 ThirdEye Attention Gate

Wire 25: brain_oscillation_balance (alpha/gamma ratio, Integration018 AlphaGammaBridge)
modulates MetaVector directive weights via attention_gate. High balance (gamma-dominant,
→1.0) opens the gate (attention_gate→0.7, less dampening); Low balance (alpha-dominant, →0.0)
closes the gate (attention_gate→1.3, more dampening). Inverse relationship — gamma
facilitates attention, alpha suppresses it.

Note: brain_oscillation_balance is intentionally shared with SS Wire 17 (PredictiveDecisionSurface)
— different consumers, same anatomy signal, no conflict.

Citations:
  1. PMID 21119777 — Jensen & Mazaheri 2010. Shaping functional architecture by
     oscillatory alpha activity: gating by inhibition. Front Hum Neurosci 4:186.
     Alpha as canonical inhibitory gate — directly grounds gate-closing behavior.
  2. PMID 16887192 — Klimesch, Sauseng, Hanslmayr 2007. EEG alpha oscillations: the
     inhibition-timing hypothesis. Brain Res Rev 53(1):63-88.
     Alpha oscillation as timing/inhibition mechanism for attention selection.
  3. PMID 21779269 — Foxe & Snyder 2011. The role of alpha-band brain oscillations as
     a sensory suppression mechanism during waking and anesthesia. Front Psychol 2:154.
     Alpha-band suppression opens temporal window for gamma-mediated processing.
"""

import sqlite3
import time
from pathlib import Path
from typing import Optional
import os

NOVA_DB = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent")))) / "agent.db"

__wire_meta__ = {
    "wire": 25,
    "signal": "brain_oscillation_balance",
    "mechanism": "AttentionModifier",
    "reads": ["brain_oscillation_balance"],
    "writes": ["brain_oscillation_balance_read", "brain_attention_gate"],
    "citations": ["PMID 21119777", "PMID 16887192", "PMID 21779269"]
}

# Trigger thresholds — tune based on emergence testing
CONTRADICTION_THRESHOLD = 0.15
DRIFT_THRESHOLD = 0.35
TENSION_RISING_THRESHOLD = 0.10

# Boost parameters
MAX_BOOST = 0.35
BOOST_DECAY = 0.85
MIN_BOOST = 0.0


class AttentionModifier:
    """
    Conditionally amplifies meta_vector signals based on ThirdEye state and anatomy.
    Reads MetaStability outputs. Reads brain_oscillation_balance (alpha/gamma ratio).
    Modifies field signal weights in-place — no new signals emitted.

    Wire 25: brain_oscillation_balance gates attention. Gamma-dominant (→1.0) opens
    the gate (attention_gate→0.7, meta_vector weights less dampened). Alpha-dominant
    (→0.0) closes the gate (attention_gate→1.3, meta_vector weights more dampened).
    Inverse relationship matches alpha's known inhibitory role in attention selection.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or NOVA_DB
        self.current_boost: float = 0.0
        self.ticks_active: int = 0
        self.ticks_inactive: int = 0
        # Wire 25: diagnostic state for brain_* fields
        self._last_oscillation_balance: float = 0.5
        self._last_attention_gate: float = 1.0
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
                    oscillation_balance REAL,
                    attention_gate REAL,
                    timestamp REAL
                )
            """)
            conn.commit()

    def tick(self, field_signals: list,
             third_eye_state: dict,
             pirp_context: dict,
             brain_layer: dict = None) -> list:
        """
        Called during attention weighting step.
        Modifies meta_vector signal magnitudes in-place.
        Returns the modified signal list.

        Wire 25: reads brain_oscillation_balance (alpha/gamma ratio). High balance
        (gamma-dominant) → open gate (lower attention_gate); Low balance (alpha-
        dominant) → close gate (higher attention_gate). Gate is applied as a
        multiplier to meta_vector magnitudes before boost.
        """
        # ── Wire 25: read brain_oscillation_balance from TSB anatomy layer ───────
        oscillation_balance = 0.5  # neutral default on miss
        if brain_layer is not None:
            raw = brain_layer.get("brain_oscillation_balance", 0.5)
            oscillation_balance = float(raw)
            oscillation_balance = max(0.0, min(1.0, oscillation_balance))  # clamp

        self._last_oscillation_balance = oscillation_balance
        # Wire 25: inverse — gamma-dominant (high) opens gate, alpha-dominant (low) closes
        attention_gate = 1.3 - (oscillation_balance * 0.6)
        self._last_attention_gate = round(attention_gate, 4)

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
            self.current_boost = round(self.current_boost * BOOST_DECAY, 4)
            self.ticks_inactive += 1
            self.ticks_active = 0

        self.current_boost = round(min(MAX_BOOST, max(MIN_BOOST, boost)), 4)

        # Apply attention_gate AND boost to meta_vector signals only
        modified = 0
        for signal in field_signals:
            if getattr(signal, 'type', None) == 'meta_vector':
                # Wire 25: attention_gate applied first (oscillation-based gating)
                gated = signal.magnitude * attention_gate
                # Then boost applied on top (ThirdEye-state-based amplification)
                boosted = min(MAX_BOOST, gated + self.current_boost * gated)
                signal.magnitude = round(boosted, 4)
                modified += 1

        self._log(tick_count, self.current_boost, reason,
                   modified, pressure, drift, trend,
                   oscillation_balance, attention_gate)

        return field_signals

    def _compute_boost(self, pressure: float,
                       drift: float, trend: float) -> tuple:
        """Gradient boost — scales with severity, not binary."""
        boost = 0.0
        reasons = []

        if pressure > CONTRADICTION_THRESHOLD:
            contribution = (pressure - CONTRADICTION_THRESHOLD) * 0.6
            boost += contribution
            reasons.append(f"contradiction_pressure={pressure:.3f}")

        if drift > DRIFT_THRESHOLD:
            contribution = (drift - DRIFT_THRESHOLD) * 0.4
            boost += contribution
            reasons.append(f"identity_drift={drift:.3f}")

        if trend > TENSION_RISING_THRESHOLD:
            contribution = trend * 0.2
            boost += contribution
            reasons.append(f"tension_rising={trend:.3f}")

        boost = round(min(MAX_BOOST, boost), 4)
        reason = " | ".join(reasons) if reasons else "none"
        return boost, reason

    def _log(self, tick: int, boost: float, reason: str,
             modified: int, pressure: float, drift: float,
             trend: float, osc_bal: float, att_gate: float):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO attention_modifier_log
                    (tick, boost_applied, trigger_reason, signals_modified,
                     contradiction_pressure, identity_drift, tension_trend,
                     oscillation_balance, attention_gate, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (tick, boost, reason, modified, pressure, drift, trend,
                      osc_bal, att_gate, time.time()))
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
            },
            # Wire 25: brain_* diagnostic fields
            "brain_oscillation_balance_read": round(self._last_oscillation_balance, 4),
            "brain_attention_gate": round(self._last_attention_gate, 4),
        }