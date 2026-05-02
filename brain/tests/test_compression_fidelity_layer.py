"""
Tests for brain.mechanisms.compression_fidelity_layer.CompressionFidelityLayer.

Covers:
  - compute_fidelity_signals: hedge counts, contradiction markers, hallucinations
  - Confidence laundering detection (source has hedging, summary doesn't)
  - Structural smoothing detection (source has contradictions, summary doesn't)
  - Hallucination heuristic (specifics in summary not in source)
  - Compression ratio for each intent
  - record_compression updates intent_state
  - Untagged compression recorded but not credited
  - should_block: invalid intent, ratio under floor, sustained low fidelity
  - Rolling fidelity window + score
  - is_systematically_low_fidelity needs min N
  - compression_state classification
  - State persists across instances
  - IPW handshake throttle
  - reset_fidelity_window
  - get_state shape
  - tick with compression dict
"""
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
    state_file = _bm._STATE_DIR / "CompressionFidelityLayer.json"
    if state_file.exists():
        state_file.unlink()
    import brain.mechanisms.compression_fidelity_layer as mod
    importlib.reload(mod)
    return mod.CompressionFidelityLayer()


def test_compute_fidelity_signals_basic():
    from brain.mechanisms.compression_fidelity_layer import compute_fidelity_signals
    src = (
        "Some studies suggest the effect might be present, although "
        "evidence is unclear. However, recent papers indicate that the "
        "result may be smaller than initially reported."
    )
    summary = (
        "Some studies suggest the effect might be present, although "
        "evidence is unclear; recent papers indicate the result may be smaller."
    )
    sig = compute_fidelity_signals(src, summary, "extract")
    assert sig["source_hedge_count"] >= 4
    assert sig["summary_hedge_count"] >= 3
    assert sig["hedge_preservation_rate"] >= 0.5
    assert sig["confidence_laundering"] is False
    assert sig["fidelity_score"] > 0.7


def test_confidence_laundering_detected():
    """Source had hedging, summary stripped it."""
    from brain.mechanisms.compression_fidelity_layer import compute_fidelity_signals
    src = (
        "Some studies suggest the effect might be present. The data appears "
        "to indicate this. Evidence suggests we should perhaps consider it."
    )
    summary = "The effect is present. The data shows this. Evidence confirms it."
    sig = compute_fidelity_signals(src, summary, "extract")
    assert sig["confidence_laundering"] is True
    assert sig["hedge_preservation_rate"] == 0.0
    assert sig["fidelity_score"] < 0.7


def test_structural_smoothing_detected():
    """Source has contradictions, summary smoothed them."""
    from brain.mechanisms.compression_fidelity_layer import compute_fidelity_signals
    src = (
        "Group A shows growth. However, group B shows decline. "
        "Although the totals balance, the dynamics differ. "
        "On the other hand, segment C is flat."
    )
    summary = "Group A grows and group B grows. Segment C also grows."
    sig = compute_fidelity_signals(src, summary, "extract")
    assert sig["source_contradiction_markers"] >= 3
    assert sig["summary_contradiction_markers"] == 0
    assert sig["contradiction_preserved"] is False
    assert sig["structural_smoothing"] is True


def test_hallucination_heuristic_detects_added_specifics():
    """Specifics in summary that aren't in source are flagged."""
    from brain.mechanisms.compression_fidelity_layer import compute_fidelity_signals
    src = "The team reviewed the proposal and decided to delay. The outcome surprised some."
    summary = (
        "The Boston team reviewed the proposal in March 2024 and decided "
        "to delay. The 47% outcome surprised some."
    )
    sig = compute_fidelity_signals(src, summary, "extract")
    # "Boston" and "March", and "47" are not in the source
    assert sig["potential_hallucination_count"] >= 2
    assert any("Boston" in h for h in sig["potential_hallucinations"])


def test_hallucination_heuristic_clean_when_specifics_match():
    from brain.mechanisms.compression_fidelity_layer import compute_fidelity_signals
    src = "The Boston team met on March 15, 2024 and reviewed 47 proposals."
    summary = "Boston team met March 2024; reviewed 47 proposals."
    sig = compute_fidelity_signals(src, summary, "extract")
    assert sig["potential_hallucination_count"] == 0


def test_compression_ratio_floor_per_intent():
    from brain.mechanisms.compression_fidelity_layer import compute_fidelity_signals
    src = "x" * 1000
    summary = "x" * 30  # 3% ratio
    sig_brief = compute_fidelity_signals(src, summary, "brief")
    sig_extract = compute_fidelity_signals(src, summary, "extract")
    # brief allows aggressive compression, extract doesn't
    assert sig_brief["fidelity_score"] >= sig_extract["fidelity_score"]


def test_record_compression_updates_intent_state():
    layer = _fresh_layer()
    src = "The team reviewed the proposal."
    summary = "Team reviewed proposal."
    rec = layer.record_compression(intent="brief", source=src, summary=summary)
    assert rec["intent"] == "brief"
    assert layer.intent_state["brief"]["total"] == 1


def test_untagged_compression_recorded_not_credited():
    layer = _fresh_layer()
    layer.record_compression(intent="banana", source="x", summary="y")
    for k in ("brief", "extract", "digest", "synthesize"):
        assert layer.intent_state[k]["total"] == 0
    assert layer.compressions[-1]["intent"] == "__untagged__"


def test_should_block_invalid_intent():
    layer = _fresh_layer()
    block, reason = layer.should_block(intent="banana")
    assert block is True
    assert "invalid intent" in reason


def test_should_block_extract_under_floor():
    layer = _fresh_layer()
    block, reason = layer.should_block(intent="extract", source_len=1000, target_len=30)
    assert block is True
    assert "below" in reason.lower() and "floor" in reason


def test_should_block_clean_passes():
    layer = _fresh_layer()
    block, reason = layer.should_block(intent="brief", source_len=1000, target_len=100)
    assert block is False


def test_low_fidelity_compression_increments_consecutive():
    layer = _fresh_layer()
    src = (
        "Some studies suggest the effect might be present. However, evidence "
        "appears unclear. Although some researchers maybe disagree."
    )
    summary = "The effect is present. Evidence shows it."  # strips hedging + contradiction
    rec = layer.record_compression(intent="extract", source=src, summary=summary)
    assert rec["signals"]["fidelity_score"] < 0.5, (
        f"score={rec['signals']['fidelity_score']}, signals={rec['signals']}"
    )
    assert layer.consecutive_low_fidelity == 1


def test_consecutive_low_fidelity_resets_on_good_compression():
    layer = _fresh_layer()
    # Bad fixture: confidence laundering AND structural smoothing
    bad_src = (
        "Some studies suggest the effect might be present, although "
        "evidence is unclear. However, recent papers maybe indicate it's smaller."
    )
    bad_summary = "The effect is present. Recent papers show it's smaller."
    layer.record_compression(intent="extract", source=bad_src, summary=bad_summary)
    assert layer.consecutive_low_fidelity == 1

    good_src = "The team reviewed the proposal carefully and at length."
    good_summary = "The team reviewed the proposal carefully."
    layer.record_compression(intent="brief", source=good_src, summary=good_summary)
    assert layer.consecutive_low_fidelity == 0


def test_systematic_low_fidelity_needs_min_n():
    """Below FIDELITY_MIN_N, can't claim systematic low fidelity."""
    from brain.mechanisms import compression_fidelity_layer as mod
    layer = _fresh_layer()
    bad_src = (
        "Some studies suggest the effect might be present, although "
        "evidence is unclear. However, recent papers maybe indicate it's smaller."
    )
    bad_summary = "The effect is present. Recent papers show it's smaller."
    # Record fewer than FIDELITY_MIN_N
    for _ in range(mod.FIDELITY_MIN_N - 1):
        layer.record_compression(intent="extract", source=bad_src, summary=bad_summary)
    assert layer.is_systematically_low_fidelity() is False


def test_systematic_low_fidelity_detected_with_enough_data():
    from brain.mechanisms import compression_fidelity_layer as mod
    layer = _fresh_layer()
    bad_src = (
        "Some studies suggest the effect might be present, although "
        "evidence is unclear. However, recent papers maybe indicate it's smaller."
    )
    bad_summary = "The effect is present. Recent papers show it's smaller."
    for _ in range(mod.FIDELITY_MIN_N + 2):
        layer.record_compression(intent="extract", source=bad_src, summary=bad_summary)
    assert layer.is_systematically_low_fidelity() is True


def test_should_block_on_systematic_low_fidelity():
    from brain.mechanisms import compression_fidelity_layer as mod
    layer = _fresh_layer()
    bad_src = (
        "Some studies suggest the effect might be present, although "
        "evidence is unclear. However, recent papers maybe indicate it's smaller."
    )
    bad_summary = "The effect is present. Recent papers show it's smaller."
    for _ in range(mod.FIDELITY_MIN_N + 2):
        layer.record_compression(intent="extract", source=bad_src, summary=bad_summary)
    block, reason = layer.should_block(intent="brief", source_len=1000, target_len=100)
    assert block is True
    assert "low fidelity" in reason


def test_compression_state_priority():
    from brain.mechanisms import compression_fidelity_layer as mod

    # Idle initially.
    layer = _fresh_layer()
    assert layer.compression_state() == "idle"

    # Active state on a recent good compression.
    layer.record_compression(
        intent="brief",
        source="The team reviewed the proposal carefully.",
        summary="Team reviewed proposal.",
    )
    assert layer.compression_state() in ("active", "faithful")

    # Drive to systematic low fidelity → degrading.
    layer = _fresh_layer()
    bad_src = (
        "Some studies suggest the effect might be present, although "
        "evidence is unclear. However, recent papers maybe indicate it's smaller."
    )
    bad_summary = "The effect is present. Recent papers show it's smaller."
    for _ in range(mod.FIDELITY_MIN_N + 2):
        layer.record_compression(intent="extract", source=bad_src, summary=bad_summary)
    assert layer.compression_state() == "degrading"


def test_state_persists_across_instances():
    layer1 = _fresh_layer()
    layer1.record_compression(
        intent="brief",
        source="The team reviewed the proposal.",
        summary="Team reviewed proposal.",
    )
    from brain.mechanisms.compression_fidelity_layer import CompressionFidelityLayer
    layer2 = CompressionFidelityLayer()
    assert layer2.intent_state["brief"]["total"] == 1
    assert len(layer2.compressions) == 1
    assert len(layer2.fidelity_window) == 1


def test_ipw_handshake_throttled():
    from brain.mechanisms import compression_fidelity_layer as mod
    layer = _fresh_layer()
    bad_src = (
        "Some studies suggest the effect might be present, although "
        "evidence is unclear. However, recent papers maybe indicate it's smaller."
    )
    bad_summary = "The effect is present. Recent papers show it's smaller."
    for _ in range(mod.FIDELITY_MIN_N + 2):
        layer.record_compression(intent="extract", source=bad_src, summary=bad_summary)
    assert layer.is_systematically_low_fidelity() is True
    assert layer.should_propose_identity_update() is True

    layer.acknowledge_proposal()
    assert layer.should_propose_identity_update() is False

    # IPW_REPORT_EVERY more low-fidelity compressions to re-fire.
    for _ in range(mod.IPW_REPORT_EVERY):
        layer.record_compression(intent="extract", source=bad_src, summary=bad_summary)
    assert layer.should_propose_identity_update() is True


def test_proposed_signal_shape():
    from brain.mechanisms import compression_fidelity_layer as mod
    layer = _fresh_layer()
    bad_src = "Some studies suggest the effect might be present. However maybe."
    bad_summary = "The effect is present."
    for _ in range(mod.FIDELITY_MIN_N + 2):
        layer.record_compression(intent="extract", source=bad_src, summary=bad_summary)
    sig = layer.proposed_identity_signal()
    for key in ("source", "kind", "rolling_fidelity_score", "consecutive_low_fidelity",
                "intent_low_fidelity_rates", "total_hallucinations", "interpretation"):
        assert key in sig
    assert sig["source"] == "CompressionFidelityLayer"
    assert sig["kind"] == "systematic_compression_drift"


def test_reset_fidelity_window():
    layer = _fresh_layer()
    layer.record_compression(intent="brief", source="x", summary="y")
    assert len(layer.fidelity_window) == 1
    layer.reset_fidelity_window()
    assert len(layer.fidelity_window) == 0
    assert layer.consecutive_low_fidelity == 0


def test_get_state_shape():
    layer = _fresh_layer()
    state = layer.get_state()
    expected = {
        "compression_state", "rolling_fidelity_score", "fidelity_window_n",
        "is_systematically_low_fidelity", "consecutive_low_fidelity",
        "intent_distribution", "compression_count", "_fired_tick",
    }
    assert expected.issubset(set(state.keys())), f"missing: {expected - set(state.keys())}"


def test_tick_with_compression_records_it():
    layer = _fresh_layer()
    out = layer.tick({
        "compression": {
            "intent": "brief",
            "source": "The team reviewed the proposal carefully.",
            "summary": "Team reviewed proposal.",
            "caveats": ["minor detail dropped"],
        }
    })
    assert out["_fired_tick"] is True
    assert out["compression_count"] == 1


def test_hallucination_count_accumulates_per_intent():
    layer = _fresh_layer()
    src = "The team met."
    summary = "The Boston team met in March 2024 with 47 attendees."  # 3 hallucinated specifics
    layer.record_compression(intent="extract", source=src, summary=summary)
    assert layer.intent_state["extract"]["hallucinations"] >= 2


def test_hedge_preservation_when_source_has_no_hedging():
    """If source has no hedging, preservation rate is trivially 1.0 and
    confidence_laundering doesn't fire."""
    from brain.mechanisms.compression_fidelity_layer import compute_fidelity_signals
    src = "The team met. The proposal was reviewed. The decision was made."
    summary = "Team met, reviewed proposal, decided."
    sig = compute_fidelity_signals(src, summary, "brief")
    assert sig["source_hedge_count"] == 0
    assert sig["hedge_preservation_rate"] == 1.0
    assert sig["confidence_laundering"] is False
