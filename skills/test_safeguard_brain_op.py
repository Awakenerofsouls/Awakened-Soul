"""
Phase 6 — Tests for the wire-aware safeguard gate
(skills/safeguard.py :: can_perform_brain_op).

Covers:
  - WIRE_GATES dispatch table is non-empty and covers expected ops
  - Healthy wire allows the op
  - Degraded wire (systematically low integrity) blocks the op
  - Live mechanism in `mechanisms` dict takes precedence over ephemeral
  - Per-wire gate logic exposed correctly:
      * memory.forget without reason → block
      * memory.encode dream + high source_confidence → block
      * self_revision.commit without ratification_token → block
      * persona.switch invalid target → block
      * outward_reach with valid provider → allow
      * compression with intent under floor → block
  - Unmapped op_kind → graceful pass-through
  - Mechanism-not-loadable → graceful pass-through (logs the issue)
  - Adapter-raises → graceful pass-through (doesn't break safeguard)
  - reset_safeguard clears the ephemeral cache
  - Audit log entries created for both allowed and blocked attempts
"""
import json
import sys
from pathlib import Path

import pytest

# The skill folder isn't a Python package by name (no __init__.py at
# skills/), so we add it to sys.path. Then `from safeguard import ...`.
_SKILLS = Path(__file__).resolve().parent
if str(_SKILLS) not in sys.path:
    sys.path.insert(0, str(_SKILLS))


@pytest.fixture
def env(tmp_path, monkeypatch):
    home = tmp_path / "home"
    ws = tmp_path / "ws"
    home.mkdir()
    ws.mkdir()
    state_dir = home / "brain_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AGENT_HOME", str(home))
    monkeypatch.setenv("AGENT_WORKSPACE", str(ws))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    import brain.base_mechanism as _bm
    monkeypatch.setattr(_bm, "_STATE_DIR", state_dir)
    # Force a fresh import of skills.safeguard so the per-process state
    # (SAFEGUARD_LOG path, _ephemeral_cache) starts empty for this test.
    if "safeguard" in sys.modules:
        del sys.modules["safeguard"]
    if "skills.safeguard" in sys.modules:
        del sys.modules["skills.safeguard"]
    yield {"home": home, "ws": ws}


# ── WIRE_GATES dispatch table ────────────────────────────────────────────


def test_wire_gates_table_populated(env):
    from safeguard import WIRE_GATES
    assert len(WIRE_GATES) >= 30
    # Spot-check key entries.
    for op in (
        "memory.encode", "memory.forget", "outward_reach",
        "self_revision.commit", "persona.switch", "report.publish",
        "planning.commit", "corpus.search", "skill_routing.route",
        "analysis.analyze", "compression", "inference",
    ):
        assert op in WIRE_GATES, f"missing op {op!r}"


# ── Allow / block paths ──────────────────────────────────────────────────


def test_healthy_wire_allows_op(env):
    from safeguard import can_perform_brain_op
    allowed, reason = can_perform_brain_op(
        "memory.encode",
        ctx={
            "content": "fresh observation",
            "intent": "observation",
            "source": "user",
            "content_confidence": 0.7,
            "source_confidence": 0.85,
        },
    )
    assert allowed is True
    assert reason == ""


def test_degraded_wire_blocks_op_via_live_instance(env):
    """When caller passes a live mechanism with degraded state, the
    gate blocks — and the live instance's state is the one consulted."""
    from safeguard import can_perform_brain_op
    from brain.mechanisms.memory_integrity_layer import MemoryIntegrityLayer

    mil = MemoryIntegrityLayer()
    for _ in range(10):
        mil.record_operation("teleport", target="x")
    assert mil.is_systematically_low_integrity() is True

    allowed, reason = can_perform_brain_op(
        "memory.encode",
        ctx={
            "content": "x", "intent": "observation",
            "source": "user", "content_confidence": 0.7,
            "source_confidence": 0.7,
        },
        mechanisms={"MemoryIntegrityLayer": mil},
    )
    assert allowed is False
    assert "MemoryIntegrityLayer.should_block" in reason
    assert "low memory integrity" in reason


def test_live_mechanism_takes_precedence_over_ephemeral(env):
    """If both a live instance is supplied AND an ephemeral exists,
    the live wins (state changes on it must be the source of truth)."""
    from safeguard import can_perform_brain_op, _ephemeral_cache
    from brain.mechanisms.memory_integrity_layer import MemoryIntegrityLayer

    # First, trigger ephemeral creation (healthy).
    can_perform_brain_op("memory.encode", ctx={
        "content": "x", "intent": "observation", "source": "user",
        "content_confidence": 0.7, "source_confidence": 0.7,
    })
    # Ephemeral now cached and healthy.
    eph = _ephemeral_cache.get("MemoryIntegrityLayer")
    assert eph is not None
    assert eph.is_systematically_low_integrity() is False

    # Now pass a DEGRADED live instance — that should block, even though
    # the ephemeral is healthy.
    live = MemoryIntegrityLayer()
    for _ in range(10):
        live.record_operation("teleport", target="x")
    allowed, _ = can_perform_brain_op(
        "memory.encode",
        ctx={"content": "x", "intent": "observation", "source": "user",
             "content_confidence": 0.7, "source_confidence": 0.7},
        mechanisms={"MemoryIntegrityLayer": live},
    )
    assert allowed is False  # live wins


# ── Per-wire gate logic ──────────────────────────────────────────────────


def test_memory_forget_without_reason_blocks(env):
    from safeguard import can_perform_brain_op
    allowed, reason = can_perform_brain_op("memory.forget", ctx={})
    assert allowed is False
    assert "reason" in reason


def test_memory_encode_dream_high_confidence_blocks(env):
    """Encoding during dream-contamination requires source_confidence
    ≤ 0.4 — higher fails closed."""
    from safeguard import can_perform_brain_op
    allowed, reason = can_perform_brain_op(
        "memory.encode",
        ctx={
            "content": "x", "intent": "observation",
            "source": "dream",
            "content_confidence": 0.9,
            "source_confidence": 0.9,
        },
    )
    assert allowed is False
    assert "dream" in reason


def test_self_revision_commit_no_ratification_blocks(env):
    from safeguard import can_perform_brain_op
    allowed, reason = can_perform_brain_op(
        "self_revision.commit", ctx={"proposal_id": "x"},
    )
    assert allowed is False
    assert "ratification_token" in reason


def test_self_revision_propose_below_confidence_floor_blocks(env):
    from safeguard import can_perform_brain_op
    allowed, reason = can_perform_brain_op(
        "self_revision.propose",
        ctx={"target": "personality", "confidence": 0.4, "text": "x"},
    )
    assert allowed is False
    assert "below floor" in reason


def test_persona_switch_invalid_target_blocks(env):
    from safeguard import can_perform_brain_op
    allowed, reason = can_perform_brain_op(
        "persona.switch",
        ctx={"target": "trade", "source": "auto"},
    )
    assert allowed is False
    assert "invalid target" in reason


def test_persona_switch_valid_allows(env):
    from safeguard import can_perform_brain_op
    allowed, _ = can_perform_brain_op(
        "persona.switch",
        ctx={"target": "brain", "source": "manual"},
    )
    assert allowed is True


def test_outward_reach_allowed_for_clean_provider(env):
    from safeguard import can_perform_brain_op
    allowed, _ = can_perform_brain_op(
        "outward_reach", ctx={"provider": "tavily", "intent": "research"},
    )
    assert allowed is True


def test_compression_below_floor_blocks(env):
    """extract intent with retention < 5% should be blocked."""
    from safeguard import can_perform_brain_op
    allowed, reason = can_perform_brain_op(
        "compression",
        ctx={"intent": "extract", "source_len": 1000, "target_len": 10},
    )
    assert allowed is False
    assert "extract" in reason


def test_planning_decompose_allowed_when_healthy(env):
    from safeguard import can_perform_brain_op
    allowed, _ = can_perform_brain_op("planning.decompose", ctx={})
    assert allowed is True


def test_corpus_search_allowed_when_healthy(env):
    from safeguard import can_perform_brain_op
    allowed, _ = can_perform_brain_op(
        "corpus.search", ctx={"query": "x"},
    )
    assert allowed is True


def test_inference_above_floor_allowed(env):
    from safeguard import can_perform_brain_op
    allowed, _ = can_perform_brain_op(
        "inference",
        ctx={
            "intent": "describe", "sample_size": 50, "claimed_confidence": 0.7,
        },
    )
    assert allowed is True


# ── Graceful degradation ─────────────────────────────────────────────────


def test_unmapped_op_kind_passes_through(env):
    from safeguard import can_perform_brain_op
    allowed, reason = can_perform_brain_op("totally.made_up_op", ctx={})
    assert allowed is True
    assert reason == ""


def test_mechanism_not_loadable_passes_through(env):
    """Inject a fake op_kind whose mechanism class doesn't exist —
    safeguard should pass through rather than crash."""
    from safeguard import WIRE_GATES, can_perform_brain_op
    # Add a poison entry pointing at a non-existent class.
    original = dict(WIRE_GATES)
    try:
        WIRE_GATES["test.nonexistent"] = (
            "DefinitelyNotARealMechanism", lambda i, c: (False, "should not reach"),
        )
        allowed, reason = can_perform_brain_op("test.nonexistent", ctx={})
        assert allowed is True
        assert reason == ""
    finally:
        WIRE_GATES.clear()
        WIRE_GATES.update(original)


def test_adapter_raising_passes_through(env):
    """If the adapter raises (e.g. wire's should_block has a bug),
    safeguard logs and passes through — never blocks the agent on
    safeguard infrastructure failure."""
    from safeguard import WIRE_GATES, can_perform_brain_op

    def boom(instance, ctx):
        raise RuntimeError("adapter exploded")

    original = dict(WIRE_GATES)
    try:
        # Use MemoryIntegrityLayer (real, importable) but a broken adapter.
        WIRE_GATES["test.broken_adapter"] = ("MemoryIntegrityLayer", boom)
        allowed, _ = can_perform_brain_op("test.broken_adapter", ctx={})
        assert allowed is True
    finally:
        WIRE_GATES.clear()
        WIRE_GATES.update(original)


# ── Operator API ─────────────────────────────────────────────────────────


def test_reset_safeguard_clears_ephemeral_cache(env):
    """After reset_safeguard, the ephemeral mechanism cache is empty."""
    from safeguard import (
        can_perform_brain_op, _ephemeral_cache, reset_safeguard,
    )
    # Trigger ephemeral creation.
    can_perform_brain_op("memory.encode", ctx={
        "content": "x", "intent": "observation", "source": "user",
        "content_confidence": 0.7, "source_confidence": 0.7,
    })
    assert len(_ephemeral_cache) >= 1
    reset_safeguard()
    assert len(_ephemeral_cache) == 0


# ── Audit log ────────────────────────────────────────────────────────────


def test_blocked_op_logged_to_safeguard_log(env):
    """Both allowed and blocked attempts are logged so the operator
    can audit. Block reason is in the log line."""
    from safeguard import can_perform_brain_op, SAFEGUARD_LOG
    can_perform_brain_op("memory.forget", ctx={})  # should block
    log_text = SAFEGUARD_LOG.read_text(encoding="utf-8") if SAFEGUARD_LOG.exists() else ""
    assert "BLOCKED" in log_text
    assert "memory.forget" in log_text


def test_allowed_op_logged_to_safeguard_log(env):
    from safeguard import can_perform_brain_op, SAFEGUARD_LOG
    can_perform_brain_op(
        "memory.encode",
        ctx={
            "content": "x", "intent": "observation", "source": "user",
            "content_confidence": 0.7, "source_confidence": 0.7,
        },
    )
    log_text = SAFEGUARD_LOG.read_text(encoding="utf-8") if SAFEGUARD_LOG.exists() else ""
    assert "ALLOWED" in log_text
    assert "memory.encode" in log_text


# ── Backward compat: old can_perform path unchanged ─────────────────────


def test_can_perform_destructive_path_unchanged(env):
    """The Phase-6 changes are additive — the original can_perform path
    (subprocess / file_write / etc.) still behaves the same."""
    from safeguard import can_perform
    # rm -rf is an absolute block.
    assert can_perform("subprocess", ["rm", "-rf", "/"], "x") is False
    # File write to journal path is allowed.
    assert can_perform("file_write", "DREAMS.md", "x") is True
