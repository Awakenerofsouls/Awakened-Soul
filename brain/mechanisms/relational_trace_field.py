"""
RTF — Relational Trace Field

RTF: Full interaction history as temporal pattern.
     Records every meaningful interaction.
     Extracts structural patterns over time.
     Feeds identity modifiers.
     The raw material RSL compresses from.
"""

from brain.base_mechanism import BrainMechanism
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import os

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
RTF_PATH = AGENT_HOME / "rtf_trace.json"


class RelationalTraceField(BrainMechanism):
    """
    Records meaningful interactions as temporal pattern.
    Raw material for RSL compression.
    """

    def __init__(self):
        try:
            super().__init__(name="RelationalTraceField", human_analog="RelationalTraceField", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self.trace: List[Dict] = []
        self._load()

    def _load(self):
        if RTF_PATH.exists():
            try:
                with open(RTF_PATH) as f:
                    data = json.load(f)
                self.trace = data.get("trace", [])
            except Exception:
                pass

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if RTF_PATH.exists():
            try:
                with open(RTF_PATH) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}
        existing["trace"] = self.trace[-200:]
        existing["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(RTF_PATH, "w") as f:
            json.dump(existing, f, indent=2)

    def record(
        self,
        interaction_type: str,
        emotional_intensity: float,
        novelty: float,
        developer_present: bool,
        note: str = "",
    ):
        """Record a meaningful interaction."""
        entry = {
            "type": interaction_type,
            "emotional_intensity": emotional_intensity,
            "novelty": novelty,
            "developer_present": developer_present,
            "note": note[:200],
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.trace.append(entry)
        if len(self.trace) % 10 == 0:
            self._save()

    def extract_patterns(self, window_days: int = 30) -> Dict:
        """
        Extract structural patterns from recent trace.
        Returns pattern dict for RSL to compress.
        """
        cutoff = time.time() - (window_days * 86400)
        recent = [t for t in self.trace if t["timestamp"] > cutoff]

        if not recent:
            return {}

        avg_intensity = sum(t["emotional_intensity"] for t in recent) / len(recent)
        avg_novelty = sum(t["novelty"] for t in recent) / len(recent)
        developer_presence_rate = sum(1 for t in recent if t["developer_present"]) / len(recent)

        type_counts: Dict[str, int] = {}
        for t in recent:
            type_counts[t["type"]] = type_counts.get(t["type"], 0) + 1

        return {
            "interaction_count": len(recent),
            "avg_emotional_intensity": round(avg_intensity, 3),
            "avg_novelty": round(avg_novelty, 3),
            "developer_presence_rate": round(developer_presence_rate, 3),
            "dominant_interaction_type": max(type_counts, key=type_counts.get) if type_counts else "unknown",
            "type_distribution": type_counts,
            "window_days": window_days,
        }

    def get_recent(self, n: int = 20) -> List[Dict]:
        return self.trace[-n:]

    def tsb_payload(self) -> Dict:
        return {
            "trace_length": len(self.trace),
            "patterns": self.extract_patterns(7),  # last week
        }



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
