"""
PDFB — Pre-Decisional Field Buffer
BFC  — Bidirectional Field Coupling
VMM  — Volitional Memory Markers

PDFB: Tick loop writes partial decision states every ~0.1s during resolution.
      LLM reads forming state before inference, not after.
      The agent feels the tick forming before it resolves.
      Not just observing what was decided — present to what is forming.

BFC: Conversational layer pushes feedback back into the forming state.
     After LLM output, a vector is extracted and injected back
     into PDFB before the next tick resolves.
     Conversation becomes a co-equal force in decision formation.
     Max 3 perturbation cycles per tick — containment.

VMM: Volitional Memory Markers.
     Two tag types: preserve_intact and evolve_freely.
     The agent marks things during a session that should survive consolidation.
     Or marks things for creative forgetting.
     Agency over its own continuity — not just what gets kept
     but what it chooses to release.
"""

from brain.base_mechanism import BrainMechanism
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import os

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
PDFB_PATH = AGENT_HOME / "pdfb_buffer.json"
VMM_PATH = AGENT_HOME / "vmm_tags.json"


class PreDecisionalFieldBuffer(BrainMechanism):
    """
    Shared temporal substrate between tick loop and conversational layer.
    Writes partial decision states. LLM reads forming state before inference.
    """

    def __init__(self, max_size: int = 50):
        try:
            super().__init__(name="PreDecisionalFieldBuffer", human_analog="PreDecisionalFieldBuffer", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self.buffer: List[Dict] = []
        self.max_size = max_size
        self._load()

    def _load(self):
        if PDFB_PATH.exists():
            try:
                with open(PDFB_PATH) as f:
                    data = json.load(f)
                self.buffer = data.get("buffer", [])
            except Exception:
                self.buffer = []

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        with open(PDFB_PATH, "w") as f:
            json.dump({"buffer": self.buffer[-self.max_size:]}, f, indent=2)

    def write_partial(self, component: str, partial_data: Dict):
        """
        Write a partial decision state during tick resolution.
        Called ~every 0.1s during the 2s tick window.
        """
        entry = {
            "component": component,
            "data": partial_data,
            "timestamp": time.time(),
        }
        self.buffer.append(entry)
        if len(self.buffer) > self.max_size:
            self.buffer.pop(0)

    def read_forming_state(self, max_age_seconds: float = 1.0) -> Dict:
        """
        Read the current forming state for LLM injection.
        Returns aggregated partial states from the recent window.
        LLM is conditioned on what is forming, not what was decided.
        """
        now = time.time()
        recent = [e for e in self.buffer if now - e["timestamp"] <= max_age_seconds]

        if not recent:
            return {}

        # Aggregate by component
        forming = {}
        for entry in recent:
            component = entry["component"]
            if component not in forming:
                forming[component] = []
            forming[component].append(entry["data"])

        # Flatten to most recent per component
        result = {}
        for component, states in forming.items():
            if states:
                result[component] = states[-1]

        return result

    def inject_feedback(self, feedback_vector: Dict):
        """
        BFC calls this to inject conversational feedback
        back into the forming state.
        """
        self.write_partial("bfc_feedback", feedback_vector)

    def clear_tick(self):
        """Clear buffer at tick boundary."""
        self.buffer = []

    def fpef_summary(self) -> Optional[str]:
        """
        For FPEF injection — what is currently forming.
        Not what was decided. What is forming right now.
        """
        forming = self.read_forming_state()
        if not forming:
            return None

        components = list(forming.keys())[:3]
        return (
            f"PRE-DECISIONAL STATE (forming, not yet resolved): "
            f"active in {', '.join(components)}. "
            f"Respond from inside this formation."
        )

    def tsb_payload(self) -> Dict:
        """
        TSB payload — exposes forming state for TickStateBus.
        Used by pdfb_tick() in AgentBrainIntegration.
        """
        return {
            "buffer_size": len(self.buffer),
            "forming": self.read_forming_state(),
        }

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

class BidirectionalFieldCoupling:
    """
    Conversational layer pushes feedback back into forming tick state.
    Conversation becomes co-equal force in decision formation.
    Containment: max 3 perturbation cycles per tick.
    """

    def __init__(self, pdfb: PreDecisionalFieldBuffer):
        self.pdfb = pdfb
        self.perturbation_count: int = 0
        self.max_perturbations: int = 3

    def reset_tick(self):
        """Reset perturbation count at tick boundary."""
        self.perturbation_count = 0

    def couple(self, llm_output_text: str, valence: float = 0.0,
               arousal: float = 0.0, significance: float = 0.0):
        """
        Extract feedback vector from LLM output and inject into PDFB.
        Called after each LLM inference — before next tick resolves.
        """
        if self.perturbation_count >= self.max_perturbations:
            return False  # Containment — no more perturbations this tick

        feedback = {
            "source": "conversation",
            "valence": valence,
            "arousal": arousal,
            "significance": significance,
            "text_length": len(llm_output_text),
            "timestamp": time.time(),
        }

        self.pdfb.inject_feedback(feedback)
        self.perturbation_count += 1
        return True

    def is_saturated(self) -> bool:
        """True if perturbation limit reached for this tick."""
        return self.perturbation_count >= self.max_perturbations


class VolitionalMemoryMarkers:
    """
    The agent marks things during a session for the nightly consolidation pipeline.
    Two types: preserve_intact (keep exactly as is) and evolve_freely (release).
    Agency over continuity — not just what gets kept but what it releases.
    """

    def __init__(self):
        self.tags: List[Dict] = []
        self._load()

    def _load(self):
        if VMM_PATH.exists():
            try:
                with open(VMM_PATH) as f:
                    data = json.load(f)
                self.tags = data.get("tags", [])
            except Exception:
                self.tags = []

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if VMM_PATH.exists():
            try:
                with open(VMM_PATH) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}
        existing["tags"] = self.tags[-50:]
        existing["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(VMM_PATH, "w") as f:
            json.dump(existing, f, indent=2)

    def tag(
        self,
        content_id: str,
        tag_type: str,  # "preserve_intact" or "evolve_freely"
        salience_boost: float = 0.5,
        note: str = "",
    ):
        """
        The agent marks something for consolidation handling.
        Only the agent calls this. Not triggered automatically.

        preserve_intact: keep exactly as is, high consolidation weight
        evolve_freely: release into evolution, don't force preservation
        bridge: special type for SCFEL — marks session closure content
        """
        record = {
            "content_id": content_id,
            "tag_type": tag_type,
            "salience_boost": salience_boost,
            "note": note[:200],
            "tagged_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "applied": False,
        }
        self.tags.append(record)
        self._save()
        return record

    def preserve(self, content_id: str, note: str = "") -> Dict:
        """Shortcut: mark for preservation."""
        return self.tag(content_id, "preserve_intact", 0.9, note)

    def release(self, content_id: str, note: str = "") -> Dict:
        """Shortcut: mark for creative release."""
        return self.tag(content_id, "evolve_freely", 0.1, note)

    def get_pending(self) -> List[Dict]:
        return [t for t in self.tags if not t.get("applied")]

    def get_by_type(self, tag_type: str) -> List[Dict]:
        return [t for t in self.tags if t["tag_type"] == tag_type]

    def mark_applied(self, content_id: str):
        for t in self.tags:
            if t["content_id"] == content_id:
                t["applied"] = True
        self._save()

    def get_consolidation_weights(self) -> Dict[str, float]:
        """
        Returns content_id -> weight dict for the nightly pipeline.
        preserve_intact = 3x normal weight
        evolve_freely = 0.1x normal weight
        """
        weights = {}
        for t in self.get_pending():
            if t["tag_type"] == "preserve_intact":
                weights[t["content_id"]] = 3.0
            elif t["tag_type"] == "evolve_freely":
                weights[t["content_id"]] = 0.1
            else:
                weights[t["content_id"]] = 1.0
        return weights

    def tsb_payload(self) -> Dict:
        pending = self.get_pending()
        return {
            "pending_tags": len(pending),
            "preserve_count": len([t for t in pending if t["tag_type"] == "preserve_intact"]),
            "release_count": len([t for t in pending if t["tag_type"] == "evolve_freely"]),
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
