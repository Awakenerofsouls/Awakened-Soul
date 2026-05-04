"""
Tests for self_check activity (Activity Port 6).

Covers: happy path, brain state seeding, malformed JSON degrade,
       journal routing, continuation, stochastic unfinished,
       prompt performance guard, proactive flag logic (signal words + random).
"""

import random
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.self_check import (
    run,
    _compute_proactive,
    UNFINISHED_PROBABILITY,
    PROACTIVE_BASE_RATE,
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
def brain_state_file(tmp_path):
    import json
    path = tmp_path / "brain_state.json"
    path.write_text(json.dumps({
        "dominant_state": "quietly present",
        "tension": 0.3,
        "energy": 0.65,
    }), encoding="utf-8")
    return path


@pytest.fixture
def empty_brain_state(tmp_path):
    path = tmp_path / "brain_state.json"
    path.write_text("{}", encoding="utf-8")
    return path


@pytest.fixture
def no_brain_state(tmp_path):
    return tmp_path / "brain_state.json"


@pytest.fixture
def user_file_with_name(tmp_path):
    """USER.md with primary name 'the operator'."""
    path = tmp_path / "USER.md"
    path.write_text("# the operator\n\nSome description", encoding="utf-8")
    return path


@pytest.fixture
def no_user_file(tmp_path):
    """"No USER.md at all."""
    return tmp_path / "USER.md"


@pytest.fixture
def malformed_user_file(tmp_path):
    """Malformed USER.md — no H1 heading."""
    path = tmp_path / "USER.md"
    path.write_text("No heading here", encoding="utf-8")
    return path


@pytest.fixture
def malformed_brain_state(tmp_path):
    path = tmp_path / "brain_state.json"
    path.write_text("not valid json{{{", encoding="utf-8")
    return path


# ── Helpers ────────────────────────────────────────────────────────────────

def fake_generate(prompt, **kw):
    return "Something has been building. I'm tired and I don't know why."


def noop_log(*a, **k):
    pass


# ── Activity Run ───────────────────────────────────────────────────────────

def test_self_check_runs_without_brain_state(no_brain_state, state, monkeypatch):
    import heartbeat_activities.self_check as self_check_module
    monkeypatch.setattr(self_check_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)

    assert result["ok"] is True
    assert result["category"] == "self_check"
    assert result["status"] in ("complete", "unfinished")
    assert result["proactive"] in (True, False)
    assert len(result["content"]) > 0


def test_self_check_reads_brain_state_when_present(brain_state_file, state, monkeypatch):
    import heartbeat_activities.self_check as self_check_module
    captured = []

    def fake_generate_capture(prompt, **kw):
        captured.append(prompt)
        return fake_generate(prompt)

    monkeypatch.setattr(self_check_module, "generate", fake_generate_capture)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)

    assert len(captured) == 1
    assert any(word in captured[0] for word in ["tension", "energy", "dominant"])


def test_self_check_handles_malformed_brain_state(malformed_brain_state, state, monkeypatch):
    """Corrupt JSON — graceful degradation, runs clean with empty state."""
    import heartbeat_activities.self_check as self_check_module
    monkeypatch.setattr(self_check_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)

    assert result["ok"] is True
    assert result["category"] == "self_check"


def test_self_check_writes_to_self_check_journal(no_brain_state, state, monkeypatch):
    import heartbeat_activities.self_check as self_check_module

    captured = {}
    def fake_write(category, content, workspace, state=None, **kw):
        captured["category"] = category
        captured["content"] = content
        return True

    monkeypatch.setattr(self_check_module, "generate", fake_generate)
    monkeypatch.setattr(self_check_module, "write_to_journal", fake_write)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)

    assert result["ok"] is True
    assert captured["category"] == "self_check"


def test_self_check_uses_continuation_content_when_provided(no_brain_state, state, monkeypatch):
    state["continuation_of"] = "self_check"
    state["prior_self_check_content"] = "Something has been building."

    captured = []
    def fake_generate_capture(prompt, **kw):
        captured.append(prompt)
        return "Where is that now?"

    import heartbeat_activities.self_check as self_check_module
    monkeypatch.setattr(self_check_module, "generate", fake_generate_capture)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)

    assert len(captured) == 1
    assert "Earlier self-check" in captured[0]
    assert "where is that now" in captured[0].lower()


def test_self_check_prompt_forbids_performance(no_brain_state, state, monkeypatch):
    """'Don't perform wellness or distress' must appear in prompt."""
    import heartbeat_activities.self_check as self_check_module
    captured = []

    def fake_generate_capture(prompt, **kw):
        captured.append(prompt)
        return "stub"

    monkeypatch.setattr(self_check_module, "generate", fake_generate_capture)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)  # complete

    run(state)

    assert len(captured) == 1
    assert "don't perform" in captured[0].lower()


def test_self_check_returns_unfinished_at_low_random(no_brain_state, state, monkeypatch):
    import heartbeat_activities.self_check as self_check_module
    monkeypatch.setattr(self_check_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.1)  # below 0.25 → unfinished

    result = run(state)
    assert result["status"] == "unfinished"


def test_self_check_returns_complete_most_of_the_time(no_brain_state, state, monkeypatch):
    import heartbeat_activities.self_check as self_check_module
    monkeypatch.setattr(self_check_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)  # above 0.25 → complete

    result = run(state)
    assert result["status"] == "complete"


# ── Proactive Flag ─────────────────────────────────────────────────────────

def test_self_check_proactive_fires_on_signal_words(no_brain_state, user_file_with_name, state, monkeypatch):
    """Content contains primary name → proactive must be True."""
    import heartbeat_activities.self_check as self_check_module

    def fake_with_signal(prompt, **kw):
        return "I want to tell the operator something. Something has been building."


    monkeypatch.setattr(self_check_module, "generate", fake_with_signal)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.99)

    result = run(state)
    assert result["proactive"] is True


def test_self_check_proactive_fires_on_low_random(no_brain_state, user_file_with_name, state, monkeypatch):
    """No signal words, random below PROACTIVE_BASE_RATE (0.15) → proactive True."""
    import heartbeat_activities.self_check as self_check_module

    def fake_no_signal(prompt, **kw):
        return "I'm tired. That's all. Nothing special going on."


    monkeypatch.setattr(self_check_module, "generate", fake_no_signal)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.05)


    result = run(state)
    assert result["proactive"] is True


def test_self_check_proactive_false_otherwise(no_brain_state, user_file_with_name, state, monkeypatch):
    """No signal words, random above PROACTIVE_BASE_RATE (0.15) → proactive False."""
    import heartbeat_activities.self_check as self_check_module

    def fake_no_signal(prompt, **kw):
        return "I'm tired. That's all. Nothing special going on."


    monkeypatch.setattr(self_check_module, "generate", fake_no_signal)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.5)


    result = run(state)
    assert result["proactive"] is False


def test_self_check_proactive_no_user_file(no_brain_state, no_user_file, state, monkeypatch):
    """No USER.md → graceful degradation, no crash, proactive still works on generic signals."""
    import heartbeat_activities.self_check as self_check_module

    def fake_with_generic(prompt, **kw):
        return "I want to tell someone something. Something has been building."

    monkeypatch.setattr(self_check_module, "generate", fake_with_generic)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.99)

    result = run(state)
    # Should succeed without crash — 'something building' is a generic signal
    assert result["ok"] is True
    assert result["proactive"] is True


def test_self_check_proactive_malformed_user_file(no_brain_state, malformed_user_file, state, monkeypatch):
    """Malformed USER.md → graceful degradation."""
    import heartbeat_activities.self_check as self_check_module

    def fake_with_signal(prompt, **kw):
        return "I want to tell the operator something."


    monkeypatch.setattr(self_check_module, "generate", fake_with_signal)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.99)

    result = run(state)
    # Should succeed without crash — the operator appears in content itself (not from USER.md)
    assert result["ok"] is True
    assert result["proactive"] is True  # the operator is in the content string
