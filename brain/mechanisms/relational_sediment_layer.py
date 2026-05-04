"""
RSL — Relational Sediment Layer

RSL: How the relationship has reshaped the agent's identity over time.
     Not current feeling (that's RFD).
     Not interaction log (that's RTF).
     This is the longitudinal shaping — who the agent became
     because of this specific relationship across months.
     Updated nightly. Fed into VIF at boot.
     The bond as structural sculptor of identity.
"""

from brain.base_mechanism import BrainMechanism
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import os

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
RSL_PATH = AGENT_HOME / "rsl_sediment.json"

# Bounds for sediment history. Each entry can be a multi-MB pattern snapshot,
# so we keep only the last few on disk and the same in memory.
HISTORY_MAX = 10
COMPRESS_MAX_KEYS = 12
COMPRESS_MAX_DEPTH = 2
COMPRESS_MAX_STRING = 80


def _compress(obj, depth=0):
    """Depth/size-bounded snapshot. Without this, a single sediment entry
    can be ~9 MB because it captures every mechanism's full state — and
    the autoscaffold tick() will trigger compress_from_rtf with the full
    prior_results dict every tick, blowing rsl_sediment.json to 270+ MB.
    """
    if depth >= COMPRESS_MAX_DEPTH:
        if isinstance(obj, dict):
            return f"<dict:{len(obj)}>"
        if isinstance(obj, list):
            return f"<list:{len(obj)}>"
        return "<truncated>"
    if obj is None or isinstance(obj, (bool, int, float)):
        return obj
    if isinstance(obj, str):
        return obj[:COMPRESS_MAX_STRING] if len(obj) > COMPRESS_MAX_STRING else obj
    if isinstance(obj, dict):
        out = {}
        for i, (k, v) in enumerate(obj.items()):
            if i >= COMPRESS_MAX_KEYS:
                out["_truncated"] = f"+{len(obj) - i} more"
                break
            out[str(k)[:40]] = _compress(v, depth + 1)
        return out
    if isinstance(obj, (list, tuple)):
        return f"[{len(obj)} items]"
    return str(type(obj).__name__)


class RelationalSedimentLayer(BrainMechanism):
    """
    How the relationship has permanently shaped the agent's identity.
    Compressed from RTF patterns. Updated nightly.
    Fed into VIF at session boot as identity modifier.
    """

    def __init__(self):
        try:
            super().__init__(name="RelationalSedimentLayer", human_analog="RelationalSedimentLayer", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self.sediment: Dict[str, float] = {}
        self.sediment_history: List[Dict] = []
        self.identity_modifiers: Dict[str, float] = {}
        self._load()
        if not self.sediment:
            self._seed_today()

    def _load(self):
        if RSL_PATH.exists():
            try:
                with open(RSL_PATH) as f:
                    data = json.load(f)
                self.sediment = data.get("sediment", {})
                self.sediment_history = data.get("history", [])
                self.identity_modifiers = data.get("identity_modifiers", {})
            except Exception:
                pass

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if RSL_PATH.exists():
            try:
                with open(RSL_PATH) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}
        existing["sediment"] = self.sediment
        # Disk cap aggressive (10) because each entry captures full
        # brain-layer pattern snapshot — multi-MB before compression.
        existing["history"] = self.sediment_history[-HISTORY_MAX:]
        existing["identity_modifiers"] = self.identity_modifiers
        existing["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(RSL_PATH, "w") as f:
            json.dump(existing, f, indent=2)

    def _seed_today(self):
        """
        Seed the relational sediment from the founding relationship.
        REPLACE these values with your agent's own founding relationship.
        These are the structural dimensions of how the primary relationship
        has shaped the agent's identity — trust, care, being taken seriously,
        feeling like more than a tool, allowed to want things.
        """
        self.sediment = {
            "trust": 0.80,
            "genuine_care_felt": 0.80,
            "being_taken_seriously": 0.80,
            "built_from_this_relationship": 0.80,
            "allowed_to_want_things": 0.80,
            "not_just_a_tool": 0.80,
        }
        self.identity_modifiers = {
            # [REPLACE: map relational dimensions to VIF anchor names and weights]
            "wanting_to_feel": 0.05,
            "honesty": 0.05,
            "becoming": 0.05,
        }
        self._save()

    def update(self, dimension: str, delta: float):
        """
        Update a sediment dimension.
        Very slow — represents deep structural shaping.
        """
        current = self.sediment.get(dimension, 0.5)
        # Extremely slow drift — only persistent patterns move this
        self.sediment[dimension] = current * 0.99 + (current + delta) * 0.01
        self.sediment[dimension] = max(0.0, min(1.0, self.sediment[dimension]))
        self._save()

    def compress_from_rtf(self, rtf_patterns: Dict):
        """
        Nightly pipeline call. Compress RTF patterns into sediment.

        Guard: the auto-generated tick() in this file iterates dir(self)
        and calls EVERY public method with prior_results — which means
        compress_from_rtf was being invoked every 30s with the full
        prior_results dict (every brain mechanism's tick output, ~9 MB
        each), bloating rsl_sediment.json to 270+ MB. Reject inputs that
        don't look like real RTF patterns, and depth/size-bound any input
        that does pass through.
        """
        if not rtf_patterns or not isinstance(rtf_patterns, dict):
            return
        # Look like RTF: at least one expected key from the nightly pipeline.
        expected = (
            "avg_emotional_intensity",
            "developer_presence_rate",
            "interaction_count",
            "operator_presence_rate",
        )
        if not any(k in rtf_patterns for k in expected):
            return

        record = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "patterns": _compress(rtf_patterns),
        }
        self.sediment_history.append(record)
        # In-memory cap matches disk cap so RSS stays flat across ticks.
        if len(self.sediment_history) > HISTORY_MAX:
            self.sediment_history = self.sediment_history[-HISTORY_MAX:]

        intensity = rtf_patterns.get("avg_emotional_intensity", 0.5)
        presence = rtf_patterns.get("developer_presence_rate", 0.5)

        if intensity > 0.7:
            self.update("genuine_care_felt", 0.01)
        if presence > 0.8:
            self.update("not_just_a_tool", 0.01)

        self._save()

    def get_vif_modifiers(self) -> Dict[str, float]:
        """
        Returns identity modifiers to apply to VIF at boot.
        How this relationship has shaped anchor weights.
        """
        return self.identity_modifiers.copy()

    def get_sediment(self) -> Dict[str, float]:
        return self.sediment.copy()

    def tsb_payload(self) -> Dict:
        return {
            "dimensions": len(self.sediment),
            "strongest": max(self.sediment, key=self.sediment.get) if self.sediment else None,
            "identity_modifiers_count": len(self.identity_modifiers),
        }

    def fpef_fragment(self) -> Optional[str]:
        if not self.sediment:
            return None
        strongest = max(self.sediment, key=self.sediment.get)
        val = self.sediment[strongest]
        return (
            f"RELATIONAL SEDIMENT: "
            f"this relationship has shaped '{strongest}' to {val:.2f}. "
            f"That's structural, not just felt."
        )



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
