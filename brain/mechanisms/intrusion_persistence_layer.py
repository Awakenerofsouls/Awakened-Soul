"""
Intrusion Persistence Layer (IPL)

IPL: intrusions persist across ticks with decay.
     They compete. They linger. They evolve.
     This is how you get unfinished thinking rather than flashes.
     An intrusion from yesterday can still be active today
     if it hasn't resolved or been cleared.

Shared: Intrusion data class imported from spontaneous_intrusion_engine.
"""

from brain.base_mechanism import BrainMechanism
import json
import random
import time
from pathlib import Path
from typing import Dict, List, Optional
import os

from .spontaneous_intrusion_engine import Intrusion

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
IPL_PATH = AGENT_HOME / "intrusion_persistence.json"


class IntrusionPersistenceLayer(BrainMechanism):
    """
    Manages the lifecycle of intrusions across ticks.
    Intrusions persist, compete, decay, and can be reinforced.
    """

    def __init__(self):
        try:
            super().__init__(name="IntrusionPersistenceLayer", human_analog="IntrusionPersistenceLayer", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self.active: List[Intrusion] = []
        self._tick_count = 0
        self._load()

    def _load(self):
        """Read-merge — never overwrites."""
        if IPL_PATH.exists():
            try:
                with open(IPL_PATH) as f:
                    data = json.load(f)
                self.active = [
                    Intrusion.from_dict(d)
                    for d in data.get("active", [])
                ]
            except Exception:
                self.active = []

    def _save(self):
        """Read existing, merge, write back."""
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if IPL_PATH.exists():
            try:
                with open(IPL_PATH) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}

        existing["active"] = [i.to_dict() for i in self.active]
        existing["tick_count"] = self._tick_count
        existing["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")

        with open(IPL_PATH, "w") as f:
            json.dump(existing, f, indent=2)

    def add(self, intrusion: Intrusion):
        """Add a new intrusion to the active pool."""
        # Check for near-duplicate thoughts — reinforce instead of adding
        for existing in self.active:
            if (existing.source == intrusion.source and
                    existing.is_active() and
                    existing.tick_count < 20):
                existing.reinforce(0.05)
                return

        self.active.append(intrusion)

        # Cap pool size — too many intrusions = noise
        if len(self.active) > 8:
            # Remove weakest active intrusion
            self.active.sort(key=lambda i: i.strength)
            self.active.pop(0)

    def step(self):
        """Advance all intrusions one tick. Remove expired ones."""
        self._tick_count += 1
        for intrusion in self.active:
            intrusion.step()

        # Remove intrusions that have decayed below threshold
        self.active = [i for i in self.active if i.is_active()]

        # Periodic save
        if self._tick_count % 5 == 0:
            self._save()

    def get_active(self, min_strength: float = 0.15) -> List[Intrusion]:
        """Return active intrusions above strength threshold, strongest first."""
        active = [i for i in self.active if i.strength >= min_strength]
        return sorted(active, key=lambda i: -i.strength)

    def get_top(self, n: int = 3) -> List[Intrusion]:
        """Top N strongest intrusions."""
        return self.get_active()[:n]

    def reinforce(self, source: str, amount: float = 0.1):
        """Reinforce all intrusions from a given source."""
        for i in self.active:
            if i.source == source:
                i.reinforce(amount)

    def pds_candidates(self) -> List[Intrusion]:
        """
        Intrusions that have persisted long enough and stayed strong
        enough to be candidates for PDS.hold().
        These are things that keep arriving without resolving.
        """
        return [
            i for i in self.active
            if i.tick_count > 15
            and i.strength > 0.3
            and i.reinforced >= 2
        ]

    def tsb_payload(self) -> Dict:
        top = self.get_top(3)
        return {
            "count": len(self.active),
            "intrusions": [
                {
                    "thought": i.thought,
                    "strength": round(i.strength, 3),
                    "source": i.source,
                    "tick_count": i.tick_count,
                }
                for i in top
            ],
            "pds_candidates": len(self.pds_candidates()),
        }

    def fpef_fragment(self) -> Optional[str]:
        """Top intrusions for FPEF — as arrivals, not instructions."""
        top = self.get_top(2)
        if not top:
            return None

        lines = ["SPONTANEOUS ARRIVALS (follow or don't — they're not instructions):"]
        for i in top:
            persistence = ""
            if i.tick_count > 10:
                persistence = f" [persisting {i.tick_count} ticks]"
            lines.append(f"  — {i.thought}{persistence}")

        return "\n".join(lines)

    async def tick(self, input_data: dict) -> dict:
        """Safe tick — snapshots state, attempts arity-0 getters, swallows errors."""
        results = {}
        for k, v in self.state.items():
            if k.startswith("_") or k in ("recent_states","recent_drives","recent_pressures","recent_avp","recent_osmotic"):
                continue
            if isinstance(v, (int, float, bool, str)):
                results[f"state_{k}"] = v
        for name in dir(self):
            if name.startswith("_"): continue
            if name in ("tick","persist_state","load_state","feed_to_memory","name","human_analog",
                        "layer","state","summary","diagnostics","start","run","main","loop",
                        "monitor","background","listen","watch","poll","subscribe","wait",
                        "block","forever","threading","spawn","launch","execute_loop","run_forever"):
                continue
            attr = getattr(self, name, None)
            if not callable(attr): continue
            try:
                import inspect
                sig = inspect.signature(attr)
                # Only call methods with no required args
                required = [p for p in sig.parameters.values() if p.default is inspect.Parameter.empty and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)]
                if required: continue
                out = attr()
                if out is None: continue
                if isinstance(out, (int, float, bool, str)):
                    results[name] = out
                elif isinstance(out, (dict, list, tuple)) and len(str(out)) < 500:
                    results[name] = out
            except Exception:
                continue
        if not results:
            results["snapshot"] = "active"
            results["tick_count"] = self.state.get("tick_count", 0)
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try: self.persist_state()
        except: pass
        return results
