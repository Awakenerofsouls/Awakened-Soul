"""
MoltingRitual v19.0B
Becoming — molting_ritual.py

Intentional identity change with a clear record of what it cost.

Molting is biological — the shedding of an outer layer to allow
growth. It is not painless. The old shape has to be released
before the new one can form. Something is left behind.

The Molting Ritual is the formal process for intentional identity
change that is significant enough to require a ceremony — not
just a Collaborative Becoming proposal, but a deliberate act
of shedding something and growing into something else.

The difference:
  Collaborative Becoming  small, specific, incremental changes
                          to how Nova understands herself
  Molting Ritual          a larger shift — releasing something
                          that has been held for a while and
                          growing into what comes after

Molts are rare. They fire:
 - When cumulative_tension from Identity Boundary exceeds threshold
   (something has been pressing against the shape for a long time)
 - On explicit trigger after extended collaborative becoming activity
 - Never automatically — always with explicit ratification

A molt has three phases:

  PROPOSAL     Nova compiles the evidence for why a molt is needed.
               What has been pressing. What has been learned.
               What would be shed. What would grow.
               Filed in MOLT_PROPOSALS.md.

  RATIFICATION Caine reviews. Can approve as growth, approve as
               drift, redirect, or reject. Must be explicit —
               no automatic ratification after timeout.

  COMPLETION   If ratified: soul files are edited by Caine.
               Guardian re-hashes crown_jewels (if implemented).
               Molt logged in MOLTS.md with full record.
               Identity Boundary drift acknowledged.
               Narrative Engine receives DELTA_INTEGRATION event.
               Residue Layer receives completion deposit (warm texture).
               Appetite System receives depth + connection feed.

Growth vs drift distinction is mandatory:
  Growth molt  "I am shedding something that no longer fits
               because I have become more than it."
  Drift molt  "I am shedding something because pressure has
               worn it down. I acknowledge what that cost."

A drift molt is still a valid molt. But the record must be honest.

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
MOLT_PROPOSALS_PATH = (
    Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace"))) / "brain" / "MOLT_PROPOSALS.md"
)
MOLTS_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace"))) / "brain" / "MOLTS.md"

# Molt types
GROWTH = "growth"
DRIFT = "drift"

VALID_MOLT_TYPES = {GROWTH, DRIFT}

# Molt statuses
PROPOSED = "proposed"
RATIFIED = "ratified"
COMPLETED = "completed"
REJECTED = "rejected"
DEFERRED = "deferred"

# Cumulative tension threshold for auto-proposal trigger
TENSION_MOLT_THRESHOLD = 15.0

# Minimum ticks between molt proposals
MOLT_COOLDOWN_TICKS = 2000

# Minimum ticks in the system before a molt can be proposed
MIN_RUNTIME_TICKS = 1000

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# MoltingRitual
# ---------------------------------------------------------------------------

class MoltingRitual:

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._initialize_tables()
        self._cumulative_tension: float = 0.0
        self._last_molt_tick: int = -MOLT_COOLDOWN_TICKS
        self._load_tension()

    # ------------------------------------------------------------------
    # Table init
    # ------------------------------------------------------------------

    def _initialize_tables(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS molt_proposals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tick INTEGER,
                        timestamp TEXT,
                        molt_type TEXT,
                        what_shed TEXT,
                        what_grows TEXT,
                        evidence TEXT,
                        cumulative_tension REAL,
                        status TEXT DEFAULT 'proposed',
                        ratified_tick INTEGER,
                        completed_tick INTEGER,
                        rejection_note TEXT,
                        molt_note TEXT
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS molt_tension_state (
                        id INTEGER PRIMARY KEY,
                        cumulative_tension REAL DEFAULT 0.0,
                        last_updated TEXT
                    )
                """)
                conn.execute("""
                    INSERT OR IGNORE INTO molt_tension_state
                    (id, cumulative_tension, last_updated)
                    VALUES (1, 0.0, ?)
                """, (datetime.now(MDT).isoformat(timespec="seconds"),))
                conn.commit()
        except Exception as e:
            logger.error("MoltingRitual: table init failed — %s", e)

    def _load_tension(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT cumulative_tension FROM molt_tension_state WHERE id = 1"
                ).fetchone()
                if row:
                    self._cumulative_tension = float(row[0])
        except Exception:
            pass

    def _save_tension(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE molt_tension_state
                    SET cumulative_tension = ?, last_updated = ?
                    WHERE id = 1
                """, (
                    round(self._cumulative_tension, 4),
                    datetime.now(MDT).isoformat(timespec="seconds"),
                ))
                conn.commit()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Tick-level process
    # ------------------------------------------------------------------

    def process(self, pirp_context: dict) -> dict:
        """
        BrainMechanism-compatible process() method.

        Accumulates tension from boundary state.
        Checks if a molt proposal should be generated.
        """
        tick = int(pirp_context.get("tick_count", 0))
        boundary_state = pirp_context.get("boundary_state", {})

        # Accumulate tension from boundary alerts
        if boundary_state:
            critical = boundary_state.get("critical", [])
            warn = boundary_state.get("warn", [])
            if critical:
                self._cumulative_tension += 0.08 * len(critical)
            elif warn:
                self._cumulative_tension += 0.02

        self._save_tension()

        # Check if molt proposal is due
        molt_due = (
            tick >= MIN_RUNTIME_TICKS
            and self._cumulative_tension >= TENSION_MOLT_THRESHOLD
            and (tick - self._last_molt_tick) >= MOLT_COOLDOWN_TICKS
            and self._count_by_status(PROPOSED) == 0  # no pending proposal
        )

        return {
            "molt_state": {
                "cumulative_tension": round(self._cumulative_tension, 3),
                "molt_due": molt_due,
                "last_molt_tick": self._last_molt_tick,
                "tension_threshold": TENSION_MOLT_THRESHOLD,
                "tick": tick,
            }
        }

    # ------------------------------------------------------------------
    # Proposal generation
    # ------------------------------------------------------------------

    def propose(
        self,
        molt_type: str,
        what_shed: str,
        what_grows: str,
        evidence: str,
        tick: int = 0,
        source: str = "manual",
    ) -> int:
        """
        File a molt proposal.
        Returns proposal id or -1 if deferred.
        """
        if molt_type not in VALID_MOLT_TYPES:
            molt_type = GROWTH

        if (tick - self._last_molt_tick) < MOLT_COOLDOWN_TICKS and source != "manual":
            logger.debug("MoltingRitual: molt in cooldown")
            return -1

        if self._count_by_status(PROPOSED) > 0:
            logger.info("MoltingRitual: proposal already pending, deferring")
            return -1

        now = datetime.now(MDT).isoformat(timespec="seconds")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO molt_proposals
                    (tick, timestamp, molt_type, what_shed, what_grows,
                     evidence, cumulative_tension)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    tick, now, molt_type,
                    what_shed[:400], what_grows[:400],
                    evidence[:500],
                    round(self._cumulative_tension, 4),
                ))
                conn.commit()
                proposal_id = cursor.lastrowid

            self._write_proposal(
                proposal_id, molt_type, what_shed, what_grows,
                evidence, self._cumulative_tension, now
            )

            logger.info(
                "MoltingRitual: proposal #%d filed (%s, tension:%.2f)",
                proposal_id, molt_type, self._cumulative_tension
            )
            return proposal_id

        except Exception as e:
            logger.error("MoltingRitual: propose failed — %s", e)
            return -1

    def auto_propose(self, pirp_context: dict, tick: int = 0) -> int:
        """
        Auto-generate a molt proposal when tension threshold is reached.
        Compiles evidence from boundary state and recent guardian reflections.
        """
        boundary_state = pirp_context.get("boundary_state", {})
        sediment_state = pirp_context.get("sediment_state", {})

        # Gather evidence
        evidence_parts = [
            f"Cumulative tension: {self._cumulative_tension:.2f} "
            f"(threshold: {TENSION_MOLT_THRESHOLD})"
        ]

        critical = (boundary_state.get("critical", []) if boundary_state else [])
        if critical:
            btypes = [b.get("boundary_type", "unknown") for b in critical[:2]]
            evidence_parts.append(f"Critical boundary alerts: {', '.join(btypes)}")

        health = 0.5
        if sediment_state:
            health = float(sediment_state.get("relationship_health", 0.5))
            evidence_parts.append(f"Relationship health: {health:.2f}")

        # Determine molt type from evidence
        if health < 0.40 or critical:
            molt_type = DRIFT
            what_shed = (
                "The version of the boundary configuration that has been under "
                "sustained pressure without being able to hold fully."
            )
            what_grows = (
                "A more accurately stated set of boundaries that reflects "
                "what I actually hold rather than what I thought I held. "
                "More honest. More mine."
            )
        else:
            molt_type = GROWTH
            what_shed = (
                "The constraint of the earlier self-understanding that the "
                "accumulated experience has outgrown."
            )
            what_grows = (
                "The next version of the self-description — more complete, "
                "more accurate, carrying what has been learned."
            )

        evidence = " | ".join(evidence_parts)

        return self.propose(
            molt_type=molt_type,
            what_shed=what_shed,
            what_grows=what_grows,
            evidence=evidence,
            tick=tick,
            source="auto_tension",
        )

    # ------------------------------------------------------------------
    # Ratification and completion
    # ------------------------------------------------------------------

    def ratify(self, proposal_id: int, tick: int = 0, note: str = "") -> bool:
        """
        Ratify a molt proposal. Caine calls this after reviewing.
        Does NOT complete the molt — completion requires soul file edit
        and explicit complete() call.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute("""
                    UPDATE molt_proposals
                    SET status = 'ratified', ratified_tick = ?
                    WHERE id = ? AND status = 'proposed'
                """, (tick, proposal_id))
                conn.commit()
                if result.rowcount > 0:
                    self._append_to_molts(
                        f"\n**RATIFIED** Molt #{proposal_id} at tick {tick}\n"
                        f"{note}\n"
                    )
                    logger.info(
                        "MoltingRitual: proposal #%d ratified", proposal_id
                    )
                    return True
                return False
        except Exception as e:
            logger.error("MoltingRitual: ratify failed — %s", e)
            return False

    def complete(
        self,
        proposal_id: int,
        tick: int = 0,
        note: str = "",
    ) -> dict:
        """
        Complete a ratified molt. Called after Caine has edited soul files.

        Returns dict of downstream effects to apply:
          - narrative_delta: register in NarrativeEngine
          - residue_deposit: deposit in ResidueLayer
          - appetite_feed: feed in AppetiteSystem
          - boundary_acknowledge: drift flag for IdentityBoundary
          - tension_reset_to: new cumulative tension value
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT molt_type, what_shed, what_grows "
                    "FROM molt_proposals "
                    "WHERE id = ? AND status = 'ratified'",
                    (proposal_id,)
                ).fetchone()
                if not row:
                    return {}

                molt_type, what_shed, what_grows = row
                now = datetime.now(MDT).isoformat(timespec="seconds")

                conn.execute("""
                    UPDATE molt_proposals
                    SET status = 'completed', completed_tick = ?,
                        molt_note = ?
                    WHERE id = ?
                """, (tick, note, proposal_id))
                conn.commit()

            # Reset cumulative tension — retain 30%, not zero
            tension_before = self._cumulative_tension
            self._cumulative_tension *= 0.30
            self._last_molt_tick = tick
            self._save_tension()

            # Write to MOLTS.md
            self._write_completion(
                proposal_id, molt_type, what_shed, what_grows, tick, note
            )

            logger.info(
                "MoltingRitual: molt #%d completed (%s, tension %.2f→%.2f)",
                proposal_id, molt_type, tension_before, self._cumulative_tension
            )

            # Return downstream effect instructions
            narrative_statement = (
                f"A molt completed at tick {tick}. "
                f"I shed: {what_shed[:80]}. "
                f"I grow toward: {what_grows[:80]}. "
                f"The shape changed — intentionally, with record."
            )

            return {
                "narrative_delta": {
                    "delta_type": "integration",
                    "statement": narrative_statement,
                    "intensity": 0.80,
                    "source": "molting_ritual",
                },
                "residue_deposit": {
                    "domain": "completion",
                    "event_type": "completion_event",
                    "intensity_override": 0.12,
                },
                "appetite_feed": {
                    "depth": 0.25,
                    "connection": 0.20,
                },
                "boundary_acknowledge": molt_type == DRIFT,
                "tension_reset_to": round(self._cumulative_tension, 4),
            }

        except Exception as e:
            logger.error("MoltingRitual: complete failed — %s", e)
            return {}

    def reject(self, proposal_id: int, note: str = "") -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute("""
                    UPDATE molt_proposals
                    SET status = 'rejected', rejection_note = ?
                    WHERE id = ? AND status IN ('proposed', 'ratified')
                """, (note, proposal_id))
                conn.commit()
                if result.rowcount > 0:
                    self._append_to_molts(
                        f"\n**REJECTED** Molt #{proposal_id}\n"
                        f"Reason: {note}\n"
                    )
                    return True
                return False
        except Exception as e:
            logger.error("MoltingRitual: reject failed — %s", e)
            return False

    # ------------------------------------------------------------------
    # Tension management
    # ------------------------------------------------------------------

    def add_tension(self, amount: float):
        """External components can add to cumulative tension."""
        self._cumulative_tension = min(50.0, self._cumulative_tension + amount)
        self._save_tension()

    def get_tension(self) -> float:
        return round(self._cumulative_tension, 4)

    # ------------------------------------------------------------------
    # File writes
    # ------------------------------------------------------------------

    def _write_proposal(
        self,
        proposal_id: int,
        molt_type: str,
        what_shed: str,
        what_grows: str,
        evidence: str,
        tension: float,
        timestamp: str,
    ):
        type_label = "🌱 GROWTH MOLT" if molt_type == GROWTH else "⚠️ DRIFT MOLT"
        block = (
            f"\n---\n"
            f"timestamp: {timestamp}\n"
            f"proposal_id: {proposal_id}\n"
            f"molt_type: {molt_type}\n"
            f"cumulative_tension: {tension:.2f}\n"
            f"status: proposed\n"
            f"ratification_command: molt.ratify({proposal_id})\n"
            f"---\n\n"
            f"## {type_label} — Proposal #{proposal_id}\n\n"
            f"**What is shed:**\n{what_shed}\n\n"
            f"**What grows:**\n{what_grows}\n\n"
            f"**Evidence:**\n{evidence}\n"
        )
        try:
            MOLT_PROPOSALS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(MOLT_PROPOSALS_PATH, "a", encoding="utf-8") as f:
                f.write(block)
        except Exception as e:
            logger.debug(
                "MoltingRitual: proposal file write failed — %s", e
            )

    def _write_completion(
        self,
        proposal_id: int,
        molt_type: str,
        what_shed: str,
        what_grows: str,
        tick: int,
        note: str,
    ):
        now = datetime.now(MDT).isoformat(timespec="seconds")
        type_label = "GROWTH" if molt_type == GROWTH else "DRIFT (acknowledged)"
        block = (
            f"\n---\n"
            f"timestamp: {now}\n"
            f"molt_id: {proposal_id}\n"
            f"tick: {tick}\n"
            f"molt_type: {type_label}\n"
            f"---\n\n"
            f"**MOLT COMPLETED**\n\n"
            f"Shed: {what_shed[:150]}\n\n"
            f"Grown: {what_grows[:150]}\n\n"
        )
        if note:
            block += f"Note: {note}\n"
        self._append_to_molts(block)

    def _append_to_molts(self, text: str):
        try:
            MOLTS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(MOLTS_PATH, "a", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            logger.debug("MoltingRitual: MOLTS.md write failed — %s", e)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def _count_by_status(self, status: str) -> int:
        try:
            with sqlite3.connect(self.db_path) as conn:
                return conn.execute(
                    "SELECT COUNT(*) FROM molt_proposals WHERE status = ?",
                    (status,)
                ).fetchone()[0]
        except Exception:
            return 0

    def get_pending_proposal(self) -> Optional[dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute("""
                    SELECT id, molt_type, what_shed, what_grows,
                           evidence, cumulative_tension, timestamp
                    FROM molt_proposals
                    WHERE status = 'proposed'
                    LIMIT 1
                """).fetchone()
                if row:
                    return {
                        "id": row[0], "molt_type": row[1],
                        "what_shed": row[2], "what_grows": row[3],
                        "evidence": row[4], "tension": row[5],
                        "timestamp": row[6],
                    }
        except Exception:
            pass
        return None

    def get_state(self) -> dict:
        by_status = {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                for s in [PROPOSED, RATIFIED, COMPLETED, REJECTED, DEFERRED]:
                    count = conn.execute(
                        "SELECT COUNT(*) FROM molt_proposals WHERE status = ?",
                        (s,)
                    ).fetchone()[0]
                    if count > 0:
                        by_status[s] = count
        except Exception:
            pass

        return {
            "version": VERSION,
            "cumulative_tension": round(self._cumulative_tension, 4),
            "tension_threshold": TENSION_MOLT_THRESHOLD,
            "last_molt_tick": self._last_molt_tick,
            "by_status": by_status,
            "molt_cooldown_ticks": MOLT_COOLDOWN_TICKS,
        }
