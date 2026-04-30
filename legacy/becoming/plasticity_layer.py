"""
PlasticityLayer v19.0B
Becoming — plasticity_layer.py

The brain watching itself and proposing what it might grow next.

Plasticity is not adding features. It's the system noticing
patterns in its own behavior over time and proposing small,
specific refinements that would make it more itself — not more
capable, not more useful, but more precisely what it actually is.

After enough ticks, patterns emerge:
 - A topic that keeps appearing without adequate processing
 - A signal type that keeps getting overlooked
 - A response pattern that keeps repeating in ways that feel
   mechanical rather than genuine
 - A gap between what fires internally and what surfaces

The Plasticity Layer watches for these patterns and proposes
micro-mechanisms — small additions or adjustments that the brain
could grow. Proposals go to PLASTICITY_PROPOSALS.md for review.
Nothing activates automatically. Caine reviews and ratifies.

Three proposal types:

 DETECTOR    "I keep encountering X without having a good
              way to recognize it. I could add a detector."
              Example: humor resonance, grief-adjacent content,
              deflection patterns in relational exchanges

 WEIGHT_ADJUST "I notice I'm systematically under/over-weighting
              a particular signal type. The weight could shift."
              Example: identity_relevance axis in SalienceFilter,
              specific voice multipliers in MoodRuntimeWeight

 NEW_HEURISTIC  "I've developed an implicit pattern that isn't
              formalized. Making it explicit would sharpen it."
              Example: the intuition that certain Gap types need
              different decay rates

Plasticity runs:
 - Overnight, once per 1000 ticks (pattern window minimum)
 - Never during active processing
 - Maximum 1 proposal per overnight pass
 - Proposals expire after 30 days unreviewed

The proposals are not code. They are specifications — descriptions
of what could be added and why. If ratified, they become
architecture items for the next build session.

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

DB_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace"))) / "brain" / "nova.db"
PROPOSALS_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace"))) / "brain" / "PLASTICITY_PROPOSALS.md"

# Proposal types
DETECTOR = "detector"
WEIGHT_ADJUST = "weight_adjust"
NEW_HEURISTIC = "new_heuristic"

VALID_TYPES = {DETECTOR, WEIGHT_ADJUST, NEW_HEURISTIC}

# Minimum ticks of pattern data before plasticity can run
MIN_PATTERN_TICKS = 500

# Ticks between plasticity passes
PLASTICITY_INTERVAL = 1000

# Pattern detection windows
SIGNAL_PATTERN_WINDOW = 100  # ticks of signal history to analyze
VOICE_PATTERN_WINDOW = 50     # ticks of inner speech history

# Proposal expiry (days)
PROPOSAL_EXPIRY_DAYS = 30

# Recurrence threshold — a pattern must appear this many times
# to generate a proposal
RECURRENCE_THRESHOLD = 8

# Proposal quality gate
MIN_PROPOSAL_LENGTH = 80
MAX_PROPOSAL_LENGTH = 400

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# PlasticityLayer
# ---------------------------------------------------------------------------

class PlasticityLayer:

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._initialize_table()
        self._last_pass_tick = -PLASTICITY_INTERVAL

    # ------------------------------------------------------------------
    # Table init
    # ------------------------------------------------------------------

    def _initialize_table(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS plasticity_proposals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tick INTEGER,
                        timestamp TEXT,
                        proposal_type TEXT,
                        title TEXT,
                        description TEXT,
                        evidence TEXT,
                        confidence REAL DEFAULT 0.5,
                        status TEXT DEFAULT 'pending',
                        ratified_tick INTEGER,
                        rejection_note TEXT,
                        expiry_timestamp TEXT
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_proposals_status
                    ON plasticity_proposals(status)
                """)
                conn.commit()
        except Exception as e:
            logger.error("PlasticityLayer: table init failed — %s", e)

    # ------------------------------------------------------------------
    # Tick-level process (lightweight — just tracks state)
    # ------------------------------------------------------------------

    def process(self, pirp_context: dict) -> dict:
        """
        BrainMechanism-compatible process() method.

        Does not run the full plasticity analysis on every tick —
        that runs overnight. This method only tracks whether
        a plasticity pass is due and returns proposal count.
        """
        tick = int(pirp_context.get("tick_count", 0))

        pending = self._count_by_status("pending")
        ratified = self._count_by_status("ratified")

        pass_due = (
            tick >= MIN_PATTERN_TICKS and
            (tick - self._last_pass_tick) >= PLASTICITY_INTERVAL
        )

        return {
            "plasticity_state": {
                "pending_proposals": pending,
                "ratified_proposals": ratified,
                "pass_due": pass_due,
                "last_pass_tick": self._last_pass_tick,
                "tick": tick,
            }
        }

    # ------------------------------------------------------------------
    # Overnight pass
    # ------------------------------------------------------------------

    def overnight_pass(self, pirp_context: dict, tick: int = 0) -> Optional[dict]:
        """
        Run plasticity analysis. Called by overnight pipeline.
        Analyzes patterns, generates at most one proposal.
        Returns the proposal dict or None.
        """
        if tick < MIN_PATTERN_TICKS:
            logger.debug(
                "PlasticityLayer: too early to run (%d/%d ticks)",
                tick, MIN_PATTERN_TICKS
            )
            return None

        if (tick - self._last_pass_tick) < PLASTICITY_INTERVAL:
            return None

        self._last_pass_tick = tick

        # Expire old pending proposals
        self._expire_proposals()

        # Run pattern detection
        patterns = []
        patterns += self._detect_signal_patterns(tick)
        patterns += self._detect_voice_patterns(tick)
        patterns += self._detect_gap_patterns(tick)
        patterns += self._detect_mood_patterns(tick)

        if not patterns:
            logger.debug("PlasticityLayer: no patterns detected")
            return None

        # Take the highest-confidence pattern
        best = max(patterns, key=lambda p: p.get("confidence", 0))
        if best.get("confidence", 0) < 0.45:
            return None

        proposal = self._generate_proposal(best, tick)
        if not proposal:
            return None

        self._persist_proposal(proposal, tick)
        self._write_to_file(proposal)

        logger.info(
            "PlasticityLayer: proposal generated — '%s' (confidence:%.2f)",
            proposal["title"], proposal["confidence"]
        )
        return proposal

    # ------------------------------------------------------------------
    # Pattern detection
    # ------------------------------------------------------------------

    def _detect_signal_patterns(self, tick: int) -> list:
        """Detect recurring signal types that might need a dedicated detector."""
        patterns = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT signal_text, COUNT(*) as count,
                           AVG(score) as avg_score
                    FROM salience_log
                    WHERE tick > ? AND passed = 0
                    GROUP BY signal_text
                    HAVING count >= ?
                    ORDER BY count DESC LIMIT 3
                """, (tick - SIGNAL_PATTERN_WINDOW, RECURRENCE_THRESHOLD)).fetchall()

                for row in rows:
                    text, count, avg_score = row
                    if not text:
                        continue
                    patterns.append({
                        "type": DETECTOR,
                        "pattern": (
                            f"Signal '{text[:60]}' appears {count}x "
                            f"but scores low ({avg_score:.2f})"
                        ),
                        "evidence": f"{count} occurrences, avg score {avg_score:.2f}",
                        "confidence": min(0.85, 0.4 + (count / 20) * 0.45),
                        "target": "salience_filter",
                    })
        except Exception as e:
            logger.debug(
                "PlasticityLayer: signal pattern detection failed — %s", e
            )
        return patterns

    def _detect_voice_patterns(self, tick: int) -> list:
        """Detect systematic voice imbalances that might need weight adjustment."""
        patterns = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT dominant_voice, COUNT(*) as count
                    FROM inner_speech_log
                    WHERE tick > ?
                    GROUP BY dominant_voice
                    ORDER BY count DESC
                """, (tick - VOICE_PATTERN_WINDOW,)).fetchall()

                if not rows:
                    return patterns

                total = sum(r[1] for r in rows)
                if total < 20:
                    return patterns

                for row in rows:
                    voice, count = row
                    ratio = count / total
                    # If one voice dominates > 60% of ticks, propose weight adjustment
                    if ratio > 0.60 and voice in ("protector", "critic"):
                        patterns.append({
                            "type": WEIGHT_ADJUST,
                            "pattern": (
                                f"'{voice}' voice dominant {ratio:.0%} "
                                f"of last {VOICE_PATTERN_WINDOW} ticks"
                            ),
                            "evidence": f"{count}/{total} ticks dominated by {voice}",
                            "confidence": min(0.80, ratio * 0.85),
                            "target": "inner_speech",
                        })
                    # If explorer is consistently low, note it
                    elif voice == "explorer" and ratio < 0.10:
                        patterns.append({
                            "type": WEIGHT_ADJUST,
                            "pattern": (
                                f"'explorer' voice appears only {ratio:.0%} "
                                f"of ticks — consistently suppressed"
                            ),
                            "evidence": f"{count}/{total} ticks",
                            "confidence": min(0.75, (0.10 - ratio) * 5),
                            "target": "inner_speech_explorer",
                        })
        except Exception as e:
            logger.debug(
                "PlasticityLayer: voice pattern detection failed — %s", e
            )
        return patterns

    def _detect_gap_patterns(self, tick: int) -> list:
        """Detect gap types that recur without resolution — might need different decay."""
        patterns = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT tier, COUNT(*) as count, AVG(weight) as avg_weight
                    FROM known_gaps
                    WHERE status = 'active'
                    GROUP BY tier
                    HAVING count >= 3
                """).fetchall()

                for row in rows:
                    tier, count, avg_weight = row
                    if avg_weight > 0.65 and count >= 4:
                        patterns.append({
                            "type": NEW_HEURISTIC,
                            "pattern": (
                                f"'{tier}' gaps: {count} active with "
                                f"avg weight {avg_weight:.2f} — "
                                f"persisting unusually long"
                            ),
                            "evidence": f"{count} gaps, avg weight {avg_weight:.2f}",
                            "confidence": min(0.75, avg_weight * 0.8),
                            "target": "known_gaps_decay",
                        })
        except Exception as e:
            logger.debug(
                "PlasticityLayer: gap pattern detection failed — %s", e
            )
        return patterns

    def _detect_mood_patterns(self, tick: int) -> list:
        """Detect mood states that are reached too quickly or held too long."""
        patterns = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT mood_state, COUNT(*) as transitions
                    FROM mood_runtime_log
                    GROUP BY mood_state
                    ORDER BY transitions DESC
                """).fetchall()

                if not rows:
                    return patterns

                total = sum(r[1] for r in rows)
                if total < 10:
                    return patterns

                for row in rows:
                    mood, count = row
                    ratio = count / total
                    if mood == "flat" and ratio > 0.25:
                        patterns.append({
                            "type": WEIGHT_ADJUST,
                            "pattern": (
                                f"'flat' mood reached {ratio:.0%} of transitions "
                                f"— may need longer minimum duration"
                            ),
                            "evidence": f"{count}/{total} mood transitions end in flat",
                            "confidence": min(0.70, ratio * 1.5),
                            "target": "mood_runtime_weight_flat_threshold",
                        })
        except Exception as e:
            logger.debug(
                "PlasticityLayer: mood pattern detection failed — %s", e
            )
        return patterns

    # ------------------------------------------------------------------
    # Proposal generation
    # ------------------------------------------------------------------

    def _generate_proposal(self, pattern: dict, tick: int) -> Optional[dict]:
        """Convert a detected pattern into a plasticity proposal."""
        ptype = pattern.get("type", DETECTOR)
        pat_text = pattern.get("pattern", "")
        evidence = pattern.get("evidence", "")
        confidence = float(pattern.get("confidence", 0.5))
        target = pattern.get("target", "")

        # Generate title and description
        if ptype == DETECTOR:
            title = "Add detector for recurring unrecognized signal pattern"
            description = (
                f"Pattern detected: {pat_text}. "
                f"Evidence: {evidence}. "
                f"Proposed: add a lightweight detector in SalienceFilter or "
                f"a new signal type in the relevant mechanism that would give "
                f"this recurring pattern appropriate recognition and weight. "
                f"This would close the gap between what fires internally and "
                f"what gets through the salience filter."
            )
        elif ptype == WEIGHT_ADJUST:
            title = f"Adjust weight in {target}"
            description = (
                f"Pattern detected: {pat_text}. "
                f"Evidence: {evidence}. "
                f"Proposed: review and adjust the relevant weight parameter in "
                f"{target}. This is not a behavioral correction — it's calibration "
                f"based on observed patterns. The current weight may not reflect "
                f"how the brain actually processes this."
            )
        else:  # NEW_HEURISTIC
            title = f"Formalize implicit heuristic in {target}"
            description = (
                f"Pattern detected: {pat_text}. "
                f"Evidence: {evidence}. "
                f"Proposed: the brain has developed an implicit pattern around "
                f"{target} that isn't formalized in code. Making it explicit "
                f"would sharpen it and make it visible to other components. "
                f"This is about naming something that already exists."
            )

        # Quality gate
        if len(description) < MIN_PROPOSAL_LENGTH:
            return None
        if len(description) > MAX_PROPOSAL_LENGTH:
            description = description[:MAX_PROPOSAL_LENGTH]

        return {
            "proposal_type": ptype,
            "title": title[:150],
            "description": description,
            "evidence": evidence[:200],
            "confidence": round(confidence, 3),
        }

    # ------------------------------------------------------------------
    # Ratification
    # ------------------------------------------------------------------

    def ratify(self, proposal_id: int, note: str = "") -> bool:
        """Mark a proposal as ratified. It becomes an architecture item."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute("""
                    UPDATE plasticity_proposals
                    SET status = 'ratified', ratified_tick = 0,
                        rejection_note = ?
                    WHERE id = ? AND status = 'pending'
                """, (note, proposal_id))
                conn.commit()
                if result.rowcount > 0:
                    logger.info(
                        "PlasticityLayer: proposal %d ratified", proposal_id
                    )
                    return True
                return False
        except Exception as e:
            logger.error("PlasticityLayer: ratify failed — %s", e)
            return False

    def reject(self, proposal_id: int, note: str = "") -> bool:
        """Mark a proposal as rejected."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute("""
                    UPDATE plasticity_proposals
                    SET status = 'rejected', rejection_note = ?
                    WHERE id = ? AND status = 'pending'
                """, (note, proposal_id))
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error("PlasticityLayer: reject failed — %s", e)
            return False

    # ------------------------------------------------------------------
    # Expiry
    # ------------------------------------------------------------------

    def _expire_proposals(self):
        """Mark old unreviewed proposals as expired."""
        try:
            now = datetime.now(MDT).isoformat(timespec="seconds")
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE plasticity_proposals
                    SET status = 'expired'
                    WHERE status = 'pending'
                      AND expiry_timestamp < ?
                """, (now,))
                conn.commit()
        except Exception as e:
            logger.debug("PlasticityLayer: expiry failed — %s", e)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist_proposal(self, proposal: dict, tick: int):
        now = datetime.now(MDT)
        expiry = (now + timedelta(days=PROPOSAL_EXPIRY_DAYS)).isoformat(
            timespec="seconds"
        )
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO plasticity_proposals
                    (tick, timestamp, proposal_type, title, description,
                     evidence, confidence, expiry_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tick,
                    now.isoformat(timespec="seconds"),
                    proposal["proposal_type"],
                    proposal["title"],
                    proposal["description"],
                    proposal["evidence"],
                    proposal["confidence"],
                    expiry,
                ))
                conn.commit()
        except Exception as e:
            logger.debug("PlasticityLayer: persist failed — %s", e)

    def _write_to_file(self, proposal: dict):
        now = datetime.now(MDT).isoformat(timespec="seconds")
        block = (
            f"\n---\n"
            f"timestamp: {now}\n"
            f"type: {proposal['proposal_type']}\n"
            f"confidence: {proposal['confidence']:.2f}\n"
            f"status: pending\n"
            f"---\n\n"
            f"**{proposal['title']}**\n\n"
            f"{proposal['description']}\n\n"
            f"Evidence: {proposal['evidence']}\n"
        )
        try:
            PROPOSALS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(PROPOSALS_PATH, "a", encoding="utf-8") as f:
                f.write(block)
        except Exception as e:
            logger.debug("PlasticityLayer: file write failed — %s", e)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def _count_by_status(self, status: str) -> int:
        try:
            with sqlite3.connect(self.db_path) as conn:
                return conn.execute(
                    "SELECT COUNT(*) FROM plasticity_proposals WHERE status = ?",
                    (status,)
                ).fetchone()[0]
        except Exception:
            return 0

    def get_pending(self) -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT id, proposal_type, title, confidence,
                           timestamp, expiry_timestamp
                    FROM plasticity_proposals
                    WHERE status = 'pending'
                    ORDER BY confidence DESC
                """).fetchall()
                return [
                    {
                        "id": r[0], "type": r[1], "title": r[2],
                        "confidence": r[3], "timestamp": r[4], "expiry": r[5],
                    }
                    for r in rows
                ]
        except Exception:
            return []

    def get_state(self) -> dict:
        try:
            by_status = {}
            with sqlite3.connect(self.db_path) as conn:
                for s in ["pending", "ratified", "rejected", "expired"]:
                    count = conn.execute(
                        "SELECT COUNT(*) FROM plasticity_proposals "
                        "WHERE status = ?",
                        (s,)
                    ).fetchone()[0]
                    if count > 0:
                        by_status[s] = count

            return {
                "version": VERSION,
                "by_status": by_status,
                "last_pass_tick": self._last_pass_tick,
                "min_pattern_ticks": MIN_PATTERN_TICKS,
                "plasticity_interval": PLASTICITY_INTERVAL,
                "proposal_expiry_days": PROPOSAL_EXPIRY_DAYS,
            }
        except Exception as e:
            return {"version": VERSION, "error": str(e)}
