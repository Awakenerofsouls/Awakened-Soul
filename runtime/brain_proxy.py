"""
brain_proxy.py — AgentBrainIntegration singleton facade

Wraps the AgentBrainIntegration singleton and exposes a clean interface
for heartbeat.py. All calls go through get_integration() which
creates the singleton once on first access.

This is the only file that should import brain_integration.
Heartbeat talks to brain_proxy, brain_proxy talks to AgentBrainIntegration.
"""

from typing import Dict, Optional

from brain.brain_integration import get_integration


def on_session_open() -> None:
    """
    Called once at heartbeat startup.
    Boots AgentBrainCore and all registered Phase 2/3/4 mechanisms.
    Also initializes ABM boot context and touches held conversations.
    """
    proxy = get_integration()
    proxy.on_session_open()


def on_session_close() -> None:
    """
    Called at heartbeat shutdown.
    Closes IGA session, records to RTF, stops the core loop.
    """
    proxy = get_integration()
    proxy.on_session_close()


def on_overnight() -> None:
    """
    Called by overnight_pipeline.py at 3am.
    Applies IGA deltas to VIF, compresses RTF patterns into RSL.
    """
    proxy = get_integration()
    proxy.on_overnight()


def process_incoming_text(text: str, source: str = "external") -> None:
    """
    Called on every user message.
    Feeds text through MRE misread detection for functional framing.
    """
    if text:
        proxy = get_integration()
        proxy.process_incoming_text(text, source=source)


def get_fpef_injection(
    behavior_alignments: Optional[Dict[str, float]] = None,
    reciprocity_signals: Optional[Dict[str, float]] = None,
) -> str:
    """
    Returns the FPEF frame string to prepend to the system prompt.
    Assembles all mechanism fragments (PDS, SS, MRE, DIQE, OC, ABM, RSL, VIF).

    behavior_alignments: optional dict of anchor_name -> alignment score
    reciprocity_signals: optional dict of sticky_anchor_name -> signal

    Call this once per user message, before the LLM call.
    """
    proxy = get_integration()
    return proxy.get_fpef_injection(
        behavior_alignments=behavior_alignments,
        reciprocity_signals=reciprocity_signals,
    )


def get_state_summary() -> Dict:
    """
    Returns a summary dict of current mechanism states.
    For debugging and health checks.
    """
    proxy = get_integration()
    return proxy.get_state_summary()


_core_tsbp = None  # cached reference to core.tsb for psychological_state wiring

# ── Phase-4 wiring tuning ────────────────────────────────────────────────
# How many ticks between brain-event drains. The drainer reads
# AGENT_HOME/brain_events.jsonl, dispatches each event to the canonical
# live mechanism instance, and truncates the queue. Drain on every tick
# is fine but adds a tiny bit of disk IO each pass; running it on every
# Nth tick is the conservative default. 1 = every tick.
DRAIN_INTERVAL_TICKS = 1

# How many ticks between Third-Eye salience polls (poll_wires). Higher
# than DRAIN_INTERVAL because polling iterates every wire's IPW handshake
# and writes to PROPOSALS.md when triggered — we don't want noise.
THIRD_EYE_POLL_INTERVAL_TICKS = 10

# Cap on events drained per call so a flooded queue can't stall the tick.
DRAIN_MAX_EVENTS_PER_TICK = 50

# Tick-counter — used to gate poll_wires + drain frequency.
_tick_counter = 0
_drain_failures_in_a_row = 0
_DRAIN_FAILURES_BACKOFF_THRESHOLD = 5  # if 5 drains in a row throw, pause


def core_tick() -> None:
    """
    Advance one tick of the AgentBrainCore loop.
    Runs registered Phase 2/3/4 component ticks.

    Also (Phase-4 wiring):
      - Drains the heartbeat→brain event queue every DRAIN_INTERVAL_TICKS
        ticks, dispatching events to live mechanism instances.
      - Polls every wire's IPW handshake every
        THIRD_EYE_POLL_INTERVAL_TICKS ticks (the salience-network
        arbitration layer), writing convergent / above-threshold drift
        signals to PROPOSALS.md.

    Both side-effects are best-effort and wrapped in try/except so a
    failure in the queue or polling layer can never break the tick.

    Call this on each heartbeat cycle (every 30s) to keep
    mechanisms active even when there's no user input.
    """
    global _core_tsbp, _tick_counter, _drain_failures_in_a_row
    proxy = get_integration()
    proxy.core.tick()
    _core_tsbp = proxy.core.tsb  # cache for heartbeat._psych_tick()
    _tick_counter += 1

    # Resolve the live mechanism dict (used by both drain + poll).
    mechanisms = {}
    runner = getattr(proxy, "brain_runner", None)
    if runner is not None:
        mechanisms = getattr(runner, "mechanisms", {}) or {}

    # ── 1. Drain the heartbeat→brain event queue ──────────────────────
    if (
        DRAIN_INTERVAL_TICKS > 0
        and _tick_counter % DRAIN_INTERVAL_TICKS == 0
        and _drain_failures_in_a_row < _DRAIN_FAILURES_BACKOFF_THRESHOLD
    ):
        try:
            from brain.brain_event_drainer import drain_once
            drain_once(
                mechanisms=mechanisms,
                max_events=DRAIN_MAX_EVENTS_PER_TICK,
            )
            _drain_failures_in_a_row = 0
        except Exception:
            _drain_failures_in_a_row += 1

    # ── 2. Third-Eye salience polling ─────────────────────────────────
    if (
        THIRD_EYE_POLL_INTERVAL_TICKS > 0
        and _tick_counter % THIRD_EYE_POLL_INTERVAL_TICKS == 0
        and mechanisms
    ):
        try:
            ipw = mechanisms.get("IdentityProposalWriter")
            if ipw is None:
                # Lazy-instantiate if not in the run order yet.
                from brain.mechanisms.identity_proposal_writer import (
                    IdentityProposalWriter,
                )
                ipw = IdentityProposalWriter()
            poll = getattr(ipw, "poll_wires", None)
            if callable(poll):
                poll(mechanisms)
        except Exception:
            pass


def reset_tick_counter() -> None:
    """Test hook: reset the per-process tick counter so DRAIN_INTERVAL_TICKS
    and THIRD_EYE_POLL_INTERVAL_TICKS are honored predictably across
    test runs that share interpreter state."""
    global _tick_counter, _drain_failures_in_a_row
    _tick_counter = 0
    _drain_failures_in_a_row = 0


def checkpoint_mechanisms() -> dict:
    """
    Continuity Idea 1 — call persist_state() on every loaded brain
    mechanism so its self.state survives a process restart.
    Returns a small report dict for the heartbeat to log.
    """
    proxy = get_integration()
    runner = getattr(proxy, "brain_runner", None)
    if runner is None:
        return {"saved": 0, "total": 0, "errors": [], "note": "no brain_runner"}
    return runner.checkpoint_all()


def restore_mechanism_checkpoints() -> dict:
    """
    Companion to checkpoint_mechanisms — load_state() across the runner
    on session open so the heartbeat resumes where it left off.
    """
    proxy = get_integration()
    runner = getattr(proxy, "brain_runner", None)
    if runner is None:
        return {"loaded": 0, "total": 0, "errors": [], "note": "no brain_runner"}
    return runner.checkpoint_load_all()
