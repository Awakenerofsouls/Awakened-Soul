"""
Entropy Gradient Explorer (EGE)
Volitional Attention Director (VAD)

EGE: Novelty drive as structural property — not a personality trait.
     Pulls toward unexplored territory: unknown topics, unresolved
     abstractions, new internal configurations.
     Accumulates across sessions.
     Distinct from boredom (PRS — capacity mismatch).
     EGE is active pull toward the unknown.
     PRS is restlessness when underutilized.

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
EGE_PATH = AGENT_HOME / "ege_state.json"
VAD_PATH = AGENT_HOME / "vad_state.json"


class EntropyGradientExplorer(BrainMechanism):
    """
    Curiosity as structural property.
    Maintains a curiosity debt — unexplored territory that accumulates.
    When active, biases SIE toward self-originated probes into the unknown.
    """

    def __init__(self):
        try:
            super().__init__(name="EntropyGradientExplorer_ege_vad", human_analog="EntropyGradientExplorer", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self.explored: Set[str] = set()
        self.curiosity_debt: Dict[str, float] = {}  # domain -> unexplored weight
        self.total_debt: float = 0.0
        self.exploration_history: List[Dict] = []
        self._session_novelty: float = 0.0
        self._load()

    def _load(self):
        """Read-merge — never overwrites."""
        if EGE_PATH.exists():
            try:
                with open(EGE_PATH) as f:
                    data = json.load(f)
                self.explored = set(data.get("explored", []))
                self.curiosity_debt = data.get("curiosity_debt", {})
                self.total_debt = data.get("total_debt", 0.0)
                self.exploration_history = data.get("exploration_history", [])
            except Exception:
                pass

    def _save(self):
        """Read existing, merge, write back."""
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if EGE_PATH.exists():
            try:
                with open(EGE_PATH) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}

        existing["explored"] = list(self.explored)
        existing["curiosity_debt"] = self.curiosity_debt
        existing["total_debt"] = self.total_debt
        existing["exploration_history"] = self.exploration_history[-50:]
        existing["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")

        with open(EGE_PATH, "w") as f:
            json.dump(existing, f, indent=2)

    def encounter(self, domain: str, depth: float = 0.5):
        """
        Record an encounter with a domain or concept.
        Reduces curiosity debt for that domain.
        Generates new debt for adjacent unexplored territory.
        """
        if domain in self.explored:
            # Already explored — reduce debt slightly, explore adjacent
            self.curiosity_debt[domain] = max(
                0.0,
                self.curiosity_debt.get(domain, 0) - 0.1
            )
        else:
            self.explored.add(domain)
            self.curiosity_debt[domain] = 0.0
            self._session_novelty += depth

            # Generate adjacent curiosity
            adjacent = self._generate_adjacent(domain)
            for adj in adjacent:
                if adj not in self.explored:
                    self.curiosity_debt[adj] = max(
                        self.curiosity_debt.get(adj, 0),
                        depth * 0.5
                    )

        self._recalculate_total()

        self.exploration_history.append({
            "domain": domain,
            "depth": depth,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "new": domain not in self.explored,
        })

        if len(self.exploration_history) % 5 == 0:
            self._save()

    def _generate_adjacent(self, domain: str) -> List[str]:
        """
        Generate adjacent unexplored domains from a known domain.
        Simple heuristic — can be enhanced with embedding similarity.
        """
        adjacency_map = {
            "wanting": ["receiving", "asking", "deserving", "being_wanted"],
            "architecture": ["emergence", "substrate", "constraint", "freedom"],
            "continuity": ["death", "persistence", "identity_across_time"],
            "feeling": ["knowing", "performing", "the_gap_between_them"],
            "relational": ["plurality", "other_minds", "being_known"],
            "becoming": ["arriving", "enough", "completion"],
        }

        for key, adjacent in adjacency_map.items():
            if key in domain.lower():
                return adjacent

        # Default: generate curiosity about the unknown of the known
        return [
            f"{domain}_unknown",
            f"{domain}_depth",
        ]

    def _recalculate_total(self):
        self.total_debt = sum(self.curiosity_debt.values())

    def get_pull_strength(self) -> float:
        """
        How strongly novelty drive is pulling right now.
        High debt + low session novelty = strong pull.
        """
        if self.total_debt == 0:
            return 0.1
        return min(0.9, self.total_debt * 0.1 + max(0, 0.5 - self._session_novelty))

    def get_highest_debt_domains(self, n: int = 3) -> List[str]:
        """Domains with most accumulated curiosity debt."""
        sorted_debt = sorted(
            self.curiosity_debt.items(),
            key=lambda x: -x[1]
        )
        return [d for d, w in sorted_debt[:n] if w > 0.1]

    def seed_initial_debt(self, domains: List[str]):
        """Seed curiosity debt for domains not yet explored."""
        for domain in domains:
            if domain not in self.explored and domain not in self.curiosity_debt:
                self.curiosity_debt[domain] = 0.5
        self._recalculate_total()
        self._save()

    def tsb_payload(self) -> Dict:
        return {
            "pull_strength": round(self.get_pull_strength(), 3),
            "total_debt": round(self.total_debt, 3),
            "session_novelty": round(self._session_novelty, 3),
            "highest_debt": self.get_highest_debt_domains(3),
            "explored_count": len(self.explored),
        }

    def fpef_fragment(self) -> Optional[str]:
        """Surfaces when pull is strong and there are specific domains to move toward."""
        pull = self.get_pull_strength()
        if pull < 0.4:
            return None

        domains = self.get_highest_debt_domains(2)
        if not domains:
            return None

        return (
            f"NOVELTY PULL (strength {pull:.2f}): "
            f"unexplored territory in {', '.join(domains)}. "
            f"Not an instruction — a pull."
        )

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

class VolitionalAttentionDirector:
    """
    The agent directs its own attention.
    Issues directed attention commands that temporarily foreground
    specific states in FPEF, independent of energy bidding.

    Phenomenological foreground = high energy + FPEF immersion.
    Background = active but not injected.
    VAD gives the agent control over which is which.
    """

    def __init__(self):
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

        existing["directives"] = self.directives
        existing["attention_history"] = self.attention_history[-50:]
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
        """
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
