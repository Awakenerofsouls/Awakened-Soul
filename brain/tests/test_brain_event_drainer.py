"""
Round-trip tests for the heartbeat → brain event queue.

Covers:
  - _brain_post: post_event basic; unknown category rejected; queue file
    created; convenience helpers post correctly
  - peek_queue / queue_size
  - BrainEventDrainer.drain: empty queue → ok with 0 drained; single
    event dispatch hits the right mechanism's method; unknown category
    routes to dead-letter; malformed JSON routes to dead-letter; live
    mechanism instances receive calls (state mutation observed)
  - drain truncates the queue
  - drain max_events caps and remainder is preserved
  - End-to-end: post 3 events → drain → mechanism state reflects all 3
"""
import json
from pathlib import Path

import pytest


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    state_dir = home / "brain_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AGENT_HOME", str(home))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    # Same anti-leak pattern: pin _STATE_DIR.
    import brain.base_mechanism as _bm
    monkeypatch.setattr(_bm, "_STATE_DIR", state_dir)
    return home


# ── _brain_post tests ────────────────────────────────────────────────────


def test_post_event_basic(isolated_home):
    from skills.heartbeat_activities._brain_post import (
        post_event, queue_size, peek_queue,
    )
    res = post_event("memory.encode", {
        "content": "first memory",
        "intent": "observation",
        "source": "external",
        "content_confidence": 0.7,
        "source_confidence": 0.85,
    })
    assert res["ok"] is True
    assert res["event_id"].startswith("ev_")
    assert queue_size() == 1
    events = peek_queue()
    assert len(events) == 1
    assert events[0]["category"] == "memory.encode"
    assert events[0]["payload"]["content"] == "first memory"


def test_post_event_unknown_category(isolated_home):
    from skills.heartbeat_activities._brain_post import post_event
    res = post_event("teleport.action", {})
    assert res["ok"] is False
    assert "unknown event category" in res["reason"]


def test_post_outward_reach_call(isolated_home):
    from skills.heartbeat_activities._brain_post import (
        post_outward_reach_call, peek_queue,
    )
    res = post_outward_reach_call(
        provider="tavily", intent="research",
        success=True, latency_ms=123.4, url="https://api.tavily.com/search",
    )
    assert res["ok"] is True
    events = peek_queue()
    assert events[0]["category"] == "outward_reach.call"
    payload = events[0]["payload"]
    assert payload["provider"] == "tavily"
    assert payload["intent"] == "research"
    assert payload["outcome"] == "success"
    assert payload["duration_ms"] == 123  # latency_ms aliased to duration_ms


def test_post_memory_encode(isolated_home):
    from skills.heartbeat_activities._brain_post import (
        post_memory_encode, peek_queue,
    )
    post_memory_encode(
        content="something noticed",
        intent="observation",
        source_kind="external",
        content_confidence=0.8,
        source_confidence=0.7,
    )
    events = peek_queue()
    assert events[0]["category"] == "memory.encode"
    assert events[0]["payload"]["intent"] == "observation"


def test_post_self_analysis(isolated_home):
    from skills.heartbeat_activities._brain_post import (
        post_self_analysis, peek_queue,
    )
    post_self_analysis(
        output="some text",
        kind="answer",
        predicted_quality=0.8,
        what_worked=["clear"],
    )
    events = peek_queue()
    assert events[0]["category"] == "self_analysis.analyze"


def test_queue_size_empty(isolated_home):
    from skills.heartbeat_activities._brain_post import queue_size
    assert queue_size() == 0


def test_peek_queue_limit(isolated_home):
    from skills.heartbeat_activities._brain_post import (
        post_event, peek_queue,
    )
    for i in range(5):
        post_event("memory.encode", {"content": f"item-{i}", "intent": "observation",
                                      "source": "external", "content_confidence": 0.7,
                                      "source_confidence": 0.7})
    events = peek_queue(limit=3)
    assert len(events) == 3


# ── BrainEventDrainer tests ──────────────────────────────────────────────


def test_drain_empty_queue(isolated_home):
    from brain.brain_event_drainer import BrainEventDrainer
    drainer = BrainEventDrainer()
    res = drainer.drain()
    assert res["ok"] is True
    assert res["drained"] == 0


def test_drain_single_event_uses_wired_mechanism(isolated_home):
    """Wired-mode: caller passes a mechanism instance; drain dispatches
    onto THAT instance, not an ephemeral one."""
    from brain.brain_event_drainer import BrainEventDrainer
    from brain.mechanisms.memory_integrity_layer import MemoryIntegrityLayer
    from skills.heartbeat_activities._brain_post import post_memory_encode

    mil = MemoryIntegrityLayer()
    assert mil.total_encoded == 0

    post_memory_encode(
        content="from drainer",
        intent="observation",
        source_kind="external",
        content_confidence=0.7,
        source_confidence=0.85,
    )

    drainer = BrainEventDrainer(
        mechanisms={"MemoryIntegrityLayer": mil},
    )
    res = drainer.drain()
    assert res["ok"] is True
    assert res["drained"] == 1
    assert res["failed"] == 0
    # The wired instance saw the call.
    assert mil.total_encoded == 1
    # Queue is truncated.
    assert drainer.queue_size() == 0


def test_drain_unknown_category_dead_letters(isolated_home):
    from brain.brain_event_drainer import BrainEventDrainer

    # Manually inject a malformed event with an unknown category.
    queue_path = isolated_home / "brain_events.jsonl"
    queue_path.write_text(json.dumps({
        "category": "teleport.action",
        "payload": {"x": 1},
        "ts": 1.0,
    }) + "\n", encoding="utf-8")

    drainer = BrainEventDrainer()
    res = drainer.drain()
    assert res["ok"] is True
    assert res["drained"] == 0
    assert res["failed"] == 1
    # Dead-letter file populated.
    dead = isolated_home / "brain_events.jsonl.dead"
    assert dead.exists()


def test_drain_malformed_json_dead_letters(isolated_home):
    from brain.brain_event_drainer import BrainEventDrainer

    queue_path = isolated_home / "brain_events.jsonl"
    queue_path.write_text("this is not json\n", encoding="utf-8")

    drainer = BrainEventDrainer()
    res = drainer.drain()
    assert res["failed"] == 1
    dead = isolated_home / "brain_events.jsonl.dead"
    assert dead.exists()


def test_drain_max_events_caps_with_remainder(isolated_home):
    """drain(max_events=N) processes only the first N and leaves the rest."""
    from brain.brain_event_drainer import BrainEventDrainer
    from brain.mechanisms.memory_integrity_layer import MemoryIntegrityLayer
    from skills.heartbeat_activities._brain_post import post_memory_encode

    mil = MemoryIntegrityLayer()

    for i in range(5):
        post_memory_encode(
            content=f"item-{i}",
            intent="observation",
            source_kind="external",
            content_confidence=0.7,
            source_confidence=0.7,
        )

    drainer = BrainEventDrainer(mechanisms={"MemoryIntegrityLayer": mil})
    res = drainer.drain(max_events=3)
    assert res["drained"] == 3
    assert res["remaining"] == 2
    assert drainer.queue_size() == 2

    # Drain the rest.
    res2 = drainer.drain()
    assert res2["drained"] == 2
    assert drainer.queue_size() == 0
    assert mil.total_encoded == 5


def test_drain_with_ephemeral_instance(isolated_home):
    """Without a `mechanisms` dict, drainer lazy-creates an instance and
    the call still lands."""
    from brain.brain_event_drainer import BrainEventDrainer
    from skills.heartbeat_activities._brain_post import post_memory_encode

    post_memory_encode(
        content="ephemeral test",
        intent="observation",
        source_kind="external",
        content_confidence=0.7,
        source_confidence=0.7,
    )

    drainer = BrainEventDrainer()  # no wired mechanisms
    res = drainer.drain()
    assert res["drained"] == 1
    assert res["failed"] == 0
    # The ephemeral cache should have the instance.
    assert "MemoryIntegrityLayer" in drainer._ephemeral


def test_drain_per_category_tally(isolated_home):
    from brain.brain_event_drainer import BrainEventDrainer
    from brain.mechanisms.memory_integrity_layer import MemoryIntegrityLayer
    from brain.mechanisms.outward_reach_layer import OutwardReachLayer
    from skills.heartbeat_activities._brain_post import (
        post_memory_encode, post_outward_reach_call,
    )

    mil = MemoryIntegrityLayer()
    orl = OutwardReachLayer()

    post_memory_encode(content="a", intent="observation", source_kind="external",
                       content_confidence=0.7, source_confidence=0.7)
    post_memory_encode(content="b", intent="observation", source_kind="external",
                       content_confidence=0.7, source_confidence=0.7)
    post_outward_reach_call(
        provider="tavily", intent="research", success=True, latency_ms=100,
    )

    drainer = BrainEventDrainer(mechanisms={
        "MemoryIntegrityLayer": mil,
        "OutwardReachLayer": orl,
    })
    res = drainer.drain()
    assert res["drained"] == 3
    per_cat = res["per_category"]
    assert per_cat.get("memory.encode") == 2
    assert per_cat.get("outward_reach.call") == 1


def test_drain_truncates_queue_on_success(isolated_home):
    from brain.brain_event_drainer import BrainEventDrainer
    from brain.mechanisms.memory_integrity_layer import MemoryIntegrityLayer
    from skills.heartbeat_activities._brain_post import post_memory_encode

    mil = MemoryIntegrityLayer()
    post_memory_encode(content="x", intent="observation", source_kind="external",
                       content_confidence=0.7, source_confidence=0.7)
    assert (isolated_home / "brain_events.jsonl").exists()

    drainer = BrainEventDrainer(mechanisms={"MemoryIntegrityLayer": mil})
    drainer.drain()
    # Queue file removed (or empty) after fully draining.
    qp = isolated_home / "brain_events.jsonl"
    assert (not qp.exists()) or qp.read_text(encoding="utf-8").strip() == ""


def test_drain_failed_events_dont_block_successful_ones(isolated_home):
    from brain.brain_event_drainer import BrainEventDrainer
    from brain.mechanisms.memory_integrity_layer import MemoryIntegrityLayer
    from skills.heartbeat_activities._brain_post import post_memory_encode

    mil = MemoryIntegrityLayer()
    queue_path = isolated_home / "brain_events.jsonl"

    # Manually craft: one bad, one good.
    bad = json.dumps({"category": "teleport.action", "payload": {}, "ts": 1.0})
    good = json.dumps({
        "category": "memory.encode",
        "payload": {
            "content": "good", "intent": "observation",
            "source": "external", "content_confidence": 0.7,
            "source_confidence": 0.7,
        },
        "ts": 2.0,
    })
    queue_path.write_text(bad + "\n" + good + "\n", encoding="utf-8")

    drainer = BrainEventDrainer(mechanisms={"MemoryIntegrityLayer": mil})
    res = drainer.drain()
    assert res["drained"] == 1
    assert res["failed"] == 1
    assert mil.total_encoded == 1


# ── End-to-end ───────────────────────────────────────────────────────────


def test_e2e_three_categories(isolated_home):
    """Post events from 3 different categories; drain; observe state on
    each respective mechanism."""
    from brain.brain_event_drainer import BrainEventDrainer
    from brain.mechanisms.memory_integrity_layer import MemoryIntegrityLayer
    from brain.mechanisms.outward_reach_layer import OutwardReachLayer
    from brain.mechanisms.compression_fidelity_layer import (
        CompressionFidelityLayer,
    )
    from skills.heartbeat_activities._brain_post import (
        post_memory_encode, post_outward_reach_call, post_compression,
    )

    mil = MemoryIntegrityLayer()
    orl = OutwardReachLayer()
    cfl = CompressionFidelityLayer()

    post_outward_reach_call(
        provider="tavily", intent="research", success=True, latency_ms=180, n_hits=4,
    )
    post_memory_encode(
        content="finding from research",
        intent="observation", source_kind="external",
        content_confidence=0.7, source_confidence=0.85,
    )
    post_compression(
        intent="digest",
        source_text="A long source text that covers something. It might be true. Some studies suggest it.",
        summary="Source covers something; might be true; some studies suggest.",
    )

    drainer = BrainEventDrainer(mechanisms={
        "MemoryIntegrityLayer": mil,
        "OutwardReachLayer": orl,
        "CompressionFidelityLayer": cfl,
    })
    res = drainer.drain()
    assert res["drained"] == 3
    assert res["failed"] == 0
    # Each mechanism saw its call.
    assert mil.total_encoded == 1
    assert orl.global_intents.get("research", 0) >= 1
    assert "tavily" in orl.providers
    assert len(cfl.compressions) == 1
