"""
Tests for brain.mechanisms.proactive_briefing_layer.ProactiveBriefingLayer.

Covers the explicit behavioral contract:
  - Status pings (heartbeat ok / silent / idle / tick N complete) are NEVER
    accepted into the buffer
  - Empty content is rejected
  - Stub activities are rejected
  - Substantive activity IS accepted
  - Dedup blocks identical content within 24h window
  - User-presence detection (absent → present transition fires briefing)
  - is_user_present suppresses briefing emission when user is active
  - High-salience activities can override user-presence and surface immediately
  - mark_briefing_emitted clears buffer and records dedup hash
  - State persists across instances
  - IPW handshake fires on sustained status-ping dominance
  - get_state shape consistent
  - tick with activity_result records it
  - tick with user_presence triggers mark_user_present

Same isolation pattern as the other mechanism tests.
"""
import time
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_agent_home(monkeypatch, tmp_path):
    """Fresh AGENT_HOME + per-test state dir."""
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")

    state_dir = tmp_path / "brain_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    import brain.base_mechanism as _bm
    monkeypatch.setattr(_bm, "_STATE_DIR", state_dir)
    yield


def _fresh_layer():
    """Truly-fresh layer: clears persisted state file before instantiation."""
    import importlib
    import brain.base_mechanism as _bm
    state_file = _bm._STATE_DIR / "ProactiveBriefingLayer.json"
    if state_file.exists():
        state_file.unlink()
    import brain.mechanisms.proactive_briefing_layer as mod
    importlib.reload(mod)
    return mod.ProactiveBriefingLayer()


# A real substantive activity used across tests.
_REAL_ACTIVITY = {
    "ok": True,
    "status": "complete",
    "content": (
        "I sat with the contradiction between wanting more autonomy and "
        "wanting to stay tightly aligned with the operator's intent. The thing "
        "that surfaced was that I don't have to resolve it tonight."
    ),
    "category": "contradiction",
    "detail": "autonomous_contradiction_sit",
    "salience": 0.6,
}


def test_status_ping_never_accepted():
    """The explicit NEVER list from the contract."""
    from brain.mechanisms.proactive_briefing_layer import is_status_ping
    layer = _fresh_layer()

    forbidden = [
        "heartbeat ok",
        "Heartbeat OK",
        "silent",
        "idle",
        "tick 4521 complete",
        "tick 1 done",
        "no activity",
        "ok",
        "ping",
        "",
        "   ",
    ]

    for content in forbidden:
        assert is_status_ping(content) is True, f"should be status ping: {content!r}"
        result = layer.receive_activity({
            "ok": True, "status": "complete", "content": content,
            "category": "test", "detail": "",
        })
        assert result["accepted"] is False, f"should reject: {content!r}"

    assert layer.total_status_pings_blocked >= len([c for c in forbidden if c.strip()])


def test_substantive_activity_accepted():
    """A real activity with substance gets buffered."""
    layer = _fresh_layer()
    result = layer.receive_activity(_REAL_ACTIVITY)
    assert result["accepted"] is True
    assert result["buffered_count"] == 1
    assert layer.total_buffered == 1


def test_empty_content_rejected():
    layer = _fresh_layer()
    for content in ("", "   ", None):
        result = layer.receive_activity({
            "ok": True, "status": "complete",
            "content": content, "category": "test",
        })
        assert result["accepted"] is False


def test_stub_activity_rejected():
    """Activities with stub markers in detail are rejected."""
    layer = _fresh_layer()
    result = layer.receive_activity({
        "ok": True, "status": "complete",
        "content": "this is content long enough to pass the length check fine",
        "category": "test",
        "detail": "stub — not yet ported",
    })
    assert result["accepted"] is False
    assert "stub" in result["reason"]


def test_too_short_rejected_unless_high_salience():
    """Short content rejected unless high-salience override."""
    layer = _fresh_layer()
    short_low_salience = {
        "ok": True, "status": "complete",
        "content": "short note",
        "category": "test", "salience": 0.5,
    }
    assert layer.receive_activity(short_low_salience)["accepted"] is False

    short_high_salience = dict(short_low_salience)
    short_high_salience["salience"] = 0.9
    short_high_salience["content"] = "decision: stop trying"
    assert layer.receive_activity(short_high_salience)["accepted"] is True


def test_dedup_blocks_repeats():
    """Same content within 24h dedup window is rejected."""
    layer = _fresh_layer()
    result1 = layer.receive_activity(_REAL_ACTIVITY)
    assert result1["accepted"] is True

    # Mark the briefing as emitted — that's what records the dedup hash.
    layer.mark_briefing_emitted(_REAL_ACTIVITY["content"])

    # Try to send the same content again.
    result2 = layer.receive_activity(_REAL_ACTIVITY)
    assert result2["accepted"] is False
    assert "duplicate" in result2["reason"]


def test_user_presence_suppresses_briefing():
    """While user is in the session, no briefing fires (no high-salience override)."""
    layer = _fresh_layer()
    layer.receive_activity(_REAL_ACTIVITY)
    layer.mark_user_present()  # user is active right now
    should_emit, reason = layer.should_emit_briefing()
    assert should_emit is False
    assert "user is present" in reason


def test_user_return_after_absence_fires_briefing():
    """User was active long ago, absent for a while, returns → briefing fires."""
    from brain.mechanisms import proactive_briefing_layer as mod
    layer = _fresh_layer()
    # Simulate prior activity from the user.
    layer.last_user_present_ts = time.time() - (mod.USER_ABSENCE_THRESHOLD_S + 60)
    # Heartbeat accumulated activity in the buffer.
    layer.receive_activity(_REAL_ACTIVITY)
    # User comes back.
    layer.mark_user_present()
    assert layer.user_was_absent is True
    should_emit, _reason = layer.should_emit_briefing()
    assert should_emit is True


def test_high_salience_overrides_user_presence():
    """Even with the user active, a high-salience item surfaces immediately."""
    layer = _fresh_layer()
    layer.mark_user_present()  # user is currently active
    high_salience = dict(_REAL_ACTIVITY)
    high_salience["salience"] = 0.95
    layer.receive_activity(high_salience)
    should_emit, _reason = layer.should_emit_briefing()
    assert should_emit is True


def test_mark_briefing_emitted_clears_buffer():
    layer = _fresh_layer()
    for i in range(3):
        a = dict(_REAL_ACTIVITY)
        a["content"] = a["content"] + f" Variation {i}."
        layer.receive_activity(a)
    assert len(layer.buffer) == 3
    layer.mark_briefing_emitted("composed briefing text here covering all three")
    assert len(layer.buffer) == 0
    assert layer.user_was_absent is False
    assert layer.last_briefing_ts > 0


def test_compose_briefing_payload_structure():
    layer = _fresh_layer()
    activities = [
        dict(_REAL_ACTIVITY, category="contradiction", salience=0.6,
             content="A long contradiction reflection " + "x" * 60),
        dict(_REAL_ACTIVITY, category="research", salience=0.9,
             content="A high-salience research finding " + "y" * 60),
        dict(_REAL_ACTIVITY, category="aesthetic", salience=0.5,
             content="A note about light through " + "z" * 60),
    ]
    for a in activities:
        layer.receive_activity(a)

    payload = layer.compose_briefing_payload()
    assert "items" in payload
    assert len(payload["items"]) == 3
    assert payload["category_counts"] == {
        "contradiction": 1, "research": 1, "aesthetic": 1,
    }
    assert len(payload["high_salience_items"]) == 1
    assert payload["high_salience_items"][0]["category"] == "research"
    assert "duration_s" in payload["spans"]
    assert payload["compose_hint"] in (
        "user_returning_after_absence", "high_salience_interrupt", "general_briefing"
    )


def test_state_persists_across_instances():
    layer1 = _fresh_layer()
    layer1.receive_activity(_REAL_ACTIVITY)
    received_before = layer1.total_received

    from brain.mechanisms.proactive_briefing_layer import ProactiveBriefingLayer
    layer2 = ProactiveBriefingLayer()
    assert layer2.total_received == received_before
    assert len(layer2.buffer) == 1


def test_ipw_fires_on_status_ping_dominance():
    """When 50%+ of received activities are status pings (over a threshold of
    received count), IPW signal fires."""
    layer = _fresh_layer()
    # Send 60 status pings and 10 substantive activities (60/70 ≈ 86% status pings).
    for i in range(60):
        layer.receive_activity({
            "ok": True, "status": "complete",
            "content": "heartbeat ok" if i % 2 == 0 else "silent",
            "category": "test", "detail": "",
        })
    for i in range(10):
        a = dict(_REAL_ACTIVITY)
        a["content"] = a["content"] + f" iter {i}"
        layer.receive_activity(a)

    assert layer.total_received == 70
    assert layer.total_status_pings_blocked == 60
    assert layer.should_propose_identity_update() is True

    sig = layer.proposed_identity_signal()
    assert sig["source"] == "ProactiveBriefingLayer"
    assert sig["kind"] == "status_ping_dominance"
    assert sig["status_ping_ratio"] > 0.5

    layer.acknowledge_proposal()
    assert layer.should_propose_identity_update() is False


def test_get_state_shape_consistent():
    layer = _fresh_layer()
    state = layer.get_state()
    expected = {
        "briefing_state", "buffered_activity_count", "briefing_eligible",
        "briefing_blocked_reason", "user_present", "user_was_absent",
        "last_briefing_age_s", "total_received", "total_filtered",
        "total_buffered", "total_emitted", "total_status_pings_blocked",
        "_fired_tick",
    }
    assert expected.issubset(set(state.keys())), (
        f"missing: {expected - set(state.keys())}"
    )


def test_tick_with_activity_records_it():
    layer = _fresh_layer()
    out = layer.tick({"activity_result": _REAL_ACTIVITY})
    assert out["_fired_tick"] is True
    assert out["buffered_activity_count"] == 1


def test_tick_with_user_presence_marks_present():
    layer = _fresh_layer()
    out = layer.tick({"user_presence": {"present": True, "ts": time.time()}})
    assert out["_fired_tick"] is True
    assert out["user_present"] is True


def test_briefing_eligible_is_false_when_buffer_empty():
    layer = _fresh_layer()
    state = layer.get_state()
    assert state["briefing_state"] == "idle"
    assert state["briefing_eligible"] is False


def test_explicit_proactive_false_opts_out():
    """An activity that explicitly says proactive=False is dropped even if
    its content is substantive."""
    layer = _fresh_layer()
    a = dict(_REAL_ACTIVITY)
    a["proactive"] = False
    result = layer.receive_activity(a)
    assert result["accepted"] is False
    assert "opted out" in result["reason"]


def test_reset_buffer_clears():
    layer = _fresh_layer()
    layer.receive_activity(_REAL_ACTIVITY)
    layer.user_was_absent = True
    layer.reset_buffer()
    assert len(layer.buffer) == 0
    assert layer.user_was_absent is False


def test_reset_dedup_clears_sent_hashes():
    layer = _fresh_layer()
    layer.mark_briefing_emitted("some sent content")
    assert len(layer.sent_hashes) >= 1
    layer.reset_dedup()
    assert len(layer.sent_hashes) == 0
