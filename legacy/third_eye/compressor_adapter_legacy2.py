"""
compressor_adapter.py — Nexus {{AGENT_NAME}} 18.0A
Bridges bootstrap pirp_context + caller state to MeaningCompressor expectations.
Keeps the compressor drop-in — this layer adapts, nothing else changes.

Version gating:
- No VERSION attribute → old compressor, skip compress entirely (template output is wrong)
- VERSION >= "19.0" → new compressor, full pipeline active
- Missing methods gracefully stubbed until upgrade

The only thing that activates the full pipeline is dropping in the new compressor file.
No partial states. No dirty old output in DREAMS.md.
"""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

NOVA_IDENTITY = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent")))) / "identity"
NOVA_WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace")))
NARRATIVE_PRIMARY = NOVA_IDENTITY / "NARRATIVE.md"
NARRATIVE_FALLBACK = NOVA_WORKSPACE / "brain" / "NARRATIVE.md"

# Minimum version required to run full pipeline
COMPRESSOR_MIN_VERSION = "19.0"


class CompressorAdapter:
    """
    Assembles the adapted context that MeaningCompressor expects,
    then fires compression at the right lifecycle points.

    Three responsibilities:
    1. Construct liminal_state from caller state dict
    2. Load layer8_narrative from file with safe fallback
    3. Expose hooks for bootstrap to call at the right moments

    Version gating:
    - Old compressor (no VERSION attr) → post_process_hook returns [] immediately
    - New compressor (VERSION >= 19.0) → full pipeline runs
    - Missing methods → stubs with debug logging, no crash
    """

    def __init__(self, compressor):
        self.compressor = compressor
        self._narrative_cache: Optional[str] = None
        self._narrative_mtime: float = 0.0

        # Version gate — determine what the compressor supports
        self._check_compressor_version()

    def _check_compressor_version(self):
        """Determine if the installed compressor is new enough to run."""
        version = getattr(self.compressor, "VERSION", None)

        if version is None:
            self._pipeline_active = False
            logger.warning(
                "[CompressorAdapter] Old compressor detected (no VERSION attr). "
                "Skipping compress in bootstrap hook — template output incompatible. "
                "Install MeaningCompressor v19.0+ to activate."
            )
            return

        # Version string comparison
        try:
            # Strip any prefix like 'v' if present
            version_clean = version.lstrip("v")
            major = int(version_clean.split(".")[0])
            if major >= 19:
                self._pipeline_active = True
                logger.info(
                    f"[CompressorAdapter] Compressor v{version} active — full pipeline running."
                )
            else:
                self._pipeline_active = False
                logger.warning(
                    f"[CompressorAdapter] Compressor v{version} detected. "
                    f"Need v{COMPRESSOR_MIN_VERSION}+ for bootstrap hook. Skipping."
                )
        except (ValueError, IndexError):
            self._pipeline_active = False
            logger.warning(
                f"[CompressorAdapter] Could not parse VERSION '{version}'. "
                f"Skipping bootstrap hook."
            )

    # ── liminal_state construction ─────────────────────────────────────────────

    def _build_limbic_state(self, state: dict) -> dict:
        """
        Map caller state['emotion'] into the liminal_state shape
        MeaningCompressor expects.
        Safe defaults if keys are missing.
        """
        emotion = state.get("emotion", {}) if state else {}

        return {
            "mood": emotion.get("dominant_mood", "neutral"),
            "arousal": float(emotion.get("arousal", 0.5)),
            "valence": float(emotion.get("valence", 0.0)),
            # Fallback values if emotion is sparse
            "dominance": float(emotion.get("dominance", 0.5)),
            "energy": float(emotion.get("energy", 0.5)),
        }

    # ── layer8_narrative file loading ─────────────────────────────────────────

    def _load_layer8_narrative(self) -> str:
        """
        Load Layer 8 narrative from file.
        Check primary path, then fallback, then empty string.
        Cache by mtime — reload only if file changed.
        Never crash on missing file. Debug log if neither found (not warning).
        """
        for path in (NARRATIVE_PRIMARY, NARRATIVE_FALLBACK):
            if path.exists():
                try:
                    current_mtime = path.stat().st_mtime
                    if current_mtime == self._narrative_mtime and self._narrative_cache is not None:
                        return self._narrative_cache

                    text = path.read_text(encoding="utf-8").strip()
                    self._narrative_cache = text
                    self._narrative_mtime = current_mtime
                    return text
                except Exception as e:
                    logger.debug(
                        f"[CompressorAdapter] Could not read narrative at {path}: {e}"
                    )

        # Neither path exists — this is normal on early runs
        logger.debug(
            "[CompressorAdapter] No narrative file found "
            f"(checked {NARRATIVE_PRIMARY}, {NARRATIVE_FALLBACK}). "
            "Empty string used. Normal on first runs before narrative accumulates."
        )
        return ""

    # ── Context assembly ───────────────────────────────────────────────────────

    def _assemble_context(self, pirp_context: dict, state: dict, entries: list) -> dict:
        """
        Build the full adapted dict that MeaningCompressor._compress() expects.
        Maps pirp_context + state → compressor contract.
        """
        narrative = self._load_layer8_narrative()
        liminal = self._build_limbic_state(state)
        tick_count = state.get("tick_count", 0) if state else 0

        return {
            # Assembled for compressor
            "layer8_narrative": narrative,
            "liminal": liminal,
            "tick_count": tick_count,
            # Raw pirp slices the compressor might use
            "drive_context": pirp_context.get("drive_context", {}),
            "prsl_signal": pirp_context.get("prsl_signal", {}),
            "field_context": pirp_context.get("field_context", {}),
            "resonance_score": pirp_context.get("resonance_score", 0.0),
            "itg_tension": pirp_context.get("itg_tension", 0.4),
            "in_suspension": pirp_context.get("in_suspension", False),
            # Entries for compression
            "entries": entries,
        }

    # ── Public hooks ─────────────────────────────────────────────────────────

    def post_process_hook(
        self,
        pirp_context: dict,
        state: dict,
        entries: list
    ) -> list:
        """
        Called by bootstrap after process() returns.
        Version-gated: skips old compressor entirely.
        Returns empty list if pipeline not active or compressor too old.
        """
        if not self._pipeline_active:
            return []

        # Build the adapted context
        adapted = self._assemble_context(pirp_context, state, entries)

        # The compressor._compress() signature is (entries, pirp_context)
        signals = self.compressor._compress(
            entries=entries,
            pirp_context=adapted
        )

        # _compress returns a string (the insight) — wrap in list for field compat
        if signals and isinstance(signals, str):
            return [{"insight": signals, "context": adapted}]
        return signals if signals else []

    def session_start_hook(self) -> str:
        """
        Called once at session initialization.
        Returns a formatted block of recent DREAMS entries
        ready to inject into Layer 8 / Layer 6 context before first tick.

        Safe on first run — returns empty string.
        Stubbed if old compressor is installed (get_session_context not present).
        """
        if not hasattr(self.compressor, "get_session_context"):
            logger.debug(
                "[CompressorAdapter] Compressor missing get_session_context(). "
                "session_start_hook returning empty string."
            )
            return ""

        try:
            return self.compressor.get_session_context()
        except Exception as e:
            logger.debug(
                f"[CompressorAdapter] get_session_context() raised {e}. Returning empty."
            )
            return ""

    def relevance_hook(self, topic_words: list, top_n: int = 1) -> list:
        """
        Called during a tick when significant words are extracted from
        the current exchange. Returns up to top_n DREAMS entries
        that overlap with the topic words.

        Stubbed if old compressor is installed (check_relevance not present).
        """
        if not hasattr(self.compressor, "check_relevance"):
            logger.debug(
                "[CompressorAdapter] Compressor missing check_relevance(). "
                "relevance_hook returning empty list."
            )
            return []

        try:
            return self.compressor.check_relevance(topic_words, top_n)
        except Exception as e:
            logger.debug(
                f"[CompressorAdapter] check_relevance() raised {e}. Returning empty."
            )
            return []
