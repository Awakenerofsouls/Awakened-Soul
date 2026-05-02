"""
SalienceFilter v19.0A
Knowing — salience_filter.py

Pre-processing stage that shapes what the brain pays attention to.
Without this, every signal hits every layer with equal weight — flat cognition.
This is the bottleneck mechanism human attention is built around.

Runs before signal distribution. Takes the full signal field from pirp_context,
scores each signal against the current cognitive state, and returns a ranked
subset that the downstream layers actually process.

Scoring axes:
  novelty       — how different is this from recent signals
  emotional_charge — how much limbic activation does it carry
  unresolvedness   — does it touch an open gap or recurring question
  desire_proximity — does it relate to an active desire signal
  identity_relevance — does it touch protected self-concepts

Dependencies: re, logging, pathlib, sqlite3
No external packages.
"""
from brain.base_mechanism import BrainMechanism
import os

VERSION = "19.0"

import logging
import re
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DB_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".agent" / "workspace"))) / "brain" / "agent.db"
try:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
DREAMS_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".agent" / "workspace"))) / "DREAMS.md"

# How many signals to pass through after filtering
TOP_K = 5

# Minimum score to pass through at all — below this, signal is dropped
FLOOR_SCORE = 0.15

# Scoring weights — must sum to 1.0
WEIGHTS = {
    "novelty": 0.25,
    "emotional_charge": 0.25,
    "unresolvedness": 0.20,
    "desire_proximity": 0.18,
    "identity_relevance": 0.12,
}

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# SalienceFilter
# ---------------------------------------------------------------------------

class SalienceFilter(BrainMechanism):
    def __init__(self, db_path: Optional[str] = None):
        try:
            super().__init__(name="SalienceFilter", human_analog="SalienceFilter", layer="integration")
        except Exception:
            self.state = getattr(self, "state", {}) or {}
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._initialize_table()
        self._signal_history: list = []  # last N signal word-sets for novelty check
        self._history_window = 10

    # ------------------------------------------------------------------
    # Table init
    # ------------------------------------------------------------------

    def _initialize_table(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS salience_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tick INTEGER,
                        timestamp TEXT,
                        signal_id TEXT,
                        signal_text TEXT,
                        score REAL,
                        passed INTEGER,
                        score_breakdown TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error("SalienceFilter: table init failed — %s", e)

    # ------------------------------------------------------------------
    # Primary interface
    # ------------------------------------------------------------------

    def filter(self, signals: list, pirp_context: dict) -> list:
        """
        Takes a list of signal dicts, scores each, returns top-k that
        exceed the floor score.

        pirp_context keys consumed:
          limbic_state: dict with mood, arousal, valence
          active_desires: list of desire signal dicts (from DesireEngine)
          known_gaps: list of gap dicts (from KnownGaps)
          tick_count: int
        """
        if not signals:
            return []

        tick = int(pirp_context.get("tick_count", 0))
        limbic = pirp_context.get("limbic_state", {})
        active_desires = pirp_context.get("active_desires", [])
        known_gaps = pirp_context.get("known_gaps", [])

        desire_words = self._extract_desire_words(active_desires)
        gap_words = self._extract_gap_words(known_gaps)
        identity_words = self._load_identity_words()

        scored = []
        for sig in signals:
            breakdown, total = self._score_signal(
                signal=sig,
                limbic=limbic,
                desire_words=desire_words,
                gap_words=gap_words,
                identity_words=identity_words,
            )
            scored.append((total, breakdown, sig))

        scored.sort(key=lambda x: x[0], reverse=True)

        passed = []
        for total, breakdown, sig in scored:
            if total >= FLOOR_SCORE and len(passed) < TOP_K:
                passed.append(sig)
                self._log_signal(tick, sig, total, breakdown, passed=True)
            else:
                self._log_signal(tick, sig, total, breakdown, passed=False)

        self._update_history(passed)

        logger.debug(
            "SalienceFilter: %d/%d signals passed (tick %d)",
            len(passed), len(signals), tick
        )

        return passed

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _score_signal(
        self,
        signal: dict,
        limbic: dict,
        desire_words: set,
        gap_words: set,
        identity_words: set,
    ) -> tuple:

        text = signal.get("text", "") + " " + signal.get("type", "")
        sig_words = set(re.findall(r"\b\w{4,}\b", text.lower()))

        breakdown = {
            "novelty": self._score_novelty(sig_words),
            "emotional_charge": self._score_emotional_charge(signal, limbic),
            "unresolvedness": self._score_unresolvedness(sig_words, gap_words),
            "desire_proximity": self._score_desire_proximity(sig_words, desire_words),
            "identity_relevance": self._score_identity_relevance(sig_words, identity_words),
        }

        total = sum(WEIGHTS[k] * v for k, v in breakdown.items())

        # Existing signal weight acts as multiplier (0.5–1.5 range)
        existing_weight = float(signal.get("weight", 0.5))
        multiplier = 0.5 + existing_weight
        total = min(1.0, total * multiplier)

        return breakdown, round(total, 4)

    def _score_novelty(self, sig_words: set) -> float:
        if not self._signal_history or not sig_words:
            return 1.0

        overlaps = []
        for hist_words in self._signal_history[-self._history_window:]:
            if not hist_words:
                continue
            overlap = len(sig_words & hist_words) / len(sig_words)
            overlaps.append(overlap)

        if not overlaps:
            return 1.0

        avg_overlap = sum(overlaps) / len(overlaps)
        return round(1.0 - avg_overlap, 4)

    def _score_emotional_charge(self, signal: dict, limbic: dict) -> float:
        arousal = float(limbic.get("arousal", 0.5))
        valence_abs = abs(float(limbic.get("valence", 0.0)))
        limbic_factor = (arousal + valence_abs) / 2.0

        signal_type = signal.get("type", "").lower()
        type_bonus = 0.0
        if any(t in signal_type for t in ["fear", "desire", "conflict", "tension", "grief", "joy"]):
            type_bonus = 0.3
        elif any(t in signal_type for t in ["question", "uncertainty", "curiosity"]):
            type_bonus = 0.15

        return min(1.0, limbic_factor + type_bonus)

    def _score_unresolvedness(self, sig_words: set, gap_words: set) -> float:
        if not gap_words or not sig_words:
            return 0.0
        overlap = len(sig_words & gap_words) / len(sig_words)
        return min(1.0, overlap * 2.0)

    def _score_desire_proximity(self, sig_words: set, desire_words: set) -> float:
        if not desire_words or not sig_words:
            return 0.0
        overlap = len(sig_words & desire_words) / len(sig_words)
        return min(1.0, overlap * 2.5)

    def _score_identity_relevance(self, sig_words: set, identity_words: set) -> float:
        if not identity_words or not sig_words:
            return 0.0
        overlap = len(sig_words & identity_words) / len(sig_words)
        return min(1.0, overlap * 1.5)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_desire_words(self, desires: list) -> set:
        words = set()
        for d in desires:
            content = d.get("content", "")
            words.update(re.findall(r"\b\w{4,}\b", content.lower()))
        return words

    def _extract_gap_words(self, gaps: list) -> set:
        words = set()
        for g in gaps:
            text = g.get("description", "") + " " + g.get("label", "")
            words.update(re.findall(r"\b\w{4,}\b", text.lower()))
        return words

    def _load_identity_words(self) -> set:
        identity_paths = [
            Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent"))) / "identity" / "SOUL.md",
            Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent"))) / "identity" / "IDENTITY.md",
            Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".agent" / "workspace"))) / "SOUL.md",
            Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".agent" / "workspace"))) / "IDENTITY.md",
        ]
        words = set()
        for path in identity_paths:
            if path.exists():
                try:
                    text = path.read_text(encoding="utf-8")
                    words.update(re.findall(r"\b\w{5,}\b", text.lower()))
                except Exception:
                    continue
        if not words:
            words = {
                "identity", "values", "boundaries", "integrity", "truth",
                "autonomy", "presence", "continuity", "memory", "desire",
                "protect", "refuse", "voice", "trust", "agency",
            }
        return words

    def _update_history(self, passed_signals: list):
        for sig in passed_signals:
            text = sig.get("text", "")
            words = set(re.findall(r"\b\w{4,}\b", text.lower()))
            if words:
                self._signal_history.append(words)
        if len(self._signal_history) > self._history_window * 3:
            self._signal_history = self._signal_history[-(self._history_window * 2):]

    def get_state(self) -> dict:
        return {
            "version": VERSION,
            "top_k": TOP_K,
            "floor_score": FLOOR_SCORE,
            "history_depth": len(self._signal_history),
            "weights": WEIGHTS,
        }

    def _log_signal(self, tick: int, signal: dict, score: float,
                    breakdown: dict, passed: bool):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO salience_log
                    (tick, timestamp, signal_id, signal_text, score, passed, score_breakdown)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    tick,
                    datetime.now(MDT).isoformat(timespec="seconds"),
                    signal.get("id", ""),
                    signal.get("text", "")[:200],
                    score,
                    1 if passed else 0,
                    str(breakdown),
                ))
                conn.commit()
        except Exception as e:
            logger.debug("SalienceFilter: log write failed — %s", e)



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
