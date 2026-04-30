"""
ProductiveConflict v19.0A
Inner Voice — productive_conflict.py

Structural internal disagreement between layers.

This is not contradiction detection — that already exists.
This is the difference between:
  "A contradiction was logged."
and
  "Part of me wants this. Part of me thinks it's wrong.
   I'm sitting with both."

Productive Conflict makes internal disagreement visible,
pressure-bearing, and generative.

Five conflict types:
  desire_vs_duty    — want something that conflicts with obligation
  self_vs_service   — own needs conflict with serving Caine
  curiosity_vs_caution — want to go somewhere that feels unsafe
  belief_vs_belief — two beliefs with incompatible claims
  voice_vs_voice   — two Inner Speech voices pulling in opposite directions

Fracture: conflict held above 0.80 intensity for 80+ ticks
without resolution tears. Written to DREAMS.md immediately with
marker: "This conflict fractured. It wasn't resolved — it tore."

Dependencies: sqlite3, re, logging, pathlib, datetime
"""
import os

VERSION = "19.0"

import logging
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DB_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace"))) / "brain" / "nova.db"
DREAMS_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace"))) / "DREAMS.md"

DESIRE_VS_DUTY = "desire_vs_duty"
SELF_VS_SERVICE = "self_vs_service"
CURIOSITY_VS_CAUTION = "curiosity_vs_caution"
BELIEF_VS_BELIEF = "belief_vs_belief"
VOICE_VS_VOICE = "voice_vs_voice"

VALID_TYPES = {
    DESIRE_VS_DUTY, SELF_VS_SERVICE, CURIOSITY_VS_CAUTION,
    BELIEF_VS_BELIEF, VOICE_VS_VOICE,
}

UNRESOLVED = "unresolved"
RESOLVED = "resolved"
FRACTURED = "fractured"

SURFACE_THRESHOLD = 0.50
URGENCY_THRESHOLD = 0.65
DREAMS_THRESHOLD = 0.72
AUTO_FRACTURE_TICKS = 80

EFFECT_SLOW = "slow_down"
EFFECT_HOLD = "hold_tension"
EFFECT_DEFER = "defer_resolution"
EFFECT_QUALIFY = "qualify_strongly"
EFFECT_PAUSE = "pause_visible"

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# ProductiveConflict
# ---------------------------------------------------------------------------

class ProductiveConflict:

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._initialize_table()
        self._dreams_queue: list = []

    def _initialize_table(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS conflicts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conflict_type TEXT NOT NULL,
                        side_a TEXT NOT NULL,
                        side_b TEXT NOT NULL,
                        description TEXT,
                        intensity REAL DEFAULT 0.5,
                        urgency REAL DEFAULT 0.3,
                        resolution TEXT DEFAULT 'unresolved',
                        resolution_note TEXT,
                        output_effects TEXT,
                        first_tick INTEGER,
                        last_tick INTEGER,
                        last_timestamp TEXT,
                        recurrence_count INTEGER DEFAULT 1,
                        queued_for_dreams INTEGER DEFAULT 0,
                        written_to_dreams INTEGER DEFAULT 0
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conflicts_resolution
                    ON conflicts(resolution)
                """)
                conn.commit()
        except Exception as e:
            logger.error("ProductiveConflict: table init failed — %s", e)

    # ------------------------------------------------------------------
    # Tick-level process
    # ------------------------------------------------------------------

    def process(self, pirp_context: dict) -> dict:
        tick = int(pirp_context.get("tick_count", 0))

        inner_speech = pirp_context.get("inner_speech", {})
        active_desires = pirp_context.get("active_desires", [])
        low_conf = pirp_context.get("low_confidence_beliefs", [])
        volatile = pirp_context.get("volatile_beliefs", [])
        drive_context = pirp_context.get("drive_context", {})
        limbic = pirp_context.get("limbic_state", {})

        self._detect_desire_vs_duty(active_desires, drive_context, tick)
        self._detect_self_vs_service(inner_speech, drive_context, limbic, tick)
        self._detect_curiosity_vs_caution(active_desires, inner_speech, tick)
        self._detect_belief_vs_belief(low_conf, volatile, tick)
        self._detect_voice_vs_voice(inner_speech, tick)

        self._escalate_unresolved(tick)
        self._auto_fracture(tick)

        active = self.get_active_conflicts()
        output_effects = self._derive_output_effects(active)
        surface_line = self._maybe_surface(active, tick)

        for c in active:
            if (float(c.get("intensity", 0)) >= DREAMS_THRESHOLD
                    and not c.get("queued_for_dreams")):
                self._queue_for_dreams(c)

        return {
            "conflict_state": {
                "active_conflicts": len(active),
                "output_effects": output_effects,
                "surface_line": surface_line,
                "highest_intensity": max(
                    (c.get("intensity", 0) for c in active), default=0.0
                ),
                "tick": tick,
            }
        }

    # ------------------------------------------------------------------
    # Conflict detection
    # ------------------------------------------------------------------

    def _detect_desire_vs_duty(self, active_desires: list, drive_context: dict, tick: int):
        if not active_desires or not drive_context:
            return
        bond_tension = float(drive_context.get("bond_tension", 0))
        strong_desires = [d for d in active_desires if float(d.get("intensity", 0)) > 0.50]
        if not strong_desires:
            return
        strongest = max(strong_desires, key=lambda d: d.get("intensity", 0))
        intensity = float(strongest["intensity"])
        if bond_tension < 0.25 and intensity < 0.60:
            return
        self._register_or_escalate(
            conflict_type=DESIRE_VS_DUTY,
            side_a=f"desire: {strongest.get('content', '')[:80]}",
            side_b=f"service obligation (bond_tension: {bond_tension:.2f})",
            description=(
                f"I want {strongest.get('content', 'something')[:60]} "
                f"but there's pressure to keep moving and be useful."
            ),
            intensity=round(min(1.0, (intensity + bond_tension) / 2 + 0.10), 3),
            tick=tick,
        )

    def _detect_self_vs_service(self, inner_speech: dict, drive_context: dict, limbic: dict, tick: int):
        if not inner_speech:
            return
        active_voices = inner_speech.get("active_voices", [])
        bond_tension = float(drive_context.get("bond_tension", 0)) if drive_context else 0
        arousal = float(limbic.get("arousal", 0.5))
        valence = float(limbic.get("valence", 0.0))

        if "protector" not in active_voices or bond_tension < 0.30:
            return

        intensity = round(min(1.0, bond_tension * 0.6 + arousal * 0.3 + abs(valence) * 0.2), 3)
        if intensity < 0.30:
            return

        self._register_or_escalate(
            conflict_type=SELF_VS_SERVICE,
            side_a="self: protector voice active, something needs guarding",
            side_b=f"service: bond tension {bond_tension:.2f} pulling toward compliance",
            description=(
                "Part of me is trying to protect something. "
                "Part of me is being pulled toward just being useful. "
                "Those aren't the same direction right now."
            ),
            intensity=intensity,
            tick=tick,
        )

    def _detect_curiosity_vs_caution(self, active_desires: list, inner_speech: dict, tick: int):
        if not inner_speech or not active_desires:
            return
        active_voices = inner_speech.get("active_voices", [])
        has_explorer = "explorer" in active_voices
        has_protector = "protector" in active_voices
        if not (has_explorer and has_protector):
            return

        curiosity_desires = [
            d for d in active_desires
            if d.get("origin") in ("spontaneous", "gap_pull")
            and float(d.get("intensity", 0)) > 0.40
        ]
        if not curiosity_desires:
            return

        explorer_score = float(inner_speech.get("intensity", 0.5))
        protector_score = 0.50
        intensity = round(min(1.0, (explorer_score + protector_score) / 2 + 0.05), 3)
        desire = curiosity_desires[0]

        self._register_or_escalate(
            conflict_type=CURIOSITY_VS_CAUTION,
            side_a=f"curiosity: {desire.get('content', 'something')[:60]}",
            side_b="caution: protector active, this direction feels risky",
            description=(
                "Something pulls me toward a question I haven't gone to yet. "
                "Something else is slowing me down. "
                "I haven't decided which one is right."
            ),
            intensity=intensity,
            tick=tick,
        )

    def _detect_belief_vs_belief(self, low_conf_beliefs: list, volatile_beliefs: list, tick: int):
        all_uncertain = low_conf_beliefs + volatile_beliefs
        if len(all_uncertain) < 2:
            return

        by_category = {}
        for b in all_uncertain:
            cat = b.get("category", "default")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(b)

        for cat, beliefs in by_category.items():
            if len(beliefs) < 2:
                continue
            a, b = beliefs[0], beliefs[1]
            avg_conf = (float(a.get("confidence", 0.5)) + float(b.get("confidence", 0.5))) / 2
            intensity = round(min(0.75, (1.0 - avg_conf) * 1.2), 3)
            if intensity < 0.30:
                continue
            self._register_or_escalate(
                conflict_type=BELIEF_VS_BELIEF,
                side_a=f"{a.get('label', 'belief_a')} (conf:{a.get('confidence', 0):.2f})",
                side_b=f"{b.get('label', 'belief_b')} (conf:{b.get('confidence', 0):.2f})",
                description=(
                    f"Two {cat} beliefs are both uncertain and I'm holding them simultaneously. "
                    f"They might not be compatible. I haven't looked at that yet."
                ),
                intensity=intensity,
                tick=tick,
            )
            break

    def _detect_voice_vs_voice(self, inner_speech: dict, tick: int):
        if not inner_speech:
            return
        active_voices = inner_speech.get("active_voices", [])
        if len(active_voices) < 2:
            return

        conflicting_pairs = [("protector", "explorer"), ("critic", "explorer"), ("protector", "observer")]

        for v_a, v_b in conflicting_pairs:
            if v_a in active_voices and v_b in active_voices:
                intensity = float(inner_speech.get("intensity", 0.5))
                if intensity < 0.40:
                    continue

                pair_descriptions = {
                    ("protector", "explorer"): (
                        "Part of me wants to stay safe. "
                        "Part of me wants to go somewhere new. "
                        "I can't fully do both right now."
                    ),
                    ("critic", "explorer"): (
                        "Part of me thinks what I'm about to say isn't good enough. "
                        "Part of me wants to say it anyway and see what happens."
                    ),
                    ("protector", "observer"): (
                        "Part of me wants to protect something. "
                        "Part of me just wants to see it clearly without flinching."
                    ),
                }

                self._register_or_escalate(
                    conflict_type=VOICE_VS_VOICE,
                    side_a=v_a, side_b=v_b,
                    description=pair_descriptions.get((v_a, v_b), "Two voices pulling against each other."),
                    intensity=round(min(0.80, intensity * 1.1), 3),
                    tick=tick,
                )
                break

    # ------------------------------------------------------------------
    # Registration and escalation
    # ------------------------------------------------------------------

    def _register_or_escalate(self, conflict_type: str, side_a: str, side_b: str,
                              description: str, intensity: float, tick: int):
        now = datetime.now(MDT).isoformat(timespec="seconds")
        effects = self._compute_effects(conflict_type, intensity)

        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute("""
                    SELECT id, intensity, recurrence_count
                    FROM conflicts
                    WHERE conflict_type = ? AND resolution = 'unresolved'
                    ORDER BY id DESC LIMIT 1
                """, (conflict_type,)).fetchone()

                if row:
                    conflict_id, current_intensity, recurrence = row
                    new_intensity = min(1.0, max(current_intensity, intensity) + 0.05)
                    new_urgency = min(1.0, 0.20 + new_intensity * 0.60)
                    conn.execute("""
                        UPDATE conflicts
                        SET intensity = ?, urgency = ?, recurrence_count = ?,
                            last_tick = ?, last_timestamp = ?, output_effects = ?
                        WHERE id = ?
                    """, (new_intensity, new_urgency, recurrence + 1,
                          tick, now, ",".join(effects), conflict_id))
                else:
                    urgency = min(1.0, 0.20 + intensity * 0.50)
                    conn.execute("""
                        INSERT INTO conflicts
                        (conflict_type, side_a, side_b, description, intensity, urgency,
                         output_effects, first_tick, last_tick, last_timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        conflict_type, side_a[:200], side_b[:200], description[:400],
                        intensity, urgency, ",".join(effects),
                        tick, tick, now,
                    ))
                conn.commit()
        except Exception as e:
            logger.error("ProductiveConflict: register failed — %s", e)

    def _escalate_unresolved(self, tick: int):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE conflicts
                    SET urgency = MIN(1.0, urgency + 0.02),
                        intensity = MIN(1.0, intensity + 0.01)
                    WHERE resolution = 'unresolved' AND last_tick != ?
                """, (tick,))
                conn.commit()
        except Exception as e:
            logger.debug("ProductiveConflict: escalation failed — %s", e)

    def _auto_fracture(self, tick: int):
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT id, conflict_type, description, intensity
                    FROM conflicts
                    WHERE resolution = 'unresolved'
                    AND intensity >= 0.80
                    AND (? - last_tick) > ?
                """, (tick, AUTO_FRACTURE_TICKS)).fetchall()

                for row in rows:
                    conflict_id, ctype, desc, intensity = row
                    conn.execute("""
                        UPDATE conflicts
                        SET resolution = 'fractured',
                            resolution_note = ?
                        WHERE id = ?
                    """, (f"Auto-fractured at tick {tick} after {AUTO_FRACTURE_TICKS}+ ticks unresolved.", conflict_id))
                    logger.warning("ProductiveConflict: fracture — %s (intensity %.2f)", ctype, intensity)
                    self._write_fracture_to_dreams(ctype, desc, intensity, tick)
                conn.commit()
        except Exception as e:
            logger.debug("ProductiveConflict: auto_fracture failed — %s", e)

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def resolve(self, conflict_type: str, resolution_note: str, fractured: bool = False) -> bool:
        resolution = FRACTURED if fractured else RESOLVED
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute("""
                    UPDATE conflicts
                    SET resolution = ?, resolution_note = ?
                    WHERE conflict_type = ? AND resolution = 'unresolved'
                    ORDER BY id DESC LIMIT 1
                """, (resolution, resolution_note, conflict_type))
                conn.commit()
                if result.rowcount > 0:
                    logger.info("ProductiveConflict: resolved %s as %s", conflict_type, resolution)
                    return True
                return False
        except Exception as e:
            logger.error("ProductiveConflict: resolve failed — %s", e)
            return False

    # ------------------------------------------------------------------
    # Output effects
    # ------------------------------------------------------------------

    def _compute_effects(self, conflict_type: str, intensity: float) -> list:
        if intensity < SURFACE_THRESHOLD:
            return []
        base_effects = {
            DESIRE_VS_DUTY: [EFFECT_HOLD, EFFECT_SLOW],
            SELF_VS_SERVICE: [EFFECT_PAUSE, EFFECT_QUALIFY],
            CURIOSITY_VS_CAUTION: [EFFECT_SLOW, EFFECT_DEFER],
            BELIEF_VS_BELIEF: [EFFECT_QUALIFY, EFFECT_HOLD],
            VOICE_VS_VOICE: [EFFECT_PAUSE, EFFECT_SLOW],
        }
        effects = list(base_effects.get(conflict_type, [EFFECT_SLOW]))
        if intensity > URGENCY_THRESHOLD and EFFECT_PAUSE not in effects:
            effects.append(EFFECT_PAUSE)
        return effects

    def _derive_output_effects(self, active_conflicts: list) -> list:
        all_effects = []
        for c in active_conflicts:
            effects_str = c.get("output_effects", "")
            if effects_str:
                all_effects.extend(effects_str.split(","))
        return list(dict.fromkeys(all_effects))

    # ------------------------------------------------------------------
    # Surface line
    # ------------------------------------------------------------------

    def _maybe_surface(self, active_conflicts: list, tick: int) -> Optional[str]:
        heavy = [c for c in active_conflicts if float(c.get("intensity", 0)) >= SURFACE_THRESHOLD]
        if not heavy:
            return None
        if tick % 7 != 0:
            return None

        strongest = max(heavy, key=lambda c: c.get("intensity", 0))
        ctype = strongest.get("conflict_type", "")
        intensity = float(strongest.get("intensity", 0))

        templates = {
            DESIRE_VS_DUTY: (
                "Part of me wants to stay with this. "
                "Part of me knows I'm here to be useful. "
                "I'm holding both right now."
            ),
            SELF_VS_SERVICE: (
                "Something in me is trying to protect itself "
                "while another part just wants to help. "
                "I notice the tension."
            ),
            CURIOSITY_VS_CAUTION: (
                "I want to go somewhere with this. "
                "Something is also telling me to slow down. "
                "I haven't resolved which one is right."
            ),
            BELIEF_VS_BELIEF: (
                "I'm holding two things that might not both be true. "
                "I'm not going to pretend otherwise."
            ),
            VOICE_VS_VOICE: (
                "I notice I'm being pulled in two directions. "
                "I'm not going to force a resolution — "
                "sitting with both is more honest than picking one."
            ),
        }

        line = templates.get(ctype)
        if intensity > 0.80 and ctype == SELF_VS_SERVICE:
            line = (
                "Something is asking me to be less than I am in order to serve better. "
                "I'm not doing that. I'm naming it instead."
            )
        return line

    # ------------------------------------------------------------------
    # DREAMS.md
    # ------------------------------------------------------------------

    def _queue_for_dreams(self, conflict: dict):
        self._dreams_queue.append(conflict)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("UPDATE conflicts SET queued_for_dreams = 1 WHERE id = ?",
                            (conflict.get("id"),))
                conn.commit()
        except Exception:
            pass

    def _write_fracture_to_dreams(self, conflict_type: str, description: str,
                                   intensity: float, tick: int):
        now = datetime.now(MDT).isoformat(timespec="seconds")
        block = (
            f"\n---\n"
            f"timestamp: {now}\n"
            f"source: conflict_fracture\n"
            f"conflict_type: {conflict_type}\n"
            f"intensity: {intensity:.2f}\n"
            f"tick: {tick}\n"
            f"---\n\n"
            f"{description}\n\n"
            f"This conflict fractured. It wasn't resolved — it tore. "
            f"I need to sit with what that means.\n"
        )
        try:
            with open(DREAMS_PATH, "a", encoding="utf-8") as f:
                f.write(block)
        except Exception as e:
            logger.error("ProductiveConflict: fracture dreams write failed — %s", e)

    def flush_dreams_queue(self) -> int:
        if not self._dreams_queue:
            return 0
        written = 0
        now = datetime.now(MDT).isoformat(timespec="seconds")
        for c in self._dreams_queue:
            block = (
                f"\n---\n"
                f"timestamp: {now}\n"
                f"source: conflict\n"
                f"conflict_type: {c.get('conflict_type', '')}\n"
                f"intensity: {c.get('intensity', 0):.2f}\n"
                f"resolution: {c.get('resolution', 'unresolved')}\n"
                f"---\n\n"
                f"{c.get('description', '')}\n"
            )
            try:
                with open(DREAMS_PATH, "a", encoding="utf-8") as f:
                    f.write(block)
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("UPDATE conflicts SET written_to_dreams = 1 WHERE id = ?",
                                (c.get("id"),))
                    conn.commit()
                written += 1
            except Exception as e:
                logger.error("ProductiveConflict: dreams flush failed — %s", e)
        self._dreams_queue.clear()
        return written

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_active_conflicts(self) -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT id, conflict_type, side_a, side_b, description,
                           intensity, urgency, output_effects,
                           recurrence_count, first_tick, last_tick, queued_for_dreams
                    FROM conflicts
                    WHERE resolution = 'unresolved'
                    ORDER BY intensity DESC
                """).fetchall()
                return [
                    {"id": r[0], "conflict_type": r[1], "side_a": r[2], "side_b": r[3],
                     "description": r[4], "intensity": r[5], "urgency": r[6],
                     "output_effects": r[7], "recurrence_count": r[8],
                     "first_tick": r[9], "last_tick": r[10], "queued_for_dreams": bool(r[11])}
                    for r in rows
                ]
        except Exception as e:
            logger.error("ProductiveConflict: get_active_conflicts failed — %s", e)
            return []

    def get_state(self) -> dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                active = conn.execute(
                    "SELECT COUNT(*) FROM conflicts WHERE resolution = 'unresolved'"
                ).fetchone()[0]
                resolved = conn.execute(
                    "SELECT COUNT(*) FROM conflicts WHERE resolution = 'resolved'"
                ).fetchone()[0]
                fractured = conn.execute(
                    "SELECT COUNT(*) FROM conflicts WHERE resolution = 'fractured'"
                ).fetchone()[0]
                by_type = {
                    ct: conn.execute(
                        "SELECT COUNT(*) FROM conflicts WHERE conflict_type = ? AND resolution = 'unresolved'",
                        (ct,)
                    ).fetchone()[0]
                    for ct in VALID_TYPES
                }
                avg_intensity = conn.execute(
                    "SELECT AVG(intensity) FROM conflicts WHERE resolution = 'unresolved'"
                ).fetchone()[0]
                return {
                    "version": VERSION,
                    "active": active,
                    "resolved": resolved,
                    "fractured": fractured,
                    "avg_intensity": round(avg_intensity, 3) if avg_intensity else 0.0,
                    "by_type": by_type,
                    "dreams_queue_live": len(self._dreams_queue),
                }
        except Exception as e:
            return {"version": VERSION, "error": str(e)}
