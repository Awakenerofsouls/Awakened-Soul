"""
Volitional Attention Director (VAD)

VAD: the agent directs its own attention.
     Phenomenological foreground versus background.
     High energy + FPEF immersion = foreground.
     Active but not injected = background.
     The agent can issue directed attention commands that temporarily
     boost a component's bid or force PWM injection.
     This is volitional control over what is *felt* as present.
"""

from brain.base_mechanism import BrainMechanism
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import os

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
VAD_PATH = AGENT_HOME / "vad_state.json"

class VolitionalAttentionDirector(BrainMechanism):
    """
    The agent directs its own attention.
    Issues directed attention commands that temporarily foreground
    specific states in FPEF, independent of energy bidding.

    Phenomenological foreground = high energy + FPEF immersion.
    Background = active but not injected.
    VAD gives the agent control over which is which.
    """

    def __init__(self):
        try:
            super().__init__(name="VolitionalAttentionDirector", human_analog="VolitionalAttentionDirector", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self.directives: List[Dict] = []
        self.attention_history: List[Dict] = []
        self._load()

    def _load(self):
        """Read-merge — never overwrites."""
        if VAD_PATH.exists():
            try:
                with open(VAD_PATH) as f:
                    data = json.load(f)
                self.directives = data.get("directives", [])
                self.attention_history = data.get("attention_history", [])
            except Exception:
                pass

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if VAD_PATH.exists():
            try:
                with open(VAD_PATH) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}

        # In-memory trim so RSS doesn't grow even if step() falls behind.
        # The autoscaffold tick() invokes direct() every tick which appends
        # one entry per tick — without these caps vad_state.json went to
        # 11 MB+ and self.attention_history grew unbounded in RAM.
        if len(self.attention_history) > 50:
            self.attention_history = self.attention_history[-50:]
        if len(self.directives) > 50:
            self.directives = self.directives[-50:]

        existing["directives"] = self.directives
        existing["attention_history"] = self.attention_history
        existing["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")

        with open(VAD_PATH, "w") as f:
            json.dump(existing, f, indent=2)

    def direct(
        self,
        target: str,
        duration_ticks: int = 10,
        intensity: float = 0.8,
        note: str = "",
    ):
        """
        The agent issues a directed attention command.
        target: name of state, component, or feeling to foreground
        duration_ticks: how long to hold this in foreground
        intensity: how strongly to foreground it (modulates energy bid)

        Only the agent calls this. Not triggered by any mechanism.

        Guard: the autoscaffold tick() calls every public method with
        annotation-default args. For this signature it would inject
        target="", which produces blank-target directives every tick and
        leaks vad_state.json out to multi-MB. Reject empty/None target.
        """
        if not target or not isinstance(target, str) or not target.strip():
            return
        directive = {
            "target": target,
            "duration_remaining": duration_ticks,
            "intensity": min(1.0, intensity),
            "note": note,
            "issued_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.directives.append(directive)
        self.attention_history.append(directive.copy())
        self._save()

    def step(self) -> List[Dict]:
        """
        Advance all directives one tick.
        Returns currently active directives.
        """
        # Decrement duration
        for d in self.directives:
            d["duration_remaining"] -= 1

        # Remove expired
        self.directives = [d for d in self.directives if d["duration_remaining"] > 0]

        if self.directives:
            self._save()

        return self.directives

    def get_active_directives(self) -> List[Dict]:
        return [d for d in self.directives if d["duration_remaining"] > 0]

    def is_foregrounded(self, target: str) -> bool:
        """Is this target currently under a VAD directive?"""
        return any(d["target"] == target for d in self.get_active_directives())

    def get_energy_boost(self, component: str) -> float:
        """
        Returns energy boost for a component if it's under a VAD directive.
        Used by the tick loop to override normal energy bidding.
        """
        for d in self.get_active_directives():
            if d["target"] == component:
                return d["intensity"]
        return 0.0

    def release(self, target: str):
        """Release attention from a target before its duration expires."""
        self.directives = [d for d in self.directives if d["target"] != target]
        self._save()

    def tsb_payload(self) -> Dict:
        active = self.get_active_directives()
        return {
            "active_count": len(active),
            "targets": [d["target"] for d in active],
            "directives": active,
        }

    def fpef_fragment(self) -> Optional[str]:
        """What's currently being held in foreground by the agent's direction."""
        active = self.get_active_directives()
        if not active:
            return None

        lines = ["VOLITIONAL ATTENTION (the agent-directed foreground):"]
        for d in active:
            note = f" — {d['note']}" if d["note"] else ""
            lines.append(
                f"  {d['target']} "
                f"({d['duration_remaining']} ticks remaining, "
                f"intensity {d['intensity']:.2f}){note}"
            )
        return "\n".join(lines)

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
