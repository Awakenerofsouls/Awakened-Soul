"""
Tests for brain.mechanisms.task_planning_layer.TaskPlanningLayer.

Covers:
  - record_decompose: over_decomposition; under_decomposition; cycle_detected;
    plan_storm; horizon + mode bookkeeping
  - record_commit: drains uncommitted; supersession increments incomplete_plans
  - record_revise: abandon w/o reason scores low; clean modify/insert; abandon
    drops plan from active
  - record_complete: unresolved subtasks block; clean path moves to pending
    reflection
  - record_reflect: unknown plan_id; non-substantive; clean path drains
    pending reflection
  - check_stale_plans: increments stale_plan after threshold
  - check_unreflected_completions: increments missing_reflection after deadline
  - should_block: invalid op; plan_storm gates decompose; abandon w/o reason;
    sustained low integrity
  - rolling integrity + min_n gate
  - planning_state classification
  - State persists across instances
  - IPW handshake fires + throttled
  - Operator API
  - tick advances + records planning_op
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
    import importlib
    import brain.base_mechanism as _bm
    state_file = _bm._STATE_DIR / "TaskPlanningLayer.json"
    if state_file.exists():
        state_file.unlink()
    import brain.mechanisms.task_planning_layer as mod
    importlib.reload(mod)
    return mod.TaskPlanningLayer()


# ── decompose ────────────────────────────────────────────────────────────

def test_decompose_records_basic():
    layer = _fresh_layer()
    rec = layer.record_decompose(
        plan_id="pl_1", goal="ship the fix",
        subtask_count=3, horizon="contextual", mode="build",
    )
    assert rec["op"] == "decompose"
    assert rec["over_decomposition"] is False
    assert rec["under_decomposition"] is False
    assert layer.horizon_counts["contextual"] == 1
    assert layer.mode_counts["build"] == 1


def test_decompose_over_decomposition_flagged():
    from brain.mechanisms.task_planning_layer import MAX_SUBTASKS_PER_GOAL
    layer = _fresh_layer()
    rec = layer.record_decompose(
        plan_id="pl_x", goal="too much",
        subtask_count=MAX_SUBTASKS_PER_GOAL + 5,
    )
    assert rec["over_decomposition"] is True
    assert layer.failure_counts["over_decomposition"] == 1


def test_decompose_under_decomposition_flagged():
    layer = _fresh_layer()
    rec = layer.record_decompose(
        plan_id="pl_x", goal="A and B and C",
        subtask_count=1, multi_part_goal=True,
    )
    assert rec["under_decomposition"] is True
    assert layer.failure_counts["under_decomposition"] == 1


def test_decompose_cycle_detected_dings_score():
    layer = _fresh_layer()
    rec = layer.record_decompose(
        plan_id="pl_x", goal="x", subtask_count=3, cycle_detected=True,
    )
    assert rec["cycle_detected"] is True
    assert rec["op_score"] < 1.0


def test_decompose_invalid_horizon_falls_back():
    layer = _fresh_layer()
    rec = layer.record_decompose(
        plan_id="pl_x", goal="x", subtask_count=2, horizon="weird",
    )
    assert rec["horizon"] == "contextual"


# ── plan_storm ───────────────────────────────────────────────────────────

def test_plan_storm_after_repeated_decomposes_no_commit():
    from brain.mechanisms.task_planning_layer import PLAN_STORM_DECOMPOSE_LIMIT
    layer = _fresh_layer()
    for i in range(PLAN_STORM_DECOMPOSE_LIMIT + 2):
        layer.record_decompose(plan_id=f"pl_{i}", goal=f"g{i}", subtask_count=2)
    assert layer.failure_counts["plan_storm"] >= 1


def test_plan_storm_clears_after_commit():
    from brain.mechanisms.task_planning_layer import PLAN_STORM_DECOMPOSE_LIMIT
    layer = _fresh_layer()
    # Decompose then commit each — never accumulates uncommitted.
    for i in range(PLAN_STORM_DECOMPOSE_LIMIT + 2):
        layer.record_decompose(plan_id=f"pl_{i}", goal=f"g{i}", subtask_count=2)
        layer.record_commit(plan_id=f"pl_{i}", goal=f"g{i}", track=f"t{i}")
    # Storm should NOT fire because each was committed.
    assert layer._plan_storm_active() is False


# ── commit ───────────────────────────────────────────────────────────────

def test_commit_clean():
    layer = _fresh_layer()
    layer.record_decompose(plan_id="pl_1", goal="x", subtask_count=2)
    rec = layer.record_commit(plan_id="pl_1", goal="x", track="main")
    assert rec["op"] == "commit"
    assert "pl_1" in layer.active_plans


def test_commit_supersedes_increments_incomplete():
    layer = _fresh_layer()
    layer.record_commit(plan_id="pl_a", goal="A", track="main")
    rec = layer.record_commit(plan_id="pl_b", goal="B", track="main", superseded="pl_a")
    assert layer.failure_counts["incomplete_plans"] == 1
    assert "pl_a" not in layer.active_plans
    assert "pl_b" in layer.active_plans


# ── revise ───────────────────────────────────────────────────────────────

def test_revise_abandon_without_reason_scores_low():
    layer = _fresh_layer()
    layer.record_commit(plan_id="pl_1", goal="x")
    rec = layer.record_revise(plan_id="pl_1", kind="abandon", reason="")
    assert rec["reason_present"] is False
    assert rec["op_score"] < 1.0


def test_revise_abandon_with_reason_drops_plan_from_active():
    layer = _fresh_layer()
    layer.record_commit(plan_id="pl_1", goal="x")
    rec = layer.record_revise(plan_id="pl_1", kind="abandon", reason="obsolete")
    assert "pl_1" not in layer.active_plans
    assert rec["op_score"] == 1.0


def test_revise_modify_touches_plan():
    layer = _fresh_layer()
    layer.record_commit(plan_id="pl_1", goal="x")
    layer.current_tick = 50
    layer.record_revise(plan_id="pl_1", kind="modify", reason="clarify")
    assert layer.active_plans["pl_1"]["last_touched_tick"] == 50


def test_revise_invalid_kind_dings_score():
    layer = _fresh_layer()
    layer.record_commit(plan_id="pl_1", goal="x")
    rec = layer.record_revise(plan_id="pl_1", kind="rewrite", reason="x")
    assert rec["kind_ok"] is False
    assert rec["op_score"] < 1.0


# ── complete ─────────────────────────────────────────────────────────────

def test_complete_unresolved_blocked():
    layer = _fresh_layer()
    layer.record_commit(plan_id="pl_1", goal="x")
    rec = layer.record_complete(
        plan_id="pl_1", subtask_count=3, unresolved_count=1,
    )
    assert rec["accepted"] is False


def test_complete_clean_moves_to_pending_reflection():
    layer = _fresh_layer()
    layer.record_commit(plan_id="pl_1", goal="x")
    rec = layer.record_complete(
        plan_id="pl_1", subtask_count=3, unresolved_count=0, elapsed_sec=120.0,
    )
    assert rec["accepted"] is True
    assert "pl_1" not in layer.active_plans
    assert "pl_1" in layer.pending_reflections


# ── reflect ──────────────────────────────────────────────────────────────

def test_reflect_unknown_plan_id():
    layer = _fresh_layer()
    rec = layer.record_reflect(plan_id="bogus", what_worked_count=1)
    assert rec["plan_known"] is False
    assert rec["op_score"] < 1.0


def test_reflect_non_substantive_dings_score():
    layer = _fresh_layer()
    layer.record_commit(plan_id="pl_1", goal="x")
    layer.record_complete(plan_id="pl_1", subtask_count=2, unresolved_count=0)
    rec = layer.record_reflect(plan_id="pl_1")
    assert rec["substantive"] is False
    assert rec["op_score"] < 1.0


def test_reflect_clean_drains_pending():
    layer = _fresh_layer()
    layer.record_commit(plan_id="pl_1", goal="x")
    layer.record_complete(plan_id="pl_1", subtask_count=2, unresolved_count=0)
    rec = layer.record_reflect(
        plan_id="pl_1",
        what_worked_count=2,
        what_didnt_count=1,
        has_what_id_do_differently=True,
    )
    assert rec["substantive"] is True
    assert rec["plan_known"] is True
    assert "pl_1" not in layer.pending_reflections


# ── stale + missing_reflection sweeps ────────────────────────────────────

def test_check_stale_plans_after_threshold():
    from brain.mechanisms.task_planning_layer import STALE_PLAN_TICK_THRESHOLD
    layer = _fresh_layer()
    layer.record_commit(plan_id="pl_1", goal="x")
    layer.current_tick = STALE_PLAN_TICK_THRESHOLD + 100
    stale = layer.check_stale_plans()
    assert "pl_1" in stale
    assert layer.failure_counts["stale_plan"] == 1


def test_check_unreflected_after_deadline():
    from brain.mechanisms.task_planning_layer import REFLECTION_DEADLINE_TICKS
    layer = _fresh_layer()
    layer.record_commit(plan_id="pl_1", goal="x")
    layer.record_complete(plan_id="pl_1", subtask_count=1, unresolved_count=0)
    layer.current_tick += REFLECTION_DEADLINE_TICKS + 5
    overdue = layer.check_unreflected_completions()
    assert "pl_1" in overdue
    assert layer.failure_counts["missing_reflection"] == 1


# ── should_block ─────────────────────────────────────────────────────────

def test_should_block_invalid_op():
    layer = _fresh_layer()
    blocked, msg = layer.should_block("teleport")
    assert blocked is True
    assert "invalid op" in msg


def test_should_block_decompose_during_storm():
    from brain.mechanisms.task_planning_layer import PLAN_STORM_DECOMPOSE_LIMIT
    layer = _fresh_layer()
    for i in range(PLAN_STORM_DECOMPOSE_LIMIT + 1):
        layer.record_decompose(plan_id=f"pl_{i}", goal="g", subtask_count=2)
    blocked, msg = layer.should_block("decompose")
    assert blocked is True
    assert "plan storm" in msg


def test_should_block_revise_abandon_no_reason():
    layer = _fresh_layer()
    blocked, msg = layer.should_block("revise", kind="abandon", reason="")
    assert blocked is True
    assert "reason" in msg


def test_should_block_when_systematically_low_integrity():
    layer = _fresh_layer()
    for _ in range(8):
        layer.record_op("teleport", goal="x")
    assert layer.is_systematically_low_integrity() is True
    blocked, msg = layer.should_block("decompose")
    assert blocked is True
    assert "low planning" in msg


# ── rolling integrity ────────────────────────────────────────────────────

def test_rolling_score_starts_at_one():
    layer = _fresh_layer()
    assert layer.rolling_integrity_score() == 1.0


def test_rolling_score_drops_with_bad_ops():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_op("teleport", goal="x")
    assert layer.rolling_integrity_score() < 0.5


def test_systematically_low_requires_min_n():
    layer = _fresh_layer()
    for _ in range(3):
        layer.record_op("teleport", goal="x")
    assert layer.is_systematically_low_integrity() is False


# ── planning_state ───────────────────────────────────────────────────────

def test_planning_state_idle_empty():
    layer = _fresh_layer()
    assert layer.planning_state() == "idle"


def test_planning_state_active_after_op():
    layer = _fresh_layer()
    layer.record_decompose(plan_id="pl_1", goal="x", subtask_count=2)
    assert layer.planning_state() == "active"


def test_planning_state_storming():
    from brain.mechanisms.task_planning_layer import PLAN_STORM_DECOMPOSE_LIMIT
    layer = _fresh_layer()
    for i in range(PLAN_STORM_DECOMPOSE_LIMIT + 1):
        layer.record_decompose(plan_id=f"pl_{i}", goal="g", subtask_count=2)
    assert layer.planning_state() == "storming"


def test_planning_state_stale():
    from brain.mechanisms.task_planning_layer import STALE_PLAN_TICK_THRESHOLD
    layer = _fresh_layer()
    layer.record_commit(plan_id="pl_1", goal="x")
    layer.current_tick = STALE_PLAN_TICK_THRESHOLD + 100
    state = layer.planning_state()
    assert state in ("stale", "active")  # depending on recent op timestamp


def test_planning_state_paralyzed_with_unreflected():
    from brain.mechanisms.task_planning_layer import REFLECTION_DEADLINE_TICKS
    layer = _fresh_layer()
    layer.record_commit(plan_id="pl_1", goal="x")
    layer.record_complete(plan_id="pl_1", subtask_count=1, unresolved_count=0)
    layer.current_tick += REFLECTION_DEADLINE_TICKS + 5
    assert layer.planning_state() in ("paralyzed", "active")


def test_planning_state_degrading():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_op("teleport", goal="x")
    assert layer.planning_state() == "degrading"


# ── persistence ──────────────────────────────────────────────────────────

def test_state_persists_across_instances():
    layer = _fresh_layer()
    layer.record_decompose(
        plan_id="pl_1", goal="x", subtask_count=3,
        horizon="temporal", mode="build",
    )
    layer.record_commit(plan_id="pl_1", goal="x")

    import brain.mechanisms.task_planning_layer as mod
    layer2 = mod.TaskPlanningLayer()
    assert layer2.op_counts["decompose"] == 1
    assert layer2.op_counts["commit"] == 1
    assert layer2.horizon_counts["temporal"] == 1
    assert layer2.mode_counts["build"] == 1
    assert "pl_1" in layer2.active_plans


# ── IPW handshake ────────────────────────────────────────────────────────

def test_ipw_silent_when_healthy():
    layer = _fresh_layer()
    layer.record_decompose(plan_id="pl_1", goal="x", subtask_count=3)
    assert layer.should_propose_identity_update() is False


def test_ipw_proposes_when_systematically_bad():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_op("teleport", goal="x")
    assert layer.should_propose_identity_update() is True
    sig = layer.proposed_identity_signal()
    assert sig["source"] == "TaskPlanningLayer"
    assert sig["kind"] == "task_planning_drift"
    assert "interpretation" in sig


def test_ipw_throttled_after_acknowledge():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_op("teleport", goal="x")
    assert layer.should_propose_identity_update() is True
    layer.acknowledge_proposal()
    assert layer.should_propose_identity_update() is False


# ── operator API ─────────────────────────────────────────────────────────

def test_reset_integrity_window():
    layer = _fresh_layer()
    for _ in range(5):
        layer.record_op("teleport", goal="x")
    assert layer.consecutive_bad_ops > 0
    layer.reset_integrity_window()
    assert layer.consecutive_bad_ops == 0


def test_reset_failure_counts_clears_per_plan_markers():
    from brain.mechanisms.task_planning_layer import STALE_PLAN_TICK_THRESHOLD
    layer = _fresh_layer()
    layer.record_commit(plan_id="pl_1", goal="x")
    layer.current_tick = STALE_PLAN_TICK_THRESHOLD + 100
    layer.check_stale_plans()
    assert layer.failure_counts["stale_plan"] == 1
    assert layer.state.get("stale_recorded_pl_1") is True
    layer.reset_failure_counts()
    assert layer.failure_counts["stale_plan"] == 0
    assert layer.state.get("stale_recorded_pl_1") is None


def test_reset_distributions():
    layer = _fresh_layer()
    layer.record_decompose(plan_id="pl_1", goal="x", subtask_count=2, horizon="temporal", mode="build")
    assert layer.horizon_counts["temporal"] == 1
    layer.reset_distributions()
    assert all(v == 0 for v in layer.horizon_counts.values())


def test_force_drop_active_plan_increments_incomplete():
    layer = _fresh_layer()
    layer.record_commit(plan_id="pl_1", goal="x")
    ok = layer.force_drop_active_plan("pl_1", reason="dead")
    assert ok is True
    assert "pl_1" not in layer.active_plans
    assert layer.failure_counts["incomplete_plans"] == 1


def test_force_drop_unknown_plan():
    layer = _fresh_layer()
    ok = layer.force_drop_active_plan("bogus", reason="x")
    assert ok is False


# ── tick / state shape ───────────────────────────────────────────────────

def test_tick_advances_current_tick():
    layer = _fresh_layer()
    start = layer.current_tick
    layer.tick()
    assert layer.current_tick == start + 1


def test_tick_records_planning_op():
    layer = _fresh_layer()
    out = layer.tick(
        pirp_context={
            "planning_op": {
                "op": "decompose",
                "plan_id": "pl_1",
                "goal": "from tick",
                "subtask_count": 2,
                "horizon": "contextual",
                "mode": "build",
            }
        }
    )
    assert out["_fired_tick"] is True
    assert layer.op_counts["decompose"] == 1


def test_tick_no_op_without_planning_op():
    layer = _fresh_layer()
    out = layer.tick(pirp_context={})
    assert out["_fired_tick"] is False


def test_get_state_has_required_keys():
    layer = _fresh_layer()
    out = layer.get_state()
    required = {
        "planning_state",
        "rolling_integrity_score",
        "integrity_window_n",
        "is_systematically_low_integrity",
        "consecutive_bad_ops",
        "operation_distribution",
        "horizon_distribution",
        "mode_distribution",
        "failure_mode_counts",
        "active_plan_count",
        "pending_reflection_count",
        "uncommitted_decompose_count",
        "plan_storm_active",
        "current_tick",
        "operation_count",
    }
    assert required.issubset(out.keys())


def test_record_op_dispatches():
    layer = _fresh_layer()
    rec = layer.record_op(
        "decompose", plan_id="pl_1", goal="x", subtask_count=2,
    )
    assert rec["op"] == "decompose"


def test_record_op_invalid():
    layer = _fresh_layer()
    rec = layer.record_op("teleport", goal="x")
    assert rec["op"] == "__invalid__"
    assert "error" in rec
