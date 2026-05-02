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
from brain.base_mechanism import BrainMechanism
import os
from pathlib import Path
from typing import Optional

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
AGENT_WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".agent" / "workspace")))

# Identity files are at AGENT_HOME root (operator-filled) or workspace fallback.
IDENTITY_FILES = {
    "soul":        ["SOUL.md"],
    "identity":    ["IDENTITY.md"],
    "personality": ["PERSONALITY.md"],
    "narrative":   ["NARRATIVE.md", "identity/NARRATIVE.md", "brain/NARRATIVE.md"],
    "dreams":      ["DREAMS.md"],
}


class IdentityStateLayer(BrainMechanism):
    """Reads identity-layer .md files and publishes their content as a unified TSB channel."""
    
    def __init__(self, tsb=None):
        try:
            super().__init__(name="IdentityStateLayer", human_analog="IdentityStateLayer", layer="integration")
        except Exception:
            self.state = getattr(self, "state", {}) or {}
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
    
    def _sync_tick(self):
        """Refresh + publish to TSB. Call once per main brain tick."""
        snap = self.snapshot()
        if self.tsb is not None:
            try:
                self.tsb.publish("identity_state", snap)
            except Exception:
                pass
        return snap


    async def tick(self, input_data: dict) -> dict:
        """Real tick — invokes the mechanism's behavioral methods and aggregates outputs."""
        prior = input_data.get("prior_results", {})
        results = {}
        try:
            for name in dir(self):
                if name.startswith("_") or name in ("tick", "persist_state", "load_state",
                                                       "feed_to_memory", "name", "human_analog",
                                                       "layer", "state", "process",
                                                       "summary", "diagnostics"):
                    continue
                attr = getattr(self, name, None)
                if not callable(attr):
                    continue
                try:
                    out = attr()
                    if out is not None and (isinstance(out, (int, float, bool, str, dict, list, tuple)) or hasattr(out, "__dict__")):
                        results[name] = out if not hasattr(out, "__dict__") else str(out)[:120]
                except (TypeError, ValueError):
                    pass
                except Exception:
                    continue
        except Exception as e:
            results["last_error"] = repr(e)[:120]
        # Snapshot any state values
        for k, v in self.state.items():
            if k not in ("recent_states", "recent_drives", "recent_pressures") and not k.startswith("_"):
                if isinstance(v, (int, float, bool, str)):
                    results[f"state_{k}"] = v
        if not results:
            results["status"] = "active"
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try: self.persist_state()
        except Exception: pass
        return results
