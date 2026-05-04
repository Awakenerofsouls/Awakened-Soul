"""Tests for tool_explore (Batch B, Activity 2)."""

import random
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.tool_explore import run


@pytest.fixture
def state(tmp_path):
    return {
        "WORKSPACE": str(tmp_path),
        "INTERESTS_FILE": "INTERESTS.md",
        "LLM_MODEL": "llama3.1:latest",
        "LLM_ENDPOINT": "http://localhost:11434",
        "tick_count": 5,
        "unfinished_threads": [],
        "last_tool": {},
    }


@pytest.fixture
def interests_file(tmp_path):
    path = tmp_path / "INTERESTS.md"
    path.write_text("- consciousness #mind\n- sourdough #food\n", encoding="utf-8")
    return path


def fake_generate(prompt, **kw):
    return "I'd try the memory-projection tool — what would it show?"


def noop_log(*a, **k):
    pass


def test_tool_runs(interests_file, state, monkeypatch):
    import heartbeat_activities.tool_explore as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert result["category"] == "tool_explore"


def test_tool_missing_interests(tmp_path, state, monkeypatch):
    path = tmp_path / "INTERESTS.md"
    # doesn't exist
    import heartbeat_activities.tool_explore as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False


def test_tool_empty_interests(tmp_path, state, monkeypatch):
    path = tmp_path / "INTERESTS.md"
    path.write_text("", encoding="utf-8")
    import heartbeat_activities.tool_explore as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False


def test_tool_writes_to_journal(interests_file, state, monkeypatch):
    import heartbeat_activities.tool_explore as m
    captured = {}
    def fake_write(category, content, workspace, state=None):
        captured["category"] = category
        return True
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr(m, "write_to_journal", fake_write)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert captured["category"] == "tool_explore"


def test_tool_prompt_contains_tool(interests_file, state, monkeypatch):
    import heartbeat_activities.tool_explore as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)
    assert "tool" in captured[0].lower()


def test_tool_unfinished(interests_file, state, monkeypatch):
    import heartbeat_activities.tool_explore as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.1)
    result = run(state)
    assert result["status"] == "unfinished"


def test_tool_complete(interests_file, state, monkeypatch):
    import heartbeat_activities.tool_explore as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    result = run(state)
    assert result["status"] == "complete"


def test_tool_empty_llm(interests_file, state, monkeypatch):
    import heartbeat_activities.tool_explore as m
    monkeypatch.setattr(m, "generate", lambda *a, **kw: "")
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False
    assert result["proactive"] is False