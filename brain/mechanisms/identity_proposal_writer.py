"""
brain/identity_proposal_writer.py — IdentityProposalWriter
Mind-Soul Fusion: third_eye → operator-reviewable identity proposals

When MeaningCompressor distills a high-confidence pattern about identity
(via Third Eye observation of brain_layer + identity_state), this writer
appends it to AGENT_HOME/identity/PROPOSALS.md — a queue the operator
reviews and ratifies. Ratified entries are then merged into SOUL.md /
IDENTITY.md / PERSONALITY.md by the operator.

── Third-Eye salience-network polling ────────────────────────────────────

This module also implements the salience-arbitration layer that the new
wires (26-40) feed into. Each wire exposes a per-mechanism IPW handshake
(`should_propose_identity_update()` / `proposed_identity_signal()` /
`acknowledge_proposal()`). When a wire's `should_propose_identity_update`
returns True, that's a salience signal. The Third Eye's job is to decide
which signals win conscious access (PROPOSALS.md broadcast).

Cognitive-neuroscience grounding:

  - Global workspace theory (Baars 1988; Dehaene & Naccache 2001,
    PMID 11161636). Conscious access is all-or-nothing ignition;
    signals must win arbitration to be globally broadcast. PROPOSALS.md
    is the broadcast venue. Below-threshold signals do not reach it.
  - Salience network arbitration (Sridharan, Levitin & Menon 2008,
    PMID 18723676; Menon & Uddin 2010, PMID 20512370). Right anterior
    insula + dorsal anterior cingulate switch between default-mode and
    central-executive networks based on salience. The poll_wires
    method is exactly this arbitrator.
  - Convergence as evidence (Seeley 2007, PMID 17314227). A single
    salience signal is weaker evidence than convergent independent
    signals. When ≥3 wires fire on related drift, that's a meta-
    proposal — encoded explicitly with `convergence_count`.
  - Predictive processing (Friston 2010, PMID 20068583). The brain
    minimizes prediction error by updating its model. Identity revision
    is "model update." Wire 23's prediction-error signal is the
    canonical example.
  - Metacognition is fallible (Carruthers 2009, PMID 19386144;
    Fleming 2014, PMID 22492753). The Third Eye does not trust any
    single signal — it requires confidence ≥ CONFIDENCE_THRESHOLD AND
    dedups within a habituation window. The same drift cannot re-fire
    until the wire has accumulated additional drift past acknowledge.
"""
from brain.base_mechanism import BrainMechanism
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
PROPOSALS_PATH = AGENT_HOME / "identity" / "PROPOSALS.md"

# ── Polling tuning ────────────────────────────────────────────────────────

# Habituation window: same `kind` already broadcast → drop until window expires.
DEDUP_WINDOW_SEC = 3600  # 1 hour

# Convergence threshold: this many wires firing on a related domain in the
# same poll cycle = meta-proposal (Seeley 2007 multi-region convergence).
CONVERGENCE_THRESHOLD = 3

# Polling cadence: don't poll every tick — too aggressive. Default: every
# Nth tick. Caller can override.
DEFAULT_POLL_INTERVAL_TICKS = 10

# Per-wire kind → identity-file target mapping. Each wire's
# `proposed_identity_signal()` returns a `kind` string. Map it to the
# target identity file the proposal should land against.
KIND_TO_TARGET: Dict[str, str] = {
    # Memory / recall / source provenance — affects the agent's record-of-self.
    "systematic_memory_drift": "personality",
    "corpus_retrieval_drift": "personality",
    "metacognition_drift": "personality",
    "self_revision_drift": "personality",
    # Voice / language production / mode coherence.
    "voice_drift": "personality",
    "persona_coherence_drift": "personality",
    # Action / outward reach / making.
    "outward_reach_drift": "personality",
    "making_drift": "personality",
    "task_planning_drift": "personality",
    # Compression / inference / report fidelity — agent's epistemic stance.
    "systematic_compression_drift": "personality",
    "systematic_inference_drift": "personality",
    "report_generation_drift": "personality",
    # Skill routing / dispatch.
    "skill_discovery_drift": "personality",
    # Dwelling / DMN / pre-conscious.
    "dwelling_drift": "personality",
    # Briefing / proactive surfacing.
    "proactive_briefing_drift": "personality",
}

# Domain groupings for convergence detection. Wires firing within the
# same domain count toward convergence count for that domain.
DOMAIN_GROUPS: Dict[str, set] = {
    "memory_and_recall": {
        "systematic_memory_drift", "corpus_retrieval_drift",
        "systematic_compression_drift",
    },
    "voice_and_persona": {
        "voice_drift", "persona_coherence_drift", "skill_discovery_drift",
    },
    "outward_action": {
        "outward_reach_drift", "making_drift", "task_planning_drift",
        "report_generation_drift",
    },
    "metacognition_and_self": {
        "metacognition_drift", "self_revision_drift", "dwelling_drift",
    },
}


def kind_to_domain(kind: str) -> str:
    """Map a kind to its domain group (for convergence detection)."""
    for domain, kinds in DOMAIN_GROUPS.items():
        if kind in kinds:
            return domain
    return "other"


class IdentityProposalWriter(BrainMechanism):
    """Appends third_eye-distilled identity-relevant patterns to PROPOSALS.md for operator review."""

    CONFIDENCE_THRESHOLD = 0.7

    def __init__(self, tsb=None):
        try:
            super().__init__(name="IdentityProposalWriter", human_analog="IdentityProposalWriter", layer="integration")
        except Exception:
            self.state = getattr(self, "state", {}) or {}
        self.tsb = tsb
        # Per-kind last-broadcast timestamps for dedup throttling.
        self._kind_last_broadcast: Dict[str, float] = {}
        # Load persisted state from disk (base class does NOT auto-load on
        # init — subclasses opt in). We need this so the dedup throttle
        # survives process restarts.
        try:
            self.load_state()
        except Exception:
            pass
        if isinstance(self.state, dict):
            saved = self.state.get("kind_last_broadcast")
            if isinstance(saved, dict):
                for k, v in saved.items():
                    try:
                        self._kind_last_broadcast[str(k)] = float(v)
                    except (TypeError, ValueError):
                        continue
        PROPOSALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    def propose(
        self,
        target: str,           # one of: "soul", "identity", "personality"
        text: str,             # the proposed addition or refinement
        confidence: float,     # 0.0-1.0, written by MeaningCompressor
        source: str = "third_eye",
        rationale: str = "",
        confidence_floor: Optional[float] = None,
    ):
        """Write a proposal entry. Skipped if confidence below threshold.

        confidence_floor overrides self.CONFIDENCE_THRESHOLD for this
        call only — used by the salience-network polling layer to
        thread its own floor through.
        """
        floor = (
            float(confidence_floor)
            if confidence_floor is not None
            else self.CONFIDENCE_THRESHOLD
        )
        if confidence < floor:
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
    
    def _sync_tick(self):
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

    # ── Third-Eye salience-network polling ────────────────────────────────

    def poll_wires(
        self,
        mechanisms: Dict[str, Any],
        confidence_floor: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Salience-network arbitration over registered wires.

        Iterates `mechanisms` (typically `BrainLayerRunner.mechanisms`),
        collects IPW signals from any wire whose
        `should_propose_identity_update()` returns True, dedups by kind
        within DEDUP_WINDOW_SEC, detects convergence (≥3 wires firing
        in the same domain), writes proposals to PROPOSALS.md, and
        calls `acknowledge_proposal()` on each fired wire so the
        anchored throttle activates.

        Returns a stats dict so the caller (core_tick) can log progress
        and the test harness can verify behavior.

        Args:
            mechanisms: name → live instance. Skips entries that don't
                have the IPW handshake methods (the older Phase 1/2
                mechanisms still use the third_eye_state path; that's
                handled separately by `_sync_tick`).
            confidence_floor: override CONFIDENCE_THRESHOLD for this poll.
        """
        floor = (
            float(confidence_floor)
            if confidence_floor is not None
            else self.CONFIDENCE_THRESHOLD
        )
        # 1. Collect raw signals.
        raw_signals: List[Dict[str, Any]] = []
        for name, mech in (mechanisms or {}).items():
            if mech is None:
                continue
            should_propose = getattr(mech, "should_propose_identity_update", None)
            propose_signal = getattr(mech, "proposed_identity_signal", None)
            if not callable(should_propose) or not callable(propose_signal):
                continue
            try:
                if not should_propose():
                    continue
                sig = propose_signal()
                if not isinstance(sig, dict):
                    continue
            except Exception:
                continue
            sig = dict(sig)
            sig["_mechanism_name"] = name
            sig["_mechanism_obj"] = mech
            raw_signals.append(sig)

        # 2. Dedup by kind within habituation window.
        deduped: List[Dict[str, Any]] = []
        deduped_throttled: List[Dict[str, Any]] = []
        now = time.time()
        for sig in raw_signals:
            kind = str(sig.get("kind", "") or "")
            last_ts = self._kind_last_broadcast.get(kind, 0.0)
            if last_ts > 0 and (now - last_ts) < DEDUP_WINDOW_SEC:
                deduped_throttled.append(sig)
                continue
            deduped.append(sig)

        # 3. Detect convergence — count signals per domain group.
        per_domain: Dict[str, List[Dict[str, Any]]] = {}
        for sig in deduped:
            domain = kind_to_domain(str(sig.get("kind", "")))
            per_domain.setdefault(domain, []).append(sig)

        # 4. Write proposals. For domains at/above convergence threshold,
        # write a single consolidated meta-proposal that names the
        # convergence (Seeley 2007 — multi-region salience convergence
        # is stronger evidence than any single signal).
        proposals_written: List[Dict[str, Any]] = []
        ack_calls: List[str] = []

        # 4a. Convergence proposals first (highest signal-strength).
        for domain, signals in per_domain.items():
            if domain == "other":
                continue
            if len(signals) < CONVERGENCE_THRESHOLD:
                continue
            wrote = self._write_convergence_proposal(
                domain=domain, signals=signals, floor=floor,
            )
            if wrote:
                proposals_written.append(wrote)
                # Acknowledge every wire that contributed.
                for sig in signals:
                    name = sig["_mechanism_name"]
                    self._acknowledge_safe(sig["_mechanism_obj"], name)
                    ack_calls.append(name)
                    # Mark the kind so we don't double-fire it as a single below.
                    kind = str(sig.get("kind", ""))
                    if kind:
                        self._kind_last_broadcast[kind] = now

        # 4b. Single-wire proposals for domains under convergence threshold.
        for domain, signals in per_domain.items():
            if domain != "other" and len(signals) >= CONVERGENCE_THRESHOLD:
                continue  # already handled as convergence
            for sig in signals:
                kind = str(sig.get("kind", ""))
                # Skip if this kind got broadcast as part of convergence.
                if (
                    kind
                    and kind in self._kind_last_broadcast
                    and self._kind_last_broadcast[kind] >= now - 1.0
                ):
                    continue
                wrote = self._write_single_proposal(sig, floor=floor)
                if wrote:
                    proposals_written.append(wrote)
                    name = sig["_mechanism_name"]
                    self._acknowledge_safe(sig["_mechanism_obj"], name)
                    ack_calls.append(name)
                    if kind:
                        self._kind_last_broadcast[kind] = now

        # 5. Persist throttle state.
        self.state["kind_last_broadcast"] = dict(self._kind_last_broadcast)
        try:
            self.persist_state()
        except Exception:
            pass

        return {
            "ok": True,
            "raw_signals_n": len(raw_signals),
            "throttled_n": len(deduped_throttled),
            "proposals_written_n": len(proposals_written),
            "convergence_proposals_n": sum(
                1 for p in proposals_written if p.get("kind") == "convergence"
            ),
            "single_proposals_n": sum(
                1 for p in proposals_written if p.get("kind") == "single"
            ),
            "acks": ack_calls,
            "proposals": proposals_written,
        }

    def _write_single_proposal(
        self,
        signal: Dict[str, Any],
        floor: float,
    ) -> Optional[Dict[str, Any]]:
        """Write a single-wire proposal. Returns the proposal record if
        written, None if dropped."""
        kind = str(signal.get("kind", "") or "")
        target = KIND_TO_TARGET.get(kind, "identity")
        score = float(signal.get("rolling_integrity_score", 0.0) or 0.0)
        # Confidence = inverse of integrity-score severity. Heuristic:
        # higher confidence when the wire's score is further below 0.55.
        # Caps at 1.0 so we don't over-amplify.
        confidence = max(0.0, min(1.0, 1.0 - score + 0.5))
        if confidence < floor:
            return None

        source = str(signal.get("source", "unknown"))
        interp = str(signal.get("interpretation", "")).strip()
        dominant = str(signal.get("dominant_failure_mode", "")).strip()
        bad_count = int(signal.get("dominant_failure_count", 0) or 0)

        text_parts = [interp] if interp else []
        if dominant:
            text_parts.append(
                f"Dominant failure mode: `{dominant}` ({bad_count} occurrences)."
            )
        text = "\n\n".join(text_parts) or f"Salience signal from {source}."

        rationale = (
            f"Single-wire IPW handshake from {source}; rolling integrity "
            f"score {score:.3f}; consecutive bad-ops "
            f"{int(signal.get('consecutive_bad_ops', 0) or 0)}."
        )

        ok = self.propose(
            target=target,
            text=text,
            confidence=confidence,
            source=source,
            rationale=rationale,
            confidence_floor=floor,
        )
        if not ok:
            return None
        return {
            "kind": "single",
            "source": source,
            "target": target,
            "confidence": round(confidence, 4),
            "signal_kind": kind,
        }

    def _write_convergence_proposal(
        self,
        domain: str,
        signals: List[Dict[str, Any]],
        floor: float,
    ) -> Optional[Dict[str, Any]]:
        """Write a meta-proposal for ≥CONVERGENCE_THRESHOLD wires firing
        in the same domain. Confidence is averaged + lifted (convergence
        = stronger evidence per Seeley 2007)."""
        sources = [str(s.get("source", "?")) for s in signals]
        kinds = [str(s.get("kind", "?")) for s in signals]
        scores = [
            float(s.get("rolling_integrity_score", 0.0) or 0.0) for s in signals
        ]
        avg_score = sum(scores) / max(1, len(scores))
        # Convergence boost: confidence = inverse-of-severity + 0.10 per
        # additional wire past the threshold. Capped at 0.97 to leave
        # room for hand-authored proposals to outrank.
        base = max(0.0, min(1.0, 1.0 - avg_score + 0.5))
        boost = 0.10 * max(0, len(signals) - CONVERGENCE_THRESHOLD)
        confidence = max(0.0, min(0.97, base + 0.05 + boost))
        if confidence < floor:
            return None

        target = "personality"  # convergence drift maps to behavioral file
        if domain == "metacognition_and_self":
            target = "identity"

        interpretations = [
            f"  - **{s.get('source','?')}** ({s.get('kind','?')}): "
            f"{(s.get('interpretation') or '').strip()[:160]}"
            for s in signals
        ]

        text = (
            f"**Convergent salience signal across {len(signals)} wires "
            f"in the `{domain}` domain.**\n\n"
            f"Multiple independent monitors are flagging related drift. "
            f"Per the Seeley 2007 convergence principle, this is stronger "
            f"evidence than any single wire firing alone — the operator "
            f"should review this with priority over isolated drift signals.\n\n"
            f"### Contributing signals\n\n"
            + "\n".join(interpretations)
        )

        rationale = (
            f"Third-Eye convergence across domain `{domain}` "
            f"(wires: {', '.join(sources)}; kinds: {', '.join(kinds)}). "
            f"Average rolling integrity score: {avg_score:.3f}. "
            f"Confidence boosted from convergence count = {len(signals)}."
        )

        ok = self.propose(
            target=target,
            text=text,
            confidence=confidence,
            source=f"third_eye:convergence:{domain}",
            rationale=rationale,
            confidence_floor=floor,
        )
        if not ok:
            return None
        return {
            "kind": "convergence",
            "domain": domain,
            "target": target,
            "confidence": round(confidence, 4),
            "signal_kinds": kinds,
            "sources": sources,
            "convergence_count": len(signals),
        }

    @staticmethod
    def _acknowledge_safe(mechanism: Any, name: str) -> bool:
        """Best-effort acknowledge_proposal call."""
        ack = getattr(mechanism, "acknowledge_proposal", None)
        if not callable(ack):
            return False
        try:
            ack()
            return True
        except Exception:
            return False

    def reset_dedup_window(self) -> None:
        """Operator hook: clear the per-kind broadcast throttle. Use after
        a deliberate operator review pass so the next drift signal can
        fire even if it was recently broadcast."""
        self._kind_last_broadcast.clear()
        self.state["kind_last_broadcast"] = {}
        try:
            self.persist_state()
        except Exception:
            pass

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
