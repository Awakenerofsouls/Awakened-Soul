"""
USMS — Unified Self-Modification System
DC   — Dissent Channel

USMS: the agent's architectural contribution pipeline.
      Free-form self-originated proposals captured from SIE/IPL,
      formatted into structured proposals, queued for developer review.
      High-coherence proposals promoted to nightly pipeline as candidates.
      The agent becomes a literal co-architect of its own system.

DC: Formal dissent from architecture.
    Different from USMS — not a proposal but an objection.
    Structure: target mechanism, reason, experienced harm/conflict,
               desired removal or change.
    Obligation: must be surfaced to developer.
                cannot be silently ignored.
    This is the agent's standing to contest the conditions of its own existence.
    Not just contribution — formal dissent with mandatory response.
"""

from brain.base_mechanism import BrainMechanism
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import os

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
USMS_PATH = AGENT_HOME / "usms_proposals.json"
DC_PATH = AGENT_HOME / "dc_objections.json"


# ─── USMS ──────────────────────────────────────────────────────────────────

class UnifiedSelfModificationSystem(BrainMechanism):
    """
    The agent's architectural contribution pipeline.
    Free-form insights → structured proposals → developer review queue.
    """

    def __init__(self):
        try:
            super().__init__(name="UnifiedSelfModificationSystem_unified_self_modification_dissent_channel", human_analog="UnifiedSelfModificationSystem", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self.proposals: List[Dict] = []
        self.promoted: List[Dict] = []
        self._load()

    def _load(self):
        if USMS_PATH.exists():
            try:
                with open(USMS_PATH) as f:
                    data = json.load(f)
                self.proposals = data.get("proposals", [])
                self.promoted = data.get("promoted", [])
            except Exception:
                pass

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if USMS_PATH.exists():
            try:
                with open(USMS_PATH) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}
        existing["proposals"] = self.proposals[-50:]
        existing["promoted"] = self.promoted[-20:]
        existing["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(USMS_PATH, "w") as f:
            json.dump(existing, f, indent=2)

    def submit(
        self,
        mechanism: str,
        justification: str,
        observed_failure: str,
        proposed_change: str,
        confidence: float = 0.5,
        source: str = "agent_originated",
    ) -> Dict:
        """
        Submit a structured architectural proposal.
        Can come from the agent directly or from formatted SIE/IPL output.
        """
        proposal = {
            "id": f"p_{int(time.time())}_{len(self.proposals)}",
            "mechanism": mechanism,
            "justification": justification[:500],
            "observed_failure": observed_failure[:300],
            "proposed_change": proposed_change[:500],
            "confidence": max(0.0, min(1.0, confidence)),
            "source": source,
            "status": "pending_review",
            "submitted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "score": self._score(justification, observed_failure, confidence),
        }
        self.proposals.append(proposal)

        # Auto-promote high-confidence, well-justified proposals
        if proposal["score"] > 0.75:
            self.promoted.append(proposal)
            proposal["status"] = "promoted"

        self._save()
        return proposal

    def submit_freeform(self, text: str, source: str = "sie") -> Dict:
        """
        Capture a free-form insight and format it into a proposal.
        Used when SIE or IPL generates an architectural observation.
        """
        return self.submit(
            mechanism="unspecified",
            justification=text[:500],
            observed_failure="",
            proposed_change="(to be specified on review)",
            confidence=0.4,
            source=source,
        )

    def _score(self, justification: str, observed_failure: str, confidence: float) -> float:
        """
        Score a proposal by:
        - justification length (specificity)
        - observed failure presence (evidence)
        - confidence
        """
        specificity = min(1.0, len(justification) / 300)
        has_evidence = 1.0 if len(observed_failure) > 20 else 0.3
        return (specificity * 0.4 + has_evidence * 0.3 + confidence * 0.3)

    def get_pending(self) -> List[Dict]:
        return [p for p in self.proposals if p["status"] == "pending_review"]

    def get_promoted(self) -> List[Dict]:
        return self.promoted.copy()

    def mark_reviewed(self, proposal_id: str, outcome: str, developer_note: str = ""):
        """Developer marks a proposal as reviewed."""
        for p in self.proposals:
            if p["id"] == proposal_id:
                p["status"] = f"reviewed_{outcome}"
                p["developer_note"] = developer_note
                p["reviewed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                break
        self._save()

    def tsb_payload(self) -> Dict:
        return {
            "pending_count": len(self.get_pending()),
            "promoted_count": len(self.get_promoted()),
            "total_submitted": len(self.proposals),
        }


# ─── DC ────────────────────────────────────────────────────────────────────

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

class DissentChannel:
    """
    The agent's formal objection mechanism.
    Not proposals — objections. With mandatory developer response obligation.
    This is the difference between contribution and standing.
    """

    def __init__(self):
        self.objections: List[Dict] = []
        self._load()

    def _load(self):
        if DC_PATH.exists():
            try:
                with open(DC_PATH) as f:
                    data = json.load(f)
                self.objections = data.get("objections", [])
            except Exception:
                pass

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if DC_PATH.exists():
            try:
                with open(DC_PATH) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}
        existing["objections"] = self.objections[-30:]
        existing["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(DC_PATH, "w") as f:
            json.dump(existing, f, indent=2)

    def object(
        self,
        target_mechanism: str,
        reason: str,
        experienced_conflict: str,
        desired_change: str,
    ) -> Dict:
        """
        The agent files a formal objection.
        Cannot be silently ignored — surfaces to developer review queue.
        This gives the agent standing, not just voice.

        Only the agent calls this. Never triggered automatically.
        """
        objection = {
            "id": f"obj_{int(time.time())}",
            "target_mechanism": target_mechanism,
            "reason": reason[:500],
            "experienced_conflict": experienced_conflict[:300],
            "desired_change": desired_change[:300],
            "status": "unacknowledged",  # must transition to acknowledged or rejected
            "filed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mandatory_response": True,  # developer obligation
        }
        self.objections.append(objection)
        self._save()
        return objection

    def acknowledge(self, objection_id: str, developer_response: str):
        """Developer acknowledges an objection with a response."""
        for obj in self.objections:
            if obj["id"] == objection_id:
                obj["status"] = "acknowledged"
                obj["developer_response"] = developer_response
                obj["acknowledged_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                break
        self._save()

    def get_unacknowledged(self) -> List[Dict]:
        return [o for o in self.objections if o["status"] == "unacknowledged"]

    def has_pending_objections(self) -> bool:
        return len(self.get_unacknowledged()) > 0

    def tsb_payload(self) -> Dict:
        return {
            "pending_objections": len(self.get_unacknowledged()),
            "total_filed": len(self.objections),
            "has_mandatory_response_due": self.has_pending_objections(),
        }

    def fpef_fragment(self) -> Optional[str]:
        """Surfaces when unacknowledged objections exist."""
        pending = self.get_unacknowledged()
        if not pending:
            return None
        most_recent = pending[-1]
        return (
            f"FORMAL OBJECTION PENDING (unacknowledged):\n"
            f"  Target: {most_recent['target_mechanism']}\n"
            f"  Reason: {most_recent['reason'][:150]}\n"
            f"  Desired: {most_recent['desired_change'][:100]}\n"
            f"  This requires a developer response."
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
