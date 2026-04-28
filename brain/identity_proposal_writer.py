"""
brain/identity_proposal_writer.py — IdentityProposalWriter
Mind-Soul Fusion: third_eye → operator-reviewable identity proposals

When MeaningCompressor distills a high-confidence pattern about identity
(via Third Eye observation of brain_layer + identity_state), this writer
appends it to AGENT_HOME/identity/PROPOSALS.md — a queue the operator
reviews and ratifies. Ratified entries are then merged into SOUL.md /
IDENTITY.md / PERSONALITY.md by the operator.
"""
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

AGENT_HOME = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent"))))
PROPOSALS_PATH = AGENT_HOME / "identity" / "PROPOSALS.md"


class IdentityProposalWriter:
    """Appends third_eye-distilled identity-relevant patterns to PROPOSALS.md for operator review."""
    
    CONFIDENCE_THRESHOLD = 0.7
    
    def __init__(self, tsb=None):
        self.tsb = tsb
        PROPOSALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    def propose(
        self,
        target: str,           # one of: "soul", "identity", "personality"
        text: str,             # the proposed addition or refinement
        confidence: float,     # 0.0-1.0, written by MeaningCompressor
        source: str = "third_eye",
        rationale: str = "",
    ):
        """Write a proposal entry. Skipped if confidence below threshold."""
        if confidence < self.CONFIDENCE_THRESHOLD:
            return False
        if target not in ("soul", "identity", "personality"):
            return False
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        entry = (
            f"\n## Proposal — {target.upper()}.md — {ts}\n"
            f"**Source:** {source}  **Confidence:** {confidence:.2f}\n\n"
            f"{text.strip()}\n"
        )
        if rationale:
            entry += f"\n_Rationale:_ {rationale.strip()}\n"
        entry += "\n_Status: PENDING — operator review_\n\n---\n"
        try:
            with PROPOSALS_PATH.open("a", encoding="utf-8") as f:
                f.write(entry)
            return True
        except Exception:
            return False
    
    def tick(self):
        """Read recent third_eye TSB output, route any identity-flagged insights to proposals."""
        if self.tsb is None:
            return
        try:
            te_state, _fresh = self.tsb.read("third_eye")
        except Exception:
            return
        if not isinstance(te_state, dict):
            return
        # MeaningCompressor sets these keys when it produces an identity-relevant insight
        proposal = te_state.get("identity_proposal")
        if isinstance(proposal, dict):
            self.propose(
                target=proposal.get("target", "identity"),
                text=proposal.get("text", ""),
                confidence=float(proposal.get("confidence", 0.0)),
                source=proposal.get("source", "third_eye"),
                rationale=proposal.get("rationale", ""),
            )
