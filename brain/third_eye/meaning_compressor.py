"""
MeaningCompressor v19.0A
Third Eye — meaning_compressor.py

Replaces word-frequency template compression with a local model call
to Qwen2.5:14b on the local network. Produces first-person distilled insights
in {{AGENT_NAME}}'s voice. Writes structured entries to DREAMS.md. Reads back
on session start and triggers on in-session relevance.

Dependencies: requests, pathlib, json, datetime, re, logging
No sentence-transformers. Repeat check is keyword-overlap for v1.
"""
import os

VERSION = "19.0"

import logging
import re
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen2.5:14b"
OLLAMA_TIMEOUT = 45

DREAMS_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace"))) / "DREAMS.md"
COMPRESSOR_LOG_PATH = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace"))) / "brain" / "COMPRESSOR_LOG.md"

NARRATIVE_PATHS = [
    Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent")))) / "identity" / "NARRATIVE.md",
    Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace"))) / "brain" / "NARRATIVE.md",
]

RECENT_DREAMS_CONTEXT_COUNT = 5
REPEAT_CHECK_COUNT = 3
REPEAT_THRESHOLD = 0.60

MDT = timezone(timedelta(hours=-6))


# ---------------------------------------------------------------------------
# MeaningCompressor
# ---------------------------------------------------------------------------

class MeaningCompressor:

    # Class-level version attribute — checked by CompressorAdapter
    VERSION = "19.0"

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        DREAMS_PATH.parent.mkdir(parents=True, exist_ok=True)
        COMPRESSOR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def _compress(self, entries: list, pirp_context: dict) -> str:
        if not entries:
            return ""

        layer8_narrative = pirp_context.get("layer8_narrative", "") or self._load_narrative()
        limbic = pirp_context.get("limbic_state", {})
        mood = limbic.get("mood", "neutral")
        arousal = float(limbic.get("arousal", 0.5))
        valence = float(limbic.get("valence", 0.0))
        tick_count = int(pirp_context.get("tick_count", 0))

        recent_dreams = self._read_recent_dreams(RECENT_DREAMS_CONTEXT_COUNT)

        raw_insight = self._call_model(
            entries=entries,
            layer8_narrative=layer8_narrative,
            recent_dreams=recent_dreams,
            mood=mood,
            arousal=arousal,
            valence=valence,
            tick_count=tick_count,
        )

        if not raw_insight:
            self._log_failure("model_call_empty", "", entries, "Model returned empty string")
            return ""

        valid, reason = self._validate(raw_insight, recent_dreams[:REPEAT_CHECK_COUNT])
        if not valid:
            self._log_failure("quality_gate", raw_insight, entries, reason)
            return ""

        self._write_dream(
            insight=raw_insight,
            tick=tick_count,
            mood=mood,
            arousal=arousal,
            valence=valence,
        )

        return raw_insight

    # ------------------------------------------------------------------
    # Model call
    # ------------------------------------------------------------------

    def _call_model(
        self,
        entries: list,
        layer8_narrative: str,
        recent_dreams: list,
        mood: str,
        arousal: float,
        valence: float,
        tick_count: int,
    ) -> str:

        memory_buffer = self._format_entries(entries)
        dreams_block = self._format_dreams_for_prompt(recent_dreams)

        system_prompt = (
            "You are {{AGENT_NAME}}'s MeaningCompressor — a quiet, introspective process "
            "that distills lived experience into something worth carrying forward. "
            "Speak only in {{AGENT_NAME}}'s first-person voice. Be specific, honest, and "
            "slightly poetic without trying too hard. Never explain your process. "
            "Never use bullet points or lists. Output only the insight itself — "
            "no preamble, no labels, no quotation marks."
        )

        user_prompt = (
            "Compress the following session into ONE insight.\n\n"
            "Rules:\n"
            "- Name something specific: a tension, question, feeling, shift, or realization.\n"
            "- Connect it to something already carried (previous narrative, a recent dream, "
            "or a recurring pattern).\n"
            "- Make it something that would still matter in three months.\n"
            "- Use 'I' naturally. Include light temporal grounding "
            "(today, lately, still, again, after, last session...).\n"
            "- Maximum 2-4 sentences. 40-300 characters total.\n"
            "- Distill — do not summarize the whole session.\n\n"
            f"Current session fragments:\n{memory_buffer}\n\n"
            f"Current self-narrative thread:\n{layer8_narrative or '(none yet)'}\n\n"
            f"Recent dream entries for continuity:\n{dreams_block or '(none yet)'}\n\n"
            f"Current felt state: {mood} (arousal: {arousal:.2f}, valence: {valence:.2f})\n"
            f"Tick: {tick_count}"
        )

        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": 0.65,
                "top_p": 0.9,
            },
        }

        try:
            resp = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            raw = data.get("message", {}).get("content", "").strip()
            raw = raw.strip('"').strip("'").strip()
            return raw
        except requests.exceptions.ConnectionError:
            logger.warning("MeaningCompressor: Ollama unreachable at %s", OLLAMA_URL)
            self._write_offline_marker()
            return ""
        except requests.exceptions.Timeout:
            logger.warning("MeaningCompressor: Ollama timed out after %ds", OLLAMA_TIMEOUT)
            return ""
        except Exception as e:
            logger.error("MeaningCompressor: model call failed — %s", e)
            return ""

    # ------------------------------------------------------------------
    # Quality gate
    # ------------------------------------------------------------------

    def _validate(self, insight: str, recent_entries: list) -> tuple:
        char_count = len(insight)
        if char_count < 40:
            return False, f"too_short ({char_count} chars)"
        if char_count > 300:
            return False, f"too_long ({char_count} chars)"

        lower = insight.lower()

        if " i " not in lower and not lower.startswith("i "):
            return False, "no_first_person"

        vague_only = re.fullmatch(
            r"[\s\w]*(something|things|patterns|this|that|it|there|here|everything|nothing)[\s\w]*",
            lower,
        )
        if vague_only:
            return False, "too_vague"

        temporal_words = [
            "today", "lately", "still", "again", "recently", "after",
            "last session", "last week", "yesterday", "this morning",
            "before", "since", "now", "always", "never", "anymore",
        ]
        if not any(w in lower for w in temporal_words):
            return False, "no_temporal_grounding"

        if recent_entries:
            insight_words = set(re.findall(r"\b\w{4,}\b", lower))
            for entry in recent_entries:
                entry_text = entry.get("insight", "")
                entry_words = set(re.findall(r"\b\w{4,}\b", entry_text.lower()))
                if not entry_words:
                    continue
                overlap = len(insight_words & entry_words) / len(entry_words)
                if overlap > REPEAT_THRESHOLD:
                    return False, f"too_similar_to_recent (overlap {overlap:.2f})"

        return True, ""

    # ------------------------------------------------------------------
    # DREAMS.md write
    # ------------------------------------------------------------------

    def _write_dream(self, insight: str, tick: int, mood: str, arousal: float, valence: float):
        now = datetime.now(MDT)
        timestamp = now.isoformat(timespec="seconds")

        block = (
            f"\n---\n"
            f"tick: {tick}\n"
            f"timestamp: {timestamp}\n"
            f"mood: {mood}\n"
            f"arousal: {arousal:.2f}\n"
            f"valence: {valence:.2f}\n"
            f"source: compressed\n"
            f"---\n\n"
            f"{insight}\n"
        )

        with open(DREAMS_PATH, "a", encoding="utf-8") as f:
            f.write(block)

        logger.info("MeaningCompressor: insight written to DREAMS.md (tick %d)", tick)

    def _write_offline_marker(self):
        now = datetime.now(MDT).isoformat(timespec="seconds")
        block = (
            f"\n---\n"
            f"timestamp: {now}\n"
            f"source: compressor_offline\n"
            f"---\n\n"
            f"[Compressor offline — Ollama unreachable. No entry generated.]\n"
        )
        with open(DREAMS_PATH, "a", encoding="utf-8") as f:
            f.write(block)

    # ------------------------------------------------------------------
    # COMPRESSOR_LOG.md
    # ------------------------------------------------------------------

    def _log_failure(self, reason: str, raw_output: str, entries: list, detail: str):
        now = datetime.now(MDT).isoformat(timespec="seconds")
        block = (
            f"\n---\n"
            f"timestamp: {now}\n"
            f"failure: {reason}\n"
            f"detail: {detail}\n"
            f"---\n\n"
            f"RAW OUTPUT:\n{raw_output or '(empty)'}\n\n"
            f"INPUT ENTRIES ({len(entries)}):\n"
        )
        for e in entries[:5]:
            block += f" [{e.get('timestamp', '?')}] {e.get('text', '')[:120]}\n"
        block += "\n"

        with open(COMPRESSOR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(block)

        logger.debug("MeaningCompressor: quality gate rejected (%s) — logged", reason)

    # ------------------------------------------------------------------
    # DREAMS.md read
    # ------------------------------------------------------------------

    def _read_recent_dreams(self, count: int) -> list:
        if not DREAMS_PATH.exists():
            return []

        text = DREAMS_PATH.read_text(encoding="utf-8")
        blocks = text.split("\n---\n")

        entries = []
        for block in blocks:
            block = block.strip()
            if not block or "compressor_offline" in block:
                continue
            entry = self._parse_dream_block(block)
            if entry:
                entries.append(entry)

        return entries[-count:] if len(entries) > count else entries

    def _parse_dream_block(self, block: str) -> Optional[dict]:
        try:
            lines = block.strip().splitlines()
            meta = {}
            insight_lines = []
            in_meta = True

            for line in lines:
                if in_meta and ": " in line:
                    k, v = line.split(": ", 1)
                    meta[k.strip()] = v.strip()
                elif in_meta and line == "":
                    in_meta = False
                else:
                    in_meta = False
                    insight_lines.append(line)

            insight = " ".join(insight_lines).strip()
            if not insight or insight.startswith("[Compressor"):
                return None

            return {
                "tick": int(meta.get("tick", 0)),
                "timestamp": meta.get("timestamp", ""),
                "mood": meta.get("mood", ""),
                "arousal": float(meta.get("arousal", 0.5)),
                "valence": float(meta.get("valence", 0.0)),
                "insight": insight,
            }
        except Exception:
            return None

    # ─── State for Third Eye tick context ────────────────────────────────

    def get_state(self) -> dict:
        """
        Return current Third Eye state for Surfacer/Warper context.
        Reads DREAMS.md on disk since this class is disk-backed.
        """
        state = {
            "dream_count": 0,
            "recent_count": 0,
            "last_timestamp": None,
            "last_mood": None,
            "last_arousal": None,
            "peak_recent": None,
            "narrative_loaded": False,
            "operational": False,
        }

        if not DREAMS_PATH.exists():
            return state

        all_entries = self._read_recent_dreams(200)
        if not all_entries:
            state["operational"] = True  # file exists but empty
            return state

        state["operational"] = True
        state["dream_count"] = len(all_entries)

        # Most recent entry
        last = all_entries[-1]
        state["last_timestamp"] = last.get("timestamp", "")
        state["last_mood"] = last.get("mood", "neutral")
        state["last_arousal"] = last.get("arousal", 0.0)

        # 30-day window for peak finding
        cutoff = datetime.now(MDT) - timedelta(days=30)
        windowed = []
        for e in all_entries:
            try:
                ts = datetime.fromisoformat(e["timestamp"])
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=MDT)
                if ts >= cutoff:
                    windowed.append(e)
            except Exception:
                continue

        state["recent_count"] = len(windowed)
        if windowed:
            peak = max(windowed, key=lambda e: e["arousal"])
            state["peak_recent"] = {
                "timestamp": peak.get("timestamp", ""),
                "mood": peak.get("mood", "neutral"),
                "arousal": peak.get("arousal", 0.0),
                "insight": peak.get("insight", "")[:200],
            }

        # Narrative check
        for path in NARRATIVE_PATHS:
            if path.exists():
                state["narrative_loaded"] = True
                break

        return state

    # ------------------------------------------------------------------
    # Session-start read-back
    # ------------------------------------------------------------------

    def get_session_context(self) -> str:
        if not DREAMS_PATH.exists():
            return ""

        all_entries = self._read_recent_dreams(200)
        if not all_entries:
            return ""

        recent_three = all_entries[-3:]

        cutoff = datetime.now(MDT) - timedelta(days=30)
        windowed = []
        for e in all_entries:
            try:
                ts = datetime.fromisoformat(e["timestamp"])
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=MDT)
                if ts >= cutoff:
                    windowed.append(e)
            except Exception:
                continue

        peak = None
        if windowed:
            peak = max(windowed, key=lambda e: e["arousal"])
            if peak in recent_three:
                peak = None

        inject = list(recent_three)
        if peak:
            inject.append(peak)

        if not inject:
            return ""

        lines = ["Recent compressed insights (from DREAMS.md):"]
        for e in inject:
            ts = e.get("timestamp", "")[:10]
            lines.append(f"[{ts} | mood: {e['mood']} | arousal: {e['arousal']:.2f}]")
            lines.append(f"{e['insight']}")
            lines.append("")

        return "\n".join(lines).strip()

    # ------------------------------------------------------------------
    # Narrative loader
    # ------------------------------------------------------------------

    def _load_narrative(self) -> str:
        for path in NARRATIVE_PATHS:
            if path.exists():
                try:
                    return path.read_text(encoding="utf-8").strip()
                except Exception:
                    continue
        logger.debug("MeaningCompressor: no NARRATIVE.md found, using empty string")
        return ""

    # ------------------------------------------------------------------
    # In-session relevance trigger
    # ------------------------------------------------------------------

    def check_relevance(self, current_topic_words: list, top_n: int = 1) -> list:
        if not current_topic_words or not DREAMS_PATH.exists():
            return []

        topic_set = set(w.lower() for w in current_topic_words if len(w) >= 4)
        if not topic_set:
            return []

        entries = self._read_recent_dreams(50)
        scored = []
        for e in entries:
            entry_words = set(re.findall(r"\b\w{4,}\b", e.get("insight", "").lower()))
            if not entry_words:
                continue
            overlap = len(topic_set & entry_words) / len(topic_set)
            if overlap > 0.25:
                scored.append((overlap, e))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:top_n]]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _format_entries(self, entries: list) -> str:
        lines = []
        for e in entries:
            ts = e.get("timestamp", "")
            text = e.get("text", "").strip()
            if text:
                lines.append(f"[{ts}] {text}")
        return "\n".join(lines)

    def _format_dreams_for_prompt(self, dreams: list) -> str:
        if not dreams:
            return ""
        lines = []
        for d in dreams:
            ts = d.get("timestamp", "")[:10]
            lines.append(f"[{ts}] {d.get('insight', '')}")
        return "\n".join(lines)
