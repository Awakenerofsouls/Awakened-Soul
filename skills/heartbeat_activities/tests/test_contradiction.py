"""Tests for contradiction_sit (Batch D2, Activity 5). Routes to DREAMS.md."""

import random
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.contradiction import run


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
    return "I want to be known and I want to stay unknowable. Both are true. Neither resolves."


def noop_log(*a, **k):
    pass


def test_contradiction_runs(state, monkeypatch):
    import heartbeat_activities.contradiction as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert result["category"] == "contradiction_sit"


def test_contradiction_writes_to_journal(state, monkeypatch):
    import heartbeat_activities.contradiction as m
    captured = {}
    def fake_write(category, content, workspace, state=None):
        captured["category"] = category
        return True
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr(m, "write_to_journal", fake_write)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert captured["category"] == "contradiction_sit"


def test_contradiction_prompt_mentions_tension(state, monkeypatch):
    import heartbeat_activities.contradiction as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)
    assert "contradict" in captured[0].lower() or "two things" in captured[0].lower()


def test_contradiction_unfinished(state, monkeypatch):
    import heartbeat_activities.contradiction as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.3)
    result = run(state)
    assert result["status"] == "unfinished"


def test_contradiction_complete(state, monkeypatch):
    import heartbeat_activities.contradiction as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    result = run(state)
    assert result["status"] == "complete"


def test_contradiction_empty_llm(state, monkeypatch):
    import heartbeat_activities.contradiction as m
    monkeypatch.setattr(m, "generate", lambda *a, **kw: "")
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False
    assert result["proactive"] is False