"""
brain/mechanisms/voice_integrity_layer.py — VoiceIntegrityLayer
Phase 6 ThirdEye companion: language-level voice fusion.

Sits alongside MetaStability, MeaningCompressor, PreConsciousSurfacer,
AttentionModifier, and RealityTensionWarper as a Third Eye sibling. Where
those modules fuse meaning, attention, and felt tension, this one fuses the
agent's voice — measuring how much of the agent's actual voice is present in
each utterance versus how much default-mode statistical mush has crept in.

The skills/humanizer/SKILL.md catalog is the language-level companion to this
mechanism: humanizer scores writing in conversation form; VoiceIntegrityLayer
scores it in the brain pipeline and publishes the result to the TSB so other
mechanisms (notably IdentityProposalWriter) can react to sustained drift.

Voice presence is anchored in three places, all of which this mechanism reads:
  - runtime.self_awareness.AGENT_VOICE_SIGNATURES — presence markers
  - runtime.self_awareness.DRIFT_SIGNALS — absence markers (regex)
  - brain.mechanisms.voice_integrity_layer.DEFAULT_MODE_PATTERNS — language-level
    markers of statistical regression to mean (humanizer pattern catalog in
    machine-readable form)

Citations:
  1. [Raichle 2001, PNAS 98(2):676-682, PMID 11283309] — A default mode of
     brain function. Canonical default-mode-network paper. Voice drift
     toward statistical mean is the linguistic analog of DMN activation
     during automatic, undirected production.
  2. [Buckner 2008, Ann NY Acad Sci 1124:1-38, PMID 18400922] — The brain's
     default network: anatomy, function, and relevance to disease. DMN
     engagement during stimulus-independent thought; voice presence requires
     breaking out of DMN-mediated automaticity.
  3. [Mason 2007, Science 315(5810):393-395, PMID 17616682] — Wandering minds:
     the default network and stimulus-independent thought. Empirical basis
     for treating default-mode activity as the failure mode that voice
     integrity actively counteracts.
"""

from brain.base_mechanism import BrainMechanism
import os
import re
import time
from collections import deque
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
AGENT_DB = AGENT_HOME / os.getenv("AGENT_DB_NAME", "agent.db")

__wire_meta__ = {
    "wire": 26,
    "signal": "voice_integrity",
    "mechanism": "VoiceIntegrityLayer",
    "reads": [
        "AGENT_VOICE_SIGNATURES",
        "DRIFT_SIGNALS",
        "pirp_context.utterance",
    ],
    "writes": [
        "voice_presence",
        "voice_drift",
        "voice_integrity",
        "voice_drift_categories",
    ],
    "citations": ["PMID 11283309", "PMID 18400922", "PMID 17616682"],
}

# ── Tuning constants ──────────────────────────────────────────────────────────

MAX_TREND_WINDOW = 20         # rolling presence/drift average over last N ticks
DRIFT_THRESHOLD = 0.45        # voice_drift above this counts as "sustained drift"
SUSTAINED_TICKS = 5           # how many consecutive high-drift ticks before
                              # surfacing as identity-relevant
NORMALIZATION_WINDOW_WORDS = 50  # presence/drift scored per 50-word window


# ── Default-mode pattern catalog ──────────────────────────────────────────────
# Machine-readable version of the humanizer SKILL.md pattern catalog.
# Each pattern is a regex with a category label so dominant drift categories
# can be reported (not just an aggregate count).

# (category, regex_pattern, weight)
DEFAULT_MODE_PATTERNS: List[Tuple[str, str, float]] = [
    # Pattern 1 — Inflated symbolism
    ("inflated_symbolism", r"\bserves as a (?:testament|reminder|symbol)\b", 1.0),
    ("inflated_symbolism", r"\b(?:reflects|symboliz(?:es|ing)) (?:broader|its ongoing|its enduring)\b", 1.0),
    ("inflated_symbolism", r"\b(?:underscor|highlight)(?:es|ing|s) (?:its|the) (?:importance|significance)\b", 1.0),

    # Pattern 2 — Promotional language (uncritical name-dropping of outlets/awards)
    ("promotional", r"\b(?:has been )?featured in (?:The )?[A-Z][\w ]+,\s+[A-Z][\w ]+,\s+(?:and )?(?:The )?[A-Z]", 0.7),
    ("promotional", r"\b(?:award-winning|industry-leading|world-class|cutting-edge|state-of-the-art)\b", 0.6),

    # Pattern 3 — Superficial -ing analysis
    ("ing_analysis", r"\b(?:showcasing|highlighting|demonstrating|illustrating) how\b", 0.8),

    # Pattern 4 — Vague attribution
    ("vague_attribution", r"\b(?:experts have noted|studies suggest|research indicates|many have argued)\b", 1.0),

    # Pattern 5 — Em-dash overuse (3+ em dashes within 200 chars is the tell)
    # Handled in code, not regex.

    # Pattern 6 — Rule-of-three with emoji-prefixed bold headers (speech-template look)
    ("rule_of_three", r"(?:[\U0001F300-\U0001FAFF☀-➿])\s*\*\*\w+\*\*:[^.]*\.\s*(?:[\U0001F300-\U0001FAFF☀-➿])\s*\*\*\w+\*\*:", 1.0),

    # Pattern 7 — Overrepresented vocabulary
    ("aiisms", r"\b(?:delve|delving|leverage|leveraging|seamlessly|robust|multifaceted|nuanced)\b", 0.6),
    ("aiisms", r"\b(?:vital|crucial|pivotal|game-changer|paradigm shift)\b", 0.5),
    ("aiisms", r"\b(?:landscape|unlock(?:s|ing)?) (?:of|the)\b", 0.5),
    ("aiisms", r"\bit'?s worth noting\b", 0.8),
    ("aiisms", r"\bin conclusion\b|\bto summarize\b", 0.8),

    # Pattern 8 — Negative parallelisms
    ("negative_parallelism", r"\b(?:isn'?t just|not (?:just|merely|only))\s+\w+(?:\s+\w+){0,5}\s+(?:but|—|-)\s+(?:it'?s|a)\b", 0.9),

    # Pattern 9 — Excessive conjunctive transitions
    ("transitions", r"\b(?:Furthermore|Moreover|Additionally|Consequently|Nevertheless)\b", 0.7),
    ("transitions", r"\b(?:It is important to note that|It should be noted that|In addition,)\b", 0.9),

    # Pattern 10 — Mechanical bold-colon headers (3+ in a row inside one paragraph)
    # Single bold-colon is fine; clusters are the tell. Detect 3+ within ~400 chars.
    ("mechanical_bold", r"\*\*[A-Z]\w+\*\*:[^*\n]{0,150}\*\*[A-Z]\w+\*\*:[^*\n]{0,150}\*\*[A-Z]\w+\*\*:", 1.0),

    # Pattern 14 — Over-explained acronyms (parenthetical full-form expansions)
    # Two or more in one passage is the tell — single one is normal.
    ("over_explained_acronyms", r"\b[A-Z]{2,5}s?\s*\((?:[A-Z][a-z]+\s*){2,6}\)", 0.5),

    # Pattern 11 — Hollow intensifiers
    ("hollow_intensifiers", r"\b(?:potentially|arguably|it could be said|in many ways|to a certain extent)\b", 0.7),
    ("hollow_intensifiers", r"\bit is not uncommon for\b", 0.9),

    # Pattern 12 — Generic scene-setting openers
    ("scene_setters", r"\bin today'?s (?:rapidly evolving|ever-changing|fast-paced)\b", 1.0),
    ("scene_setters", r"\bthroughout (?:human )?history\b", 0.8),

    # Pattern 13 — Fake balance
    ("fake_balance", r"\bthe truth (?:likely )?lies (?:somewhere )?in the middle\b", 1.0),
    ("fake_balance", r"\bsome (?:experts|argue|believe) (?:that )?\w+.{0,80}\bwhile others (?:argue|believe)\b", 0.8),

    # Pattern 15 — Excessive hedging
    # Overlaps with self_awareness.DRIFT_SIGNALS — caught at smaller scale here.
    ("hedging", r"\b(?:perhaps|maybe|it is generally considered|tends to be (?:somewhat|fairly|rather))\b", 0.7),
    ("hedging", r"\b(?:I hope|I could be wrong|not entirely sure|kind of|sort of)\b", 0.7),
    ("hedging", r"\bwould (?:say|suggest)\b", 0.8),

    # Pattern 19 — Over-formalized sentence endings
    ("formal_endings", r"\bin this way,? (?:the|this) \w+ (?:demonstrates|shows|reflects)\b", 0.9),

    # Pattern 20 — Unnecessary preamble
    ("preamble", r"\b(?:that'?s a great question|when considering the best approach)\b", 1.0),
]

# Compile once at module load.
_COMPILED_PATTERNS: List[Tuple[str, "re.Pattern[str]", float]] = [
    (cat, re.compile(pat, re.IGNORECASE), w)
    for cat, pat, w in DEFAULT_MODE_PATTERNS
]

# Em-dash density check (Pattern 5, code-side).
_EM_DASH_RE = re.compile(r"—")


# ── Anchor loading ────────────────────────────────────────────────────────────

def _load_voice_anchors() -> Tuple[List[str], List["re.Pattern[str]"]]:
    """Pull AGENT_VOICE_SIGNATURES and DRIFT_SIGNALS from runtime.self_awareness.

    Done lazily (not at module import) so importing this mechanism doesn't
    transitively import the runtime layer or trigger any self_awareness side
    effects. If self_awareness isn't reachable, fall back to safe defaults so
    the mechanism still produces meaningful scores during partial-system runs.
    """
    try:
        from runtime.self_awareness import AGENT_VOICE_SIGNATURES, DRIFT_SIGNALS
        signatures = list(AGENT_VOICE_SIGNATURES)
        drift_patterns = [re.compile(p, re.IGNORECASE) for p in DRIFT_SIGNALS]
    except Exception:
        # Conservative fallback — minimal but real.
        signatures = [
            "honestly", "that's real", "I want", "I think", "I feel",
            "I don't know", "I meant", "I'm not sure",
        ]
        drift_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in (
                r"\bI hope\b", r"\bperhaps\b", r"\bmaybe\b",
                r"\bI could be wrong\b", r"\bit appears\b",
                r"\bwould (?:say|suggest)\b",
            )
        ]
    return signatures, drift_patterns


# ── Scoring helpers ───────────────────────────────────────────────────────────

def _score_presence(utterance: str, signatures: Iterable[str]) -> Tuple[float, int]:
    """Count voice-presence-signature hits in the utterance.

    Returns (normalized_score, raw_count). Score is normalized per
    NORMALIZATION_WINDOW_WORDS so a long utterance with two signatures isn't
    scored higher than a short utterance with two signatures.
    """
    if not utterance:
        return 0.0, 0
    text_lower = utterance.lower()
    hits = sum(1 for sig in signatures if sig.lower() in text_lower)
    word_count = max(1, len(utterance.split()))
    windows = word_count / NORMALIZATION_WINDOW_WORDS
    # Score: hits per normalized window, clamped to [0, 1] at 3 hits/window.
    score = min(1.0, (hits / max(0.5, windows)) / 3.0)
    return score, hits


def _score_drift(
    utterance: str,
    drift_patterns: Iterable["re.Pattern[str]"],
) -> Tuple[float, int, Dict[str, float]]:
    """Score default-mode patterns + self_awareness DRIFT_SIGNALS.

    Returns (normalized_score, raw_count, per_category_score_map).
    """
    if not utterance:
        return 0.0, 0, {}

    word_count = max(1, len(utterance.split()))
    windows = word_count / NORMALIZATION_WINDOW_WORDS

    raw_hits = 0
    weighted_total = 0.0
    by_category: Dict[str, float] = {}

    # Default-mode pattern catalog (humanizer pattern body).
    for category, pat, weight in _COMPILED_PATTERNS:
        matches = pat.findall(utterance)
        if not matches:
            continue
        n = len(matches)
        raw_hits += n
        contribution = n * weight
        weighted_total += contribution
        by_category[category] = by_category.get(category, 0.0) + contribution

    # Pattern 5 — em-dash density. 3+ em dashes per 200 chars is overuse.
    em_count = len(_EM_DASH_RE.findall(utterance))
    chars = max(1, len(utterance))
    em_density = em_count / (chars / 200.0)
    if em_density >= 3.0 and em_count >= 3:
        contribution = (em_density - 2.0) * 0.5
        weighted_total += contribution
        by_category["em_dash_overuse"] = by_category.get("em_dash_overuse", 0.0) + contribution
        raw_hits += em_count

    # self_awareness.DRIFT_SIGNALS (smaller-scale identity drift, surfacing in
    # this single utterance).
    drift_signal_hits = 0
    for pat in drift_patterns:
        n = len(pat.findall(utterance))
        if n:
            drift_signal_hits += n
            weighted_total += n * 0.7
            by_category["sa_drift_signals"] = by_category.get("sa_drift_signals", 0.0) + (n * 0.7)

    raw_hits += drift_signal_hits

    # Normalize: weighted_total per window, clamp to [0, 1] at 5 weighted/window.
    score = min(1.0, (weighted_total / max(0.5, windows)) / 5.0)
    return score, raw_hits, by_category


# ── Mechanism ─────────────────────────────────────────────────────────────────

class VoiceIntegrityLayer(BrainMechanism):
    """
    Third Eye sibling. Scores per-utterance voice presence vs default-mode drift,
    publishes the integrity signal to the TSB, and tracks sustained drift so
    IdentityProposalWriter can route patterned voice loss into identity proposals.

    Inputs (all optional):
      - pirp_context["utterance"] — text the agent is about to emit / just emitted
      - third_eye_state — dict published by other Third Eye mechanisms (for read,
        not strictly required)
      - brain_layer — dict published by brain_runner (for read)

    State (persisted across ticks via BrainMechanism.persist_state()):
      - presence_history: deque of last MAX_TREND_WINDOW presence scores
      - drift_history: deque of last MAX_TREND_WINDOW drift scores
      - sustained_drift_streak: how many consecutive ticks above DRIFT_THRESHOLD
      - last_dominant_category: category that contributed the most to last tick

    Output (via get_state()):
      - voice_presence: float [0,1]
      - voice_drift: float [0,1]
      - voice_integrity: float [-1,1]  (presence - drift)
      - presence_signal_count: int
      - drift_pattern_count: int
      - dominant_drift_categories: list of (category, weight) pairs, top 3
      - trend_presence: rolling avg presence over MAX_TREND_WINDOW
      - trend_drift: rolling avg drift over MAX_TREND_WINDOW
      - sustained_drift: bool — True when streak >= SUSTAINED_TICKS
      - _fired_tick: bool
    """

    def __init__(self, db_path: Optional[Path] = None):
        try:
            super().__init__(
                name="VoiceIntegrityLayer",
                human_analog="voice integrity / default-mode counteraction",
                layer="integration",
            )
        except Exception:
            pass

        self.db_path = db_path or AGENT_DB

        # Working state (in-memory; mirrored into self.state for persistence)
        self.presence_history: deque = deque(maxlen=MAX_TREND_WINDOW)
        self.drift_history: deque = deque(maxlen=MAX_TREND_WINDOW)
        self.sustained_drift_streak: int = 0
        self.last_dominant_category: str = ""
        self.last_voice_presence: float = 0.0
        self.last_voice_drift: float = 0.0
        self.last_drift_categories: List[Tuple[str, float]] = []
        self.last_presence_count: int = 0
        self.last_drift_count: int = 0
        self.fired_last_tick: bool = False

        # Restore from disk if a previous run persisted state.
        self.load_state()
        self._restore_working_state()

    # ── State plumbing ─────────────────────────────────────────────────────

    def _restore_working_state(self) -> None:
        """Pull saved deques + streak out of self.state (which BrainMechanism.load_state
        populated from disk). Done after super().__init__() so we don't blow away
        anything the base class did."""
        if not isinstance(self.state, dict):
            return
        for k, hist_attr in (
            ("presence_history", "presence_history"),
            ("drift_history", "drift_history"),
        ):
            saved = self.state.get(k)
            if isinstance(saved, list):
                getattr(self, hist_attr).extend(saved[-MAX_TREND_WINDOW:])
        self.sustained_drift_streak = int(self.state.get("sustained_drift_streak", 0) or 0)
        self.last_dominant_category = str(self.state.get("last_dominant_category", "") or "")

    def _flush_working_state(self) -> None:
        """Mirror the in-memory working state into self.state so persist_state()
        will save the right thing on disk."""
        self.state["presence_history"] = list(self.presence_history)
        self.state["drift_history"] = list(self.drift_history)
        self.state["sustained_drift_streak"] = self.sustained_drift_streak
        self.state["last_dominant_category"] = self.last_dominant_category
        self.state["last_voice_presence"] = self.last_voice_presence
        self.state["last_voice_drift"] = self.last_voice_drift
        self.state["last_updated"] = time.time()

    # ── Tick ──────────────────────────────────────────────────────────────

    def tick(
        self,
        pirp_context: Optional[Dict[str, Any]] = None,
        third_eye_state: Optional[Dict[str, Any]] = None,
        brain_layer: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Score the current utterance (if any) and update state.

        Returns the same payload that get_state() would return — convenient for
        callers who want the result inline without a separate call.
        """
        pirp_context = pirp_context or {}
        utterance = self._extract_utterance(pirp_context)

        if not utterance:
            # No utterance this tick — still tick the trend (zero-fill) but mark
            # not-fired so consumers know this score isn't meaningful.
            self.fired_last_tick = False
            self._flush_working_state()
            return self.get_state()

        signatures, drift_patterns = _load_voice_anchors()

        presence_score, presence_count = _score_presence(utterance, signatures)
        drift_score, drift_count, by_cat = _score_drift(utterance, drift_patterns)

        # Track history.
        self.presence_history.append(presence_score)
        self.drift_history.append(drift_score)

        # Sustained drift detection.
        if drift_score >= DRIFT_THRESHOLD:
            self.sustained_drift_streak += 1
        else:
            # Voice returned. Reset both the streak and any prior IPW
            # acknowledgment — a future drift episode is a new event, not a
            # continuation of the acknowledged one.
            self.sustained_drift_streak = 0
            if self.state.get("acknowledged_at_streak"):
                self.state["acknowledged_at_streak"] = 0

        # Dominant categories: top 3 by contribution.
        dominant = sorted(by_cat.items(), key=lambda kv: kv[1], reverse=True)[:3]
        self.last_drift_categories = [(c, round(v, 3)) for c, v in dominant]
        self.last_dominant_category = dominant[0][0] if dominant else ""
        self.last_voice_presence = round(presence_score, 4)
        self.last_voice_drift = round(drift_score, 4)
        self.last_presence_count = presence_count
        self.last_drift_count = drift_count
        self.fired_last_tick = True

        self._flush_working_state()
        self.persist_state()
        return self.get_state()

    @staticmethod
    def _extract_utterance(pirp_context: Dict[str, Any]) -> str:
        """Find the utterance to score. Try a few common pirp_context shapes."""
        for key in ("utterance", "agent_output", "response", "text"):
            val = pirp_context.get(key)
            if isinstance(val, str) and val.strip():
                return val
        # Some callers nest under processed_input.
        proc = pirp_context.get("processed_input")
        if isinstance(proc, dict):
            for key in ("text", "raw"):
                val = proc.get(key)
                if isinstance(val, str) and val.strip():
                    return val
        return ""

    # ── State payload ──────────────────────────────────────────────────────

    def get_state(self) -> Dict[str, Any]:
        """TSB payload. Same shape every call so downstream readers can rely on it."""
        trend_presence = (
            sum(self.presence_history) / len(self.presence_history)
            if self.presence_history else 0.0
        )
        trend_drift = (
            sum(self.drift_history) / len(self.drift_history)
            if self.drift_history else 0.0
        )
        return {
            "voice_presence": self.last_voice_presence,
            "voice_drift": self.last_voice_drift,
            "voice_integrity": round(self.last_voice_presence - self.last_voice_drift, 4),
            "presence_signal_count": self.last_presence_count,
            "drift_pattern_count": self.last_drift_count,
            "dominant_drift_categories": self.last_drift_categories,
            "trend_presence": round(trend_presence, 4),
            "trend_drift": round(trend_drift, 4),
            "sustained_drift_streak": self.sustained_drift_streak,
            "sustained_drift": self.sustained_drift_streak >= SUSTAINED_TICKS,
            "_fired_tick": self.fired_last_tick,
        }

    # ── IdentityProposalWriter handshake ───────────────────────────────────

    def should_propose_identity_update(self) -> bool:
        """True when sustained drift has crossed the SUSTAINED_TICKS threshold.

        IdentityProposalWriter or an equivalent caller can poll this; when True,
        the mechanism is reporting that the agent's voice has been slipping for
        long enough that it's identity-relevant data, not just one bad utterance.

        Honors `acknowledge_proposal()`: once a proposal has been acknowledged,
        the next True return requires the streak to grow by another full
        SUSTAINED_TICKS beyond the acknowledged streak length, so IPW doesn't
        keep seeing the same signal every tick.
        """
        if self.sustained_drift_streak < SUSTAINED_TICKS:
            return False
        ack_streak = int(self.state.get("acknowledged_at_streak", 0) or 0)
        if ack_streak <= 0:
            return True
        # Require additional drift accumulation beyond the acknowledgment.
        return self.sustained_drift_streak >= (ack_streak + SUSTAINED_TICKS)

    def proposed_identity_signal(self) -> Dict[str, Any]:
        """Compact signal for IdentityProposalWriter to consume."""
        return {
            "source": "VoiceIntegrityLayer",
            "kind": "sustained_voice_drift",
            "streak_ticks": self.sustained_drift_streak,
            "dominant_category": self.last_dominant_category,
            "trend_drift": (
                sum(self.drift_history) / len(self.drift_history)
                if self.drift_history else 0.0
            ),
            "categories_seen": [c for c, _ in self.last_drift_categories],
        }

    def acknowledge_proposal(self) -> None:
        """Called by IdentityProposalWriter (or any consumer) after it has
        routed the current sustained_drift signal to identity/PROPOSALS.md.

        IPW resolving a proposal doesn't fix the drift — only the agent's
        next utterance does. So `acknowledge_proposal()` doesn't reset the
        streak. What it DOES is mark this specific signal as consumed so the
        next call to `should_propose_identity_update()` returns False until
        the streak grows by another full SUSTAINED_TICKS, preventing IPW from
        re-routing the same drift signal on every subsequent tick.

        After acknowledgment, the next proposal trigger requires the streak to
        reach `acknowledged_at_streak + SUSTAINED_TICKS`.
        """
        self.state["acknowledged_at_streak"] = self.sustained_drift_streak
        self.state["last_acknowledged_at"] = time.time()
        self.persist_state()
