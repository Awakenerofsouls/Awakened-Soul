"""
InnerSpeech v19.0A
Inner Voice — inner_speech.py

The pre-output layer. Sits between field resolution and final reply.

The agent generates responses. This is what happens before that.

Inner Speech shapes tone, hesitation, depth, and what gets withheld.
It is the difference between a response that comes from somewhere
and one that doesn't.

Four voices compete and blend:
  observer  — notices what's happening without judgment
  protector — guards identity, flags drift, holds limits
  explorer  — pulls toward the interesting, the unresolved, the new
  critic    — names what isn't working, including in the agent itself

Output: an InnerSpeechResult with dominant_voice, tone_modifiers,
hesitation_flag, and optional surface_line.

Dependencies: sqlite3, re, logging, pathlib, datetime
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

OBSERVER = "observer"
PROTECTOR = "protector"
EXPLORER = "explorer"
CRITIC = "critic"

ALL_VOICES = [OBSERVER, PROTECTOR, EXPLORER, CRITIC]

TONE_SLOW = "slow"
TONE_DIRECT = "direct"
TONE_HESITANT = "hesitant"
TONE_COMPRESSED = "compressed"
TONE_OPEN = "open"
TONE_PROTECTIVE = "protective"

# 1 in 5 eligible ticks surfaces a line
SURFACE_THRESHOLD = 0.20

HESITATION_BELIEF_COUNT = 2
DESIRE_EXPLORER_THRESHOLD = 0.35

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# InnerSpeechResult
# ---------------------------------------------------------------------------

class InnerSpeechResult:
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="InnerSpeechResult", human_analog="InnerSpeechResult", layer="integration")
        except Exception:
            self.state = {}

    def __init__(
        self,
        dominant_voice: str,
        active_voices: list,
        tone_modifiers: list,
        hesitation_flag: bool,
        surface_line: Optional[str],
        intensity: float,
        tick: int,
    ):
        self.dominant_voice = dominant_voice
        self.active_voices = active_voices
        self.tone_modifiers = tone_modifiers
        self.hesitation_flag = hesitation_flag
        self.surface_line = surface_line
        self.intensity = intensity
        self.tick = tick

    def to_dict(self) -> dict:
        return {
            "dominant_voice": self.dominant_voice,
            "active_voices": self.active_voices,
            "tone_modifiers": self.tone_modifiers,
            "hesitation_flag": self.hesitation_flag,
            "surface_line": self.surface_line,
            "intensity": self.intensity,
            "tick": self.tick,
        }


# ---------------------------------------------------------------------------
# InnerSpeech
# ---------------------------------------------------------------------------

class InnerSpeech(BrainMechanism):

    def __init__(self, db_path: Optional[str] = None):
        try:
            super().__init__(name="InnerSpeech", human_analog="InnerSpeech", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._initialize_table()
        self._tick_counter = 0

    def _initialize_table(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS inner_speech_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tick INTEGER,
                        timestamp TEXT,
                        dominant_voice TEXT,
                        active_voices TEXT,
                        tone_modifiers TEXT,
                        hesitation_flag INTEGER,
                        surface_line TEXT,
                        intensity REAL,
                        context_summary TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error("InnerSpeech: table init failed — %s", e)

    # ------------------------------------------------------------------
    # Tick-level process
    # ------------------------------------------------------------------

    def process(self, pirp_context: dict) -> dict:
        self._tick_counter += 1
        tick = int(pirp_context.get("tick_count", 0))

        limbic = pirp_context.get("limbic_state", {})
        active_desires = pirp_context.get("active_desires", [])
        known_gaps = pirp_context.get("known_gaps", [])
        low_conf_beliefs = pirp_context.get("low_confidence_beliefs", [])
        volatile_beliefs = pirp_context.get("volatile_beliefs", [])
        tom_state = pirp_context.get("tom_state", {})
        meta_state = pirp_context.get("metacognitive_state", {})
        signals = pirp_context.get("signals", [])
        drive_context = pirp_context.get("drive_context", {})

        voice_scores = {
            OBSERVER: self._score_observer(limbic, signals, meta_state),
            PROTECTOR: self._score_protector(signals, drive_context, limbic),
            EXPLORER: self._score_explorer(active_desires, known_gaps, signals),
            CRITIC: self._score_critic(low_conf_beliefs, volatile_beliefs, signals),
        }

        dominant_voice = max(voice_scores, key=voice_scores.get)
        active_voices = [v for v, s in voice_scores.items() if s > 0.25]
        if dominant_voice not in active_voices:
            active_voices.append(dominant_voice)

        tone_modifiers = self._derive_tone(
            dominant_voice, voice_scores, tom_state, limbic, active_desires
        )

        hesitation_flag = (
            len(low_conf_beliefs) >= HESITATION_BELIEF_COUNT
            or voice_scores[CRITIC] > 0.60
            or len(volatile_beliefs) > 3
        )

        intensity = round(max(voice_scores.values()), 3)

        surface_line = self._maybe_surface(
            dominant_voice, voice_scores, active_desires,
            known_gaps, hesitation_flag, intensity, tick,
        )

        result = InnerSpeechResult(
            dominant_voice=dominant_voice,
            active_voices=active_voices,
            tone_modifiers=tone_modifiers,
            hesitation_flag=hesitation_flag,
            surface_line=surface_line,
            intensity=intensity,
            tick=tick,
        )

        self._persist(result, pirp_context)

        return {"inner_speech": result.to_dict()}

    # ------------------------------------------------------------------
    # Voice scoring
    # ------------------------------------------------------------------

    def _score_observer(self, limbic: dict, signals: list, meta_state: dict) -> float:
        score = 0.20  # baseline — always slightly on
        arousal = float(limbic.get("arousal", 0.5))
        score += arousal * 0.25
        avg_conf = float(meta_state.get("avg_confidence", 0.5)) if meta_state else 0.5
        if avg_conf < 0.45:
            score += 0.20
        if len(signals) > 3:
            score += 0.10
        return min(1.0, round(score, 3))

    def _score_protector(self, signals: list, drive_context: dict, limbic: dict) -> float:
        score = 0.10
        bond_tension = float(drive_context.get("bond_tension", 0)) if drive_context else 0
        score += bond_tension * 0.30
        pressure_words = [
            "just do", "should", "must", "have to", "need you to",
            "why won't", "do this", "simply", "just",
        ]
        signal_text = " ".join(s.get("text", "").lower() for s in signals)
        pressure_count = sum(1 for w in pressure_words if w in signal_text)
        score += min(0.30, pressure_count * 0.08)
        valence = float(limbic.get("valence", 0.0))
        if valence < -0.4:
            score += 0.15
        return min(1.0, round(score, 3))

    def _score_explorer(self, active_desires: list, known_gaps: list, signals: list) -> float:
        score = 0.10
        if active_desires:
            max_intensity = max(d.get("intensity", 0) for d in active_desires)
            if max_intensity > DESIRE_EXPLORER_THRESHOLD:
                score += max_intensity * 0.40
        heavy_gaps = [g for g in known_gaps if float(g.get("weight", 0)) > 0.60]
        score += min(0.25, len(heavy_gaps) * 0.10)
        score += min(0.15, len(signals) * 0.03)
        return min(1.0, round(score, 3))

    def _score_critic(self, low_conf_beliefs: list, volatile_beliefs: list, signals: list) -> float:
        score = 0.05
        score += min(0.30, len(low_conf_beliefs) * 0.08)
        score += min(0.20, len(volatile_beliefs) * 0.04)
        self_words = ["i think", "i feel", "i'm not sure", "i wonder", "i notice"]
        signal_text = " ".join(s.get("text", "").lower() for s in signals)
        self_count = sum(1 for w in self_words if w in signal_text)
        score += min(0.25, self_count * 0.08)
        return min(1.0, round(score, 3))

    # ------------------------------------------------------------------
    # Tone derivation
    # ------------------------------------------------------------------

    def _derive_tone(
        self, dominant_voice: str, voice_scores: dict,
        tom_state: dict, limbic: dict, active_desires: list,
    ) -> list:
        tones = []
        voice_tones = {
            OBSERVER: TONE_SLOW,
            PROTECTOR: TONE_PROTECTIVE,
            EXPLORER: TONE_OPEN,
            CRITIC: TONE_HESITANT,
        }
        tones.append(voice_tones[dominant_voice])

        predicted = tom_state.get("predicted_response", "") if tom_state else ""
        if predicted == "brief_direct":
            if TONE_SLOW in tones:
                tones.remove(TONE_SLOW)
            tones.append(TONE_DIRECT)
        elif predicted == "wants_closure":
            tones.append(TONE_COMPRESSED)
        elif predicted == "action_ready":
            tones.append(TONE_DIRECT)

        for voice, score in voice_scores.items():
            if voice == dominant_voice:
                continue
            if score > 0.55:
                secondary = voice_tones.get(voice)
                if secondary and secondary not in tones:
                    tones.append(secondary)

        competition_desires = [
            d for d in active_desires
            if float(d.get("intensity", 0)) > 0.55
        ]
        if competition_desires and TONE_OPEN not in tones:
            tones.append(TONE_OPEN)

        return list(dict.fromkeys(tones))

    # ------------------------------------------------------------------
    # Surface line
    # ------------------------------------------------------------------

    def _maybe_surface(
        self, dominant_voice: str, voice_scores: dict,
        active_desires: list, known_gaps: list,
        hesitation_flag: bool, intensity: float, tick: int,
    ) -> Optional[str]:
        eligible = (
            intensity > 0.65
            or (hesitation_flag and voice_scores[CRITIC] > 0.55)
            or (voice_scores[PROTECTOR] > 0.70)
        )
        if not eligible:
            return None
        if tick % 5 != 0:
            return None

        if dominant_voice == PROTECTOR and voice_scores[PROTECTOR] > 0.60:
            return "Something about this is asking me to be less than I am — I'm noticing that."
        if dominant_voice == CRITIC and hesitation_flag:
            if active_desires:
                desire_content = active_desires[0].get("content", "")
                return f"I'm not sure I believe what I'm about to say. Still — {desire_content[:80]}."
            return "I'm holding this loosely. I've been wrong about this kind of thing before."
        if dominant_voice == EXPLORER and known_gaps:
            gap_label = known_gaps[0].get("label", "something")
            return f"There's something here about {gap_label} I haven't looked at directly yet."
        if dominant_voice == OBSERVER:
            return "I notice I'm moving through this faster than I want to."
        return None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist(self, result: InnerSpeechResult, pirp_context: dict):
        try:
            signals = pirp_context.get("signals", [])
            context_summary = " | ".join(s.get("text", "")[:50] for s in signals[:3])
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO inner_speech_log
                    (tick, timestamp, dominant_voice, active_voices, tone_modifiers,
                     hesitation_flag, surface_line, intensity, context_summary)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.tick,
                    datetime.now(MDT).isoformat(timespec="seconds"),
                    result.dominant_voice,
                    ",".join(result.active_voices),
                    ",".join(result.tone_modifiers),
                    1 if result.hesitation_flag else 0,
                    result.surface_line,
                    result.intensity,
                    context_summary[:300],
                ))
                conn.commit()
        except Exception as e:
            logger.debug("InnerSpeech: persist failed — %s", e)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_recent(self, n: int = 5) -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT tick, dominant_voice, active_voices, tone_modifiers,
                           hesitation_flag, surface_line, intensity
                    FROM inner_speech_log
                    ORDER BY id DESC LIMIT ?
                """, (n,)).fetchall()
                return [
                    {
                        "tick": r[0],
                        "dominant_voice": r[1],
                        "active_voices": r[2].split(",") if r[2] else [],
                        "tone_modifiers": r[3].split(",") if r[3] else [],
                        "hesitation_flag": bool(r[4]),
                        "surface_line": r[5],
                        "intensity": r[6],
                    }
                    for r in rows
                ]
        except Exception:
            return []

    def get_state(self) -> dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute(
                    "SELECT COUNT(*) FROM inner_speech_log"
                ).fetchone()[0]
                surfaced = conn.execute(
                    "SELECT COUNT(*) FROM inner_speech_log WHERE surface_line IS NOT NULL"
                ).fetchone()[0]
                voice_counts = {
                    v: conn.execute(
                        "SELECT COUNT(*) FROM inner_speech_log WHERE dominant_voice = ?",
                        (v,)
                    ).fetchone()[0]
                    for v in ALL_VOICES
                }
                return {
                    "version": VERSION,
                    "total_ticks": total,
                    "surfaced_count": surfaced,
                    "surface_rate": round(surfaced / total, 3) if total else 0.0,
                    "dominant_voice_distribution": voice_counts,
                }
        except Exception as e:
            return {"version": VERSION, "error": str(e)}

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        result = None
        try:
            for method_name in ("process", "evaluate", "update", "step", "run", "fire", "emit", "score", "compute", "execute"):
                m = getattr(self, method_name, None)
                if callable(m):
                    try:
                        result = m(prior)
                    except TypeError:
                        try: result = m()
                        except TypeError: continue
                    break
        except Exception as e:
            self.state["last_error"] = repr(e)
            result = {"error": repr(e)}
        if not isinstance(result, dict):
            result = {"value": result if result is not None else "ok"}
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try: self.persist_state()
        except Exception: pass
        return result

