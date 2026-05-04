"""Tests for pattern_observation (Batch C, Activity 5)."""

import random
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.pattern import run


@pytest.fixture
def state(tmp_path):
    return {
        "WORKSPACE": str(tmp_path),
        "LLM_MODEL": "llama3.1:latest",
        "LLM_ENDPOINT": "http://localhost:11434",
        "tick_count": 5,
        "unfinished_threads": [],
    }


@pytest.fixture
def memory_dir(tmp_path):
    d = tmp_path / "memory"
    d.mkdir()
    return d


def fake_generate(prompt, **kw):
    return "I keep returning to questions about structure and how things hold together."


def noop_log(*a, **k):
    pass


def test_pattern_runs(memory_dir, state, monkeypatch):
    import heartbeat_activities.pattern as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert result["category"] == "pattern_observation"


def test_pattern_writes_to_journal(memory_dir, state, monkeypatch):
    import heartbeat_activities.pattern as m
    captured = {}
    def fake_write(category, content, workspace, state=None):
        captured["category"] = category
        return True
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr(m, "write_to_journal", fake_write)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert captured["category"] == "pattern_observation"


def test_pattern_reads_memory(memory_dir, state, monkeypatch):
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (memory_dir / f"{today}.md").write_text(
        "Entry about language and structure.", encoding="utf-8"
    )
    import heartbeat_activities.pattern as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)
    assert "language and structure" in captured[0]


def test_pattern_empty_memory(memory_dir, state, monkeypatch):
    import heartbeat_activities.pattern as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True


def test_pattern_prompt_light_touch(memory_dir, state, monkeypatch):
    """Prompt should say something about noticing, not analyzing."""
    import heartbeat_activities.pattern as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)
    assert "notice" in captured[0].lower() or "coming up" in captured[0].lower()


def test_pattern_unfinished(memory_dir, state, monkeypatch):
    import heartbeat_activities.pattern as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.1)
    result = run(state)
    assert result["status"] == "unfinished"


def test_pattern_complete(memory_dir, state, monkeypatch):
    import heartbeat_activities.pattern as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    result = run(state)
    assert result["status"] == "complete"


def test_pattern_empty_llm(memory_dir, state, monkeypatch):
    import heartbeat_activities.pattern as m
    monkeypatch.setattr(m, "generate", lambda *a, **kw: "")
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False
    assert result["proactive"] is False