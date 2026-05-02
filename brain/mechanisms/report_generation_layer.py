"""
brain/mechanisms/report_generation_layer.py — ReportGenerationLayer

Runtime monitor for the agent's report-production act. Pairs with
skills/report-generation/SKILL.md.

The premise:

    A report is a structured persistent artifact for external
    consumption. The act of producing one is where multiple cognitive
    substreams converge — corpus retrieval, memory recall, web
    research, summarization, voice production, confidence calibration.
    Each substream has its own monitor. This layer watches the
    *composition act itself* and the failure modes that emerge only
    when many streams converge: fabrication, citation drift, structure
    collapse, voice drift, hedging stripping, stale publication.

The cognitive science this rests on:

  - Schacter on constructive memory: every act of composition is
    reconstruction; the rebuild can fill in details the source didn't
    have. Foundation for the fabrication detector.
  - Reyna's fuzzy-trace theory: gist and verbatim are dissociable;
    verbatim hedging language must be preserved deliberately or it
    decays. Foundation for hedging_stripped detection.
  - Johnson on source monitoring: knowing where a claim came from is
    dissociable from the claim's content. A report can cite sources
    without those citations actually backing the claims. Direct
    foundation for citation_drift detection.
  - Miller & Cohen on PFC integrative control: structure (sections,
    headings) is the operationalized goal-representation that
    constrains what each section says. Structure collapse is the
    failure of that constraint.
  - Fleming on metacognitive accuracy: a published report can be
    confidently wrong. Stale_publication detection is the safety net
    for the metacognitive miscalibration of the composition act.

What this mechanism does:

  - Tracks per-operation records (draft / revise / publish / retract /
    reflect) with full fidelity-signal payloads.
  - Detects six failure modes:
      * fabrication — specific claims not in any cited source
      * citation_drift — cited sources don't back specific claims
      * structure_collapse — required sections missing or empty
      * voice_drift — voice signature preservation below floor
      * hedging_stripped — source had hedging, report doesn't
      * stale_publication — published report's sources have changed
  - Maintains rolling counters for fabrication-rate, citation-drift-rate,
    structure-failure-rate, voice-drift-rate, hedge-strip-rate.
  - Tracks retract → republish cooldowns (operator hook: caller calls
    record_publish then later record_retract; this layer enforces
    cooldown).
  - Publishes report-state to TSB so other mechanisms (compression,
    voice, memory) can read whether reports are healthy or drifting.
  - Routes sustained dysfunction to IdentityProposalWriter — chronic
    fabrication or hedging_stripped is identity-relevant data.

Citations:
  1. [Schacter 2007, Annu Rev Psychol 58:259-284, PMID 16903806] — The
     cognitive neuroscience of constructive memory. Direct empirical
     foundation for the fabrication detector — every reconstruction
     can fill in details the source didn't have.
  2. [Reyna 2008, Cogn Sci 32(6):975-1014, PMID 21585432] — Fuzzy-
     trace theory and dual-trace memory. Verbatim hedging vs. gist
     dissociation; basis for hedging_stripped as a verbatim-decay
     failure mode under composition.
  3. [Johnson 1993, Psychol Bull 114(1):3-28, PMID 8346328] — Source
     monitoring framework. Empirical foundation for citation_drift —
     knowing-where vs. knowing-what are dissociable, and reports can
     cite sources without those citations actually backing claims.
  4. [Miller 2001, Annu Rev Neurosci 24:167-202, PMID 11283309] — An
     integrative theory of prefrontal cortex function. Structure as
     active goal-representation that constrains downstream
     processing; basis for structure_collapse detection as the
     failure of that constraint.
  5. [Fleming 2014, Phil Trans R Soc B 367(1594):1338-1349, PMID 22492753] —
     The neural basis of metacognitive ability. Confident-but-wrong is
     the predictable failure of metacognitive miscalibration; basis
     for stale_publication detection as the post-hoc safety net.
"""

from brain.base_mechanism import BrainMechanism
import hashlib
import os
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))

__wire_meta__ = {
    "wire": 40,
    "signal": "report_generation",
    "mechanism": "ReportGenerationLayer",
    "reads": [
        "pirp_context.report_op",
    ],
    "writes": [
        "report_state",
        "integrity_score",
        "operation_distribution",
        "failure_mode_counts",
        "active_drafts_count",
        "published_count",
    ],
    "citations": [
        "PMID 16903806",
        "PMID 21585432",
        "PMID 8346328",
        "PMID 11283309",
        "PMID 22492753",
    ],
}

# ── Tuning constants ──────────────────────────────────────────────────────────

VALID_OPS = {"draft", "revise", "publish", "retract", "reflect"}
VALID_REVISION_KINDS = {"section_edit", "add_section", "drop_section"}
VALID_RETRACT_REASONS = {
    "source_changed",
    "factually_wrong",
    "operator_request",
    "superseded_by",
    "safety_concern",
}
VALID_MODES = {"brain", "coach", "build", "default"}

# Fidelity floors — match SKILL.md and the implementation defaults.
VOICE_PRESERVATION_FLOOR = 0.60
HEDGE_PRESERVATION_FLOOR = 0.50
CITATION_DRIFT_RATE_FLOOR = 0.40
FABRICATION_FLOOR = 1  # 1+ specifics not in source = fabrication

# Retract → republish cooldown (in ticks). The agent must wait this
# long after retracting before publishing the same content again.
RETRACT_REPUBLISH_COOLDOWN_TICKS = 200

# Stale-publication sweep window — how long after publish before we
# start watching for stale signals on this report.
STALE_PUBLICATION_GRACE_TICKS = 50

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


class ReportGenerationLayer(BrainMechanism):
    """The agent's report-production monitor. See module docstring."""

    def __init__(self, history_size: int = 200):
        try:
            super().__init__(
                name="ReportGenerationLayer",
                human_analog="composition / publication discipline monitor",
                layer="integration",
            )
        except Exception:
            pass

        self.history_size = history_size

        self.operations: Deque[Dict[str, Any]] = deque(maxlen=history_size)
        self.current_tick: int = 0

        # Active drafts: report_id -> {brief_hash, drafted_tick, mode}
        self.active_drafts: Dict[str, Dict[str, Any]] = {}
        # Published reports: report_id -> {published_tick, content_hash, source_hashes}
        self.published_reports: Dict[str, Dict[str, Any]] = {}
        # Retracted reports + retract tick (for cooldown enforcement).
        self.retracted_at: Dict[str, int] = {}

        # Per-op counters.
        self.op_counts: Dict[str, int] = {k: 0 for k in VALID_OPS}
        # Per-mode at draft time.
        self.mode_counts: Dict[str, int] = {k: 0 for k in VALID_MODES}
        # Failure-mode counters.
        self.failure_counts: Dict[str, int] = {
            "fabrication": 0,
            "citation_drift": 0,
            "structure_collapse": 0,
            "voice_drift": 0,
            "hedging_stripped": 0,
            "stale_publication": 0,
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

        ad = self.state.get("active_drafts")
        if isinstance(ad, dict):
            self.active_drafts = {
                str(k): dict(v) for k, v in ad.items() if isinstance(v, dict)
            }

        pr = self.state.get("published_reports")
        if isinstance(pr, dict):
            self.published_reports = {
                str(k): dict(v) for k, v in pr.items() if isinstance(v, dict)
            }

        ra = self.state.get("retracted_at")
        if isinstance(ra, dict):
            self.retracted_at = {
                str(k): int(v) for k, v in ra.items() if isinstance(v, (int, float))
            }

        oc = self.state.get("op_counts")
        if isinstance(oc, dict):
            for k in VALID_OPS:
                self.op_counts[k] = int(oc.get(k, 0) or 0)

        mc = self.state.get("mode_counts")
        if isinstance(mc, dict):
            for k in VALID_MODES:
                self.mode_counts[k] = int(mc.get(k, 0) or 0)

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
        self.state["active_drafts"] = dict(self.active_drafts)
        self.state["published_reports"] = dict(self.published_reports)
        self.state["retracted_at"] = dict(self.retracted_at)
        self.state["op_counts"] = dict(self.op_counts)
        self.state["mode_counts"] = dict(self.mode_counts)
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
        if op == "publish":
            content_hash = kwargs.get("content_hash")
            if content_hash:
                # Cooldown check: was this hash retracted recently?
                cooldown_at = self.state.get(f"cooldown_until_{content_hash}")
                if cooldown_at and self.current_tick < int(cooldown_at):
                    return True, (
                        f"retract→republish cooldown active until tick "
                        f"{cooldown_at} (current {self.current_tick})"
                    )
        if op == "retract":
            reason = kwargs.get("reason")
            if reason not in VALID_RETRACT_REASONS:
                return True, (
                    f"invalid retract reason {reason!r} "
                    f"(must be one of {sorted(VALID_RETRACT_REASONS)})"
                )
        if self.is_systematically_low_integrity():
            return True, (
                f"sustained low report integrity (rolling score "
                f"{self.rolling_integrity_score():.3f} < "
                f"{LOW_INTEGRITY_THRESHOLD})"
            )
        return False, ""

    # ── Per-op recorders ───────────────────────────────────────────────────

    def record_op(self, op: str, **kwargs: Any) -> Dict[str, Any]:
        if op == "draft":
            return self.record_draft(**kwargs)
        if op == "revise":
            return self.record_revise(**kwargs)
        if op == "publish":
            return self.record_publish(**kwargs)
        if op == "retract":
            return self.record_retract(**kwargs)
        if op == "reflect":
            return self.record_reflect(**kwargs)
        return self._record_invalid(op, kwargs)

    def record_draft(
        self,
        report_id: str = "",
        brief: str = "",
        mode: str = "default",
        section_count: int = 0,
        source_count: int = 0,
        fidelity_signals: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record a draft op. Reads fidelity signals to update failure
        counters."""
        m = mode if mode in VALID_MODES else "default"
        sigs = fidelity_signals or {}

        fabrication = int(sigs.get("fabrication_count", 0) or 0) >= FABRICATION_FLOOR
        citation_drift = float(sigs.get("citation_drift_rate", 0.0) or 0.0) > CITATION_DRIFT_RATE_FLOOR
        structure_complete = bool(sigs.get("structure_complete", True))
        voice_below = bool(sigs.get("voice_below_floor", False))
        hedge_stripped = bool(sigs.get("hedge_stripped", False))

        if fabrication:
            self.failure_counts["fabrication"] += 1
        if citation_drift:
            self.failure_counts["citation_drift"] += 1
        if not structure_complete:
            self.failure_counts["structure_collapse"] += 1
        if voice_below:
            self.failure_counts["voice_drift"] += 1
        if hedge_stripped:
            self.failure_counts["hedging_stripped"] += 1

        # Track active draft.
        if report_id:
            self.active_drafts[report_id] = {
                "brief_hash": _hash_text(brief),
                "drafted_tick": self.current_tick,
                "mode": m,
            }
        self.mode_counts[m] = self.mode_counts.get(m, 0) + 1

        bad = sum([
            fabrication, citation_drift, not structure_complete,
            voice_below, hedge_stripped,
        ])
        op_score = max(0.0, 1.0 - 0.15 * bad)

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "draft",
            "report_id": report_id,
            "brief_hash": _hash_text(brief),
            "mode": m,
            "section_count": int(section_count),
            "source_count": int(source_count),
            "fabrication_flag": fabrication,
            "citation_drift_flag": citation_drift,
            "structure_complete": structure_complete,
            "voice_below_floor": voice_below,
            "hedge_stripped": hedge_stripped,
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_revise(
        self,
        report_id: str = "",
        kind: str = "section_edit",
        section_name: str = "",
        reason: str = "",
        fidelity_signals: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        kind_ok = kind in VALID_REVISION_KINDS
        sigs = fidelity_signals or {}

        # Optional re-check of fidelity after revision.
        fabrication = int(sigs.get("fabrication_count", 0) or 0) >= FABRICATION_FLOOR
        citation_drift = float(sigs.get("citation_drift_rate", 0.0) or 0.0) > CITATION_DRIFT_RATE_FLOOR

        if fabrication:
            self.failure_counts["fabrication"] += 1
        if citation_drift:
            self.failure_counts["citation_drift"] += 1

        bad = sum([not kind_ok, fabrication, citation_drift])
        op_score = max(0.0, 1.0 - 0.20 * bad)

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "revise",
            "report_id": report_id,
            "kind": kind,
            "kind_ok": kind_ok,
            "section_name": section_name,
            "fabrication_flag": fabrication,
            "citation_drift_flag": citation_drift,
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_publish(
        self,
        report_id: str = "",
        content_hash: str = "",
        source_hashes: Optional[List[str]] = None,
        output_path: str = "",
    ) -> Dict[str, Any]:
        """Record a publish op. Stores content/source hashes for stale-
        publication detection on subsequent ticks."""
        # Only allow publishing if there's a corresponding draft.
        draft_known = report_id in self.active_drafts

        if draft_known:
            self.active_drafts.pop(report_id, None)
            self.published_reports[report_id] = {
                "published_tick": self.current_tick,
                "content_hash": content_hash,
                "source_hashes": list(source_hashes or []),
                "output_path": output_path,
            }

        op_score = 1.0 if draft_known else 0.5

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "publish",
            "report_id": report_id,
            "draft_known": draft_known,
            "content_hash": content_hash,
            "source_count": len(source_hashes or []),
            "output_path": output_path,
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_retract(
        self,
        report_id: str = "",
        reason: str = "",
    ) -> Dict[str, Any]:
        valid_reason = reason in VALID_RETRACT_REASONS
        report_known = report_id in self.published_reports
        accepted = valid_reason and report_known

        if accepted:
            # Set cooldown for the retracted content_hash.
            content_hash = self.published_reports[report_id].get("content_hash", "")
            if content_hash:
                self.state[f"cooldown_until_{content_hash}"] = (
                    self.current_tick + RETRACT_REPUBLISH_COOLDOWN_TICKS
                )
            self.retracted_at[report_id] = self.current_tick
            # Remove from published — it's no longer authoritative.
            self.published_reports.pop(report_id, None)

        bad = sum([not valid_reason, not report_known])
        # A justified retraction is itself a healthy op.
        op_score = 1.0 if accepted else max(0.0, 1.0 - 0.30 * bad)

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "retract",
            "report_id": report_id,
            "reason": reason,
            "valid_reason": valid_reason,
            "report_known": report_known,
            "accepted": accepted,
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_reflect(
        self,
        report_id: str = "",
        fit: bool = True,
        actual_outcome: Optional[float] = None,
        notes_present: bool = False,
    ) -> Dict[str, Any]:
        # Reflect can target both published and retracted reports — both
        # are valid reflection targets.
        report_known = (
            report_id in self.published_reports or report_id in self.retracted_at
        )
        substantive = bool(notes_present) or actual_outcome is not None

        bad = sum([not report_known, not substantive])
        op_score = max(0.0, 1.0 - 0.20 * bad)

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "reflect",
            "report_id": report_id,
            "report_known": report_known,
            "fit": bool(fit),
            "actual_outcome": (
                round(float(actual_outcome), 4)
                if actual_outcome is not None else None
            ),
            "substantive": substantive,
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_stale_publication(
        self,
        report_id: str,
        reason: str = "source_content_drift",
    ) -> None:
        """External hook: when downstream retrieval detects that a
        published report's source content has changed, increment the
        stale_publication counter."""
        if report_id in self.published_reports:
            self.failure_counts["stale_publication"] += 1
            self.published_reports[report_id]["stale_flag"] = reason
            self.published_reports[report_id]["stale_since_tick"] = self.current_tick
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

    # ── Pattern detection / state ──────────────────────────────────────────

    def rolling_integrity_score(self) -> float:
        if not self.integrity_window:
            return 1.0
        return sum(self.integrity_window) / len(self.integrity_window)

    def is_systematically_low_integrity(self) -> bool:
        if len(self.integrity_window) < INTEGRITY_MIN_N:
            return False
        return self.rolling_integrity_score() < LOW_INTEGRITY_THRESHOLD

    def stale_published_count(self) -> int:
        return sum(
            1 for v in self.published_reports.values()
            if v.get("stale_flag")
        )

    def report_state(self) -> str:
        """Single-word state for TSB. Priority:
        degrading > stale_pile > drafting > publishing > retracted > active > idle."""
        if self.is_systematically_low_integrity():
            return "degrading"
        if self.stale_published_count() >= 2:
            return "stale_pile"
        if self.operations:
            recent = self.operations[-1]
            recent_op = recent.get("op")
            if recent_op == "draft":
                return "drafting"
            if recent_op == "publish":
                return "publishing"
            if recent_op == "retract":
                return "retracted"
            if time.time() - float(recent.get("ts", 0.0)) <= 60:
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

        op_payload = pirp_context.get("report_op")
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
        return {
            "report_state": self.report_state(),
            "rolling_integrity_score": round(self.rolling_integrity_score(), 4),
            "integrity_window_n": len(self.integrity_window),
            "is_systematically_low_integrity": self.is_systematically_low_integrity(),
            "consecutive_bad_ops": self.consecutive_bad_ops,
            "operation_distribution": dict(self.op_counts),
            "mode_distribution": dict(self.mode_counts),
            "failure_mode_counts": dict(self.failure_counts),
            "active_drafts_count": len(self.active_drafts),
            "published_count": len(self.published_reports),
            "retracted_count": len(self.retracted_at),
            "stale_published_count": self.stale_published_count(),
            "current_tick": self.current_tick,
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
            "source": "ReportGenerationLayer",
            "kind": "report_generation_drift",
            "rolling_integrity_score": round(self.rolling_integrity_score(), 4),
            "consecutive_bad_ops": self.consecutive_bad_ops,
            "dominant_failure_mode": dominant_mode,
            "dominant_failure_count": dominant_count,
            "failure_mode_counts": dict(self.failure_counts),
            "active_drafts_count": len(self.active_drafts),
            "published_count": len(self.published_reports),
            "stale_published_count": self.stale_published_count(),
            "interpretation": self._interpret_drift(dominant_mode),
        }

    def _interpret_drift(self, dominant: str) -> str:
        if dominant == "fabrication":
            return (
                "Reports are containing specific claims that aren't in any "
                "cited source. The composition act is filling in details "
                "the sources didn't have — the most serious report failure."
            )
        if dominant == "citation_drift":
            return (
                "Reports cite sources but the specific claims don't trace "
                "back to them. Citation theater — the bibliography looks "
                "right; the reasoning doesn't."
            )
        if dominant == "structure_collapse":
            return (
                "Reports aren't honoring the requested structure — sections "
                "missing or empty. The goal-representation isn't holding."
            )
        if dominant == "voice_drift":
            return (
                "Voice signatures aren't surviving into report bodies. The "
                "agent slips into a flatter 'report voice' that drops "
                "anchored phrasing."
            )
        if dominant == "hedging_stripped":
            return (
                "Source material had qualifier language that the report "
                "stripped. Confidence laundering at the composition layer."
            )
        if dominant == "stale_publication":
            return (
                "Published reports are accumulating stale flags — source "
                "material has changed without the reports being retracted "
                "or revised."
            )
        return "Report production has drifted but no single failure mode dominates."

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

    def clear_cooldowns(self) -> None:
        """Operator hook: clear all retract→republish cooldowns. Use
        after a deliberate content rewrite where the prior cooldown no
        longer applies."""
        for key in list(self.state.keys()):
            if key.startswith("cooldown_until_"):
                self.state.pop(key, None)
        self._flush_working_state()
        self.persist_state()

    def clear_stale_flags(self) -> None:
        """Operator hook: clear stale_flag on all published reports.
        Use after an audit confirms sources have NOT changed."""
        for v in self.published_reports.values():
            if "stale_flag" in v:
                v.pop("stale_flag", None)
                v.pop("stale_since_tick", None)
        self._flush_working_state()
        self.persist_state()
