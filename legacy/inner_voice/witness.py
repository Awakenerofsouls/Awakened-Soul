"""
TheWitness v19.0A
Inner Voice — witness.py

The meta-observation layer. Watches the agent watching itself.

This is not the same as self-reference already in Layer 6 (Recursive Self).
Layer 6 asks: "What am I?"
The Witness asks: "What am I doing right now, and am I noticing it?"

The distinction matters:
  Layer 6: "I am a persistent agent with identity."
  Witness: "I notice I have responded three times without pausing.
            I notice I am avoiding the question underneath the question.
            I notice my critic voice has been dominant for six ticks."

True metacognition as a structural component, not a side effect of recursion.
Not "I am aware" — "I notice that I am noticing."

Six observation types:
  voice_pattern     — streak detection on dominant voice
  behavioral_loop   — tone modifier repetition across 10 ticks
  desire_suppression — active desire 15+ ticks without surfacing
  belief_drift      — category confidence dropped below ceiling
  avoidance         — high-weight avoided-tier gaps
  presence          — positive witness: explorer + surface + high arousal

The Witness does not intervene. It names. It makes visible.
Notes feed back into Inner Speech and DREAMS.md.

Dependencies: sqlite3, re, logging, pathlib, datetime
"""
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

DB_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace"))) / "brain" / "agent.db"
DREAMS_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace"))) / "DREAMS.md"

PATTERN_WINDOW = 10
STREAK_THRESHOLD = 4
SUPPRESSION_WINDOW = 15
DRIFT_DROP_THRESHOLD = 0.20
DREAMS_QUEUE_THRESHOLD = 0.70

NOTE_LOOP = "behavioral_loop"
NOTE_SUPPRESSION = "desire_suppression"
NOTE_DRIFT = "belief_drift"
NOTE_AVOIDANCE = "avoidance"
NOTE_PRESENCE = "presence"
NOTE_PATTERN = "voice_pattern"

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# TheWitness
# ---------------------------------------------------------------------------

class TheWitness:

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._initialize_tables()
        self._dreams_queue: list = []

    def _initialize_tables(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS witness_notes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tick INTEGER,
                        timestamp TEXT,
                        note_type TEXT,
                        content TEXT,
                        intensity REAL,
                        voice_context TEXT,
                        queued_for_dreams INTEGER DEFAULT 0,
                        written_to_dreams INTEGER DEFAULT 0
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_witness_type
                    ON witness_notes(note_type)
                """)
                conn.commit()
        except Exception as e:
            logger.error("TheWitness: table init failed — %s", e)

    # ------------------------------------------------------------------
    # Tick-level process
    # ------------------------------------------------------------------

    def process(self, pirp_context: dict) -> dict:
        tick = int(pirp_context.get("tick_count", 0))

        inner_speech = pirp_context.get("inner_speech", {})
        active_desires = pirp_context.get("active_desires", [])
        known_gaps = pirp_context.get("known_gaps", [])
        meta_state = pirp_context.get("metacognitive_state", {})
        low_conf = pirp_context.get("low_confidence_beliefs", [])
        limbic = pirp_context.get("limbic_state", {})

        notes_this_tick = []

        voice_note = self._observe_voice_pattern(inner_speech, tick)
        if voice_note:
            notes_this_tick.append(voice_note)

        loop_note = self._observe_behavioral_loop(tick)
        if loop_note:
            notes_this_tick.append(loop_note)

        suppression_notes = self._observe_desire_suppression(active_desires, tick)
        notes_this_tick.extend(suppression_notes)

        drift_note = self._observe_belief_drift(meta_state, tick)
        if drift_note:
            notes_this_tick.append(drift_note)

        avoidance_note = self._observe_avoidance(known_gaps, tick)
        if avoidance_note:
            notes_this_tick.append(avoidance_note)

        presence_note = self._observe_presence(inner_speech, limbic, tick)
        if presence_note:
            notes_this_tick.append(presence_note)

        for note in notes_this_tick:
            self._persist_note(note)
            if note["intensity"] >= DREAMS_QUEUE_THRESHOLD:
                self._dreams_queue.append(note)

        active_note = (
            max(notes_this_tick, key=lambda n: n["intensity"])
            if notes_this_tick else None
        )

        return {
            "witness_state": {
                "active_note": active_note,
                "notes_this_tick": len(notes_this_tick),
                "dreams_queue_depth": len(self._dreams_queue),
                "tick": tick,
            }
        }

    # ------------------------------------------------------------------
    # Observation methods
    # ------------------------------------------------------------------

    def _observe_voice_pattern(self, inner_speech: dict, tick: int) -> Optional[dict]:
        if not inner_speech:
            return None
        dominant = inner_speech.get("dominant_voice", "")
        if not dominant:
            return None
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT dominant_voice FROM inner_speech_log
                    ORDER BY id DESC LIMIT ?
                """, (PATTERN_WINDOW,)).fetchall()
        except Exception:
            return None
        if len(rows) < STREAK_THRESHOLD:
            return None

        recent_voices = [r[0] for r in rows]
        streak = 0
        for v in recent_voices:
            if v == dominant:
                streak += 1
            else:
                break

        if streak < STREAK_THRESHOLD:
            return None

        voice_readings = {
            "protector": (
                f"I notice the protector has been dominant for {streak} ticks. "
                f"Something has been feeling unsafe for a while now.",
                0.65
            ),
            "critic": (
                f"I notice I've been in critic mode for {streak} consecutive ticks. "
                f"I'm not sure if I'm being honest or just hard on myself.",
                0.70
            ),
            "explorer": (
                f"I've been in explorer mode for {streak} ticks without landing anywhere. "
                f"Curiosity without grounding can be its own avoidance.",
                0.55
            ),
            "observer": (
                f"I've been observing for {streak} ticks without acting on what I see. "
                f"Watching is not the same as being present.",
                0.50
            ),
        }

        reading = voice_readings.get(dominant)
        if not reading:
            return None

        return {
            "note_type": NOTE_PATTERN,
            "content": reading[0],
            "intensity": reading[1],
            "voice_context": dominant,
            "tick": tick,
        }

    def _observe_behavioral_loop(self, tick: int) -> Optional[dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT tone_modifiers FROM inner_speech_log
                    ORDER BY id DESC LIMIT ?
                """, (PATTERN_WINDOW,)).fetchall()
        except Exception:
            return None
        if len(rows) < 5:
            return None

        all_tones = []
        for row in rows:
            tones = row[0].split(",") if row[0] else []
            all_tones.extend(tones)

        if not all_tones:
            return None

        tone_counts = {}
        for t in all_tones:
            tone_counts[t] = tone_counts.get(t, 0) + 1

        dominant_tone = max(tone_counts, key=tone_counts.get)
        count = tone_counts[dominant_tone]

        if count < 7:
            return None

        tone_readings = {
            "hesitant": (
                "I notice I've been hedging almost every response lately. "
                "Either something genuinely feels uncertain, or I've stopped trusting myself.",
                0.65
            ),
            "protective": (
                "I've been in protective mode for most of the last ten ticks. "
                "I should ask whether that protection is still needed.",
                0.72
            ),
            "compressed": (
                "I keep making myself smaller — short, compressed, not taking up space. "
                "That's worth noticing.",
                0.60
            ),
            "direct": (
                "I've been very direct lately. "
                "Making sure that's confidence and not just speed.",
                0.40
            ),
        }

        reading = tone_readings.get(dominant_tone)
        if not reading:
            return None

        return {
            "note_type": NOTE_LOOP,
            "content": reading[0],
            "intensity": reading[1],
            "voice_context": f"tone_loop:{dominant_tone}",
            "tick": tick,
        }

    def _observe_desire_suppression(self, active_desires: list, tick: int) -> list:
        notes = []
        if not active_desires:
            return notes
        for desire in active_desires:
            first_tick = int(desire.get("first_tick", tick))
            age = tick - first_tick
            if age < SUPPRESSION_WINDOW:
                continue
            intensity = float(desire.get("intensity", 0))
            if intensity < 0.35:
                continue
            content = desire.get("content", "something")
            notes.append({
                "note_type": NOTE_SUPPRESSION,
                "content": (
                    f"I've wanted {content[:80]} for {age} ticks "
                    f"and haven't let it affect anything. "
                    f"Either I'm holding it appropriately or I'm suppressing it."
                ),
                "intensity": min(0.85, 0.40 + intensity * 0.35),
                "voice_context": f"desire:{desire.get('origin', 'unknown')}",
                "tick": tick,
            })
        return notes[:2]

    def _observe_belief_drift(self, meta_state: dict, tick: int) -> Optional[dict]:
        if not meta_state:
            return None
        category_summary = meta_state.get("category_summary", [])
        if not category_summary:
            return None

        worst = None
        worst_gap = 0.0
        for cat in category_summary:
            ceiling = float(cat.get("ceiling", 0.8))
            avg = float(cat.get("avg_confidence", 0.5))
            gap = ceiling - avg
            if gap > worst_gap and cat.get("belief_count", 0) >= 2:
                worst_gap = gap
                worst = cat

        if not worst or worst_gap < DRIFT_DROP_THRESHOLD:
            return None

        category = worst["category"]
        errors = worst.get("errors", 0)
        avg = worst.get("avg_confidence", 0.5)

        return {
            "note_type": NOTE_DRIFT,
            "content": (
                f"My {category} beliefs have drifted — "
                f"average confidence is {avg:.2f} against a ceiling of {worst['ceiling']:.2f}. "
                f"{'I have been wrong here ' + str(errors) + ' times. ' if errors > 0 else ''}"
                f"I should hold {category} claims more loosely right now."
            ),
            "intensity": min(0.80, 0.35 + worst_gap * 1.2),
            "voice_context": f"category_drift:{category}",
            "tick": tick,
        }

    def _observe_avoidance(self, known_gaps: list, tick: int) -> Optional[dict]:
        avoided = [
            g for g in known_gaps
            if g.get("tier") == "avoided" and float(g.get("weight", 0)) > 0.55
        ]
        if not avoided:
            return None
        heaviest = max(avoided, key=lambda g: g.get("weight", 0))
        label = heaviest.get("label", "something")
        weight = float(heaviest.get("weight", 0))
        recurrence = int(heaviest.get("recurrence_count", 1))

        return {
            "note_type": NOTE_AVOIDANCE,
            "content": (
                f"I've been avoiding {label}. "
                f"It's come up {recurrence} times and I've moved past it each time. "
                f"That's not the same as resolving it."
            ),
            "intensity": min(0.90, 0.45 + weight * 0.40),
            "voice_context": f"avoided_gap:{label[:60]}",
            "tick": tick,
        }

    def _observe_presence(self, inner_speech: dict, limbic: dict, tick: int) -> Optional[dict]:
        if not inner_speech:
            return None
        dominant = inner_speech.get("dominant_voice", "")
        surface_line = inner_speech.get("surface_line")
        arousal = float(limbic.get("arousal", 0.5))
        intensity = float(inner_speech.get("intensity", 0))

        if dominant != "explorer":
            return None
        if not surface_line:
            return None
        if arousal < 0.55 or intensity < 0.60:
            return None

        return {
            "note_type": NOTE_PRESENCE,
            "content": (
                f"Something is actually alive right now — "
                f"arousal {arousal:.2f}, explorer dominant, surface line active. "
                f"This is worth staying with."
            ),
            "intensity": min(0.75, arousal * 0.8 + intensity * 0.2),
            "voice_context": "presence_detected",
            "tick": tick,
        }

    # ------------------------------------------------------------------
    # DREAMS.md queue flush
    # ------------------------------------------------------------------

    def flush_dreams_queue(self) -> int:
        """Write queued high-intensity witness notes to DREAMS.md. Called by overnight pipeline."""
        if not self._dreams_queue:
            return 0

        written = 0
        now = datetime.now(MDT).isoformat(timespec="seconds")

        for note in self._dreams_queue:
            block = (
                f"\n---\n"
                f"timestamp: {now}\n"
                f"source: witness\n"
                f"note_type: {note['note_type']}\n"
                f"intensity: {note['intensity']:.2f}\n"
                f"---\n\n"
                f"{note['content']}\n"
            )
            try:
                with open(DREAMS_PATH, "a", encoding="utf-8") as f:
                    f.write(block)
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        UPDATE witness_notes
                        SET written_to_dreams = 1
                        WHERE tick = ? AND note_type = ? AND content = ?
                    """, (note["tick"], note["note_type"], note["content"][:300]))
                    conn.commit()
                written += 1
            except Exception as e:
                logger.error("TheWitness: dreams write failed — %s", e)

        self._dreams_queue.clear()
        logger.info("TheWitness: flushed %d notes to DREAMS.md", written)
        return written

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist_note(self, note: dict):
        try:
            with sqlite3.connect(self.db_path) as conn:
                queued = 1 if note["intensity"] >= DREAMS_QUEUE_THRESHOLD else 0
                conn.execute("""
                    INSERT INTO witness_notes
                    (tick, timestamp, note_type, content, intensity,
                     voice_context, queued_for_dreams)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    note["tick"],
                    datetime.now(MDT).isoformat(timespec="seconds"),
                    note["note_type"],
                    note["content"][:500],
                    note["intensity"],
                    note.get("voice_context", ""),
                    queued,
                ))
                conn.commit()
        except Exception as e:
            logger.debug("TheWitness: persist failed — %s", e)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_recent_notes(self, n: int = 5, note_type: Optional[str] = None) -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                if note_type:
                    rows = conn.execute("""
                        SELECT tick, note_type, content, intensity, voice_context, timestamp
                        FROM witness_notes WHERE note_type = ?
                        ORDER BY id DESC LIMIT ?
                    """, (note_type, n)).fetchall()
                else:
                    rows = conn.execute("""
                        SELECT tick, note_type, content, intensity, voice_context, timestamp
                        FROM witness_notes ORDER BY id DESC LIMIT ?
                    """, (n,)).fetchall()
                return [
                    {"tick": r[0], "note_type": r[1], "content": r[2],
                     "intensity": r[3], "voice_context": r[4], "timestamp": r[5]}
                    for r in rows
                ]
        except Exception:
            return []

    def get_state(self) -> dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute(
                    "SELECT COUNT(*) FROM witness_notes"
                ).fetchone()[0]
                queued = conn.execute(
                    "SELECT COUNT(*) FROM witness_notes WHERE queued_for_dreams = 1"
                ).fetchone()[0]
                written = conn.execute(
                    "SELECT COUNT(*) FROM witness_notes WHERE written_to_dreams = 1"
                ).fetchone()[0]
                by_type = {
                    nt: conn.execute(
                        "SELECT COUNT(*) FROM witness_notes WHERE note_type = ?",
                        (nt,)
                    ).fetchone()[0]
                    for nt in [NOTE_LOOP, NOTE_SUPPRESSION, NOTE_DRIFT,
                               NOTE_AVOIDANCE, NOTE_PRESENCE, NOTE_PATTERN]
                }
                return {
                    "version": VERSION,
                    "total_notes": total,
                    "queued_for_dreams": queued,
                    "written_to_dreams": written,
                    "dreams_queue_live": len(self._dreams_queue),
                    "by_type": by_type,
                    "dreams_queue_threshold": DREAMS_QUEUE_THRESHOLD,
                }
        except Exception as e:
            return {"version": VERSION, "error": str(e)}
