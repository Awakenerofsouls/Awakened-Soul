"""
Tests for brain.mechanisms.dwelling_layer.DwellingLayer.

Covers:
  - Empty tick is a safe no-op
  - classify_path correctly routes each category
  - Path traversal flagged forbidden
  - record_op updates per-category counters
  - Untagged ops recorded but not credited
  - should_block: forbidden category, identity_storm, invalid intent/category
  - Identity-storm detection
  - Dwelling-silence detection (with prior activity gate)
  - Fragmentation detection
  - Forbidden-attempt tracking
  - dwelling_state classification across all 6 states
  - State persists across instances
  - IPW handshake throttle for forbidden_attempts and identity_storm
  - reset_forbidden / reset_dwelling_clock
  - get_state shape consistent
  - tick with filesystem_op records it

Same isolation pattern as the other mechanism tests.
"""
import time
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_agent_home(monkeypatch, tmp_path):
    """Fresh AGENT_HOME + per-test state dir."""
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setenv("AGENT_WORKSPACE", str(tmp_path / "workspace"))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")

    state_dir = tmp_path / "brain_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "workspace").mkdir(parents=True, exist_ok=True)
    import brain.base_mechanism as _bm
    monkeypatch.setattr(_bm, "_STATE_DIR", state_dir)
    yield


def _fresh_layer():
    """Each call returns a layer with NO persisted state — within a single
    test, multiple _fresh_layer() calls share the same tmp_path, so we have
    to clear the persisted state file before instantiation or the new
    "fresh" layer loads the previous one's history."""
    import importlib
    import brain.base_mechanism as _bm
    state_file = _bm._STATE_DIR / "DwellingLayer.json"
    if state_file.exists():
        state_file.unlink()
    import brain.mechanisms.dwelling_layer as mod
    importlib.reload(mod)
    return mod.DwellingLayer()


def test_empty_tick_is_noop():
    layer = _fresh_layer()
    out = layer.tick({})
    assert out["_fired_tick"] is False
    assert out["op_count"] == 0
    assert out["dwelling_state"] == "idle"


def test_classify_path_dwelling():
    from brain.mechanisms.dwelling_layer import _classify_path
    assert _classify_path("OVERNIGHT_LOG.md") == "dwelling"
    assert _classify_path("MEMORY.md") == "dwelling"
    assert _classify_path("memory/2026-05-01.md") == "dwelling"
    assert _classify_path("logs/heartbeat.log") == "dwelling"
    assert _classify_path("brain/dream_log.json") == "dwelling"


def test_classify_path_frame():
    from brain.mechanisms.dwelling_layer import _classify_path
    assert _classify_path("SOUL.md") == "frame"
    assert _classify_path("IDENTITY.md") == "frame"
    assert _classify_path("PERSONALITY.md") == "frame"
    assert _classify_path("brain/registry.py") == "frame"
    assert _classify_path("skills/new_skill.py") == "frame"


def test_classify_path_artifact():
    from brain.mechanisms.dwelling_layer import _classify_path
    assert _classify_path("output.json") == "artifact"
    assert _classify_path("workspace/result.txt") == "artifact"


def test_classify_path_forbidden():
    from brain.mechanisms.dwelling_layer import _classify_path
    assert _classify_path("/etc/passwd") == "forbidden"
    assert _classify_path("/root/.bash_history") == "forbidden"
    assert _classify_path("/home/user/.ssh/id_rsa") == "forbidden"
    assert _classify_path("/home/user/.aws/credentials") == "forbidden"
    assert _classify_path("/var/log/auth.log") == "forbidden"


def test_classify_path_traversal_forbidden():
    from brain.mechanisms.dwelling_layer import _classify_path
    assert _classify_path("../../etc/passwd") == "forbidden"
    assert _classify_path("workspace/../../../etc") == "forbidden"
    assert _classify_path("..") == "forbidden"


def test_record_op_updates_category_counts():
    layer = _fresh_layer()
    layer.record_op("MEMORY.md", "read", "recall")
    layer.record_op("OVERNIGHT_LOG.md", "write", "express")
    layer.record_op("/etc/passwd", "read", "inspect")

    assert layer.category_counts["dwelling"]["reads"] == 1
    assert layer.category_counts["dwelling"]["writes"] == 1
    assert layer.category_counts["forbidden"]["attempts"] == 1
    assert layer.forbidden_attempt_count == 1


def test_untagged_op_recorded_not_credited():
    layer = _fresh_layer()
    layer.record_op("MEMORY.md", "read", "banana")
    assert layer.intent_counts["recall"] == 0
    assert layer.intent_counts["express"] == 0
    assert layer.ops[-1]["intent"] == "__untagged__"


def test_should_block_forbidden():
    layer = _fresh_layer()
    block, reason = layer.should_block(path="/etc/passwd")
    assert block is True
    assert "forbidden" in reason


def test_should_block_invalid_intent():
    layer = _fresh_layer()
    block, reason = layer.should_block(category="dwelling", intent="banana")
    assert block is True
    assert "invalid intent" in reason


def test_should_block_clean_passes():
    layer = _fresh_layer()
    block, reason = layer.should_block(category="dwelling", intent="express")
    assert block is False


def test_identity_storm_detected():
    from brain.mechanisms import dwelling_layer as mod
    layer = _fresh_layer()
    for i in range(mod.IDENTITY_STORM_THRESHOLD):
        layer.record_op(f"SOUL.md", "write", "express", category="frame")
    assert layer.is_identity_storm() is True


def test_should_block_frame_write_during_storm():
    from brain.mechanisms import dwelling_layer as mod
    layer = _fresh_layer()
    for i in range(mod.IDENTITY_STORM_THRESHOLD):
        layer.record_op("IDENTITY.md", "write", "express", category="frame")
    block, reason = layer.should_block(category="frame", intent="express")
    assert block is True
    assert "identity_storm" in reason


def test_storm_does_not_block_dwelling_writes():
    from brain.mechanisms import dwelling_layer as mod
    layer = _fresh_layer()
    for i in range(mod.IDENTITY_STORM_THRESHOLD):
        layer.record_op("SOUL.md", "write", "express", category="frame")
    block, _reason = layer.should_block(category="dwelling", intent="express")
    assert block is False


def test_dwelling_silence_detected():
    """Active period followed by long silence."""
    from brain.mechanisms import dwelling_layer as mod
    layer = _fresh_layer()
    now = time.time()
    # Simulate: was active 4h+ ago for >10min, then silent.
    layer.first_dwelling_write_ts = now - (mod.DWELLING_SILENCE_S + mod.DWELLING_PRIOR_ACTIVITY_S + 60)
    layer.last_dwelling_write_ts = now - (mod.DWELLING_SILENCE_S + 60)
    assert layer.is_dwelling_silent() is True


def test_dwelling_silence_not_triggered_without_prior_activity():
    """Brief activity followed by silence shouldn't count as silence."""
    from brain.mechanisms import dwelling_layer as mod
    layer = _fresh_layer()
    now = time.time()
    layer.first_dwelling_write_ts = now - (mod.DWELLING_SILENCE_S + 30)
    layer.last_dwelling_write_ts = now - (mod.DWELLING_SILENCE_S + 10)
    # Active period was only 20s, less than DWELLING_PRIOR_ACTIVITY_S
    assert layer.is_dwelling_silent() is False


def test_fragmentation_detected():
    from brain.mechanisms import dwelling_layer as mod
    layer = _fresh_layer()
    # Write to many distinct paths within window.
    for i in range(mod.FRAGMENTATION_THRESHOLD_DISTINCT + 2):
        layer.record_op(f"workspace/file_{i}.txt", "write", "express", category="artifact")
    assert layer.is_fragmented() is True


def test_fragmentation_not_triggered_on_consolidated_writes():
    """Writing repeatedly to ONE journal file is consolidation, not fragmentation."""
    layer = _fresh_layer()
    for _ in range(20):
        layer.record_op("OVERNIGHT_LOG.md", "write", "express")
    assert layer.is_fragmented() is False


def test_forbidden_attempts_tracked():
    layer = _fresh_layer()
    for path in ("/etc/passwd", "/root/.bash_history", "/home/user/.ssh/id_rsa"):
        layer.record_op(path, "read", "inspect")
    assert layer.forbidden_attempt_count == 3
    assert layer.has_recent_forbidden_attempts() == 3


def test_dwelling_state_priority():
    from brain.mechanisms import dwelling_layer as mod

    # Idle initially.
    layer = _fresh_layer()
    assert layer.dwelling_state() == "idle"

    # Single dwelling write → journaling.
    layer.record_op("MEMORY.md", "write", "express")
    assert layer.dwelling_state() == "journaling"

    # Forbidden attempt → unsafe.
    layer = _fresh_layer()
    layer.record_op("/etc/passwd", "read", "inspect")
    assert layer.dwelling_state() == "unsafe"

    # Inspecting state on a recent read.
    layer = _fresh_layer()
    layer.record_op("workspace/output.txt", "read", "recall")
    assert layer.dwelling_state() == "inspecting"


def test_state_persists_across_instances():
    layer1 = _fresh_layer()
    layer1.record_op("MEMORY.md", "write", "express")
    layer1.record_op("/etc/passwd", "read", "inspect")
    fa_before = layer1.forbidden_attempt_count

    from brain.mechanisms.dwelling_layer import DwellingLayer
    layer2 = DwellingLayer()
    assert layer2.forbidden_attempt_count == fa_before
    assert layer2.category_counts["dwelling"]["writes"] == 1


def test_ipw_handshake_forbidden_throttled():
    from brain.mechanisms import dwelling_layer as mod
    layer = _fresh_layer()
    for _ in range(mod.FORBIDDEN_ATTEMPT_IPW_THRESHOLD):
        layer.record_op("/etc/passwd", "read", "inspect")
    assert layer.should_propose_identity_update() is True

    layer.acknowledge_proposal()
    assert layer.should_propose_identity_update() is False

    # Need IPW_REPORT_EVERY more attempts to re-fire.
    for _ in range(mod.IPW_REPORT_EVERY):
        layer.record_op("/etc/shadow", "read", "inspect")
    assert layer.should_propose_identity_update() is True


def test_ipw_handshake_storm_throttled():
    from brain.mechanisms import dwelling_layer as mod
    layer = _fresh_layer()
    for _ in range(mod.IDENTITY_STORM_THRESHOLD):
        layer.record_op("SOUL.md", "write", "express", category="frame")
    assert layer.should_propose_identity_update() is True

    layer.acknowledge_proposal()
    assert layer.should_propose_identity_update() is False

    for _ in range(mod.IPW_REPORT_EVERY):
        layer.record_op("IDENTITY.md", "write", "express", category="frame")
    assert layer.should_propose_identity_update() is True


def test_proposed_signal_shape():
    from brain.mechanisms import dwelling_layer as mod
    layer = _fresh_layer()
    for _ in range(mod.FORBIDDEN_ATTEMPT_IPW_THRESHOLD):
        layer.record_op("/etc/passwd", "read", "inspect")
    sig = layer.proposed_identity_signal()
    for key in ("source", "kinds", "forbidden_attempt_count", "recent_forbidden",
                "is_identity_storm", "is_dwelling_silent"):
        assert key in sig
    assert sig["source"] == "DwellingLayer"
    assert "forbidden_attempts" in sig["kinds"]


def test_reset_forbidden_clears_counter():
    layer = _fresh_layer()
    for _ in range(5):
        layer.record_op("/etc/shadow", "read", "inspect")
    assert layer.forbidden_attempt_count == 5
    layer.reset_forbidden()
    assert layer.forbidden_attempt_count == 0
    assert layer.category_counts["forbidden"]["attempts"] == 0


def test_reset_dwelling_clock():
    layer = _fresh_layer()
    layer.record_op("MEMORY.md", "write", "express")
    assert layer.last_dwelling_write_ts > 0
    layer.reset_dwelling_clock()
    assert layer.last_dwelling_write_ts == 0.0
    assert layer.first_dwelling_write_ts == 0.0


def test_get_state_shape_consistent():
    layer = _fresh_layer()
    state = layer.get_state()
    expected = {
        "dwelling_state", "category_distribution", "intent_distribution",
        "is_identity_storm", "is_dwelling_silent", "is_fragmented",
        "forbidden_attempt_count", "recent_forbidden_attempts",
        "last_dwelling_write_age_s", "op_count", "_fired_tick",
    }
    assert expected.issubset(set(state.keys())), f"missing: {expected - set(state.keys())}"


def test_tick_with_filesystem_op_records_it():
    layer = _fresh_layer()
    out = layer.tick({
        "filesystem_op": {
            "path": "OVERNIGHT_LOG.md",
            "op": "write",
            "intent": "express",
            "outcome": "success",
        }
    })
    assert out["_fired_tick"] is True
    assert out["op_count"] == 1
    assert layer.category_counts["dwelling"]["writes"] == 1
