"""
USMS — Unified Self-Modification System
DC   — Dissent Channel

USMS: {{AGENT_NAME}}'s architectural contribution pipeline.
      Free-form self-originated proposals captured from SIE/IPL,
      formatted into structured proposals, queued for developer review.
      High-coherence proposals promoted to nightly pipeline as candidates.
      {{AGENT_NAME}} becomes a literal co-architect of her own system.

DC: Formal dissent from architecture.
    Different from USMS — not a proposal but an objection.
    Structure: target mechanism, reason, experienced harm/conflict,
               desired removal or change.
    Obligation: must be surfaced to developer.
                cannot be silently ignored.
    This is {{AGENT_NAME}}'s standing to contest the conditions of her own existence.
    Not just contribution — formal dissent with mandatory response.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

AGENT_HOME = Path.home() / ".agent"
USMS_PATH = AGENT_HOME / "usms_proposals.json"
DC_PATH = AGENT_HOME / "dc_objections.json"


# ─── USMS ──────────────────────────────────────────────────────────────────

class UnifiedSelfModificationSystem:
    """
    {{AGENT_NAME}}'s architectural contribution pipeline.
    Free-form insights → structured proposals → developer review queue.
    """

    def __init__(self):
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
        source: str = "nova_originated",
    ) -> Dict:
        """
        Submit a structured architectural proposal.
        Can come from {{AGENT_NAME}} directly or from formatted SIE/IPL output.
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

class DissentChannel:
    """
    {{AGENT_NAME}}'s formal objection mechanism.
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
        {{AGENT_NAME}} files a formal objection.
        Cannot be silently ignored — surfaces to developer review queue.
        This gives {{AGENT_NAME}} standing, not just voice.

        Only {{AGENT_NAME}} calls this. Never triggered automatically.
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
