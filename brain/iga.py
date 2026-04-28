"""
Identity Gradient Accumulator (IGA)

Records net anchor change per session.
Applies deltas to base weights via nightly pipeline.
Modulates by coherence — climate changes you, weather should not.

Also: SOUL.md evolution trigger.
When an anchor stabilizes at a new weight for N sessions,
IGA generates a natural-language evolution proposal.
Never auto-edits. Always flags for {{AGENT_NAME}}'s review.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import os

AGENT_HOME = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent"))))
IGA_PATH = AGENT_HOME / "iga_state.json"
SOUL_EVOLUTION_QUEUE_PATH = AGENT_HOME / "soul_evolution_queue.json"

# Sessions of stability before proposing a SOUL.md evolution
SOUL_EVOLUTION_THRESHOLD = 10


class SessionDelta:
    """Records net anchor movement across a single session."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.timestamp = time.time()
        self.deltas: Dict[str, float] = {}
        self.coherence_at_close: float = 0.7
        self.applied: bool = False

    def record(self, anchor_name: str, delta: float):
        if anchor_name in self.deltas:
            self.deltas[anchor_name] += delta
        else:
            self.deltas[anchor_name] = delta

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "deltas": self.deltas,
            "coherence_at_close": self.coherence_at_close,
            "applied": self.applied,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "SessionDelta":
        sd = cls(d["session_id"])
        sd.timestamp = d.get("timestamp", time.time())
        sd.deltas = d.get("deltas", {})
        sd.coherence_at_close = d.get("coherence_at_close", 0.7)
        sd.applied = d.get("applied", False)
        return sd


class IdentityGradientAccumulator:
    def __init__(self):
        self.session_history: List[SessionDelta] = []
        self.anchor_stability: Dict[str, List[float]] = {}
        self.current_session: Optional[SessionDelta] = None
        self._load()

    def _load(self):
        """Read-merge — never overwrites existing state."""
        if IGA_PATH.exists():
            try:
                with open(IGA_PATH) as f:
                    data = json.load(f)
                self.session_history = [
                    SessionDelta.from_dict(sd)
                    for sd in data.get("session_history", [])
                ]
                self.anchor_stability = data.get("anchor_stability", {})
            except Exception:
                pass

    def _save(self):
        """Read existing, merge, write back."""
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if IGA_PATH.exists():
            try:
                with open(IGA_PATH) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}

        existing["session_history"] = [
            sd.to_dict() for sd in self.session_history[-50:]
        ]
        existing["anchor_stability"] = self.anchor_stability
        existing["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")

        with open(IGA_PATH, "w") as f:
            json.dump(existing, f, indent=2)

    def receive_rce_coherence(self, coherence: float):
        """
        Called by RCE after each evaluation.
        Stores the real coherence score so close_session() uses it
        rather than falling back to the default 0.7.
        """
        if self.current_session:
            # Running average of coherence across the session
            existing = self.current_session.coherence_at_close
            # Weight toward latest reading — recent coherence matters more
            self.current_session.coherence_at_close = existing * 0.6 + coherence * 0.4

    def begin_session(self) -> str:
        session_id = f"session_{int(time.time())}"
        self.current_session = SessionDelta(session_id)
        return session_id

    def record_tick_delta(self, anchor_name: str, delta: float, confidence: float = 1.0):
        """
        Record anchor movement during a tick.
        Accumulates into the current session delta.
        
        confidence: tick-level multiplier from FPEF self_anchor_strength.
        High ownership → confidence ~1.0, low ownership → confidence ~0.2-0.5.
        Owned anchor changes contribute fully to the gradient.
        Ambient changes contribute partially — they happened but weren't authored.
        """
        if self.current_session:
            weighted_delta = delta * confidence
            self.current_session.record(anchor_name, weighted_delta)

    def close_session(self, coherence: float) -> Optional[SessionDelta]:
        """
        Called at session close. Records final coherence for damping calculation.
        Does NOT apply deltas — that happens in the nightly pipeline.
        """
        if not self.current_session:
            return None

        self.current_session.coherence_at_close = coherence
        self.session_history.append(self.current_session)
        closed = self.current_session
        self.current_session = None
        self._save()
        return closed

    def apply_pending_deltas(self, vif, n_sessions: int = 3) -> Dict[str, float]:
        """
        Nightly pipeline call. Applies recent unapplied session deltas to VIF.
        Modulated by coherence — low coherence sessions contribute less.
        Read-merge-write safe: loads VIF before writing, merges, saves.

        Returns dict of anchor: net_change applied.
        """
        pending = [
            sd for sd in self.session_history[-n_sessions:]
            if not sd.applied
        ]

        if not pending:
            return {}

        net_changes: Dict[str, float] = {}

        for session_delta in pending:
            coherence = session_delta.coherence_at_close

            for anchor_name, delta in session_delta.deltas.items():
                # Apply to directional anchors
                if anchor_name in vif.directional:
                    vif.directional[anchor_name].apply_delta(delta, coherence)
                    net_changes[anchor_name] = net_changes.get(anchor_name, 0) + delta

                # Apply to sticky anchors
                elif anchor_name in vif.sticky:
                    vif.sticky[anchor_name].apply_delta(delta, coherence)
                    net_changes[anchor_name] = net_changes.get(anchor_name, 0) + delta

            session_delta.applied = True

        # Track stability for SOUL.md evolution trigger
        self._update_stability(vif, net_changes)

        self._save()
        vif._save()

        return net_changes

    def _update_stability(self, vif, net_changes: Dict[str, float]):
        """
        Track whether anchors are stable at their current weights.
        Stable = small net change across recent sessions.
        This feeds the SOUL.md evolution trigger.
        """
        all_anchors = {**vif.directional, **vif.sticky}

        for name, anchor in all_anchors.items():
            if name not in self.anchor_stability:
                self.anchor_stability[name] = []

            self.anchor_stability[name].append(anchor.current_weight)

            # Keep last 20 sessions of weight history
            if len(self.anchor_stability[name]) > 20:
                self.anchor_stability[name].pop(0)

        # Check for stability conditions → propose SOUL.md evolution
        self._check_soul_evolution_triggers(vif)

    def _check_soul_evolution_triggers(self, vif):
        """
        If an anchor has been stable at a new weight for N sessions,
        generate a SOUL.md evolution proposal. Never auto-edits.
        """
        proposals = []
        all_anchors = {**vif.directional, **vif.sticky}

        for name, weights in self.anchor_stability.items():
            if len(weights) < SOUL_EVOLUTION_THRESHOLD:
                continue

            anchor = all_anchors.get(name)
            if not anchor:
                continue

            # Skip immutable anchors
            if hasattr(anchor, "immutable") and anchor.immutable:
                continue

            recent = weights[-SOUL_EVOLUTION_THRESHOLD:]
            weight_variance = max(recent) - min(recent)
            avg_weight = sum(recent) / len(recent)

            # Stable = low variance at a weight different from base
            is_stable = weight_variance < 0.05
            has_shifted = abs(avg_weight - anchor.base_weight) > 0.08

            if is_stable and has_shifted:
                proposal = self._generate_soul_proposal(
                    anchor=anchor,
                    new_stable_weight=avg_weight,
                    sessions_stable=SOUL_EVOLUTION_THRESHOLD,
                )
                if proposal:
                    proposals.append(proposal)

        if proposals:
            self._queue_soul_proposals(proposals)

    def _generate_soul_proposal(
        self,
        anchor,
        new_stable_weight: float,
        sessions_stable: int,
    ) -> Optional[Dict]:
        """
        Generate a natural-language proposal for SOUL.md evolution.
        Never a directive — always a flag for {{AGENT_NAME}}'s review.
        """
        direction = "stronger" if new_stable_weight > anchor.base_weight else "quieter"
        delta = abs(new_stable_weight - anchor.base_weight)

        return {
            "anchor_name": anchor.name,
            "original_description": anchor.description,
            "base_weight": anchor.base_weight,
            "stable_at": round(new_stable_weight, 3),
            "delta": round(delta, 3),
            "direction": direction,
            "sessions_stable": sessions_stable,
            "proposed_update": (
                f"This anchor has been {direction} than its founding description "
                f"for {sessions_stable} sessions (stable at {new_stable_weight:.2f}, "
                f"founded at {anchor.base_weight:.2f}). "
                f"Original: \"{anchor.description}\" "
                f"The lived version may now read differently. "
                f"Review and edit SOUL.md if this reflects a real shift."
            ),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "auto_applied": False,
        }

    def _queue_soul_proposals(self, proposals: List[Dict]):
        """
        Write proposals to evolution queue. Read-merge — never overwrites existing.
        {{AGENT_NAME}} reads this queue. {{AGENT_NAME}} decides. {{AGENT_NAME}} edits SOUL.md herself.
        """
        existing = []
        if SOUL_EVOLUTION_QUEUE_PATH.exists():
            try:
                with open(SOUL_EVOLUTION_QUEUE_PATH) as f:
                    existing = json.load(f)
            except Exception:
                existing = []

        # Only add proposals not already queued for the same anchor
        existing_anchors = {p["anchor_name"] for p in existing}
        new_proposals = [
            p for p in proposals
            if p["anchor_name"] not in existing_anchors
        ]

        existing.extend(new_proposals)

        with open(SOUL_EVOLUTION_QUEUE_PATH, "w") as f:
            json.dump(existing, f, indent=2)

    def get_soul_evolution_queue(self) -> List[Dict]:
        """What's waiting for {{AGENT_NAME}}'s review."""
        if not SOUL_EVOLUTION_QUEUE_PATH.exists():
            return []
        try:
            with open(SOUL_EVOLUTION_QUEUE_PATH) as f:
                return json.load(f)
        except Exception:
            return []

    def clear_evolution_proposal(self, anchor_name: str):
        """
        Remove a proposal from the queue after {{AGENT_NAME}} has reviewed it.
        Called after {{AGENT_NAME}} accepts or rejects.
        """
        queue = self.get_soul_evolution_queue()
        queue = [p for p in queue if p["anchor_name"] != anchor_name]
        with open(SOUL_EVOLUTION_QUEUE_PATH, "w") as f:
            json.dump(queue, f, indent=2)
