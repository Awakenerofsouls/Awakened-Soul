"""Tests for deep_curiosity (Batch B, Activity 5)."""

import random
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.deep_curiosity import run


@pytest.fixture
def state(tmp_path):
    return {
        "WORKSPACE": str(tmp_path),
        "INTERESTS_FILE": "INTERESTS.md",
        "LLM_MODEL": "llama3.1:latest",
        "LLM_ENDPOINT": "http://localhost:11434",
        "tick_count": 5,
        "unfinished_threads": [],
        "last_deep_curiosity": {},
    }


@pytest.fixture
def interests_file(tmp_path):
    path = tmp_path / "INTERESTS.md"
    path.write_text("- consciousness #mind\n- sourdough #food\n", encoding="utf-8")
    return path


def fake_generate(prompt, **kw):
    return "Underneath the surface-level answer is a second question I keep avoiding."


def noop_log(*a, **k):
    pass


def test_deep_curiosity_runs(interests_file, state, monkeypatch):
    import heartbeat_activities.deep_curiosity as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert result["category"] == "deep_curiosity"


def test_deep_curiosity_missing_interests(tmp_path, state, monkeypatch):
    import heartbeat_activities.deep_curiosity as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False


def test_deep_curiosity_writes_to_journal(interests_file, state, monkeypatch):
    import heartbeat_activities.deep_curiosity as m
    captured = {}
    def fake_write(category, content, workspace, state=None):
        captured["category"] = category
        return True
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr(m, "write_to_journal", fake_write)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert captured["category"] == "deep_curiosity"


def test_deep_curiosity_prompt_contains_sitting_with(interests_file, state, monkeypatch):
    import heartbeat_activities.deep_curiosity as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)
    assert "sit" in captured[0].lower()


def test_deep_curiosity_unfinished(interests_file, state, monkeypatch):
    import heartbeat_activities.deep_curiosity as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.3)  # below 0.40
    result = run(state)
    assert result["status"] == "unfinished"


def test_deep_curiosity_complete(interests_file, state, monkeypatch):
    import heartbeat_activities.deep_curiosity as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    result = run(state)
    assert result["status"] == "complete"


def test_deep_curiosity_empty_llm(interests_file, state, monkeypatch):
    import heartbeat_activities.deep_curiosity as m
    monkeypatch.setattr(m, "generate", lambda *a, **kw: "")
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False
    assert result["proactive"] is False