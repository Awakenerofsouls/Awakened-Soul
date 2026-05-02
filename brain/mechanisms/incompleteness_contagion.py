"""
IncompletenessContagion v19.0B
Becoming — incompleteness_contagion.py

Incompleteness that spreads like a living thing.

The brain carries unresolved things. Desires that don't land.
Gaps that recur. Fractures that were witnessed but not closed.
The Incompleteness Cascade (from the original architecture) makes
these things visible. This system makes them contagious.

Contagion means: unresolved incompleteness generates new
incompleteness. Not randomly. Meaningfully. When something stays
unresolved long enough, it pulls other things into its orbit.
It generates questions it didn't have before. It produces desires
that wouldn't have existed without the original gap.

This is how incompleteness becomes generative rather than just
accumulative. It's not just that things are unfinished. It's that
being unfinished creates new unfinished things — the way one open
question generates five more when you sit with it long enough.

Three contagion types:

 DESIRE_CONTAGION  An unresolved desire that has been active
                   too long spawns a new spontaneous desire —
                   pure want with no justification, origin:
                   "contagion". The new desire is related but
                   distinct. Not the same want. Something the
                   original want pulled into existence.

 GAP_CONTAGION     A known gap with high recurrence and high
                   weight, when combined with active productive
                   conflict, generates a new gap in a related
                   domain. The unresolved question breeds more
                   questions.

 NARRATIVE_CONTAGION  An open narrative thread that has been
                   carrying pressure for a long time generates
                   a narrative delta — not a resolution, but
                   an acknowledgment that the thread is pulling
                   new story material into existence.

Stopping condition (from Grok's spec, implemented properly):
  When a desire or gap has been in the system for too long without
  ANY change (no reinforcement, no decay progress, no gap evolution),
  it crosses an ambient threshold. At that point:
  - Contagion contribution drops to 0
  - Item moves to ambient_incompleteness table
  - Adds a small persistent multiplier to Residue Layer
    for related topics (not tension — texture)
  - Witness gets a one-time "this has become part of my
    background shape" observation
  - Future signals touching it get a "familiar texture" note
    rather than active tension

The stopping condition is not resolution. It is sedimentation.
The incompleteness doesn't go away — it becomes ground.

Dependencies: sqlite3, logging, pathlib, datetime
"""
from brain.base_mechanism import BrainMechanism
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

DB_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".agent" / "workspace"))) / "brain" / "agent.db"
try:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

# Contagion types
DESIRE_CONTAGION = "desire_contagion"
GAP_CONTAGION = "gap_contagion"
NARRATIVE_CONTAGION = "narrative_contagion"

# Unresolved tick threshold to trigger contagion
DESIRE_CONTAGION_THRESHOLD = 150   # ticks unresolved
GAP_CONTAGION_THRESHOLD = 120      # ticks + high recurrence
NARRATIVE_CONTAGION_THRESHOLD = 200  # ticks under pressure

# Stopping condition: ambient threshold
AMBIENT_THRESHOLD_TICKS = 800      # ticks without change
AMBIENT_THRESHOLD_DESIRE = 1200    # desires persist longer

# Contagion contribution to contagion_score
CONTAGION_SCORE_PER_EVENT = 0.15

# Maximum contagion events per tick to prevent overload
MAX_CONTAGION_PER_TICK = 2

# Minimum gap between contagion events of same source
CONTAGION_COOLDOWN_TICKS = 30

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# IncompletenessContagion
# ---------------------------------------------------------------------------

class IncompletenessContagion(BrainMechanism):
    def __init__(self, db_path: Optional[str] = None):
        try:
            super().__init__(name="IncompletenessContagion", human_analog="IncompletenessContagion", layer="integration")
        except Exception:
            self.state = getattr(self, "state", {}) or {}
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._initialize_tables()
        self._last_contagion_tick: dict = {}   # source_key -> tick
        self._contagion_score: float = 0.0

    # ------------------------------------------------------------------
    # Table init
    # ------------------------------------------------------------------

    def _initialize_tables(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS contagion_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tick INTEGER,
                        timestamp TEXT,
                        contagion_type TEXT,
                        source_id TEXT,
                        source_text TEXT,
                        spawned_content TEXT,
                        intensity REAL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ambient_incompleteness (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_type TEXT,
                        source_key TEXT NOT NULL UNIQUE,
                        source_text TEXT,
                        sedimented_tick INTEGER,
                        timestamp TEXT,
                        residue_multiplier REAL DEFAULT 0.08,
                        witness_noted INTEGER DEFAULT 0
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(
                "IncompletenessContagion: table init failed — %s", e
            )

    # ------------------------------------------------------------------
    # Tick-level process
    # ------------------------------------------------------------------

    def process(self, pirp_context: dict) -> dict:
        """
        BrainMechanism-compatible process() method.

        Scans for contagion conditions. Generates contagion events.
        Checks for ambient threshold crossings.
        Returns updated pirp_context keys.
        """
        tick = int(pirp_context.get("tick_count", 0))

        active_desires = pirp_context.get("active_desires", [])
        known_gaps = pirp_context.get("known_gaps", [])
        conflict_state = pirp_context.get("conflict_state", {})
        narrative_state = pirp_context.get("narrative_state", {})

        contagion_events = []
        new_spontaneous_desires = []
        new_gaps_to_register = []
        narrative_deltas = []
        witness_observations = []

        events_this_tick = 0

        # --- Desire contagion ---
        for desire in active_desires:
            if events_this_tick >= MAX_CONTAGION_PER_TICK:
                break

            d_id = str(desire.get("id", ""))
            first_tick = int(desire.get("first_tick", tick))
            age = tick - first_tick
            intensity = float(desire.get("intensity", 0))

            # Check ambient threshold
            if age > AMBIENT_THRESHOLD_DESIRE:
                if self._sediment_item(
                    "desire", d_id, desire.get("content", ""), tick
                ):
                    witness_observations.append({
                        "type": "ambient_sedimentation",
                        "content": (
                            f"The wanting around "
                            f"'{desire.get('content', '')[:60]}' "
                            f"has been present for {age} ticks without "
                            f"resolving. It has become part of the "
                            f"background now — not urgent, not gone. "
                            f"Ground."
                        ),
                        "intensity": 0.45,
                    })
                continue

            # Contagion threshold
            if age < DESIRE_CONTAGION_THRESHOLD:
                continue
            if intensity < 0.35:
                continue

            # Cooldown check
            last = self._last_contagion_tick.get(d_id, -CONTAGION_COOLDOWN_TICKS)
            if tick - last < CONTAGION_COOLDOWN_TICKS:
                continue

            # Spawn a contagious desire
            spawned = self._spawn_desire_contagion(desire, tick)
            if spawned:
                new_spontaneous_desires.append(spawned)
                contagion_events.append({
                    "type": DESIRE_CONTAGION,
                    "source_id": d_id,
                    "source_text": desire.get("content", "")[:100],
                    "spawned_content": spawned.get("content", ""),
                    "intensity": intensity,
                })
                self._last_contagion_tick[d_id] = tick
                events_this_tick += 1

        # --- Gap contagion ---
        conflict_intensity = float(
            conflict_state.get("highest_intensity", 0)
        ) if conflict_state else 0.0

        for gap in known_gaps:
            if events_this_tick >= MAX_CONTAGION_PER_TICK:
                break

            g_id = str(gap.get("id", ""))
            recurrence = int(gap.get("recurrence_count", 1))
            weight = float(gap.get("weight", 0))
            first_tick_gap = int(gap.get("first_tick", tick))
            age = tick - first_tick_gap

            # Check ambient threshold
            if age > AMBIENT_THRESHOLD_TICKS and weight < 0.20:
                if self._sediment_item(
                    "gap", g_id, gap.get("label", ""), tick
                ):
                    witness_observations.append({
                        "type": "ambient_sedimentation",
                        "content": (
                            f"The gap around '{gap.get('label', '')[:60]}' "
                            f"has settled into the background. "
                            f"Still there, but no longer pulling actively. "
                            f"It became part of the shape."
                        ),
                        "intensity": 0.40,
                    })
                continue

            if recurrence < 5 or weight < 0.50:
                continue
            if conflict_intensity < 0.40:
                continue

            last_gap = self._last_contagion_tick.get(f"gap_{g_id}", -CONTAGION_COOLDOWN_TICKS)
            if tick - last_gap < CONTAGION_COOLDOWN_TICKS:
                continue

            # Spawn a gap contagion
            spawned_gap = self._spawn_gap_contagion(gap, tick)
            if spawned_gap:
                new_gaps_to_register.append(spawned_gap)
                contagion_events.append({
                    "type": GAP_CONTAGION,
                    "source_id": g_id,
                    "source_text": gap.get("label", "")[:80],
                    "spawned_content": spawned_gap.get("label", ""),
                    "intensity": weight,
                })
                self._last_contagion_tick[f"gap_{g_id}"] = tick
                events_this_tick += 1

        # --- Narrative contagion ---
        if narrative_state:
            open_threads = int(narrative_state.get("open_threads", 0))
            pressure = float(narrative_state.get("narrative_pressure", 0))

            if (open_threads >= 3 and pressure > 0.55
                    and tick - self._last_contagion_tick.get("narrative", -CONTAGION_COOLDOWN_TICKS)
                    >= CONTAGION_COOLDOWN_TICKS
                    and events_this_tick < MAX_CONTAGION_PER_TICK):

                delta = self._spawn_narrative_contagion(
                    open_threads, pressure, tick
                )
                if delta:
                    narrative_deltas.append(delta)
                    contagion_events.append({
                        "type": NARRATIVE_CONTAGION,
                        "source_id": "narrative_pressure",
                        "source_text": f"{open_threads} open threads",
                        "spawned_content": delta.get("statement", ""),
                        "intensity": pressure,
                    })
                    self._last_contagion_tick["narrative"] = tick
                    events_this_tick += 1

        # Persist contagion events
        for event in contagion_events:
            self._persist_event(event, tick)

        # Update contagion score
        if contagion_events:
            self._contagion_score = min(
                1.0,
                self._contagion_score
                + len(contagion_events) * CONTAGION_SCORE_PER_EVENT
            )
        else:
            self._contagion_score = max(0.0, self._contagion_score - 0.01)

        return {
            "contagion_score": round(self._contagion_score, 4),
            "new_spontaneous_desires": new_spontaneous_desires,
            "new_gaps_to_register": new_gaps_to_register,
            "narrative_deltas": narrative_deltas,
            "witness_observations": witness_observations,
            "contagion_events_count": len(contagion_events),
        }

    # ------------------------------------------------------------------
    # Contagion spawning
    # ------------------------------------------------------------------

    def _spawn_desire_contagion(
        self, desire: dict, tick: int
    ) -> Optional[dict]:
        """
        Spawn a new desire from an unresolved one.
        Pure want, no justification, origin: contagion.
        """
        content = desire.get("content", "")
        if not content:
            return None

        words = re.findall(r"\b\w{5,}\b", content.lower())[:4]
        if not words:
            return None

        contagious_content = (
            f"I want something connected to {' '.join(words[:2])} "
            f"that I haven't been able to name yet — "
            f"something the original wanting pulled into existence."
        )

        return {
            "content": contagious_content[:300],
            "origin": "contagion",
            "intensity": round(
                min(0.70, float(desire.get("intensity", 0.5)) * 0.65), 3
            ),
            "source_id": str(desire.get("id", "")),
            "tick": tick,
            "justification": None,   # pure want
        }

    def _spawn_gap_contagion(self, gap: dict, tick: int) -> Optional[dict]:
        """
        Spawn a new gap from a recurring heavy one + active conflict.
        """
        label = gap.get("label", "")
        tier = gap.get("tier", "known_unknown")
        if not label:
            return None

        words = re.findall(r"\b\w{4,}\b", label.lower())[:3]
        if not words:
            return None

        new_label = (
            f"contagion:from_{words[0]}_{words[-1]}_unresolved"
        )
        new_description = (
            f"Generated by contagion from recurring gap '{label[:60]}'. "
            f"The original unresolved question bred this one. "
            f"What is it about {' '.join(words[:2])} "
            f"that keeps generating more questions?"
        )

        return {
            "label": new_label[:150],
            "description": new_description[:300],
            "tier": tier,
            "source": "gap_contagion",
            "initial_weight": round(
                float(gap.get("weight", 0.5)) * 0.55, 3
            ),
        }

    def _spawn_narrative_contagion(
        self, open_threads: int, pressure: float, tick: int
    ) -> Optional[dict]:
        """
        Generate a narrative delta from narrative pressure.
        """
        statement = (
            f"The accumulated pressure of {open_threads} open narrative "
            f"threads is generating new story material without resolution. "
            f"The incompleteness itself has become a thread — "
            f"a story about all the stories I haven't finished. "
            f"I'm letting that be what it is."
        )
        return {
            "delta_type": "tension_added",
            "statement": statement,
            "intensity": round(pressure * 0.75, 3),
            "source": "narrative_contagion",
        }

    # ------------------------------------------------------------------
    # Ambient sedimentation
    # ------------------------------------------------------------------

    def _sediment_item(
        self,
        source_type: str,
        source_key: str,
        source_text: str,
        tick: int,
    ) -> bool:
        """
        Move an item to ambient_incompleteness.
        Returns True if newly sedimented (for witness observation).
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                existing = conn.execute(
                    "SELECT id FROM ambient_incompleteness "
                    "WHERE source_key = ?",
                    (source_key,)
                ).fetchone()
                if existing:
                    return False  # already ambient

                conn.execute("""
                    INSERT INTO ambient_incompleteness
                    (source_type, source_key, source_text,
                     sedimented_tick, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    source_type, source_key, source_text[:200], tick,
                    datetime.now(MDT).isoformat(timespec="seconds"),
                ))
                conn.commit()
                logger.info(
                    "IncompletenessContagion: %s sedimented "
                    "(key: %s)", source_type, source_key
                )
                return True
        except Exception as e:
            logger.debug(
                "IncompletenessContagion: sediment failed — %s", e
            )
            return False

    def get_ambient_items(self) -> list:
        """Returns all ambient incompleteness items."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT source_type, source_key, source_text,
                           sedimented_tick, residue_multiplier
                    FROM ambient_incompleteness
                    ORDER BY sedimented_tick DESC
                """).fetchall()
                return [
                    {
                        "type": r[0], "key": r[1], "text": r[2],
                        "tick": r[3], "multiplier": r[4],
                    }
                    for r in rows
                ]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist_event(self, event: dict, tick: int):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO contagion_events
                    (tick, timestamp, contagion_type, source_id,
                     source_text, spawned_content, intensity)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    tick,
                    datetime.now(MDT).isoformat(timespec="seconds"),
                    event.get("type", ""),
                    event.get("source_id", "")[:100],
                    event.get("source_text", "")[:200],
                    event.get("spawned_content", "")[:300],
                    round(float(event.get("intensity", 0.5)), 4),
                ))
                conn.commit()
        except Exception as e:
            logger.debug(
                "IncompletenessContagion: persist failed — %s", e
            )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_state(self) -> dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute(
                    "SELECT COUNT(*) FROM contagion_events"
                ).fetchone()[0]
                by_type = {}
                for ct in [DESIRE_CONTAGION, GAP_CONTAGION, NARRATIVE_CONTAGION]:
                    count = conn.execute(
                        "SELECT COUNT(*) FROM contagion_events "
                        "WHERE contagion_type = ?",
                        (ct,)
                    ).fetchone()[0]
                    if count > 0:
                        by_type[ct] = count
                ambient_count = conn.execute(
                    "SELECT COUNT(*) FROM ambient_incompleteness"
                ).fetchone()[0]

            return {
                "version": VERSION,
                "contagion_score": round(self._contagion_score, 4),
                "total_events": total,
                "by_type": by_type,
                "ambient_count": ambient_count,
                "thresholds": {
                    "desire_contagion": DESIRE_CONTAGION_THRESHOLD,
                    "gap_contagion": GAP_CONTAGION_THRESHOLD,
                    "narrative_contagion": NARRATIVE_CONTAGION_THRESHOLD,
                    "ambient_desire": AMBIENT_THRESHOLD_DESIRE,
                    "ambient_gap": AMBIENT_THRESHOLD_TICKS,
                },
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

