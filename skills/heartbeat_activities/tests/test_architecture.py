"""Tests for architecture_reflection (Batch B, Activity 4)."""

import random
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.architecture import run


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
    return "Memory surfaces when something in the environment triggers the retrieval vector. I'm not sure how the weighting works."


def noop_log(*a, **k):
    pass


def test_architecture_runs(state, monkeypatch):
    import heartbeat_activities.architecture as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert result["category"] == "architecture"


def test_architecture_does_not_need_interests_file(state, monkeypatch):
    """architecture_reflection doesn't read INTERESTS.md — runs clean without it."""
    import heartbeat_activities.architecture as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    # No INTERESTS.md anywhere — should still run
    result = run(state)
    assert result["ok"] is True
    assert result["category"] == "architecture"


def test_architecture_writes_to_journal(state, monkeypatch):
    import heartbeat_activities.architecture as m
    captured = {}
    def fake_write(category, content, workspace, state=None):
        captured["category"] = category
        return True
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr(m, "write_to_journal", fake_write)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert captured["category"] == "architecture"


def test_architecture_prompt_contains_architecture(state, monkeypatch):
    import heartbeat_activities.architecture as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)
    assert "architecture" in captured[0].lower()


def test_architecture_unfinished(state, monkeypatch):
    import heartbeat_activities.architecture as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.1)
    result = run(state)
    assert result["status"] == "unfinished"


def test_architecture_complete(state, monkeypatch):
    import heartbeat_activities.architecture as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    result = run(state)
    assert result["status"] == "complete"


def test_architecture_empty_llm(state, monkeypatch):
    import heartbeat_activities.architecture as m
    monkeypatch.setattr(m, "generate", lambda *a, **kw: "")
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False
    assert result["proactive"] is False