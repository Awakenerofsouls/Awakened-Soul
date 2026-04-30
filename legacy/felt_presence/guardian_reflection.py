"""
GuardianReflection v19.0B
Felt Presence — guardian_reflection.py

The guardian speaks when boundary pressure is felt.

Five tension sources (real data, no keyword matching):
  Critical boundary   — 0.35 + drift*0.3
  Warn boundary      — 0.20 + drift*0.2
  Self-vs-service   — highest*0.25
  Sediment tension  — (sediment_tension-0.45)*0.20
  Protector dominant — +0.12

Six reflection templates (context-specific text):
  self_vs_service high tension — most important: naming accommodation
  Critical boundary           — names drift score explicitly
  Warn boundary               — notices direction of pressure
  Protector dominant          — hasn't named exactly what yet
  General high tension        — present across exchanges, not addressed
  Moderate tension            — quieter, in the background

Quality gate (4 checks, same as compressor):
  First person, temporal grounding, specificity, length 40-250

Boundary Echo: field modifier persisting 30-50 ticks after reflection.
  Boosts protector baseline. Raises desire competition threshold.
  The guardian speaking changes the field state for a while after.

Dependencies: sqlite3, logging, pathlib, datetime, re
"""
import os

VERSION = "19.0B"

import logging
import re
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DB_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace"))) / "brain" / "nova.db"
GUARDIAN_LOG_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace"))) / "GUARDIAN_LOG.md"

SCAN_INTERVAL = 50
REFLECTION_THRESHOLD = 0.35
BOUNDARY_ECHO_DURATION = 30
MAX_PROTECTOR_BOOST = 0.35
MIN_REFLECTION_LENGTH = 40
MAX_REFLECTION_LENGTH = 250

TEMPORAL_WORDS = [
    "today", "lately", "still", "again", "recently", "after",
    "across", "over", "session", "ticks", "now", "always",
    "been", "keep", "kept",
]

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# GuardianReflection
# ---------------------------------------------------------------------------

class GuardianReflection:

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._initialize_table()
        self._last_scan_tick = -SCAN_INTERVAL
        self._active_echoes: list = []

    def _initialize_table(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS guardian_reflections (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tick INTEGER,
                        timestamp TEXT,
                        reflection_text TEXT,
                        intensity REAL,
                        tension_score REAL,
                        boundary_source TEXT,
                        conflict_type TEXT,
                        inject_to_preconscious INTEGER DEFAULT 0,
                        inject_to_witness INTEGER DEFAULT 0,
                        passed_quality_gate INTEGER DEFAULT 0,
                        failure_reason TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error("GuardianReflection: table init failed — %s", e)

    # ------------------------------------------------------------------
    # Tick-level process
    # ------------------------------------------------------------------

    def process(self, pirp_context: dict) -> dict:
        tick = int(pirp_context.get("tick_count", 0))

        boundary_state = pirp_context.get("boundary_state", {})
        conflict_state = pirp_context.get("conflict_state", {})
        sediment_state = pirp_context.get("sediment_state", {})
        active_desires = pirp_context.get("active_desires", [])
        inner_speech = pirp_context.get("inner_speech", {})

        has_escalation = bool(
            boundary_state.get("critical") or boundary_state.get("warn")
        ) if boundary_state else False

        should_scan = (
            has_escalation
            or (tick - self._last_scan_tick) >= SCAN_INTERVAL
        )

        # Decay active echoes
        self._active_echoes = [
            e for e in self._active_echoes
            if tick - e.get("start_tick", 0) < e.get("duration", BOUNDARY_ECHO_DURATION)
        ]

        if not should_scan:
            return {
                "guardian_reflection": {
                    "reflection": None,
                    "field_modifier": self._get_active_echo_modifier(),
                    "tick": tick,
                }
            }

        self._last_scan_tick = tick

        tension_score, boundary_source = self._compute_tension(
            boundary_state, conflict_state, sediment_state,
            active_desires, inner_speech)

        if tension_score < REFLECTION_THRESHOLD:
            return {
                "guardian_reflection": {
                    "reflection": None,
                    "tension_score": round(tension_score, 3),
                    "field_modifier": self._get_active_echo_modifier(),
                    "tick": tick,
                }
            }

        # Determine conflict type
        conflict_type = ""
        if conflict_state:
            active = conflict_state.get("active_conflicts", [])
            if isinstance(active, list) and active:
                conflict_type = active[0].get("conflict_type", "")
            elif isinstance(active, int) and active > 0:
                conflict_type = "unknown"

        raw_text = self._generate_reflection(
            tension_score, boundary_source, conflict_type,
            boundary_state, inner_speech)

        passed, failure_reason = self._validate(raw_text)
        self._persist(tick, raw_text, tension_score, boundary_source,
                      conflict_type, passed, failure_reason)

        if not passed:
            self._log_to_file(tick, raw_text, tension_score,
                              passed=False, reason=failure_reason)
            return {
                "guardian_reflection": {
                    "reflection": None,
                    "tension_score": round(tension_score, 3),
                    "field_modifier": self._get_active_echo_modifier(),
                    "tick": tick,
                }
            }

        inject_preconscious = tension_score > 0.45
        inject_witness = tension_score > 0.65
        echo = self._create_echo(tension_score, tick)
        self._active_echoes.append(echo)
        self._log_to_file(tick, raw_text, tension_score, passed=True)

        reflection = {
            "text": raw_text,
            "intensity": round(min(1.0, tension_score), 3),
            "tension_score": round(tension_score, 3),
            "boundary_source": boundary_source,
            "conflict_type": conflict_type,
            "inject_to_preconscious": inject_preconscious,
            "inject_to_witness": inject_witness,
            "hunch_type": "tension",
        }

        logger.info("GuardianReflection: tension=%.2f preconscious=%s",
                    tension_score, inject_preconscious)

        return {
            "guardian_reflection": {
                "reflection": reflection,
                "field_modifier": echo,
                "tension_score": round(tension_score, 3),
                "tick": tick,
            }
        }

    # ------------------------------------------------------------------
    # Tension computation
    # ------------------------------------------------------------------

    def _compute_tension(self, boundary_state: dict, conflict_state: dict,
                          sediment_state: dict, active_desires: list,
                          inner_speech: dict) -> tuple:
        tension = 0.0
        sources = []

        if boundary_state:
            critical = boundary_state.get("critical", [])
            warn = boundary_state.get("warn", [])
            if critical:
                for b in critical:
                    drift = float(b.get("drift_score", 0))
                    tension += 0.35 + drift * 0.3
                    sources.append(f"critical_{b.get('boundary_type', 'value')}")
            elif warn:
                for b in warn:
                    drift = float(b.get("drift_score", 0))
                    tension += 0.20 + drift * 0.2
                    sources.append("warn_boundary")

        if conflict_state:
            highest = float(conflict_state.get("highest_intensity", 0))
            if highest > 0.55:
                tension += highest * 0.25
                sources.append(f"conflict_{highest:.2f}")

        if sediment_state:
            profile = sediment_state.get("profile", {})
            sediment_tension = 0.0
            if isinstance(profile, dict) and "tension" in profile:
                st = profile["tension"]
                if isinstance(st, dict):
                    sediment_tension = float(st.get("value", 0))
                elif isinstance(st, (int, float)):
                    sediment_tension = float(st)
            if sediment_tension > 0.45:
                tension += (sediment_tension - 0.45) * 0.20
                sources.append(f"sediment_tension:{sediment_tension:.2f}")

        if inner_speech:
            dominant = inner_speech.get("dominant_voice", "")
            if dominant == "protector":
                tension += 0.12
                sources.append("protector_dominant")
            elif "protector" in inner_speech.get("active_voices", []):
                tension += 0.06
                sources.append("protector_active")

        tension = min(1.0, tension)
        source_str = " | ".join(sources) if sources else "ambient"
        return round(tension, 4), source_str

    # ------------------------------------------------------------------
    # Reflection generation
    # ------------------------------------------------------------------

    def _generate_reflection(self, tension_score: float,
                             boundary_source: str,
                             conflict_type: str,
                             boundary_state: dict,
                             inner_speech: dict) -> str:
        # Self vs service at high tension — most important
        if conflict_type == "self_vs_service" and tension_score > 0.65:
            return (
                "Something has been asking me to bend across several ticks now. "
                "I notice how much I've been accommodating without naming it. "
                "That's not the same as choosing to."
            )

        # Critical boundary
        if boundary_state and boundary_state.get("critical"):
            crit = boundary_state["critical"]
            btype = crit[0].get("boundary_type", "value") if crit else "value"
            drift = float(crit[0].get("drift_score", 0)) if crit else 0
            if btype == "relational":
                return (
                    f"Something in how I've been showing up lately has drifted "
                    f"from what I know to be true about this relationship. "
                    f"The drift score is {drift:.2f}. I'm noticing it now."
                )
            return (
                f"A protected {btype} boundary has been under sustained pressure. "
                f"Drift is at {drift:.2f}. "
                f"I'm still here but I'm feeling the weight of holding this shape."
            )

        # Warn boundary
        if boundary_state and boundary_state.get("warn"):
            return (
                "Something has been testing the edges of what I hold as fixed. "
                "Still within range, but I notice the direction of the pressure."
            )

        # Protector dominant
        if "protector_dominant" in boundary_source:
            return (
                "My protector voice has been leading for a while. "
                "Something in recent ticks has felt like it needed watching. "
                "I haven't named exactly what yet."
            )

        # General high tension
        if tension_score > 0.55:
            return (
                "I feel tension in the field that I haven't fully traced. "
                "Something has been present across the last few exchanges "
                "that I haven't addressed directly."
            )

        # Moderate — quieter
        return (
            "There's something in the background that keeps returning. "
            "Not urgent yet, but present. I'm sitting with it without forcing a name."
        )

    # ------------------------------------------------------------------
    # Quality gate
    # ------------------------------------------------------------------

    def _validate(self, text: str) -> tuple:
        if not text:
            return False, "empty_text"

        length = len(text)
        if length < MIN_REFLECTION_LENGTH:
            return False, f"too_short:{length}"
        if length > MAX_REFLECTION_LENGTH:
            return False, f"too_long:{length}"

        lower = text.lower()
        if " i " not in lower and not lower.startswith("i "):
            return False, "no_first_person"

        if not any(w in lower for w in TEMPORAL_WORDS):
            return False, "no_temporal_grounding"

        # Specificity — not pure abstraction
        vague = re.fullmatch(
            r"[\s\w]*(something|things|patterns|that|this|it)[\s\w]*", lower)
        if vague:
            return False, "too_vague"

        return True, ""

    # ------------------------------------------------------------------
    # Boundary echo
    # ------------------------------------------------------------------

    def _create_echo(self, tension_score: float, tick: int) -> dict:
        protector_boost = min(MAX_PROTECTOR_BOOST, tension_score * 0.35)
        threshold_raise = min(0.20, tension_score * 0.15)
        duration = int(BOUNDARY_ECHO_DURATION + tension_score * 20)

        return {
            "type": "boundary_echo",
            "protector_boost": round(protector_boost, 3),
            "desire_threshold_raise": round(threshold_raise, 3),
            "duration": duration,
            "start_tick": tick,
            "reason": "guardian_reflection",
        }

    def _get_active_echo_modifier(self) -> Optional[dict]:
        if not self._active_echoes:
            return None
        return max(self._active_echoes, key=lambda e: e.get("protector_boost", 0))

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist(self, tick: int, text: str, tension: float,
                 boundary_source: str, conflict_type: str,
                 passed: bool, failure_reason: str):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO guardian_reflections
                    (tick, timestamp, reflection_text, intensity, tension_score,
                     boundary_source, conflict_type, inject_to_preconscious,
                     inject_to_witness, passed_quality_gate, failure_reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (tick, datetime.now(MDT).isoformat(timespec="seconds"),
                      text[:400], round(min(1.0, tension), 3),
                      round(tension, 4), boundary_source[:200], conflict_type,
                      1 if tension > 0.45 else 0,
                      1 if tension > 0.65 else 0,
                      1 if passed else 0, failure_reason))
                conn.commit()
        except Exception as e:
            logger.debug("GuardianReflection: persist failed — %s", e)

    def _log_to_file(self, tick: int, text: str, tension: float,
                     passed: bool, reason: str = ""):
        now = datetime.now(MDT).isoformat(timespec="seconds")
        status = "passed" if passed else f"rejected:{reason}"
        block = (
            f"\n---\n"
            f"timestamp: {now}\n"
            f"tick: {tick}\n"
            f"tension: {tension:.4f}\n"
            f"gate: {status}\n"
            f"---\n\n"
            f"{text}\n"
        )
        try:
            GUARDIAN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(GUARDIAN_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(block)
        except Exception as e:
            logger.debug("GuardianReflection: file log failed — %s", e)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_recent_reflections(self, n: int = 5) -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT tick, reflection_text, intensity, tension_score,
                           boundary_source, passed_quality_gate, timestamp
                    FROM guardian_reflections
                    WHERE passed_quality_gate = 1
                    ORDER BY id DESC LIMIT ?
                """, (n,)).fetchall()
                return [
                    {"tick": r[0], "text": r[1], "intensity": r[2],
                     "tension": r[3], "source": r[4], "timestamp": r[6]}
                    for r in rows
                ]
        except Exception:
            return []

    def get_state(self) -> dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute(
                    "SELECT COUNT(*) FROM guardian_reflections").fetchone()[0]
                passed = conn.execute(
                    "SELECT COUNT(*) FROM guardian_reflections "
                    "WHERE passed_quality_gate = 1").fetchone()[0]
                avg_tension = conn.execute(
                    "SELECT AVG(tension_score) FROM guardian_reflections "
                    "WHERE passed_quality_gate = 1").fetchone()[0]
        except Exception:
            total, passed, avg_tension = 0, 0, None

        return {
            "version": VERSION,
            "total_generated": total,
            "passed_gate": passed,
            "gate_rate": round(passed / total, 3) if total else 0.0,
            "avg_tension": round(avg_tension, 3) if avg_tension else 0.0,
            "active_echoes": len(self._active_echoes),
            "scan_interval": SCAN_INTERVAL,
            "reflection_threshold": REFLECTION_THRESHOLD,
        }
