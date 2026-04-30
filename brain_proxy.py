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

def core_tick() -> None:
    """
    Advance one tick of the AgentBrainCore loop.
    Runs registered Phase 2/3/4 component ticks.

    Call this on each heartbeat cycle (every 30s) to keep
    mechanisms active even when there's no user input.
    """
    global _core_tsbp
    proxy = get_integration()
    proxy.core.tick()
    _core_tsbp = proxy.core.tsb  # cache for heartbeat._psych_tick()


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
