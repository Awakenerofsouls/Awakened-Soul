"""Tests for memory_protocol_review (Batch C, Activity 3)."""

import random
import pytest
import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.memory_protocol import run, _build_memory_index


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
    return "Memory hygiene looks good. The protocol is holding."


def noop_log(*a, **k):
    pass


def test_protocol_runs(memory_dir, state, monkeypatch):
    import heartbeat_activities.memory_protocol as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert result["category"] == "memory_protocol"


def test_protocol_writes_to_journal(memory_dir, state, monkeypatch):
    import heartbeat_activities.memory_protocol as m
    captured = {}
    def fake_write(category, content, workspace, state=None):
        captured["category"] = category
        return True
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr(m, "write_to_journal", fake_write)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert captured["category"] == "memory_protocol"


def test_protocol_builds_index_not_contents(memory_dir, state, monkeypatch):
    """Prompt should contain file names and sizes, NOT content from files."""
    (memory_dir / "2026-04-22.md").write_text(
        "This is a very long entry that should not appear in the prompt.",
        encoding="utf-8"
    )
    (memory_dir / "2026-04-23.md").write_text(
        "Another long entry that should not be visible either.",
        encoding="utf-8"
    )

    import heartbeat_activities.memory_protocol as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)

    assert len(captured) == 1
    prompt_text = captured[0]
    # Should have file names
    assert "2026-04" in prompt_text
    # Should NOT have file contents
    assert "very long entry" not in prompt_text
    assert "Another long entry" not in prompt_text


def test_protocol_empty_memory_dir(memory_dir, state, monkeypatch):
    """Empty memory dir → runs fine, prompt has no index."""
    import heartbeat_activities.memory_protocol as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)

    # Prompt should not contain "Memory index:" heading
    assert "Memory index:" not in captured[0]


def test_build_memory_index_returns_names_and_sizes(tmp_path):
    d = tmp_path / "memory"
    d.mkdir()
    (d / "2026-04-22.md").write_text("content here", encoding="utf-8")

    index = _build_memory_index(tmp_path)  # pass workspace, not memory_dir
    assert "2026-04-22.md" in index
    assert "KB" in index


def test_build_memory_index_missing_dir(tmp_path):
    result = _build_memory_index(tmp_path / "NOT_A_DIR")
    assert result == ""


def test_protocol_unfinished(memory_dir, state, monkeypatch):
    import heartbeat_activities.memory_protocol as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.1)
    result = run(state)
    assert result["status"] == "unfinished"


def test_protocol_complete(memory_dir, state, monkeypatch):
    import heartbeat_activities.memory_protocol as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    result = run(state)
    assert result["status"] == "complete"


def test_protocol_empty_llm(memory_dir, state, monkeypatch):
    import heartbeat_activities.memory_protocol as m
    monkeypatch.setattr(m, "generate", lambda *a, **kw: "")
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False
    assert result["proactive"] is False