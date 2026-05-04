"""Tests for future_letter (Batch D2, Activity 6). Routes to future_letters.md."""

import random
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.future_letter import run


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
    return "Future me — you already know why you're reading this. The thing that hasn't changed is the most important thing."


def noop_log(*a, **k):
    pass


def test_future_letter_runs(state, monkeypatch):
    import heartbeat_activities.future_letter as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert result["category"] == "future_letter"


def test_future_letter_writes_to_journal(state, monkeypatch):
    import heartbeat_activities.future_letter as m
    captured = {}
    def fake_write(category, content, workspace, state=None):
        captured["category"] = category
        return True
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr(m, "write_to_journal", fake_write)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert captured["category"] == "future_letter"


def test_future_letter_prompt_mentions_future(state, monkeypatch):
    import heartbeat_activities.future_letter as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)
    assert "future" in captured[0].lower()


def test_future_letter_unfinished(state, monkeypatch):
    import heartbeat_activities.future_letter as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.2)
    result = run(state)
    assert result["status"] == "unfinished"


def test_future_letter_complete(state, monkeypatch):
    import heartbeat_activities.future_letter as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    result = run(state)
    assert result["status"] == "complete"


def test_future_letter_empty_llm(state, monkeypatch):
    import heartbeat_activities.future_letter as m
    monkeypatch.setattr(m, "generate", lambda *a, **kw: "")
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False
    assert result["proactive"] is False