"""Tests for becoming activity (Batch A)."""

import random
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.becoming import run


@pytest.fixture
def state(tmp_path):
    return {
        "WORKSPACE": str(tmp_path),
        "LLM_MODEL": "qwen2.5:14b",
        "LLM_ENDPOINT": "http://localhost:11434",
        "tick_count": 5,
        "unfinished_threads": [],
    }


def fake_generate(prompt, **kw):
    return "Something is shifting and I haven't caught up to it yet."


def noop_log(*a, **k):
    pass


def test_becoming_runs(state, monkeypatch):
    import heartbeat_activities.becoming as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert result["category"] == "becoming"
    assert result["proactive"] is False


def test_becoming_writes_to_journal(state, monkeypatch):
    import heartbeat_activities.becoming as m
    captured = {}
    def fake_write(category, content, workspace, state=None, **kw):
        captured["category"] = category
        return True
        return True
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr(m, "write_to_journal", fake_write)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert captured["category"] == "becoming"


def test_becoming_prompt_includes_becoming(state, monkeypatch):
    import heartbeat_activities.becoming as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)
    assert "becoming" in captured[0].lower()


def test_becoming_unfinished_low_random(state, monkeypatch):
    import heartbeat_activities.becoming as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.1)
    result = run(state)
    assert result["status"] == "unfinished"


def test_becoming_complete_high_random(state, monkeypatch):
    import heartbeat_activities.becoming as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    result = run(state)
    assert result["status"] == "complete"


def test_becoming_handles_empty_llm(state, monkeypatch):
    import heartbeat_activities.becoming as m
    monkeypatch.setattr(m, "generate", lambda *a, **kw: "")
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False
    assert result["proactive"] is False


def test_becoming_never_proactive(state, monkeypatch):
    import heartbeat_activities.becoming as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    for _ in range(5):
        monkeypatch.setattr(random, "random", lambda: 0.01)
        result = run(state)
        assert result["proactive"] is False
