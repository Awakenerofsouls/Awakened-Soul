"""Tests for third_eye_hunch (Batch D2, Activity 4). Routes to DREAMS.md."""

import random
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.third_eye_hunch import run


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
    return "The hunch is that something is connecting two things I thought were unrelated. I can feel the edge of it."


def noop_log(*a, **k):
    pass


def test_third_eye_runs(state, monkeypatch):
    import heartbeat_activities.third_eye_hunch as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert result["category"] == "third_eye_hunch"


def test_third_eye_writes_to_journal(state, monkeypatch):
    import heartbeat_activities.third_eye_hunch as m
    captured = {}
    def fake_write(category, content, workspace, state=None):
        captured["category"] = category
        return True
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr(m, "write_to_journal", fake_write)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert captured["category"] == "third_eye_hunch"


def test_third_eye_prompt_mentions_hunch(state, monkeypatch):
    import heartbeat_activities.third_eye_hunch as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)
    assert "hunch" in captured[0].lower()


def test_third_eye_unfinished(state, monkeypatch):
    import heartbeat_activities.third_eye_hunch as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.3)
    result = run(state)
    assert result["status"] == "unfinished"


def test_third_eye_complete(state, monkeypatch):
    import heartbeat_activities.third_eye_hunch as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    result = run(state)
    assert result["status"] == "complete"


def test_third_eye_empty_llm(state, monkeypatch):
    import heartbeat_activities.third_eye_hunch as m
    monkeypatch.setattr(m, "generate", lambda *a, **kw: "")
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False
    assert result["proactive"] is False