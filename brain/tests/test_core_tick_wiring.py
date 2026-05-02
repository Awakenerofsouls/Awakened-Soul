"""
Tests for the Phase-4 core_tick hooks in runtime/brain_proxy.py.

The tick hook is the production drain + poll path. We can't boot the
full AgentBrainIntegration in a test (it loads ~350 mechanisms), so
we stub get_integration to return a minimal proxy with a wired
mechanisms dict + a fake .core.tick() that just counts calls.

Covers:
  - core_tick advances tick counter
  - Drain fires every DRAIN_INTERVAL_TICKS ticks
  - Third-Eye poll fires every THIRD_EYE_POLL_INTERVAL_TICKS ticks
  - Both hooks see live mechanism instances (state mutation observable)
  - Drain failures back off after threshold
  - Poll exception doesn't break tick
  - reset_tick_counter resets the counter
"""
import json
from pathlib import Path

import pytest


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / "identity").mkdir(parents=True)
    state_dir = home / "brain_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AGENT_HOME", str(home))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    import brain.base_mechanism as _bm
    monkeypatch.setattr(_bm, "_STATE_DIR", state_dir)
    # Re-bind the PROPOSALS_PATH the IPW module captured at import time.
    import brain.mechanisms.identity_proposal_writer as ipw_mod
    monkeypatch.setattr(
        ipw_mod, "PROPOSALS_PATH", home / "identity" / "PROPOSALS.md",
    )
    return home


# ── Stub proxy / runner ──────────────────────────────────────────────────


class _StubCore:
    def __init__(self):
        self.ticks = 0
        self.tsb = object()
    def tick(self):
        self.ticks += 1


class _StubRunner:
    def __init__(self, mechanisms):
        self.mechanisms = dict(mechanisms or {})


class _StubProxy:
    def __init__(self, mechanisms=None):
        self.core = _StubCore()
        self.brain_runner = _StubRunner(mechanisms)


def _patch_get_integration(monkeypatch, proxy):
    """Make get_integration() return our stub. Patches both the
    function in brain_proxy AND the underlying brain.brain_integration
    so any indirect calls land on the stub."""
    import runtime.brain_proxy as bp
    monkeypatch.setattr(bp, "get_integration", lambda: proxy)


def _reset_tick(monkeypatch=None):
    import runtime.brain_proxy as bp
    bp.reset_tick_counter()


# ── Basic dispatch ───────────────────────────────────────────────────────


def test_core_tick_advances_tick_counter(isolated, monkeypatch):
    _patch_get_integration(monkeypatch, _StubProxy())
    _reset_tick()
    import runtime.brain_proxy as bp
    bp.core_tick()
    assert bp._tick_counter == 1
    bp.core_tick()
    bp.core_tick()
    assert bp._tick_counter == 3


def test_core_tick_calls_underlying_core(isolated, monkeypatch):
    proxy = _StubProxy()
    _patch_get_integration(monkeypatch, proxy)
    _reset_tick()
    import runtime.brain_proxy as bp
    bp.core_tick()
    bp.core_tick()
    assert proxy.core.ticks == 2


# ── Drain hook ───────────────────────────────────────────────────────────


def test_drain_hook_fires_every_tick_at_default_interval(isolated, monkeypatch):
    """DRAIN_INTERVAL_TICKS = 1 by default → drains every tick."""
    from brain.mechanisms.memory_integrity_layer import MemoryIntegrityLayer
    from skills.heartbeat_activities._brain_post import post_memory_encode

    mil = MemoryIntegrityLayer()
    proxy = _StubProxy(mechanisms={"MemoryIntegrityLayer": mil})
    _patch_get_integration(monkeypatch, proxy)
    _reset_tick()

    # Pre-tick: queue an event.
    post_memory_encode(
        content="from drain hook test", intent="observation",
        source_kind="external", content_confidence=0.7, source_confidence=0.7,
    )
    queue_path = isolated / "brain_events.jsonl"
    assert queue_path.exists()

    # core_tick should drain it.
    import runtime.brain_proxy as bp
    bp.core_tick()
    # Mechanism saw the encode.
    assert mil.total_encoded == 1
    # Queue is empty / removed.
    assert (not queue_path.exists()) or queue_path.read_text().strip() == ""


def test_drain_hook_caps_at_max_events_per_tick(isolated, monkeypatch):
    """Queue with > MAX events → only MAX get drained per tick; rest stay."""
    from brain.mechanisms.memory_integrity_layer import MemoryIntegrityLayer
    from skills.heartbeat_activities._brain_post import post_memory_encode
    import runtime.brain_proxy as bp

    mil = MemoryIntegrityLayer()
    proxy = _StubProxy(mechanisms={"MemoryIntegrityLayer": mil})
    _patch_get_integration(monkeypatch, proxy)
    _reset_tick()

    # Force the per-tick cap to be tiny so the test runs fast.
    monkeypatch.setattr(bp, "DRAIN_MAX_EVENTS_PER_TICK", 3)

    # Post 5 events.
    for i in range(5):
        post_memory_encode(
            content=f"item-{i}", intent="observation",
            source_kind="external",
            content_confidence=0.7, source_confidence=0.7,
        )

    bp.core_tick()
    # Only 3 should have been processed.
    assert mil.total_encoded == 3
    queue_path = isolated / "brain_events.jsonl"
    remaining = queue_path.read_text().strip().splitlines()
    assert len(remaining) == 2

    # Second tick drains the rest.
    bp.core_tick()
    assert mil.total_encoded == 5


def test_drain_failures_back_off_after_threshold(isolated, monkeypatch):
    """If drain throws _DRAIN_FAILURES_BACKOFF_THRESHOLD times in a row,
    further drain calls are skipped (the tick stays alive)."""
    proxy = _StubProxy(mechanisms={})
    _patch_get_integration(monkeypatch, proxy)
    _reset_tick()

    import runtime.brain_proxy as bp
    # Force drain_once to always raise.
    raise_count = {"n": 0}
    def boom(*args, **kwargs):
        raise_count["n"] += 1
        raise RuntimeError("synthetic drain failure")
    monkeypatch.setattr("brain.brain_event_drainer.drain_once", boom)

    # First N+1 ticks should all *attempt* drain (each catching the
    # exception). N+2nd tick should NOT call drain (backoff).
    for _ in range(bp._DRAIN_FAILURES_BACKOFF_THRESHOLD):
        bp.core_tick()
    expected = bp._DRAIN_FAILURES_BACKOFF_THRESHOLD
    assert raise_count["n"] == expected
    # One more tick — this should be skipped due to backoff.
    bp.core_tick()
    assert raise_count["n"] == expected  # no new attempt


# ── Third-Eye poll hook ──────────────────────────────────────────────────


class _FiringWire:
    """Mock wire that always fires IPW."""
    def __init__(self, kind="systematic_memory_drift", source="MIL"):
        self.kind = kind
        self.source = source
        self.acks = 0
    def should_propose_identity_update(self):
        return True
    def proposed_identity_signal(self):
        return {
            "source": self.source,
            "kind": self.kind,
            "rolling_integrity_score": 0.30,
            "consecutive_bad_ops": 10,
            "interpretation": f"synthetic from {self.source}",
        }
    def acknowledge_proposal(self):
        self.acks += 1


def test_third_eye_poll_fires_at_interval(isolated, monkeypatch):
    """Third-Eye poll fires every THIRD_EYE_POLL_INTERVAL_TICKS ticks."""
    import runtime.brain_proxy as bp
    monkeypatch.setattr(bp, "THIRD_EYE_POLL_INTERVAL_TICKS", 3)

    wire = _FiringWire()
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter
    ipw = IdentityProposalWriter()

    proxy = _StubProxy(mechanisms={
        "MemoryIntegrityLayer": wire,
        "IdentityProposalWriter": ipw,
    })
    _patch_get_integration(monkeypatch, proxy)
    _reset_tick()

    # Tick 1: no poll (1 % 3 != 0).
    bp.core_tick()
    assert wire.acks == 0

    # Tick 2: still no poll.
    bp.core_tick()
    assert wire.acks == 0

    # Tick 3: poll fires.
    bp.core_tick()
    assert wire.acks == 1
    text = (isolated / "identity" / "PROPOSALS.md").read_text()
    assert "MIL" in text


def test_third_eye_poll_lazy_instantiates_ipw(isolated, monkeypatch):
    """If IdentityProposalWriter isn't in the runner's mechanisms dict,
    core_tick should lazy-instantiate one rather than skipping the poll."""
    import runtime.brain_proxy as bp
    monkeypatch.setattr(bp, "THIRD_EYE_POLL_INTERVAL_TICKS", 1)

    wire = _FiringWire()
    proxy = _StubProxy(mechanisms={"MIL": wire})  # no IdentityProposalWriter
    _patch_get_integration(monkeypatch, proxy)
    _reset_tick()

    bp.core_tick()
    # Wire got acknowledged → poll happened despite IPW not in the dict.
    assert wire.acks == 1


def test_third_eye_poll_exception_doesnt_break_tick(isolated, monkeypatch):
    """If the polling layer raises, the tick continues unaffected."""
    import runtime.brain_proxy as bp
    monkeypatch.setattr(bp, "THIRD_EYE_POLL_INTERVAL_TICKS", 1)

    class BrokenIPW:
        def poll_wires(self, mechanisms):
            raise RuntimeError("synthetic poll failure")

    proxy = _StubProxy(mechanisms={"IdentityProposalWriter": BrokenIPW()})
    _patch_get_integration(monkeypatch, proxy)
    _reset_tick()

    # Should NOT raise.
    bp.core_tick()
    assert proxy.core.ticks == 1


def test_third_eye_skipped_when_no_mechanisms(isolated, monkeypatch):
    """No mechanisms in the runner → no poll attempted."""
    import runtime.brain_proxy as bp
    monkeypatch.setattr(bp, "THIRD_EYE_POLL_INTERVAL_TICKS", 1)

    # Runner exists but has no mechanisms.
    proxy = _StubProxy(mechanisms={})
    _patch_get_integration(monkeypatch, proxy)
    _reset_tick()

    # Should not raise; just no-op the poll.
    bp.core_tick()
    assert proxy.core.ticks == 1


# ── Combined: drain AND poll ──────────────────────────────────────────────


def test_combined_drain_and_poll_in_same_tick(isolated, monkeypatch):
    """Tick where both interval conditions fire — drain processes the
    queue AND poll surfaces a proposal."""
    import runtime.brain_proxy as bp
    monkeypatch.setattr(bp, "DRAIN_INTERVAL_TICKS", 1)
    monkeypatch.setattr(bp, "THIRD_EYE_POLL_INTERVAL_TICKS", 1)

    from brain.mechanisms.memory_integrity_layer import MemoryIntegrityLayer
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter
    from skills.heartbeat_activities._brain_post import post_memory_encode

    # A drain-target mechanism + a wire that fires.
    mil = MemoryIntegrityLayer()
    wire = _FiringWire(kind="voice_drift", source="VIL")
    ipw = IdentityProposalWriter()

    proxy = _StubProxy(mechanisms={
        "MemoryIntegrityLayer": mil,
        "VoiceIntegrityLayer": wire,
        "IdentityProposalWriter": ipw,
    })
    _patch_get_integration(monkeypatch, proxy)
    _reset_tick()

    # Pre-queue an event.
    post_memory_encode(
        content="drain target",
        intent="observation",
        source_kind="external",
        content_confidence=0.7,
        source_confidence=0.7,
    )

    bp.core_tick()
    # Drain processed the event.
    assert mil.total_encoded == 1
    # Poll fired and acknowledged the wire.
    assert wire.acks == 1


# ── reset hook ───────────────────────────────────────────────────────────


def test_reset_tick_counter(isolated, monkeypatch):
    proxy = _StubProxy()
    _patch_get_integration(monkeypatch, proxy)
    _reset_tick()  # zero baseline for this test (module state leaks across tests)
    import runtime.brain_proxy as bp
    bp.core_tick()
    bp.core_tick()
    assert bp._tick_counter == 2
    bp.reset_tick_counter()
    assert bp._tick_counter == 0
