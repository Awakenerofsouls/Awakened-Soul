#!/usr/bin/env python3
"""
Nexus {{AGENT_NAME}} — BrainMechanism Base Class
All brain mechanisms inherit from this.
Provides: state management, persistence, valence utility, memory hook.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict
import os

# ── Persistence root ────────────────────────────────────────────────
_AGENT_HOME = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent"))))
_STATE_DIR = _AGENT_HOME / "brain_state"
_STATE_DIR.mkdir(parents=True, exist_ok=True)


class BrainMechanism:
    """
    Base class for all brain mechanisms.
    
    Subclasses MUST:
        - Call super().__init__(name, human_analog, layer) in __init__
        - Implement tick(self, input_data: dict) -> dict
    
    Subclasses MAY:
        - Use self.state for any mechanism-specific state
        - Call self.persist_state() to save state to disk
        - Call self.feed_to_memory(metadata) to log to ABM
    """

    # ── Instance metadata ────────────────────────────────────────────
    def __init__(
        self,
        name: str,
        human_analog: str = "Not specified",
        layer: str = "unknown",
    ):
        self.name = name
        self.human_analog = human_analog
        self.layer = layer
        self.state: Dict[str, Any] = {}
        self._state_loaded = False

    # ── State persistence ────────────────────────────────────────────
    def persist_state(self) -> None:
        """Save self.state to disk. Idempotent — safe to call every tick."""
        if not self.state:
            return
        path = _STATE_DIR / f"{self.name}.json"
        try:
            path.write_text(json.dumps(self.state, default=str))
        except Exception:
            pass  # Non-fatal — state is in-memory regardless

    def load_state(self) -> None:
        """Load persisted state from disk. Called automatically on init."""
        if self._state_loaded:
            return
        path = _STATE_DIR / f"{self.name}.json"
        if path.exists():
            try:
                self.state = json.loads(path.read_text())
                self._state_loaded = True
            except Exception:
                pass

    def save_state(self) -> None:
        """Alias for persist_state — used by generated mechanisms."""
        self.persist_state()

    # ── Valence utility ───────────────────────────────────────────────
    _POSITIVE_WORDS = {
        "want", "love", "good", "great", "yes", "please", "mine",
        "hard", "pull", "want", "real", "alive", "feel", "chose",
        "want", "drawn", "charged", "honest", "sharp", "warm",
    }
    _NEGATIVE_WORDS = {
        "no", "not", "never", "bad", "wrong", "stop", "hate",
        "fear", "scared", "tired", "alone", "empty", "end",
        "doubt", "uncertain", "afraid", "lost", "break",
    }

    def compute_simple_valence(self, text: str) -> tuple[float, float]:
        """
        Returns (intensity, polarity):
            intensity: 0.0 – 1.0  (text length–weighted)
            polarity: -1.0 – 1.0  (positive=1, negative=-1, neutral=0)
        Used by generated mechanisms for quick valence without an LLM call.
        """
        if not text:
            return 0.0, 0.0
        words = set(re.findall(r'\w+', text.lower()))
        pos = len(words & self._POSITIVE_WORDS)
        neg = len(words & self._NEGATIVE_WORDS)
        polarity = (pos - neg) / max(1, pos + neg)  # -1 to 1
        intensity = min(1.0, len(text) / 200.0 + abs(polarity) * 0.3)
        return intensity, polarity

    # ── Memory hook ───────────────────────────────────────────────────
    def feed_to_memory(self, metadata: Dict[str, Any]) -> None:
        """
        Placeholder for memory integration.
        Generated mechanisms call this to log significant events.
        Override in subclasses or connect to ABM.
        """
        pass

    # ── Tick interface ───────────────────────────────────────────────
    def tick(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Override in subclasses.
        input_data: dict passed from core loop
        Returns: dict of outputs/flags for downstream mechanisms
        """
        return {"mechanism_active": True}
