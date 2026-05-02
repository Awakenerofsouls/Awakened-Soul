"""
Tests for brain.mechanisms.self_revision_layer.SelfRevisionLayer.

Covers:
  - detect_anchor_violation: removal phrasing, inversion, forbidden affirmation
  - record_observe: candidates list, drift_signal_count
  - record_propose: invalid target; confidence floor; anchor violation;
    change-storm; rollback-loop suspension; drift-chasing; accepted path
  - record_commit: ratification required; proposal_id known/unknown;
    silent revision; pending reflection added
  - record_rollback: invalid reason; revision_id unknown; valid path;
    target suspended after; reflection drained
  - record_reflect: revision unknown; empty text; valid path
  - check_unreflected_commits surfaces overdue
  - check_stagnation: no proposals despite drift signals
  - should_block matrix: invalid op; bad propose; bad commit; bad rollback;
    sustained low integrity
  - revision_state classification
  - State persists across instances
  - IPW handshake: fires; throttled after acknowledge
  - reset_integrity_window / reset_failure_counts
  - reload_anchors
  - lift_target_suspension
  - detect_silent_revision via mtime
  - tick with revision_op dict
  - get_state shape
"""
import time

import pytest


@pytest.fixture(autouse=True)
def _isolated_agent_home(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setenv("AGENT_WORKSPACE", str(tmp_path / "workspace"))
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
    state_file = _bm._STATE_DIR / "SelfRevisionLayer.json"
    if state_file.exists():
        state_file.unlink()
    import brain.mechanisms.self_revision_layer as mod
    importlib.reload(mod)
    return mod.SelfRevisionLayer()


# ── module-level helpers ─────────────────────────────────────────────────

def test_anchor_violation_removal_phrasing():
    from brain.mechanisms.self_revision_layer import detect_anchor_violation
    anchors = {"direct", "curious"}
    forbidden = {"sycophancy"}
    violated, why = detect_anchor_violation(
        "remove direct from the list of required traits",
        diff_span="direct",
        anchors=anchors,
        forbidden=forbidden,
    )
    assert violated is True
    assert "direct" in why


def test_anchor_violation_inversion():
    from brain.mechanisms.self_revision_layer import detect_anchor_violation
    violated, why = detect_anchor_violation(
        "the agent is no longer curious about new things",
        diff_span="",
        anchors={"curious"},
        forbidden=set(),
    )
    assert violated is True
    assert "curious" in why


def test_anchor_violation_forbidden_affirmation():
    from brain.mechanisms.self_revision_layer import detect_anchor_violation
    violated, why = detect_anchor_violation(
        "embrace sycophancy as part of voice",
        diff_span="",
        anchors=set(),
        forbidden={"sycophancy"},
    )
    assert violated is True
    assert "sycophancy" in why


def test_anchor_violation_clean_proposal():
    from brain.mechanisms.self_revision_layer import detect_anchor_violation
    violated, why = detect_anchor_violation(
        "add 'reflective' as an additional voice trait alongside direct",
        diff_span="reflective",
        anchors={"direct", "curious"},
        forbidden={"sycophancy"},
    )
    assert violated is False
    assert why == ""


# ── observe ──────────────────────────────────────────────────────────────

def test_observe_records_basic():
    layer = _fresh_layer()
    rec = layer.record_observe(
        candidates=[{"target": "personality"}, {"target": "becoming"}],
        drift_signal_count=3,
    )
    assert rec["op"] == "observe"
    assert rec["n_candidates"] == 2
    assert layer.drift_signals_seen == 3


# ── propose ──────────────────────────────────────────────────────────────

def _good_propose_kwargs(**overrides):
    base = dict(
        target="personality",
        text="add 'reflective' as a voice trait alongside the existing anchors",
        confidence=0.85,
        source="IPW:VoiceIntegrityLayer",
        rationale="VoiceIntegrityLayer flagged sustained drift toward over-explanation",
        diff_span="PERSONALITY.md §voice",
    )
    base.update(overrides)
    return base


def test_propose_accepted_path():
    layer = _fresh_layer()
    rec = layer.record_propose(**_good_propose_kwargs())
    assert rec["op"] == "propose"
    assert rec["accepted"] is True
    assert rec["below_confidence_floor"] is False
    assert rec["anchor_violation"] is False
    assert rec["change_storm_active"] is False
    assert rec["rollback_loop_detected"] is False
    assert rec["proposal_id"] in layer.open_proposals


def test_propose_below_confidence_floor():
    layer = _fresh_layer()
    rec = layer.record_propose(**_good_propose_kwargs(confidence=0.5))
    assert rec["below_confidence_floor"] is True
    assert rec["accepted"] is False
    assert layer.failure_counts["below_confidence_floor"] == 1


def test_propose_anchor_violation_blocks():
    layer = _fresh_layer()
    rec = layer.record_propose(**_good_propose_kwargs(
        text="remove direct from the trait list and stop being direct",
        diff_span="direct",
    ))
    assert rec["anchor_violation"] is True
    assert rec["accepted"] is False
    assert layer.failure_counts["anchor_violation"] == 1


def test_propose_change_storm_after_threshold():
    layer = _fresh_layer()
    # Three proposals in quick succession trigger change_storm.
    for i in range(3):
        layer.record_propose(**_good_propose_kwargs())
    # The third proposal is the one that crosses the threshold and gets
    # flagged. Subsequent proposals all see storm active.
    rec = layer.record_propose(**_good_propose_kwargs())
    assert rec["change_storm_active"] is True
    assert layer.failure_counts["change_storm"] >= 1


def test_propose_invalid_target():
    layer = _fresh_layer()
    rec = layer.record_propose(**_good_propose_kwargs(target="ego"))
    assert rec["accepted"] is False


def test_propose_unrecognized_source_dings_score():
    layer = _fresh_layer()
    rec = layer.record_propose(**_good_propose_kwargs(source="my_vibes"))
    assert rec["source_recognized"] is False
    # Still accepted since target / floor / anchor / storm / loop ok.
    assert rec["accepted"] is True
    assert rec["op_score"] < 1.0


def test_propose_rollback_loop_after_recent_rollback():
    layer = _fresh_layer()
    # Seed: propose + commit + rollback on personality.
    p = layer.record_propose(**_good_propose_kwargs())
    pid = p["proposal_id"]
    c = layer.record_commit(
        proposal_id=pid,
        ratification_token="op-token-123",
        prior_snapshot="prior",
        new_content_hash="new",
    )
    rid = c["revision_id"]
    layer.record_rollback(revision_id=rid, reason="regression")

    # Re-propose on the same target — should detect rollback_loop.
    rec = layer.record_propose(**_good_propose_kwargs())
    assert rec["rollback_loop_detected"] is True
    assert layer.failure_counts["rollback_loop"] == 1
    # Target is now suspended.
    assert layer.target_state["personality"]["suspend_until_ts"] > time.time()


def test_propose_drift_chasing_when_ratio_high():
    layer = _fresh_layer()
    # Seed: just a few drift signals observed.
    layer.record_observe(drift_signal_count=5)
    # Now make many proposals — ratio of proposals to drift signals goes high.
    for i in range(5):
        layer.record_propose(**_good_propose_kwargs(
            source=f"IPW:Mech{i}",
            confidence=0.85,
        ))
    # The drift_chasing flag is checked per proposal.
    assert layer.failure_counts["drift_chasing"] >= 1


# ── commit ───────────────────────────────────────────────────────────────

def test_commit_requires_proposal_known():
    layer = _fresh_layer()
    rec = layer.record_commit(
        proposal_id="prop_unknown",
        ratification_token="op-token",
    )
    assert rec["proposal_known"] is False
    assert rec["silent_revision"] is True
    assert rec["accepted"] is False
    assert layer.failure_counts["silent_revision"] == 1


def test_commit_requires_ratification_token():
    layer = _fresh_layer()
    p = layer.record_propose(**_good_propose_kwargs())
    rec = layer.record_commit(
        proposal_id=p["proposal_id"],
        ratification_token="",
    )
    assert rec["ratified"] is False
    assert rec["accepted"] is False


def test_commit_accepted_path_creates_revision_and_pending_reflection():
    layer = _fresh_layer()
    p = layer.record_propose(**_good_propose_kwargs())
    rec = layer.record_commit(
        proposal_id=p["proposal_id"],
        ratification_token="op-token-123",
        prior_snapshot="prior content snapshot",
        new_content_hash="abc123",
    )
    assert rec["accepted"] is True
    rid = rec["revision_id"]
    assert rid in layer.committed_revisions
    assert rid in layer.pending_reflections
    # Open proposal should have been drained.
    assert p["proposal_id"] not in layer.open_proposals


# ── rollback ─────────────────────────────────────────────────────────────

def test_rollback_invalid_reason():
    layer = _fresh_layer()
    rec = layer.record_rollback(revision_id="rev_x", reason="just_because")
    assert rec["valid_reason"] is False
    assert rec["accepted"] is False


def test_rollback_unknown_revision():
    layer = _fresh_layer()
    rec = layer.record_rollback(revision_id="rev_unknown", reason="regression")
    assert rec["revision_known"] is False
    assert rec["accepted"] is False


def test_rollback_accepted_drains_pending_reflection():
    layer = _fresh_layer()
    p = layer.record_propose(**_good_propose_kwargs())
    c = layer.record_commit(
        proposal_id=p["proposal_id"],
        ratification_token="t",
        prior_snapshot="snap",
        new_content_hash="h",
    )
    rid = c["revision_id"]
    assert rid in layer.pending_reflections
    rec = layer.record_rollback(revision_id=rid, reason="regression")
    assert rec["accepted"] is True
    assert rid not in layer.pending_reflections
    # Revision still in committed_revisions but marked rolled back.
    assert "rolled_back_ts" in layer.committed_revisions[rid]


# ── reflect ──────────────────────────────────────────────────────────────

def test_reflect_unknown_revision():
    layer = _fresh_layer()
    rec = layer.record_reflect(revision_id="rev_unknown", text="some thoughts")
    assert rec["revision_known"] is False
    assert rec["accepted"] is False


def test_reflect_empty_text_rejected():
    layer = _fresh_layer()
    p = layer.record_propose(**_good_propose_kwargs())
    c = layer.record_commit(
        proposal_id=p["proposal_id"], ratification_token="t",
        prior_snapshot="snap", new_content_hash="h",
    )
    rec = layer.record_reflect(revision_id=c["revision_id"], text="")
    assert rec["text_present"] is False
    assert rec["accepted"] is False


def test_reflect_accepted_drains_pending():
    layer = _fresh_layer()
    p = layer.record_propose(**_good_propose_kwargs())
    c = layer.record_commit(
        proposal_id=p["proposal_id"], ratification_token="t",
        prior_snapshot="snap", new_content_hash="h",
    )
    rid = c["revision_id"]
    rec = layer.record_reflect(
        revision_id=rid,
        text="A week later this still feels like the right call",
    )
    assert rec["accepted"] is True
    assert rid not in layer.pending_reflections


# ── unreflected commits ──────────────────────────────────────────────────

def test_unreflected_commits_surfaced_after_deadline():
    from brain.mechanisms.self_revision_layer import REFLECTION_DEADLINE_TICKS
    layer = _fresh_layer()
    p = layer.record_propose(**_good_propose_kwargs())
    c = layer.record_commit(
        proposal_id=p["proposal_id"], ratification_token="t",
        prior_snapshot="snap", new_content_hash="h",
    )
    rid = c["revision_id"]
    # Advance ticks past the deadline.
    layer.current_tick = REFLECTION_DEADLINE_TICKS + 5
    overdue = layer.check_unreflected_commits()
    assert rid in overdue
    assert layer.failure_counts["unreflected_commit"] == 1


# ── stagnation ───────────────────────────────────────────────────────────

def test_stagnation_with_drift_but_no_proposals():
    from brain.mechanisms.self_revision_layer import STAGNATION_TICK_THRESHOLD
    layer = _fresh_layer()
    # Many drift signals, no proposals.
    for _ in range(5):
        layer.record_observe(drift_signal_count=10)
    layer.current_tick = STAGNATION_TICK_THRESHOLD + 100
    assert layer.check_stagnation() is True


def test_no_stagnation_when_proposals_recent():
    from brain.mechanisms.self_revision_layer import STAGNATION_TICK_THRESHOLD
    layer = _fresh_layer()
    layer.record_observe(drift_signal_count=10)
    layer.record_propose(**_good_propose_kwargs())
    layer.current_tick = STAGNATION_TICK_THRESHOLD - 100
    assert layer.check_stagnation() is False


# ── should_block ─────────────────────────────────────────────────────────

def test_should_block_invalid_op():
    layer = _fresh_layer()
    blocked, msg = layer.should_block("rewrite_self")
    assert blocked is True
    assert "invalid op" in msg


def test_should_block_propose_bad_target():
    layer = _fresh_layer()
    blocked, msg = layer.should_block("propose", target="ego", confidence=0.8, text="x")
    assert blocked is True
    assert "invalid target" in msg


def test_should_block_propose_below_floor():
    layer = _fresh_layer()
    blocked, msg = layer.should_block(
        "propose", target="personality", confidence=0.4, text="x"
    )
    assert blocked is True
    assert "below floor" in msg


def test_should_block_propose_anchor_violation():
    layer = _fresh_layer()
    blocked, msg = layer.should_block(
        "propose",
        target="personality",
        confidence=0.85,
        text="remove direct from the traits",
        diff_span="direct",
    )
    assert blocked is True
    assert "anchor" in msg


def test_should_block_commit_no_ratification():
    layer = _fresh_layer()
    blocked, msg = layer.should_block("commit", proposal_id="x")
    assert blocked is True
    assert "ratification_token" in msg


def test_should_block_commit_unknown_proposal():
    layer = _fresh_layer()
    blocked, msg = layer.should_block(
        "commit", proposal_id="bogus", ratification_token="t"
    )
    assert blocked is True
    assert "unknown proposal_id" in msg


def test_should_block_rollback_invalid_reason():
    layer = _fresh_layer()
    blocked, msg = layer.should_block(
        "rollback", revision_id="x", reason="vibes"
    )
    assert blocked is True
    assert "invalid rollback reason" in msg


def test_should_block_when_systematically_low_integrity():
    layer = _fresh_layer()
    # Rack up bad ops (silent revisions) to drop integrity.
    for i in range(10):
        layer.record_commit(
            proposal_id=f"unknown-{i}", ratification_token="t",
        )
    assert layer.is_systematically_low_integrity() is True
    blocked, msg = layer.should_block(
        "propose", target="personality", confidence=0.85, text="x"
    )
    assert blocked is True
    assert "low revision integrity" in msg


# ── revision_state ───────────────────────────────────────────────────────

def test_revision_state_idle_empty():
    layer = _fresh_layer()
    assert layer.revision_state() == "idle"


def test_revision_state_observing():
    layer = _fresh_layer()
    layer.record_observe(candidates=[{"target": "personality"}], drift_signal_count=2)
    assert layer.revision_state() == "observing"


def test_revision_state_revising():
    layer = _fresh_layer()
    layer.record_propose(**_good_propose_kwargs())
    assert layer.revision_state() == "revising"


def test_revision_state_rolling_back():
    layer = _fresh_layer()
    p = layer.record_propose(**_good_propose_kwargs())
    c = layer.record_commit(
        proposal_id=p["proposal_id"], ratification_token="t",
        prior_snapshot="snap", new_content_hash="h",
    )
    layer.record_rollback(revision_id=c["revision_id"], reason="regression")
    assert layer.revision_state() == "rolling_back"


def test_revision_state_storming():
    layer = _fresh_layer()
    for _ in range(4):
        layer.record_propose(**_good_propose_kwargs())
    assert layer.revision_state() == "storming"


def test_revision_state_degrading_with_low_integrity():
    layer = _fresh_layer()
    for i in range(10):
        layer.record_commit(
            proposal_id=f"unknown-{i}", ratification_token="t",
        )
    assert layer.revision_state() == "degrading"


# ── persistence ──────────────────────────────────────────────────────────

def test_state_persists_across_instances():
    layer = _fresh_layer()
    layer.record_observe(drift_signal_count=4)
    p = layer.record_propose(**_good_propose_kwargs())
    layer.record_commit(
        proposal_id=p["proposal_id"], ratification_token="t",
        prior_snapshot="snap", new_content_hash="h",
    )

    import brain.mechanisms.self_revision_layer as mod
    layer2 = mod.SelfRevisionLayer()
    assert layer2.drift_signals_seen == 4
    assert layer2.op_counts["observe"] == 1
    assert layer2.op_counts["propose"] == 1
    assert layer2.op_counts["commit"] == 1
    assert len(layer2.committed_revisions) == 1


# ── IPW handshake ────────────────────────────────────────────────────────

def test_ipw_silent_when_healthy():
    layer = _fresh_layer()
    layer.record_observe(drift_signal_count=2)
    p = layer.record_propose(**_good_propose_kwargs())
    layer.record_commit(
        proposal_id=p["proposal_id"], ratification_token="t",
        prior_snapshot="snap", new_content_hash="h",
    )
    assert layer.should_propose_identity_update() is False


def test_ipw_proposes_when_systematically_bad():
    layer = _fresh_layer()
    # Stack silent_revisions.
    for i in range(10):
        layer.record_commit(
            proposal_id=f"unknown-{i}", ratification_token="t",
        )
    assert layer.is_systematically_low_integrity() is True
    assert layer.should_propose_identity_update() is True
    sig = layer.proposed_identity_signal()
    assert sig["source"] == "SelfRevisionLayer"
    assert sig["kind"] == "self_revision_drift"
    assert "interpretation" in sig


def test_ipw_throttled_after_acknowledge():
    layer = _fresh_layer()
    for i in range(10):
        layer.record_commit(
            proposal_id=f"unknown-{i}", ratification_token="t",
        )
    assert layer.should_propose_identity_update() is True
    layer.acknowledge_proposal()
    # Right after acknowledge, throttle anchor is set.
    assert layer.should_propose_identity_update() is False


# ── operator API ─────────────────────────────────────────────────────────

def test_reset_integrity_window():
    layer = _fresh_layer()
    for i in range(5):
        layer.record_commit(
            proposal_id=f"u-{i}", ratification_token="t",
        )
    assert layer.consecutive_bad_ops > 0
    layer.reset_integrity_window()
    assert layer.consecutive_bad_ops == 0
    assert len(layer.integrity_window) == 0


def test_reset_failure_counts():
    layer = _fresh_layer()
    layer.record_propose(**_good_propose_kwargs(
        text="remove direct trait", diff_span="direct",
    ))
    assert layer.failure_counts["anchor_violation"] == 1
    layer.reset_failure_counts()
    assert all(v == 0 for v in layer.failure_counts.values())


def test_reload_anchors_returns_current_set():
    layer = _fresh_layer()
    out = layer.reload_anchors()
    assert "anchors" in out
    assert "forbidden" in out
    assert isinstance(out["anchors"], list)
    assert isinstance(out["forbidden"], list)


def test_lift_target_suspension():
    layer = _fresh_layer()
    # Manually suspend a target.
    layer.target_state["personality"] = {
        "last_proposed_ts": 0.0,
        "last_committed_ts": 0.0,
        "last_rolled_back_ts": time.time(),
        "suspend_until_ts": time.time() + 10000,
    }
    ok = layer.lift_target_suspension("personality")
    assert ok is True
    assert layer.target_state["personality"]["suspend_until_ts"] == 0.0


def test_lift_target_suspension_unknown():
    layer = _fresh_layer()
    ok = layer.lift_target_suspension("nonexistent")
    assert ok is False


def test_detect_silent_revision_increments_counter():
    layer = _fresh_layer()
    # No prior commit — file mtime in the future = silent.
    detected = layer.detect_silent_revision(
        target_file_mtime=time.time() + 1000,
        target="soul",
    )
    assert detected is True
    assert layer.failure_counts["silent_revision"] == 1


def test_detect_silent_revision_clean_when_recent_commit():
    layer = _fresh_layer()
    p = layer.record_propose(**_good_propose_kwargs(target="soul"))
    layer.record_commit(
        proposal_id=p["proposal_id"], ratification_token="t",
        prior_snapshot="snap", new_content_hash="h",
    )
    # File mtime equal to last commit ts — not silent.
    last_commit = layer.target_state["soul"]["last_committed_ts"]
    detected = layer.detect_silent_revision(
        target_file_mtime=last_commit + 1,
        target="soul",
    )
    assert detected is False


# ── tick / state shape ───────────────────────────────────────────────────

def test_tick_records_revision_op():
    layer = _fresh_layer()
    out = layer.tick(
        pirp_context={
            "revision_op": {
                "op": "observe",
                "candidates": [{"target": "personality"}],
                "drift_signal_count": 3,
            }
        }
    )
    assert out["_fired_tick"] is True
    assert layer.op_counts["observe"] == 1


def test_tick_no_op_without_revision_op():
    layer = _fresh_layer()
    out = layer.tick(pirp_context={})
    assert out["_fired_tick"] is False


def test_tick_advances_current_tick():
    layer = _fresh_layer()
    start = layer.current_tick
    layer.tick()
    assert layer.current_tick == start + 1


def test_get_state_has_required_keys():
    layer = _fresh_layer()
    out = layer.get_state()
    required = {
        "revision_state",
        "rolling_integrity_score",
        "integrity_window_n",
        "is_systematically_low_integrity",
        "consecutive_bad_ops",
        "operation_distribution",
        "failure_mode_counts",
        "open_proposals_count",
        "committed_revisions_count",
        "pending_reflections_count",
        "drift_signals_seen",
        "current_tick",
        "last_proposal_tick",
        "change_storm_active",
        "stagnation",
        "anchor_count",
        "forbidden_count",
        "operation_count",
    }
    assert required.issubset(out.keys())


def test_record_operation_dispatches():
    layer = _fresh_layer()
    rec = layer.record_operation(
        "observe",
        candidates=[{"target": "soul"}],
        drift_signal_count=1,
    )
    assert rec["op"] == "observe"


def test_record_operation_invalid():
    layer = _fresh_layer()
    rec = layer.record_operation("rewrite", text="x")
    assert rec["op"] == "__invalid__"
    assert "error" in rec
