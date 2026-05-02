"""
brain/processor.py — AgentProcessor

The thread-safe entry point that takes incoming messages, runs them through
the bootstrap brain, writes the active cognitive state to disk, and assembles
the prompt prefix the LLM call site reads.

Mechanism wiring is delegated to BrainRegistry — this module no longer
hardcodes a list of imports, so the processor doesn't decay as mechanisms
are added, renamed, or moved within brain/mechanisms/.
"""

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict

from core.context_survival import ContextSurvival

WORKSPACE = Path(
    os.environ.get("AGENT_WORKSPACE", os.path.expanduser("~/.agent/workspace"))
)
DB_PATH = WORKSPACE / os.getenv("AGENT_DB_NAME", "agent.db")

# Module-level singleton — used by build_prompt_prefix for context-window
# survival logic.
_ctx_survival = ContextSurvival()


class AgentProcessor:
    """
    Singleton per process. Holds:
      - the bootstrap brain (from brain.bootstrap.get_agent)
      - a discovered list of registered mechanisms (from BrainRegistry)
      - the continuous background runtime (from core.runtime.AgentRuntime)
      - the per-process ContextSurvival helper

    Use AgentProcessor.get() to fetch the singleton; use .process_message(...)
    to feed a user message through the pipeline.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self, db_path: str | None = None):
        from brain.bootstrap import get_agent
        from brain.registry import BrainRegistry
        from core.runtime import AgentRuntime as ContinuousRuntime

        self.db_path = db_path or str(DB_PATH)
        self.bootstrap = get_agent()
        self._process_lock = threading.Lock()

        # Mechanism discovery — replaces the historical hardcoded import lists.
        # BrainRegistry walks brain/mechanisms/ + brain/ and instantiates every
        # BrainMechanism subclass it finds. After consolidation into a single
        # brain/mechanisms/ folder, this is the single source of truth.
        try:
            BrainRegistry.load_all()
            mechanisms = BrainRegistry.all()
        except Exception as e:
            print(f"[AgentProcessor] BrainRegistry.load_all failed: {e}")
            mechanisms = []

        # Expose the discovered mechanisms on the bootstrap brain so older
        # callers can still iterate them.
        self.bootstrap.mechanisms = mechanisms
        self.bootstrap.mechanisms_by_name = {m.name: m for m in mechanisms if hasattr(m, "name")}

        # Per-process continuity helper. Same instance pattern as the
        # module-level _ctx_survival, exposed as an attribute for convenience.
        self.context_survival = _ctx_survival

        # Continuous runtime — non-blocking background thread. If the runtime
        # cannot start we keep going so message processing still works.
        try:
            self.runtime = ContinuousRuntime(self.bootstrap, dt=2.0)
            self.runtime.start()
        except Exception as e:
            print(f"[AgentProcessor] continuous runtime failed to start: {e}")
            self.runtime = None

    @classmethod
    def get(cls, db_path: str | None = None) -> "AgentProcessor":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_path)
        return cls._instance

    def process_message(self, message: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """
        Call this with every incoming message before LLM inference.
        Returns enriched cognitive state to inject into the prompt.
        """
        with self._process_lock:
            result = self.bootstrap.process(
                text=message,
                architect_present=True,
            )
            # Register operator presence on every incoming message
            relation = getattr(self.bootstrap, "relation", None)
            if relation is not None and hasattr(relation, "on_presence"):
                try:
                    relation.on_presence("user")
                except Exception:
                    pass
            self._write_active_state(result)
            return result

    def _write_active_state(self, state: Dict[str, Any]) -> None:
        """Write cognitive state to active_state.json for downstream readers."""
        try:
            state_dir = WORKSPACE / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            active_state_path = state_dir / "active_state.json"
            cognitive_state: Dict[str, Any] = {}
            for k, v in state.items():
                if isinstance(v, (int, float, str, bool)):
                    cognitive_state[k] = v
            with open(active_state_path, "w") as f:
                json.dump({
                    "last_processed": time.time(),
                    "cognitive_state": cognitive_state,
                    "db_path": self.db_path,
                }, f, indent=2)
        except Exception as e:
            print(f"[AgentProcessor] Failed to write active_state: {e}")

    def get_cognitive_state(self) -> Dict[str, Any]:
        """Return last processed brain state without running pipeline."""
        try:
            active_state_path = WORKSPACE / "state" / "active_state.json"
            if active_state_path.exists():
                with open(active_state_path) as f:
                    return json.load(f).get("cognitive_state", {})
        except Exception:
            pass
        return {}

    def build_prompt_prefix(self, state: Dict[str, Any], context_usage: float = 0.0) -> str:
        """
        Called when assembling the prompt. If context_usage >= the
        ContextSurvival threshold, compress recent_memory and inject an
        identity snapshot rather than raw history. This is the CTX
        continuity path that lets the agent survive compaction with
        continuity intact.
        """
        if _ctx_survival.should_compress(context_usage):
            state["recent_memory"] = _ctx_survival.compress_memory(state.get("recent_memory", []))
        snapshot = _ctx_survival.build(state)
        cognitive = self.format_for_prompt(state)
        parts = []
        if snapshot:
            parts.append(snapshot)
        if cognitive:
            parts.append(cognitive)
        return "\n\n".join(parts) if parts else ""

    def format_for_prompt(self, state: Dict[str, Any]) -> str:
        """Returns a compact cognitive state string to prepend to LLM prompt."""
        lines = []
        key_signals = [
            "drift_composite", "anti_coherence", "longing_weight",
            "absence_weight", "ambivalence", "incompleteness_score",
            "tension_gradient", "pirp_tension",
        ]
        for k in key_signals:
            if k in state:
                v = state[k]
                lines.append(f"{k}: {v:.3f}" if isinstance(v, float) else f"{k}: {v}")
        if not lines:
            return ""
        return "[COGNITIVE STATE]\n" + "\n".join(lines) + "\n[/COGNITIVE STATE]"

    def reset(self) -> None:
        """Clear singleton instance — used after db path changes."""
        with self._lock:
            AgentProcessor._instance = None


__all__ = ["AgentProcessor", "WORKSPACE", "DB_PATH"]
