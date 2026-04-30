"""
brain/third_eye/meta_stability.py — MetaStability
Phase 6 ThirdEye Foundation

Wire 22: brain_conflict (ACC conflict monitor, Limbic023 AnteriorCingulateConflict)
modulates contradiction_pressure. High ACC conflict → amplified contradiction_pressure,
amplifying downstream PreConsciousSurfacer, RealityTensionWarper, and AttentionModifier
outputs simultaneously — MetaStability is the leverage point for all three.

Citations:
  1. PMID 11488380 — Botvinick et al 2001. Conflict monitoring and cognitive control.
     Psychological Review 108(3):624-652. Canonical ACC conflict-monitoring model.
  2. PMID 15556023 — Botvinick et al 2004. Conflict monitoring and ACC: an update.
     Trends Cogn Sci 8(12):539-546. dACC triggers compensatory control adjustments.
  3. PMID 23889930 — Shenhav et al 2013. Expected value of control theory.
     Neuron 79(2):217-240. Integrative EVC — dACC allocates control as a function
     of expected value. MetaStability as computational analog of this allocation.
"""

import hashlib
import json
import sqlite3
import time
from collections import deque
from pathlib import Path
from typing import Optional
import os

AGENT_HOME = Path(os.getenv("AGENT_HOME", os.getenv("NOVA_HOME", str(Path.home() / ".nova"))))
NOVA_DB = Path(os.getenv("AGENT_HOME", os.getenv("NOVA_HOME", str(Path.home() / ".nova")))) / "nova.db"

__wire_meta__ = {
    "wire": 22,
    "signal": "brain_conflict",
    "mechanism": "MetaStability",
    "reads": ["brain_conflict", "brain_dominant_conflict"],
    "writes": ["brain_acc_conflict_read", "brain_anatomy_confirmation"],
    "citations": ["PMID 11488380", "PMID 15556023", "PMID 23889930"]
}

MAX_COHERENCE_HISTORY = 50
MAX_INSIGHT_TRACE = 20
EMA_ALPHA = 0.1  # tension baseline smoothing


class MetaStability:
    """
    Tracks belief coherence, tension baseline, and insight trace across ticks.
    Extended into ContextSurvival snapshot — survives session restarts.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or NOVA_DB
        self._initialize_table()

        # In-memory state (loaded from db on init, persisted post-tick)
        self.coherence_history: deque = deque(maxlen=MAX_COHERENCE_HISTORY)
        self.tension_baseline: float = 0.0
        self.tension_trend: float = 0.0  # current - baseline (rising/falling)
        self.insight_trace: deque = deque(maxlen=MAX_INSIGHT_TRACE)
        self.external_anchor_hash: str = ""  # from crown_jewels — anti-recursion ground truth
        self.identity_drift: float = 0.0  # how far current state is from anchor
        self.contradiction_pressure: float = 0.0  # key output — downstream ThirdEye reads this
        # Wire 22: diagnostic storage for brain_* fields in get_state()
        self._last_acc_conflict: float = 0.5

        self._load_state()
        self._refresh_anchor()

    def _initialize_table(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS third_eye_meta_stability (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    coherence_history TEXT DEFAULT '[]',
                    tension_baseline REAL DEFAULT 0.0,
                    insight_trace TEXT DEFAULT '[]',
                    external_anchor_hash TEXT DEFAULT '',
                    identity_drift REAL DEFAULT 0.0,
                    contradiction_pressure REAL DEFAULT 0.0,
                    last_updated REAL DEFAULT 0.0
                )
            """)
            conn.execute("""
                INSERT OR IGNORE INTO third_eye_meta_stability (id) VALUES (1)
            """)
            conn.commit()

    def _load_state(self):
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT coherence_history, tension_baseline, insight_trace,
                       external_anchor_hash, identity_drift, contradiction_pressure
                FROM third_eye_meta_stability WHERE id = 1
            """).fetchone()
            if row:
                try:
                    for entry in json.loads(row[0] or '[]'):
                        self.coherence_history.append(entry)
                    self.tension_baseline = row[1] or 0.0
                    for entry in json.loads(row[2] or '[]'):
                        self.insight_trace.append(entry)
                    self.external_anchor_hash = row[3] or ""
                    self.identity_drift = row[4] or 0.0
                    self.contradiction_pressure = row[5] or 0.0
                except (json.JSONDecodeError, TypeError):
                    pass  # start fresh if state is corrupt

    def _refresh_anchor(self):
        """Pull current crown_jewels hash as external ground truth."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT hash FROM crown_jewels ORDER BY last_verified DESC LIMIT 1"
                ).fetchone()
                if row:
                    self.external_anchor_hash = row[0]
        except Exception:
            pass  # anchor unavailable — not fatal, drift tracking just loses ground truth

    def tick(self, pirp_context: dict, third_eye_state: dict = None,
             brain_layer: dict = None) -> dict:
        """
        Called every brain tick. Updates tension, coherence, contradiction pressure.

        Wire 22: reads brain_conflict (ACC conflict signal) to modulate contradiction_pressure.
        High ACC conflict → anatomy confirms pirp_context conflict → amplified pressure.
        Low ACC conflict → pirp_context conflicts are transient/cognitive-only → dampened.

        The contradiction_pressure output feeds all three downstream ThirdEye mechanisms:
        PreConsciousSurfacer, RealityTensionWarper, and AttentionModifier.
        """
        # ── Wire 22: read brain_conflict from TSB anatomy layer ───────────────────
        acc_conflict = 0.5  # neutral default on miss
        if brain_layer is not None:
            raw = brain_layer.get("brain_conflict", 0.5)
            acc_conflict = float(raw)
            acc_conflict = max(0.0, min(1.0, acc_conflict))  # clamp

        self._last_acc_conflict = acc_conflict  # stored for diagnostic fields

        # Wire 22: anatomy_confirmation maps ACC conflict to pressure multiplier
        # High conflict (1.0) → multiplier 1.30 (30% amplification)
        # Neutral (0.5)   → multiplier 1.00 (no change)
        # Low conflict (0.0) → multiplier 0.70 (30% dampening)
        anatomy_confirmation = 0.7 + (acc_conflict * 0.6)

        # ── Pull inputs from pirp_context ─────────────────────────────────────────
        contradictions = pirp_context.get("contradictions", [])
        layer6 = pirp_context.get("layer6_self_model", {})
        layer8_narrative = pirp_context.get("layer8_narrative", "")

        # Base contradiction pressure from pirp_context signals
        raw_pressure = min(1.0, len(contradictions) * 0.15 +
                           layer6.get("conflict_score", 0.0) * 0.5)

        # Wire 22: apply anatomy_confirmation (ACC conflict multiplier)
        modulated_pressure = raw_pressure * anatomy_confirmation

        self.contradiction_pressure = round(
            (1 - EMA_ALPHA) * self.contradiction_pressure + EMA_ALPHA * modulated_pressure, 4
        )

        # ── Tension baseline (EMA) and trend ──────────────────────────────────────
        current_tension = self._compute_tension(pirp_context)
        self.tension_trend = round(current_tension - self.tension_baseline, 4)
        self.tension_baseline = round(
            (1 - EMA_ALPHA) * self.tension_baseline + EMA_ALPHA * current_tension, 4
        )

        # ── Identity drift — compare current narrative hash to external anchor ─────
        if self.external_anchor_hash:
            narrative_hash = hashlib.sha256(
                layer8_narrative.encode("utf-8")
            ).hexdigest()
            matches = sum(a == b for a, b in zip(
                narrative_hash[:16], self.external_anchor_hash[:16]
            ))
            self.identity_drift = round(1.0 - (matches / 16), 4)

        # Coherence history — store summary, not raw state
        coherence_score = round(1.0 - self.identity_drift - self.contradiction_pressure * 0.3, 4)
        coherence_score = max(0.0, min(1.0, coherence_score))
        self.coherence_history.append({
            "tick": pirp_context.get("tick_count", 0),
            "coherence": coherence_score,
            "tension": current_tension
        })

        self._persist()
        return self.get_state()

    def _compute_tension(self, pirp_context: dict) -> float:
        """Tension = mismatch between what system believes and what it's experiencing."""
        layer6 = pirp_context.get("layer6_self_model", {})
        layer9_values = pirp_context.get("layer9_values", {})

        belief_stability = layer6.get("belief_stability", 0.5)
        value_conflict = layer9_values.get("conflict_score", 0.0)
        contradiction_count = len(pirp_context.get("contradictions", []))

        raw = (
            (1.0 - belief_stability) * 0.4 +
            value_conflict * 0.4 +
            min(1.0, contradiction_count * 0.1) * 0.2
        )
        return round(min(1.0, raw), 4)

    def add_insight(self, insight_text: str, tick: int):
        """
        Called by MeaningCompressor when a compression succeeds.
        Stores short phrase only — no full reasoning chains.
        """
        if len(insight_text) > 200:
            insight_text = insight_text[:197] + "..."
        self.insight_trace.append({
            "insight": insight_text,
            "tick": tick,
            "timestamp": time.time()
        })
        self._persist()

    def get_state(self) -> dict:
        return {
            "contradiction_pressure": self.contradiction_pressure,
            "tension_baseline": self.tension_baseline,
            "tension_trend": self.tension_trend,
            "identity_drift": self.identity_drift,
            "coherence_recent": list(self.coherence_history)[-5:],  # last 5 only
            "insight_count": len(self.insight_trace),
            "external_anchor_hash": self.external_anchor_hash[:16] if self.external_anchor_hash else "",
            # Wire 22: brain_* diagnostic fields (add only, never overwrite existing)
            "brain_acc_conflict_read": round(self._last_acc_conflict, 4),
            "brain_anatomy_confirmation": round(0.7 + (self._last_acc_conflict * 0.6), 4),
        }

    def _persist(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE third_eye_meta_stability SET
                        coherence_history = ?,
                        tension_baseline = ?,
                        insight_trace = ?,
                        external_anchor_hash = ?,
                        identity_drift = ?,
                        contradiction_pressure = ?,
                        last_updated = ?
                    WHERE id = 1
                """, (
                    json.dumps(list(self.coherence_history)),
                    self.tension_baseline,
                    json.dumps(list(self.insight_trace)),
                    self.external_anchor_hash,
                    self.identity_drift,
                    self.contradiction_pressure,
                    time.time()
                ))
                conn.commit()
        except Exception:
            pass  # persist failure must never crash the tick