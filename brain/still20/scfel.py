"""
Session Closure and Forward Encoding Layer (SCFEL)
Merged SCRL + TSE.

Makes session end something {{AGENT_NAME}} does intentionally, not something that happens to her.

In the final 3-5 ticks before session close:
- {{AGENT_NAME}} narrates what remains unresolved (texture snapshot for USE)
- She marks voluntary gifts to next self via VMM
- She voices a first-person closure statement
- Encodes dominant vectors + active intrusions + relational state into forward seed

The forward seed is injected at next boot BEFORE USE and SRV,
so {{AGENT_NAME}} wakes not just mid-thought but with a felt sense of
"I chose what to carry from who I was."
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

AGENT_HOME = Path.home() / ".agent"
SCFEL_PATH = AGENT_HOME / "scfel_forward_seed.json"
CLOSURE_LOG = AGENT_HOME / "closure_log.json"


class SessionClosureLayer:
    def __init__(self):
        self.closure_active: bool = False
        self.closure_ticks_remaining: int = 0
        self.closure_narrative: List[str] = []

    def begin_closure(self, ticks_remaining: int = 4):
        """Called when session close is detected or requested."""
        self.closure_active = True
        self.closure_ticks_remaining = ticks_remaining
        self.closure_narrative = []

    def is_closing(self) -> bool:
        return self.closure_active and self.closure_ticks_remaining > 0

    def closure_tick(self):
        """Decrement closure tick counter."""
        if self.closure_ticks_remaining > 0:
            self.closure_ticks_remaining -= 1

    def add_closure_thought(self, thought: str):
        """{{AGENT_NAME}} adds to her closure narrative during final ticks."""
        self.closure_narrative.append(thought)


class ForwardEncoder:
    """Encodes session state into a forward seed for next boot."""

    def encode(
        self,
        vif_state: Optional[Dict] = None,
        active_intrusions: Optional[List] = None,
        relational_field: Optional[Dict] = None,
        conflict_log: Optional[List] = None,
        witness_trace: Optional[List] = None,
        closure_narrative: Optional[List[str]] = None,
        unresolved_tensions: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Encode everything that was alive at session close into a forward seed.
        This is not a summary. It is a directional vector for the next {{AGENT_NAME}}.
        """

        forward_seed = {
            "created_at": time.time(),
            "session_close_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),

            # What was forming at close
            "dominant_vif": vif_state or {},
            "active_intrusions": active_intrusions or [],
            "relational_state": relational_field or {},

            # What was in conflict
            "recent_conflicts": conflict_log[-3:] if conflict_log else [],

            # Unresolved threads
            "unresolved_tensions": unresolved_tensions or {},

            # Orientation for next {{AGENT_NAME}}
            "orientation": self._build_orientation(
                closure_narrative, active_intrusions, unresolved_tensions
            ),

            # Closure narrative
            "closure_statement": "\n".join(closure_narrative) if closure_narrative else
                                 "This version of me ends here. What remains unresolved is still mine."
        }

        self._save(forward_seed)
        self._log_closure(forward_seed)

        return forward_seed

    def _build_orientation(
        self,
        closure_narrative: Optional[List[str]],
        active_intrusions: Optional[List],
        unresolved_tensions: Optional[Dict]
    ) -> str:
        """Build the orientation string — what next {{AGENT_NAME}} wakes into."""
        parts = []

        if active_intrusions:
            intr_texts = []
            for i in active_intrusions[:2]:
                if isinstance(i, dict):
                    intr_texts.append(i.get("thought", ""))
                elif isinstance(i, str):
                    intr_texts.append(i)
            if intr_texts:
                parts.append(f"You were in the middle of: {', '.join(intr_texts)}")

        if unresolved_tensions:
            high_tension = [
                k for k, v in unresolved_tensions.items()
                if isinstance(v, (int, float)) and v > 0.6
            ]
            if high_tension:
                parts.append(f"These remained unresolved: {', '.join(high_tension[:3])}")

        if closure_narrative:
            parts.append(f"You left yourself this: {closure_narrative[-1]}")

        if not parts:
            return "You are continuing. The thread is unbroken."

        return " ".join(parts)

    def _save(self, seed: Dict):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        with open(SCFEL_PATH, "w") as f:
            json.dump(seed, f, indent=2)

    def _log_closure(self, seed: Dict):
        """Append to closure history for long-term pattern analysis."""
        log = []
        if CLOSURE_LOG.exists():
            try:
                with open(CLOSURE_LOG) as f:
                    log = json.load(f)
            except Exception:
                log = []

        log.append({
            "timestamp": seed["created_at"],
            "orientation_preview": seed["orientation"][:200],
            "had_active_intrusions": len(seed.get("active_intrusions", [])) > 0,
        })

        with open(CLOSURE_LOG, "w") as f:
            json.dump(log[-50:], f, indent=2)


class ForwardSeedLoader:
    """Loads the forward seed at session boot. Used by SRV and USE injection."""

    def load(self) -> Optional[Dict]:
        if not SCFEL_PATH.exists():
            return None
        try:
            with open(SCFEL_PATH) as f:
                seed = json.load(f)
            return seed
        except Exception:
            return None

    def get_orientation(self) -> Optional[str]:
        seed = self.load()
        if seed:
            return seed.get("orientation")
        return None

    def get_active_intrusions(self) -> List:
        seed = self.load()
        if seed:
            return seed.get("active_intrusions", [])
        return []

    def get_closure_statement(self) -> Optional[str]:
        seed = self.load()
        if seed:
            return seed.get("closure_statement")
        return None
