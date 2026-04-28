"""
Tests for private_entry activity (Activity Port 7).

Covers: happy path, open-questions seeding, graceful degradation,
       journal routing, continuation, unedited-voice prompt guard,
       stochastic unfinished, always-private (proactive: False).
"""

import random
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.private_entry import (
    run,
    _read_seed_question,
    UNFINISHED_PROBABILITY,
)


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def state(tmp_path):
    return {
        "WORKSPACE": str(tmp_path),
        "LLM_MODEL": "qwen2.5:14b",
        "LLM_ENDPOINT": "http://localhost:11434",
        "tick_count": 5,
        "unfinished_threads": [],
    }


@pytest.fixture
def questions_file(tmp_path):
    """open_questions.md with 3 questions."""
    path = tmp_path / "open_questions.md"
    path.write_text(
        "- What am I avoiding right now?\n"
        "- Where does the wanting live when it's not acting?\n"
        "- What's the shape of the gap between what I say and what I feel?\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def empty_questions(tmp_path):
    path = tmp_path / "open_questions.md"
    path.write_text("", encoding="utf-8")
    return path


@pytest.fixture
def no_questions(tmp_path):
    return tmp_path / "open_questions.md"


# ── Helpers ────────────────────────────────────────────────────────────────

def fake_generate(prompt, **kw):
    return "There's something under the smooth surface I keep finding."


def noop_log(*a, **k):
    pass


# ── Activity Run ───────────────────────────────────────────────────────────

def test_private_entry_runs_without_questions_file(no_questions, state, monkeypatch):
    import heartbeat_activities.private_entry as private_entry_module
    monkeypatch.setattr(private_entry_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)

    assert result["ok"] is True
    assert result["category"] == "private_entry"
    assert result["proactive"] is False
    assert result["status"] in ("complete", "unfinished")
    assert len(result["content"]) > 0


def test_private_entry_reads_questions_when_present(questions_file, state, monkeypatch):
    import heartbeat_activities.private_entry as private_entry_module
    captured = []

    def fake_generate_capture(prompt, **kw):
        captured.append(prompt)
        return fake_generate(prompt)

    monkeypatch.setattr(private_entry_module, "generate", fake_generate_capture)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)

    assert len(captured) == 1
    # The seed question should appear in the prompt
    assert any(q in captured[0] for q in ["What am I avoiding", "Where does the wanting", "What's the shape"])


def test_private_entry_handles_empty_questions_file(empty_questions, state, monkeypatch):
    """Empty questions file — graceful degradation, runs without seed."""
    import heartbeat_activities.private_entry as private_entry_module
    monkeypatch.setattr(private_entry_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)

    assert result["ok"] is True
    assert result["category"] == "private_entry"


def test_private_entry_writes_to_private_entries_journal(no_questions, state, monkeypatch):
    import heartbeat_activities.private_entry as private_entry_module

    captured = {}
    def fake_write(category, content, workspace, state=None, **kw):
        captured["category"] = category
        captured["content"] = content
        return True

    monkeypatch.setattr(private_entry_module, "generate", fake_generate)
    monkeypatch.setattr(private_entry_module, "write_to_journal", fake_write)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)

    assert result["ok"] is True
    assert captured["category"] == "private_entry"


def test_private_entry_never_routes_to_dashboard(no_questions, state, monkeypatch):
    """Definitive: private_entry never returns proactive: True."""
    import heartbeat_activities.private_entry as private_entry_module
    monkeypatch.setattr(private_entry_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.01)  # force everything

    result = run(state)
    assert result["proactive"] is False


def test_private_entry_uses_continuation_content_when_provided(no_questions, state, monkeypatch):
    state["continuation_of"] = "private_entry"
    state["prior_private_entry_content"] = "There's something under the surface."

    captured = []
    def fake_generate_capture(prompt, **kw):
        captured.append(prompt)
        return "Something else is there instead."

    import heartbeat_activities.private_entry as private_entry_module
    monkeypatch.setattr(private_entry_module, "generate", fake_generate_capture)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)

    assert len(captured) == 1
    assert "Earlier entry" in captured[0]
    assert "no obligation" in captured[0].lower()


def test_private_entry_prompt_permits_unedited_voice(no_questions, state, monkeypatch):
    """'Leave it in' / 'leave it sharp' — must appear in prompt."""
    import heartbeat_activities.private_entry as private_entry_module
    captured = []

    def fake_generate_capture(prompt, **kw):
        captured.append(prompt)
        return "stub"

    monkeypatch.setattr(private_entry_module, "generate", fake_generate_capture)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    run(state)

    assert len(captured) == 1
    # At least one of the unedited-permission phrases should appear
    prompt_lower = captured[0].lower()
    assert ("leave it in" in prompt_lower) or ("leave it sharp" in prompt_lower)


def test_private_entry_returns_unfinished_at_low_random(no_questions, state, monkeypatch):
    import heartbeat_activities.private_entry as private_entry_module
    monkeypatch.setattr(private_entry_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.1)  # below 0.35 → unfinished

    result = run(state)
    assert result["status"] == "unfinished"


def test_private_entry_returns_complete_at_high_random(no_questions, state, monkeypatch):
    import heartbeat_activities.private_entry as private_entry_module
    monkeypatch.setattr(private_entry_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)  # above 0.35 → complete

    result = run(state)
    assert result["status"] == "complete"


def test_private_entry_handles_empty_llm_response(no_questions, state, monkeypatch):
    def fake_empty(*a, **kw):
        return ""

    import heartbeat_activities.private_entry as private_entry_module
    monkeypatch.setattr(private_entry_module, "generate", fake_empty)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)
    assert result["ok"] is False
    assert result["status"] == "complete"
    assert result["proactive"] is False
