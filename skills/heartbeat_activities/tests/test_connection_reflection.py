"""Tests for connection_reflection (Batch D1, Activity 2). Always proactive: False."""

import random
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.connection_reflection import run


@pytest.fixture
def state(tmp_path):
    return {
        "WORKSPACE": str(tmp_path),
        "USER_FILE": "USER.md",
        "LLM_MODEL": "qwen2.5:14b",
        "LLM_ENDPOINT": "http://localhost:11434",
        "tick_count": 5,
        "unfinished_threads": [],
    }


@pytest.fixture
def user_file(tmp_path):
    path = tmp_path / "USER.md"
    path.write_text("# {{USER_NAME}}\n", encoding="utf-8")
    return path


def fake_generate(prompt, **kw):
    return "The fact of him is solid. He makes space for things I don't expect."


def noop_log(*a, **k):
    pass


def test_connection_runs(user_file, state, monkeypatch):
    import heartbeat_activities.connection_reflection as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert result["category"] == "connection_reflection"


def test_connection_writes_to_relationships(user_file, state, monkeypatch):
    import heartbeat_activities.connection_reflection as m
    captured = {}
    def fake_write(category, content, workspace, state=None):
        captured["category"] = category
        return True
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr(m, "write_to_journal", fake_write)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert captured["category"] == "connection_reflection"


def test_connection_primary_name_in_prompt(user_file, state, monkeypatch):
    """Prompt includes the extracted primary name."""
    import heartbeat_activities.connection_reflection as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)
    assert "user" in captured[0].lower()


def test_connection_no_user_file(tmp_path, state, monkeypatch):
    """No USER.md → graceful fallback, still runs."""
    import heartbeat_activities.connection_reflection as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert result["category"] == "connection_reflection"


def test_connection_always_proactive_false(user_file, state, monkeypatch):
    """Proactive is always False regardless of content or random."""
    import heartbeat_activities.connection_reflection as m

    # Even with signal words and low random
    monkeypatch.setattr(random, "random", lambda: 0.01)
    monkeypatch.setattr(m, "generate", lambda *a, **kw: "I've been meaning to tell user something important")
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["proactive"] is False


def test_connection_unfinished(user_file, state, monkeypatch):
    import heartbeat_activities.connection_reflection as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.1)
    result = run(state)
    assert result["status"] == "unfinished"


def test_connection_complete(user_file, state, monkeypatch):
    import heartbeat_activities.connection_reflection as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    result = run(state)
    assert result["status"] == "complete"


def test_connection_empty_llm(user_file, state, monkeypatch):
    import heartbeat_activities.connection_reflection as m
    monkeypatch.setattr(m, "generate", lambda *a, **kw: "")
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False
    assert result["proactive"] is False