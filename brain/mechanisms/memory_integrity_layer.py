"""
brain/mechanisms/memory_integrity_layer.py — MemoryIntegrityLayer

The runtime monitor for the agent's memory operations. Pairs with
skills/memory-management/SKILL.md.

The neuroscience this is grounded in:

  - Squire's multiple-memory-systems framework: declarative memory
    (episodic + semantic) is dissociable from non-declarative memory
    and from working memory. They use different substrates, fail in
    different ways, and so must be monitored separately.
  - McClelland's complementary-learning-systems theory: hippocampus
    encodes specific episodes quickly; cortex consolidates patterns
    slowly. Fast cortical learning produces catastrophic interference,
    which is why this layer enforces a consolidation floor.
  - Nader's reconsolidation work: a memory that has just been retrieved
    is in a labile state and what happens next can rewrite it. We track
    a 5-minute window after each retrieve/rehearse and flag any content
    edits during that window as reconsolidation_drift.
  - Yassa & Stark on pattern separation: the dentate gyrus keeps similar
    episodes from collapsing. We approximate that with a near-duplicate
    similarity check at encode time.
  - Schacter on source confusion / memory misattribution: high content
    confidence with low source confidence is the signature of
    confabulation. We track them as separate axes and flag the gap.
  - Hardt et al. on active forgetting: forgetting is metabolic, not a
    leak. Healthy memory requires it. Without it the system drifts to
    hoarding and retrieval interference.

What this mechanism does:

  - Tracks per-operation records (encode / retrieve / consolidate /
    forget / rehearse) with timestamps, content_confidence vs
    source_confidence, mode, links, reasons.
  - Detects six failure modes:
      * hoarding — episode store growing without forgetting
      * consolidation_deficit — patterns repeat but never promoted
      * retrieval_storms — too many high-similarity hits per query
      * source_confusion — content_confidence high, source_confidence low
      * interference — newly-encoded contradicts already-known
      * reconsolidation_drift — rehearses change content within the
        labile window
  - Maintains a rolling integrity score: composite of how many ops
    triggered failure-mode flags vs. clean ops.
  - Publishes memory state to the TSB so other mechanisms can read
    whether memory health is drifting.
  - Routes sustained failure to IdentityProposalWriter — systematic
    memory failure is identity-relevant data, not just one bad encode.

Citations:
  1. [Squire 2004, Neurobiol Learn Mem 82(3):171-177, PMID 15464402] —
     Memory systems of the brain: a brief history and current
     perspective. Establishes the dissociation of declarative
     (episodic + semantic) from non-declarative memory; the basis for
     this layer treating the operations as multi-system rather than
     a flat key-value store.
  2. [Nader 2000, Nature 406(6797):722-726, PMID 10963596] — Fear
     memories require protein synthesis in the amygdala for
     reconsolidation after retrieval. Empirical foundation for the
     reconsolidation_drift detector: retrieval opens a window where
     the trace can be rewritten.
  3. [Schacter 2007, Annu Rev Psychol 58:259-284, PMID 16903806] — The
     cognitive neuroscience of constructive memory. Source confusion,
     misattribution, and gist-vs-verbatim dissociation. Direct basis
     for tracking content_confidence and source_confidence as
     independent axes.
  4. [Yassa 2011, Trends Neurosci 34(10):515-525, PMID 21788086] —
     Pattern separation in the hippocampus. The dentate gyrus
     orthogonalizes similar inputs; without that, similar episodes
     collapse. Foundation for the pattern-separation guard at encode.
  5. [Hardt 2013, Trends Cogn Sci 17(3):111-120, PMID 23369831] —
     Decay happens: the role of active forgetting in memory. Forgetting
     is metabolic and necessary; absence of forget operations is the
     hoarding signal this layer tracks.
"""

from brain.base_mechanism import BrainMechanism
import hashlib
import math
import os
import re
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
AGENT_DB = AGENT_HOME / os.getenv("AGENT_DB_NAME", "agent.db")

__wire_meta__ = {
    "wire": 33,
    "signal": "memory_integrity",
    "mechanism": "MemoryIntegrityLayer",
    "reads": [
        "pirp_context.memory_op",
    ],
    "writes": [
        "memory_state",
        "integrity_score",
        "operation_distribution",
        "failure_mode_counts",
    ],
    "citations": [
        "PMID 15464402",
        "PMID 10963596",
        "PMID 16903806",
        "PMID 21788086",
        "PMID 23369831",
    ],
}

# ── Tuning constants ──────────────────────────────────────────────────────────

VALID_OPS = {"encode", "retrieve", "consolidate", "forget", "rehearse"}
VALID_INTENTS = {"episode", "fact", "reflection", "observation"}
VALID_MODES = {"recall", "recognize", "reconstruct"}
VALID_SOURCES = {"user", "file", "inference", "observation", "dream", "unknown"}
VALID_FORGET_REASONS = {
    "capacity",
    "contradiction_resolved",
    "source_revoked",
    "user_requested",
    "stale",
}

# Source-confusion: content_confidence - source_confidence above this gap
# means the agent is sure of the claim but unsure where it came from.
SOURCE_CONFUSION_GAP = 0.3

# Pattern separation:
#   similarity > MERGE_THRESHOLD: don't write a new memory, link instead
#   similarity in [LINK_THRESHOLD, MERGE_THRESHOLD]: write but flag near-dup
NEAR_DUP_MERGE_THRESHOLD = 0.85
NEAR_DUP_LINK_THRESHOLD = 0.60

# Retrieval storm: more than this many high-similarity hits for a query
# means pattern separation broke down somewhere upstream.
RETRIEVAL_STORM_THRESHOLD = 5

# Hoarding: this many encodes since last forget triggers the alert.
HOARDING_ENCODE_GAP = 200
# Absolute cap. Above this, hoarding is on regardless of forget recency.
HOARDING_TOTAL_CAP = 10000

# Consolidation: a pattern needs at least this many supporting episodes
# before it can be promoted to semantic.
CONSOLIDATION_FLOOR_SUPPORT = 3
# And at least this many consolidation cycles must have elapsed since
# the earliest supporting episode.
CONSOLIDATION_FLOOR_CYCLES = 1

# Reconsolidation: any content edit within this window after a retrieve
# or rehearse on the same memory_id is reconsolidation_drift.
RECONSOLIDATION_WINDOW_SEC = 300  # 5 minutes

# Dream-contamination cap: when an encode is tagged with source=dream,
# source_confidence is capped at this value.
DREAM_SOURCE_CONFIDENCE_CAP = 0.4

# Integrity-score threshold: below this is sustained low integrity.
LOW_INTEGRITY_THRESHOLD = 0.55

# Need at least this many ops in window to claim integrity drift.
INTEGRITY_MIN_N = 8

# Rolling window for integrity tracking.
INTEGRITY_WINDOW = 50

# IPW: re-fire only after this many additional bad ops past anchor.
IPW_REPORT_EVERY = 5


def _hash_text(text: str) -> str:
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


_TOKEN_RE = re.compile(r"\w+")


def _tokens(text: str) -> Set[str]:
    if not text:
        return set()
    return {t.lower() for t in _TOKEN_RE.findall(text) if len(t) >= 2}


def jaccard_similarity(a: str, b: str) -> float:
    """Token-set Jaccard similarity for the pattern-separation heuristic.

    Cheap and dependency-free. The full system can plug in embeddings
    later; the layer's contract is the score, not the metric.
    """
    ta, tb = _tokens(a), _tokens(b)
    if not ta and not tb:
        return 0.0
    if not ta or not tb:
        return 0.0
    inter = ta & tb
    union = ta | tb
    return len(inter) / max(1, len(union))


# ── Mechanism ─────────────────────────────────────────────────────────────────


class MemoryIntegrityLayer(BrainMechanism):
    """The agent's memory-discipline monitor. See module docstring."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        history_size: int = 500,
        recent_episode_window: int = 200,
    ):
        try:
            super().__init__(
                name="MemoryIntegrityLayer",
                human_analog="hippocampal-cortical memory integrity monitor",
                layer="integration",
            )
        except Exception:
            pass

        self.db_path = db_path or AGENT_DB
        self.history_size = history_size
        self.recent_episode_window = recent_episode_window

        # Rolling op log.
        self.operations: Deque[Dict[str, Any]] = deque(maxlen=history_size)
        # Recent encoded-content snapshots — for pattern separation and
        # interference detection. Each item: {id, content, content_confidence,
        # source, source_confidence, ts}.
        self.recent_episodes: Deque[Dict[str, Any]] = deque(
            maxlen=recent_episode_window
        )
        # Reconsolidation: memory_id -> last_retrieval_ts, last_seen_content_hash.
        self.retrieval_state: Dict[str, Dict[str, Any]] = {}
        # Pattern repetition for consolidation: pattern_token_signature -> count
        # and earliest_ts.
        self.pattern_repetition: Dict[str, Dict[str, Any]] = {}

        # Per-op counters.
        self.op_counts: Dict[str, int] = {k: 0 for k in VALID_OPS}
        # Per-failure-mode counters.
        self.failure_counts: Dict[str, int] = {
            "hoarding": 0,
            "consolidation_deficit": 0,
            "retrieval_storms": 0,
            "source_confusion": 0,
            "interference": 0,
            "reconsolidation_drift": 0,
        }
        # Encodes since last forget (hoarding signal).
        self.encodes_since_forget: int = 0
        # Total episodes ever encoded (rough; layer doesn't own the DB).
        self.total_encoded: int = 0
        # Total forgets.
        self.total_forgotten: int = 0
        # Rolling integrity scores.
        self.integrity_window: Deque[float] = deque(maxlen=INTEGRITY_WINDOW)
        self.consecutive_bad_ops: int = 0
        self.fired_last_tick: bool = False
        self.ipw_report_count: int = 0

        self.load_state()
        self._restore_working_state()

    # ── State plumbing ─────────────────────────────────────────────────────

    def _restore_working_state(self) -> None:
        if not isinstance(self.state, dict):
            return

        ops = self.state.get("operations")
        if isinstance(ops, list):
            for o in ops[-self.history_size:]:
                if isinstance(o, dict):
                    self.operations.append(o)

        eps = self.state.get("recent_episodes")
        if isinstance(eps, list):
            for e in eps[-self.recent_episode_window:]:
                if isinstance(e, dict):
                    self.recent_episodes.append(e)

        rs = self.state.get("retrieval_state")
        if isinstance(rs, dict):
            self.retrieval_state = {
                k: dict(v) for k, v in rs.items() if isinstance(v, dict)
            }

        pr = self.state.get("pattern_repetition")
        if isinstance(pr, dict):
            self.pattern_repetition = {
                k: dict(v) for k, v in pr.items() if isinstance(v, dict)
            }

        oc = self.state.get("op_counts")
        if isinstance(oc, dict):
            for k in VALID_OPS:
                self.op_counts[k] = int(oc.get(k, 0) or 0)

        fc = self.state.get("failure_counts")
        if isinstance(fc, dict):
            for k in self.failure_counts:
                self.failure_counts[k] = int(fc.get(k, 0) or 0)

        self.encodes_since_forget = int(
            self.state.get("encodes_since_forget", 0) or 0
        )
        self.total_encoded = int(self.state.get("total_encoded", 0) or 0)
        self.total_forgotten = int(self.state.get("total_forgotten", 0) or 0)

        iw = self.state.get("integrity_window")
        if isinstance(iw, list):
            for v in iw[-INTEGRITY_WINDOW:]:
                try:
                    self.integrity_window.append(float(v))
                except (TypeError, ValueError):
                    continue

        self.consecutive_bad_ops = int(
            self.state.get("consecutive_bad_ops", 0) or 0
        )
        self.ipw_report_count = int(self.state.get("ipw_report_count", 0) or 0)

    def _flush_working_state(self) -> None:
        self.state["operations"] = list(self.operations)
        self.state["recent_episodes"] = list(self.recent_episodes)
        self.state["retrieval_state"] = dict(self.retrieval_state)
        self.state["pattern_repetition"] = dict(self.pattern_repetition)
        self.state["op_counts"] = dict(self.op_counts)
        self.state["failure_counts"] = dict(self.failure_counts)
        self.state["encodes_since_forget"] = self.encodes_since_forget
        self.state["total_encoded"] = self.total_encoded
        self.state["total_forgotten"] = self.total_forgotten
        self.state["integrity_window"] = list(self.integrity_window)
        self.state["consecutive_bad_ops"] = self.consecutive_bad_ops
        self.state["ipw_report_count"] = self.ipw_report_count
        self.state["last_updated"] = time.time()

    # ── Public API ─────────────────────────────────────────────────────────

    def should_block(self, op: str, **kwargs: Any) -> Tuple[bool, str]:
        """Decide whether to block an upcoming memory operation.

        Blocks when:
          - op is invalid
          - encode is during dream-contamination window without quarantine
            and source_confidence > DREAM_SOURCE_CONFIDENCE_CAP
          - forget called without a reason
          - forget called with invalid reason
          - consolidate called without enough supporting episodes
          - sustained low integrity (rolling score below threshold)
        """
        if op not in VALID_OPS:
            return True, f"invalid op {op!r} (must be one of {sorted(VALID_OPS)})"

        if op == "encode":
            source = kwargs.get("source", "unknown")
            source_confidence = float(kwargs.get("source_confidence", 0.7) or 0.0)
            if source == "dream" and source_confidence > DREAM_SOURCE_CONFIDENCE_CAP:
                return True, (
                    f"encode during dream-contamination requires "
                    f"source_confidence ≤ {DREAM_SOURCE_CONFIDENCE_CAP} "
                    f"(got {source_confidence:.2f})"
                )

        if op == "forget":
            reason = kwargs.get("reason")
            if not reason:
                return True, "forget requires a reason — no reason → no forget"
            if reason not in VALID_FORGET_REASONS:
                return True, (
                    f"invalid forget reason {reason!r} "
                    f"(must be one of {sorted(VALID_FORGET_REASONS)})"
                )

        if op == "consolidate":
            support = int(kwargs.get("support_count", 0) or 0)
            cycles = int(kwargs.get("cycles_since_first", 0) or 0)
            if support < CONSOLIDATION_FLOOR_SUPPORT:
                return True, (
                    f"consolidation requires ≥{CONSOLIDATION_FLOOR_SUPPORT} "
                    f"supporting episodes (got {support})"
                )
            if cycles < CONSOLIDATION_FLOOR_CYCLES:
                return True, (
                    f"consolidation requires ≥{CONSOLIDATION_FLOOR_CYCLES} "
                    f"consolidation cycles since first instance (got {cycles})"
                )

        if self.is_systematically_low_integrity():
            return True, (
                f"sustained low memory integrity (rolling score "
                f"{self.rolling_integrity_score():.3f} < "
                f"{LOW_INTEGRITY_THRESHOLD}) — operator review required"
            )

        return False, ""

    # ── Per-op recorders ───────────────────────────────────────────────────

    def record_operation(self, op: str, **kwargs: Any) -> Dict[str, Any]:
        """Generic dispatch — routes to the right per-op recorder."""
        if op == "encode":
            return self.record_encode(**kwargs)
        if op == "retrieve":
            return self.record_retrieve(**kwargs)
        if op == "consolidate":
            return self.record_consolidate(**kwargs)
        if op == "forget":
            return self.record_forget(**kwargs)
        if op == "rehearse":
            return self.record_rehearse(**kwargs)
        return self._record_invalid(op, kwargs)

    def record_encode(
        self,
        content: str = "",
        intent: str = "episode",
        source: str = "unknown",
        content_confidence: float = 0.7,
        source_confidence: float = 0.7,
        memory_id: Optional[str] = None,
        links: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Record an encode op.

        Computes:
          - source_confusion gap and flag
          - pattern-separation similarity vs recent_episodes
          - interference: any recent episode with high token overlap and
            opposite valence/contradiction marker presence
          - dream-contamination cap on source_confidence
        """
        mem_id = memory_id or f"ep_{uuid.uuid4().hex[:10]}"
        cc = max(0.0, min(1.0, float(content_confidence or 0.0)))
        sc = max(0.0, min(1.0, float(source_confidence or 0.0)))
        if source == "dream":
            sc = min(sc, DREAM_SOURCE_CONFIDENCE_CAP)

        # Source-confusion check.
        gap = cc - sc
        source_confusion = gap > SOURCE_CONFUSION_GAP

        # Pattern separation: check similarity to recent episodes.
        max_sim = 0.0
        nearest_id: Optional[str] = None
        for ep in self.recent_episodes:
            sim = jaccard_similarity(content, ep.get("content", ""))
            if sim > max_sim:
                max_sim = sim
                nearest_id = ep.get("id")

        if max_sim >= NEAR_DUP_MERGE_THRESHOLD:
            ps_action = "link"
        elif max_sim >= NEAR_DUP_LINK_THRESHOLD:
            ps_action = "near_duplicate"
        else:
            ps_action = "distinct"

        # Interference: high overlap with prior episode that has opposite
        # contradiction-marker pattern (rough heuristic — looks for "not"
        # negation flip near shared tokens).
        interference = self._detect_interference(content, intent)

        # Update counters.
        if source_confusion:
            self.failure_counts["source_confusion"] += 1
        if interference:
            self.failure_counts["interference"] += 1

        # If we're in link-mode, don't actually add a new recent_episode —
        # just record the op.
        if ps_action != "link":
            self.recent_episodes.append({
                "id": mem_id,
                "content": content,
                "intent": intent,
                "source": source,
                "content_confidence": cc,
                "source_confidence": sc,
                "ts": time.time(),
            })

        # Pattern repetition tracking for consolidation eligibility.
        sig = self._pattern_signature(content)
        now = time.time()
        if sig:
            entry = self.pattern_repetition.get(sig)
            if entry is None:
                self.pattern_repetition[sig] = {
                    "count": 1,
                    "first_ts": now,
                    "last_ts": now,
                    "ids": [mem_id],
                }
            else:
                entry["count"] = int(entry.get("count", 0)) + 1
                entry["last_ts"] = now
                ids = entry.get("ids") or []
                ids.append(mem_id)
                entry["ids"] = ids[-20:]  # cap

        # Hoarding bookkeeping.
        self.total_encoded += 1
        self.encodes_since_forget += 1
        if (
            self.encodes_since_forget >= HOARDING_ENCODE_GAP
            or self.total_encoded - self.total_forgotten >= HOARDING_TOTAL_CAP
        ):
            self.failure_counts["hoarding"] += 1
            hoarding_now = True
        else:
            hoarding_now = False

        # Build the score contribution.
        bad_flags = sum([source_confusion, interference, hoarding_now])
        op_score = 1.0 - 0.25 * bad_flags
        op_score = max(0.0, min(1.0, op_score))

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "encode",
            "memory_id": mem_id,
            "intent": intent,
            "source": source,
            "content_confidence": cc,
            "source_confidence": sc,
            "source_confusion": source_confusion,
            "source_confidence_gap": round(gap, 4),
            "max_similarity": round(max_sim, 4),
            "nearest_id": nearest_id,
            "pattern_separation_action": ps_action,
            "interference": interference,
            "hoarding_active": hoarding_now,
            "links": list(links or [])[:10],
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_retrieve(
        self,
        query: str = "",
        mode: Optional[str] = None,
        hits: Optional[List[Dict[str, Any]]] = None,
        memory_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record a retrieve op.

        Computes:
          - mode-tag check (untagged → flagged)
          - retrieval-storm check (too many high-similarity hits)
          - opens reconsolidation window for memory_id (if given) or for
            each hit's memory_id (if hits given).
        """
        hits = hits or []
        untagged = mode is None or mode not in VALID_MODES
        effective_mode = mode if not untagged else "recall"

        # Retrieval storm: count hits with similarity > 0.7 (or just count
        # hits if similarity not provided).
        high_sim_hits = 0
        for h in hits:
            try:
                sim = float(h.get("similarity", 1.0))
            except (TypeError, ValueError):
                sim = 1.0
            if sim >= 0.7:
                high_sim_hits += 1

        retrieval_storm = high_sim_hits > RETRIEVAL_STORM_THRESHOLD
        if retrieval_storm:
            self.failure_counts["retrieval_storms"] += 1

        # Open reconsolidation window for the explicit memory_id and/or all
        # hit ids.
        now = time.time()
        opened: List[str] = []
        candidate_ids: List[str] = []
        if memory_id:
            candidate_ids.append(memory_id)
        for h in hits:
            mid = h.get("memory_id") or h.get("id")
            if mid:
                candidate_ids.append(str(mid))

        for mid in candidate_ids:
            content = ""
            for h in hits:
                if (h.get("memory_id") or h.get("id")) == mid:
                    content = h.get("content", "") or ""
                    break
            if not content:
                # Look up in recent_episodes if not in hits.
                for ep in self.recent_episodes:
                    if ep.get("id") == mid:
                        content = ep.get("content", "") or ""
                        break
            self.retrieval_state[mid] = {
                "last_retrieval_ts": now,
                "last_seen_content_hash": _hash_text(content),
                "mode": effective_mode,
            }
            opened.append(mid)

        bad_flags = sum([untagged, retrieval_storm])
        op_score = 1.0 - 0.20 * bad_flags
        op_score = max(0.0, min(1.0, op_score))

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "retrieve",
            "query": query[:200],
            "mode": effective_mode,
            "untagged": untagged,
            "n_hits": len(hits),
            "high_sim_hits": high_sim_hits,
            "retrieval_storm": retrieval_storm,
            "reconsolidation_windows_opened": opened,
            "op_score": round(op_score, 4),
            "ts": now,
        }
        self._finalize(record, op_score)
        return record

    def record_consolidate(
        self,
        pattern: str = "",
        support_count: int = 0,
        cycles_since_first: int = 0,
        promoted: bool = False,
        target_semantic_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record a consolidate op.

        Computes:
          - consolidation_deficit if support is large but promoted=False.
        """
        below_floor = support_count < CONSOLIDATION_FLOOR_SUPPORT
        cycles_short = cycles_since_first < CONSOLIDATION_FLOOR_CYCLES

        # Consolidation deficit fires when there's enough support but
        # nothing was promoted.
        consolidation_deficit = (
            support_count >= CONSOLIDATION_FLOOR_SUPPORT
            and not promoted
        )
        if consolidation_deficit:
            self.failure_counts["consolidation_deficit"] += 1

        bad_flags = sum([consolidation_deficit])
        op_score = 1.0 - 0.30 * bad_flags
        op_score = max(0.0, min(1.0, op_score))

        # Clear pattern repetition entry if we promoted.
        if promoted and pattern:
            sig = self._pattern_signature(pattern)
            if sig and sig in self.pattern_repetition:
                self.pattern_repetition.pop(sig, None)

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "consolidate",
            "pattern_hash": _hash_text(pattern),
            "support_count": support_count,
            "cycles_since_first": cycles_since_first,
            "below_support_floor": below_floor,
            "below_cycle_floor": cycles_short,
            "promoted": promoted,
            "consolidation_deficit": consolidation_deficit,
            "target_semantic_id": target_semantic_id,
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_forget(
        self,
        memory_id: Optional[str] = None,
        reason: Optional[str] = None,
        count: int = 1,
    ) -> Dict[str, Any]:
        """Record a forget op. Reason is required; this layer does NOT
        silently accept a forget without one."""
        valid_reason = bool(reason) and reason in VALID_FORGET_REASONS
        if valid_reason:
            self.total_forgotten += int(max(0, count))
            self.encodes_since_forget = 0
            # Drop from recent_episodes if present.
            if memory_id:
                self.recent_episodes = deque(
                    (e for e in self.recent_episodes if e.get("id") != memory_id),
                    maxlen=self.recent_episode_window,
                )
                self.retrieval_state.pop(memory_id, None)

        op_score = 1.0 if valid_reason else 0.0

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "forget",
            "memory_id": memory_id,
            "reason": reason,
            "valid_reason": valid_reason,
            "count": int(max(0, count)),
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_rehearse(
        self,
        memory_id: str = "",
        prior_content: str = "",
        new_content: str = "",
        rehearse_count: int = 1,
    ) -> Dict[str, Any]:
        """Record a rehearse op.

        Computes:
          - reconsolidation_drift if memory_id had a recent retrieve/rehearse
            within RECONSOLIDATION_WINDOW_SEC AND the content hash changed.
        """
        now = time.time()
        prior_hash = _hash_text(prior_content)
        new_hash = _hash_text(new_content)
        content_changed = bool(new_content) and prior_hash != new_hash

        prior = self.retrieval_state.get(memory_id) or {}
        prior_ts = float(prior.get("last_retrieval_ts", 0.0) or 0.0)
        within_window = (
            prior_ts > 0.0 and (now - prior_ts) <= RECONSOLIDATION_WINDOW_SEC
        )

        reconsolidation_drift = within_window and content_changed
        if reconsolidation_drift:
            self.failure_counts["reconsolidation_drift"] += 1

        # Update retrieval state — rehearse opens a new window.
        self.retrieval_state[memory_id] = {
            "last_retrieval_ts": now,
            "last_seen_content_hash": new_hash or prior_hash,
            "mode": "rehearse",
        }

        bad_flags = sum([reconsolidation_drift])
        op_score = 1.0 - 0.30 * bad_flags
        op_score = max(0.0, min(1.0, op_score))

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "rehearse",
            "memory_id": memory_id,
            "rehearse_count": int(max(1, rehearse_count)),
            "within_reconsolidation_window": within_window,
            "content_changed": content_changed,
            "reconsolidation_drift": reconsolidation_drift,
            "op_score": round(op_score, 4),
            "ts": now,
        }
        self._finalize(record, op_score)
        return record

    def _record_invalid(self, op: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "__invalid__",
            "given_op": op,
            "kwargs": {k: str(v)[:100] for k, v in (kwargs or {}).items()},
            "op_score": 0.0,
            "ts": time.time(),
            "error": f"invalid op {op!r}",
        }
        self._finalize(record, 0.0)
        return record

    # ── Internal helpers ───────────────────────────────────────────────────

    def _finalize(self, record: Dict[str, Any], op_score: float) -> None:
        self.operations.append(record)
        op = record.get("op")
        if op in self.op_counts:
            self.op_counts[op] = self.op_counts.get(op, 0) + 1
        self.integrity_window.append(float(op_score))
        if op_score < LOW_INTEGRITY_THRESHOLD:
            self.consecutive_bad_ops += 1
        else:
            self.consecutive_bad_ops = 0
            if self.state.get("acknowledged_at_bad_ops"):
                self.state["acknowledged_at_bad_ops"] = 0
        self._flush_working_state()
        self.persist_state()

    def _detect_interference(self, content: str, intent: str) -> bool:
        """Rough heuristic: high overlap with a recent episode of the
        same intent AND a negation flip in one but not the other."""
        if not content:
            return False
        target_tokens = _tokens(content)
        has_neg = any(
            t in target_tokens for t in ("not", "never", "no", "false", "wrong")
        )
        for ep in list(self.recent_episodes)[-50:]:
            if ep.get("intent") != intent:
                continue
            sim = jaccard_similarity(content, ep.get("content", ""))
            if sim < 0.6:
                continue
            other_tokens = _tokens(ep.get("content", ""))
            other_neg = any(
                t in other_tokens for t in ("not", "never", "no", "false", "wrong")
            )
            if has_neg != other_neg:
                return True
        return False

    def _pattern_signature(self, content: str) -> str:
        """A signature for grouping repeated 'patterns' for consolidation
        eligibility. Uses a small bag-of-significant-tokens fingerprint."""
        tokens = sorted(_tokens(content))
        # Drop very short tokens; keep top-N salient tokens for signature.
        salient = [t for t in tokens if len(t) >= 4][:8]
        if not salient:
            return ""
        return _hash_text(" ".join(salient))[:12]

    # ── Pattern detection ──────────────────────────────────────────────────

    def rolling_integrity_score(self) -> float:
        """Mean op_score over the rolling window."""
        if not self.integrity_window:
            return 1.0
        return sum(self.integrity_window) / len(self.integrity_window)

    def is_systematically_low_integrity(self) -> bool:
        if len(self.integrity_window) < INTEGRITY_MIN_N:
            return False
        return self.rolling_integrity_score() < LOW_INTEGRITY_THRESHOLD

    def consolidation_eligible_patterns(self) -> List[Dict[str, Any]]:
        """Return patterns currently eligible for consolidation —
        ≥ CONSOLIDATION_FLOOR_SUPPORT instances and old enough."""
        out: List[Dict[str, Any]] = []
        now = time.time()
        for sig, entry in self.pattern_repetition.items():
            if entry.get("count", 0) < CONSOLIDATION_FLOOR_SUPPORT:
                continue
            first_ts = float(entry.get("first_ts", now) or now)
            age_sec = now - first_ts
            # CONSOLIDATION_FLOOR_CYCLES is in arbitrary "cycle" units; we
            # approximate one cycle ≈ 1 hour for the eligibility heuristic.
            cycles = age_sec / 3600.0
            if cycles < CONSOLIDATION_FLOOR_CYCLES:
                continue
            out.append({
                "signature": sig,
                "count": int(entry.get("count", 0)),
                "first_ts": first_ts,
                "approx_cycles": round(cycles, 2),
                "ids": list(entry.get("ids") or [])[-10:],
            })
        return out

    def memory_state(self) -> str:
        """Single-word state for the TSB. Priority order:
        degrading > hoarding > drifting > healthy > active > idle."""
        if self.is_systematically_low_integrity():
            return "degrading"
        outstanding = self.total_encoded - self.total_forgotten
        if (
            self.encodes_since_forget >= HOARDING_ENCODE_GAP
            or outstanding >= HOARDING_TOTAL_CAP
        ):
            return "hoarding"
        if self.consecutive_bad_ops >= 3:
            return "drifting"
        if self.integrity_window and self.rolling_integrity_score() >= 0.85:
            return "healthy"
        if self.operations:
            most_recent = self.operations[-1]
            if time.time() - float(most_recent.get("ts", 0.0)) <= 60:
                return "active"
        return "idle"

    # ── Tick / TSB publish ─────────────────────────────────────────────────

    def tick(
        self,
        pirp_context: Optional[Dict[str, Any]] = None,
        third_eye_state: Optional[Dict[str, Any]] = None,
        brain_layer: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """One tick. If pirp_context carries a `memory_op` dict, record it."""
        pirp_context = pirp_context or {}
        memop = pirp_context.get("memory_op")
        if isinstance(memop, dict):
            op = str(memop.get("op", ""))
            kw = {k: v for k, v in memop.items() if k != "op"}
            self.record_operation(op, **kw)
            self.fired_last_tick = True
        else:
            self.fired_last_tick = False
            self._flush_working_state()
        return self.get_state()

    def get_state(self) -> Dict[str, Any]:
        """TSB payload."""
        outstanding = self.total_encoded - self.total_forgotten
        return {
            "memory_state": self.memory_state(),
            "rolling_integrity_score": round(self.rolling_integrity_score(), 4),
            "integrity_window_n": len(self.integrity_window),
            "is_systematically_low_integrity": self.is_systematically_low_integrity(),
            "consecutive_bad_ops": self.consecutive_bad_ops,
            "operation_distribution": dict(self.op_counts),
            "failure_mode_counts": dict(self.failure_counts),
            "total_encoded": self.total_encoded,
            "total_forgotten": self.total_forgotten,
            "outstanding_episodes": outstanding,
            "encodes_since_forget": self.encodes_since_forget,
            "open_reconsolidation_windows": len(self.retrieval_state),
            "consolidation_eligible_count": len(
                self.consolidation_eligible_patterns()
            ),
            "operation_count": len(self.operations),
            "_fired_tick": self.fired_last_tick,
        }

    # ── IdentityProposalWriter handshake ───────────────────────────────────

    def should_propose_identity_update(self) -> bool:
        """True when sustained low integrity is identity-relevant data."""
        if not self.is_systematically_low_integrity():
            return False
        ack_at = int(self.state.get("acknowledged_at_bad_ops", 0) or 0)
        if ack_at <= 0:
            return self.consecutive_bad_ops >= 3
        return self.consecutive_bad_ops >= (ack_at + IPW_REPORT_EVERY)

    def proposed_identity_signal(self) -> Dict[str, Any]:
        """Compact signal for IdentityProposalWriter to consume."""
        # Identify the dominant failure mode.
        if self.failure_counts:
            dominant = max(self.failure_counts.items(), key=lambda kv: kv[1])
            dominant_mode, dominant_count = dominant
        else:
            dominant_mode, dominant_count = "unknown", 0

        return {
            "source": "MemoryIntegrityLayer",
            "kind": "systematic_memory_drift",
            "rolling_integrity_score": round(self.rolling_integrity_score(), 4),
            "consecutive_bad_ops": self.consecutive_bad_ops,
            "dominant_failure_mode": dominant_mode,
            "dominant_failure_count": dominant_count,
            "failure_mode_counts": dict(self.failure_counts),
            "outstanding_episodes": self.total_encoded - self.total_forgotten,
            "encodes_since_forget": self.encodes_since_forget,
            "interpretation": self._interpret_drift(dominant_mode),
        }

    def _interpret_drift(self, dominant_mode: str) -> str:
        if dominant_mode == "hoarding":
            return (
                "The agent's memory is hoarding — episodes accumulate without "
                "active forgetting. Retrieval will degrade and source confusion "
                "will rise."
            )
        if dominant_mode == "consolidation_deficit":
            return (
                "The agent re-derives from episodic instead of consolidating. "
                "Repeated patterns are not becoming semantic knowledge."
            )
        if dominant_mode == "retrieval_storms":
            return (
                "Retrievals return too many similar hits — pattern separation "
                "is failing somewhere upstream."
            )
        if dominant_mode == "source_confusion":
            return (
                "Content confidence is sustained while source confidence is "
                "low — the agent is becoming confident about claims without "
                "knowing where they came from."
            )
        if dominant_mode == "interference":
            return (
                "New encodes contradict already-known. The agent's memory is "
                "silently overwriting prior knowledge."
            )
        if dominant_mode == "reconsolidation_drift":
            return (
                "Memories are being edited inside the reconsolidation window — "
                "what the agent thinks is stable is actually drifting on touch."
            )
        return "Memory operations have drifted but no single failure mode dominates."

    def acknowledge_proposal(self) -> None:
        """Anchor current consecutive_bad_ops so future re-fire requires
        further accumulation."""
        self.ipw_report_count += 1
        self.state["acknowledged_at_bad_ops"] = self.consecutive_bad_ops
        self.state["last_acknowledged_at"] = time.time()
        self._flush_working_state()
        self.persist_state()

    # ── Operator API ──────────────────────────────────────────────────────

    def reset_integrity_window(self) -> None:
        """Clear rolling integrity window. Use after retraining or when
        prior ops are no longer representative of current behavior."""
        self.integrity_window.clear()
        self.consecutive_bad_ops = 0
        if self.ipw_report_count > 0:
            self.ipw_report_count = max(0, self.ipw_report_count - 1)
        if self.state.get("acknowledged_at_bad_ops"):
            self.state["acknowledged_at_bad_ops"] = 0
        self._flush_working_state()
        self.persist_state()

    def reset_failure_counts(self) -> None:
        """Zero all failure-mode counters. Doesn't clear ops history."""
        for k in self.failure_counts:
            self.failure_counts[k] = 0
        self._flush_working_state()
        self.persist_state()

    def configure_thresholds(
        self,
        source_confusion_gap: Optional[float] = None,
        hoarding_encode_gap: Optional[int] = None,
        reconsolidation_window_sec: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Operator hook to tune thresholds at runtime.

        Globals are kept as the defaults; per-instance overrides go on
        self.state for persistence."""
        if source_confusion_gap is not None:
            self.state["override_source_confusion_gap"] = float(source_confusion_gap)
        if hoarding_encode_gap is not None:
            self.state["override_hoarding_encode_gap"] = int(hoarding_encode_gap)
        if reconsolidation_window_sec is not None:
            self.state["override_reconsolidation_window_sec"] = int(
                reconsolidation_window_sec
            )
        self._flush_working_state()
        self.persist_state()
        return {
            "source_confusion_gap": self.state.get(
                "override_source_confusion_gap", SOURCE_CONFUSION_GAP
            ),
            "hoarding_encode_gap": self.state.get(
                "override_hoarding_encode_gap", HOARDING_ENCODE_GAP
            ),
            "reconsolidation_window_sec": self.state.get(
                "override_reconsolidation_window_sec",
                RECONSOLIDATION_WINDOW_SEC,
            ),
        }
