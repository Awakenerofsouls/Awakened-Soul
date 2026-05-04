"""Tests for memory_capture (Batch C, Activity 1)."""

import random
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.memory_capture import run


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
    return "Tick 5 capture: working on the memory system, something shifted."


def noop_log(*a, **k):
    pass


def test_memory_capture_runs(memory_dir, state, monkeypatch):
    import heartbeat_activities.memory_capture as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert result["category"] == "memory_capture"


def test_memory_capture_writes_to_journal(memory_dir, state, monkeypatch):
    import heartbeat_activities.memory_capture as m
    captured = {}
    def fake_write(category, content, workspace, state=None):
        captured["category"] = category
        return True
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr(m, "write_to_journal", fake_write)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert captured["category"] == "memory_capture"


def test_memory_capture_empty_memory_file(memory_dir, state, monkeypatch):
    """Empty memory file → runs fine (capture prompts without context)."""
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (memory_dir / f"{today}.md").write_text("", encoding="utf-8")
    import heartbeat_activities.memory_capture as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True


def test_memory_capture_missing_memory_file(memory_dir, state, monkeypatch):
    """No memory file → runs fine (captures without context)."""
    import heartbeat_activities.memory_capture as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True


def test_memory_capture_includes_memory_context(memory_dir, state, monkeypatch):
    """Prompt includes recent memory content."""
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (memory_dir / f"{today}.md").write_text(
        "Previous entry: something about the project.", encoding="utf-8"
    )
    import heartbeat_activities.memory_capture as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)
    assert "Previous entry" in captured[0]


def test_memory_capture_continuation(memory_dir, state, monkeypatch):
    state["continuation_of"] = "memory_capture"
    state["prior_memory_capture_content"] = "Earlier capture."
    import heartbeat_activities.memory_capture as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "More."
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    run(state)
    assert "Earlier capture" in captured[0]


def test_memory_capture_unfinished(memory_dir, state, monkeypatch):
    import heartbeat_activities.memory_capture as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.05)
    result = run(state)
    assert result["status"] == "unfinished"


def test_memory_capture_complete(memory_dir, state, monkeypatch):
    import heartbeat_activities.memory_capture as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    result = run(state)
    assert result["status"] == "complete"


def test_memory_capture_empty_llm(memory_dir, state, monkeypatch):
    import heartbeat_activities.memory_capture as m
    monkeypatch.setattr(m, "generate", lambda *a, **kw: "")
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False
    assert result["proactive"] is False