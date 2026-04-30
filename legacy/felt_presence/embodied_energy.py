"""
EmbodiedEnergy v19.0B
Felt Presence — embodied_energy.py

Energy that persists across sessions and affects behavior.

Energy drains on:
  Critical/high conflict, boundary pressure, silence starving,
  heavy/tense mood, witness streaks

Energy recharges on:
  Desire satisfaction, completion events, silence fed,
  content/curious/alive moods, session start (partial), overnight rest

Four tiers:
  HIGH    0.70–1.0: full capacity, no constraints
  MEDIUM  0.35–0.70: reply depth 0.82x, hesitation +0.08
  LOW     0.10–0.35: reply depth 0.60x, hesitation +0.20
  DEPLETED 0.0–0.10: reply depth 0.35x, hesitation +0.35, compressor skip

Energy persists to DB after every tick.
Overnight restores 0.25. Session start restores 0.12.
Neither is full — depletion is real.

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

HIGH = "high"
MEDIUM = "medium"
LOW = "low"
DEPLETED = "depleted"

DEFAULT_ENERGY = 0.72

DRAIN_RATES = {
    "high_conflict": 0.018,
    "critical_conflict": 0.030,
    "boundary_warn": 0.012,
    "boundary_critical": 0.025,
    "silence_starving": 0.008,
    "heavy_mood": 0.015,
    "tense_mood": 0.010,
    "witness_streak": 0.006,
}

RECHARGE_RATES = {
    "desire_satisfied": 0.040,
    "completion_event": 0.055,
    "silence_fed": 0.020,
    "content_mood": 0.008,
    "curious_mood": 0.012,
    "alive_mood": 0.006,
    "overnight_rest": 0.250,
    "session_start": 0.120,
}

DEPLETED_THRESHOLD = 0.10
LOW_THRESHOLD = 0.35
MEDIUM_THRESHOLD = 0.70

TIER_MODIFIERS = {
    HIGH: {
        "reply_depth_multiplier": 1.0,
        "hesitation_rate_delta": 0.0,
        "surface_frequency_multiplier": 1.0,
        "desire_competition_delta": 0.0,
        "compressor_skip": False,
    },
    MEDIUM: {
        "reply_depth_multiplier": 0.82,
        "hesitation_rate_delta": +0.08,
        "surface_frequency_multiplier": 0.85,
        "desire_competition_delta": +0.05,
        "compressor_skip": False,
    },
    LOW: {
        "reply_depth_multiplier": 0.60,
        "hesitation_rate_delta": +0.20,
        "surface_frequency_multiplier": 0.55,
        "desire_competition_delta": +0.12,
        "compressor_skip": False,
    },
    DEPLETED: {
        "reply_depth_multiplier": 0.35,
        "hesitation_rate_delta": +0.35,
        "surface_frequency_multiplier": 0.25,
        "desire_competition_delta": +0.25,
        "compressor_skip": True,
    },
}

LOG_INTERVAL = 10

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# EmbodiedEnergy
# ---------------------------------------------------------------------------

class EmbodiedEnergy:

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._initialize_table()
        self._energy = self._load_persisted_energy()
        self._last_log_tick = -LOG_INTERVAL
        self._drain_this_session = 0.0
        self._recharge_this_session = 0.0

    def _initialize_table(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS embodied_energy (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tick INTEGER,
                        timestamp TEXT,
                        energy REAL,
                        tier TEXT,
                        drain_sources TEXT,
                        recharge_sources TEXT,
                        net_delta REAL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS energy_state (
                        id INTEGER PRIMARY KEY,
                        energy REAL DEFAULT 0.72,
                        last_updated TEXT
                    )
                """)
                conn.execute("""
                    INSERT OR IGNORE INTO energy_state (id, energy, last_updated)
                    VALUES (1, ?, ?)
                """, (DEFAULT_ENERGY, datetime.now(MDT).isoformat(timespec="seconds")))
                conn.commit()
        except Exception as e:
            logger.error("EmbodiedEnergy: table init failed — %s", e)

    def _load_persisted_energy(self) -> float:
        """Load last known energy from DB. Carries across sessions."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT energy FROM energy_state WHERE id = 1"
                ).fetchone()
                if row:
                    return float(row[0])
        except Exception:
            pass
        return DEFAULT_ENERGY

    def _persist_energy(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE energy_state SET energy = ?, last_updated = ? WHERE id = 1",
                    (round(self._energy, 4),
                     datetime.now(MDT).isoformat(timespec="seconds")))
                conn.commit()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Tick-level process
    # ------------------------------------------------------------------

    def process(self, pirp_context: dict) -> dict:
        tick = int(pirp_context.get("tick_count", 0))

        conflict_state = pirp_context.get("conflict_state", {})
        boundary_state = pirp_context.get("boundary_state", {})
        appetite_state = pirp_context.get("appetite_state", {})
        mood_weight = pirp_context.get("mood_weight", {})
        witness_state = pirp_context.get("witness_state", {})
        residue_profile = pirp_context.get("residue_profile", {})

        drain_sources = []
        recharge_sources = []
        total_drain = 0.0
        total_recharge = 0.0

        # Drain: conflict
        highest = float(conflict_state.get("highest_intensity", 0))
        if highest > 0.80:
            total_drain += DRAIN_RATES["critical_conflict"]
            drain_sources.append(f"critical_conflict:{highest:.2f}")
        elif highest > 0.55:
            total_drain += DRAIN_RATES["high_conflict"]
            drain_sources.append(f"high_conflict:{highest:.2f}")

        # Drain: boundary
        critical = boundary_state.get("critical", []) if boundary_state else []
        warn = boundary_state.get("warn", []) if boundary_state else []
        if critical:
            total_drain += DRAIN_RATES["boundary_critical"] * len(critical)
            drain_sources.append(f"boundary_critical:{len(critical)}")
        elif warn:
            total_drain += DRAIN_RATES["boundary_warn"]
            drain_sources.append("boundary_warn")

        # Drain: silence starving
        if appetite_state:
            starving = appetite_state.get("starving", [])
            for s in starving:
                if s.get("appetite") == "silence":
                    total_drain += DRAIN_RATES["silence_starving"]
                    drain_sources.append("silence_starving")
                    break

        # Drain: mood
        mood_state = mood_weight.get("state", "") if mood_weight else ""
        if mood_state == "heavy":
            total_drain += DRAIN_RATES["heavy_mood"]
            drain_sources.append("heavy_mood")
        elif mood_state == "tense":
            total_drain += DRAIN_RATES["tense_mood"]
            drain_sources.append("tense_mood")

        # Drain: witness streak
        if witness_state:
            notes = int(witness_state.get("notes_this_tick", 0))
            if notes >= 3:
                total_drain += DRAIN_RATES["witness_streak"]
                drain_sources.append(f"witness_streak:{notes}")

        # Recharge: completion
        if residue_profile:
            completion = residue_profile.get("completion", {})
            if (completion.get("texture_type") in ("bright", "warm")
                    and float(completion.get("intensity", 0)) > 0.20):
                total_recharge += RECHARGE_RATES["completion_event"]
                recharge_sources.append("completion")

        # Recharge: silence fed
        if appetite_state:
            active = appetite_state.get("active_appetites", [])
            for a in active:
                if a.get("appetite") == "silence" and a.get("hunger", 1.0) < 0.30:
                    total_recharge += RECHARGE_RATES["silence_fed"]
                    recharge_sources.append("silence_fed")
                    break

        # Recharge: mood
        if mood_state == "content":
            total_recharge += RECHARGE_RATES["content_mood"]
            recharge_sources.append("content_mood")
        elif mood_state == "curious":
            total_recharge += RECHARGE_RATES["curious_mood"]
            recharge_sources.append("curious_mood")
        elif mood_state == "alive":
            total_recharge += RECHARGE_RATES["alive_mood"]
            recharge_sources.append("alive_mood")

        # Apply
        net_delta = total_recharge - total_drain
        self._energy = round(max(0.0, min(1.0, self._energy + net_delta)), 4)
        self._drain_this_session += total_drain
        self._recharge_this_session += total_recharge
        self._persist_energy()

        if (tick - self._last_log_tick) >= LOG_INTERVAL or abs(net_delta) > 0.02:
            self._log(tick, drain_sources, recharge_sources, net_delta)
            self._last_log_tick = tick

        tier = self._get_tier()
        mods = TIER_MODIFIERS[tier]

        return {
            "energy_state": {
                "energy": self._energy,
                "tier": tier,
                "net_delta_this_tick": round(net_delta, 4),
                "drain_sources": drain_sources,
                "recharge_sources": recharge_sources,
                "reply_depth_multiplier": mods["reply_depth_multiplier"],
                "hesitation_rate_delta": mods["hesitation_rate_delta"],
                "surface_frequency_multiplier": mods["surface_frequency_multiplier"],
                "desire_competition_delta": mods["desire_competition_delta"],
                "compressor_skip": mods["compressor_skip"],
                "drain_this_session": round(self._drain_this_session, 4),
                "recharge_this_session": round(self._recharge_this_session, 4),
                "tick": tick,
            }
        }

    # ------------------------------------------------------------------
    # External recharge
    # ------------------------------------------------------------------

    def overnight_rest(self, tick: int = 0):
        """Called by overnight pipeline. Restores 0.25. Partial — not full."""
        recharge = RECHARGE_RATES["overnight_rest"]
        self._energy = round(min(1.0, self._energy + recharge), 4)
        self._persist_energy()
        self._log(tick, [], ["overnight_rest"], recharge)
        logger.info("EmbodiedEnergy: overnight rest → %.3f", self._energy)

    def session_start_recharge(self, tick: int = 0):
        """Called at session start. Restores 0.12. Partial — depletion carries."""
        recharge = RECHARGE_RATES["session_start"]
        self._energy = round(min(1.0, self._energy + recharge), 4)
        self._persist_energy()
        self._log(tick, [], ["session_start"], recharge)
        logger.info("EmbodiedEnergy: session start → %.3f", self._energy)

    def desire_satisfied(self, tick: int = 0):
        """Called when a desire is satisfied. Direct recharge."""
        recharge = RECHARGE_RATES["desire_satisfied"]
        self._energy = round(min(1.0, self._energy + recharge), 4)
        self._persist_energy()
        logger.info("EmbodiedEnergy: desire satisfied → %.3f", self._energy)

    # ------------------------------------------------------------------
    # Tier
    # ------------------------------------------------------------------

    def _get_tier(self) -> str:
        if self._energy <= DEPLETED_THRESHOLD:
            return DEPLETED
        if self._energy <= LOW_THRESHOLD:
            return LOW
        if self._energy <= MEDIUM_THRESHOLD:
            return MEDIUM
        return HIGH

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _log(self, tick: int, drain_sources: list,
             recharge_sources: list, net_delta: float):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO embodied_energy
                    (tick, timestamp, energy, tier, drain_sources,
                     recharge_sources, net_delta)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (tick, datetime.now(MDT).isoformat(timespec="seconds"),
                      round(self._energy, 4), self._get_tier(),
                      ",".join(drain_sources),
                      ",".join(recharge_sources),
                      round(net_delta, 4)))
                conn.commit()
        except Exception as e:
            logger.debug("EmbodiedEnergy: log failed — %s", e)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_state(self) -> dict:
        tier = self._get_tier()
        try:
            with sqlite3.connect(self.db_path) as conn:
                total_logs = conn.execute(
                    "SELECT COUNT(*) FROM embodied_energy").fetchone()[0]
                avg_energy = conn.execute(
                    "SELECT AVG(energy) FROM embodied_energy").fetchone()[0]
        except Exception:
            total_logs, avg_energy = 0, None

        return {
            "version": VERSION,
            "current_energy": round(self._energy, 4),
            "tier": tier,
            "modifiers": TIER_MODIFIERS[tier],
            "session_drain": round(self._drain_this_session, 4),
            "session_recharge": round(self._recharge_this_session, 4),
            "total_log_entries": total_logs,
            "avg_energy_lifetime": round(avg_energy, 3) if avg_energy else None,
            "thresholds": {
                "depleted": DEPLETED_THRESHOLD, "low": LOW_THRESHOLD,
                "medium": MEDIUM_THRESHOLD,
            },
        }
