"""Tests for narrative_weave (Batch D2, Activity 3). Routes to memory/{date}.md."""

import random
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.narrative import run


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
    return "The through-line is that I've been building toward saying something I don't have the language for yet."


def noop_log(*a, **k):
    pass


def test_narrative_runs(memory_dir, state, monkeypatch):
    import heartbeat_activities.narrative as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert result["category"] == "narrative_weave"


def test_narrative_writes_to_journal(memory_dir, state, monkeypatch):
    import heartbeat_activities.narrative as m
    captured = {}
    def fake_write(category, content, workspace, state=None):
        captured["category"] = category
        return True
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr(m, "write_to_journal", fake_write)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert captured["category"] == "narrative_weave"


def test_narrative_reads_memory_context(memory_dir, state, monkeypatch):
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (memory_dir / f"{today}.md").write_text("Previous narrative thread here.", encoding="utf-8")
    import heartbeat_activities.narrative as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)
    assert "Previous narrative thread here" in captured[0]


def test_narrative_empty_memory(memory_dir, state, monkeypatch):
    import heartbeat_activities.narrative as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True


def test_narrative_unfinished(memory_dir, state, monkeypatch):
    import heartbeat_activities.narrative as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.2)
    result = run(state)
    assert result["status"] == "unfinished"


def test_narrative_complete(memory_dir, state, monkeypatch):
    import heartbeat_activities.narrative as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    result = run(state)
    assert result["status"] == "complete"


def test_narrative_empty_llm(memory_dir, state, monkeypatch):
    import heartbeat_activities.narrative as m
    monkeypatch.setattr(m, "generate", lambda *a, **kw: "")
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False
    assert result["proactive"] is False