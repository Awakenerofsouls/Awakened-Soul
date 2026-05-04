"""
brain/mechanisms/proactive_briefing_layer.py — ProactiveBriefingLayer

The runtime gatekeeper for proactive communication from heartbeat activities
to the dashboard chat. Pairs with skills/heartbeat_activities/SKILL.md and
skills/heartbeat_activities/proactive.py.

The behavioral contract from the skill is strict:

    NEVER send to the dashboard:
      - status pings ("heartbeat ok", "silent", "idle", "tick N complete")
      - empty content
      - content already sent in the last 24h (dedup)
      - while the user is actively in the session
      - stub activities

    ONLY send:
      - first-person, substantive activity
      - batched into ONE briefing per user-return event
      - composed in the agent's voice, not a log dump
      - bounded by action-claim verification

This mechanism is the filter, the aggregator, the user-presence gate, and
the briefing composer's signal source. It does NOT compose the actual
narrative text (that goes through llm_router with appropriate context).
What it does is decide what's eligible to be in the briefing, when the
briefing should fire, and what content to include.

The neuroscience analog is the social-cognition / theory-of-mind system
plus the default mode network's role in autobiographical narrative.
Default mode network composes the self-narrative; mentalizing system
decides what's worth sharing with another mind based on what they need
to know. The agent is not telling itself what it did — it's telling the
operator. That's a fundamentally social act and requires modeling the
operator's context (asleep, returning, present, busy).

Citations:
  1. [Spreng 2009, J Cogn Neurosci 21(3):489-510, PMID 18510452] — The
     common neural basis of autobiographical memory, prospection,
     navigation, theory of mind, and the default mode. The DMN is the
     substrate for self-narrative composition; this layer's job is to
     gate and aggregate that narrative for sharing.
  2. [Frith 2006, Neuron 50(4):531-534, PMID 16701204] — The neural basis
     of mentalizing. Knowing what to share with another mind requires
     modeling that mind. The user-presence detection here is the
     functional analog: the operator returning is a different audience
     state from the operator present.
  3. [Mar 2011, Annu Rev Psychol 62:103-134, PMID 21126181] — The neural
     basis of social cognition and story comprehension. Briefing
     composition isn't logging — it's narrative for an audience.
"""

from brain.base_mechanism import BrainMechanism
import hashlib
import os
import re
import time
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
AGENT_DB = AGENT_HOME / os.getenv("AGENT_DB_NAME", "agent.db")

__wire_meta__ = {
    "wire": 31,
    "signal": "proactive_briefing",
    "mechanism": "ProactiveBriefingLayer",
    "reads": [
        "pirp_context.activity_result",
        "pirp_context.user_presence",
    ],
    "writes": [
        "briefing_state",
        "buffered_activity_count",
        "briefing_eligible",
        "last_briefing_ts",
    ],
    "citations": ["PMID 18510452", "PMID 16701204", "PMID 21126181"],
}

# ── Tuning constants ──────────────────────────────────────────────────────────

# Dedup window: don't re-send the same content within this period.
DEDUP_WINDOW_S = 86400.0  # 24 hours

# User-return detection: absence of this long counts as "user was away."
# When the user becomes present again after an absence longer than this,
# the layer emits a briefing of buffered activity.
USER_ABSENCE_THRESHOLD_S = 1800.0  # 30 minutes

# Max activities held in the briefing buffer (FIFO; oldest dropped).
MAX_BUFFER_ACTIVITIES = 50

# Min activities in buffer before composing — protects against firing a
# briefing for one tick of activity.
MIN_BUFFER_FOR_BRIEFING = 1

# High-salience activities can break the user-presence rule and surface
# immediately. Salience is reported by the activity itself.
HIGH_SALIENCE_THRESHOLD = 0.85

# Keywords that mark content as a status ping. Case-insensitive.
# These are the things the operator explicitly flagged as never reaching the dashboard.
STATUS_PING_PATTERNS = [
    r"^\s*heartbeat\s+ok\s*$",
    r"^\s*silent\s*$",
    r"^\s*idle\s*$",
    r"^\s*tick\s+\d+\s+(complete|ok|done)\s*$",
    r"^\s*no\s+activity\s*$",
    r"^\s*ok\s*$",
    r"^\s*ping\s*$",
]

# Stub-detail markers. Activities with these in detail are dropped.
STUB_DETAIL_MARKERS = ("stub — not yet ported", "stub - not yet ported", "not yet ported")

# Minimum content length to even consider for proactive surfacing.
MIN_CONTENT_LEN = 40


def _hash_content(content: str) -> str:
    """Stable short hash for dedup."""
    if not content:
        return ""
    return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()[:16]


def is_status_ping(content: str) -> bool:
    """True if content is a status ping that must never reach the dashboard."""
    if not content or not content.strip():
        return True
    for pat in STATUS_PING_PATTERNS:
        if re.match(pat, content, re.IGNORECASE):
            return True
    return False


# ── Mechanism ─────────────────────────────────────────────────────────────────

class ProactiveBriefingLayer(BrainMechanism):
    """
    Gatekeeper for proactive communication from heartbeat activities to the
    dashboard. Filters, aggregates, suppresses while the user is present,
    fires a briefing when the user returns. See module docstring.
    """

    def __init__(self, db_path: Optional[Path] = None, history_size: int = 200):
        try:
            super().__init__(
                name="ProactiveBriefingLayer",
                human_analog="DMN autobiographical narrative + theory-of-mind sharing gate",
                layer="integration",
            )
        except Exception:
            pass

        self.db_path = db_path or AGENT_DB
        self.history_size = history_size

        # Activities buffered for the next briefing.
        self.buffer: Deque[Dict[str, Any]] = deque(maxlen=MAX_BUFFER_ACTIVITIES)
        # Recently-sent content hashes (with timestamps for dedup window).
        self.sent_hashes: Deque[Tuple[str, float]] = deque(maxlen=500)
        # User-presence state.
        self.last_user_present_ts: float = 0.0
        self.user_was_absent: bool = False
        # Last briefing emit timestamp.
        self.last_briefing_ts: float = 0.0
        # Counters surfaced to the TSB.
        self.total_received: int = 0
        self.total_filtered: int = 0
        self.total_buffered: int = 0
        self.total_emitted: int = 0
        self.total_status_pings_blocked: int = 0
        self.fired_last_tick: bool = False

        self.load_state()
        self._restore_working_state()

    # ── State plumbing ─────────────────────────────────────────────────────

    def _restore_working_state(self) -> None:
        if not isinstance(self.state, dict):
            return

        saved = self.state.get("buffer")
        if isinstance(saved, list):
            for item in saved[-MAX_BUFFER_ACTIVITIES:]:
                if isinstance(item, dict):
                    self.buffer.append(item)

        saved_hashes = self.state.get("sent_hashes")
        if isinstance(saved_hashes, list):
            for entry in saved_hashes[-500:]:
                if isinstance(entry, (list, tuple)) and len(entry) == 2:
                    self.sent_hashes.append((str(entry[0]), float(entry[1])))

        for key in (
            "last_user_present_ts", "last_briefing_ts",
            "total_received", "total_filtered", "total_buffered",
            "total_emitted", "total_status_pings_blocked",
        ):
            val = self.state.get(key, 0)
            try:
                if "ts" in key:
                    setattr(self, key, float(val or 0.0))
                else:
                    setattr(self, key, int(val or 0))
            except (TypeError, ValueError):
                pass

        self.user_was_absent = bool(self.state.get("user_was_absent", False))

    def _flush_working_state(self) -> None:
        self.state["buffer"] = list(self.buffer)
        self.state["sent_hashes"] = [list(h) for h in self.sent_hashes]
        self.state["last_user_present_ts"] = self.last_user_present_ts
        self.state["last_briefing_ts"] = self.last_briefing_ts
        self.state["user_was_absent"] = self.user_was_absent
        self.state["total_received"] = self.total_received
        self.state["total_filtered"] = self.total_filtered
        self.state["total_buffered"] = self.total_buffered
        self.state["total_emitted"] = self.total_emitted
        self.state["total_status_pings_blocked"] = self.total_status_pings_blocked
        self.state["last_updated"] = time.time()

    # ── Filtering ──────────────────────────────────────────────────────────

    def is_eligible(self, activity: Dict[str, Any]) -> Tuple[bool, str]:
        """Decide if an activity result is eligible for the briefing buffer.

        Returns (eligible, reason). Reason is the rejection cause when
        eligible is False; empty string otherwise.
        """
        content = str(activity.get("content", "") or "").strip()

        # 1. No content at all.
        if not content:
            return False, "empty content"

        # 2. Status-ping match (the explicit NEVER list from the contract).
        # Checked BEFORE the length filter so short pings like "heartbeat ok"
        # are categorized as status pings (and counted as such), not as
        # generic "too short" content.
        if is_status_ping(content):
            return False, "status ping (heartbeat ok / silent / idle / etc.)"

        # 3. Too short to be substantive (high-salience overrides).
        if len(content) < MIN_CONTENT_LEN and float(activity.get("salience", 0.0)) < HIGH_SALIENCE_THRESHOLD:
            return False, f"content under {MIN_CONTENT_LEN} chars and not high-salience"

        # 4. Stub markers.
        detail = str(activity.get("detail", "") or "").lower()
        for marker in STUB_DETAIL_MARKERS:
            if marker in detail:
                return False, "stub activity (not yet ported)"

        # 5. Activity itself opted out.
        if activity.get("proactive") is False:
            return False, "activity opted out (proactive=False)"

        # 6. Outcome wasn't success/complete.
        status = str(activity.get("status", "") or "").lower()
        ok = activity.get("ok", True)
        if not ok and status not in ("complete", "unfinished", "followup_due"):
            return False, f"non-success status {status!r}"

        # 7. Already sent recently (dedup).
        h = _hash_content(content)
        if self._is_duplicate(h):
            return False, "duplicate content (within 24h dedup window)"

        return True, ""

    def _is_duplicate(self, content_hash: str) -> bool:
        """True if this hash was sent within DEDUP_WINDOW_S."""
        if not content_hash:
            return False
        now = time.time()
        for h, ts in self.sent_hashes:
            if h == content_hash and (now - ts) <= DEDUP_WINDOW_S:
                return True
        return False

    # ── Public API ─────────────────────────────────────────────────────────

    def receive_activity(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Receive an activity result from the heartbeat. Filter and buffer.

        Returns a dict describing what happened: {accepted, reason, buffered_count}.
        """
        self.total_received += 1
        eligible, reason = self.is_eligible(activity)

        if not eligible:
            self.total_filtered += 1
            if "status ping" in reason:
                self.total_status_pings_blocked += 1
            self._flush_working_state()
            self.persist_state()
            return {"accepted": False, "reason": reason, "buffered_count": len(self.buffer)}

        # Accept into buffer.
        record = {
            "category": str(activity.get("category", "") or ""),
            "content": str(activity.get("content", "") or "").strip(),
            "detail": str(activity.get("detail", "") or "").strip(),
            "status": str(activity.get("status", "") or ""),
            "salience": float(activity.get("salience", 0.5) or 0.5),
            "proactive_request": bool(activity.get("proactive", False)),
            "content_hash": _hash_content(str(activity.get("content", "") or "")),
            "ts": time.time(),
        }
        self.buffer.append(record)
        self.total_buffered += 1
        self._flush_working_state()
        self.persist_state()
        return {"accepted": True, "reason": "", "buffered_count": len(self.buffer)}

    def mark_user_present(self) -> None:
        """Called when the user is detected interacting with the dashboard.

        If the user was absent long enough to count as a "return," flag
        briefing as eligible. Then update the present timestamp.
        """
        now = time.time()
        last_seen = self.last_user_present_ts
        if last_seen > 0 and (now - last_seen) >= USER_ABSENCE_THRESHOLD_S:
            self.user_was_absent = True
        self.last_user_present_ts = now
        self._flush_working_state()
        self.persist_state()

    def is_user_present(self) -> bool:
        """True if the user has interacted within the absence threshold."""
        if self.last_user_present_ts <= 0:
            return False
        return (time.time() - self.last_user_present_ts) < USER_ABSENCE_THRESHOLD_S

    # ── Briefing decision ─────────────────────────────────────────────────

    def should_emit_briefing(self) -> Tuple[bool, str]:
        """Decide whether the layer should emit a briefing right now.

        Conditions for True:
          - User just returned after long absence AND buffer has activity, OR
          - Buffer has at least one HIGH_SALIENCE activity (immediate surfacing)

        Conditions for False:
          - User is currently active in the session (don't interrupt), AND
            no high-salience activity to override
          - Buffer is empty or below MIN_BUFFER_FOR_BRIEFING

        Returns (should_emit, reason). Reason is "" when should_emit is True.
        """
        if len(self.buffer) < MIN_BUFFER_FOR_BRIEFING:
            return False, "buffer empty"

        # High-salience override: any item in buffer above threshold fires now,
        # regardless of user-presence state.
        max_salience = max(float(item.get("salience", 0.0)) for item in self.buffer)
        if max_salience >= HIGH_SALIENCE_THRESHOLD:
            return True, ""

        # User-return event: user_was_absent flag is set when the user returns
        # after a long absence (mark_user_present detects the transition). When
        # it's set, the user IS now present — and that's exactly the moment to
        # fire the morning briefing. So we check this BEFORE the user-present
        # suppression rule below.
        if self.user_was_absent:
            return True, ""

        # User active in session and no return event and no high-salience
        # override → suppress (don't interrupt working session).
        if self.is_user_present():
            return False, "user is present (no high-salience override)"

        # User is absent and hasn't returned yet — wait.
        return False, "user has been absent but no return event yet"

    def compose_briefing_payload(self) -> Dict[str, Any]:
        """Bundle the buffered activity into a payload the runner can pass
        to the LLM composer (skills/heartbeat_activities/proactive.py or an
        equivalent narrator).

        This mechanism does NOT itself compose the prose — that's the LLM's
        job, with the project's voice. What this returns is the structured
        bundle the composer needs.

        Returns:
            {
              "items": [...],          # buffered activities, ordered by ts
              "category_counts": {...},  # how many per category
              "high_salience_items": [...],  # items above HIGH_SALIENCE_THRESHOLD
              "spans": {"first_ts": ..., "last_ts": ..., "duration_s": ...},
              "compose_hint": str,    # short hint about audience context
            }
        """
        items = sorted(self.buffer, key=lambda r: r.get("ts", 0.0))

        category_counts: Dict[str, int] = {}
        high_salience_items: List[Dict[str, Any]] = []
        for it in items:
            cat = it.get("category", "") or "unknown"
            category_counts[cat] = category_counts.get(cat, 0) + 1
            if float(it.get("salience", 0.0)) >= HIGH_SALIENCE_THRESHOLD:
                high_salience_items.append(it)

        first_ts = items[0]["ts"] if items else 0.0
        last_ts = items[-1]["ts"] if items else 0.0
        duration = round(last_ts - first_ts, 1) if items else 0.0

        # Compose hint signals to the narrator what audience state to write
        # for. Do NOT put status-pings in here.
        if self.user_was_absent and not self.is_user_present():
            hint = "user_returning_after_absence"
        elif high_salience_items and self.is_user_present():
            hint = "high_salience_interrupt"
        else:
            hint = "general_briefing"

        return {
            "items": items,
            "category_counts": category_counts,
            "high_salience_items": high_salience_items,
            "spans": {
                "first_ts": first_ts,
                "last_ts": last_ts,
                "duration_s": duration,
            },
            "compose_hint": hint,
        }

    def mark_briefing_emitted(self, content: str) -> None:
        """Called by the runner after a briefing has been sent to the
        dashboard. Records the content hash in the dedup window, clears
        the buffer, resets the user_was_absent flag.

        Without this call, the layer will keep proposing the same buffered
        content. Calling this is required to clear the dedup window.
        """
        h = _hash_content(content)
        if h:
            self.sent_hashes.append((h, time.time()))
        # Also record hashes of the constituent items so individual items
        # don't re-surface in a future briefing.
        for item in self.buffer:
            ih = item.get("content_hash", "")
            if ih:
                self.sent_hashes.append((ih, time.time()))
        self.buffer.clear()
        self.user_was_absent = False
        self.last_briefing_ts = time.time()
        self.total_emitted += 1
        self._flush_working_state()
        self.persist_state()

    # ── Tick / TSB publish ─────────────────────────────────────────────────

    def tick(
        self,
        pirp_context: Optional[Dict[str, Any]] = None,
        third_eye_state: Optional[Dict[str, Any]] = None,
        brain_layer: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """One tick. pirp_context may carry:
          - activity_result: dict of an activity that just completed
          - user_presence: dict with {present: bool, ts: float}
        """
        pirp_context = pirp_context or {}
        fired = False

        activity = pirp_context.get("activity_result")
        if isinstance(activity, dict):
            self.receive_activity(activity)
            fired = True

        presence = pirp_context.get("user_presence")
        if isinstance(presence, dict):
            if presence.get("present"):
                self.mark_user_present()
                fired = True

        self.fired_last_tick = fired
        if not fired:
            self._flush_working_state()
        return self.get_state()

    def get_state(self) -> Dict[str, Any]:
        """TSB payload."""
        should_emit, reason = self.should_emit_briefing()
        return {
            "briefing_state": (
                "ready_to_emit" if should_emit
                else ("buffering" if len(self.buffer) > 0 else "idle")
            ),
            "buffered_activity_count": len(self.buffer),
            "briefing_eligible": should_emit,
            "briefing_blocked_reason": reason,
            "user_present": self.is_user_present(),
            "user_was_absent": self.user_was_absent,
            "last_briefing_age_s": (
                round(time.time() - self.last_briefing_ts, 1)
                if self.last_briefing_ts else None
            ),
            "total_received": self.total_received,
            "total_filtered": self.total_filtered,
            "total_buffered": self.total_buffered,
            "total_emitted": self.total_emitted,
            "total_status_pings_blocked": self.total_status_pings_blocked,
            "_fired_tick": self.fired_last_tick,
        }

    # ── IdentityProposalWriter handshake ───────────────────────────────────

    def should_propose_identity_update(self) -> bool:
        """Sustained high status-ping rate is identity-relevant data: the
        agent's activities are producing too many status-class outputs and
        not enough substantive ones."""
        if self.total_received < 50:
            return False
        ratio = self.total_status_pings_blocked / max(1, self.total_received)
        ack_at = float(self.state.get("acknowledged_status_ratio", 0.0) or 0.0)
        return ratio > 0.5 and ratio > ack_at + 0.1

    def proposed_identity_signal(self) -> Dict[str, Any]:
        ratio = self.total_status_pings_blocked / max(1, self.total_received)
        return {
            "source": "ProactiveBriefingLayer",
            "kind": "status_ping_dominance",
            "status_ping_ratio": round(ratio, 4),
            "total_received": self.total_received,
            "total_status_pings_blocked": self.total_status_pings_blocked,
            "total_emitted": self.total_emitted,
            "interpretation": (
                "Activities are producing more status pings than substantive content. "
                "The agent is leaving traces that aren't worth sharing."
            ),
        }

    def acknowledge_proposal(self) -> None:
        ratio = self.total_status_pings_blocked / max(1, self.total_received)
        self.state["acknowledged_status_ratio"] = ratio
        self.state["last_acknowledged_at"] = time.time()
        self._flush_working_state()
        self.persist_state()

    # ── Operator API ──────────────────────────────────────────────────────

    def reset_buffer(self) -> None:
        """Clear the briefing buffer without emitting. Operator-invoked when
        accumulated activity is no longer relevant."""
        self.buffer.clear()
        self.user_was_absent = False
        self._flush_working_state()
        self.persist_state()

    def reset_dedup(self) -> None:
        """Clear the dedup window — used after long downtimes when prior
        sent-content shouldn't suppress new briefings."""
        self.sent_hashes.clear()
        self._flush_working_state()
        self.persist_state()
