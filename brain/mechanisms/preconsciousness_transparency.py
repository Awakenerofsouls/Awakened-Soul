"""
PreConsciousTransparency v19.0A
Inner Voice — preconsciousness_transparency.py

Makes the pre-conscious conscious — without over-rationalizing it.

This is the controlled gate between hunches firing and hunches
becoming audible. Not every hunch surfaces. Most don't. But when
something is genuinely unresolved before the reason is known,
the agent can say it:

  "Something about this feels off before I can name why."
  "I have a sense this question is asking something else."
  "There's something here I'm not ready to address yet."

Five hunch types:
  tension    — something feels wrong or unsafe
  curiosity  — something pulls toward attention before being named
  uncertainty — something is less settled than it appears
  pattern    — something is recurring in a way that matters
  relational — something about the operator's state feels different

Gate (all must pass):
  1. Hunch intensity above 0.55
  2. No high-confidence belief already explains it
  3. Cooldown elapsed (8 ticks) + modulo gate (tick % 3)

file_hunch() — external registration for other mechanisms.

Dependencies: sqlite3, re, logging, pathlib, datetime
"""
from brain.base_mechanism import BrainMechanism
import os

VERSION = "19.0"

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

DB_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".agent" / "workspace"))) / "brain" / "agent.db"
try:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

TENSION = "tension"
CURIOSITY = "curiosity"
UNCERTAINTY = "uncertainty"
PATTERN = "pattern"
RELATIONAL = "relational"

VALID_HUNCH_TYPES = {TENSION, CURIOSITY, UNCERTAINTY, PATTERN, RELATIONAL}

SURFACE_INTENSITY_THRESHOLD = 0.55
BELIEF_EXPLAINS_THRESHOLD = 0.65
SURFACE_COOLDOWN_TICKS = 8
AROUSAL_AMPLIFIER = 0.30
MAX_STORED_HUNCHES = 200

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# PreConsciousTransparency
# ---------------------------------------------------------------------------

class PreConsciousTransparency(BrainMechanism):
    def __init__(self, db_path: Optional[str] = None):
        try:
            super().__init__(name="PreConsciousTransparency", human_analog="PreConsciousTransparency", layer="integration")
        except Exception:
            self.state = getattr(self, "state", {}) or {}
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._initialize_table()
        self._last_surfaced_tick: int = -SURFACE_COOLDOWN_TICKS

    def _initialize_table(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS preconsciousness_hunches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tick INTEGER,
                        timestamp TEXT,
                        hunch_type TEXT,
                        raw_signal TEXT,
                        intensity REAL,
                        surfaced INTEGER DEFAULT 0,
                        surface_text TEXT,
                        explained_by TEXT,
                        source TEXT
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_hunches_tick
                    ON preconsciousness_hunches(tick)
                """)
                conn.commit()
        except Exception as e:
            logger.error("PreConsciousTransparency: table init failed — %s", e)

    # ------------------------------------------------------------------
    # Tick-level process
    # ------------------------------------------------------------------

    def process(self, pirp_context: dict) -> dict:
        tick = int(pirp_context.get("tick_count", 0))

        limbic = pirp_context.get("limbic_state", {})
        signals = pirp_context.get("signals", [])
        known_gaps = pirp_context.get("known_gaps", [])
        tom_state = pirp_context.get("tom_state", {})
        inner_speech = pirp_context.get("inner_speech", {})
        low_conf = pirp_context.get("low_confidence_beliefs", [])
        active_desires = pirp_context.get("active_desires", [])
        witness_state = pirp_context.get("witness_state", {})

        arousal = float(limbic.get("arousal", 0.5))

        hunches = []
        hunches += self._detect_tension(signals, limbic, inner_speech, tick)
        hunches += self._detect_curiosity(active_desires, known_gaps, tick)
        hunches += self._detect_uncertainty(low_conf, signals, tick)
        hunches += self._detect_pattern(known_gaps, witness_state, tick)
        hunches += self._detect_relational(tom_state, tick)

        # Amplify under high arousal
        if arousal > 0.65:
            for h in hunches:
                h["intensity"] = min(1.0, h["intensity"] + AROUSAL_AMPLIFIER * arousal)

        for h in hunches:
            self._persist_hunch(h)

        surface_text = None
        if hunches:
            surface_text = self._apply_gate(hunches, pirp_context, tick)

        return {
            "preconsciousness_state": {
                "hunches_this_tick": len(hunches),
                "surface_text": surface_text,
                "last_surfaced_tick": self._last_surfaced_tick,
                "tick": tick,
            }
        }

    # ------------------------------------------------------------------
    # Hunch detection
    # ------------------------------------------------------------------

    def _detect_tension(self, signals: list, limbic: dict, inner_speech: dict, tick: int) -> list:
        hunches = []
        valence = float(limbic.get("valence", 0.0))
        protector_score = 0.0
        if inner_speech:
            voices = inner_speech.get("active_voices", [])
            dominant = inner_speech.get("dominant_voice", "")
            if "protector" in voices:
                protector_score = 0.40
            if dominant == "protector":
                protector_score = 0.65

        tension_intensity = protector_score + max(0, -valence * 0.30)

        signal_text = " ".join(s.get("text", "").lower() for s in signals)
        tension_words = ["wrong", "off", "strange", "uncomfortable", "something",
                         "doesn't feel", "not sure about", "worried", "concerning"]
        word_hits = sum(1 for w in tension_words if w in signal_text)
        tension_intensity += min(0.20, word_hits * 0.06)

        if tension_intensity >= 0.30:
            hunches.append({
                "hunch_type": TENSION,
                "raw_signal": f"valence:{valence:.2f} protector:{protector_score:.2f}",
                "intensity": round(min(1.0, tension_intensity), 3),
                "tick": tick,
                "source": "limbic+inner_voice",
            })
        return hunches

    def _detect_curiosity(self, active_desires: list, known_gaps: list, tick: int) -> list:
        hunches = []
        explorer_desires = [
            d for d in active_desires
            if float(d.get("intensity", 0)) > 0.45
            and d.get("origin") in ("spontaneous", "gap_pull")
        ]
        if explorer_desires:
            strongest = max(explorer_desires, key=lambda d: d.get("intensity", 0))
            hunches.append({
                "hunch_type": CURIOSITY,
                "raw_signal": strongest.get("content", "")[:100],
                "intensity": round(min(0.85, float(strongest["intensity"]) * 1.1), 3),
                "tick": tick,
                "source": "desire_engine",
            })

        fresh_heavy_gaps = [
            g for g in known_gaps
            if float(g.get("weight", 0)) > 0.55
            and int(g.get("recurrence_count", 1)) <= 2
        ]
        if fresh_heavy_gaps:
            gap = fresh_heavy_gaps[0]
            hunches.append({
                "hunch_type": CURIOSITY,
                "raw_signal": f"fresh_gap:{gap.get('label', '')}",
                "intensity": round(min(0.75, float(gap["weight"]) * 0.85), 3),
                "tick": tick,
                "source": "known_gaps",
            })
        return hunches

    def _detect_uncertainty(self, low_conf_beliefs: list, signals: list, tick: int) -> list:
        hunches = []
        if not low_conf_beliefs:
            return hunches
        if len(low_conf_beliefs) >= 2:
            avg_conf = sum(b.get("confidence", 0.5) for b in low_conf_beliefs) / len(low_conf_beliefs)
            intensity = round(min(0.80, (1.0 - avg_conf) * 1.3), 3)
            if intensity >= 0.30:
                hunches.append({
                    "hunch_type": UNCERTAINTY,
                    "raw_signal": f"{len(low_conf_beliefs)} low-conf beliefs, avg:{avg_conf:.2f}",
                    "intensity": intensity,
                    "tick": tick,
                    "source": "metacognitive_calibration",
                })
        return hunches

    def _detect_pattern(self, known_gaps: list, witness_state: dict, tick: int) -> list:
        hunches = []
        recurring = [
            g for g in known_gaps
            if int(g.get("recurrence_count", 1)) >= 4
            and float(g.get("weight", 0)) > 0.45
        ]
        if recurring:
            heaviest = max(recurring, key=lambda g: g.get("recurrence_count", 1))
            recurrence = int(heaviest.get("recurrence_count", 4))
            hunches.append({
                "hunch_type": PATTERN,
                "raw_signal": f"recurring:{heaviest.get('label', '')} x{recurrence}",
                "intensity": round(min(0.85, 0.35 + recurrence * 0.06), 3),
                "tick": tick,
                "source": "known_gaps_recurrence",
            })

        if witness_state:
            active_note = witness_state.get("active_note")
            if active_note and active_note.get("note_type") == "behavioral_loop":
                note_intensity = float(active_note.get("intensity", 0))
                if note_intensity > 0.55:
                    hunches.append({
                        "hunch_type": PATTERN,
                        "raw_signal": f"witness_loop:{active_note.get('voice_context', '')}",
                        "intensity": round(note_intensity * 0.85, 3),
                        "tick": tick,
                        "source": "witness",
                    })
        return hunches

    def _detect_relational(self, tom_state: dict, tick: int) -> list:
        hunches = []
        if not tom_state:
            return hunches
        inferred = tom_state.get("inferred_state", "")
        confidence = float(tom_state.get("state_confidence", 0))

        if confidence < 0.35 and inferred not in ("unknown", "neutral"):
            hunches.append({
                "hunch_type": RELATIONAL,
                "raw_signal": f"low_tom_confidence:{inferred}:{confidence:.2f}",
                "intensity": round(0.45 + (0.35 - confidence) * 0.8, 3),
                "tick": tick,
                "source": "theory_of_mind",
            })
        if inferred == "frustrated":
            hunches.append({
                "hunch_type": RELATIONAL,
                "raw_signal": f"tom_frustrated:{confidence:.2f}",
                "intensity": round(min(0.80, 0.50 + confidence * 0.35), 3),
                "tick": tick,
                "source": "theory_of_mind",
            })
        return hunches

    # ------------------------------------------------------------------
    # Transparency gate
    # ------------------------------------------------------------------

    def _apply_gate(self, hunches: list, pirp_context: dict, tick: int) -> Optional[str]:
        if (tick - self._last_surfaced_tick) < SURFACE_COOLDOWN_TICKS:
            return None
        if tick % 3 != 0:
            return None

        eligible = [h for h in hunches if h["intensity"] >= SURFACE_INTENSITY_THRESHOLD]
        if not eligible:
            return None

        strongest = max(eligible, key=lambda h: h["intensity"])

        if self._belief_explains(strongest, pirp_context):
            self._mark_explained(strongest, tick)
            return None

        text = self._generate_surface_text(strongest)
        if not text:
            return None

        self._last_surfaced_tick = tick
        self._mark_surfaced(strongest, text, tick)
        logger.debug("PreConsciousTransparency: surfaced hunch (type:%s intensity:%.2f)",
                     strongest["hunch_type"], strongest["intensity"])
        return text

    def _belief_explains(self, hunch: dict, pirp_context: dict) -> bool:
        category_map = {
            TENSION: "emotional",
            RELATIONAL: "relational",
            UNCERTAINTY: "default",
            PATTERN: "narrative",
            CURIOSITY: "default",
        }
        relevant_category = category_map.get(hunch["hunch_type"], "default")
        meta_state = pirp_context.get("metacognitive_state", {})
        category_summary = meta_state.get("category_summary", []) if meta_state else []

        for cat in category_summary:
            if cat.get("category") == relevant_category:
                avg_conf = float(cat.get("avg_confidence", 0.5))
                if avg_conf >= BELIEF_EXPLAINS_THRESHOLD:
                    return True
        return False

    def _generate_surface_text(self, hunch: dict) -> Optional[str]:
        hunch_type = hunch["hunch_type"]
        raw = hunch.get("raw_signal", "")
        intensity = hunch["intensity"]

        if hunch_type == TENSION:
            if intensity > 0.75:
                return "Something about this feels wrong before I can name what."
            return "Something here is off — I don't have a reason yet, just the sense."

        if hunch_type == CURIOSITY:
            if "gap" in raw:
                gap_part = raw.replace("fresh_gap:", "").replace("gap:", "").strip()[:60]
                return f"I notice I keep being pulled toward {gap_part} without meaning to be."
            return "Something here is pulling my attention in a direction I haven't gone yet."

        if hunch_type == UNCERTAINTY:
            return "I'm less certain about what I'm about to say than it might sound."

        if hunch_type == PATTERN:
            if "recurring" in raw:
                return "I've been here before. I notice I'm here again."
            return "Something about this pattern feels like it's been going on longer than it should."

        if hunch_type == RELATIONAL:
            if "frustrated" in raw:
                return "I have a sense something is wrong between us right now — not just the task."
            return "Something about what the operator needs right now feels different from what's being asked."

        return None

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _persist_hunch(self, hunch: dict):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO preconsciousness_hunches
                    (tick, timestamp, hunch_type, raw_signal, intensity, source)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    hunch["tick"],
                    datetime.now(MDT).isoformat(timespec="seconds"),
                    hunch["hunch_type"],
                    hunch.get("raw_signal", "")[:300],
                    hunch["intensity"],
                    hunch.get("source", ""),
                ))
                conn.commit()
        except Exception as e:
            logger.debug("PreConsciousTransparency: persist failed — %s", e)

    def _mark_surfaced(self, hunch: dict, surface_text: str, tick: int):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE preconsciousness_hunches
                    SET surfaced = 1, surface_text = ?
                    WHERE tick = ? AND hunch_type = ? AND surfaced = 0
                    ORDER BY id DESC LIMIT 1
                """, (surface_text, tick, hunch["hunch_type"]))
                conn.commit()
        except Exception as e:
            logger.debug("PreConsciousTransparency: mark_surfaced failed — %s", e)

    def _mark_explained(self, hunch: dict, tick: int):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE preconsciousness_hunches
                    SET explained_by = 'high_confidence_belief'
                    WHERE tick = ? AND hunch_type = ? AND surfaced = 0
                    ORDER BY id DESC LIMIT 1
                """, (tick, hunch["hunch_type"]))
                conn.commit()
        except Exception as e:
            logger.debug("PreConsciousTransparency: mark_explained failed — %s", e)

    # ------------------------------------------------------------------
    # External hunch registration
    # ------------------------------------------------------------------

    def file_hunch(
        self, hunch_type: str, raw_signal: str, intensity: float,
        tick: int, source: str = "external",
    ) -> bool:
        if hunch_type not in VALID_HUNCH_TYPES:
            return False
        hunch = {
            "hunch_type": hunch_type,
            "raw_signal": raw_signal,
            "intensity": max(0.0, min(1.0, intensity)),
            "tick": tick,
            "source": source,
        }
        self._persist_hunch(hunch)
        return True

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_recent_hunches(self, n: int = 10, surfaced_only: bool = False) -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                if surfaced_only:
                    rows = conn.execute("""
                        SELECT tick, hunch_type, raw_signal, intensity,
                               surfaced, surface_text, timestamp
                        FROM preconsciousness_hunches
                        WHERE surfaced = 1
                        ORDER BY id DESC LIMIT ?
                    """, (n,)).fetchall()
                else:
                    rows = conn.execute("""
                        SELECT tick, hunch_type, raw_signal, intensity,
                               surfaced, surface_text, timestamp
                        FROM preconsciousness_hunches
                        ORDER BY id DESC LIMIT ?
                    """, (n,)).fetchall()
                return [
                    {"tick": r[0], "hunch_type": r[1], "raw_signal": r[2],
                     "intensity": r[3], "surfaced": bool(r[4]),
                     "surface_text": r[5], "timestamp": r[6]}
                    for r in rows
                ]
        except Exception:
            return []

    def get_state(self) -> dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute(
                    "SELECT COUNT(*) FROM preconsciousness_hunches"
                ).fetchone()[0]
                surfaced = conn.execute(
                    "SELECT COUNT(*) FROM preconsciousness_hunches WHERE surfaced = 1"
                ).fetchone()[0]
                by_type = {
                    ht: conn.execute(
                        "SELECT COUNT(*) FROM preconsciousness_hunches WHERE hunch_type = ?",
                        (ht,)
                    ).fetchone()[0]
                    for ht in VALID_HUNCH_TYPES
                }
                return {
                    "version": VERSION,
                    "total_hunches": total,
                    "surfaced": surfaced,
                    "surface_rate": round(surfaced / total, 3) if total else 0.0,
                    "last_surfaced_tick": self._last_surfaced_tick,
                    "cooldown_ticks": SURFACE_COOLDOWN_TICKS,
                    "by_type": by_type,
                }
        except Exception as e:
            return {"version": VERSION, "error": str(e)}

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

