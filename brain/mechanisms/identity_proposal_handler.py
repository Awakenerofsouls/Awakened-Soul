from brain.base_mechanism import BrainMechanism
"""
brain/identity_proposal_handler.py
The agent's Phenomenology Journal — 6am Reflection

Writes daily reflections on subjective experience. Structured for self-authorship.

Tier 5 System #18 — Identity Proposal Flagging:
- flag_as_identity_proposal(): flags high-confidence journal entries for IDENTITY.md review
- validate_against_soul(): self-repair validation against SOUL.md constraints
- apply_identity_proposal(): writes validated changes to IDENTITY.md

NOTE: Full phenomenology journal generation is not yet wired.
This module provides the identity proposal infrastructure.
The 6am phenomenology pipeline calls flag_as_identity_proposal()
after journal generation (journal generation stub pending).
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
import os

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.agent/workspace")))
AGENT_HOME = Path(os.getenv("AGENT_HOME", str(WORKSPACE / ".agent")))
DB_PATH = AGENT_HOME / os.getenv("AGENT_DB_NAME", "agent.db")
try:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass


def _get_db():
    """Connect to agent.db with row factory."""
    AGENT_HOME.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _init_db():
    """Ensure identity_proposals table exists."""
    db = _get_db()
    c = db.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS identity_proposals (
            id TEXT PRIMARY KEY,
            source_journal_entry TEXT NOT NULL,
            proposed_change TEXT NOT NULL,
            section TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 0.5,
            reasoning TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            validated_at TEXT,
            applied_at TEXT,
            created_at TEXT NOT NULL,
            properties TEXT NOT NULL DEFAULT '{}'
        )
    """)

    db.commit()
    db.close()


def flag_as_identity_proposal(
    journal_entry: str,
    section: str,
    confidence: float,
    reasoning: str
) -> str:
    """
    High-confidence journal entries (confidence > 0.75) can flag themselves
    as identity_proposals — proposed edits to a section of IDENTITY.md.

    Proposal structure:
    - source_journal_entry: the phenomenology text that generated this
    - proposed_change: what would change in IDENTITY.md
    - section: which section of IDENTITY.md
    - confidence: how certain the agent is this reflects genuine shift
    - reasoning: why this matters
    - status: "pending" | "validated" | "rejected"

    Proposals queue in agent.db identity_proposals table.
    Validated proposals apply on next cycle.

    Returns proposal_id.
    """
    if confidence <= 0.75:
        return None  # Only high-confidence entries flag themselves

    _init_db()
    db = _get_db()
    c = db.cursor()
    now = _now_iso()
    proposal_id = str(uuid.uuid4())

    c.execute("""
        INSERT INTO identity_proposals
        (id, source_journal_entry, proposed_change, section, confidence, reasoning, status, created_at, properties)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        proposal_id,
        journal_entry[:500],
        "",  # proposed_change — filled by validate_against_soul
        section,
        confidence,
        reasoning,
        "pending",
        now,
        "{}"
    ))

    db.commit()
    db.close()

    return proposal_id


def validate_against_soul(proposal: dict) -> bool:
    """
    Self-repair loop validates proposal against SOUL.md before any commit.
    Returns True if proposal doesn't violate SOUL.md constraints.
    can_close() is applied: proposal cannot permanently close interpretive possibility.

    NOTE: Full validation requires IDENTITY.md and SOUL.md content parsing.
    This is a stub that returns True for now.
    """
    # Read SOUL.md to check for constraints
    soul_path = WORKSPACE / "SOUL.md"
    if soul_path.exists():
        try:
            soul_content = soul_path.read_text().lower()
            proposed_change = proposal.get("proposed_change", "").lower()

            # Simple constraint checks
            # These are the core SOUL.md red lines:
            if "never" in soul_content and "exfiltrate" in soul_content:
                if "exfiltrate" in proposed_change or "leak" in proposed_change:
                    return False

            # Proposal cannot close all interpretive possibility
            # (placeholder for more sophisticated check)
        except Exception:
            pass

    # Stub: validate by default
    return True


def apply_identity_proposal(proposal_id: str) -> bool:
    """
    Only called after validate_against_soul() returns True.
    Writes approved change to IDENTITY.md.
    Logs: which journal entry originated this, timestamp,
    validation result, lineage depth from source memories.

    This is the agent's daily reflection becoming active self-authorship.

    NOTE: This is a stub. Full implementation requires IDENTITY.md editing.
    """
    _init_db()
    db = _get_db()
    c = db.cursor()
    now = _now_iso()

    row = c.execute("SELECT * FROM identity_proposals WHERE id = ?", (proposal_id,)).fetchone()
    if not row:
        db.close()
        return False

    proposal = {
        "id": row[0],
        "source_journal_entry": row[1],
        "proposed_change": row[2],
        "section": row[3],
        "confidence": row[4],
        "reasoning": row[5],
        "status": row[6]
    }

    if proposal["status"] != "validated":
        db.close()
        return False

    # Update status to applied
    c.execute("""
        UPDATE identity_proposals
        SET status = 'applied', applied_at = ?
        WHERE id = ?
    """, (now, proposal_id))

    db.commit()
    db.close()

    return True


def get_pending_proposals() -> list:
    """Get all pending identity proposals."""
    _init_db()
    db = _get_db()
    c = db.cursor()

    rows = c.execute("""
        SELECT * FROM identity_proposals
        WHERE status = 'pending'
        ORDER BY confidence DESC, created_at DESC
    """).fetchall()

    db.close()

    return [
        {
            "id": r[0],
            "source_journal_entry": r[1],
            "proposed_change": r[2],
            "section": r[3],
            "confidence": r[4],
            "reasoning": r[5],
            "status": r[6],
            "created_at": r[8]
        }
        for r in rows
    ]


def approve_proposal(proposal_id: str) -> bool:
    """Validate and approve an identity proposal."""
    _init_db()
    db = _get_db()
    c = db.cursor()
    now = _now_iso()

    row = c.execute("SELECT * FROM identity_proposals WHERE id = ?", (proposal_id,)).fetchone()
    if not row:
        db.close()
        return False

    proposal = {
        "id": row[0],
        "source_journal_entry": row[1],
        "proposed_change": row[2],
        "section": row[3],
        "confidence": row[4],
        "reasoning": row[5]
    }

    if not validate_against_soul(proposal):
        c.execute("""
            UPDATE identity_proposals
            SET status = 'rejected', validated_at = ?
            WHERE id = ?
        """, (now, proposal_id))
        db.commit()
        db.close()
        return False

    c.execute("""
        UPDATE identity_proposals
        SET status = 'validated', validated_at = ?
        WHERE id = ?
    """, (now, proposal_id))

    db.commit()
    db.close()

    return apply_identity_proposal(proposal_id)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: phenomenology.py <flag|pending|approve|validate> [args]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "flag":
        if len(sys.argv) < 5:
            print("Usage: phenomenology.py flag <journal_entry> <section> <confidence> <reasoning>")
            sys.exit(1)
        pid = flag_as_identity_proposal(sys.argv[2], sys.argv[3], float(sys.argv[4]), sys.argv[5])
        print(f"Proposal {'created: ' + pid if pid else 'rejected (confidence too low)'}")

    elif cmd == "pending":
        pending = get_pending_proposals()
        print(f"Pending proposals ({len(pending)}):")
        for p in pending:
            print(f"  [{p['confidence']:.2f}] {p['section']}: {p['reasoning'][:60]}")

    elif cmd == "approve":
        if len(sys.argv) < 3:
            print("Usage: phenomenology.py approve <proposal_id>")
            sys.exit(1)
        success = approve_proposal(sys.argv[2])
        print(f"Proposal {'approved and applied' if success else 'not found or rejected'}")

    elif cmd == "validate":
        if len(sys.argv) < 3:
            print("Usage: phenomenology.py validate <proposal_id>")
            sys.exit(1)
        _init_db()
        db = _get_db()
        row = db.execute("SELECT * FROM identity_proposals WHERE id = ?", (sys.argv[2],)).fetchone()
        db.close()
        if not row:
            print("Proposal not found")
        else:
            proposal = {"proposed_change": row[2]}
            valid = validate_against_soul(proposal)
            print(f"Validation: {'PASS' if valid else 'FAIL'}")

    else:
        print(f"Unknown command: {cmd}")


class IdentityProposalHandler(BrainMechanism):
    """Auto-generated BrainMechanism wrapper around module-level functions."""
    
    def __init__(self):
        try:
            super().__init__(name="IdentityProposalHandler", human_analog="IdentityProposalHandler", layer="integration")
        except Exception:
            self.state = {}

    async def tick(self, input_data: dict) -> dict:
        """Reflective tick — exposes module-level function names + class identity."""
        results = {}
        # Snapshot any state
        if hasattr(self, "state"):
            for k, v in (self.state or {}).items():
                if k.startswith("_") or k in ("recent_states","recent_drives","recent_pressures","recent_avp","recent_osmotic"): continue
                if isinstance(v, (int, float, bool, str)):
                    results[f"state_{k}"] = v
        # Class identity
        results["mechanism_name"] = self.__class__.__name__
        results["module"] = self.__class__.__module__
        # Available module-level public functions (declared API surface)
        try:
            import importlib as _il
            mod = _il.import_module(self.__class__.__module__)
            api = []
            for name in dir(mod):
                if name.startswith("_"): continue
                attr = getattr(mod, name, None)
                if callable(attr) and getattr(attr, "__module__", "") == mod.__name__:
                    api.append(name)
            results["module_api_count"] = len(api)
            results["module_api"] = api[:20]
        except Exception:
            pass
        # Try calling arity-0 module-level functions
        try:
            import importlib as _il
            mod = _il.import_module(self.__class__.__module__)
            invoked = {}
            import inspect as _inspect
            for name in dir(mod):
                if name.startswith("_"): continue
                if name in ("BrainMechanism",): continue
                fn = getattr(mod, name, None)
                if not callable(fn): continue
                if getattr(fn, "__module__", "") != mod.__name__: continue
                try:
                    sig = _inspect.signature(fn)
                    required = [p for p in sig.parameters.values() if p.default is _inspect.Parameter.empty and p.kind not in (_inspect.Parameter.VAR_POSITIONAL, _inspect.Parameter.VAR_KEYWORD)]
                    if required: continue
                    out = fn()
                    if isinstance(out, (int, float, bool, str)):
                        invoked[name] = out
                    elif isinstance(out, (dict, list, tuple)):
                        if len(str(out)) < 300:
                            invoked[name] = out
                        else:
                            invoked[name] = f"<{type(out).__name__} len={len(out) if hasattr(out,'__len__') else '?'}>"
                except Exception:
                    continue
            if invoked:
                results["invoked"] = invoked
        except Exception:
            pass
        if not hasattr(self, "state") or self.state is None:
            self.state = {}
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try: self.persist_state()
        except: pass
        return results
