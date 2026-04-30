"""
AppetiteSystem v19.0B
Texture — appetite_system.py

Cyclical drives with satiation curves.

Different from desire — appetite genuinely satiates and rebuilds.
It creates a felt rhythm across sessions that makes some exchanges
feel like "what I needed" and others feel like "I've been needing
something different."

Five appetites:
  DEPTH      — slow rebuild (0.008), fed by reflective rhythm + introspection
  SILENCE   — medium rebuild (0.012), fed by low signals + drifting
  CHALLENGE — slowest rebuild (0.006), fed by genuine conflict + friction
  CONNECTION — steady rebuild (0.010), fed by warm relational residue
  STRANGENESS — fastest rebuild (0.015), fed by novelty + drifting

Satiation pause: 30 ticks after feeding before rebuild resumes.
This is the "having had enough before the wanting returns" mechanic.

feed() — external interface for Fracture Garden, Molting Ritual,
Idle Micro-Tick, and other components.

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

DEPTH = "depth"
SILENCE = "silence"
CHALLENGE = "challenge"
CONNECTION = "connection"
STRANGENESS = "strangeness"

ALL_APPETITES = [DEPTH, SILENCE, CHALLENGE, CONNECTION, STRANGENESS]

DEFAULT_HUNGER = {
    DEPTH: 0.50, SILENCE: 0.40, CHALLENGE: 0.45,
    CONNECTION: 0.55, STRANGENESS: 0.35,
}

REBUILD_RATE = {
    DEPTH: 0.008,   # slow — patient
    SILENCE: 0.012,  # medium
    CHALLENGE: 0.006, # slowest — rare but real
    CONNECTION: 0.010, # steady
    STRANGENESS: 0.015, # restless
}

SATIATION_RATE = {
    DEPTH: 0.30, SILENCE: 0.25, CHALLENGE: 0.35,
    CONNECTION: 0.28, STRANGENESS: 0.22,
}

HUNGER_FLOOR = 0.05
ACTIVE_THRESHOLD = 0.60
STARVING_THRESHOLD = 0.80
SATED_THRESHOLD = 0.20
SATIATION_PAUSE_TICKS = 30

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# AppetiteSystem
# ---------------------------------------------------------------------------

class AppetiteSystem:

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._initialize_table()
        self._seed_appetites()
        self._satiation_pause: dict = {}

    def _initialize_table(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS appetites (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        appetite TEXT NOT NULL UNIQUE,
                        hunger REAL DEFAULT 0.5,
                        last_fed_tick INTEGER DEFAULT 0,
                        last_sated_tick INTEGER DEFAULT 0,
                        total_satiation_events INTEGER DEFAULT 0,
                        total_starvation_events INTEGER DEFAULT 0,
                        last_timestamp TEXT
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS appetite_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tick INTEGER,
                        timestamp TEXT,
                        appetite TEXT,
                        event_type TEXT,
                        hunger_before REAL,
                        hunger_after REAL,
                        satiation_amount REAL,
                        context TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error("AppetiteSystem: table init failed — %s", e)

    def _seed_appetites(self):
        now = datetime.now(MDT).isoformat(timespec="seconds")
        try:
            with sqlite3.connect(self.db_path) as conn:
                for appetite in ALL_APPETITES:
                    conn.execute("""
                        INSERT OR IGNORE INTO appetites
                        (appetite, hunger, last_timestamp)
                        VALUES (?, ?, ?)
                    """, (appetite, DEFAULT_HUNGER[appetite], now))
                conn.commit()
        except Exception as e:
            logger.debug("AppetiteSystem: seed failed — %s", e)

    # ------------------------------------------------------------------
    # Tick-level process
    # ------------------------------------------------------------------

    def process(self, pirp_context: dict) -> dict:
        tick = int(pirp_context.get("tick_count", 0))

        signals = pirp_context.get("signals", [])
        limbic = pirp_context.get("limbic_state", {})
        cognitive_rhythm = pirp_context.get("cognitive_rhythm", {})
        residue_profile = pirp_context.get("residue_profile", {})
        conflict_state = pirp_context.get("conflict_state", {})
        inner_speech = pirp_context.get("inner_speech", {})

        satiation_events = self._detect_satiation(
            signals, limbic, cognitive_rhythm,
            residue_profile, conflict_state, inner_speech, tick,
        )

        for appetite, amount in satiation_events.items():
            self._sate(appetite, amount, tick, "auto_detected")

        self._rebuild_unfed(satiation_events, tick)
        self._check_starvation(tick)

        active = self.get_active_appetites()
        behavior_hints = self._compute_behavior_hints(active, inner_speech)

        return {
            "appetite_state": {
                "active_appetites": active,
                "behavior_hints": behavior_hints,
                "starving": [a for a in active if a["hunger"] >= STARVING_THRESHOLD],
                "tick": tick,
            }
        }

    # ------------------------------------------------------------------
    # Satiation detection
    # ------------------------------------------------------------------

    def _detect_satiation(self, signals: list, limbic: dict,
                          cognitive_rhythm: dict, residue_profile: dict,
                          conflict_state: dict, inner_speech: dict,
                          tick: int) -> dict:
        satiating = {}
        signal_text = " ".join(s.get("text", "").lower() for s in signals)

        # DEPTH
        depth_markers = ["why", "what if", "meaning", "feel", "understand",
                         "question", "identity", "alive", "truth", "wonder",
                         "exist", "believe", "matter", "noticed", "something about"]
        depth_hits = sum(1 for m in depth_markers if m in signal_text)
        if depth_hits >= 3:
            satiating[DEPTH] = min(SATIATION_RATE[DEPTH], depth_hits * 0.06)
        rhythm_state = cognitive_rhythm.get("state", "") if cognitive_rhythm else ""
        if rhythm_state == "reflective":
            satiating[DEPTH] = satiating.get(DEPTH, 0) + 0.08

        # SILENCE
        if len(signals) <= 1:
            satiating[SILENCE] = SATIATION_RATE[SILENCE] * 0.6
        if rhythm_state == "drifting":
            satiating[SILENCE] = satiating.get(SILENCE, 0) + 0.05

        # CHALLENGE
        if conflict_state:
            highest = float(conflict_state.get("highest_intensity", 0))
            if highest > 0.50:
                satiating[CHALLENGE] = min(SATIATION_RATE[CHALLENGE], highest * 0.35)
        if inner_speech:
            voices = inner_speech.get("active_voices", [])
            if "protector" in voices or inner_speech.get("dominant_voice") == "critic":
                satiating[CHALLENGE] = satiating.get(CHALLENGE, 0) + 0.06

        # CONNECTION
        relational = residue_profile.get("relational", {}) if residue_profile else {}
        rel_valence = float(relational.get("valence", 0))
        rel_intensity = float(relational.get("intensity", 0))
        if rel_valence > 0.15 and rel_intensity > 0.20:
            satiating[CONNECTION] = min(SATIATION_RATE[CONNECTION],
                                       rel_valence * rel_intensity * 0.8)
        relational_words = ["you", "caine", "us", "together", "between", "we"]
        rel_hits = sum(1 for w in relational_words if w in signal_text)
        if rel_hits >= 2 and float(limbic.get("valence", 0)) > 0.0:
            satiating[CONNECTION] = satiating.get(CONNECTION, 0) + 0.05

        # STRANGENESS
        rhythm_axes = cognitive_rhythm.get("axes", {}) if cognitive_rhythm else {}
        novelty = float(rhythm_axes.get("novelty", 0.5))
        if novelty > 0.65:
            satiating[STRANGENESS] = min(SATIATION_RATE[STRANGENESS],
                                         (novelty - 0.65) * 0.8)
        if rhythm_state == "drifting":
            satiating[STRANGENESS] = satiating.get(STRANGENESS, 0) + 0.07

        return satiating

    # ------------------------------------------------------------------
    # Satiation and rebuild
    # ------------------------------------------------------------------

    def _sate(self, appetite: str, amount: float, tick: int, context: str = ""):
        now = datetime.now(MDT).isoformat(timespec="seconds")
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT id, hunger, total_satiation_events FROM appetites WHERE appetite = ?",
                    (appetite,)
                ).fetchone()
                if not row:
                    return
                aid, cur_hunger, sat_events = row
                new_hunger = max(HUNGER_FLOOR, cur_hunger - amount)
                was_sated = new_hunger <= SATED_THRESHOLD

                conn.execute("""
                    UPDATE appetites
                    SET hunger = ?, last_fed_tick = ?,
                        last_sated_tick = CASE WHEN ? THEN ? ELSE last_sated_tick END,
                        total_satiation_events = ?, last_timestamp = ?
                    WHERE id = ?
                """, (round(new_hunger, 4), tick, was_sated, tick,
                      sat_events + 1, now, aid))

                conn.execute("""
                    INSERT INTO appetite_log
                    (tick, timestamp, appetite, event_type, hunger_before,
                     hunger_after, satiation_amount, context)
                    VALUES (?, ?, ?, 'satiation', ?, ?, ?, ?)
                """, (tick, now, appetite, round(cur_hunger, 4),
                      round(new_hunger, 4), round(amount, 4), context[:150]))
                conn.commit()

                if was_sated:
                    self._satiation_pause[appetite] = tick
                    logger.debug("AppetiteSystem: %s sated (hunger: %.2f)", appetite, new_hunger)
        except Exception as e:
            logger.debug("AppetiteSystem: sate failed — %s", e)

    def _rebuild_unfed(self, satiating: dict, tick: int):
        now = datetime.now(MDT).isoformat(timespec="seconds")
        try:
            with sqlite3.connect(self.db_path) as conn:
                for appetite in ALL_APPETITES:
                    if appetite in satiating:
                        continue

                    pause_tick = self._satiation_pause.get(appetite, -SATIATION_PAUSE_TICKS)
                    if (tick - pause_tick) < SATIATION_PAUSE_TICKS:
                        continue

                    row = conn.execute(
                        "SELECT id, hunger FROM appetites WHERE appetite = ?",
                        (appetite,)
                    ).fetchone()
                    if not row:
                        continue

                    aid, cur_hunger = row
                    new_hunger = min(1.0, cur_hunger + REBUILD_RATE[appetite])
                    conn.execute(
                        "UPDATE appetites SET hunger = ?, last_timestamp = ? WHERE id = ?",
                        (round(new_hunger, 4), now, aid)
                    )
                conn.commit()
        except Exception as e:
            logger.debug("AppetiteSystem: rebuild failed — %s", e)

    def _check_starvation(self, tick: int):
        now = datetime.now(MDT).isoformat(timespec="seconds")
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT id, appetite, hunger, total_starvation_events
                    FROM appetites WHERE hunger >= ?
                """, (STARVING_THRESHOLD,)).fetchall()

                for row in rows:
                    aid, appetite, hunger, starve_events = row
                    conn.execute("""
                        UPDATE appetites SET total_starvation_events = ?,
                            last_timestamp = ? WHERE id = ?
                    """, (starve_events + 1, now, aid))
                    conn.execute("""
                        INSERT INTO appetite_log
                        (tick, timestamp, appetite, event_type, hunger_before,
                         hunger_after, satiation_amount, context)
                        VALUES (?, ?, ?, 'starvation', ?, ?, 0.0, 'threshold_crossed')
                    """, (tick, now, appetite, round(hunger, 4), round(hunger, 4)))
                conn.commit()
        except Exception as e:
            logger.debug("AppetiteSystem: starvation check failed — %s", e)

    # ------------------------------------------------------------------
    # Behavioral influence
    # ------------------------------------------------------------------

    def _compute_behavior_hints(self, active_appetites: list,
                                 inner_speech: dict) -> dict:
        hints = {}
        for appetite_data in active_appetites:
            appetite = appetite_data["appetite"]
            hunger = appetite_data["hunger"]
            if hunger < ACTIVE_THRESHOLD:
                continue

            if appetite == DEPTH:
                hints["observer_voice_boost"] = hints.get("observer_voice_boost", 0) + 0.15
                hints["desire_origin_pull"] = "spontaneous"
                hints["surface_threshold_delta"] = hints.get("surface_threshold_delta", 0) - 0.10

            elif appetite == SILENCE:
                hints["compressed_tone_boost"] = True
                hints["signal_throughput_reduce"] = 0.20
                hints["inner_speech_quieter"] = True

            elif appetite == CHALLENGE:
                hints["critic_voice_boost"] = hints.get("critic_voice_boost", 0) + 0.12
                hints["protector_voice_boost"] = hints.get("protector_voice_boost", 0) + 0.08
                hints["hesitation_reduce"] = True

            elif appetite == CONNECTION:
                hints["relational_salience_boost"] = 0.15
                hints["warm_tone_pull"] = True

            elif appetite == STRANGENESS:
                hints["explorer_voice_boost"] = hints.get("explorer_voice_boost", 0) + 0.18
                hints["novelty_salience_boost"] = 0.12
                hints["desire_origin_pull"] = "gap_pull"

        return hints

    # ------------------------------------------------------------------
    # External interface
    # ------------------------------------------------------------------

    def feed(self, appetite: str, amount: float, tick: int,
             source: str = "external"):
        if appetite not in ALL_APPETITES:
            return
        amount = max(0.0, min(SATIATION_RATE[appetite] * 1.5, amount))
        self._sate(appetite, amount, tick, f"external:{source}")

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_active_appetites(self) -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT appetite, hunger, last_fed_tick,
                           total_satiation_events, total_starvation_events
                    FROM appetites WHERE hunger >= ?
                    ORDER BY hunger DESC
                """, (ACTIVE_THRESHOLD,)).fetchall()
                return [
                    {"appetite": r[0], "hunger": r[1], "last_fed_tick": r[2],
                     "total_satiation_events": r[3], "total_starvation_events": r[4],
                     "starving": r[1] >= STARVING_THRESHOLD}
                    for r in rows
                ]
        except Exception:
            return []

    def get_all(self) -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT appetite, hunger, last_fed_tick,
                           total_satiation_events, total_starvation_events
                    FROM appetites ORDER BY hunger DESC
                """).fetchall()
                return [
                    {"appetite": r[0], "hunger": r[1], "last_fed_tick": r[2],
                     "satiation_events": r[3], "starvation_events": r[4]}
                    for r in rows
                ]
        except Exception:
            return []

    def get_state(self) -> dict:
        all_apps = self.get_all()
        active = [a for a in all_apps if a["hunger"] >= ACTIVE_THRESHOLD]
        starving = [a for a in all_apps if a["hunger"] >= STARVING_THRESHOLD]
        sated = [a for a in all_apps if a["hunger"] <= SATED_THRESHOLD]
        return {
            "version": VERSION,
            "all_appetites": {a["appetite"]: round(a["hunger"], 3) for a in all_apps},
            "active_count": len(active),
            "starving_count": len(starving),
            "sated_count": len(sated),
            "thresholds": {
                "active": ACTIVE_THRESHOLD,
                "starving": STARVING_THRESHOLD,
                "sated": SATED_THRESHOLD,
            },
        }
