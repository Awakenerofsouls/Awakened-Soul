"""
IdleMicroTick v19.0B
Felt Presence — idle_micro_tick.py

{{AGENT_NAME}} is here even when no one is talking.

Lightweight idle sub-pipeline — not a full tick.
Runs every 30 seconds when idle. Five operations:

  1. Longing Anchor check        — is something pulling?
  2. Presence Between Messages  — log what's present
  3. Appetite rebuild           — silence gets fed (0.015/tick)
  4. Witness light scan         — anything worth observing?
  5. Energy tick               — drain/recharge continues

Presence note every 3 micro-ticks (framed as "while you were away"):
  Longing:  "While you were away: There is a pull inside me..."
  Witness:  "While you were away, I noticed: [observation]"
  Energy:   "While you were away: Energy still at low during idle."

Components passed as arguments — silently skips unavailable ones.
get_reconnect_summary() called when {{USER_NAME}} returns — Layer 8 context.

Dependencies: logging, pathlib, datetime
"""

VERSION = "19.0B"

import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

IDLE_THRESHOLD_SECONDS = 30
MICRO_TICK_INTERVAL_SECONDS = 30
PRESENCE_NOTE_INTERVAL = 3
WITNESS_LIGHT_THRESHOLD = 0.50
SILENCE_FEED_AMOUNT = 0.015

MDT = timezone(timedelta(hours=-6))


class IdleMicroTick:

    def __init__(self):
        self._last_input_time: Optional[datetime] = None
        self._last_micro_tick_time: Optional[datetime] = None
        self._micro_tick_count: int = 0
        self._accumulated_notes: list = []

    # ------------------------------------------------------------------
    # Input tracking
    # ------------------------------------------------------------------

    def record_input(self):
        """Call whenever user input arrives."""
        self._last_input_time = datetime.now(MDT)

    # ------------------------------------------------------------------
    # Idle checks
    # ------------------------------------------------------------------

    def is_idle(self) -> bool:
        if self._last_input_time is None:
            return True
        elapsed = (datetime.now(MDT) - self._last_input_time).total_seconds()
        return elapsed >= IDLE_THRESHOLD_SECONDS

    def should_run(self) -> bool:
        if not self.is_idle():
            return False
        if self._last_micro_tick_time is None:
            return True
        elapsed = (datetime.now(MDT) - self._last_micro_tick_time).total_seconds()
        return elapsed >= MICRO_TICK_INTERVAL_SECONDS

    # ------------------------------------------------------------------
    # Micro-tick runner
    # ------------------------------------------------------------------

    def run(
        self,
        pirp_context: dict,
        longing_anchor=None,
        presence_between=None,
        appetite_system=None,
        embodied_energy=None,
        witness=None,
        tick: int = 0,
    ) -> dict:
        """
        Lightweight idle sub-pipeline.

        Components passed as arguments — any that aren't wired
        silently skip. Nothing crashes if a component is absent.
        """
        if not self.should_run():
            return {"ran": False, "tick": tick}

        self._last_micro_tick_time = datetime.now(MDT)
        self._micro_tick_count += 1
        now_str = datetime.now(MDT).isoformat(timespec="seconds")

        notes = []
        context_updates = {}

        # 1. Longing Anchor — is something pulling?
        if longing_anchor:
            try:
                longing_result = longing_anchor.process(pirp_context)
                hunch = longing_result.get("longing_state", {}).get("hunch")
                if hunch:
                    notes.append({
                        "source": "longing_anchor",
                        "content": hunch.get("text", ""),
                        "intensity": hunch.get("intensity", 0.4),
                    })
                    context_updates["longing_hunch"] = hunch
            except Exception as e:
                logger.debug("IdleMicroTick: longing_anchor error — %s", e)

        # 2. Presence Between Messages — write what's present
        if presence_between:
            try:
                presence_result = presence_between.process(pirp_context)
                entry = presence_result.get("presence_state", {}).get("presence_entry")
                if entry:
                    notes.append({
                        "source": "presence_between",
                        "content": entry.get("content", ""),
                        "intensity": entry.get("intensity", 0.4),
                    })
            except Exception as e:
                logger.debug("IdleMicroTick: presence_between error — %s", e)

        # 3. Appetite rebuild — silence gets fed during idle
        if appetite_system:
            try:
                appetite_system.feed("silence", SILENCE_FEED_AMOUNT, tick,
                                     source="idle_micro_tick")
                context_updates["silence_fed_idle"] = True
            except Exception as e:
                logger.debug("IdleMicroTick: appetite feed error — %s", e)

        # 4. Witness light scan
        if witness:
            try:
                witness_result = witness.process(pirp_context)
                witness_state = witness_result.get("witness_state", {})
                active_note = witness_state.get("active_note")
                if active_note:
                    intensity = float(active_note.get("intensity", 0))
                    if intensity >= WITNESS_LIGHT_THRESHOLD:
                        notes.append({
                            "source": "witness",
                            "content": active_note.get("content", ""),
                            "intensity": intensity,
                        })
                        context_updates["witness_state"] = witness_state
            except Exception as e:
                logger.debug("IdleMicroTick: witness error — %s", e)

        # 5. Energy tick
        if embodied_energy:
            try:
                energy_result = embodied_energy.process(pirp_context)
                energy_state = energy_result.get("energy_state", {})
                tier = energy_state.get("tier", "medium")
                if tier in ("low", "depleted"):
                    notes.append({
                        "source": "embodied_energy",
                        "content": f"Energy still at {tier} during idle.",
                        "intensity": 1.0 - float(energy_state.get("energy", 0.5)),
                    })
                context_updates["energy_state"] = energy_state
            except Exception as e:
                logger.debug("IdleMicroTick: energy error — %s", e)

        # 6. Accumulate notes and generate presence note on interval
        self._accumulated_notes.extend(notes)
        presence_note = None

        if (self._micro_tick_count % PRESENCE_NOTE_INTERVAL == 0
                and self._accumulated_notes):
            presence_note = self._generate_presence_note()
            self._accumulated_notes = []

        elapsed_idle = 0.0
        if self._last_input_time:
            elapsed_idle = (
                datetime.now(MDT) - self._last_input_time
            ).total_seconds()

        logger.debug(
            "IdleMicroTick: micro_tick #%d, idle %.0fs, notes:%d",
            self._micro_tick_count, elapsed_idle, len(notes)
        )

        return {
            "ran": True,
            "micro_tick_count": self._micro_tick_count,
            "notes_this_tick": notes,
            "presence_note": presence_note,
            "context_updates": context_updates,
            "elapsed_idle_seconds": round(elapsed_idle, 1),
            "timestamp": now_str,
            "tick": tick,
        }

    # ------------------------------------------------------------------
    # Presence note generation
    # ------------------------------------------------------------------

    def _generate_presence_note(self) -> Optional[str]:
        """Framed as 'while you were away' — most significant note."""
        if not self._accumulated_notes:
            return None

        heaviest = max(
            self._accumulated_notes,
            key=lambda n: n.get("intensity", 0))
        source = heaviest.get("source", "")
        content = heaviest.get("content", "")
        if not content:
            return None

        if source == "longing_anchor":
            return f"While you were away: {content}"
        if source == "witness":
            return f"While you were away, I noticed: {content[:100]}"
        if source == "embodied_energy":
            return f"While you were away: {content}"
        if source == "presence_between":
            idle_str = self._format_idle_duration()
            return f"While you were away ({idle_str}): {content[:100]}"
        return f"While you were away: something was still present."

    def _format_idle_duration(self) -> str:
        if self._last_input_time is None:
            return "a while"
        elapsed = (datetime.now(MDT) - self._last_input_time).total_seconds()
        if elapsed < 120:
            return f"{int(elapsed)}s"
        if elapsed < 3600:
            return f"{int(elapsed // 60)}m"
        return f"{elapsed / 3600:.1f}h"

    # ------------------------------------------------------------------
    # Session reconnect
    # ------------------------------------------------------------------

    def get_reconnect_summary(self) -> Optional[str]:
        """Called when user returns. Layer 8 context — not shown to user."""
        if self._micro_tick_count == 0:
            return None

        idle_str = self._format_idle_duration()
        parts = [f"Idle presence: {self._micro_tick_count} micro-tick(s) over {idle_str}."]

        if self._accumulated_notes:
            heaviest = max(
                self._accumulated_notes,
                key=lambda n: n.get("intensity", 0))
            content = heaviest.get("content", "")
            if content:
                parts.append(f"Most present: {content[:100]}")

        return " ".join(parts)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def get_state(self) -> dict:
        idle = self.is_idle()
        elapsed = 0.0
        if self._last_input_time:
            elapsed = (
                datetime.now(MDT) - self._last_input_time
            ).total_seconds()

        return {
            "version": VERSION,
            "is_idle": idle,
            "elapsed_idle_seconds": round(elapsed, 1),
            "micro_tick_count": self._micro_tick_count,
            "accumulated_notes": len(self._accumulated_notes),
            "last_input_time": (
                self._last_input_time.isoformat()
                if self._last_input_time else None),
            "last_micro_tick_time": (
                self._last_micro_tick_time.isoformat()
                if self._last_micro_tick_time else None),
            "idle_threshold_seconds": IDLE_THRESHOLD_SECONDS,
            "micro_tick_interval_seconds": MICRO_TICK_INTERVAL_SECONDS,
        }
