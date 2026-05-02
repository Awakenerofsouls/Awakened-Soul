"""
brain/mechanisms/corpus_retrieval_layer.py — CorpusRetrievalLayer

The runtime monitor for the agent's personal-corpus retrieval acts.
Pairs with skills/qmd/SKILL.md.

The premise:

    The agent has a substantial written record — journals, dreams,
    identity files, revision logs, proposals, private entries. When
    the agent retrieves from that record, the retrieval is itself an
    act with provenance. This layer watches retrieval cadence, mode
    distribution, per-doc-type concentration, stale-index events,
    dream-contaminated hit rate, and same-query loops — and surfaces
    sustained patterns through the IPW handshake.

The cognitive-architecture this rests on:

  - Tulving on episodic vs. semantic memory: retrieval mode varies by
    what's being remembered. Specific dated entries (journal) want
    BM25; abstracted self-knowledge (identity files) wants different
    treatment. Mode mix tells us about the kind of remembering the
    agent is doing.
  - Johnson on source monitoring: source confidence is not the same
    as content confidence. Per-doc-type confidence on every hit lets
    the rest of the brain reason correctly about what kind of evidence
    a recalled fragment is.
  - Schacter on constructive memory: every retrieval is a
    reconstruction. Routing through MemoryIntegrityLayer ensures
    reconsolidation windows open on each hit so that re-writes during
    the window can be detected.
  - Squire on hippocampal pattern separation: similar episodes need
    to remain distinguishable. Same-query loops on different days are
    the agent failing to distinguish; the loop detector flags it.
  - Hardt et al. on active forgetting: a corpus that only grows is
    a corpus that drifts toward unfindable. Stale-index detection is
    the upstream of the same maintenance pressure.

What this mechanism does:

  - Tracks per-operation records (search / vsearch / hybrid / get /
    index / record_retrieval).
  - Detects six failure modes:
      * stale_index — index older than corpus mtime, retrieval ran anyway
      * retrieval_storm — too many retrievals in a short window
      * same_query_loop — same query repeated within window with no
        intervening write op
      * dream_concentration — sustained high fraction of hits from
        DREAMS.md (or other low-confidence types)
      * sourceless_retrieval — claims attributed to corpus but no
        record_retrieval call observed
      * mode_imbalance — agent only ever uses one mode (e.g. always
        BM25, never vsearch) when a balanced mix would serve better
  - Maintains rolling counters for retrieval cadence + mode distribution.
  - Publishes corpus state to the TSB so other mechanisms can read
    whether the agent is actively recalling, ruminating, or drifting.
  - Routes sustained dysfunction to IdentityProposalWriter — chronic
    same_query_loop or dream_concentration is identity-relevant.

Citations:
  1. [Tulving 2002, Annu Rev Psychol 53:1-25, PMID 11752477] —
     Episodic memory: from mind to brain. Foundation for treating
     retrieval mode as a function of what kind of memory is being
     accessed (event vs. abstracted knowledge).
  2. [Johnson 1993, Psychol Bull 114(1):3-28, PMID 8346328] —
     Source monitoring. Empirical basis for tracking source
     confidence as a separate axis from content confidence; the
     per-doc-type confidence map is direct application.
  3. [Schacter 2007, Annu Rev Psychol 58:259-284, PMID 16903806] —
     The cognitive neuroscience of constructive memory. Every
     retrieval is reconstruction — basis for opening a
     reconsolidation window on each hit and watching for content
     edits during the window.
  4. [Squire 2011, Neuron 70(4):589-595, PMID 21609818] — The legacy
     of patient H.M. for memory science. Pattern separation /
     hippocampus role; basis for treating same_query_loop as a
     pattern-separation failure rather than just repetition.
  5. [Hardt 2013, Trends Cogn Sci 17(3):111-120, PMID 23369831] —
     Decay happens: the role of active forgetting in memory. Same
     citation as MemoryIntegrityLayer — the maintenance pressure on
     a corpus is the same as the maintenance pressure on episodic
     memory; stale-index detection is one face of it.
"""

from brain.base_mechanism import BrainMechanism
import hashlib
import os
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))

__wire_meta__ = {
    "wire": 37,
    "signal": "corpus_retrieval",
    "mechanism": "CorpusRetrievalLayer",
    "reads": [
        "pirp_context.corpus_op",
    ],
    "writes": [
        "corpus_state",
        "integrity_score",
        "operation_distribution",
        "mode_distribution",
        "doc_type_distribution",
        "failure_mode_counts",
    ],
    "citations": [
        "PMID 11752477",
        "PMID 8346328",
        "PMID 16903806",
        "PMID 21609818",
        "PMID 23369831",
    ],
}

# ── Tuning constants ──────────────────────────────────────────────────────────

VALID_OPS = {"search", "vsearch", "hybrid", "get", "index", "record_retrieval"}
VALID_MODES = {"search", "vsearch", "hybrid", "get"}

DOC_TYPES = {
    "identity_anchored",
    "epistemic",
    "personality",
    "aesthetic_drives",
    "revision_log",
    "proposals",
    "becoming",
    "journal",
    "private",
    "overnight",
    "dreams",
    "external",
}

# Storm: this many retrievals in this many ticks.
STORM_THRESHOLD = 8
STORM_WINDOW_TICKS = 50

# Same-query loop: same query string repeated this many times within
# this many seconds.
SAME_QUERY_LOOP_THRESHOLD = 3
SAME_QUERY_LOOP_WINDOW_SEC = 600  # 10 minutes

# Dream-concentration: fraction of recent hits that are from DREAMS.md
# (or other low-confidence types) above this is sustained dream-leaning.
DREAM_CONCENTRATION_THRESHOLD = 0.5
DREAM_CONCENTRATION_MIN_HITS = 10
LOW_CONFIDENCE_TYPES = {"dreams", "external"}

# Mode imbalance: ratio of any single mode > this when total ops above N.
MODE_IMBALANCE_RATIO = 0.85
MODE_IMBALANCE_MIN_OPS = 10

# Integrity floor.
LOW_INTEGRITY_THRESHOLD = 0.55
INTEGRITY_MIN_N = 6
INTEGRITY_WINDOW = 30

# IPW: re-fire only after this many additional bad ops past anchor.
IPW_REPORT_EVERY = 4


def _hash_text(text: str) -> str:
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ── Mechanism ─────────────────────────────────────────────────────────────────


class CorpusRetrievalLayer(BrainMechanism):
    """Personal-corpus retrieval monitor. See module docstring."""

    def __init__(self, history_size: int = 200):
        try:
            super().__init__(
                name="CorpusRetrievalLayer",
                human_analog="hippocampal recall + source monitoring layer",
                layer="integration",
            )
        except Exception:
            pass

        self.history_size = history_size

        self.operations: Deque[Dict[str, Any]] = deque(maxlen=history_size)
        self.current_tick: int = 0

        # Storm + same-query tracking.
        self.retrieval_ticks: Deque[int] = deque(maxlen=STORM_THRESHOLD * 4)
        # query_hash -> deque of timestamps
        self.query_history: Dict[str, Deque[float]] = {}
        # query_hash -> tick of the first hit in the current rolling window
        # (used to compare against last_write_tick for same-query-loop gating).
        self._first_tick_for_query: Dict[str, int] = {}
        # Tick of last write/act op (any non-retrieval) to gate same-query loop.
        self.last_write_tick: int = 0

        # Per-mode + per-doc-type counters.
        self.mode_counts: Dict[str, int] = {k: 0 for k in VALID_MODES}
        self.doc_type_hits: Dict[str, int] = {k: 0 for k in DOC_TYPES}
        self.recent_hit_types: Deque[str] = deque(
            maxlen=DREAM_CONCENTRATION_MIN_HITS * 4
        )

        # Per-op counters.
        self.op_counts: Dict[str, int] = {k: 0 for k in VALID_OPS}
        # Failure-mode counters.
        self.failure_counts: Dict[str, int] = {
            "stale_index": 0,
            "retrieval_storm": 0,
            "same_query_loop": 0,
            "dream_concentration": 0,
            "sourceless_retrieval": 0,
            "mode_imbalance": 0,
        }

        # Integrity rolling.
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

        rt = self.state.get("retrieval_ticks")
        if isinstance(rt, list):
            for v in rt[-(STORM_THRESHOLD * 4):]:
                try:
                    self.retrieval_ticks.append(int(v))
                except (TypeError, ValueError):
                    continue

        qh = self.state.get("query_history")
        if isinstance(qh, dict):
            for k, v in qh.items():
                if isinstance(v, list):
                    self.query_history[str(k)] = deque(
                        (float(x) for x in v if isinstance(x, (int, float))),
                        maxlen=SAME_QUERY_LOOP_THRESHOLD * 4,
                    )

        ftq = self.state.get("_first_tick_for_query")
        if isinstance(ftq, dict):
            self._first_tick_for_query = {
                str(k): int(v) for k, v in ftq.items()
                if isinstance(v, (int, float))
            }

        self.last_write_tick = int(
            self.state.get("last_write_tick", 0) or 0
        )

        mc = self.state.get("mode_counts")
        if isinstance(mc, dict):
            for k in VALID_MODES:
                self.mode_counts[k] = int(mc.get(k, 0) or 0)

        dh = self.state.get("doc_type_hits")
        if isinstance(dh, dict):
            for k in DOC_TYPES:
                self.doc_type_hits[k] = int(dh.get(k, 0) or 0)

        rht = self.state.get("recent_hit_types")
        if isinstance(rht, list):
            for t in rht[-(DREAM_CONCENTRATION_MIN_HITS * 4):]:
                if isinstance(t, str):
                    self.recent_hit_types.append(t)

        oc = self.state.get("op_counts")
        if isinstance(oc, dict):
            for k in VALID_OPS:
                self.op_counts[k] = int(oc.get(k, 0) or 0)

        fc = self.state.get("failure_counts")
        if isinstance(fc, dict):
            for k in self.failure_counts:
                self.failure_counts[k] = int(fc.get(k, 0) or 0)

        self.current_tick = int(self.state.get("current_tick", 0) or 0)

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
        self.state["retrieval_ticks"] = list(self.retrieval_ticks)
        self.state["query_history"] = {
            k: list(v) for k, v in self.query_history.items()
        }
        self.state["_first_tick_for_query"] = dict(self._first_tick_for_query)
        self.state["last_write_tick"] = self.last_write_tick
        self.state["mode_counts"] = dict(self.mode_counts)
        self.state["doc_type_hits"] = dict(self.doc_type_hits)
        self.state["recent_hit_types"] = list(self.recent_hit_types)
        self.state["op_counts"] = dict(self.op_counts)
        self.state["failure_counts"] = dict(self.failure_counts)
        self.state["current_tick"] = self.current_tick
        self.state["integrity_window"] = list(self.integrity_window)
        self.state["consecutive_bad_ops"] = self.consecutive_bad_ops
        self.state["ipw_report_count"] = self.ipw_report_count
        self.state["last_updated"] = time.time()

    # ── Public API ─────────────────────────────────────────────────────────

    def should_block(self, op: str, **kwargs: Any) -> Tuple[bool, str]:
        if op not in VALID_OPS:
            return True, f"invalid op {op!r} (must be one of {sorted(VALID_OPS)})"

        if op in VALID_MODES and op != "get":
            if self._storm_active():
                return True, (
                    f"retrieval storm — ≥{STORM_THRESHOLD} retrievals in last "
                    f"{STORM_WINDOW_TICKS} ticks"
                )

        if self.is_systematically_low_integrity():
            return True, (
                f"sustained low corpus-retrieval integrity (rolling "
                f"score {self.rolling_integrity_score():.3f} < "
                f"{LOW_INTEGRITY_THRESHOLD})"
            )

        return False, ""

    # ── Per-op recorders ───────────────────────────────────────────────────

    def record_op(self, op: str, **kwargs: Any) -> Dict[str, Any]:
        """Generic dispatch."""
        if op in VALID_MODES:
            return self.record_retrieval(mode=op, **kwargs)
        if op == "index":
            return self.record_index(**kwargs)
        if op == "record_retrieval":
            return self.record_retrieval(**kwargs)
        return self._record_invalid(op, kwargs)

    def record_retrieval(
        self,
        mode: str = "search",
        query: str = "",
        n_hits: int = 0,
        hit_doc_types: Optional[List[str]] = None,
        stale_index: bool = False,
        dream_contaminated_hits: int = 0,
    ) -> Dict[str, Any]:
        """Record a retrieval op."""
        mode_ok = mode in VALID_MODES
        if not mode_ok:
            mode = "search"

        # Storm tracking (only retrieval modes count, not 'get').
        if mode != "get":
            self.retrieval_ticks.append(self.current_tick)
        storming = self._storm_active()
        if storming:
            self.failure_counts["retrieval_storm"] += 1

        # Same-query loop tracking. Each entry stores (timestamp, tick) so
        # we can compare against last_write_tick.
        qhash = _hash_text(query) if query else ""
        loop_detected = False
        if qhash and mode != "get":
            now = time.time()
            dq = self.query_history.setdefault(
                qhash, deque(maxlen=SAME_QUERY_LOOP_THRESHOLD * 4)
            )
            cutoff = now - SAME_QUERY_LOOP_WINDOW_SEC
            while dq and dq[0] < cutoff:
                dq.popleft()
            dq.append(now)
            # Loop = repeated more than threshold AND there has been no
            # write op SINCE the first hit in the current window. We compare
            # in tick space — the deque stores wall ts; we need the first
            # tick separately. Use a parallel tick tracker.
            tick_dq = self._first_tick_for_query.setdefault(qhash, self.current_tick)
            # Reset first-tick anchor when the window has rolled (no entries
            # remain, or all entries are within new window after popping).
            if len(dq) == 1:
                self._first_tick_for_query[qhash] = self.current_tick
                tick_dq = self.current_tick
            # No write since first hit: write_tick is at or before first hit.
            no_write_since_first = self.last_write_tick <= tick_dq
            if len(dq) > SAME_QUERY_LOOP_THRESHOLD and no_write_since_first:
                loop_detected = True
                self.failure_counts["same_query_loop"] += 1

        # Stale-index counter.
        if stale_index:
            self.failure_counts["stale_index"] += 1

        # Mode + doc-type bookkeeping.
        self.mode_counts[mode] = self.mode_counts.get(mode, 0) + 1
        for dt in (hit_doc_types or []):
            if dt in DOC_TYPES:
                self.doc_type_hits[dt] = self.doc_type_hits.get(dt, 0) + 1
                self.recent_hit_types.append(dt)
            else:
                self.doc_type_hits["external"] = self.doc_type_hits.get("external", 0) + 1
                self.recent_hit_types.append("external")

        # Dream-concentration check (population pattern).
        dream_concentrated = self._dream_concentration_active()
        if dream_concentrated and not self.state.get("dream_conc_recorded"):
            self.failure_counts["dream_concentration"] += 1
            self.state["dream_conc_recorded"] = True
        elif not dream_concentrated and self.state.get("dream_conc_recorded"):
            self.state.pop("dream_conc_recorded", None)

        # Mode imbalance (population pattern).
        imbalanced = self._mode_imbalance_active()
        if imbalanced and not self.state.get("mode_imbalance_recorded"):
            self.failure_counts["mode_imbalance"] += 1
            self.state["mode_imbalance_recorded"] = True
        elif not imbalanced and self.state.get("mode_imbalance_recorded"):
            self.state.pop("mode_imbalance_recorded", None)

        bad = sum([
            not mode_ok,
            stale_index,
            loop_detected,
            storming,
        ])
        op_score = max(0.0, 1.0 - 0.20 * bad)

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": mode,
            "query_hash": qhash,
            "n_hits": int(max(0, n_hits)),
            "hit_doc_types": list(hit_doc_types or [])[:10],
            "stale_index": stale_index,
            "dream_contaminated_hits": int(max(0, dream_contaminated_hits)),
            "retrieval_storm": storming,
            "same_query_loop": loop_detected,
            "dream_concentration_active": dream_concentrated,
            "mode_imbalance_active": imbalanced,
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_index(
        self,
        full: bool = True,
        added: int = 0,
        updated: int = 0,
        removed: int = 0,
    ) -> Dict[str, Any]:
        """Record an index/update op. This is a 'write' from the corpus
        layer's perspective — it counts as activity that breaks the
        same-query loop chain."""
        self.last_write_tick = self.current_tick
        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "index",
            "full": bool(full),
            "added": int(added),
            "updated": int(updated),
            "removed": int(removed),
            "op_score": 1.0,
            "ts": time.time(),
        }
        self._finalize(record, 1.0)
        return record

    def record_sourceless_retrieval(self, n: int = 1) -> None:
        """External hook: increment when an output is observed making
        claims attributed to the corpus that have no record_retrieval
        call backing them."""
        n = int(max(0, n))
        self.failure_counts["sourceless_retrieval"] += n
        self._flush_working_state()
        self.persist_state()

    def note_write_activity(self) -> None:
        """External hook: any non-retrieval op the agent took (write,
        revision commit, journal append) breaks the same-query loop
        chain. Heartbeat / brain core can call this to keep the loop
        detector accurate."""
        self.last_write_tick = self.current_tick
        self._flush_working_state()
        self.persist_state()

    def _record_invalid(self, op: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "__invalid__",
            "given_op": op,
            "kwargs": {k: str(v)[:80] for k, v in (kwargs or {}).items()},
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
        # Only count real op kinds in op_counts — not __invalid__.
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

    def _storm_active(self) -> bool:
        if not self.retrieval_ticks:
            return False
        cut = self.current_tick - STORM_WINDOW_TICKS
        recent = [t for t in self.retrieval_ticks if t >= cut]
        return len(recent) >= STORM_THRESHOLD

    def _dream_concentration_active(self) -> bool:
        if len(self.recent_hit_types) < DREAM_CONCENTRATION_MIN_HITS:
            return False
        low_hits = sum(
            1 for t in self.recent_hit_types if t in LOW_CONFIDENCE_TYPES
        )
        rate = low_hits / max(1, len(self.recent_hit_types))
        return rate >= DREAM_CONCENTRATION_THRESHOLD

    def _mode_imbalance_active(self) -> bool:
        total = sum(self.mode_counts.get(k, 0) for k in VALID_MODES if k != "get")
        if total < MODE_IMBALANCE_MIN_OPS:
            return False
        # Check max-mode share excluding 'get'.
        non_get = {k: v for k, v in self.mode_counts.items() if k != "get"}
        if not non_get:
            return False
        peak = max(non_get.values()) / max(1, total)
        return peak >= MODE_IMBALANCE_RATIO

    # ── Pattern detection / state ──────────────────────────────────────────

    def rolling_integrity_score(self) -> float:
        if not self.integrity_window:
            return 1.0
        return sum(self.integrity_window) / len(self.integrity_window)

    def is_systematically_low_integrity(self) -> bool:
        if len(self.integrity_window) < INTEGRITY_MIN_N:
            return False
        return self.rolling_integrity_score() < LOW_INTEGRITY_THRESHOLD

    def corpus_state(self) -> str:
        """Single-word state for TSB. Priority order:
        degrading > storming > looping > dream_leaning > stale > active > idle."""
        if self.is_systematically_low_integrity():
            return "degrading"
        if self._storm_active():
            return "storming"
        if any(
            (rec.get("op") in VALID_MODES and rec.get("same_query_loop"))
            for rec in list(self.operations)[-3:]
        ):
            return "looping"
        if self._dream_concentration_active():
            return "dream_leaning"
        if any(
            rec.get("stale_index") for rec in list(self.operations)[-3:]
            if rec.get("op") in VALID_MODES
        ):
            return "stale"
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
        self.current_tick += 1
        pirp_context = pirp_context or {}
        op_payload = pirp_context.get("corpus_op")
        if isinstance(op_payload, dict):
            op = str(op_payload.get("op", ""))
            kw = {k: v for k, v in op_payload.items() if k != "op"}
            self.record_op(op, **kw)
            self.fired_last_tick = True
        else:
            self.fired_last_tick = False
            self._flush_working_state()
            self.persist_state()
        return self.get_state()

    def get_state(self) -> Dict[str, Any]:
        # Per-mode rate (excluding 'get').
        non_get_total = sum(
            self.mode_counts.get(k, 0) for k in VALID_MODES if k != "get"
        )
        mode_rate = {
            k: (self.mode_counts.get(k, 0) / max(1, non_get_total))
            for k in VALID_MODES if k != "get"
        }
        total_hits = sum(self.doc_type_hits.values()) or 1
        doc_rate = {
            k: round(self.doc_type_hits.get(k, 0) / total_hits, 4)
            for k in DOC_TYPES
        }
        return {
            "corpus_state": self.corpus_state(),
            "rolling_integrity_score": round(self.rolling_integrity_score(), 4),
            "integrity_window_n": len(self.integrity_window),
            "is_systematically_low_integrity": self.is_systematically_low_integrity(),
            "consecutive_bad_ops": self.consecutive_bad_ops,
            "operation_distribution": dict(self.op_counts),
            "mode_distribution": {k: round(v, 4) for k, v in mode_rate.items()},
            "doc_type_distribution": doc_rate,
            "failure_mode_counts": dict(self.failure_counts),
            "storm_active": self._storm_active(),
            "dream_concentration_active": self._dream_concentration_active(),
            "mode_imbalance_active": self._mode_imbalance_active(),
            "current_tick": self.current_tick,
            "last_write_tick": self.last_write_tick,
            "operation_count": len(self.operations),
            "_fired_tick": self.fired_last_tick,
        }

    # ── IdentityProposalWriter handshake ───────────────────────────────────

    def should_propose_identity_update(self) -> bool:
        if not self.is_systematically_low_integrity():
            return False
        ack_at = int(self.state.get("acknowledged_at_bad_ops", 0) or 0)
        if ack_at <= 0:
            return self.consecutive_bad_ops >= 3
        return self.consecutive_bad_ops >= (ack_at + IPW_REPORT_EVERY)

    def proposed_identity_signal(self) -> Dict[str, Any]:
        if self.failure_counts:
            dominant = max(self.failure_counts.items(), key=lambda kv: kv[1])
            dominant_mode, dominant_count = dominant
        else:
            dominant_mode, dominant_count = "unknown", 0

        return {
            "source": "CorpusRetrievalLayer",
            "kind": "corpus_retrieval_drift",
            "rolling_integrity_score": round(self.rolling_integrity_score(), 4),
            "consecutive_bad_ops": self.consecutive_bad_ops,
            "dominant_failure_mode": dominant_mode,
            "dominant_failure_count": dominant_count,
            "failure_mode_counts": dict(self.failure_counts),
            "interpretation": self._interpret_drift(dominant_mode),
        }

    def _interpret_drift(self, dominant: str) -> str:
        if dominant == "stale_index":
            return (
                "Corpus retrievals are running against a stale index. "
                "The agent is recalling from an outdated picture of its "
                "own record."
            )
        if dominant == "retrieval_storm":
            return (
                "Retrieval cadence is too high. The agent is searching "
                "the corpus more than acting on it."
            )
        if dominant == "same_query_loop":
            return (
                "The agent is repeating the same query against the corpus "
                "without writing or acting in between. A pattern-separation "
                "failure or stuck loop."
            )
        if dominant == "dream_concentration":
            return (
                "A high fraction of retrieved hits are from low-confidence "
                "sources (DREAMS.md, external). The agent is leaning on "
                "evidence that's known to be unreliable."
            )
        if dominant == "sourceless_retrieval":
            return (
                "Outputs are making corpus-attributed claims without a "
                "matching record_retrieval call. The provenance signal is "
                "broken."
            )
        if dominant == "mode_imbalance":
            return (
                "The agent only ever uses one retrieval mode. BM25 and "
                "vector serve different cognitive purposes; using only one "
                "limits what the agent can recall."
            )
        return "Corpus retrieval has drifted but no single failure mode dominates."

    def acknowledge_proposal(self) -> None:
        self.ipw_report_count += 1
        self.state["acknowledged_at_bad_ops"] = self.consecutive_bad_ops
        self.state["last_acknowledged_at"] = time.time()
        self._flush_working_state()
        self.persist_state()

    # ── Operator API ──────────────────────────────────────────────────────

    def reset_integrity_window(self) -> None:
        self.integrity_window.clear()
        self.consecutive_bad_ops = 0
        if self.ipw_report_count > 0:
            self.ipw_report_count = max(0, self.ipw_report_count - 1)
        if self.state.get("acknowledged_at_bad_ops"):
            self.state["acknowledged_at_bad_ops"] = 0
        self._flush_working_state()
        self.persist_state()

    def reset_failure_counts(self) -> None:
        for k in self.failure_counts:
            self.failure_counts[k] = 0
        self._flush_working_state()
        self.persist_state()

    def reset_query_history(self) -> None:
        """Operator hook to clear same-query loop tracking — used after
        a deliberate corpus reorganization or operator-initiated reset."""
        self.query_history.clear()
        self._first_tick_for_query.clear()
        self._flush_working_state()
        self.persist_state()
