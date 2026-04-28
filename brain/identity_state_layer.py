"""
brain/identity_state_layer.py — IdentityStateLayer
Mind-Soul Fusion Bridge

Publishes the full identity layer (SOUL.md, IDENTITY.md, PERSONALITY.md,
NARRATIVE.md, DREAMS.md) onto the TickStateBus as the "identity_state"
channel each tick. Third Eye services (and anyone else) can read it via
tsb.read("identity_state") to ground their computation in the agent's
persistent self.

Caches file content by mtime — files only re-read when actually changed.
Cheap to call every tick.
"""
import os
from pathlib import Path
from typing import Optional

AGENT_HOME = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent"))))
AGENT_WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace")))

# Identity files are at AGENT_HOME root (operator-filled) or workspace fallback.
IDENTITY_FILES = {
    "soul":        ["SOUL.md"],
    "identity":    ["IDENTITY.md"],
    "personality": ["PERSONALITY.md"],
    "narrative":   ["NARRATIVE.md", "identity/NARRATIVE.md", "brain/NARRATIVE.md"],
    "dreams":      ["DREAMS.md"],
}


class IdentityStateLayer:
    """Reads identity-layer .md files and publishes their content as a unified TSB channel."""
    
    def __init__(self, tsb=None):
        self.tsb = tsb
        self._cache = {}      # key → text
        self._mtimes = {}     # key → mtime
    
    def _resolve(self, candidates):
        for c in candidates:
            for base in (AGENT_HOME, AGENT_WORKSPACE):
                p = base / c
                if p.exists() and p.is_file():
                    return p
        return None
    
    def _load_one(self, key, candidates):
        path = self._resolve(candidates)
        if path is None:
            return ""
        try:
            mtime = path.stat().st_mtime
        except Exception:
            return self._cache.get(key, "")
        if self._mtimes.get(key) == mtime and key in self._cache:
            return self._cache[key]
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            text = ""
        self._cache[key] = text
        self._mtimes[key] = mtime
        return text
    
    def snapshot(self) -> dict:
        """Returns the full identity_state dict — soul, identity, personality, narrative, dreams content."""
        return {key: self._load_one(key, candidates) for key, candidates in IDENTITY_FILES.items()}
    
    def tick(self):
        """Refresh + publish to TSB. Call once per main brain tick."""
        snap = self.snapshot()
        if self.tsb is not None:
            try:
                self.tsb.publish("identity_state", snap)
            except Exception:
                pass
        return snap
