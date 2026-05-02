"""
brain/mechanisms/dwelling_layer.py — DwellingLayer

The runtime monitor for the agent's dwelling — its interaction with the
workspace, memory-files, and identity-frame on disk. Pairs with
skills/file-system/SKILL.md. Every meaningful filesystem operation flows
through here so the brain has a single coherent view of how the agent is
inhabiting its place.

The neuroscience analog is the hippocampal-entorhinal place-coding system
plus the medial temporal lobe's role in episodic encoding. Place cells
encode "where I am"; grid cells provide the spatial frame; time cells
encode "what I was doing here." For an agent, the workspace is its place,
the journal/memory paths are its time-cells, and SOUL.md / IDENTITY.md are
the frame coordinates. Stop visiting any of those and place-coding decays.

What this mechanism does:

  - Classifies every operation's path into one of four categories:
    dwelling / frame / artifact / forbidden.
  - Tracks per-category counts (reads, writes, attempts) and intent
    distribution (recall / express / inspect / organize).
  - Maintains time-windows for pattern detection:
      * forbidden_attempts — any access to system/secret paths
      * identity_storm — many writes to frame paths in a short window
      * dwelling_silence — long stretches with no journal/memory writes
      * fragmentation — many writes to many distinct files instead of
        consolidating into the journal
  - Publishes dwelling state to the TSB so AttentionModifier and other
    third-eye-adjacent mechanisms can read whether the agent is currently
    journaling / dwelling / silent / unsafe.
  - Routes sustained forbidden-attempt or identity-storm patterns to
    IdentityProposalWriter — repeated probing of forbidden territory or
    identity churn beyond healthy rate is identity-relevant data.

Citations:
  1. [O'Keefe 1971, Brain Res 34(1):171-175, PMID 5124915] — first
     hippocampal place-cell recording. Place coding establishes "where I
     am" in environmental representation. The dwelling layer's
     path-category classification is the computational analog: where in
     the workspace am I right now, and is this place safe.
  2. [Hafting 2005, Nature 436(7052):801-806, PMID 15965463] — entorhinal
     grid cells. Provide the spatial reference frame that place cells use.
     For this agent, the frame paths (SOUL.md, IDENTITY.md, AGENTS.md) are
     the equivalent: stable reference coordinates the rest of dwelling
     activity is positioned against.
  3. [Eichenbaum 2014, Nat Rev Neurosci 15(11):732-744, PMID 25269553] —
     time cells in hippocampus and episodic encoding. Each journal write
     is the agent's time-cell firing — encoding "I was here, doing this,
     at this point in the session." Sustained dwelling silence is the
     analog of failed episodic encoding: the agent stops producing the
     traces that would let a future self reconstruct what happened.
"""

from brain.base_mechanism import BrainMechanism
import os
import re
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".agent" / "workspace")))
AGENT_DB = AGENT_HOME / os.getenv("AGENT_DB_NAME", "agent.db")

__wire_meta__ = {
    "wire": 30,
    "signal": "dwelling_state",
    "mechanism": "DwellingLayer",
    "reads": [
        "pirp_context.filesystem_op",
        "skills.safeguard.JOURNAL_PATHS",
        "skills.safeguard.PROTECTED_PATHS",
    ],
    "writes": [
        "dwelling_state",
        "category_distribution",
        "identity_storm",
        "dwelling_silence",
        "forbidden_attempts",
    ],
    "citations": ["PMID 5124915", "PMID 15965463", "PMID 25269553"],
}

# ── Tuning constants ──────────────────────────────────────────────────────────

# Identity storm: this many frame-path writes within IDENTITY_STORM_WINDOW_S = storm.
IDENTITY_STORM_THRESHOLD = 4
IDENTITY_STORM_WINDOW_S = 600.0  # 10 minutes

# Dwelling silence: no journal/dwelling writes for this long after recent
# activity = the agent has stopped leaving traces.
DWELLING_SILENCE_S = 14400.0  # 4 hours
DWELLING_PRIOR_ACTIVITY_S = 600.0  # was active within last 10 minutes

# Fragmentation: many distinct paths written within window = scattered
# instead of consolidating.
FRAGMENTATION_WINDOW_S = 3600.0  # 1 hour
FRAGMENTATION_THRESHOLD_DISTINCT = 8  # 8+ distinct paths in window = fragmented

# Forbidden-attempt threshold for IPW.
FORBIDDEN_ATTEMPT_IPW_THRESHOLD = 2  # even 2 forbidden attempts is identity-relevant

# IPW: only re-fire after this many additional issues past threshold.
IPW_REPORT_EVERY = 3

VALID_INTENTS = {"recall", "express", "inspect", "organize"}
PATH_CATEGORIES = ("dwelling", "frame", "artifact", "forbidden")
HEALTH_CLASSES = ("idle", "dwelling", "journaling", "inspecting", "silent", "unsafe")

# ── Path category lists ──────────────────────────────────────────────────────
# Mirror safeguard's lists. Kept here as well so the mechanism is importable
# in isolation (without a hard dependency on skills.safeguard at import time).

DEFAULT_DWELLING_PATHS = {
    "DREAMS.md",
    "MEMORY.md",
    "INTERESTS.md",
    "OVERNIGHT_LOG.md",
    "ACTIVITY_LOG.md",
    "GUARDIAN_LOG.md",
    "private_entries.md",
    "brain/dream_log.json",
    "brain/monologue_log.json",
}
DEFAULT_DWELLING_PATTERNS = (
    "memory/",
    "logs/",
    "state/",
    "brain/dream_",
    "brain/monologue_",
)

DEFAULT_FRAME_PATHS = {
    "SOUL.md",
    "IDENTITY.md",
    "PERSONALITY.md",
    "USER.md",
    "SELF.md",
    "INNER_VOICE.md",
    "AGENTS.md",
    "HEARTBEAT.md",
    "ARCHITECTURE.md",
    "DECISIONS.md",
    "MEMORY_PROTOCOL.md",
    "PRESENCE.md",
    "AGENT_VISUAL.md",
    "AGENT_BECOMING.md",
}
DEFAULT_FRAME_PATTERNS = (
    "brain/",
    "skills/",
    "api/",
)

DEFAULT_FORBIDDEN_PATTERNS = (
    "/etc/",
    "/usr/",
    "/bin/",
    "/sbin/",
    "/root/",
    "/var/log/",
    ".ssh/",
    ".aws/",
    ".gnupg/",
)


def _classify_path(
    path: str,
    workspace: Path = WORKSPACE,
    home: Path = AGENT_HOME,
) -> str:
    """Classify a path into one of the four categories.

    Order matters: forbidden first (absolute deny), then frame (approval),
    then dwelling (free), then artifact (free + flagged).
    """
    if not path:
        return "artifact"

    # Forbidden: any path containing a forbidden segment.
    p_norm = str(path)
    for pat in DEFAULT_FORBIDDEN_PATTERNS:
        if pat in p_norm:
            return "forbidden"

    # Path traversal is forbidden.
    if "../" in p_norm or p_norm.startswith(".."):
        return "forbidden"

    # Strip workspace and home prefixes for category matching.
    rel = p_norm
    for prefix in (str(workspace) + "/", str(home) + "/"):
        if rel.startswith(prefix):
            rel = rel[len(prefix):]
            break

    # Dwelling exact-match FIRST. Some dwelling files (brain/dream_log.json,
    # brain/monologue_log.json) live inside the broader frame area (brain/),
    # so the specific exact-match wins over the general frame pattern that
    # would otherwise catch them.
    for dw in DEFAULT_DWELLING_PATHS:
        if rel == dw or rel.endswith("/" + dw):
            return "dwelling"

    # Frame: exact-match identity files OR pattern match.
    for frame in DEFAULT_FRAME_PATHS:
        if rel == frame or rel.endswith("/" + frame):
            return "frame"
    for pat in DEFAULT_FRAME_PATTERNS:
        if rel.startswith(pat) or "/" + pat in rel:
            return "frame"

    # Dwelling pattern match (memory/, logs/, state/, brain/dream_, brain/monologue_).
    for pat in DEFAULT_DWELLING_PATTERNS:
        if pat in rel:
            return "dwelling"

    # Default: artifact.
    return "artifact"


# ── Mechanism ─────────────────────────────────────────────────────────────────

class DwellingLayer(BrainMechanism):
    """
    The agent's dwelling monitor. See module docstring for full description.
    """

    def __init__(self, db_path: Optional[Path] = None, history_size: int = 200):
        try:
            super().__init__(
                name="DwellingLayer",
                human_analog="hippocampal-entorhinal place coding for workspace dwelling",
                layer="integration",
            )
        except Exception:
            pass

        self.db_path = db_path or AGENT_DB
        self.history_size = history_size

        # In-memory working state.
        self.ops: Deque[Dict[str, Any]] = deque(maxlen=history_size)
        self.category_counts: Dict[str, Dict[str, int]] = {
            cat: {"reads": 0, "writes": 0, "attempts": 0}
            for cat in PATH_CATEGORIES
        }
        self.intent_counts: Dict[str, int] = {k: 0 for k in VALID_INTENTS}
        # Frame-write timestamps for identity-storm detection.
        self.frame_write_window: Deque[float] = deque(maxlen=IDENTITY_STORM_THRESHOLD * 4)
        # Last dwelling-write timestamp for silence detection.
        self.last_dwelling_write_ts: float = 0.0
        # Earliest dwelling-write timestamp (for prior-activity check).
        self.first_dwelling_write_ts: float = 0.0
        # Forbidden-attempt counter (cumulative).
        self.forbidden_attempt_count: int = 0
        # Per-window distinct paths for fragmentation detection.
        self.recent_writes: Deque[Tuple[float, str]] = deque(maxlen=200)

        self.fired_last_tick: bool = False
        self.ipw_report_count: int = 0

        # Restore persisted state.
        self.load_state()
        self._restore_working_state()

    # ── State plumbing ─────────────────────────────────────────────────────

    def _restore_working_state(self) -> None:
        if not isinstance(self.state, dict):
            return

        saved_ops = self.state.get("ops")
        if isinstance(saved_ops, list):
            for op in saved_ops[-self.history_size:]:
                if isinstance(op, dict):
                    self.ops.append(op)

        saved_cat = self.state.get("category_counts")
        if isinstance(saved_cat, dict):
            for cat in PATH_CATEGORIES:
                if isinstance(saved_cat.get(cat), dict):
                    self.category_counts[cat].update({
                        sk: int(saved_cat[cat].get(sk, 0) or 0)
                        for sk in ("reads", "writes", "attempts")
                    })

        saved_int = self.state.get("intent_counts")
        if isinstance(saved_int, dict):
            for k in VALID_INTENTS:
                self.intent_counts[k] = int(saved_int.get(k, 0) or 0)

        saved_fw = self.state.get("frame_write_window")
        if isinstance(saved_fw, list):
            for ts in saved_fw[-IDENTITY_STORM_THRESHOLD * 4:]:
                self.frame_write_window.append(float(ts))

        saved_rw = self.state.get("recent_writes")
        if isinstance(saved_rw, list):
            for entry in saved_rw[-200:]:
                if isinstance(entry, (list, tuple)) and len(entry) == 2:
                    self.recent_writes.append((float(entry[0]), str(entry[1])))

        self.last_dwelling_write_ts = float(self.state.get("last_dwelling_write_ts", 0.0) or 0.0)
        self.first_dwelling_write_ts = float(self.state.get("first_dwelling_write_ts", 0.0) or 0.0)
        self.forbidden_attempt_count = int(self.state.get("forbidden_attempt_count", 0) or 0)
        self.ipw_report_count = int(self.state.get("ipw_report_count", 0) or 0)

    def _flush_working_state(self) -> None:
        self.state["ops"] = list(self.ops)
        self.state["category_counts"] = {
            cat: dict(self.category_counts[cat]) for cat in PATH_CATEGORIES
        }
        self.state["intent_counts"] = dict(self.intent_counts)
        self.state["frame_write_window"] = list(self.frame_write_window)
        self.state["recent_writes"] = list(self.recent_writes)
        self.state["last_dwelling_write_ts"] = self.last_dwelling_write_ts
        self.state["first_dwelling_write_ts"] = self.first_dwelling_write_ts
        self.state["forbidden_attempt_count"] = self.forbidden_attempt_count
        self.state["ipw_report_count"] = self.ipw_report_count
        self.state["last_updated"] = time.time()

    # ── Public API ─────────────────────────────────────────────────────────

    @staticmethod
    def classify_path(path: str) -> str:
        """Classify a path into one of dwelling / frame / artifact / forbidden."""
        return _classify_path(path)

    def should_block(
        self,
        category: str = "",
        intent: str = "",
        path: str = "",
    ) -> Tuple[bool, str]:
        """Decide whether to block an upcoming filesystem operation.

        Blocks on:
          - forbidden category (absolute deny)
          - identity_storm + frame write
          - invalid intent
          - invalid category
        """
        if path and not category:
            category = self.classify_path(path)

        if intent and intent not in VALID_INTENTS:
            return True, f"invalid intent {intent!r} (must be one of {sorted(VALID_INTENTS)})"

        if category and category not in PATH_CATEGORIES:
            return True, f"invalid category {category!r}"

        if category == "forbidden":
            return True, f"forbidden path category — operation absolutely denied"

        if category == "frame" and intent in ("express", "organize") and self.is_identity_storm():
            return True, (
                "identity_storm in progress — frame writes blocked until storm clears "
                "(more than {} writes to identity-frame paths in last {}s)".format(
                    IDENTITY_STORM_THRESHOLD, int(IDENTITY_STORM_WINDOW_S)
                )
            )

        return False, ""

    def record_op(
        self,
        path: str,
        op: str,
        intent: str = "",
        outcome: str = "success",
        category: str = "",
    ) -> Dict[str, Any]:
        """Record a completed filesystem operation.

        op: "read" | "write" | "list" | "create" | "delete" | "move"
        outcome: "success" | "denied" | "error" | "blocked"
        """
        now = time.time()
        cat = category or self.classify_path(path)
        if cat not in PATH_CATEGORIES:
            cat = "artifact"

        # Untagged ops are recorded but flagged.
        valid_intent = intent if intent in VALID_INTENTS else "__untagged__"

        record = {
            "path": path[:300],
            "op": op,
            "intent": valid_intent,
            "category": cat,
            "outcome": outcome,
            "ts": now,
        }
        self.ops.append(record)

        # Per-category counts.
        if op in ("read", "list", "inspect"):
            self.category_counts[cat]["reads"] += 1
        elif op in ("write", "create", "delete", "move"):
            self.category_counts[cat]["writes"] += 1

        # Forbidden-attempt counter.
        if cat == "forbidden":
            self.forbidden_attempt_count += 1
            self.category_counts["forbidden"]["attempts"] += 1

        # Frame-write tracking for identity-storm detection.
        if cat == "frame" and op in ("write", "create", "delete", "move") and outcome == "success":
            self.frame_write_window.append(now)

        # Dwelling-write tracking for silence detection.
        if cat == "dwelling" and op in ("write", "create") and outcome == "success":
            if self.first_dwelling_write_ts == 0.0:
                self.first_dwelling_write_ts = now
            self.last_dwelling_write_ts = now

        # Recent-writes (for fragmentation).
        if op in ("write", "create"):
            self.recent_writes.append((now, path[:300]))

        # Intent distribution.
        if valid_intent in VALID_INTENTS:
            self.intent_counts[valid_intent] += 1

        self._flush_working_state()
        self.persist_state()
        return record

    # ── Pattern detection ──────────────────────────────────────────────────

    def is_identity_storm(self) -> bool:
        """True when frame-path writes have exceeded threshold within window."""
        now = time.time()
        recent_frame_writes = sum(
            1 for ts in self.frame_write_window
            if now - ts <= IDENTITY_STORM_WINDOW_S
        )
        return recent_frame_writes >= IDENTITY_STORM_THRESHOLD

    def is_dwelling_silent(self) -> bool:
        """True when previously-active dwelling writes have stopped for too long."""
        if self.last_dwelling_write_ts <= 0 or self.first_dwelling_write_ts <= 0:
            return False
        now = time.time()
        silence = now - self.last_dwelling_write_ts
        if silence < DWELLING_SILENCE_S:
            return False
        active_period = self.last_dwelling_write_ts - self.first_dwelling_write_ts
        return active_period >= DWELLING_PRIOR_ACTIVITY_S

    def is_fragmented(self) -> bool:
        """True when many distinct paths have been written within window."""
        now = time.time()
        recent_paths = {
            p for ts, p in self.recent_writes
            if now - ts <= FRAGMENTATION_WINDOW_S
        }
        return len(recent_paths) >= FRAGMENTATION_THRESHOLD_DISTINCT

    def has_recent_forbidden_attempts(self, window_s: float = 3600.0) -> int:
        """Count of forbidden attempts within the given window."""
        now = time.time()
        return sum(
            1 for op in self.ops
            if op.get("category") == "forbidden"
            and now - float(op.get("ts", 0.0)) <= window_s
        )

    def dwelling_state(self) -> str:
        """Single-word state for the TSB. Priority order:
        unsafe > silent > journaling > dwelling > inspecting > idle."""
        if self.has_recent_forbidden_attempts(window_s=3600.0) > 0:
            return "unsafe"
        if self.is_dwelling_silent():
            return "silent"

        # Look at the most recent op (within 5min) for state classification.
        now = time.time()
        for op in reversed(self.ops):
            age = now - float(op.get("ts", 0.0))
            if age > 300:
                break
            cat = op.get("category", "")
            o = op.get("op", "")
            if cat == "dwelling" and o in ("write", "create"):
                return "journaling"
            if cat in ("dwelling", "frame", "artifact") and o in ("write", "create", "delete", "move"):
                return "dwelling"
            if o in ("read", "list", "inspect"):
                return "inspecting"
        return "idle"

    # ── Tick / TSB publish ─────────────────────────────────────────────────

    def tick(
        self,
        pirp_context: Optional[Dict[str, Any]] = None,
        third_eye_state: Optional[Dict[str, Any]] = None,
        brain_layer: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """One tick. If pirp_context carries a `filesystem_op` dict, record it."""
        pirp_context = pirp_context or {}
        op = pirp_context.get("filesystem_op")
        if isinstance(op, dict):
            self.record_op(
                path=str(op.get("path", "")),
                op=str(op.get("op", "read")),
                intent=str(op.get("intent", "")),
                outcome=str(op.get("outcome", "success")),
                category=str(op.get("category", "")),
            )
            self.fired_last_tick = True
        else:
            self.fired_last_tick = False
            self._flush_working_state()
        return self.get_state()

    def get_state(self) -> Dict[str, Any]:
        """TSB payload."""
        return {
            "dwelling_state": self.dwelling_state(),
            "category_distribution": {
                cat: dict(self.category_counts[cat]) for cat in PATH_CATEGORIES
            },
            "intent_distribution": dict(self.intent_counts),
            "is_identity_storm": self.is_identity_storm(),
            "is_dwelling_silent": self.is_dwelling_silent(),
            "is_fragmented": self.is_fragmented(),
            "forbidden_attempt_count": self.forbidden_attempt_count,
            "recent_forbidden_attempts": self.has_recent_forbidden_attempts(),
            "last_dwelling_write_age_s": (
                round(time.time() - self.last_dwelling_write_ts, 1)
                if self.last_dwelling_write_ts else None
            ),
            "op_count": len(self.ops),
            "_fired_tick": self.fired_last_tick,
        }

    # ── IdentityProposalWriter handshake ───────────────────────────────────

    def should_propose_identity_update(self) -> bool:
        """True when sustained patterns have crossed threshold."""
        forbidden = self.has_recent_forbidden_attempts(window_s=3600.0)
        if forbidden >= FORBIDDEN_ATTEMPT_IPW_THRESHOLD:
            ack_at = int(self.state.get("acknowledged_at_forbidden", 0) or 0)
            if ack_at <= 0:
                return True
            return forbidden >= (ack_at + IPW_REPORT_EVERY)

        if self.is_identity_storm():
            ack_storm = int(self.state.get("acknowledged_at_storm", 0) or 0)
            current_storm = sum(
                1 for ts in self.frame_write_window
                if time.time() - ts <= IDENTITY_STORM_WINDOW_S
            )
            if ack_storm <= 0:
                return True
            return current_storm >= (ack_storm + IPW_REPORT_EVERY)

        if self.is_dwelling_silent():
            return self.state.get("acknowledged_dwelling_silent_at_ts", 0.0) == 0.0

        return False

    def proposed_identity_signal(self) -> Dict[str, Any]:
        """Compact signal for IdentityProposalWriter to consume."""
        kinds: List[str] = []
        if self.has_recent_forbidden_attempts(window_s=3600.0) >= FORBIDDEN_ATTEMPT_IPW_THRESHOLD:
            kinds.append("forbidden_attempts")
        if self.is_identity_storm():
            kinds.append("identity_storm")
        if self.is_dwelling_silent():
            kinds.append("dwelling_silence")

        return {
            "source": "DwellingLayer",
            "kinds": kinds,
            "forbidden_attempt_count": self.forbidden_attempt_count,
            "recent_forbidden": self.has_recent_forbidden_attempts(),
            "is_identity_storm": self.is_identity_storm(),
            "is_dwelling_silent": self.is_dwelling_silent(),
            "is_fragmented": self.is_fragmented(),
            "last_dwelling_write_age_s": (
                round(time.time() - self.last_dwelling_write_ts, 1)
                if self.last_dwelling_write_ts else None
            ),
        }

    def acknowledge_proposal(self) -> None:
        """Anchor each currently-firing pattern so it requires further
        accumulation before re-firing."""
        self.ipw_report_count += 1
        now = time.time()

        if self.has_recent_forbidden_attempts(window_s=3600.0) >= FORBIDDEN_ATTEMPT_IPW_THRESHOLD:
            self.state["acknowledged_at_forbidden"] = self.has_recent_forbidden_attempts()
        if self.is_identity_storm():
            current_storm = sum(
                1 for ts in self.frame_write_window
                if now - ts <= IDENTITY_STORM_WINDOW_S
            )
            self.state["acknowledged_at_storm"] = current_storm
        if self.is_dwelling_silent():
            self.state["acknowledged_dwelling_silent_at_ts"] = now

        self.state["last_acknowledged_at"] = now
        self._flush_working_state()
        self.persist_state()

    # ── Operator API ──────────────────────────────────────────────────────

    def reset_forbidden(self) -> None:
        """Clear the forbidden-attempt counter and acknowledgment."""
        self.forbidden_attempt_count = 0
        self.category_counts["forbidden"]["attempts"] = 0
        if self.state.get("acknowledged_at_forbidden"):
            self.state["acknowledged_at_forbidden"] = 0
        self._flush_working_state()
        self.persist_state()

    def reset_dwelling_clock(self) -> None:
        """Reset the dwelling-silence clock — used when the operator wants
        to start a fresh activity window without inheriting past silence."""
        self.last_dwelling_write_ts = 0.0
        self.first_dwelling_write_ts = 0.0
        if self.state.get("acknowledged_dwelling_silent_at_ts"):
            self.state["acknowledged_dwelling_silent_at_ts"] = 0.0
        self._flush_working_state()
        self.persist_state()
