"""
Tests for dreams activity (Activity Port 4).

Covers: happy path, missing memory file, journal routing to DREAMS.md,
       continuation handling, deliberate unfinished (50%), empty LLM.
"""

import random
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.dreams import (
    run,
    UNFINISHED_PROBABILITY,
)


# ── Fixtures ────────────────────────────────────────────────────────────────

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
def today_memory(tmp_path):
    """Today's memory file with ~3KB of content."""
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = tmp_path / "memory" / f"{today}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write enough content that the last 2KB matters
    path.write_text("x" * 3000, encoding="utf-8")
    return path


@pytest.fixture
def empty_memory(tmp_path):
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = tmp_path / "memory" / f"{today}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    return path


@pytest.fixture
def no_memory(tmp_path):
    """No memory directory at all."""
    return tmp_path / "memory"


# ── Helpers ────────────────────────────────────────────────────────────────

def fake_generate(prompt, **kw):
    return "A corridor that smells like rain. The door keeps moving."


def noop_log(*a, **k):
    pass


# ── Activity Run ───────────────────────────────────────────────────────────

def test_dreams_runs_with_memory_file(today_memory, state, monkeypatch):
    import heartbeat_activities.dreams as dreams_module
    monkeypatch.setattr(dreams_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)

    assert result["ok"] is True
    assert result["category"] == "dreams"
    assert result["status"] in ("complete", "unfinished")
    assert len(result["content"]) > 0


def test_dreams_handles_missing_memory_directory(no_memory, state, monkeypatch):
    """No memory file at all — should not crash."""
    import heartbeat_activities.dreams as dreams_module
    monkeypatch.setattr(dreams_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)

    assert result["ok"] is True
    assert result["category"] == "dreams"


def test_dreams_handles_empty_memory_file(empty_memory, state, monkeypatch):
    """Empty memory file — prompt should still generate."""
    import heartbeat_activities.dreams as dreams_module
    monkeypatch.setattr(dreams_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)

    assert result["ok"] is True
    assert result["category"] == "dreams"


def test_dreams_handles_empty_llm_response(today_memory, state, monkeypatch):
    def fake_empty(*a, **kw):
        return ""

    import heartbeat_activities.dreams as dreams_module
    monkeypatch.setattr(dreams_module, "generate", fake_empty)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)
    assert result["ok"] is False
    assert result["status"] == "complete"


def test_dreams_writes_to_DREAMS_journal(today_memory, state, monkeypatch):
    import heartbeat_activities.dreams as dreams_module
    import heartbeat_activities.journal as journal_module

    captured = {}
    def fake_write(category, content, workspace, state=None, **kw):
        captured["category"] = category
        captured["content"] = content
        return True

    monkeypatch.setattr(dreams_module, "generate", fake_generate)
    monkeypatch.setattr(dreams_module, "write_to_journal", fake_write)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)

    assert result["ok"] is True
    assert captured["category"] == "dreams"


def test_dreams_uses_continuation_prompt(today_memory, state, monkeypatch):
    state["continuation_of"] = "dreams"
    state["prior_dream_content"] = "A corridor that smells like rain."

    captured = []
    def fake_generate_capture(prompt, **kw):
        captured.append(prompt)
        return "The door is still moving."

    import heartbeat_activities.dreams as dreams_module
    monkeypatch.setattr(dreams_module, "generate", fake_generate_capture)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)

    assert len(captured) == 1
    assert "Earlier" in captured[0]


def test_dreams_sometimes_returns_unfinished(today_memory, state, monkeypatch):
    import heartbeat_activities.dreams as dreams_module
    monkeypatch.setattr(dreams_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.1)  # below 0.5 → unfinished

    result = run(state)
    assert result["status"] == "unfinished"


def test_dreams_returns_complete_when_random_high(today_memory, state, monkeypatch):
    import heartbeat_activities.dreams as dreams_module
    monkeypatch.setattr(dreams_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)  # above 0.5 → complete

    result = run(state)
    assert result["status"] == "complete"
