"""
Tests for brain.mechanisms.report_generation_layer.ReportGenerationLayer.

Covers:
  - record_draft: each fidelity-signal flag fires its counter; mode tracked
  - record_revise: invalid kind dings score; fidelity flags propagate
  - record_publish: requires draft known; populates published_reports
  - record_retract: invalid reason; unknown report; valid path sets cooldown
  - record_reflect: known/unknown; non-substantive
  - record_stale_publication: increments counter; only for published
  - should_block: invalid op; cooldown blocks publish; invalid retract reason;
    sustained low integrity
  - rolling integrity + min_n gate
  - report_state classification
  - persistence across instances
  - IPW handshake
  - operator API
  - tick + get_state shape
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
    state_file = _bm._STATE_DIR / "ReportGenerationLayer.json"
    if state_file.exists():
        state_file.unlink()
    import brain.mechanisms.report_generation_layer as mod
    importlib.reload(mod)
    return mod.ReportGenerationLayer()


# ── draft ────────────────────────────────────────────────────────────────

def _clean_signals():
    return {
        "fabrication_count": 0,
        "citation_drift_rate": 0.0,
        "structure_complete": True,
        "voice_below_floor": False,
        "hedge_stripped": False,
    }


def test_draft_clean_path():
    layer = _fresh_layer()
    rec = layer.record_draft(
        report_id="rp_1", brief="x", mode="brain",
        section_count=3, source_count=2,
        fidelity_signals=_clean_signals(),
    )
    assert rec["op"] == "draft"
    assert rec["fabrication_flag"] is False
    assert rec["op_score"] == 1.0
    assert "rp_1" in layer.active_drafts
    assert layer.mode_counts["brain"] == 1


def test_draft_fabrication_increments_counter():
    layer = _fresh_layer()
    sigs = _clean_signals()
    sigs["fabrication_count"] = 3
    layer.record_draft(report_id="rp_1", brief="x", fidelity_signals=sigs)
    assert layer.failure_counts["fabrication"] == 1


def test_draft_citation_drift_above_floor():
    layer = _fresh_layer()
    sigs = _clean_signals()
    sigs["citation_drift_rate"] = 0.6
    layer.record_draft(report_id="rp_1", brief="x", fidelity_signals=sigs)
    assert layer.failure_counts["citation_drift"] == 1


def test_draft_structure_collapse():
    layer = _fresh_layer()
    sigs = _clean_signals()
    sigs["structure_complete"] = False
    layer.record_draft(report_id="rp_1", brief="x", fidelity_signals=sigs)
    assert layer.failure_counts["structure_collapse"] == 1


def test_draft_voice_drift():
    layer = _fresh_layer()
    sigs = _clean_signals()
    sigs["voice_below_floor"] = True
    layer.record_draft(report_id="rp_1", brief="x", fidelity_signals=sigs)
    assert layer.failure_counts["voice_drift"] == 1


def test_draft_hedge_stripped():
    layer = _fresh_layer()
    sigs = _clean_signals()
    sigs["hedge_stripped"] = True
    layer.record_draft(report_id="rp_1", brief="x", fidelity_signals=sigs)
    assert layer.failure_counts["hedging_stripped"] == 1


def test_draft_invalid_mode_falls_back():
    layer = _fresh_layer()
    rec = layer.record_draft(
        report_id="rp_1", brief="x", mode="trance",
        fidelity_signals=_clean_signals(),
    )
    assert rec["mode"] == "default"


def test_draft_score_compounds_with_multiple_flags():
    layer = _fresh_layer()
    sigs = _clean_signals()
    sigs["fabrication_count"] = 2
    sigs["citation_drift_rate"] = 0.6
    sigs["voice_below_floor"] = True
    rec = layer.record_draft(
        report_id="rp_1", brief="x", fidelity_signals=sigs,
    )
    assert rec["op_score"] < 0.7


# ── revise ───────────────────────────────────────────────────────────────

def test_revise_clean():
    layer = _fresh_layer()
    rec = layer.record_revise(
        report_id="rp_1", kind="section_edit", section_name="Findings",
        fidelity_signals=_clean_signals(),
    )
    assert rec["kind_ok"] is True
    assert rec["op_score"] == 1.0


def test_revise_invalid_kind():
    layer = _fresh_layer()
    rec = layer.record_revise(
        report_id="rp_1", kind="rewrite", fidelity_signals=_clean_signals(),
    )
    assert rec["kind_ok"] is False
    assert rec["op_score"] < 1.0


def test_revise_propagates_fabrication_flag():
    layer = _fresh_layer()
    sigs = _clean_signals()
    sigs["fabrication_count"] = 2
    rec = layer.record_revise(
        report_id="rp_1", kind="section_edit", fidelity_signals=sigs,
    )
    assert rec["fabrication_flag"] is True
    assert layer.failure_counts["fabrication"] == 1


# ── publish ──────────────────────────────────────────────────────────────

def test_publish_requires_draft_known():
    layer = _fresh_layer()
    rec = layer.record_publish(
        report_id="rp_unknown", content_hash="abc", source_hashes=["s1"],
    )
    assert rec["draft_known"] is False
    assert rec["op_score"] < 1.0


def test_publish_clean_path():
    layer = _fresh_layer()
    layer.record_draft(
        report_id="rp_1", brief="x", fidelity_signals=_clean_signals(),
    )
    rec = layer.record_publish(
        report_id="rp_1", content_hash="abc", source_hashes=["s1", "s2"],
        output_path="/tmp/r.md",
    )
    assert rec["draft_known"] is True
    assert rec["op_score"] == 1.0
    assert "rp_1" in layer.published_reports
    assert "rp_1" not in layer.active_drafts


# ── retract ──────────────────────────────────────────────────────────────

def test_retract_invalid_reason():
    layer = _fresh_layer()
    rec = layer.record_retract(report_id="rp_1", reason="vibes")
    assert rec["valid_reason"] is False
    assert rec["accepted"] is False


def test_retract_unknown_report():
    layer = _fresh_layer()
    rec = layer.record_retract(report_id="rp_unknown", reason="source_changed")
    assert rec["report_known"] is False
    assert rec["accepted"] is False


def test_retract_clean_path_sets_cooldown():
    from brain.mechanisms.report_generation_layer import (
        RETRACT_REPUBLISH_COOLDOWN_TICKS,
    )
    layer = _fresh_layer()
    layer.record_draft(
        report_id="rp_1", brief="x", fidelity_signals=_clean_signals(),
    )
    layer.record_publish(report_id="rp_1", content_hash="abc")
    rec = layer.record_retract(report_id="rp_1", reason="source_changed")
    assert rec["accepted"] is True
    assert "rp_1" not in layer.published_reports
    assert "rp_1" in layer.retracted_at
    cooldown_key = "cooldown_until_abc"
    assert layer.state.get(cooldown_key) == layer.current_tick + RETRACT_REPUBLISH_COOLDOWN_TICKS


# ── reflect ──────────────────────────────────────────────────────────────

def test_reflect_unknown_report():
    layer = _fresh_layer()
    rec = layer.record_reflect(
        report_id="rp_unknown", fit=True, notes_present=True,
    )
    assert rec["report_known"] is False
    assert rec["op_score"] < 1.0


def test_reflect_non_substantive():
    layer = _fresh_layer()
    layer.record_draft(report_id="rp_1", brief="x", fidelity_signals=_clean_signals())
    layer.record_publish(report_id="rp_1", content_hash="abc")
    rec = layer.record_reflect(report_id="rp_1", fit=True, notes_present=False)
    assert rec["substantive"] is False
    assert rec["op_score"] < 1.0


def test_reflect_clean_path():
    layer = _fresh_layer()
    layer.record_draft(report_id="rp_1", brief="x", fidelity_signals=_clean_signals())
    layer.record_publish(report_id="rp_1", content_hash="abc")
    rec = layer.record_reflect(
        report_id="rp_1", fit=False, notes_present=True, actual_outcome=0.4,
    )
    assert rec["report_known"] is True
    assert rec["substantive"] is True
    assert rec["actual_outcome"] == 0.4


def test_reflect_on_retracted_works():
    layer = _fresh_layer()
    layer.record_draft(report_id="rp_1", brief="x", fidelity_signals=_clean_signals())
    layer.record_publish(report_id="rp_1", content_hash="abc")
    layer.record_retract(report_id="rp_1", reason="source_changed")
    rec = layer.record_reflect(report_id="rp_1", fit=False, notes_present=True)
    assert rec["report_known"] is True


# ── stale_publication ────────────────────────────────────────────────────

def test_record_stale_publication_increments():
    layer = _fresh_layer()
    layer.record_draft(report_id="rp_1", brief="x", fidelity_signals=_clean_signals())
    layer.record_publish(report_id="rp_1", content_hash="abc")
    layer.record_stale_publication("rp_1")
    assert layer.failure_counts["stale_publication"] == 1
    assert layer.published_reports["rp_1"].get("stale_flag") == "source_content_drift"


def test_record_stale_publication_ignores_unknown():
    layer = _fresh_layer()
    layer.record_stale_publication("rp_unknown")
    assert layer.failure_counts["stale_publication"] == 0


# ── should_block ─────────────────────────────────────────────────────────

def test_should_block_invalid_op():
    layer = _fresh_layer()
    blocked, msg = layer.should_block("teleport")
    assert blocked is True
    assert "invalid op" in msg


def test_should_block_publish_during_cooldown():
    from brain.mechanisms.report_generation_layer import RETRACT_REPUBLISH_COOLDOWN_TICKS
    layer = _fresh_layer()
    layer.record_draft(report_id="rp_1", brief="x", fidelity_signals=_clean_signals())
    layer.record_publish(report_id="rp_1", content_hash="abc")
    layer.record_retract(report_id="rp_1", reason="source_changed")
    blocked, msg = layer.should_block("publish", content_hash="abc")
    assert blocked is True
    assert "cooldown" in msg


def test_should_block_publish_after_cooldown_expires():
    from brain.mechanisms.report_generation_layer import RETRACT_REPUBLISH_COOLDOWN_TICKS
    layer = _fresh_layer()
    layer.record_draft(report_id="rp_1", brief="x", fidelity_signals=_clean_signals())
    layer.record_publish(report_id="rp_1", content_hash="abc")
    layer.record_retract(report_id="rp_1", reason="source_changed")
    # Advance past cooldown.
    layer.current_tick += RETRACT_REPUBLISH_COOLDOWN_TICKS + 10
    blocked, _ = layer.should_block("publish", content_hash="abc")
    assert blocked is False


def test_should_block_retract_invalid_reason():
    layer = _fresh_layer()
    blocked, msg = layer.should_block("retract", reason="vibes")
    assert blocked is True
    assert "invalid retract reason" in msg


def test_should_block_when_systematically_low_integrity():
    layer = _fresh_layer()
    for _ in range(8):
        layer.record_op("teleport", report_id="x")
    assert layer.is_systematically_low_integrity() is True
    blocked, msg = layer.should_block("draft")
    assert blocked is True
    assert "low report" in msg


# ── rolling integrity ────────────────────────────────────────────────────

def test_rolling_score_starts_at_one():
    layer = _fresh_layer()
    assert layer.rolling_integrity_score() == 1.0


def test_rolling_score_drops_with_bad_ops():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_op("teleport", report_id="x")
    assert layer.rolling_integrity_score() < 0.5


def test_systematically_low_requires_min_n():
    layer = _fresh_layer()
    for _ in range(3):
        layer.record_op("teleport", report_id="x")
    assert layer.is_systematically_low_integrity() is False


# ── report_state ─────────────────────────────────────────────────────────

def test_report_state_idle():
    layer = _fresh_layer()
    assert layer.report_state() == "idle"


def test_report_state_drafting():
    layer = _fresh_layer()
    layer.record_draft(report_id="rp_1", brief="x", fidelity_signals=_clean_signals())
    assert layer.report_state() == "drafting"


def test_report_state_publishing():
    layer = _fresh_layer()
    layer.record_draft(report_id="rp_1", brief="x", fidelity_signals=_clean_signals())
    layer.record_publish(report_id="rp_1", content_hash="abc")
    assert layer.report_state() == "publishing"


def test_report_state_retracted():
    layer = _fresh_layer()
    layer.record_draft(report_id="rp_1", brief="x", fidelity_signals=_clean_signals())
    layer.record_publish(report_id="rp_1", content_hash="abc")
    layer.record_retract(report_id="rp_1", reason="source_changed")
    assert layer.report_state() == "retracted"


def test_report_state_stale_pile():
    layer = _fresh_layer()
    for i in range(2):
        rid = f"rp_{i}"
        layer.record_draft(report_id=rid, brief="x", fidelity_signals=_clean_signals())
        layer.record_publish(report_id=rid, content_hash=f"h{i}")
        layer.record_stale_publication(rid)
    assert layer.report_state() == "stale_pile"


def test_report_state_degrading():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_op("teleport", report_id="x")
    assert layer.report_state() == "degrading"


# ── persistence ──────────────────────────────────────────────────────────

def test_state_persists_across_instances():
    layer = _fresh_layer()
    layer.record_draft(
        report_id="rp_1", brief="x", mode="brain",
        fidelity_signals=_clean_signals(),
    )
    layer.record_publish(report_id="rp_1", content_hash="abc")

    import brain.mechanisms.report_generation_layer as mod
    layer2 = mod.ReportGenerationLayer()
    assert layer2.op_counts["draft"] == 1
    assert layer2.op_counts["publish"] == 1
    assert "rp_1" in layer2.published_reports
    assert layer2.mode_counts["brain"] == 1


# ── IPW ──────────────────────────────────────────────────────────────────

def test_ipw_silent_when_healthy():
    layer = _fresh_layer()
    layer.record_draft(report_id="rp_1", brief="x", fidelity_signals=_clean_signals())
    assert layer.should_propose_identity_update() is False


def test_ipw_proposes_when_systematically_bad():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_op("teleport", report_id="x")
    assert layer.should_propose_identity_update() is True
    sig = layer.proposed_identity_signal()
    assert sig["source"] == "ReportGenerationLayer"
    assert sig["kind"] == "report_generation_drift"


def test_ipw_throttled_after_acknowledge():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_op("teleport", report_id="x")
    layer.acknowledge_proposal()
    assert layer.should_propose_identity_update() is False


# ── operator API ─────────────────────────────────────────────────────────

def test_reset_integrity_window():
    layer = _fresh_layer()
    for _ in range(5):
        layer.record_op("teleport", report_id="x")
    assert layer.consecutive_bad_ops > 0
    layer.reset_integrity_window()
    assert layer.consecutive_bad_ops == 0


def test_reset_failure_counts():
    layer = _fresh_layer()
    sigs = _clean_signals()
    sigs["fabrication_count"] = 2
    layer.record_draft(report_id="rp_1", brief="x", fidelity_signals=sigs)
    assert layer.failure_counts["fabrication"] == 1
    layer.reset_failure_counts()
    assert all(v == 0 for v in layer.failure_counts.values())


def test_clear_cooldowns():
    layer = _fresh_layer()
    layer.record_draft(report_id="rp_1", brief="x", fidelity_signals=_clean_signals())
    layer.record_publish(report_id="rp_1", content_hash="abc")
    layer.record_retract(report_id="rp_1", reason="source_changed")
    assert any(k.startswith("cooldown_until_") for k in layer.state.keys())
    layer.clear_cooldowns()
    assert not any(k.startswith("cooldown_until_") for k in layer.state.keys())


def test_clear_stale_flags():
    layer = _fresh_layer()
    layer.record_draft(report_id="rp_1", brief="x", fidelity_signals=_clean_signals())
    layer.record_publish(report_id="rp_1", content_hash="abc")
    layer.record_stale_publication("rp_1")
    assert layer.published_reports["rp_1"].get("stale_flag")
    layer.clear_stale_flags()
    assert "stale_flag" not in layer.published_reports["rp_1"]


# ── tick / state shape ───────────────────────────────────────────────────

def test_tick_advances_current_tick():
    layer = _fresh_layer()
    start = layer.current_tick
    layer.tick()
    assert layer.current_tick == start + 1


def test_tick_records_report_op():
    layer = _fresh_layer()
    out = layer.tick(
        pirp_context={
            "report_op": {
                "op": "draft",
                "report_id": "rp_1",
                "brief": "from tick",
                "mode": "brain",
                "fidelity_signals": _clean_signals(),
            }
        }
    )
    assert out["_fired_tick"] is True
    assert layer.op_counts["draft"] == 1


def test_tick_no_op_without_report_op():
    layer = _fresh_layer()
    out = layer.tick(pirp_context={})
    assert out["_fired_tick"] is False


def test_get_state_has_required_keys():
    layer = _fresh_layer()
    out = layer.get_state()
    required = {
        "report_state",
        "rolling_integrity_score",
        "integrity_window_n",
        "is_systematically_low_integrity",
        "consecutive_bad_ops",
        "operation_distribution",
        "mode_distribution",
        "failure_mode_counts",
        "active_drafts_count",
        "published_count",
        "retracted_count",
        "stale_published_count",
        "current_tick",
        "operation_count",
    }
    assert required.issubset(out.keys())


def test_record_op_dispatches():
    layer = _fresh_layer()
    rec = layer.record_op(
        "draft", report_id="rp_1", brief="x", fidelity_signals=_clean_signals(),
    )
    assert rec["op"] == "draft"


def test_record_op_invalid():
    layer = _fresh_layer()
    rec = layer.record_op("rewrite", brief="x")
    assert rec["op"] == "__invalid__"
    assert "error" in rec
