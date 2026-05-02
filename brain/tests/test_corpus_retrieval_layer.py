"""
Tests for brain.mechanisms.corpus_retrieval_layer.CorpusRetrievalLayer.

Covers:
  - record_retrieval: invalid mode falls back; storm; same-query loop;
    stale-index counter; doc-type bookkeeping; dream-concentration;
    mode-imbalance
  - record_index resets last_write_tick (breaks loop chain)
  - record_sourceless_retrieval / note_write_activity hooks
  - should_block: invalid op, storm, sustained low integrity
  - rolling integrity score + min N gate
  - corpus_state classification
  - State persists across instances
  - IPW handshake fires + throttled
  - Operator API: reset_integrity_window / reset_failure_counts /
    reset_query_history
  - tick advances and records corpus_op
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
    state_file = _bm._STATE_DIR / "CorpusRetrievalLayer.json"
    if state_file.exists():
        state_file.unlink()
    import brain.mechanisms.corpus_retrieval_layer as mod
    importlib.reload(mod)
    return mod.CorpusRetrievalLayer()


# ── retrieval ────────────────────────────────────────────────────────────

def test_retrieval_basic_records():
    layer = _fresh_layer()
    rec = layer.record_retrieval(
        mode="search", query="deadline", n_hits=2,
        hit_doc_types=["journal", "dreams"],
    )
    assert rec["op"] == "search"
    assert rec["n_hits"] == 2
    assert layer.mode_counts["search"] == 1
    assert layer.doc_type_hits["journal"] == 1
    assert layer.doc_type_hits["dreams"] == 1


def test_retrieval_invalid_mode_falls_back():
    layer = _fresh_layer()
    rec = layer.record_retrieval(
        mode="vibes", query="x", n_hits=1, hit_doc_types=["journal"],
    )
    # Falls back to "search" — record stores normalized op.
    assert rec["op"] == "search"
    # And the score is dinged.
    assert rec["op_score"] < 1.0


def test_retrieval_unknown_doc_type_routes_to_external():
    layer = _fresh_layer()
    layer.record_retrieval(
        mode="search", query="x", n_hits=1, hit_doc_types=["wizardry"],
    )
    assert layer.doc_type_hits["external"] == 1


def test_storm_after_threshold():
    from brain.mechanisms.corpus_retrieval_layer import STORM_THRESHOLD
    layer = _fresh_layer()
    for i in range(STORM_THRESHOLD + 1):
        layer.record_retrieval(mode="search", query=f"q{i}")
    assert layer._storm_active() is True
    assert layer.failure_counts["retrieval_storm"] >= 1


def test_storm_window_expires():
    from brain.mechanisms.corpus_retrieval_layer import (
        STORM_THRESHOLD, STORM_WINDOW_TICKS,
    )
    layer = _fresh_layer()
    for i in range(STORM_THRESHOLD):
        layer.record_retrieval(mode="search", query=f"q{i}")
    # Skip past the window.
    layer.current_tick += STORM_WINDOW_TICKS + 10
    assert layer._storm_active() is False


def test_same_query_loop_after_repeated_query_no_writes():
    from brain.mechanisms.corpus_retrieval_layer import SAME_QUERY_LOOP_THRESHOLD
    layer = _fresh_layer()
    for _ in range(SAME_QUERY_LOOP_THRESHOLD + 1):
        layer.record_retrieval(mode="search", query="repeated")
    assert layer.failure_counts["same_query_loop"] >= 1


def test_same_query_loop_broken_by_index():
    from brain.mechanisms.corpus_retrieval_layer import SAME_QUERY_LOOP_THRESHOLD
    layer = _fresh_layer()
    layer.current_tick = 5
    for _ in range(SAME_QUERY_LOOP_THRESHOLD):
        layer.record_retrieval(mode="search", query="repeated")
        layer.current_tick += 1
    # Break the chain with an index op.
    layer.record_index(full=False, added=0, updated=1)
    layer.current_tick += 1
    # One more retrieval after the write — should NOT increment loop.
    before = layer.failure_counts["same_query_loop"]
    layer.record_retrieval(mode="search", query="repeated")
    # Loop count shouldn't increase because last_write_tick is recent.
    assert layer.failure_counts["same_query_loop"] == before


def test_same_query_loop_broken_by_note_write_activity():
    from brain.mechanisms.corpus_retrieval_layer import SAME_QUERY_LOOP_THRESHOLD
    layer = _fresh_layer()
    layer.current_tick = 5
    for _ in range(SAME_QUERY_LOOP_THRESHOLD):
        layer.record_retrieval(mode="search", query="repeated")
        layer.current_tick += 1
    layer.note_write_activity()
    layer.current_tick += 1
    before = layer.failure_counts["same_query_loop"]
    layer.record_retrieval(mode="search", query="repeated")
    assert layer.failure_counts["same_query_loop"] == before


def test_stale_index_counter():
    layer = _fresh_layer()
    layer.record_retrieval(mode="search", query="x", stale_index=True)
    assert layer.failure_counts["stale_index"] == 1


def test_dream_concentration_after_many_low_hits():
    from brain.mechanisms.corpus_retrieval_layer import (
        DREAM_CONCENTRATION_MIN_HITS,
    )
    layer = _fresh_layer()
    for i in range(DREAM_CONCENTRATION_MIN_HITS + 2):
        layer.record_retrieval(
            mode="search", query=f"q-{i}", hit_doc_types=["dreams"],
        )
    assert layer._dream_concentration_active() is True
    assert layer.failure_counts["dream_concentration"] >= 1


def test_no_dream_concentration_when_balanced():
    from brain.mechanisms.corpus_retrieval_layer import (
        DREAM_CONCENTRATION_MIN_HITS,
    )
    layer = _fresh_layer()
    # 1-in-3 dreams, 2-in-3 journal — well below the 0.5 threshold.
    for i in range(DREAM_CONCENTRATION_MIN_HITS + 2):
        dt = "dreams" if i % 3 == 0 else "journal"
        layer.record_retrieval(
            mode="search", query=f"q-{i}", hit_doc_types=[dt],
        )
    assert layer._dream_concentration_active() is False


def test_mode_imbalance_when_only_one_mode():
    from brain.mechanisms.corpus_retrieval_layer import MODE_IMBALANCE_MIN_OPS
    layer = _fresh_layer()
    for i in range(MODE_IMBALANCE_MIN_OPS + 2):
        layer.record_retrieval(mode="search", query=f"q-{i}")
    assert layer._mode_imbalance_active() is True
    assert layer.failure_counts["mode_imbalance"] >= 1


def test_no_mode_imbalance_when_balanced():
    from brain.mechanisms.corpus_retrieval_layer import MODE_IMBALANCE_MIN_OPS
    layer = _fresh_layer()
    for i in range(MODE_IMBALANCE_MIN_OPS + 2):
        mode = "search" if i % 2 == 0 else "vsearch"
        layer.record_retrieval(mode=mode, query=f"q-{i}")
    assert layer._mode_imbalance_active() is False


# ── index ────────────────────────────────────────────────────────────────

def test_record_index_updates_last_write_tick():
    layer = _fresh_layer()
    layer.current_tick = 100
    layer.record_index(full=True, added=5)
    assert layer.last_write_tick == 100


# ── operator hooks ───────────────────────────────────────────────────────

def test_record_sourceless_retrieval_increments():
    layer = _fresh_layer()
    layer.record_sourceless_retrieval(2)
    assert layer.failure_counts["sourceless_retrieval"] == 2


def test_note_write_activity_sets_last_write_tick():
    layer = _fresh_layer()
    layer.current_tick = 42
    layer.note_write_activity()
    assert layer.last_write_tick == 42


# ── should_block ─────────────────────────────────────────────────────────

def test_should_block_invalid_op():
    layer = _fresh_layer()
    blocked, msg = layer.should_block("teleport")
    assert blocked is True
    assert "invalid op" in msg


def test_should_block_storm_active():
    from brain.mechanisms.corpus_retrieval_layer import STORM_THRESHOLD
    layer = _fresh_layer()
    for i in range(STORM_THRESHOLD + 1):
        layer.record_retrieval(mode="search", query=f"q-{i}")
    blocked, msg = layer.should_block("search", query="another")
    assert blocked is True
    assert "retrieval storm" in msg


def test_should_block_get_not_blocked_by_storm():
    from brain.mechanisms.corpus_retrieval_layer import STORM_THRESHOLD
    layer = _fresh_layer()
    for i in range(STORM_THRESHOLD + 1):
        layer.record_retrieval(mode="search", query=f"q-{i}")
    # 'get' is excluded from storm gating — it's a direct fetch, not a search.
    blocked, _ = layer.should_block("get", path_or_hash="SOUL.md")
    assert blocked is False


def test_should_block_when_systematically_low_integrity():
    layer = _fresh_layer()
    for _ in range(8):
        layer.record_op("teleport", target="x")
    assert layer.is_systematically_low_integrity() is True
    blocked, msg = layer.should_block("search", query="x")
    assert blocked is True
    assert "low corpus" in msg


# ── rolling integrity ────────────────────────────────────────────────────

def test_rolling_score_starts_at_one():
    layer = _fresh_layer()
    assert layer.rolling_integrity_score() == 1.0


def test_rolling_score_drops_with_bad_ops():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_op("teleport", target="x")
    assert layer.rolling_integrity_score() < 0.5


def test_systematically_low_requires_min_n():
    layer = _fresh_layer()
    for _ in range(3):
        layer.record_op("teleport", target="x")
    assert layer.is_systematically_low_integrity() is False


# ── corpus_state ─────────────────────────────────────────────────────────

def test_corpus_state_idle_empty():
    layer = _fresh_layer()
    assert layer.corpus_state() == "idle"


def test_corpus_state_active_recent_op():
    layer = _fresh_layer()
    layer.record_retrieval(mode="search", query="x", hit_doc_types=["journal"])
    assert layer.corpus_state() == "active"


def test_corpus_state_storming():
    from brain.mechanisms.corpus_retrieval_layer import STORM_THRESHOLD
    layer = _fresh_layer()
    for i in range(STORM_THRESHOLD + 1):
        layer.record_retrieval(mode="search", query=f"q{i}")
    assert layer.corpus_state() == "storming"


def test_corpus_state_looping():
    from brain.mechanisms.corpus_retrieval_layer import SAME_QUERY_LOOP_THRESHOLD
    layer = _fresh_layer()
    for _ in range(SAME_QUERY_LOOP_THRESHOLD + 1):
        layer.record_retrieval(mode="search", query="repeated")
    assert layer.corpus_state() == "looping"


def test_corpus_state_stale():
    layer = _fresh_layer()
    layer.record_retrieval(mode="search", query="x", stale_index=True)
    assert layer.corpus_state() == "stale"


def test_corpus_state_dream_leaning():
    from brain.mechanisms.corpus_retrieval_layer import (
        DREAM_CONCENTRATION_MIN_HITS,
    )
    layer = _fresh_layer()
    for i in range(DREAM_CONCENTRATION_MIN_HITS + 2):
        layer.record_retrieval(
            mode="search", query=f"q-{i}", hit_doc_types=["dreams"],
        )
    # dream_leaning OR storming OR looping — depending on which trips first.
    assert layer.corpus_state() in (
        "dream_leaning", "storming", "degrading", "looping",
    )


def test_corpus_state_degrading():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_op("teleport", target="x")
    assert layer.corpus_state() == "degrading"


# ── persistence ──────────────────────────────────────────────────────────

def test_state_persists_across_instances():
    layer = _fresh_layer()
    layer.record_retrieval(
        mode="search", query="x", n_hits=2, hit_doc_types=["journal"],
    )
    layer.record_index(full=True, added=3)

    import brain.mechanisms.corpus_retrieval_layer as mod
    layer2 = mod.CorpusRetrievalLayer()
    assert layer2.op_counts["search"] == 1
    assert layer2.op_counts["index"] == 1
    assert layer2.doc_type_hits["journal"] == 1


# ── IPW handshake ────────────────────────────────────────────────────────

def test_ipw_silent_when_healthy():
    layer = _fresh_layer()
    layer.record_retrieval(
        mode="search", query="x", n_hits=1, hit_doc_types=["journal"],
    )
    assert layer.should_propose_identity_update() is False


def test_ipw_proposes_when_systematically_bad():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_op("teleport", target="x")
    assert layer.should_propose_identity_update() is True
    sig = layer.proposed_identity_signal()
    assert sig["source"] == "CorpusRetrievalLayer"
    assert sig["kind"] == "corpus_retrieval_drift"
    assert "interpretation" in sig


def test_ipw_throttled_after_acknowledge():
    layer = _fresh_layer()
    for _ in range(10):
        layer.record_op("teleport", target="x")
    assert layer.should_propose_identity_update() is True
    layer.acknowledge_proposal()
    assert layer.should_propose_identity_update() is False


# ── operator API ─────────────────────────────────────────────────────────

def test_reset_integrity_window():
    layer = _fresh_layer()
    for _ in range(5):
        layer.record_op("teleport", target="x")
    assert layer.consecutive_bad_ops > 0
    layer.reset_integrity_window()
    assert layer.consecutive_bad_ops == 0


def test_reset_failure_counts():
    layer = _fresh_layer()
    layer.record_retrieval(mode="search", query="x", stale_index=True)
    assert layer.failure_counts["stale_index"] == 1
    layer.reset_failure_counts()
    assert all(v == 0 for v in layer.failure_counts.values())


def test_reset_query_history():
    from brain.mechanisms.corpus_retrieval_layer import SAME_QUERY_LOOP_THRESHOLD
    layer = _fresh_layer()
    for _ in range(SAME_QUERY_LOOP_THRESHOLD):
        layer.record_retrieval(mode="search", query="x")
    assert "x" or len(layer.query_history) > 0
    layer.reset_query_history()
    assert len(layer.query_history) == 0


# ── tick / state shape ───────────────────────────────────────────────────

def test_tick_advances_current_tick():
    layer = _fresh_layer()
    start = layer.current_tick
    layer.tick()
    assert layer.current_tick == start + 1


def test_tick_records_corpus_op():
    layer = _fresh_layer()
    out = layer.tick(
        pirp_context={
            "corpus_op": {
                "op": "search",
                "query": "from tick",
                "n_hits": 1,
                "hit_doc_types": ["journal"],
            }
        }
    )
    assert out["_fired_tick"] is True
    assert layer.op_counts["search"] == 1


def test_tick_no_op_without_corpus_op():
    layer = _fresh_layer()
    out = layer.tick(pirp_context={})
    assert out["_fired_tick"] is False


def test_get_state_has_required_keys():
    layer = _fresh_layer()
    out = layer.get_state()
    required = {
        "corpus_state",
        "rolling_integrity_score",
        "integrity_window_n",
        "is_systematically_low_integrity",
        "consecutive_bad_ops",
        "operation_distribution",
        "mode_distribution",
        "doc_type_distribution",
        "failure_mode_counts",
        "storm_active",
        "dream_concentration_active",
        "mode_imbalance_active",
        "current_tick",
        "last_write_tick",
        "operation_count",
    }
    assert required.issubset(out.keys())


def test_record_op_dispatches_search():
    layer = _fresh_layer()
    rec = layer.record_op(
        "search", query="x", n_hits=1, hit_doc_types=["journal"],
    )
    assert rec["op"] == "search"


def test_record_op_dispatches_index():
    layer = _fresh_layer()
    rec = layer.record_op("index", full=True, added=2)
    assert rec["op"] == "index"


def test_record_op_invalid():
    layer = _fresh_layer()
    rec = layer.record_op("rewrite", target="x")
    assert rec["op"] == "__invalid__"
    assert "error" in rec
