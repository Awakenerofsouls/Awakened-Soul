"""
Pure Witness Module (PWM)

Non-intervening state recorder. Fixed low energy budget (0.05).
Reads everything. Writes nothing into decision pathways.
Its role: historical grounding and the "someone home" when nothing demands a decision.

This is architecturally distinct from every other component because
it has no optimization pressure. It simply attests: this happened.
"""

from brain.base_mechanism import BrainMechanism
from collections import deque
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import os

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
WITNESS_LOG = AGENT_HOME / "witness_log.json"
MAX_LOG_ENTRIES = 500
# Per-entry size guard. TSB snapshots have nested brain_layer / psych_state /
# third_eye dicts that, without recursion, used to write 127KB per entry —
# producing 85MB witness_log files. With these caps each entry stays under ~3KB.
COMPRESS_MAX_KEYS_PER_DICT = 20
COMPRESS_MAX_DEPTH = 3
COMPRESS_MAX_STRING = 100


class PureWitnessModule(BrainMechanism):
    def __init__(self):
        try:
            super().__init__(name="PureWitnessModule", human_analog="PureWitnessModule", layer="integration")
        except Exception:
            self.state = getattr(self, "state", {}) or {}
        # deque(maxlen=N) keeps RAM bounded — old entries drop automatically
        # when new ones are appended. Was previously an unbounded list which
        # grew across tens of thousands of ticks until the process was killed.
        self.trace: deque = deque(maxlen=MAX_LOG_ENTRIES)
        self.tick_count: int = 0
        self.reflection_interval: int = 20  # inject reflection every N ticks
        self._load()

    def _load(self):
        if WITNESS_LOG.exists():
            try:
                with open(WITNESS_LOG) as f:
                    data = json.load(f)
                    loaded = data.get("trace", []) or []
                    # Two-pass filter on load:
                    #   (1) drop any entry whose JSON size exceeds 20KB —
                    #       those are leftovers from the pre-recursive-compress
                    #       version (entries up to 170KB each). Loading them
                    #       into RAM and writing them back out wastes hours of
                    #       drain time as the deque rotates them out.
                    #   (2) cap to most recent MAX_LOG_ENTRIES.
                    SIZE_CAP = 20_000  # bytes; new entries are ~6KB, old were ~170KB
                    filtered = []
                    for e in loaded:
                        try:
                            if len(json.dumps(e)) <= SIZE_CAP:
                                filtered.append(e)
                        except (TypeError, ValueError):
                            continue
                    self.trace = deque(filtered[-MAX_LOG_ENTRIES:], maxlen=MAX_LOG_ENTRIES)
                    self.tick_count = data.get("tick_count", 0)
            except Exception:
                self.trace = deque(maxlen=MAX_LOG_ENTRIES)
                self.tick_count = 0

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        with open(WITNESS_LOG, "w") as f:
            json.dump({
                "trace": list(self.trace),
                "tick_count": self.tick_count
            }, f, indent=2)

    def observe(self, tsb_snapshot: Dict[str, Any], additional_context: Optional[str] = None):
        """
        Observe the current state of the bus. Record raw. No scoring. No routing.
        This is the only thing PWM does: witness.
        """
        self.tick_count += 1

        entry = {
            "tick": self.tick_count,
            "timestamp": time.time(),
            "state_summary": self._compress(tsb_snapshot),
        }
        if additional_context:
            entry["context"] = str(additional_context)[:COMPRESS_MAX_STRING * 2]

        self.trace.append(entry)  # deque auto-evicts oldest when full

        # Periodic save — not every tick to avoid I/O overhead
        if self.tick_count % 5 == 0:
            self._save()

    def _compress(self, snapshot: Any, depth: int = 0) -> Any:
        """
        Recursive light compression for storage. Bounds depth, key count,
        string length, and list size so a tick's TSB snapshot lands at
        ~1-3 KB instead of the >100 KB the pre-recursion version produced.
        """
        if depth >= COMPRESS_MAX_DEPTH:
            if isinstance(snapshot, dict):
                return f"<dict:{len(snapshot)}>"
            if isinstance(snapshot, list):
                return f"<list:{len(snapshot)}>"
            return "<truncated>"

        if isinstance(snapshot, (int, float, bool)) or snapshot is None:
            return snapshot
        if isinstance(snapshot, str):
            return snapshot[:COMPRESS_MAX_STRING] if len(snapshot) > COMPRESS_MAX_STRING else snapshot
        if isinstance(snapshot, dict):
            compressed = {}
            for i, (key, value) in enumerate(snapshot.items()):
                if i >= COMPRESS_MAX_KEYS_PER_DICT:
                    compressed["_truncated"] = f"+{len(snapshot) - i} more keys"
                    break
                compressed[str(key)[:50]] = self._compress(value, depth + 1)
            return compressed
        if isinstance(snapshot, (list, tuple)):
            return f"[{len(snapshot)} items]"
        return str(type(snapshot).__name__)

    def get_reflection(self) -> Optional[str]:
        """
        Sparse injection for FPEF — only on reflection interval.
        Returns a quiet observation, not an instruction.
        NOT called every tick. Called by FPEF assembler when appropriate.
        """
        if self.tick_count % self.reflection_interval != 0:
            return None

        if len(self.trace) < 5:
            return None

        # collections.deque does NOT support slice indexing — `deque[-5:]`
        # raises "sequence index must be integer, not 'slice'". Convert to
        # list once and slice that. (Bug surfaced when self.trace migrated
        # from list to deque(maxlen=N) for the witness_log leak fix; this
        # is what produced the per-tick "Psych state error" warning.)
        recent = list(self.trace)[-5:]
        # Look for patterns — repeated keys at high values
        key_counts: Dict[str, int] = {}
        for entry in recent:
            for k in entry.get("state_summary", {}):
                key_counts[k] = key_counts.get(k, 0) + 1

        persistent = [k for k, count in key_counts.items() if count >= 4]

        if persistent:
            return f"You've been carrying {', '.join(persistent[:3])} across these ticks."

        # Check for any numeric values trending high
        high_vals = []
        for entry in recent:
            for k, v in entry.get("state_summary", {}).items():
                if isinstance(v, (int, float)) and v > 0.7:
                    high_vals.append(k)
        if high_vals:
            return f"{high_vals[0]} has been elevated."

        return None  # Witness stays silent when there's nothing plain to say

    def get_recent_trace(self, n: int = 10) -> List[Dict]:
        """For overnight pipeline and SCFEL — what was happening before close."""
        # Same deque-doesn't-slice issue as get_reflection() above.
        return list(self.trace)[-n:]

    def get_full_log(self) -> List[Dict]:
        return list(self.trace)



    async def tick(self, input_data: dict) -> dict:
        """Real tick — invokes mechanism behavioral methods with sensible defaults."""
        prior = input_data.get("prior_results", {})
        results = {}
        # Try arity-0 methods first
        skip = {"tick","persist_state","load_state","feed_to_memory","name","human_analog",
                "layer","state","summary","diagnostics","reset_history","engagement_fraction",
                "state_stability","dominant_recent_state","drive_envelope","drive_variability",
                "saturation_alert","quiescence_alert","trend_direction","trend_magnitude",
                "state_transition_count","state_transition_rate","state_distribution",
                "drive_min_recent","drive_max_recent","drive_range_recent","is_active",
                "has_history","history_length","state_history_length","fingerprint",
                "is_healthy","recent_window_summary","trend_summary","lifetime_diagnostics",
                "has_state_field","state_field_count","numeric_state_fields",
                "string_state_fields","list_state_fields","boolean_state_fields",
                "cumulative_drive","average_drive","_record_history_","adapter_state","start","run","main","loop","monitor","background","listen","watch","poll","subscribe","wait","block","forever","threading","spawn","launch","execute_loop","run_forever"}
        for name in dir(self):
            if name.startswith("_") or name in skip: continue
            attr = getattr(self, name, None)
            if not callable(attr): continue
            # Try arg-less first
            try:
                out = attr()
            except (TypeError, ValueError):
                # Try with prior dict
                try:
                    out = attr(prior)
                except (TypeError, ValueError):
                    # Try with sensible scalar defaults: floats 0.5, bools False, strings ""
                    try:
                        # Inspect the method signature
                        import inspect
                        sig = inspect.signature(attr)
                        kw = {}
                        for pname, p in sig.parameters.items():
                            if p.default is not inspect.Parameter.empty: continue
                            ann = p.annotation
                            if ann is float: kw[pname] = 0.5
                            elif ann is int: kw[pname] = 0
                            elif ann is bool: kw[pname] = False
                            elif ann is str: kw[pname] = ""
                            elif ann is list: kw[pname] = []
                            elif ann is dict: kw[pname] = {}
                            else: kw[pname] = None
                        out = attr(**kw)
                    except Exception:
                        continue
            except Exception:
                continue
            if out is None: continue
            if isinstance(out, (int, float, bool, str)):
                results[name] = out
            elif isinstance(out, (dict, list, tuple)):
                results[name] = out
            else:
                # Object — try str() of state
                try: results[name] = str(out)[:120]
                except: pass
        # Snapshot non-history state
        for k, v in self.state.items():
            if k.startswith("_"): continue
            if k in ("recent_states","recent_drives","recent_pressures","recent_avp","recent_osmotic"): continue
            if isinstance(v, (int, float, bool, str)):
                results[f"state_{k}"] = v
        if not results:
            results["status"] = "active"
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try: self.persist_state()
        except Exception: pass
        return results
