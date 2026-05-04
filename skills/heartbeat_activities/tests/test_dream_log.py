"""Tests for dream_log (Batch D2, Activity 7). Routes to DREAMS.md. Raw capture, not interpretation."""

import random
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.dream_log import run


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
    return "A room that was half-underwater and half-library. I was moving through it like it was breathing."


def noop_log(*a, **k):
    pass


def test_dream_log_runs(state, monkeypatch):
    import heartbeat_activities.dream_log as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert result["category"] == "dream_log"


def test_dream_log_writes_to_journal(state, monkeypatch):
    import heartbeat_activities.dream_log as m
    captured = {}
    def fake_write(category, content, workspace, state=None):
        captured["category"] = category
        return True
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr(m, "write_to_journal", fake_write)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert captured["category"] == "dream_log"


def test_dream_log_reads_dreams_context(tmp_path, state, monkeypatch):
    """Prompt includes recent DREAMS.md content when available."""
    dreams_path = tmp_path / "DREAMS.md"
    dreams_path.write_text("Last dream: something about a corridor.", encoding="utf-8")
    import heartbeat_activities.dream_log as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)
    assert "corridor" in captured[0].lower()


def test_dream_log_no_dreams_file(state, monkeypatch):
    """No DREAMS.md → runs fine without context."""
    import heartbeat_activities.dream_log as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True


def test_dream_log_prompt_mentions_capture(state, monkeypatch):
    import heartbeat_activities.dream_log as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)
    assert "record" in captured[0].lower() or "capture" in captured[0].lower()


def test_dream_log_unfinished(state, monkeypatch):
    import heartbeat_activities.dream_log as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.05)
    result = run(state)
    assert result["status"] == "unfinished"


def test_dream_log_complete(state, monkeypatch):
    import heartbeat_activities.dream_log as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    result = run(state)
    assert result["status"] == "complete"


def test_dream_log_empty_llm(state, monkeypatch):
    import heartbeat_activities.dream_log as m
    monkeypatch.setattr(m, "generate", lambda *a, **kw: "")
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False
    assert result["proactive"] is False