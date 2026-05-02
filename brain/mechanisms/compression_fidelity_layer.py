"""
brain/mechanisms/compression_fidelity_layer.py — CompressionFidelityLayer

The runtime monitor for the agent's act of compression — taking source
material and reducing it to its load-bearing structure while keeping faith
with what was actually there. Pairs with skills/knowledge-summarization/
SKILL.md.

The neuroscience analog is the gist-vs-verbatim dual-trace memory system.
Reyna's fuzzy-trace theory: humans encode both the verbatim form of
information and an extracted gist. Summarization is gist extraction made
explicit, and the failure modes are the same as false memory: the gist
survives but verbatim details get fabricated to fill in. Hippocampal-
medial-temporal integration handles gist; verbatim survives in different
traces and decays faster, leading to schema-fitting reconstruction errors
when verbatim isn't checked.

What this mechanism does:

  - Tracks per-compression records: source hash, source length, summary
    length, intent, hedge counts, contradiction-marker counts, potential
    hallucinations (heuristic), compression ratio, fidelity score.
  - Maintains intent distribution (brief / extract / digest / synthesize).
  - Detects unhealthy patterns:
      * confidence_laundering: source hedging present but summary stripped it
      * structural_smoothing: source contradiction present but summary
        flattened it
      * critical_drop: high-stakes compression below retention floor
      * hallucination_signal: capitalized proper nouns or specific numbers
        in summary that don't appear in source (heuristic)
  - Maintains a rolling fidelity-score window: each compression gets a
    composite score; if it consistently drops below threshold, the agent's
    compression behavior is systematically degrading.
  - Publishes compression state to the TSB so other mechanisms can read
    whether fidelity is drifting.
  - Routes sustained low fidelity to IdentityProposalWriter — systematic
    compression failure is identity-relevant data, not just one bad summary.

Citations:
  1. [Reyna 2008, Cogn Sci 32(6):975-1014, PMID 21585432] — Fuzzy-trace
     theory and the dual-trace model of memory. Gist extraction (what
     summarization computationally is) coexists with verbatim memory; the
     systematic failure modes of gist-only retrieval are the same false
     memory patterns this layer detects in compression output.
  2. [Schacter 2007, Annu Rev Psychol 58:259-284, PMID 16903806] — The
     cognitive neuroscience of constructive memory. Reconstruction during
     retrieval introduces systematic errors that mirror compression
     failures: schema-fitting (smoothing), source confusion (hallucination),
     and confidence-without-evidence.
  3. [Brainerd 2002, Psychol Sci 13(2):122-127, PMID 11933996] — When
     things that were never said are remembered: gist-based false recall.
     Direct empirical basis for the hallucination heuristic — coherent
     content that fits the gist but wasn't in the source is a measurable
     failure mode.
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
AGENT_DB = AGENT_HOME / os.getenv("AGENT_DB_NAME", "agent.db")

__wire_meta__ = {
    "wire": 32,
    "signal": "compression_fidelity",
    "mechanism": "CompressionFidelityLayer",
    "reads": [
        "pirp_context.compression",
    ],
    "writes": [
        "compression_state",
        "fidelity_score",
        "intent_distribution",
        "hallucination_signal_count",
    ],
    "citations": ["PMID 21585432", "PMID 16903806", "PMID 11933996"],
}

# ── Tuning constants ──────────────────────────────────────────────────────────

# Compression-ratio floors: minimum (summary_len / source_len) per intent.
# brief: aggressive compression OK.
# extract: must keep at least 5%.
# digest: at least 10%.
# synthesize: at least 8% across multi-source.
COMPRESSION_FLOORS = {
    "brief": 0.0,
    "extract": 0.05,
    "digest": 0.10,
    "synthesize": 0.08,
}

# Hedging words / phrases. If source has any, summary should preserve some
# fraction of the count.
HEDGING_PATTERNS = [
    r"\bmight\b", r"\bmay\b", r"\bcould\b", r"\bperhaps\b", r"\bpossibly\b",
    r"\bsomewhat\b", r"\bapproximately\b", r"\babout\b", r"\bsome\b",
    r"\bsuggests?\b", r"\bappears?\b", r"\bseems?\b", r"\bindicates?\b",
    r"\blikely\b", r"\bunlikely\b", r"\bprobably\b", r"\bevidence suggests\b",
    r"\bin many cases\b", r"\bin some cases\b", r"\bnot conclusive\b",
    r"\bunclear\b", r"\buncertain\b", r"\btentative\b",
]

# Contradiction markers — source has these, summary should keep them or
# explicitly note the conflict.
CONTRADICTION_MARKERS = [
    r"\bbut\b", r"\bhowever\b", r"\balthough\b", r"\bthough\b",
    r"\byet\b", r"\bwhereas\b", r"\bin contrast\b", r"\bon the other hand\b",
    r"\bconflicts? with\b", r"\bcontradicts?\b", r"\bdisagrees?\b",
    r"\bwhile\b",
]

# Pattern to extract candidate proper nouns and specific numbers from text.
# Used for the hallucination heuristic.
_PROPER_NOUN_RE = re.compile(r"\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]+)*)\b")
_NUMBER_RE = re.compile(r"\b(\d{2,}(?:[.,]\d+)?(?:\s*%)?)\b")

# Hedge preservation: ratio threshold — summary should keep at least this
# fraction of the source's hedging.
HEDGE_PRESERVATION_THRESHOLD = 0.5

# Fidelity score below this counts as "low fidelity" for IPW.
LOW_FIDELITY_THRESHOLD = 0.5

# Need at least this many compressions in window to claim fidelity drift.
FIDELITY_MIN_N = 5

# Rolling window for fidelity tracking.
FIDELITY_WINDOW = 30

# IPW: only re-fire after this many additional low-fidelity compressions.
IPW_REPORT_EVERY = 3

VALID_INTENTS = {"brief", "extract", "digest", "synthesize"}


def _hash_text(text: str) -> str:
    """Stable short hash for source/summary identification."""
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _count_pattern_hits(text: str, patterns: List[str]) -> int:
    """Count total matches across all patterns in text."""
    if not text:
        return 0
    total = 0
    lower = text.lower()
    for pat in patterns:
        total += len(re.findall(pat, lower))
    return total


def _candidate_specifics(text: str) -> Set[str]:
    """Extract proper-noun-looking and number-looking strings from text.

    Multi-word proper-noun phrases are split into their constituent single
    words AS WELL AS kept as the full phrase, so a summary's "Boston" alone
    matches a source's "The Boston" — set difference doesn't false-flag the
    constituent. Used to compare summary vs source: any specific in summary
    that's not in source is a potential hallucination.
    """
    if not text:
        return set()
    nouns: Set[str] = set()
    for phrase in _PROPER_NOUN_RE.findall(text):
        phrase = phrase.strip()
        if not phrase:
            continue
        nouns.add(phrase)
        # Also add each capitalized word from the phrase.
        for word in phrase.split():
            w = word.strip()
            if w and w[0].isupper():
                nouns.add(w)
    numbers = set(_NUMBER_RE.findall(text))
    return {s.strip() for s in nouns | numbers if s.strip()}


def compute_fidelity_signals(
    source: str,
    summary: str,
    intent: str = "digest",
) -> Dict[str, Any]:
    """Compute the fidelity signals for a (source, summary) pair.

    Heuristic, not LLM-grade. Returns:
        - source_hedge_count, summary_hedge_count, hedge_preservation_rate
        - source_contradiction_markers, summary_contradiction_markers,
          contradiction_preserved (bool)
        - potential_hallucinations: list of specifics in summary not in source
        - confidence_laundering (bool)
        - structural_smoothing (bool)
        - compression_ratio (summary_len / source_len)
        - fidelity_score (0-1 composite)
    """
    src = source or ""
    summ = summary or ""
    src_len = len(src)
    summ_len = len(summ)

    s_hedges = _count_pattern_hits(src, HEDGING_PATTERNS)
    summ_hedges = _count_pattern_hits(summ, HEDGING_PATTERNS)
    if s_hedges == 0:
        hedge_rate = 1.0  # source had no hedging to preserve
    else:
        hedge_rate = min(1.0, summ_hedges / s_hedges)

    s_contradictions = _count_pattern_hits(src, CONTRADICTION_MARKERS)
    summ_contradictions = _count_pattern_hits(summ, CONTRADICTION_MARKERS)
    contradiction_preserved = (s_contradictions == 0) or (summ_contradictions > 0)

    # Hallucination heuristic: specifics in summary not in source.
    src_specifics = _candidate_specifics(src)
    summ_specifics = _candidate_specifics(summ)
    potential_hallucinations = sorted(summ_specifics - src_specifics)

    confidence_laundering = (s_hedges >= 3 and summ_hedges == 0)
    structural_smoothing = (s_contradictions >= 2 and summ_contradictions == 0)

    compression_ratio = (summ_len / src_len) if src_len > 0 else 0.0

    # Composite fidelity score (0-1):
    #   start at 1.0
    #   -0.4 * (1 - hedge_rate) for confidence laundering
    #   -0.3 if structural smoothing fires
    #   -0.05 per potential hallucination, capped at -0.3
    #   -0.1 if compression ratio under floor for intent
    score = 1.0
    score -= 0.4 * (1.0 - hedge_rate)
    if structural_smoothing:
        score -= 0.3
    score -= min(0.3, len(potential_hallucinations) * 0.05)
    floor = COMPRESSION_FLOORS.get(intent, 0.0)
    if compression_ratio < floor and src_len > 0:
        score -= 0.1
    score = max(0.0, min(1.0, score))

    return {
        "source_hedge_count": s_hedges,
        "summary_hedge_count": summ_hedges,
        "hedge_preservation_rate": round(hedge_rate, 4),
        "source_contradiction_markers": s_contradictions,
        "summary_contradiction_markers": summ_contradictions,
        "contradiction_preserved": contradiction_preserved,
        "potential_hallucinations": potential_hallucinations[:10],
        "potential_hallucination_count": len(potential_hallucinations),
        "confidence_laundering": confidence_laundering,
        "structural_smoothing": structural_smoothing,
        "compression_ratio": round(compression_ratio, 4),
        "fidelity_score": round(score, 4),
    }


# ── Mechanism ─────────────────────────────────────────────────────────────────

class CompressionFidelityLayer(BrainMechanism):
    """
    The agent's compression monitor. See module docstring.
    """

    def __init__(self, db_path: Optional[Path] = None, history_size: int = 200):
        try:
            super().__init__(
                name="CompressionFidelityLayer",
                human_analog="gist-extraction fidelity monitor (fuzzy-trace memory analog)",
                layer="integration",
            )
        except Exception:
            pass

        self.db_path = db_path or AGENT_DB
        self.history_size = history_size

        # In-memory working state.
        self.compressions: Deque[Dict[str, Any]] = deque(maxlen=history_size)
        self.intent_state: Dict[str, Dict[str, int]] = {
            k: {"total": 0, "low_fidelity": 0, "hallucinations": 0}
            for k in VALID_INTENTS
        }
        self.fidelity_window: Deque[float] = deque(maxlen=FIDELITY_WINDOW)
        self.consecutive_low_fidelity: int = 0
        self.fired_last_tick: bool = False
        self.ipw_report_count: int = 0

        # Restore persisted state.
        self.load_state()
        self._restore_working_state()

    # ── State plumbing ─────────────────────────────────────────────────────

    def _restore_working_state(self) -> None:
        if not isinstance(self.state, dict):
            return

        saved = self.state.get("compressions")
        if isinstance(saved, list):
            for c in saved[-self.history_size:]:
                if isinstance(c, dict):
                    self.compressions.append(c)

        saved_intents = self.state.get("intent_state")
        if isinstance(saved_intents, dict):
            for k in VALID_INTENTS:
                if isinstance(saved_intents.get(k), dict):
                    self.intent_state[k].update({
                        sk: int(saved_intents[k].get(sk, 0) or 0)
                        for sk in ("total", "low_fidelity", "hallucinations")
                    })

        saved_fw = self.state.get("fidelity_window")
        if isinstance(saved_fw, list):
            for v in saved_fw[-FIDELITY_WINDOW:]:
                self.fidelity_window.append(float(v))

        self.consecutive_low_fidelity = int(
            self.state.get("consecutive_low_fidelity", 0) or 0
        )
        self.ipw_report_count = int(self.state.get("ipw_report_count", 0) or 0)

    def _flush_working_state(self) -> None:
        self.state["compressions"] = list(self.compressions)
        self.state["intent_state"] = {
            k: dict(self.intent_state[k]) for k in VALID_INTENTS
        }
        self.state["fidelity_window"] = list(self.fidelity_window)
        self.state["consecutive_low_fidelity"] = self.consecutive_low_fidelity
        self.state["ipw_report_count"] = self.ipw_report_count
        self.state["last_updated"] = time.time()

    # ── Public API ─────────────────────────────────────────────────────────

    def should_block(
        self,
        intent: str,
        source_len: int = 0,
        target_len: int = 0,
    ) -> Tuple[bool, str]:
        """Decide whether to block an upcoming compression.

        Blocks when:
          - intent is invalid
          - extract intent and target/source ratio < 5% (critical drop)
          - sustained low fidelity (recent compressions consistently below
            LOW_FIDELITY_THRESHOLD)
        """
        if intent not in VALID_INTENTS:
            return True, (
                f"invalid intent {intent!r} (must be one of {sorted(VALID_INTENTS)})"
            )

        if source_len > 0 and target_len > 0:
            ratio = target_len / source_len
            floor = COMPRESSION_FLOORS.get(intent, 0.0)
            if ratio < floor:
                return True, (
                    f"compression ratio {ratio:.3f} below {intent!r} floor "
                    f"({floor}) — requires operator approval"
                )

        if self.is_systematically_low_fidelity():
            return True, (
                f"sustained low fidelity (rolling score "
                f"{self.rolling_fidelity_score():.3f} < {LOW_FIDELITY_THRESHOLD}) — "
                "operator should review prior compressions before approving more"
            )

        return False, ""

    def record_compression(
        self,
        intent: str,
        source: str,
        summary: str,
        caveats: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Record a completed compression with computed fidelity signals.

        Returns the compression record dict (with id and signals).
        """
        if intent not in VALID_INTENTS:
            return self._record_untagged(source, summary, caveats)

        signals = compute_fidelity_signals(source, summary, intent)
        record = {
            "id": uuid.uuid4().hex[:12],
            "intent": intent,
            "source_hash": _hash_text(source),
            "source_len": len(source or ""),
            "summary_len": len(summary or ""),
            "caveats": list(caveats or [])[:10],
            "signals": signals,
            "ts": time.time(),
        }
        self.compressions.append(record)

        # Update per-intent counters.
        self.intent_state[intent]["total"] += 1
        if signals["fidelity_score"] < LOW_FIDELITY_THRESHOLD:
            self.intent_state[intent]["low_fidelity"] += 1
            self.consecutive_low_fidelity += 1
        else:
            self.consecutive_low_fidelity = 0
            if self.state.get("acknowledged_at_low_fidelity"):
                self.state["acknowledged_at_low_fidelity"] = 0

        if signals["potential_hallucination_count"] > 0:
            self.intent_state[intent]["hallucinations"] += signals[
                "potential_hallucination_count"
            ]

        # Update rolling fidelity window.
        self.fidelity_window.append(signals["fidelity_score"])

        self._flush_working_state()
        self.persist_state()
        return record

    def _record_untagged(
        self,
        source: str,
        summary: str,
        caveats: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Untagged compressions still get computed signals but don't credit
        any valid intent."""
        signals = compute_fidelity_signals(source, summary, "digest")  # default for scoring
        record = {
            "id": uuid.uuid4().hex[:12],
            "intent": "__untagged__",
            "source_hash": _hash_text(source),
            "source_len": len(source or ""),
            "summary_len": len(summary or ""),
            "caveats": list(caveats or [])[:10],
            "signals": signals,
            "ts": time.time(),
            "error": "intent missing — compression recorded as untagged",
        }
        self.compressions.append(record)
        self._flush_working_state()
        self.persist_state()
        return record

    # ── Pattern detection ──────────────────────────────────────────────────

    def rolling_fidelity_score(self) -> float:
        """Mean fidelity score over the rolling window."""
        if not self.fidelity_window:
            return 1.0
        return sum(self.fidelity_window) / len(self.fidelity_window)

    def is_systematically_low_fidelity(self) -> bool:
        """True when rolling fidelity is below threshold AND we have enough
        data to claim it."""
        if len(self.fidelity_window) < FIDELITY_MIN_N:
            return False
        return self.rolling_fidelity_score() < LOW_FIDELITY_THRESHOLD

    def compression_state(self) -> str:
        """Single-word state for the TSB. Priority order:
        degrading > recent_low > faithful > active > idle."""
        if self.is_systematically_low_fidelity():
            return "degrading"
        if self.consecutive_low_fidelity >= 2:
            return "recent_low"
        if self.fidelity_window and self.rolling_fidelity_score() >= 0.85:
            return "faithful"
        # Recent compression within last 60s = active.
        if self.compressions:
            most_recent = self.compressions[-1]
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
        """One tick. If pirp_context carries a `compression` dict, record it."""
        pirp_context = pirp_context or {}
        comp = pirp_context.get("compression")
        if isinstance(comp, dict):
            self.record_compression(
                intent=str(comp.get("intent", "")),
                source=str(comp.get("source", "")),
                summary=str(comp.get("summary", "")),
                caveats=list(comp.get("caveats") or []),
            )
            self.fired_last_tick = True
        else:
            self.fired_last_tick = False
            self._flush_working_state()
        return self.get_state()

    def get_state(self) -> Dict[str, Any]:
        """TSB payload."""
        per_intent = {
            k: {
                "total": s["total"],
                "low_fidelity": s["low_fidelity"],
                "hallucinations": s["hallucinations"],
                "low_fidelity_rate": (
                    s["low_fidelity"] / s["total"] if s["total"] else 0.0
                ),
            }
            for k, s in self.intent_state.items()
        }

        return {
            "compression_state": self.compression_state(),
            "rolling_fidelity_score": round(self.rolling_fidelity_score(), 4),
            "fidelity_window_n": len(self.fidelity_window),
            "is_systematically_low_fidelity": self.is_systematically_low_fidelity(),
            "consecutive_low_fidelity": self.consecutive_low_fidelity,
            "intent_distribution": per_intent,
            "compression_count": len(self.compressions),
            "_fired_tick": self.fired_last_tick,
        }

    # ── IdentityProposalWriter handshake ───────────────────────────────────

    def should_propose_identity_update(self) -> bool:
        """True when sustained low fidelity is identity-relevant data."""
        if not self.is_systematically_low_fidelity():
            return False
        ack_at = int(self.state.get("acknowledged_at_low_fidelity", 0) or 0)
        if ack_at <= 0:
            return self.consecutive_low_fidelity >= 3
        return self.consecutive_low_fidelity >= (ack_at + IPW_REPORT_EVERY)

    def proposed_identity_signal(self) -> Dict[str, Any]:
        """Compact signal for IdentityProposalWriter to consume."""
        return {
            "source": "CompressionFidelityLayer",
            "kind": "systematic_compression_drift",
            "rolling_fidelity_score": round(self.rolling_fidelity_score(), 4),
            "consecutive_low_fidelity": self.consecutive_low_fidelity,
            "intent_low_fidelity_rates": {
                k: (s["low_fidelity"] / s["total"] if s["total"] else 0.0)
                for k, s in self.intent_state.items()
            },
            "total_hallucinations": sum(
                s["hallucinations"] for s in self.intent_state.values()
            ),
            "interpretation": (
                "The agent's compressions are systematically losing fidelity — "
                "stripping hedging, smoothing contradictions, or interpolating "
                "specifics that aren't in the source."
            ),
        }

    def acknowledge_proposal(self) -> None:
        """Anchor current consecutive_low_fidelity so future re-fire requires
        further accumulation."""
        self.ipw_report_count += 1
        self.state["acknowledged_at_low_fidelity"] = self.consecutive_low_fidelity
        self.state["last_acknowledged_at"] = time.time()
        self._flush_working_state()
        self.persist_state()

    # ── Operator API ──────────────────────────────────────────────────────

    def reset_fidelity_window(self) -> None:
        """Clear the rolling fidelity window. Use after retraining or when
        prior compressions are no longer representative of current behavior."""
        self.fidelity_window.clear()
        self.consecutive_low_fidelity = 0
        if self.ipw_report_count > 0:
            self.ipw_report_count = max(0, self.ipw_report_count - 1)
        if self.state.get("acknowledged_at_low_fidelity"):
            self.state["acknowledged_at_low_fidelity"] = 0
        self._flush_working_state()
        self.persist_state()
