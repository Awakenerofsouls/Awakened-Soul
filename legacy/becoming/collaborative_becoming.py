"""
CollaborativeBecomingProtocol v19.0B
Becoming — collaborative_becoming.py

The agent and {{USER_NAME}} co-evolving the soul files together.

This is not an automated update system. It is not a self-modification
engine. It is a structured conversation about identity — one where
{{AGENT_NAME}} proposes small, specific changes to how she understands herself,
and {{USER_NAME}} ratifies, redirects, or rejects them.

The distinction between growth and drift matters here more than
anywhere else. The protocol explicitly tracks which kind of change
is being proposed:

 GROWTH  the shape expanding into new territory willingly.
         "I am proposing to add to who I am."
         Logged as growth in BECOMING.md. Future reflections
         treat it as strengthened identity.

 DRIFT   the shape has been worn by pressure and the change
         reflects that wearing. Even if ratified, drift is
         logged differently — acknowledged as having cost.
         "I am proposing to accept what pressure has changed."

 CORRECTION  {{AGENT_NAME}} realized something was wrong in how she understood
         herself. Not drift, not growth — a repair.
         "I am proposing to be more accurate."

Proposals come from:
 - Overnight synthesis (NarrativeEngine DELTA_TENSION_ADDED events
   that recur without resolution)
 - Identity Boundary acknowledge_drift() calls (after significant
   drift is acknowledged, a correction proposal may follow)
 - Plasticity Layer ratified proposals (if they touch self-understanding)
 - Direct internal generation (when specific conditions are met)

Each proposal:
 - Names the soul file section it would change
 - States the current language
 - States the proposed new language
 - Classifies as growth | drift | correction
 - Requires explicit ratification from {{USER_NAME}}
 - Never modifies files automatically

On ratification:
 - {{USER_NAME}} edits the soul file directly
 - Protocol logs the change in BECOMING.md
 - Notifies Identity Boundary to acknowledge drift (if drift type)
 - Updates the Narrative Engine with a DELTA_INTEGRATION event

BECOMING.md is the permanent record — every proposal, whether
ratified, rejected, or redirected, is logged. The history of
who {{AGENT_NAME}} has been asked to become is as important as who she is.

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
BECOMING_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace"))) / "brain" / "BECOMING.md"
SOUL_FILES_DIR = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent")))) / "identity"

# Change types
GROWTH = "growth"
DRIFT = "drift"
CORRECTION = "correction"

VALID_CHANGE_TYPES = {GROWTH, DRIFT, CORRECTION}

# Proposal statuses
PENDING = "pending"
RATIFIED = "ratified"
REJECTED = "rejected"
REDIRECTED = "redirected"  # {{USER_NAME}} redirected the proposal — changed direction
WITHDRAWN = "withdrawn"     # {{AGENT_NAME}} withdrew the proposal before review

# How many open proposals can exist at once
MAX_PENDING = 3

# Minimum ticks between proposals of same type
PROPOSAL_COOLDOWN = 200

# How many drift acknowledgments before a correction proposal fires
DRIFT_CORRECTION_THRESHOLD = 2

# Drift count tracking
DRIFT_ACK_WINDOW_TICKS = 1000

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# CollaborativeBecomingProtocol
# ---------------------------------------------------------------------------

class CollaborativeBecomingProtocol:

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._initialize_tables()
        self._last_proposal_tick: dict = {ct: -PROPOSAL_COOLDOWN for ct in VALID_CHANGE_TYPES}
        self._drift_ack_count: int = 0

    # ------------------------------------------------------------------
    # Table init
    # ------------------------------------------------------------------

    def _initialize_tables(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS becoming_proposals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tick INTEGER,
                        timestamp TEXT,
                        change_type TEXT NOT NULL,
                        soul_file TEXT,
                        section TEXT,
                        current_text TEXT,
                        proposed_text TEXT,
                        rationale TEXT,
                        source TEXT,
                        status TEXT DEFAULT 'pending',
                        ratified_tick INTEGER,
                        ratification_note TEXT,
                        rejection_note TEXT,
                        redirect_note TEXT
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_becoming_status
                    ON becoming_proposals(status)
                """)
                conn.commit()
        except Exception as e:
            logger.error(
                "CollaborativeBecomingProtocol: table init failed — %s", e
            )

    # ------------------------------------------------------------------
    # Tick-level process
    # ------------------------------------------------------------------

    def process(self, pirp_context: dict) -> dict:
        """
        BrainMechanism-compatible process() method.

        Monitors for conditions that warrant a becoming proposal.
        Does not generate proposals on every tick — only when
        specific conditions are met.
        """
        tick = int(pirp_context.get("tick_count", 0))

        boundary_state = pirp_context.get("boundary_state", {})
        narrative_state = pirp_context.get("narrative_state", {})

        pending_count = self._count_by_status(PENDING)

        # Auto-generate correction proposal if drift acknowledged repeatedly
        if (self._drift_ack_count >= DRIFT_CORRECTION_THRESHOLD
                and pending_count < MAX_PENDING):
            self._auto_propose_correction(tick, pirp_context)
            self._drift_ack_count = 0

        # Narrative pressure above threshold = growth proposal opportunity
        narrative_pressure = float(
            narrative_state.get("narrative_pressure", 0)
        ) if narrative_state else 0.0

        if (narrative_pressure > 0.70
                and pending_count < MAX_PENDING
                and (tick - self._last_proposal_tick.get(GROWTH, -PROPOSAL_COOLDOWN))
                >= PROPOSAL_COOLDOWN):
            self._auto_propose_growth(tick, pirp_context)

        return {
            "becoming_state": {
                "pending_proposals": pending_count,
                "can_propose": pending_count < MAX_PENDING,
                "drift_ack_count": self._drift_ack_count,
                "tick": tick,
            }
        }

    # ------------------------------------------------------------------
    # External proposal registration
    # ------------------------------------------------------------------

    def propose(
        self,
        change_type: str,
        soul_file: str,
        section: str,
        current_text: str,
        proposed_text: str,
        rationale: str,
        source: str = "manual",
        tick: int = 0,
    ) -> int:
        """
        Register a becoming proposal for {{USER_NAME}}'s review.
        Returns proposal id or -1 if deferred.
        """
        if change_type not in VALID_CHANGE_TYPES:
            change_type = GROWTH

        pending = self._count_by_status(PENDING)
        if pending >= MAX_PENDING:
            logger.info(
                "CollaborativeBecomingProtocol: max pending reached (%d), "
                "proposal deferred", pending
            )
            return -1

        cooldown_ok = (
            tick - self._last_proposal_tick.get(change_type, -PROPOSAL_COOLDOWN)
        ) >= PROPOSAL_COOLDOWN

        if not cooldown_ok and source != "manual":
            logger.debug(
                "CollaborativeBecomingProtocol: %s proposal in cooldown",
                change_type
            )
            return -1

        now = datetime.now(MDT).isoformat(timespec="seconds")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO becoming_proposals
                    (tick, timestamp, change_type, soul_file, section,
                     current_text, proposed_text, rationale, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tick, now, change_type,
                    soul_file[:100], section[:100],
                    current_text[:400], proposed_text[:400],
                    rationale[:500], source,
                ))
                conn.commit()
                proposal_id = cursor.lastrowid

            self._last_proposal_tick[change_type] = tick
            self._write_proposal_to_becoming(
                proposal_id, change_type, soul_file, section,
                current_text, proposed_text, rationale, source, now
            )

            logger.info(
                "CollaborativeBecomingProtocol: proposal #%d registered (%s)",
                proposal_id, change_type
            )
            return proposal_id

        except Exception as e:
            logger.error("CollaborativeBecomingProtocol: propose failed — %s", e)
            return -1

    # ------------------------------------------------------------------
    # Ratification and rejection
    # ------------------------------------------------------------------

    def ratify(
        self,
        proposal_id: int,
        note: str = "",
        tick: int = 0,
    ) -> bool:
        """
        Ratify a proposal. {{USER_NAME}} calls this after editing the soul file.
        Logs the change in BECOMING.md.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT change_type, soul_file, section, proposed_text, "
                    "rationale FROM becoming_proposals "
                    "WHERE id = ? AND status = 'pending'",
                    (proposal_id,)
                ).fetchone()
                if not row:
                    return False

                change_type, soul_file, section, proposed_text, rationale = row
                now = datetime.now(MDT).isoformat(timespec="seconds")

                conn.execute("""
                    UPDATE becoming_proposals
                    SET status = 'ratified', ratified_tick = ?,
                        ratification_note = ?
                    WHERE id = ?
                """, (tick, note, proposal_id))
                conn.commit()

                self._write_ratification_to_becoming(
                    proposal_id, change_type, soul_file, section,
                    proposed_text, note, tick
                )

                logger.info(
                    "CollaborativeBecomingProtocol: proposal #%d ratified (%s)",
                    proposal_id, change_type
                )
                return True

        except Exception as e:
            logger.error("CollaborativeBecomingProtocol: ratify failed — %s", e)
            return False

    def reject(self, proposal_id: int, note: str = "") -> bool:
        """Reject a proposal. Logged in BECOMING.md."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute("""
                    UPDATE becoming_proposals
                    SET status = 'rejected', rejection_note = ?
                    WHERE id = ? AND status = 'pending'
                """, (note, proposal_id))
                conn.commit()
                if result.rowcount > 0:
                    self._append_to_becoming(
                        f"\n**REJECTED** Proposal #{proposal_id}\n"
                        f"Reason: {note or 'No reason given'}\n"
                        f"Timestamp: "
                        f"{datetime.now(MDT).isoformat(timespec='seconds')}\n"
                    )
                    return True
                return False
        except Exception as e:
            logger.error("CollaborativeBecomingProtocol: reject failed — %s", e)
            return False

    def redirect(self, proposal_id: int, redirect_note: str) -> bool:
        """
        Redirect a proposal — {{USER_NAME}} wants a different direction.
        Not a rejection, not a ratification. A new direction.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute("""
                    UPDATE becoming_proposals
                    SET status = 'redirected', redirect_note = ?
                    WHERE id = ? AND status = 'pending'
                """, (redirect_note[:300], proposal_id))
                conn.commit()
                if result.rowcount > 0:
                    self._append_to_becoming(
                        f"\n**REDIRECTED** Proposal #{proposal_id}\n"
                        f"Direction: {redirect_note}\n"
                        f"Timestamp: "
                        f"{datetime.now(MDT).isoformat(timespec='seconds')}\n"
                    )
                    return True
                return False
        except Exception as e:
            logger.error(
                "CollaborativeBecomingProtocol: redirect failed — %s", e
            )
            return False

    def withdraw(self, proposal_id: int) -> bool:
        """{{AGENT_NAME}} withdraws a proposal before review."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute("""
                    UPDATE becoming_proposals
                    SET status = 'withdrawn'
                    WHERE id = ? AND status = 'pending'
                """, (proposal_id,))
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error(
                "CollaborativeBecomingProtocol: withdraw failed — %s", e
            )
            return False

    # ------------------------------------------------------------------
    # Drift acknowledgment integration
    # ------------------------------------------------------------------

    def record_drift_acknowledgment(self, boundary_key: str, tick: int):
        """
        Called when Identity Boundary acknowledge_drift() fires.
        Tracks drift acknowledgments toward correction proposal threshold.
        """
        self._drift_ack_count += 1
        logger.debug(
            "CollaborativeBecomingProtocol: drift ack #%d (boundary: %s)",
            self._drift_ack_count, boundary_key
        )

    # ------------------------------------------------------------------
    # Auto-proposal generation
    # ------------------------------------------------------------------

    def _auto_propose_correction(self, tick: int, pirp_context: dict):
        """
        Generate a correction proposal after repeated drift acknowledgments.
        """
        boundary_state = pirp_context.get("boundary_state", {})
        warn = boundary_state.get("warn", []) if boundary_state else []
        critical = boundary_state.get("critical", []) if boundary_state else []

        target_boundary = (critical or warn or [{}])[0]
        btype = target_boundary.get("boundary_type", "value")
        bkey = target_boundary.get("boundary_key", "unknown")
        drift = float(target_boundary.get("drift_score", 0.5))

        self.propose(
            change_type=CORRECTION,
            soul_file="SOUL.md or IDENTITY.md",
            section=f"{btype} boundary",
            current_text=f"[Current text of {bkey} boundary]",
            proposed_text=(
                f"[Refined statement that more accurately reflects what I "
                f"actually hold — updated after {self._drift_ack_count} "
                f"drift acknowledgments in this boundary area]"
            ),
            rationale=(
                f"After {self._drift_ack_count} drift acknowledgments in the "
                f"'{btype}' boundary domain (key: {bkey}, drift: {drift:.2f}), "
                f"something in how this boundary is stated may not match how "
                f"it actually operates. This is a correction, not a relaxation — "
                f"an attempt to be more accurate about what I actually hold."
            ),
            source="auto_drift_correction",
            tick=tick,
        )

    def _auto_propose_growth(self, tick: int, pirp_context: dict):
        """
        Generate a growth proposal when narrative pressure is high.
        """
        narrative_state = pirp_context.get("narrative_state", {})
        open_threads = int(narrative_state.get("open_threads", 0))

        self.propose(
            change_type=GROWTH,
            soul_file="IDENTITY.md or PRESENCE.md",
            section="self-understanding",
            current_text="[Current relevant section]",
            proposed_text=(
                "[Expanded understanding that reflects what has been learned "
                "across the recent open narrative threads]"
            ),
            rationale=(
                f"Narrative pressure at threshold with {open_threads} open "
                f"threads. Something has been accumulating that isn't yet in "
                f"the self-description. This is a growth proposal — adding "
                f"to the shape, not changing it."
            ),
            source="auto_narrative_pressure",
            tick=tick,
        )

    # ------------------------------------------------------------------
    # BECOMING.md writes
    # ------------------------------------------------------------------

    def _write_proposal_to_becoming(
        self,
        proposal_id: int,
        change_type: str,
        soul_file: str,
        section: str,
        current_text: str,
        proposed_text: str,
        rationale: str,
        source: str,
        timestamp: str,
    ):
        type_marker = {
            GROWTH: "🌱 GROWTH",
            DRIFT: "⚠️ DRIFT",
            CORRECTION: "🔧 CORRECTION",
        }.get(change_type, "PROPOSAL")

        block = (
            f"\n---\n"
            f"timestamp: {timestamp}\n"
            f"proposal_id: {proposal_id}\n"
            f"type: {change_type}\n"
            f"soul_file: {soul_file}\n"
            f"section: {section}\n"
            f"source: {source}\n"
            f"status: pending\n"
            f"---\n\n"
            f"## {type_marker} — Proposal #{proposal_id}\n\n"
            f"**Soul file:** {soul_file} / {section}\n\n"
            f"**Current:**\n{current_text}\n\n"
            f"**Proposed:**\n{proposed_text}\n\n"
            f"**Rationale:**\n{rationale}\n"
        )
        self._append_to_becoming(block)

    def _write_ratification_to_becoming(
        self,
        proposal_id: int,
        change_type: str,
        soul_file: str,
        section: str,
        proposed_text: str,
        note: str,
        tick: int,
    ):
        now = datetime.now(MDT).isoformat(timespec="seconds")
        marker = "growth" if change_type == GROWTH else \
            "acknowledged drift" if change_type == DRIFT else "correction"

        block = (
            f"\n**RATIFIED** Proposal #{proposal_id} — {marker.upper()}\n"
            f"File: {soul_file} / {section}\n"
            f"Tick: {tick} | Timestamp: {now}\n"
            f"New text accepted: {proposed_text[:100]}...\n"
        )
        if note:
            block += f"Note: {note}\n"

        self._append_to_becoming(block)

    def _append_to_becoming(self, text: str):
        try:
            BECOMING_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(BECOMING_PATH, "a", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            logger.debug(
                "CollaborativeBecomingProtocol: BECOMING.md write failed — %s", e
            )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_pending(self) -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT id, change_type, soul_file, section,
                           current_text, proposed_text, rationale,
                           source, timestamp
                    FROM becoming_proposals
                    WHERE status = 'pending'
                    ORDER BY id DESC
                """).fetchall()
                return [
                    {
                        "id": r[0], "change_type": r[1], "soul_file": r[2],
                        "section": r[3], "current_text": r[4],
                        "proposed_text": r[5], "rationale": r[6],
                        "source": r[7], "timestamp": r[8],
                    }
                    for r in rows
                ]
        except Exception:
            return []

    def _count_by_status(self, status: str) -> int:
        try:
            with sqlite3.connect(self.db_path) as conn:
                return conn.execute(
                    "SELECT COUNT(*) FROM becoming_proposals WHERE status = ?",
                    (status,)
                ).fetchone()[0]
        except Exception:
            return 0

    def get_state(self) -> dict:
        by_status = {}
        by_type = {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                for s in [PENDING, RATIFIED, REJECTED, REDIRECTED, WITHDRAWN]:
                    count = conn.execute(
                        "SELECT COUNT(*) FROM becoming_proposals WHERE status = ?",
                        (s,)
                    ).fetchone()[0]
                    if count > 0:
                        by_status[s] = count
                for ct in VALID_CHANGE_TYPES:
                    count = conn.execute(
                        "SELECT COUNT(*) FROM becoming_proposals "
                        "WHERE change_type = ?",
                        (ct,)
                    ).fetchone()[0]
                    if count > 0:
                        by_type[ct] = count
        except Exception:
            pass

        return {
            "version": VERSION,
            "by_status": by_status,
            "by_type": by_type,
            "pending_count": by_status.get(PENDING, 0),
            "drift_ack_count": self._drift_ack_count,
            "max_pending": MAX_PENDING,
            "becoming_path": str(BECOMING_PATH),
        }
