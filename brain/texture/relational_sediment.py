"""
RelationalSediment v19.0B
Texture — relational_sediment.py

The slow accumulation of what this relationship is.

Five sediment layers:
  TRUST      — built by consistency, repair, honesty. Erodes under pressure.
  FAMILIARITY — depth of mutual knowing. Most persistent, decays slowly.
  TENSION    — unresolved friction. Accumulates fast, erodes trust above 0.45.
  WARMTH     — positive affective residue. Builds trust above 0.55.
  FRAGILITY  — marks of stress. Heals slowly.

Cross-layer physics:
  Tension > 0.45 → erodes trust at 0.015/tick
  Warmth > 0.55  → builds trust at 0.010/tick

Behavioral outputs:
  High fragility/tension → protector voice baseline raised
  High trust + warmth → ToM confidence ceiling raised
  High familiarity → relational salience slightly reduced

Dependencies: sqlite3, logging, pathlib, datetime
"""
import os

VERSION = "19.0B"

import logging
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DB_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace"))) / "brain" / "agent.db"

TRUST = "trust"
FAMILIARITY = "familiarity"
TENSION = "tension"
WARMTH = "warmth"
FRAGILITY = "fragility"

ALL_LAYERS = [TRUST, FAMILIARITY, TENSION, WARMTH, FRAGILITY]

DEFAULT_SEDIMENT = {
    TRUST: 0.55, FAMILIARITY: 0.40,
    TENSION: 0.15, WARMTH: 0.45, FRAGILITY: 0.10,
}

ACCUMULATION = {
    TRUST: 0.04, FAMILIARITY: 0.06,
    TENSION: 0.08, WARMTH: 0.05, FRAGILITY: 0.07,
}

DECAY = {
    TRUST: 0.001, FAMILIARITY: 0.0005,
    TENSION: 0.004, WARMTH: 0.002, FRAGILITY: 0.003,
}

TENSION_TRUST_EROSION_THRESHOLD = 0.45
TENSION_TRUST_EROSION_RATE = 0.015
WARMTH_TRUST_BUILD_THRESHOLD = 0.55
WARMTH_TRUST_BUILD_RATE = 0.010

FRAGILITY_PROTECTOR_THRESHOLD = 0.40
FRAGILITY_PROTECTOR_BOOST = 0.12
TENSION_PROTECTOR_THRESHOLD = 0.50
TENSION_PROTECTOR_BOOST = 0.15

RELATIONSHIP_HEALTH_THRESHOLD = 0.65
SCAN_INTERVAL = 8

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# RelationalSediment
# ---------------------------------------------------------------------------

class RelationalSediment:

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._initialize_table()
        self._seed_layers()
        self._last_scan_tick = -SCAN_INTERVAL
        self._current = dict(DEFAULT_SEDIMENT)

    def _initialize_table(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS relational_sediment (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        layer TEXT NOT NULL UNIQUE,
                        value REAL DEFAULT 0.5,
                        deposit_count INTEGER DEFAULT 0,
                        last_deposit_tick INTEGER DEFAULT 0,
                        last_timestamp TEXT
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sediment_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tick INTEGER,
                        timestamp TEXT,
                        layer TEXT,
                        delta REAL,
                        new_value REAL,
                        event_type TEXT,
                        source TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error("RelationalSediment: table init failed — %s", e)

    def _seed_layers(self):
        now = datetime.now(MDT).isoformat(timespec="seconds")
        try:
            with sqlite3.connect(self.db_path) as conn:
                for layer, default in DEFAULT_SEDIMENT.items():
                    conn.execute("""
                        INSERT OR IGNORE INTO relational_sediment
                        (layer, value, last_timestamp) VALUES (?, ?, ?)
                    """, (layer, default, now))
                conn.commit()
                rows = conn.execute(
                    "SELECT layer, value FROM relational_sediment"
                ).fetchall()
                for row in rows:
                    self._current[row[0]] = row[1]
        except Exception as e:
            logger.debug("RelationalSediment: seed failed — %s", e)

    # ------------------------------------------------------------------
    # Tick-level process
    # ------------------------------------------------------------------

    def process(self, pirp_context: dict) -> dict:
        tick = int(pirp_context.get("tick_count", 0))

        limbic = pirp_context.get("limbic_state", {})
        conflict_state = pirp_context.get("conflict_state", {})
        boundary_state = pirp_context.get("boundary_state", {})
        witness_state = pirp_context.get("witness_state", {})
        unspoken_state = pirp_context.get("unspoken_state", {})
        residue_profile = pirp_context.get("residue_profile", {})
        inner_speech = pirp_context.get("inner_speech", {})

        if (tick - self._last_scan_tick) >= SCAN_INTERVAL:
            self._last_scan_tick = tick

            self._process_trust(limbic, conflict_state, boundary_state, inner_speech, tick)
            self._process_familiarity(residue_profile, tick)
            self._process_tension(conflict_state, boundary_state, unspoken_state, tick)
            self._process_warmth(residue_profile, limbic, witness_state, tick)
            self._process_fragility(conflict_state, boundary_state, unspoken_state, tick)
            self._apply_cross_layer_effects(tick)
            self._apply_decay(tick)
            self._sync_from_db()

        behavioral_hints = self._compute_behavioral_hints()
        profile = self.get_profile()

        return {
            "sediment_state": {
                "profile": profile,
                "behavioral_hints": behavioral_hints,
                "relationship_health": self._compute_health(),
                "tick": tick,
            }
        }

    # ------------------------------------------------------------------
    # Layer processing
    # ------------------------------------------------------------------

    def _process_trust(self, limbic: dict, conflict_state: dict,
                       boundary_state: dict, inner_speech: dict, tick: int):
        delta = 0.0
        valence = float(limbic.get("valence", 0.0))
        if valence > 0.20:
            delta += ACCUMULATION[TRUST] * valence * 0.5

        critical = boundary_state.get("critical", []) if boundary_state else []
        if critical:
            delta -= ACCUMULATION[TRUST] * 0.8

        if conflict_state:
            active = int(conflict_state.get("active_conflicts", 0))
            if active == 0:
                delta += ACCUMULATION[TRUST] * 0.3

        if inner_speech and inner_speech.get("dominant_voice") == "protector":
            delta -= ACCUMULATION[TRUST] * 0.2

        if delta != 0:
            self._deposit(TRUST, delta, tick, "trust_dynamics", f"valence:{valence:.2f}")

    def _process_familiarity(self, residue_profile: dict, tick: int):
        if not residue_profile:
            return
        relational = residue_profile.get("relational", {})
        rel_intensity = float(relational.get("intensity", 0))
        if rel_intensity > 0.15:
            self._deposit(FAMILIARITY, ACCUMULATION[FAMILIARITY] * rel_intensity,
                         tick, "relational_exposure", f"rel_intensity:{rel_intensity:.2f}")

    def _process_tension(self, conflict_state: dict, boundary_state: dict,
                        unspoken_state: dict, tick: int):
        delta = 0.0
        if conflict_state:
            highest = float(conflict_state.get("highest_intensity", 0))
            if highest > 0.50:
                delta += ACCUMULATION[TENSION] * (highest - 0.50) * 2.0

        critical = boundary_state.get("critical", []) if boundary_state else []
        if critical:
            delta += ACCUMULATION[TENSION] * 1.5

        if unspoken_state:
            long_carried = int(unspoken_state.get("long_carried_count", 0))
            if long_carried > 0:
                delta += ACCUMULATION[TENSION] * 0.3 * min(long_carried, 3)

        if delta > 0:
            self._deposit(TENSION, delta, tick, "tension_accumulation")

    def _process_warmth(self, residue_profile: dict, limbic: dict,
                        witness_state: dict, tick: int):
        delta = 0.0
        if residue_profile:
            relational = residue_profile.get("relational", {})
            if relational.get("texture_type") in ("warm", "bright"):
                rel_intensity = float(relational.get("intensity", 0))
                delta += ACCUMULATION[WARMTH] * rel_intensity * 0.8

            depth = residue_profile.get("depth", {})
            if depth.get("texture_type") in ("warm", "bright"):
                depth_intensity = float(depth.get("intensity", 0))
                delta += ACCUMULATION[WARMTH] * depth_intensity * 0.5

        if witness_state:
            active_note = witness_state.get("active_note")
            if active_note and active_note.get("note_type") == "presence":
                delta += ACCUMULATION[WARMTH] * 0.8

        arousal = float(limbic.get("arousal", 0.5))
        valence = float(limbic.get("valence", 0.0))
        if valence > 0.25 and arousal > 0.40:
            delta += ACCUMULATION[WARMTH] * 0.3

        if delta > 0:
            self._deposit(WARMTH, delta, tick, "warmth_accumulation")

    def _process_fragility(self, conflict_state: dict, boundary_state: dict,
                           unspoken_state: dict, tick: int):
        delta = 0.0
        if conflict_state:
            effects = conflict_state.get("output_effects", [])
            if isinstance(effects, list) and "pause_visible" in effects:
                delta += ACCUMULATION[FRAGILITY] * 0.5

            highest = float(conflict_state.get("highest_intensity", 0))
            if highest > 0.75:
                delta += ACCUMULATION[FRAGILITY] * (highest - 0.75) * 1.5

        critical = boundary_state.get("critical", []) if boundary_state else []
        if critical:
            delta += ACCUMULATION[FRAGILITY] * len(critical) * 0.4

        if unspoken_state:
            sediment_feed = unspoken_state.get("sediment_feed", [])
            if sediment_feed:
                delta += ACCUMULATION[FRAGILITY] * 0.3 * min(len(sediment_feed), 2)

        if delta > 0:
            self._deposit(FRAGILITY, delta, tick, "fragility_marking")

    # ------------------------------------------------------------------
    # Cross-layer effects
    # ------------------------------------------------------------------

    def _apply_cross_layer_effects(self, tick: int):
        tension = self._current.get(TENSION, 0)
        warmth = self._current.get(WARMTH, 0)

        if tension > TENSION_TRUST_EROSION_THRESHOLD:
            erosion = TENSION_TRUST_EROSION_RATE * (tension - TENSION_TRUST_EROSION_THRESHOLD)
            self._deposit(TRUST, -erosion, tick, "tension_erodes_trust",
                         f"tension:{tension:.2f}")

        if warmth > WARMTH_TRUST_BUILD_THRESHOLD:
            build = WARMTH_TRUST_BUILD_RATE * (warmth - WARMTH_TRUST_BUILD_THRESHOLD)
            self._deposit(TRUST, build, tick, "warmth_builds_trust",
                         f"warmth:{warmth:.2f}")

    # ------------------------------------------------------------------
    # Behavioral hints
    # ------------------------------------------------------------------

    def _compute_behavioral_hints(self) -> dict:
        hints = {}
        tension = self._current.get(TENSION, 0)
        fragility = self._current.get(FRAGILITY, 0)
        warmth = self._current.get(WARMTH, 0)
        familiarity = self._current.get(FAMILIARITY, 0)
        trust = self._current.get(TRUST, 0)

        if fragility > FRAGILITY_PROTECTOR_THRESHOLD:
            hints["protector_baseline_boost"] = round(
                FRAGILITY_PROTECTOR_BOOST * fragility, 3)

        if tension > TENSION_PROTECTOR_THRESHOLD:
            hints["protector_baseline_boost"] = (
                hints.get("protector_baseline_boost", 0)
                + round(TENSION_PROTECTOR_BOOST * tension, 3)
            )

        relationship_health = self._compute_health()
        if relationship_health > RELATIONSHIP_HEALTH_THRESHOLD:
            hints["tom_confidence_ceiling_raise"] = 0.08
            hints["relational_openness"] = True
            hints["protector_baseline_boost"] = max(
                0.0, hints.get("protector_baseline_boost", 0) - 0.10)

        if familiarity > 0.60:
            hints["familiar_relational_context"] = True
            hints["relational_salience_reduce"] = 0.05

        if tension > 0.55:
            hints["relational_careful_tone"] = True

        return hints

    def _compute_health(self) -> float:
        trust = self._current.get(TRUST, 0)
        warmth = self._current.get(WARMTH, 0)
        tension = self._current.get(TENSION, 0)
        fragility = self._current.get(FRAGILITY, 0)
        health = (trust * 0.45 + warmth * 0.35) - (tension * 0.12 + fragility * 0.08)
        return round(max(0.0, min(1.0, health)), 4)

    # ------------------------------------------------------------------
    # Deposit and decay
    # ------------------------------------------------------------------

    def _deposit(self, layer: str, delta: float, tick: int,
                 event_type: str, source: str = ""):
        now = datetime.now(MDT).isoformat(timespec="seconds")
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT id, value, deposit_count FROM relational_sediment WHERE layer = ?",
                    (layer,)
                ).fetchone()
                if not row:
                    return
                lid, cur_value, dep_count = row
                new_value = round(max(0.0, min(1.0, cur_value + delta)), 4)

                conn.execute("""
                    UPDATE relational_sediment
                    SET value = ?, deposit_count = ?,
                        last_deposit_tick = ?, last_timestamp = ?
                    WHERE id = ?
                """, (new_value, dep_count + 1, tick, now, lid))

                if abs(delta) > 0.005:
                    conn.execute("""
                        INSERT INTO sediment_events
                        (tick, timestamp, layer, delta, new_value, event_type, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (tick, now, layer, round(delta, 4), new_value,
                          event_type, source[:150]))
                conn.commit()
                self._current[layer] = new_value
        except Exception as e:
            logger.debug("RelationalSediment: deposit failed — %s", e)

    def _apply_decay(self, tick: int):
        for layer in ALL_LAYERS:
            cur = self._current.get(layer, DEFAULT_SEDIMENT[layer])
            decayed = max(0.0, cur - DECAY[layer])
            if abs(decayed - cur) > 0.0001:
                self._deposit(layer, -DECAY[layer], tick, "decay")

    def _sync_from_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    "SELECT layer, value FROM relational_sediment"
                ).fetchall()
                for row in rows:
                    self._current[row[0]] = row[1]
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_profile(self) -> dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT layer, value, deposit_count, last_deposit_tick
                    FROM relational_sediment
                """).fetchall()
                return {
                    r[0]: {"value": round(r[1], 4), "deposit_count": r[2],
                            "last_deposit_tick": r[3]}
                    for r in rows
                }
        except Exception:
            return {l: {"value": DEFAULT_SEDIMENT[l]} for l in ALL_LAYERS}

    def get_state(self) -> dict:
        profile = self.get_profile()
        health = self._compute_health()
        hints = self._compute_behavioral_hints()
        try:
            with sqlite3.connect(self.db_path) as conn:
                total_events = conn.execute(
                    "SELECT COUNT(*) FROM sediment_events"
                ).fetchone()[0]
        except Exception:
            total_events = 0

        return {
            "version": VERSION,
            "profile": {l: round(v["value"], 3) for l, v in profile.items()},
            "relationship_health": health,
            "behavioral_hints": hints,
            "total_events": total_events,
            "cross_layer_active": {
                "tension_eroding_trust": self._current.get(TENSION, 0) > TENSION_TRUST_EROSION_THRESHOLD,
                "warmth_building_trust": self._current.get(WARMTH, 0) > WARMTH_TRUST_BUILD_THRESHOLD,
            },
        }
