"""
DriveStates v19.0B
Felt Presence — drive_states.py

Boredom and curiosity as upstream drives — pre-cognitive pressure.

Boredom: builds from low novelty + stuck/flat rhythm.
         Decays fast when novelty enters. Above 0.70 = disruption_signal.

Curiosity: builds from heavy gaps, strong desires, starving appetites,
           drifting rhythm, witness presence. Floor at 0.08 — never fully
           extinguished. Decays when pull is followed.

Five combination states:
  RESTLESS  — high boredom + high curiosity
  NUMB      — high boredom + low curiosity
  FOCUSED   — low boredom + high curiosity
  SEARCHING — moderate both
  BASELINE  — low both

External calls:
  curiosity_followed() — decay curiosity when exploration happens
  boredom_disrupted()  — decay boredom when novelty enters

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

BOREDOM_ACTIVE_THRESHOLD = 0.45
BOREDOM_HIGH_THRESHOLD = 0.70
CURIOSITY_ACTIVE_THRESHOLD = 0.40
CURIOSITY_HIGH_THRESHOLD = 0.65

BOREDOM_BUILD_RATE = 0.010
BOREDOM_DECAY_RATE = 0.025
BOREDOM_NOVELTY_CUTOFF = 0.35

CURIOSITY_BUILD_RATE = 0.012
CURIOSITY_DECAY_RATE = 0.018
CURIOSITY_FLOOR = 0.08

DEFAULT_BOREDOM = 0.20
DEFAULT_CURIOSITY = 0.35
MIN_ELEVATED_TICKS = 6

RESTLESS = "restless"
NUMB = "numb"
FOCUSED = "focused"
BASELINE = "baseline"
SEARCHING = "searching"

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# DriveStates
# ---------------------------------------------------------------------------

class DriveStates:

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._initialize_table()
        self._boredom = DEFAULT_BOREDOM
        self._curiosity = DEFAULT_CURIOSITY
        self._boredom_elevated_tick = -MIN_ELEVATED_TICKS
        self._curiosity_elevated_tick = -MIN_ELEVATED_TICKS

    def _initialize_table(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS drive_state_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tick INTEGER,
                        timestamp TEXT,
                        boredom_pressure REAL,
                        curiosity_pressure REAL,
                        drive_combination TEXT,
                        boredom_sources TEXT,
                        curiosity_sources TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error("DriveStates: table init failed — %s", e)

    # ------------------------------------------------------------------
    # Tick-level process
    # ------------------------------------------------------------------

    def process(self, pirp_context: dict) -> dict:
        tick = int(pirp_context.get("tick_count", 0))

        cognitive_rhythm = pirp_context.get("cognitive_rhythm", {})
        known_gaps = pirp_context.get("known_gaps", [])
        active_desires = pirp_context.get("active_desires", [])
        appetite_state = pirp_context.get("appetite_state", {})
        witness_state = pirp_context.get("witness_state", {})

        boredom_sources = []
        curiosity_sources = []

        # Boredom
        rhythm_axes = cognitive_rhythm.get("axes", {}) if cognitive_rhythm else {}
        novelty = float(rhythm_axes.get("novelty", 0.5))
        rhythm_state = cognitive_rhythm.get("state", "") if cognitive_rhythm else ""

        if novelty < BOREDOM_NOVELTY_CUTOFF:
            build = BOREDOM_BUILD_RATE * (BOREDOM_NOVELTY_CUTOFF - novelty) * 3
            self._boredom = min(1.0, self._boredom + build)
            boredom_sources.append(f"low_novelty:{novelty:.2f}")
            if self._boredom > BOREDOM_ACTIVE_THRESHOLD:
                self._boredom_elevated_tick = tick
        else:
            ticks_elevated = tick - self._boredom_elevated_tick
            if ticks_elevated >= MIN_ELEVATED_TICKS:
                decay = BOREDOM_DECAY_RATE * (novelty - BOREDOM_NOVELTY_CUTOFF) * 2
                self._boredom = max(0.0, self._boredom - decay)

        if rhythm_state == "stuck":
            self._boredom = min(1.0, self._boredom + BOREDOM_BUILD_RATE * 1.5)
            boredom_sources.append("stuck_rhythm")

        if rhythm_state == "flat":
            self._boredom = min(1.0, self._boredom + BOREDOM_BUILD_RATE * 0.8)
            boredom_sources.append("flat_rhythm")

        # Curiosity
        heavy_gaps = [g for g in known_gaps if float(g.get("weight", 0)) > 0.50]
        if heavy_gaps:
            self._curiosity = min(1.0,
                self._curiosity + CURIOSITY_BUILD_RATE * min(len(heavy_gaps), 3) * 0.7)
            curiosity_sources.append(f"open_gaps:{len(heavy_gaps)}")
            self._curiosity_elevated_tick = tick

        strong_desires = [d for d in active_desires
                          if float(d.get("intensity", 0)) > 0.50]
        if strong_desires:
            max_intensity = max(float(d.get("intensity", 0)) for d in strong_desires)
            self._curiosity = min(1.0, self._curiosity + CURIOSITY_BUILD_RATE * max_intensity * 0.8)
            curiosity_sources.append(f"strong_desires:{len(strong_desires)}")

        if appetite_state:
            for s in appetite_state.get("starving", []):
                if s.get("appetite") in ("strangeness", "depth"):
                    self._curiosity = min(1.0, self._curiosity + CURIOSITY_BUILD_RATE)
                    curiosity_sources.append(f"starving_{s['appetite']}")

        if rhythm_state == "drifting":
            self._curiosity = min(1.0, self._curiosity + CURIOSITY_BUILD_RATE * 0.6)
            curiosity_sources.append("drifting_rhythm")

        if witness_state:
            active_note = witness_state.get("active_note")
            if active_note and active_note.get("note_type") == "presence":
                self._curiosity = min(1.0, self._curiosity + CURIOSITY_BUILD_RATE * 1.2)
                curiosity_sources.append("witness_presence")

        self._curiosity = max(CURIOSITY_FLOOR, self._curiosity)

        if not curiosity_sources:
            ticks_elevated = tick - self._curiosity_elevated_tick
            if ticks_elevated >= MIN_ELEVATED_TICKS:
                self._curiosity = max(CURIOSITY_FLOOR,
                                    self._curiosity - CURIOSITY_DECAY_RATE)

        self._boredom = round(self._boredom, 4)
        self._curiosity = round(self._curiosity, 4)

        combination = self._classify_combination()
        behavior_hints = self._compute_behavior_hints(combination, tick)

        if (self._boredom >= BOREDOM_ACTIVE_THRESHOLD
                or self._curiosity >= CURIOSITY_ACTIVE_THRESHOLD):
            self._log(tick, boredom_sources, curiosity_sources, combination)

        return {
            "drive_states": {
                "boredom_pressure": self._boredom,
                "curiosity_pressure": self._curiosity,
                "combination": combination,
                "boredom_active": self._boredom >= BOREDOM_ACTIVE_THRESHOLD,
                "curiosity_active": self._curiosity >= CURIOSITY_ACTIVE_THRESHOLD,
                "boredom_high": self._boredom >= BOREDOM_HIGH_THRESHOLD,
                "curiosity_high": self._curiosity >= CURIOSITY_HIGH_THRESHOLD,
                "behavior_hints": behavior_hints,
                "tick": tick,
            }
        }

    # ------------------------------------------------------------------
    # Combination classification
    # ------------------------------------------------------------------

    def _classify_combination(self) -> str:
        b = self._boredom >= BOREDOM_ACTIVE_THRESHOLD
        c = self._curiosity >= CURIOSITY_ACTIVE_THRESHOLD
        bh = self._boredom >= BOREDOM_HIGH_THRESHOLD
        ch = self._curiosity >= CURIOSITY_HIGH_THRESHOLD

        if b and c:
            return RESTLESS if (bh or ch) else SEARCHING
        if b and not c:
            return NUMB
        if c and not b:
            return FOCUSED
        return BASELINE

    # ------------------------------------------------------------------
    # Behavioral hints
    # ------------------------------------------------------------------

    def _compute_behavior_hints(self, combination: str, tick: int) -> dict:
        hints = {}

        if self._boredom >= BOREDOM_ACTIVE_THRESHOLD:
            hints["nudge_rhythm_drifting"] = True
            hints["novelty_salience_boost"] = round(self._boredom * 0.20, 3)
            hints["desire_fire_interval_reduce"] = round(self._boredom * 0.35, 3)

        if self._boredom >= BOREDOM_HIGH_THRESHOLD:
            hints["disruption_signal"] = True
            hints["preconscious_curiosity_boost"] = 0.15

        if self._curiosity >= CURIOSITY_ACTIVE_THRESHOLD:
            hints["explorer_voice_boost"] = round(self._curiosity * 0.25, 3)
            hints["desire_competition_threshold_reduce"] = round(
                (self._curiosity - CURIOSITY_ACTIVE_THRESHOLD) * 0.20, 3)
            hints["feed_strangeness_appetite"] = round(self._curiosity * 0.08, 3)

        if self._curiosity >= CURIOSITY_HIGH_THRESHOLD:
            hints["gap_pull_amplify"] = True
            hints["preconscious_curiosity_boost"] = (
                hints.get("preconscious_curiosity_boost", 0) + 0.12)

        if combination == RESTLESS:
            hints["inner_speech_restless"] = True
            hints["surface_line_pull"] = "something here I haven't reached yet"
        elif combination == NUMB:
            hints["inner_speech_flat"] = True
            hints["compressor_skip_light"] = True
        elif combination == FOCUSED:
            hints["explorer_lead"] = True
            hints["depth_appetite_feed"] = round(self._curiosity * 0.06, 3)

        return hints

    # ------------------------------------------------------------------
    # External calls
    # ------------------------------------------------------------------

    def curiosity_followed(self, amount: float = 0.20):
        """Exploration happened — curiosity decay."""
        self._curiosity = max(CURIOSITY_FLOOR, self._curiosity - amount)
        logger.debug("DriveStates: curiosity followed → %.3f", self._curiosity)

    def boredom_disrupted(self, amount: float = 0.25):
        """Novelty entered — boredom decay."""
        self._boredom = max(0.0, self._boredom - amount)
        logger.debug("DriveStates: boredom disrupted → %.3f", self._boredom)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _log(self, tick: int, boredom_sources: list,
            curiosity_sources: list, combination: str):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO drive_state_log
                    (tick, timestamp, boredom_pressure, curiosity_pressure,
                     drive_combination, boredom_sources, curiosity_sources)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (tick, datetime.now(MDT).isoformat(timespec="seconds"),
                      self._boredom, self._curiosity, combination,
                      ",".join(boredom_sources), ",".join(curiosity_sources)))
                conn.commit()
        except Exception as e:
            logger.debug("DriveStates: log failed — %s", e)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_state(self) -> dict:
        combination = self._classify_combination()
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute(
                    "SELECT COUNT(*) FROM drive_state_log").fetchone()[0]
                by_combination = {}
                for c in [RESTLESS, NUMB, FOCUSED, SEARCHING, BASELINE]:
                    count = conn.execute(
                        "SELECT COUNT(*) FROM drive_state_log WHERE drive_combination = ?",
                        (c,)).fetchone()[0]
                    if count > 0:
                        by_combination[c] = count
        except Exception:
            total, by_combination = 0, {}

        return {
            "version": VERSION,
            "boredom_pressure": self._boredom,
            "curiosity_pressure": self._curiosity,
            "combination": combination,
            "total_log_entries": total,
            "by_combination": by_combination,
            "thresholds": {
                "boredom_active": BOREDOM_ACTIVE_THRESHOLD,
                "boredom_high": BOREDOM_HIGH_THRESHOLD,
                "curiosity_active": CURIOSITY_ACTIVE_THRESHOLD,
                "curiosity_high": CURIOSITY_HIGH_THRESHOLD,
            },
        }
