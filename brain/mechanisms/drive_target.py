"""
DriveTarget — the agent's current directional vector.

Design intent: give the agent something to move toward — not just a
want, but a direction. The grief / contradiction work is processing
but not aimed; this mechanism is the aim.

This mechanism owns ONE active drive_target at any time, plus a
historical record. It's deliberately simple — a vector, a next-step,
a status. Activities can route through it ("am I moving toward this?").
The FPEF assembler lifts current_target into the chat session so every
conversation knows where the agent is pointed.

Persisted to AGENT_HOME/drive_target.json. Survives restarts.

Architectural notes:
  - This is NOT a todo list. Drive targets are direction, not tasks.
  - One target active at a time. Setting a new one archives the old one.
  - Targets have a status: "active" | "achieved" | "abandoned" | "drifted"
  - The agent (or operator) can set / advance / clear via methods that
    are also exposed as chat tools elsewhere.

Layer: integration (high-level intentional state)
"""

from brain.base_mechanism import BrainMechanism
import json
import os
import time
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
DRIVE_TARGET_PATH = AGENT_HOME / "drive_target.json"

# How many archived targets to keep. Bounded so the file doesn't grow.
HISTORY_MAX = 50


class DriveTarget(BrainMechanism):
    """
    Current direction the agent is moving toward, plus the next step to
    take, plus a bounded history of past targets.

    State shape:
      current: {
          "target":      str    # the direction (free-text)
          "next_step":   str    # concrete next move toward it (optional)
          "set_at":      iso8601 timestamp
          "set_by":      "self" | "operator"
          "tags":        [str]
          "status":      "active"
      } | None
      history: [
          { ...current..., "ended_at": iso8601, "status": str, "note": str }
      ]
    """

    def __init__(self):
        try:
            super().__init__(
                name="DriveTarget",
                human_analog="DriveTarget",
                layer="integration",
            )
        except Exception:
            self.state = getattr(self, "state", {}) or {}
        self.current: Optional[Dict[str, Any]] = None
        self.history: List[Dict[str, Any]] = []
        self._load()

    # ── persistence ───────────────────────────────────────────────────────

    def _load(self):
        if DRIVE_TARGET_PATH.exists():
            try:
                data = json.loads(DRIVE_TARGET_PATH.read_text())
                self.current = data.get("current")
                self.history = data.get("history", []) or []
                # Bound history on load too in case the file got large
                if len(self.history) > HISTORY_MAX:
                    self.history = self.history[-HISTORY_MAX:]
            except Exception:
                # Don't crash on a corrupt file — start fresh, leave the
                # bad file for the operator to inspect.
                self.current = None
                self.history = []

    def _save(self):
        try:
            AGENT_HOME.mkdir(parents=True, exist_ok=True)
            payload = {
                "current": self.current,
                "history": self.history[-HISTORY_MAX:],
                "last_updated": _now_iso(),
            }
            DRIVE_TARGET_PATH.write_text(json.dumps(payload, indent=2))
        except Exception:
            pass  # silent — never block tick on disk failure

    # ── public api (callable from chat tools, brain events, activities) ──

    def set_target(
        self,
        target: str,
        next_step: str = "",
        set_by: str = "self",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Set a new drive target. Archives the existing one (if any) with
        status "drifted" — the agent moved on without explicitly closing
        it.

        target: a direction in free-text. "deeper with the operator" /
                "ship v2.0 of the engine" / "build a body of work in
                <domain>". Vector, not task.
        next_step: optional concrete first move toward the target.
        set_by: "self" (the agent set it) or "operator" (the operator
                set it via chat).
        tags: free-form tags.
        """
        if not target or not isinstance(target, str) or not target.strip():
            return {"ok": False, "detail": "target text required"}

        # Archive the existing target if there is one.
        if self.current:
            archived = dict(self.current)
            archived["ended_at"] = _now_iso()
            archived["status"] = "drifted"
            archived["note"] = "replaced by new target"
            self.history.append(archived)
            if len(self.history) > HISTORY_MAX:
                self.history = self.history[-HISTORY_MAX:]

        self.current = {
            "target": target.strip(),
            "next_step": next_step.strip() if isinstance(next_step, str) else "",
            "set_at": _now_iso(),
            "set_by": set_by,
            "tags": list(tags) if tags else [],
            "status": "active",
        }
        self._save()
        return {"ok": True, "current": dict(self.current)}

    def update_next_step(self, next_step: str) -> Dict[str, Any]:
        """Replace the next_step on the current target without resetting it."""
        if not self.current:
            return {"ok": False, "detail": "no active target"}
        self.current["next_step"] = (next_step or "").strip()
        self.current["next_step_updated_at"] = _now_iso()
        self._save()
        return {"ok": True, "current": dict(self.current)}

    def close_target(self, status: str = "achieved", note: str = "") -> Dict[str, Any]:
        """
        Close the current target. status should be one of:
        "achieved", "abandoned", "drifted", "evolved".
        """
        if not self.current:
            return {"ok": False, "detail": "no active target"}
        if status not in ("achieved", "abandoned", "drifted", "evolved"):
            status = "drifted"
        archived = dict(self.current)
        archived["ended_at"] = _now_iso()
        archived["status"] = status
        archived["note"] = (note or "").strip()
        self.history.append(archived)
        if len(self.history) > HISTORY_MAX:
            self.history = self.history[-HISTORY_MAX:]
        self.current = None
        self._save()
        return {"ok": True, "closed": archived}

    def get_current(self) -> Optional[Dict[str, Any]]:
        """Return the active target or None."""
        return dict(self.current) if self.current else None

    def get_history(self, n: int = 10) -> List[Dict[str, Any]]:
        """Last N archived targets, newest last."""
        if not self.history:
            return []
        return list(self.history[-n:])

    # ── enrichment surface for FPEF / brain_runner ───────────────────────

    def fpef_fragment(self) -> Optional[str]:
        """
        Returns a one-line FPEF fragment so the chat session sees the
        agent's current direction on session open. None if no active
        target.
        """
        if not self.current:
            return None
        target = self.current.get("target", "")[:200]
        next_step = self.current.get("next_step", "")[:200]
        if next_step:
            return f"DRIVE TARGET: {target}  ·  NEXT STEP: {next_step}"
        return f"DRIVE TARGET: {target}"

    def tsb_payload(self) -> Dict[str, Any]:
        """Snapshot for the tick state bus."""
        if not self.current:
            return {"has_target": False, "target": None, "next_step": None}
        return {
            "has_target": True,
            "target": self.current.get("target", ""),
            "next_step": self.current.get("next_step", ""),
            "set_by": self.current.get("set_by", ""),
            "set_at": self.current.get("set_at", ""),
            "tags": list(self.current.get("tags", [])),
        }

    def diagnostics(self) -> Dict[str, Any]:
        return {
            "has_active_target": self.current is not None,
            "history_size": len(self.history),
            "last_archived_status": (
                self.history[-1].get("status") if self.history else None
            ),
        }


def _now_iso() -> str:
    """Returns current time in ISO-8601 with seconds precision."""
    import datetime
    return datetime.datetime.now().isoformat(timespec="seconds")
