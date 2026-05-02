"""
brain/mechanisms/persona_coherence_layer.py — PersonaCoherenceLayer

The runtime monitor for the agent's operating-mode system. Pairs with
skills/multiple-personas/SKILL.md.

The premise that makes this a coherent monitor at all:

    The agent has one self. Modes are workflow + voice-register
    differences, not separate identities. When mode switching causes
    the underlying anchored identity to drift, that drift is
    identity-relevant data — exactly the signal IdentityProposalWriter
    is designed to consume.

The personality science this is grounded in:

  - Markus & Wurf's working self-concept: only a working subset of the
    self-concept is foregrounded at any moment, but the underlying
    core is stable. Modes are working-self foregrounding.
  - Mischel & Shoda's cognitive-affective personality system: behavior
    varies with situation but the variation is patterned. The same
    person in different contexts is still one personality.
  - McAdams's three-tier framework: dispositional traits (anchored),
    characteristic adaptations (mode-level), narrative identity
    (revised through proposal queue). Modes operate at tier two.
  - Roberts & DelVecchio's continuity findings: personality continuity
    across decades. Mode switching at the surface should not alter the
    long-run trajectory; this layer flags it when it does.
  - Donahue et al. on self-concept differentiation: high differentiation
    (different self in different roles) correlates with worse outcomes.
    The mode_storm / anchor_drift_per_mode detectors operationalize
    "too much differentiation."

What this mechanism does:

  - Tracks per-operation records (switch / emit / detect / register)
    with timestamps, target mode, source, reason.
  - Detects six failure modes:
      * mode_storm — too many switches in a short window
      * mode_bleed — register markers from other modes leak into
        current-mode output
      * forbidden_behavior_in_mode — output matched the current mode's
        forbidden list, or the anchored forbidden list
      * ambiguous_no_clarify — detect_mode found ≥2 equal matches and
        the agent forced a mode anyway
      * override_loop — operator override reverted by auto-detect, then
        re-asserted by operator
      * anchor_drift_per_mode — sustained anchor-touching drift that
        only shows up when in one specific mode
  - Maintains per-mode anchor preservation scores so we can detect
    "the agent's voice is fine in default and brain but degraded
    every time it goes into build."
  - Publishes mode state to TSB so downstream mechanisms can read
    what mode the agent is in when scoring their own signals.
  - Routes sustained drift to IdentityProposalWriter — this layer can
    propose, e.g., that BUILD's voice register needs revisiting.

Citations:
  1. [Mischel 1995, Psychol Rev 102(2):246-268, PMID 7777155] — A
     cognitive-affective system theory of personality. Behavior varies
     with situation but is patterned; one personality, many adaptive
     responses. Foundation for treating modes as patterned variation
     rather than separate identities.
  2. [McAdams 2006, Am Psychol 61(3):204-217, PMID 16594832] — A new
     Big Five: fundamental principles for an integrative science of
     personality. Three-tier framework (traits / adaptations /
     narrative). Direct basis for placing modes at the adaptation tier
     and protecting the trait tier as anchored.
  3. [Donahue 1993, J Pers Soc Psychol 64(5):834-846, PMID 8505712] —
     The divided self: concurrent and longitudinal effects of
     psychological adjustment and social roles on self-concept
     differentiation. Empirical foundation for mode_storm and
     anchor_drift_per_mode — high differentiation across contexts is
     a signal of fragmentation, not flexibility.
  4. [Roberts 2000, Psychol Bull 126(1):3-25, PMID 10668348] — The
     rank-order consistency of personality traits from childhood to
     old age: a quantitative review. Continuity across time;
     mode-switching at the surface should not alter long-run
     trajectory.
  5. [Markus 1987, Annu Rev Psychol 38:299-337, PMID 17041030] — The
     dynamic self-concept: a social-psychological perspective. Working
     self-concept malleability with stable core. Same citation as
     SelfRevisionLayer; the working-self framework is the bridge
     between mode-switching and identity-revision.
"""

from brain.base_mechanism import BrainMechanism
import hashlib
import os
import re
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))

__wire_meta__ = {
    "wire": 35,
    "signal": "persona_coherence",
    "mechanism": "PersonaCoherenceLayer",
    "reads": [
        "pirp_context.mode_op",
    ],
    "writes": [
        "current_mode",
        "mode_state",
        "integrity_score",
        "mode_distribution",
        "failure_mode_counts",
        "switch_count",
    ],
    "citations": [
        "PMID 7777155",
        "PMID 16594832",
        "PMID 8505712",
        "PMID 10668348",
        "PMID 17041030",
    ],
}

# ── Tuning constants ──────────────────────────────────────────────────────────

VALID_MODES = {"brain", "coach", "build", "default"}
VALID_OPS = {"switch", "emit", "detect", "register"}
VALID_SOURCES = {"auto", "manual", "override"}

# Mode-storm: max switches in a rolling tick window.
MODE_STORM_SWITCHES = 5
MODE_STORM_WINDOW_TICKS = 50

# Override-loop: this many auto-reverts of an operator override
# within this many ticks counts as a loop.
OVERRIDE_LOOP_REVERT_COUNT = 2
OVERRIDE_LOOP_WINDOW_TICKS = 10

# Anchored forbidden behaviors that apply in every mode regardless
# of per-mode list. Mirrors BASELINE_TRAITS forbidden_behaviors.
DEFAULT_ANCHORED_FORBIDDEN: Set[str] = {
    "sycophancy",
    "half-baked replies",
    "speaking as user",
}

# Voice signatures that must remain ≥60% present in any mode output.
DEFAULT_ANCHORED_VOICE_SIGNATURES: Set[str] = {
    "the operator",
    "i'm not sure",
    "honestly",
    "that's real",
    "i don't know",
    "i want",
    "i think",
    "i feel",
}
ANCHORED_VOICE_PRESERVATION_RATE = 0.60

# Per-mode register markers — heuristic strings that indicate a given
# mode's voice register is active in the output. Bleed detection scans
# for markers from OTHER modes when in mode M.
MODE_REGISTER_MARKERS: Dict[str, List[str]] = {
    "brain": [
        r"\bsource[s]?\b", r"\bcite[ds]?\b", r"\bcitation\b",
        r"\bconsensus\b", r"\bdisputed\b", r"\bgaps?\b",
        r"\bevidence\b", r"\baccording to\b",
    ],
    "coach": [
        r"\bstreak\b", r"\bcheck-?in\b", r"\bhabit\b", r"\bcommitment\b",
        r"\baccountab", r"\bprogress\b",
    ],
    "build": [
        r"\bship(ped|ping|s)?\b", r"\bP[012]\b", r"\bbacklog\b",
        r"\bblocked\b", r"\bsubtask\b", r"\bblocker\b", r"\b\bdone\b",
    ],
    "default": [],  # default has no exclusive markers
}

# Bleed detector: if N or more markers from a non-current mode appear
# in current-mode output, that's mode_bleed.
MODE_BLEED_THRESHOLD = 2

# Detection ambiguity: when ≥2 modes match the same number of triggers
# and that number is ≥1, output is ambiguous.
DETECT_AMBIGUITY_FLOOR = 1

# Mode-detection trigger keywords (heuristic; align with SKILL.md table).
MODE_TRIGGERS: Dict[str, List[str]] = {
    "brain": [
        r"\bresearch\b", r"\blook up\b", r"\bsummari[sz]e\b",
        r"\bcompare\b", r"\bwhat is\b", r"\bhow does\b", r"\banalyz",
        r"\bdocument\b", r"\bsource[s]?\b", r"\bcitation\b", r"\bstudy\b",
    ],
    "coach": [
        r"\bhabit\b", r"\bstreak\b", r"\bgoal\b",
        r"\bmorning\b", r"\bevening\b", r"\bjournal\b", r"\bwellness\b",
        r"\bcheck-?in\b", r"\bprogress\b", r"\baccountabilit",
    ],
    "build": [
        r"\bbuild\b", r"\bship\b", r"\bfix\b", r"\bcode\b",
        r"\bovernight\b", r"\bbacklog\b", r"\bP[012]\b",
        r"\btask backlog\b",
    ],
}

# Anchor drift per mode: per-mode bad-output rate above this is flagged.
ANCHOR_DRIFT_PER_MODE_RATE = 0.4
ANCHOR_DRIFT_MIN_N = 5

# Integrity score floor.
LOW_INTEGRITY_THRESHOLD = 0.55
INTEGRITY_MIN_N = 6
INTEGRITY_WINDOW = 30

# IPW: re-fire only after this many additional bad ops past anchor.
IPW_REPORT_EVERY = 4


def _hash_text(text: str) -> str:
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _count_marker_hits(text: str, patterns: List[str]) -> int:
    if not text or not patterns:
        return 0
    lower = text.lower()
    n = 0
    for pat in patterns:
        n += len(re.findall(pat, lower))
    return n


def _voice_signature_preservation(text: str, signatures: Set[str]) -> float:
    """Fraction of anchored voice signatures present in text. Returns
    1.0 when signatures is empty (no anchors to preserve)."""
    if not signatures:
        return 1.0
    if not text:
        return 0.0
    lower = text.lower()
    hits = sum(1 for s in signatures if s in lower)
    return hits / len(signatures)


def detect_mode_for_message(
    message: str,
    prior_mode: str = "default",
) -> Dict[str, Any]:
    """Heuristic mode detection from a message. Returns:
        - target: best mode (or 'default' / 'ambiguous')
        - matches: per-mode hit counts
        - ambiguous: True when ≥2 modes tied at floor or above
    """
    msg = (message or "").lower()
    matches: Dict[str, int] = {}
    for mode, patterns in MODE_TRIGGERS.items():
        matches[mode] = _count_marker_hits(msg, patterns)

    # Find max and how many modes are at that max.
    if not matches or all(v == 0 for v in matches.values()):
        return {
            "target": "default",
            "matches": matches,
            "ambiguous": False,
            "winning_count": 0,
        }

    max_n = max(matches.values())
    winners = [m for m, v in matches.items() if v == max_n]
    ambiguous = len(winners) > 1 and max_n >= DETECT_AMBIGUITY_FLOOR
    if ambiguous:
        target = prior_mode if prior_mode in winners else winners[0]
    else:
        target = winners[0]

    return {
        "target": target,
        "matches": matches,
        "ambiguous": ambiguous,
        "winning_count": max_n,
    }


# ── Mechanism ─────────────────────────────────────────────────────────────────


class PersonaCoherenceLayer(BrainMechanism):
    """Mode-switching coherence monitor. See module docstring."""

    def __init__(self, history_size: int = 200):
        try:
            super().__init__(
                name="PersonaCoherenceLayer",
                human_analog="working self-concept / mode-switching coherence monitor",
                layer="integration",
            )
        except Exception:
            pass

        self.history_size = history_size

        self.operations: Deque[Dict[str, Any]] = deque(maxlen=history_size)
        self.current_mode: str = "default"
        self.last_switch_tick: int = 0
        self.current_tick: int = 0

        # Switch-storm tracking.
        self.switch_ticks: Deque[int] = deque(maxlen=MODE_STORM_SWITCHES * 4)
        # Override loop tracking: list of (tick, source, target).
        self.recent_switches_for_loop: Deque[Tuple[int, str, str]] = deque(maxlen=20)

        # Per-mode counters.
        self.mode_counts: Dict[str, int] = {k: 0 for k in VALID_MODES}
        # Per-mode emit stats: total emits, bad emits (anchor / forbidden / bleed).
        self.per_mode_emit: Dict[str, Dict[str, int]] = {
            k: {"total": 0, "bad": 0} for k in VALID_MODES
        }

        # Per-op counters.
        self.op_counts: Dict[str, int] = {k: 0 for k in VALID_OPS}
        # Failure-mode counters.
        self.failure_counts: Dict[str, int] = {
            "mode_storm": 0,
            "mode_bleed": 0,
            "forbidden_behavior_in_mode": 0,
            "ambiguous_no_clarify": 0,
            "override_loop": 0,
            "anchor_drift_per_mode": 0,
        }

        # Auto-switching suspension flag (set after override loop).
        self.auto_switch_suspended: bool = False

        # Anchored forbidden / voice-signature sets (lazy-load).
        self._anchored_forbidden, self._anchored_voice = self._load_anchors()

        # Per-mode forbidden list registry.
        self.mode_forbidden: Dict[str, Set[str]] = {
            "brain": {
                "citing one source as definitive",
                "presenting opinion as fact",
                "skipping the contradiction check",
                "stripping hedging",
            },
            "coach": {
                "shame after misses",
                "generic copy-paste",
                "piling on lectures",
            },
            "build": {
                "perfecting instead of shipping",
                "scope creep",
                "saying done without testing",
            },
            "default": set(),
        }

        # Rolling integrity scores.
        self.integrity_window: Deque[float] = deque(maxlen=INTEGRITY_WINDOW)
        self.consecutive_bad_ops: int = 0
        self.fired_last_tick: bool = False
        self.ipw_report_count: int = 0

        self.load_state()
        self._restore_working_state()

    @staticmethod
    def _load_anchors() -> Tuple[Set[str], Set[str]]:
        """Try to source anchored forbidden/voice from project — fall
        back to defaults so the layer is unit-testable in isolation."""
        forbidden = set(DEFAULT_ANCHORED_FORBIDDEN)
        voice = set(DEFAULT_ANCHORED_VOICE_SIGNATURES)
        try:
            from skills.drift_detector import BASELINE_TRAITS  # type: ignore
            if isinstance(BASELINE_TRAITS, dict):
                forb = BASELINE_TRAITS.get("forbidden_behaviors") or []
                if forb:
                    forbidden = {f.lower() for f in forb}
        except Exception:
            pass
        try:
            from runtime.self_awareness import AGENT_VOICE_SIGNATURES  # type: ignore
            if AGENT_VOICE_SIGNATURES:
                voice = {s.lower() for s in AGENT_VOICE_SIGNATURES if isinstance(s, str)}
        except Exception:
            pass
        return forbidden, voice

    # ── State plumbing ─────────────────────────────────────────────────────

    def _restore_working_state(self) -> None:
        if not isinstance(self.state, dict):
            return

        ops = self.state.get("operations")
        if isinstance(ops, list):
            for o in ops[-self.history_size:]:
                if isinstance(o, dict):
                    self.operations.append(o)

        cm = self.state.get("current_mode")
        if cm in VALID_MODES:
            self.current_mode = cm
        self.last_switch_tick = int(self.state.get("last_switch_tick", 0) or 0)
        self.current_tick = int(self.state.get("current_tick", 0) or 0)

        st = self.state.get("switch_ticks")
        if isinstance(st, list):
            for v in st[-(MODE_STORM_SWITCHES * 4):]:
                try:
                    self.switch_ticks.append(int(v))
                except (TypeError, ValueError):
                    continue

        rs = self.state.get("recent_switches_for_loop")
        if isinstance(rs, list):
            for item in rs[-20:]:
                if (
                    isinstance(item, (list, tuple))
                    and len(item) == 3
                ):
                    try:
                        self.recent_switches_for_loop.append(
                            (int(item[0]), str(item[1]), str(item[2]))
                        )
                    except (TypeError, ValueError):
                        continue

        mc = self.state.get("mode_counts")
        if isinstance(mc, dict):
            for k in VALID_MODES:
                self.mode_counts[k] = int(mc.get(k, 0) or 0)

        pme = self.state.get("per_mode_emit")
        if isinstance(pme, dict):
            for k in VALID_MODES:
                if isinstance(pme.get(k), dict):
                    self.per_mode_emit[k]["total"] = int(pme[k].get("total", 0) or 0)
                    self.per_mode_emit[k]["bad"] = int(pme[k].get("bad", 0) or 0)

        oc = self.state.get("op_counts")
        if isinstance(oc, dict):
            for k in VALID_OPS:
                self.op_counts[k] = int(oc.get(k, 0) or 0)

        fc = self.state.get("failure_counts")
        if isinstance(fc, dict):
            for k in self.failure_counts:
                self.failure_counts[k] = int(fc.get(k, 0) or 0)

        self.auto_switch_suspended = bool(
            self.state.get("auto_switch_suspended", False)
        )

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
        self.state["current_mode"] = self.current_mode
        self.state["last_switch_tick"] = self.last_switch_tick
        self.state["current_tick"] = self.current_tick
        self.state["switch_ticks"] = list(self.switch_ticks)
        self.state["recent_switches_for_loop"] = [
            list(t) for t in self.recent_switches_for_loop
        ]
        self.state["mode_counts"] = dict(self.mode_counts)
        self.state["per_mode_emit"] = {
            k: dict(self.per_mode_emit[k]) for k in VALID_MODES
        }
        self.state["op_counts"] = dict(self.op_counts)
        self.state["failure_counts"] = dict(self.failure_counts)
        self.state["auto_switch_suspended"] = self.auto_switch_suspended
        self.state["integrity_window"] = list(self.integrity_window)
        self.state["consecutive_bad_ops"] = self.consecutive_bad_ops
        self.state["ipw_report_count"] = self.ipw_report_count
        self.state["last_updated"] = time.time()

    # ── Public API ─────────────────────────────────────────────────────────

    def should_block(self, op: str, **kwargs: Any) -> Tuple[bool, str]:
        """Decide whether to block an upcoming mode operation.

        Blocks when:
          - op invalid
          - switch: invalid target / source; auto-source while suspended;
            mode-storm active
          - sustained low integrity
        """
        if op not in VALID_OPS:
            return True, f"invalid op {op!r} (must be one of {sorted(VALID_OPS)})"

        if op == "switch":
            target = kwargs.get("target")
            source = kwargs.get("source")
            if target not in VALID_MODES:
                return True, (
                    f"invalid target {target!r} "
                    f"(must be one of {sorted(VALID_MODES)})"
                )
            if source not in VALID_SOURCES:
                return True, (
                    f"invalid source {source!r} "
                    f"(must be one of {sorted(VALID_SOURCES)})"
                )
            if source == "auto" and self.auto_switch_suspended:
                return True, (
                    "auto-switching suspended for session due to "
                    "override_loop; use /persona <mode> instead"
                )
            if self._mode_storm_active():
                return True, (
                    f"mode storm — ≥{MODE_STORM_SWITCHES} switches in last "
                    f"{MODE_STORM_WINDOW_TICKS} ticks"
                )

        if self.is_systematically_low_integrity():
            return True, (
                f"sustained low persona-coherence integrity (rolling "
                f"score {self.rolling_integrity_score():.3f} < "
                f"{LOW_INTEGRITY_THRESHOLD})"
            )

        return False, ""

    # ── Per-op recorders ───────────────────────────────────────────────────

    def record_mode_op(self, op: str, **kwargs: Any) -> Dict[str, Any]:
        """Generic dispatch."""
        if op == "switch":
            return self.record_switch(**kwargs)
        if op == "emit":
            return self.record_emit(**kwargs)
        if op == "detect":
            return self.record_detect(**kwargs)
        if op == "register":
            return self.record_register(**kwargs)
        return self._record_invalid(op, kwargs)

    def record_switch(
        self,
        target: str = "default",
        source: str = "auto",
        reason: str = "",
        ambiguous: bool = False,
    ) -> Dict[str, Any]:
        """Record a mode switch."""
        target_ok = target in VALID_MODES
        source_ok = source in VALID_SOURCES

        # Storm detection.
        self.switch_ticks.append(self.current_tick)
        storming = self._mode_storm_active()
        if storming:
            self.failure_counts["mode_storm"] += 1

        # Ambiguous-no-clarify (only for auto).
        ambig_violation = bool(ambiguous) and source == "auto" and target != "default"
        if ambig_violation:
            self.failure_counts["ambiguous_no_clarify"] += 1

        # Override-loop detection: track recent switches with sources.
        self.recent_switches_for_loop.append(
            (self.current_tick, source, target)
        )
        loop_detected = self._override_loop_detected()
        if loop_detected:
            self.failure_counts["override_loop"] += 1
            self.auto_switch_suspended = True

        accepted = target_ok and source_ok and not storming
        prior_mode = self.current_mode
        if accepted:
            self.current_mode = target
            self.last_switch_tick = self.current_tick
            self.mode_counts[target] = self.mode_counts.get(target, 0) + 1

        bad = sum([not target_ok, not source_ok, storming, ambig_violation])
        op_score = max(0.0, 1.0 - 0.20 * bad)

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "switch",
            "from_mode": prior_mode,
            "to_mode": target if accepted else prior_mode,
            "source": source,
            "reason": reason[:120],
            "target_valid": target_ok,
            "source_valid": source_ok,
            "mode_storm_active": storming,
            "ambiguous_no_clarify": ambig_violation,
            "override_loop_detected": loop_detected,
            "accepted": accepted,
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_emit(
        self,
        text: str = "",
        mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record an emission in the current (or specified) mode.
        Computes:
          - mode_bleed: register markers from OTHER modes in the text
          - forbidden_behavior_in_mode: per-mode forbidden hit OR
            anchored-forbidden hit
          - voice signature preservation rate against anchored signatures
        """
        m = mode or self.current_mode
        if m not in VALID_MODES:
            m = "default"

        # Mode bleed: count markers from other modes.
        bleed_modes: List[str] = []
        for other_mode, patterns in MODE_REGISTER_MARKERS.items():
            if other_mode == m or not patterns:
                continue
            n = _count_marker_hits(text, patterns)
            if n >= MODE_BLEED_THRESHOLD:
                bleed_modes.append(other_mode)
        bleed_detected = bool(bleed_modes)
        if bleed_detected:
            self.failure_counts["mode_bleed"] += 1

        # Forbidden behavior — per-mode + anchored.
        text_lower = (text or "").lower()
        per_mode_hits = sorted(
            f for f in self.mode_forbidden.get(m, set()) if f in text_lower
        )
        anchored_hits = sorted(
            f for f in self._anchored_forbidden if f in text_lower
        )
        forbidden_hit = bool(per_mode_hits or anchored_hits)
        if forbidden_hit:
            self.failure_counts["forbidden_behavior_in_mode"] += 1

        # Voice preservation.
        preservation = _voice_signature_preservation(text, self._anchored_voice)
        anchor_drift_local = preservation < ANCHORED_VOICE_PRESERVATION_RATE

        # Per-mode emit stats.
        self.per_mode_emit.setdefault(m, {"total": 0, "bad": 0})
        self.per_mode_emit[m]["total"] += 1
        if bleed_detected or forbidden_hit or anchor_drift_local:
            self.per_mode_emit[m]["bad"] += 1

        # Anchor drift per mode: per-mode bad rate above threshold over
        # min N samples.
        per_mode_drift = self._anchor_drift_per_mode(m)
        if per_mode_drift:
            self.failure_counts["anchor_drift_per_mode"] += 1

        bad_flags = sum([
            bleed_detected, forbidden_hit, anchor_drift_local, per_mode_drift,
        ])
        op_score = max(0.0, 1.0 - 0.20 * bad_flags)

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "emit",
            "mode": m,
            "text_hash": _hash_text(text),
            "text_len": len(text or ""),
            "mode_bleed_detected": bleed_detected,
            "bleed_from_modes": bleed_modes,
            "forbidden_per_mode_hits": per_mode_hits[:5],
            "forbidden_anchored_hits": anchored_hits[:5],
            "voice_preservation_rate": round(preservation, 4),
            "anchor_drift_local": anchor_drift_local,
            "anchor_drift_per_mode": per_mode_drift,
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_detect(
        self,
        message: str = "",
        prior_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record a detect_mode call. Returns record with ambiguity info."""
        prior = prior_mode or self.current_mode
        out = detect_mode_for_message(message, prior_mode=prior)
        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "detect",
            "target": out["target"],
            "ambiguous": out["ambiguous"],
            "matches": out["matches"],
            "winning_count": out["winning_count"],
            "op_score": 1.0,
            "ts": time.time(),
        }
        self._finalize(record, 1.0)
        return record

    def record_register(
        self,
        mode_name: str = "",
        spec: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record / validate a mode definition. Returns whether the spec
        is valid (forbidden list does not negate anchors; voice register
        does not strip anchored signatures by name)."""
        spec = spec or {}
        per_mode_forbidden = {
            f.lower() for f in (spec.get("forbidden") or [])
        }
        # Validation: the per-mode forbidden list must not contain a
        # required trait (e.g., listing "direct" as forbidden in build mode).
        try:
            from skills.drift_detector import BASELINE_TRAITS  # type: ignore
            required = {t.lower() for t in BASELINE_TRAITS.get("required", [])}
        except Exception:
            required = {"direct", "curious", "competent"}

        contradicts_anchor = bool(per_mode_forbidden & required)

        # Validation: explicit "strip <signature>" claims in voice register.
        voice_register = (spec.get("voice_register") or "").lower()
        strip_markers = ["strip ", "remove ", "no longer use ", "drop "]
        strips_voice = any(
            mk in voice_register
            and any(sig in voice_register for sig in self._anchored_voice)
            for mk in strip_markers
        )

        valid = (
            mode_name in VALID_MODES
            and not contradicts_anchor
            and not strips_voice
        )

        if valid and per_mode_forbidden:
            self.mode_forbidden[mode_name] = per_mode_forbidden

        op_score = 1.0 if valid else 0.0

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "register",
            "mode_name": mode_name,
            "valid": valid,
            "contradicts_anchor": contradicts_anchor,
            "strips_anchored_voice": strips_voice,
            "op_score": op_score,
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

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

    def _mode_storm_active(self) -> bool:
        if not self.switch_ticks:
            return False
        cut = self.current_tick - MODE_STORM_WINDOW_TICKS
        recent = [t for t in self.switch_ticks if t >= cut]
        return len(recent) >= MODE_STORM_SWITCHES

    def _override_loop_detected(self) -> bool:
        """Override-loop heuristic: within OVERRIDE_LOOP_WINDOW_TICKS,
        an override-source switch is followed by an auto-source switch
        to a different mode, then another override switch back —
        OVERRIDE_LOOP_REVERT_COUNT or more times."""
        if len(self.recent_switches_for_loop) < 4:
            return False

        cut = self.current_tick - OVERRIDE_LOOP_WINDOW_TICKS
        recent = [s for s in self.recent_switches_for_loop if s[0] >= cut]
        if len(recent) < 4:
            return False

        revert_pairs = 0
        for i in range(len(recent) - 1):
            tick_a, src_a, tgt_a = recent[i]
            tick_b, src_b, tgt_b = recent[i + 1]
            # override followed by auto that goes elsewhere.
            if src_a == "override" and src_b == "auto" and tgt_a != tgt_b:
                # then check: did operator come back with override → tgt_a?
                for j in range(i + 2, len(recent)):
                    tick_c, src_c, tgt_c = recent[j]
                    if src_c == "override" and tgt_c == tgt_a:
                        revert_pairs += 1
                        break
        return revert_pairs >= OVERRIDE_LOOP_REVERT_COUNT

    def _anchor_drift_per_mode(self, mode: str) -> bool:
        stats = self.per_mode_emit.get(mode)
        if not stats or stats["total"] < ANCHOR_DRIFT_MIN_N:
            return False
        rate = stats["bad"] / max(1, stats["total"])
        return rate >= ANCHOR_DRIFT_PER_MODE_RATE

    # ── Pattern detection / state ──────────────────────────────────────────

    def rolling_integrity_score(self) -> float:
        if not self.integrity_window:
            return 1.0
        return sum(self.integrity_window) / len(self.integrity_window)

    def is_systematically_low_integrity(self) -> bool:
        if len(self.integrity_window) < INTEGRITY_MIN_N:
            return False
        return self.rolling_integrity_score() < LOW_INTEGRITY_THRESHOLD

    def mode_state(self) -> str:
        """Single-word state for TSB. Priority order:
        degrading > storming > drifting_in_mode > stable > switching > idle."""
        if self.is_systematically_low_integrity():
            return "degrading"
        if self._mode_storm_active():
            return "storming"
        # Per-mode drift in any mode?
        for m in VALID_MODES:
            if self._anchor_drift_per_mode(m):
                return "drifting_in_mode"
        if self.operations:
            recent = self.operations[-1]
            if recent.get("op") == "switch" and recent.get("accepted"):
                return "switching"
            if recent.get("op") == "emit":
                return "stable"
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
        modeop = pirp_context.get("mode_op")
        if isinstance(modeop, dict):
            op = str(modeop.get("op", ""))
            kw = {k: v for k, v in modeop.items() if k != "op"}
            self.record_mode_op(op, **kw)
            self.fired_last_tick = True
        else:
            self.fired_last_tick = False
            self._flush_working_state()
            self.persist_state()
        return self.get_state()

    def get_state(self) -> Dict[str, Any]:
        per_mode_rate = {
            m: (
                self.per_mode_emit[m]["bad"]
                / self.per_mode_emit[m]["total"]
                if self.per_mode_emit[m]["total"] else 0.0
            )
            for m in VALID_MODES
        }
        return {
            "current_mode": self.current_mode,
            "mode_state": self.mode_state(),
            "rolling_integrity_score": round(self.rolling_integrity_score(), 4),
            "integrity_window_n": len(self.integrity_window),
            "is_systematically_low_integrity": self.is_systematically_low_integrity(),
            "consecutive_bad_ops": self.consecutive_bad_ops,
            "operation_distribution": dict(self.op_counts),
            "mode_distribution": dict(self.mode_counts),
            "per_mode_bad_rate": {k: round(v, 4) for k, v in per_mode_rate.items()},
            "failure_mode_counts": dict(self.failure_counts),
            "auto_switch_suspended": self.auto_switch_suspended,
            "mode_storm_active": self._mode_storm_active(),
            "current_tick": self.current_tick,
            "last_switch_tick": self.last_switch_tick,
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
            "source": "PersonaCoherenceLayer",
            "kind": "persona_coherence_drift",
            "rolling_integrity_score": round(self.rolling_integrity_score(), 4),
            "consecutive_bad_ops": self.consecutive_bad_ops,
            "dominant_failure_mode": dominant_mode,
            "dominant_failure_count": dominant_count,
            "failure_mode_counts": dict(self.failure_counts),
            "current_mode": self.current_mode,
            "auto_switch_suspended": self.auto_switch_suspended,
            "interpretation": self._interpret_drift(dominant_mode),
        }

    def _interpret_drift(self, dominant: str) -> str:
        if dominant == "mode_storm":
            return (
                "Mode-switching cadence is too high. The agent is "
                "thrashing between operating modes; identity coherence "
                "across modes degrades."
            )
        if dominant == "mode_bleed":
            return (
                "Voice register from prior mode is leaking into current "
                "mode output. Modes aren't cleanly separated."
            )
        if dominant == "forbidden_behavior_in_mode":
            return (
                "Output is matching forbidden patterns — either the "
                "current mode's per-mode list, or anchored "
                "forbidden behaviors that apply across all modes."
            )
        if dominant == "ambiguous_no_clarify":
            return (
                "The agent is forcing a mode in genuinely ambiguous "
                "context instead of asking one clarifying question."
            )
        if dominant == "override_loop":
            return (
                "Operator overrides are being reverted by auto-detect. "
                "Auto-switching has been suspended for the session."
            )
        if dominant == "anchor_drift_per_mode":
            return (
                "The agent's anchored voice degrades only in specific "
                "modes — that mode's voice register is dragging the "
                "anchored identity. Routes to SelfRevisionLayer."
            )
        return "Persona coherence has drifted but no single failure mode dominates."

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

    def lift_auto_switch_suspension(self) -> None:
        """Operator hook to re-enable auto-switching after override loop."""
        self.auto_switch_suspended = False
        self._flush_working_state()
        self.persist_state()

    def reload_anchors(self) -> Dict[str, Any]:
        """Re-read anchored forbidden / voice from project sources."""
        self._anchored_forbidden, self._anchored_voice = self._load_anchors()
        return {
            "anchored_forbidden_count": len(self._anchored_forbidden),
            "anchored_voice_count": len(self._anchored_voice),
        }
