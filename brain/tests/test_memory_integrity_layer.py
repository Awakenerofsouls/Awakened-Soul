"""
Tests for brain.mechanisms.memory_integrity_layer.MemoryIntegrityLayer.

Covers:
  - jaccard_similarity helper
  - record_encode: source-confusion gap, pattern-separation actions,
    interference detection, dream-source cap
  - record_retrieve: untagged mode flagged, retrieval-storm flagged,
    reconsolidation windows opened
  - record_consolidate: consolidation_deficit when support exists but
    not promoted; pattern_repetition cleared on promote
  - record_forget: requires reason, drops episode, resets encode counter
  - record_rehearse: reconsolidation_drift when content changes within
    window
  - should_block: invalid op; dream encode with too-high source_conf;
    forget without reason; consolidate below floor; sustained low integrity
  - Rolling integrity score + min N gate
  - Hoarding signal increments correctly
  - consolidation_eligible_patterns surfaces ready patterns
  - memory_state classification: idle, active, drifting, hoarding,
    healthy, degrading
  - State persists across instances
  - IPW handshake: fires after threshold; throttled after acknowledge
  - reset_integrity_window / reset_failure_counts / configure_thresholds
  - tick with memory_op dict
  - get_state shape
"""
import time

import pytest


@pytest.fixture(autouse=True)
def _isolated_agent_home(monkeypatch, tmp_path):
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
    state_file = _bm._STATE_DIR / "MemoryIntegrityLayer.json"
    if state_file.exists():
        state_file.unlink()
    import brain.mechanisms.memory_integrity_layer as mod
    importlib.reload(mod)
    return mod.MemoryIntegrityLayer()


# ── helpers / module-level ───────────────────────────────────────────────

def test_jaccard_similarity_identical_and_disjoint():
    from brain.mechanisms.memory_integrity_layer import jaccard_similarity

    assert jaccard_similarity("the dog ran fast", "the dog ran fast") == 1.0
    assert jaccard_similarity("foo bar", "baz qux") == 0.0
    assert 0.0 < jaccard_similarity(
        "the dog ran fast through the park",
        "the dog walked through the park slowly",
    ) < 1.0


def test_jaccard_empty_inputs():
    from brain.mechanisms.memory_integrity_layer import jaccard_similarity
    assert jaccard_similarity("", "") == 0.0
    assert jaccard_similarity("hello", "") == 0.0


# ── encode ───────────────────────────────────────────────────────────────

def test_encode_records_basic_op():
    layer = _fresh_layer()
    rec = layer.record_encode(
        content="The user said the deadline is Tuesday.",
        intent="episode",
        source="user",
        content_confidence=0.9,
        source_confidence=0.9,
    )
    assert rec["op"] == "encode"
    assert rec["source_confusion"] is False
    assert rec["pattern_separation_action"] == "distinct"
    assert layer.op_counts["encode"] == 1
    assert layer.total_encoded == 1


def test_encode_source_confusion_flagged():
    """High content confidence with low source confidence flags."""
    layer = _fresh_layer()
    rec = layer.record_encode(
        content="The market closes at 4pm.",
        intent="fact",
        source="inference",
        content_confidence=0.95,
        source_confidence=0.3,
    )
    assert rec["source_confusion"] is True
    assert rec["source_confidence_gap"] > 0.3
    assert layer.failure_counts["source_confusion"] == 1


def test_encode_no_source_confusion_when_aligned():
    layer = _fresh_layer()
    rec = layer.record_encode(
        content="A note.",
        intent="observation",
        source="user",
        content_confidence=0.6,
        source_confidence=0.5,
    )
    assert rec["source_confusion"] is False
    assert layer.failure_counts["source_confusion"] == 0


def test_encode_pattern_separation_link_when_near_identical():
    layer = _fresh_layer()
    text = "user requested a daily summary at 9am every weekday morning"
    layer.record_encode(content=text, intent="episode", source="user")
    rec = layer.record_encode(content=text, intent="episode", source="user")
    assert rec["max_similarity"] >= 0.85
    assert rec["pattern_separation_action"] == "link"
    # Link-mode does NOT add a new recent_episode, so length stays 1.
    assert len(layer.recent_episodes) == 1


def test_encode_pattern_separation_near_duplicate():
    layer = _fresh_layer()
    layer.record_encode(
        content="user mentioned the deadline for the report is Friday afternoon",
        intent="episode",
        source="user",
    )
    rec = layer.record_encode(
        content="user mentioned the deadline for the report is Friday morning",
        intent="episode",
        source="user",
    )
    assert rec["pattern_separation_action"] in ("near_duplicate", "link")


def test_encode_dream_source_caps_confidence():
    layer = _fresh_layer()
    rec = layer.record_encode(
        content="A dreamed observation",
        intent="observation",
        source="dream",
        content_confidence=0.9,
        source_confidence=0.9,  # gets capped
    )
    assert rec["source_confidence"] <= 0.4


def test_encode_interference_with_negation_flip():
    layer = _fresh_layer()
    layer.record_encode(
        content="the API rate limit is fifty requests per minute strict",
        intent="fact",
        source="user",
    )
    rec = layer.record_encode(
        content="the API rate limit is not fifty requests per minute strict",
        intent="fact",
        source="user",
    )
    assert rec["interference"] is True
    assert layer.failure_counts["interference"] == 1


# ── retrieve ─────────────────────────────────────────────────────────────

def test_retrieve_untagged_mode_flagged():
    layer = _fresh_layer()
    rec = layer.record_retrieve(query="what did the user say?", mode=None)
    assert rec["untagged"] is True
    assert rec["mode"] == "recall"  # default fallback


def test_retrieve_tagged_mode_clean():
    layer = _fresh_layer()
    rec = layer.record_retrieve(query="recall test", mode="recall")
    assert rec["untagged"] is False
    assert rec["mode"] == "recall"


def test_retrieve_storm_flagged():
    layer = _fresh_layer()
    hits = [
        {"memory_id": f"m{i}", "similarity": 0.9, "content": "foo"}
        for i in range(7)
    ]
    rec = layer.record_retrieve(query="too many", mode="recall", hits=hits)
    assert rec["retrieval_storm"] is True
    assert layer.failure_counts["retrieval_storms"] == 1


def test_retrieve_no_storm_when_few_hits():
    layer = _fresh_layer()
    hits = [{"memory_id": f"m{i}", "similarity": 0.9} for i in range(3)]
    rec = layer.record_retrieve(query="few", mode="recognize", hits=hits)
    assert rec["retrieval_storm"] is False


def test_retrieve_opens_reconsolidation_window():
    layer = _fresh_layer()
    rec = layer.record_retrieve(
        query="x",
        mode="recall",
        hits=[{"memory_id": "ep_42", "similarity": 0.9, "content": "old text"}],
    )
    assert "ep_42" in rec["reconsolidation_windows_opened"]
    assert "ep_42" in layer.retrieval_state


# ── consolidate ──────────────────────────────────────────────────────────

def test_consolidate_deficit_when_support_but_not_promoted():
    layer = _fresh_layer()
    rec = layer.record_consolidate(
        pattern="user prefers dark mode",
        support_count=5,
        cycles_since_first=2,
        promoted=False,
    )
    assert rec["consolidation_deficit"] is True
    assert layer.failure_counts["consolidation_deficit"] == 1


def test_consolidate_no_deficit_when_promoted():
    layer = _fresh_layer()
    rec = layer.record_consolidate(
        pattern="user prefers dark mode",
        support_count=5,
        cycles_since_first=2,
        promoted=True,
    )
    assert rec["consolidation_deficit"] is False


def test_consolidate_below_floor_no_deficit_flag():
    """Below floor isn't a deficit — it's just not eligible yet."""
    layer = _fresh_layer()
    rec = layer.record_consolidate(
        pattern="too few examples",
        support_count=2,
        cycles_since_first=2,
        promoted=False,
    )
    assert rec["consolidation_deficit"] is False
    assert rec["below_support_floor"] is True


def test_consolidate_promoted_clears_pattern_repetition():
    layer = _fresh_layer()
    # Build pattern repetition through encodes.
    for _ in range(3):
        layer.record_encode(
            content="agent should always use absolute paths in scripts",
            intent="reflection",
            source="inference",
        )
    assert len(layer.pattern_repetition) >= 1
    # Pull out the actual pattern signature to "promote"
    layer.record_consolidate(
        pattern="agent should always use absolute paths in scripts",
        support_count=3,
        cycles_since_first=2,
        promoted=True,
    )
    # Promotion clears it.
    assert len(layer.pattern_repetition) == 0


# ── forget ───────────────────────────────────────────────────────────────

def test_forget_with_valid_reason_succeeds():
    layer = _fresh_layer()
    layer.record_encode(content="ephemeral", intent="episode", source="user")
    rec = layer.record_forget(reason="capacity", count=1)
    assert rec["valid_reason"] is True
    assert rec["op_score"] == 1.0
    assert layer.total_forgotten == 1
    assert layer.encodes_since_forget == 0


def test_forget_without_reason_scores_zero():
    layer = _fresh_layer()
    rec = layer.record_forget(reason=None)
    assert rec["valid_reason"] is False
    assert rec["op_score"] == 0.0


def test_forget_invalid_reason_scores_zero():
    layer = _fresh_layer()
    rec = layer.record_forget(reason="because")
    assert rec["valid_reason"] is False


def test_forget_drops_episode_from_recent():
    layer = _fresh_layer()
    enc = layer.record_encode(content="x", intent="episode", source="user")
    mid = enc["memory_id"]
    assert any(e["id"] == mid for e in layer.recent_episodes)
    layer.record_forget(memory_id=mid, reason="user_requested")
    assert not any(e["id"] == mid for e in layer.recent_episodes)


# ── rehearse ─────────────────────────────────────────────────────────────

def test_rehearse_reconsolidation_drift_when_content_changes_in_window():
    layer = _fresh_layer()
    # Open a window via retrieve.
    layer.record_retrieve(
        query="q",
        mode="recall",
        hits=[{"memory_id": "ep_1", "similarity": 0.9, "content": "old"}],
    )
    rec = layer.record_rehearse(
        memory_id="ep_1",
        prior_content="old",
        new_content="new",  # content actually changed
    )
    assert rec["reconsolidation_drift"] is True
    assert layer.failure_counts["reconsolidation_drift"] == 1


def test_rehearse_no_drift_when_content_unchanged():
    layer = _fresh_layer()
    layer.record_retrieve(
        query="q",
        mode="recall",
        hits=[{"memory_id": "ep_2", "similarity": 0.9, "content": "stable"}],
    )
    rec = layer.record_rehearse(
        memory_id="ep_2",
        prior_content="stable",
        new_content="stable",
    )
    assert rec["reconsolidation_drift"] is False
    assert rec["content_changed"] is False


def test_rehearse_no_drift_outside_window(monkeypatch):
    layer = _fresh_layer()
    # Manually pre-set a stale retrieval state.
    layer.retrieval_state["ep_3"] = {
        "last_retrieval_ts": time.time() - 10_000,  # way past 5 min
        "last_seen_content_hash": "abc",
        "mode": "recall",
    }
    rec = layer.record_rehearse(
        memory_id="ep_3",
        prior_content="x",
        new_content="y",
    )
    assert rec["within_reconsolidation_window"] is False
    assert rec["reconsolidation_drift"] is False


# ── should_block ─────────────────────────────────────────────────────────

def test_should_block_invalid_op():
    layer = _fresh_layer()
    blocked, msg = layer.should_block("hallucinate")
    assert blocked is True
    assert "invalid op" in msg


def test_should_block_dream_encode_with_high_source_confidence():
    layer = _fresh_layer()
    blocked, msg = layer.should_block(
        "encode", source="dream", source_confidence=0.9
    )
    assert blocked is True
    assert "dream" in msg


def test_should_block_dream_encode_below_cap_allowed():
    layer = _fresh_layer()
    blocked, _ = layer.should_block(
        "encode", source="dream", source_confidence=0.3
    )
    assert blocked is False


def test_should_block_forget_without_reason():
    layer = _fresh_layer()
    blocked, msg = layer.should_block("forget")
    assert blocked is True
    assert "reason" in msg


def test_should_block_forget_invalid_reason():
    layer = _fresh_layer()
    blocked, msg = layer.should_block("forget", reason="whim")
    assert blocked is True


def test_should_block_consolidate_below_floor():
    layer = _fresh_layer()
    blocked, msg = layer.should_block(
        "consolidate", support_count=1, cycles_since_first=2
    )
    assert blocked is True
    assert "supporting" in msg


def test_should_block_consolidate_below_cycle_floor():
    layer = _fresh_layer()
    blocked, msg = layer.should_block(
        "consolidate", support_count=5, cycles_since_first=0
    )
    assert blocked is True


def test_should_block_consolidate_above_floor_allowed():
    layer = _fresh_layer()
    blocked, _ = layer.should_block(
        "consolidate", support_count=5, cycles_since_first=2
    )
    assert blocked is False


def test_should_block_when_systematically_low_integrity():
    layer = _fresh_layer()
    # Rack up bad ops.
    for _ in range(15):
        layer.record_forget(reason=None)  # op_score=0 each time
    assert layer.is_systematically_low_integrity() is True
    blocked, msg = layer.should_block("encode", source="user", source_confidence=0.7)
    assert blocked is True
    assert "low memory integrity" in msg


# ── rolling integrity ────────────────────────────────────────────────────

def test_rolling_integrity_score_starts_at_one():
    layer = _fresh_layer()
    assert layer.rolling_integrity_score() == 1.0


def test_rolling_integrity_drops_with_bad_ops():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_forget(reason=None)
    assert layer.rolling_integrity_score() < 0.5


def test_systematically_low_integrity_requires_min_n():
    layer = _fresh_layer()
    # Just 3 bad ops — below INTEGRITY_MIN_N=8.
    for _ in range(3):
        layer.record_forget(reason=None)
    assert layer.is_systematically_low_integrity() is False


# ── hoarding ─────────────────────────────────────────────────────────────

def test_hoarding_increments_when_no_forget():
    from brain.mechanisms.memory_integrity_layer import HOARDING_ENCODE_GAP
    layer = _fresh_layer()
    for i in range(HOARDING_ENCODE_GAP + 1):
        layer.record_encode(
            content=f"distinct content number {i} with unique tokens",
            intent="episode",
            source="user",
            content_confidence=0.7,
            source_confidence=0.7,
        )
    assert layer.failure_counts["hoarding"] >= 1


def test_hoarding_resets_on_forget():
    layer = _fresh_layer()
    for i in range(20):
        layer.record_encode(content=f"item {i}", intent="episode", source="user")
    assert layer.encodes_since_forget == 20
    layer.record_forget(reason="capacity")
    assert layer.encodes_since_forget == 0


# ── consolidation eligibility ────────────────────────────────────────────

def test_consolidation_eligible_patterns_surfaces_ready(monkeypatch):
    layer = _fresh_layer()
    # Manually inject a pattern_repetition entry with old first_ts.
    sig = "abcd1234"
    layer.pattern_repetition[sig] = {
        "count": 4,
        "first_ts": time.time() - 7200,  # 2 hours ago
        "last_ts": time.time(),
        "ids": ["m1", "m2", "m3", "m4"],
    }
    eligible = layer.consolidation_eligible_patterns()
    assert any(p["signature"] == sig for p in eligible)


def test_consolidation_eligible_excludes_too_recent():
    layer = _fresh_layer()
    sig = "fresh1234"
    layer.pattern_repetition[sig] = {
        "count": 4,
        "first_ts": time.time(),  # right now
        "last_ts": time.time(),
        "ids": ["m1", "m2", "m3", "m4"],
    }
    eligible = layer.consolidation_eligible_patterns()
    assert not any(p["signature"] == sig for p in eligible)


# ── memory_state classification ──────────────────────────────────────────

def test_memory_state_idle_empty():
    layer = _fresh_layer()
    assert layer.memory_state() == "idle"


def test_memory_state_active_recent_op():
    layer = _fresh_layer()
    layer.record_encode(content="x", intent="episode", source="user")
    assert layer.memory_state() in ("active", "healthy")


def test_memory_state_degrading():
    layer = _fresh_layer()
    for _ in range(15):
        layer.record_forget(reason=None)
    assert layer.memory_state() == "degrading"


def test_memory_state_hoarding():
    from brain.mechanisms.memory_integrity_layer import HOARDING_ENCODE_GAP
    layer = _fresh_layer()
    for i in range(HOARDING_ENCODE_GAP + 1):
        layer.record_encode(
            content=f"unique-tokens-{i} distinct content here please",
            intent="episode",
            source="user",
        )
    # State should be hoarding (or degrading if score also tanked).
    assert layer.memory_state() in ("hoarding", "degrading")


# ── persistence ──────────────────────────────────────────────────────────

def test_state_persists_across_instances():
    layer = _fresh_layer()
    layer.record_encode(content="durable", intent="episode", source="user")
    layer.record_forget(reason="capacity")

    # Re-instantiate (without clearing state file).
    import brain.mechanisms.memory_integrity_layer as mod
    layer2 = mod.MemoryIntegrityLayer()
    assert layer2.total_encoded == 1
    assert layer2.total_forgotten == 1
    assert layer2.op_counts["encode"] == 1
    assert layer2.op_counts["forget"] == 1


# ── IPW handshake ────────────────────────────────────────────────────────

def test_ipw_does_not_propose_when_healthy():
    layer = _fresh_layer()
    layer.record_encode(
        content="happy path",
        intent="episode",
        source="user",
        content_confidence=0.7,
        source_confidence=0.7,
    )
    assert layer.should_propose_identity_update() is False


def test_ipw_proposes_when_systematically_bad():
    layer = _fresh_layer()
    for _ in range(15):
        layer.record_forget(reason=None)
    assert layer.is_systematically_low_integrity() is True
    assert layer.should_propose_identity_update() is True
    sig = layer.proposed_identity_signal()
    assert sig["source"] == "MemoryIntegrityLayer"
    assert sig["kind"] == "systematic_memory_drift"
    assert "interpretation" in sig


def test_ipw_throttled_after_acknowledge():
    layer = _fresh_layer()
    for _ in range(15):
        layer.record_forget(reason=None)
    assert layer.should_propose_identity_update() is True
    layer.acknowledge_proposal()
    # Right after acknowledge, threshold was anchored at 15; should not
    # re-fire until consecutive_bad_ops climbs by IPW_REPORT_EVERY.
    assert layer.should_propose_identity_update() is False
    # Add a couple more bad ops — still below new threshold.
    for _ in range(2):
        layer.record_forget(reason=None)
    assert layer.should_propose_identity_update() is False


# ── operator API ─────────────────────────────────────────────────────────

def test_reset_integrity_window():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_forget(reason=None)
    assert layer.consecutive_bad_ops > 0
    layer.reset_integrity_window()
    assert layer.consecutive_bad_ops == 0
    assert len(layer.integrity_window) == 0


def test_reset_failure_counts():
    layer = _fresh_layer()
    layer.record_encode(
        content="x",
        intent="episode",
        source="inference",
        content_confidence=0.95,
        source_confidence=0.2,
    )
    assert layer.failure_counts["source_confusion"] == 1
    layer.reset_failure_counts()
    assert all(v == 0 for v in layer.failure_counts.values())


def test_configure_thresholds_persists_overrides():
    layer = _fresh_layer()
    out = layer.configure_thresholds(
        source_confusion_gap=0.5,
        hoarding_encode_gap=50,
        reconsolidation_window_sec=120,
    )
    assert out["source_confusion_gap"] == 0.5
    assert out["hoarding_encode_gap"] == 50
    assert out["reconsolidation_window_sec"] == 120


# ── tick / state shape ───────────────────────────────────────────────────

def test_tick_records_memory_op_from_pirp():
    layer = _fresh_layer()
    out = layer.tick(
        pirp_context={
            "memory_op": {
                "op": "encode",
                "content": "from tick",
                "intent": "episode",
                "source": "user",
                "content_confidence": 0.8,
                "source_confidence": 0.8,
            }
        }
    )
    assert out["_fired_tick"] is True
    assert layer.op_counts["encode"] == 1


def test_tick_no_op_without_memory_op():
    layer = _fresh_layer()
    out = layer.tick(pirp_context={})
    assert out["_fired_tick"] is False


def test_get_state_has_required_keys():
    layer = _fresh_layer()
    out = layer.get_state()
    required = {
        "memory_state",
        "rolling_integrity_score",
        "integrity_window_n",
        "is_systematically_low_integrity",
        "consecutive_bad_ops",
        "operation_distribution",
        "failure_mode_counts",
        "total_encoded",
        "total_forgotten",
        "outstanding_episodes",
        "encodes_since_forget",
        "open_reconsolidation_windows",
        "consolidation_eligible_count",
        "operation_count",
    }
    assert required.issubset(out.keys())


def test_record_operation_dispatches_to_encode():
    layer = _fresh_layer()
    rec = layer.record_operation(
        "encode",
        content="dispatched",
        intent="episode",
        source="user",
    )
    assert rec["op"] == "encode"


def test_record_operation_invalid_op():
    layer = _fresh_layer()
    rec = layer.record_operation("teleport", content="x")
    assert rec["op"] == "__invalid__"
    assert "error" in rec
