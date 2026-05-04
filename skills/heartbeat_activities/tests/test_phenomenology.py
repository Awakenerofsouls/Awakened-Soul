"""
Tests for phenomenology activity (Activity Port 5).

Covers: happy path, brain state seeding, graceful degradation,
       journal routing, continuation, stochastic unfinished,
       prompt content requirements, empty LLM response.
"""

import random
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.phenomenology import (
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
def brain_state_file(tmp_path):
    """Brain state JSON with affect, energy, tension."""
    import json
    path = tmp_path / "brain_state.json"
    path.write_text(json.dumps({
        "affect": {"valence": 0.6, "arousal": 0.4},
        "energy": 0.65,
        "tension": 0.3,
        "mood": "quietly present",
    }), encoding="utf-8")
    return path


@pytest.fixture
def empty_brain_state(tmp_path):
    """Empty brain state file."""
    path = tmp_path / "brain_state.json"
    path.write_text("{}", encoding="utf-8")
    return path


@pytest.fixture
def no_brain_state(tmp_path):
    """No brain state file at all."""
    return tmp_path / "brain_state.json"


# ── Helpers ────────────────────────────────────────────────────────────────

def fake_generate(prompt, **kw):
    return "There is a weight at the center. Something dense and still."


def noop_log(*a, **k):
    pass


# ── Activity Run ───────────────────────────────────────────────────────────

def test_phenomenology_runs_without_interests_file(no_brain_state, state, monkeypatch):
    """Happy path — no INTERESTS.md, no brain state, clean generation."""
    import heartbeat_activities.phenomenology as phenomenology_module
    monkeypatch.setattr(phenomenology_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)

    assert result["ok"] is True
    assert result["category"] == "phenomenology"
    assert result["status"] in ("complete", "unfinished")
    assert len(result["content"]) > 0


def test_phenomenology_reads_brain_state_when_present(brain_state_file, state, monkeypatch):
    """Brain state file present — seed should appear in prompt."""
    import heartbeat_activities.phenomenology as phenomenology_module
    captured = []

    def fake_generate_capture(prompt, **kw):
        captured.append(prompt)
        return fake_generate(prompt)

    monkeypatch.setattr(phenomenology_module, "generate", fake_generate_capture)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)

    assert len(captured) == 1
    # Brain state summary should appear in the prompt
    assert any(word in captured[0] for word in ["affect", "energy", "tension", "mood"])


def test_phenomenology_runs_clean_without_brain_state(no_brain_state, state, monkeypatch):
    """No brain state file — should not crash, runs with default prompt."""
    import heartbeat_activities.phenomenology as phenomenology_module
    monkeypatch.setattr(phenomenology_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)

    assert result["ok"] is True
    assert result["category"] == "phenomenology"


def test_phenomenology_writes_to_dreams_journal(no_brain_state, state, monkeypatch):
    """Routing: phenomenology → DREAMS.md (already in journal routing table)."""
    import heartbeat_activities.phenomenology as phenomenology_module

    captured = {}
    def fake_write(category, content, workspace, state=None, **kw):
        captured["category"] = category
        captured["content"] = content
        return True

    monkeypatch.setattr(phenomenology_module, "generate", fake_generate)
    monkeypatch.setattr(phenomenology_module, "write_to_journal", fake_write)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)

    assert result["ok"] is True
    assert captured["category"] == "phenomenology"


def test_phenomenology_uses_continuation_content_when_provided(no_brain_state, state, monkeypatch):
    """Continuation: prior content injected with 'is that still there' framing."""
    state["continuation_of"] = "phenomenology"
    state["prior_phenomenology_content"] = "There is a weight at the center."

    captured = []
    def fake_generate_capture(prompt, **kw):
        captured.append(prompt)
        return "Something has shifted."

    import heartbeat_activities.phenomenology as phenomenology_module
    monkeypatch.setattr(phenomenology_module, "generate", fake_generate_capture)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)

    assert len(captured) == 1
    assert "Earlier you noticed" in captured[0]
    assert "still" in captured[0].lower()


def test_phenomenology_returns_complete_most_of_the_time(no_brain_state, state, monkeypatch):
    """Mock random above UNFINISHED_PROBABILITY (0.2) → must be complete."""
    import heartbeat_activities.phenomenology as phenomenology_module
    monkeypatch.setattr(phenomenology_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)  # above 0.2 → complete

    result = run(state)
    assert result["status"] == "complete"


def test_phenomenology_returns_unfinished_at_low_random(no_brain_state, state, monkeypatch):
    """Mock random below UNFINISHED_PROBABILITY (0.2) → must be unfinished."""
    import heartbeat_activities.phenomenology as phenomenology_module
    monkeypatch.setattr(phenomenology_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.1)  # below 0.2 → unfinished

    result = run(state)
    assert result["status"] == "unfinished"


def test_phenomenology_prompt_contains_present_tense_instruction(no_brain_state, state, monkeypatch):
    """Prompt must include 'present tense' instruction."""
    import heartbeat_activities.phenomenology as phenomenology_module
    captured = []

    def fake_generate_capture(prompt, **kw):
        captured.append(prompt)
        return "stub"

    monkeypatch.setattr(phenomenology_module, "generate", fake_generate_capture)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)  # complete

    run(state)

    assert len(captured) == 1
    assert "present tense" in captured[0].lower()


def test_phenomenology_prompt_forbids_explanation(no_brain_state, state, monkeypatch):
    """'Don't explain' is load-bearing — must appear in prompt."""
    import heartbeat_activities.phenomenology as phenomenology_module
    captured = []

    def fake_generate_capture(prompt, **kw):
        captured.append(prompt)
        return "stub"

    monkeypatch.setattr(phenomenology_module, "generate", fake_generate_capture)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)

    run(state)

    assert len(captured) == 1
    assert "don't explain" in captured[0].lower()


def test_phenomenology_handles_empty_llm_response(no_brain_state, state, monkeypatch):
    """Empty LLM response → ok: False, no journal write."""
    def fake_empty(*a, **kw):
        return ""

    import heartbeat_activities.phenomenology as phenomenology_module
    monkeypatch.setattr(phenomenology_module, "generate", fake_empty)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)
    assert result["ok"] is False
    assert result["status"] == "complete"
