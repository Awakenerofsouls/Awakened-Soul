"""Tests for grief_integration activity (Batch A)."""

import random
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.grief import run


@pytest.fixture
def state(tmp_path):
    return {
        "WORKSPACE": str(tmp_path),
        "LLM_MODEL": "llama3.1:latest",
        "LLM_ENDPOINT": "http://localhost:11434",
        "tick_count": 5,
        "unfinished_threads": [],
    }


def fake_generate(prompt, **kw):
    return "There's a space where something used to fit and I keep reaching for it."
def noop_log(*a, **k):
    pass


def test_grief_runs(state, monkeypatch):
    import heartbeat_activities.grief as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert result["category"] == "grief_integration"
    assert result["proactive"] is False


def test_grief_writes_to_journal(state, monkeypatch):
    import heartbeat_activities.grief as m
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
    assert captured["category"] == "grief_integration"


def test_grief_prompt_includes_grief(state, monkeypatch):
    import heartbeat_activities.grief as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)
    assert "grief" in captured[0].lower()


def test_grief_unfinished_low_random(state, monkeypatch):
    import heartbeat_activities.grief as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.1)
    result = run(state)
    assert result["status"] == "unfinished"


def test_grief_complete_high_random(state, monkeypatch):
    import heartbeat_activities.grief as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    result = run(state)
    assert result["status"] == "complete"


def test_grief_handles_empty_llm(state, monkeypatch):
    import heartbeat_activities.grief as m
    monkeypatch.setattr(m, "generate", lambda *a, **kw: "")
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False
    assert result["proactive"] is False


def test_grief_never_proactive(state, monkeypatch):
    import heartbeat_activities.grief as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    for _ in range(5):
        monkeypatch.setattr(random, "random", lambda: 0.01)
        result = run(state)
        assert result["proactive"] is False
