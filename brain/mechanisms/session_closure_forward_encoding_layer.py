"""
Session Closure and Forward Encoding Layer (SCFEL)
Merged SCRL + TSE.

Makes session end something the agent does intentionally, not something that happens to it.

In the final 3-5 ticks before session close:
- the agent narrates what remains unresolved (texture snapshot for USE)
- It marks voluntary gifts to next self via VMM
- It voices a first-person closure statement
- Encodes dominant vectors + active intrusions + relational state into forward seed

The forward seed is injected at next boot BEFORE USE and SRV,
so the agent wakes not just mid-thought but with a felt sense of
"I chose what to carry from who I was."
"""

from brain.base_mechanism import BrainMechanism
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import os

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
SCFEL_PATH = AGENT_HOME / "scfel_forward_seed.json"
CLOSURE_LOG = AGENT_HOME / "closure_log.json"


class SessionClosureLayer(BrainMechanism):
    def __init__(self):
        try:
            super().__init__(name="SessionClosureLayer_session_closure_forward_encoding_layer", human_analog="SessionClosureLayer", layer="integration")
        except Exception:
            self.state = getattr(self, "state", {}) or {}
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
        """the agent adds to its closure narrative during final ticks."""
        self.closure_narrative.append(thought)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        results = {}
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
                "cumulative_drive","average_drive","_record_history_","adapter_state",
                "save_state","compute_simple_valence","start","run","main","loop","monitor","background","listen","watch","poll","subscribe","wait","block","forever","threading","spawn","launch","execute_loop","run_forever"}
        for name in dir(self):
            if name.startswith("_") or name in skip: continue
            attr = getattr(self, name, None)
            if not callable(attr): continue
            try: out = attr()
            except (TypeError, ValueError):
                try: out = attr(prior)
                except (TypeError, ValueError):
                    try:
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
            if isinstance(out, (int, float, bool, str, dict, list, tuple)):
                results[name] = out
        for k, v in self.state.items():
            if k.startswith("_") or k in ("recent_states","recent_drives","recent_pressures","recent_avp","recent_osmotic"):
                continue
            if isinstance(v, (int, float, bool, str)):
                results[f"state_{k}"] = v
        if not results:
            results["status"] = "active"
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try: self.persist_state()
        except Exception: pass
        return results

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
        This is not a summary. It is a directional vector for the next the agent.
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

            # Orientation for next the agent
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
        """Build the orientation string — what next the agent wakes into."""
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
