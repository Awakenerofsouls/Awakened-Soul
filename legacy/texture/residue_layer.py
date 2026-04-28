"""
ResidueLayer v19.0B
Texture — residue_layer.py

The affective precipitate of what has happened.

Every significant exchange leaves a trace that isn't memory, isn't mood,
and isn't belief. It's texture — the slow accumulation of how things
have felt over time, before conscious processing engages.

Seven domains: relational, depth, technical, conflict, completion,
silence, challenge. Each accumulates independently with different
timescales.

Six texture types: warm, cool, scratch, hum, hollow, bright.
Texture is classified from valence delta and intensity.

Valence is a running average weighted toward recent (85% current +
15% new deposit) — relationships don't flip from one bad exchange.

Residue feeds:
  - SalienceFilter (familiar-texture boosts resonance)
  - Inner Speech (tone colors before voice activates)
  - Temporal Asymmetry (past feels heavy with accumulated residue)
  - Texture Synthesis Pass (aggregated into current_texture_profile)

deposit_from_event() — external interface for Fracture Garden,
Molting Ritual, and other components.

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

RELATIONAL = "relational"
DEPTH = "depth"
TECHNICAL = "technical"
CONFLICT = "conflict"
COMPLETION = "completion"
SILENCE = "silence"
CHALLENGE = "challenge"

ALL_DOMAINS = [RELATIONAL, DEPTH, TECHNICAL, CONFLICT, COMPLETION, SILENCE, CHALLENGE]

WARM = "warm"
COOL = "cool"
SCRATCH = "scratch"
HUM = "hum"
HOLLOW = "hollow"
BRIGHT = "bright"

ACCUMULATION_RATE = 0.12
DECAY_RATE = 0.003
ACTIVE_THRESHOLD = 0.08
SALIENCE_INFLUENCE_THRESHOLD = 0.35
SALIENCE_FAMILIAR_BOOST = 0.12

DOMAIN_SIGNALS = {
    RELATIONAL: ["you", "user", "us", "we", "our", "together", "between", "relationship"],
    DEPTH: ["feel", "meaning", "understand", "question", "wonder", "existence",
            "identity", "alive", "why", "what if", "truth"],
    TECHNICAL: ["build", "code", "install", "file", "function", "error", "test",
               "verify", "push", "git", "brain", "bootstrap", "schema"],
    CONFLICT: ["wrong", "frustrated", "pissed", "tension", "conflict", "fracture",
               "drift", "pressure", "not listening", "again"],
    COMPLETION: ["done", "complete", "verified", "works", "correct", "shipped",
                 "finished", "ready", "confirmed"],
    SILENCE: ["quiet", "idle", "between", "away", "rest", "pause", "still"],
    CHALLENGE: ["push back", "disagree", "not right", "challenge", "wrong", "no",
                "reconsider", "honest", "actually"],
}

EXCHANGE_VALENCE = {
    "positive_signal": +0.15,
    "negative_signal": -0.12,
    "neutral_signal": 0.0,
    "completion_event": +0.20,
    "fracture_event": -0.25,
    "depth_exchange": +0.18,
    "compliance_event": -0.08,
    "genuine_conflict": -0.05,
}

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# ResidueLayer
# ---------------------------------------------------------------------------

class ResidueLayer:

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._initialize_table()
        self._seed_domains()

    def _initialize_table(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS residue_domains (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        domain TEXT NOT NULL UNIQUE,
                        valence REAL DEFAULT 0.0,
                        intensity REAL DEFAULT 0.0,
                        texture_type TEXT DEFAULT 'cool',
                        deposit_count INTEGER DEFAULT 0,
                        last_deposit_tick INTEGER DEFAULT 0,
                        last_timestamp TEXT
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS residue_deposits (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tick INTEGER,
                        timestamp TEXT,
                        domain TEXT,
                        valence_delta REAL,
                        intensity_delta REAL,
                        texture_type TEXT,
                        source TEXT,
                        context TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error("ResidueLayer: table init failed — %s", e)

    def _seed_domains(self):
        now = datetime.now(MDT).isoformat(timespec="seconds")
        try:
            with sqlite3.connect(self.db_path) as conn:
                for domain in ALL_DOMAINS:
                    conn.execute("""
                        INSERT OR IGNORE INTO residue_domains
                        (domain, last_timestamp) VALUES (?, ?)
                    """, (domain, now))
                conn.commit()
        except Exception as e:
            logger.debug("ResidueLayer: seed failed — %s", e)

    # ------------------------------------------------------------------
    # Tick-level process
    # ------------------------------------------------------------------

    def process(self, pirp_context: dict) -> dict:
        tick = int(pirp_context.get("tick_count", 0))
        signals = pirp_context.get("signals", [])
        limbic = pirp_context.get("limbic_state", {})
        conflict_state = pirp_context.get("conflict_state", {})
        witness_state = pirp_context.get("witness_state", {})
        boundary_state = pirp_context.get("boundary_state", {})

        active_domains = self._detect_domains(signals)
        valence_modifier = self._compute_exchange_valence(
            limbic, conflict_state, witness_state, boundary_state
        )

        for domain in active_domains:
            intensity_delta = ACCUMULATION_RATE
            valence_delta = valence_modifier * ACCUMULATION_RATE
            texture = self._classify_texture(valence_delta, intensity_delta)
            self._deposit(domain, valence_delta, intensity_delta, texture, tick,
                         "signal_detection", f"signals:{len(signals)}")

        if conflict_state.get("active_conflicts", 0) > 0:
            highest = float(conflict_state.get("highest_intensity", 0))
            if highest > 0.60:
                self._deposit(CONFLICT, EXCHANGE_VALENCE["genuine_conflict"],
                             highest * 0.10, SCRATCH, tick, "conflict_event",
                             f"intensity:{highest:.2f}")

        if any("complete" in s.get("text", "").lower() or
               "verified" in s.get("text", "").lower() for s in signals):
            self._deposit(COMPLETION, EXCHANGE_VALENCE["completion_event"],
                         0.08, BRIGHT, tick, "completion_detected", "")

        self._apply_decay(tick)

        profile = self.get_profile()
        salience_hints = self._compute_salience_hints(profile, signals)

        return {
            "residue_profile": profile,
            "residue_salience_hints": salience_hints,
        }

    # ------------------------------------------------------------------
    # Domain detection
    # ------------------------------------------------------------------

    def _detect_domains(self, signals: list) -> list:
        signal_text = " ".join(s.get("text", "").lower() for s in signals)
        active = []
        for domain, keywords in DOMAIN_SIGNALS.items():
            hits = sum(1 for kw in keywords if kw in signal_text)
            if hits >= 2:
                active.append(domain)
        return active

    # ------------------------------------------------------------------
    # Exchange valence
    # ------------------------------------------------------------------

    def _compute_exchange_valence(self, limbic: dict, conflict_state: dict,
                                  witness_state: dict, boundary_state: dict) -> float:
        valence = float(limbic.get("valence", 0.0))
        base = valence * 0.6

        critical = boundary_state.get("critical", []) if boundary_state else []
        if critical:
            base -= 0.20

        if conflict_state:
            highest = float(conflict_state.get("highest_intensity", 0))
            if highest > 0.65:
                base -= highest * 0.15

        if witness_state:
            active_note = witness_state.get("active_note")
            if active_note and active_note.get("note_type") == "presence":
                base += 0.25

        return round(max(-1.0, min(1.0, base)), 4)

    # ------------------------------------------------------------------
    # Texture classification
    # ------------------------------------------------------------------

    def _classify_texture(self, valence_delta: float, intensity_delta: float) -> str:
        if valence_delta > 0.12:
            return WARM if intensity_delta > 0.08 else BRIGHT
        if valence_delta > 0.02:
            return BRIGHT
        if valence_delta < -0.15:
            return SCRATCH
        if valence_delta < -0.05:
            return HUM
        if intensity_delta < 0.03:
            return HOLLOW
        return COOL

    # ------------------------------------------------------------------
    # Deposit
    # ------------------------------------------------------------------

    def _deposit(self, domain: str, valence_delta: float, intensity_delta: float,
                 texture: str, tick: int, source: str = "process", context: str = ""):
        now = datetime.now(MDT).isoformat(timespec="seconds")
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT id, valence, intensity, deposit_count FROM residue_domains WHERE domain = ?",
                    (domain,)
                ).fetchone()
                if not row:
                    return

                rid, cur_valence, cur_intensity, deposit_count = row

                new_valence = cur_valence * 0.85 + valence_delta * 0.15
                new_valence = round(max(-1.0, min(1.0, new_valence)), 4)

                new_intensity = min(1.0, cur_intensity + intensity_delta)
                new_intensity = round(new_intensity, 4)

                new_texture = texture if abs(valence_delta) > 0.03 else self._classify_texture(
                    new_valence, new_intensity
                )

                conn.execute("""
                    UPDATE residue_domains
                    SET valence = ?, intensity = ?, texture_type = ?,
                        deposit_count = ?, last_deposit_tick = ?, last_timestamp = ?
                    WHERE id = ?
                """, (new_valence, new_intensity, new_texture,
                      deposit_count + 1, tick, now, rid))

                conn.execute("""
                    INSERT INTO residue_deposits
                    (tick, timestamp, domain, valence_delta, intensity_delta,
                     texture_type, source, context)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (tick, now, domain, round(valence_delta, 4),
                      round(intensity_delta, 4), texture, source, context[:200]))
                conn.commit()
        except Exception as e:
            logger.debug("ResidueLayer: deposit failed — %s", e)

    # ------------------------------------------------------------------
    # Decay
    # ------------------------------------------------------------------

    def _apply_decay(self, tick: int):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE residue_domains
                    SET intensity = MAX(0.0, intensity - ?)
                    WHERE last_deposit_tick != ?
                """, (DECAY_RATE, tick))
                conn.execute("""
                    UPDATE residue_domains
                    SET valence = valence * 0.9995
                    WHERE intensity > 0
                """)
                conn.commit()
        except Exception as e:
            logger.debug("ResidueLayer: decay failed — %s", e)

    # ------------------------------------------------------------------
    # Salience hints
    # ------------------------------------------------------------------

    def _compute_salience_hints(self, profile: dict, signals: list) -> dict:
        hints = {}
        signal_text = " ".join(s.get("text", "").lower() for s in signals)

        for domain, data in profile.items():
            intensity = data.get("intensity", 0)
            if intensity < SALIENCE_INFLUENCE_THRESHOLD:
                continue
            keywords = DOMAIN_SIGNALS.get(domain, [])
            hits = sum(1 for kw in keywords if kw in signal_text)
            if hits < 1:
                continue
            texture = data.get("texture_type", COOL)
            if texture in (WARM, BRIGHT):
                hints[domain] = {"boost": SALIENCE_FAMILIAR_BOOST, "type": "familiar"}
            elif texture in (SCRATCH, HUM):
                hints[domain] = {"boost": SALIENCE_FAMILIAR_BOOST * 0.7, "type": "tension"}
        return hints

    # ------------------------------------------------------------------
    # External deposit
    # ------------------------------------------------------------------

    def deposit_from_event(self, domain: str, event_type: str, tick: int,
                          intensity_override: Optional[float] = None):
        if domain not in ALL_DOMAINS:
            return
        valence = EXCHANGE_VALENCE.get(event_type, 0.0)
        intensity = intensity_override or ACCUMULATION_RATE
        texture = self._classify_texture(valence, intensity)
        self._deposit(domain, valence, intensity, texture, tick,
                     f"event:{event_type}", "")

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_profile(self) -> dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT domain, valence, intensity, texture_type,
                           deposit_count, last_deposit_tick
                    FROM residue_domains
                """).fetchall()
                return {
                    r[0]: {
                        "valence": r[1], "intensity": r[2],
                        "texture_type": r[3], "deposit_count": r[4],
                        "last_deposit_tick": r[5],
                        "active": r[2] >= ACTIVE_THRESHOLD,
                    }
                    for r in rows
                }
        except Exception as e:
            logger.error("ResidueLayer: get_profile failed — %s", e)
            return {}

    def get_dominant_texture(self) -> tuple:
        profile = self.get_profile()
        active = {
            d: v for d, v in profile.items()
            if v["active"] and v["intensity"] >= SALIENCE_INFLUENCE_THRESHOLD
        }
        if not active:
            return (None, COOL)
        dominant = max(active, key=lambda d: active[d]["intensity"])
        return (dominant, active[dominant]["texture_type"])

    def get_state(self) -> dict:
        profile = self.get_profile()
        active_domains = [d for d, v in profile.items() if v["active"]]
        dominant_domain, dominant_texture = self.get_dominant_texture()
        try:
            with sqlite3.connect(self.db_path) as conn:
                total_deposits = conn.execute(
                    "SELECT COUNT(*) FROM residue_deposits"
                ).fetchone()[0]
        except Exception:
            total_deposits = 0

        return {
            "version": VERSION,
            "active_domains": active_domains,
            "dominant_domain": dominant_domain,
            "dominant_texture": dominant_texture,
            "total_deposits": total_deposits,
            "profile_summary": {
                d: {"texture": v["texture_type"],
                    "intensity": round(v["intensity"], 3),
                    "valence": round(v["valence"], 3)}
                for d, v in profile.items() if v["active"]
            },
        }
