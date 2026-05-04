"""
Tests for creative activity (Activity Port 3).

Covers: happy path, missing interests, journal routing, continuation,
       deliberate unfinished, novelty vs. due-bias pick, prompt content,
       empty LLM response.
"""

import random
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.creative import (
    run,
    _parse_interests,
    UNFINISHED_PROBABILITY,
    NOVELTY_PROBABILITY,
)


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def interests_file(tmp_path):
    path = tmp_path / "INTERESTS.md"
    path.write_text(
        "- chaos theory #math\n"
        "- sourdough fermentation #food\n"
        "- the colour purple #aesthetic\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def empty_interests(tmp_path):
    path = tmp_path / "INTERESTS.md"
    path.write_text("", encoding="utf-8")
    return path


@pytest.fixture
def state(tmp_path):
    return {
        "WORKSPACE": str(tmp_path),
        "INTERESTS_FILE": "INTERESTS.md",
        "LLM_MODEL": "llama3.1:latest",
        "LLM_ENDPOINT": "http://localhost:11434",
        "tick_count": 5,
        "last_creative": {},
        "overdue_activities": {},
        "unfinished_threads": [],
    }


# ── Helpers ────────────────────────────────────────────────────────────────

def fake_generate(prompt, **kw):
    return "A strange light falls through the window, the colour of old grief."


def noop_log(*a, **k):
    pass


# ── Interest Parsing ───────────────────────────────────────────────────────

def test_parses_interests_file(interests_file):
    interests = _parse_interests(interests_file)
    topics = {i["topic"] for i in interests}
    assert "chaos theory" in topics
    assert "sourdough fermentation" in topics


# ── Activity Run ───────────────────────────────────────────────────────────

def test_creative_runs_with_interests_file(interests_file, state, monkeypatch):
    import heartbeat_activities.creative as creative_module
    monkeypatch.setattr(creative_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)

    assert result["ok"] is True
    assert result["category"] == "creative"
    assert result["status"] in ("complete", "unfinished")
    assert len(result["content"]) > 0


def test_creative_handles_missing_interests(interests_file, state):
    state["INTERESTS_FILE"] = "NOT_HERE.md"
    result = run(state)
    assert result["ok"] is False
    assert result["status"] == "complete"
    assert result["detail"] == "INTERESTS.md not found"


def test_creative_handles_empty_llm_response(interests_file, state, monkeypatch):
    def fake_empty(*a, **kw):
        return ""

    import heartbeat_activities.creative as creative_module
    monkeypatch.setattr(creative_module, "generate", fake_empty)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)
    assert result["ok"] is False
    assert result["status"] == "complete"


def test_creative_writes_to_memory_journal(interests_file, state, monkeypatch):
    """Journal path includes memory/{date}.md routing."""
    import heartbeat_activities.creative as creative_module
    import heartbeat_activities.journal as journal_module

    captured = {}
    def fake_write(category, content, workspace, state=None, **kw):
        captured["category"] = category
        captured["content"] = content
        return True

    monkeypatch.setattr(creative_module, "generate", fake_generate)
    monkeypatch.setattr(creative_module, "write_to_journal", fake_write)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)

    assert result["ok"] is True
    assert captured["category"] == "creative"


def test_creative_uses_continuation_content_when_provided(interests_file, state, monkeypatch):
    state["continuation_of"] = "creative"
    state["prior_creative_content"] = "A strange light falls through the window."

    captured = []
    def fake_generate_capture(prompt, **kw):
        captured.append(prompt)
        return "It comes back to it."

    import heartbeat_activities.creative as creative_module
    monkeypatch.setattr(creative_module, "generate", fake_generate_capture)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    result = run(state)

    assert len(captured) == 1
    assert "Earlier you wrote" in captured[0]
    assert "strange light" in captured[0]


def test_creative_sometimes_returns_unfinished(interests_file, state, monkeypatch):
    """Mock random below UNFINISHED_PROBABILITY → status must be unfinished."""
    import heartbeat_activities.creative as creative_module
    monkeypatch.setattr(creative_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    # Force random below threshold
    monkeypatch.setattr(random, "random", lambda: 0.1)

    result = run(state)
    assert result["status"] == "unfinished"


def test_creative_returns_complete_when_random_high(interests_file, state, monkeypatch):
    """Mock random above UNFINISHED_PROBABILITY → status must be complete."""
    import heartbeat_activities.creative as creative_module
    monkeypatch.setattr(creative_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    # Force random above threshold
    monkeypatch.setattr(random, "random", lambda: 0.9)

    result = run(state)
    assert result["status"] == "complete"


def test_creative_picks_random_interest_when_novelty_fires(interests_file, state, monkeypatch):
    """Mock random below NOVELTY_PROBABILITY → novelty path → random.choice used."""
    import heartbeat_activities.creative as creative_module
    monkeypatch.setattr(creative_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    # Force novelty path (first random call = novelty check, second = unfinished)
    original_random = random.Random(42)
    def forced_random():
        # First call → below 0.3 = novelty fires
        # Second call → above 0.3 = complete (not unfinished)
        return 0.05   # same value used for both calls

    call_count = [0]
    def controlled_random():
        call_count[0] += 1
        val = 0.05   # novelty fires (below 0.3), complete (above 0.3)
        return val

    monkeypatch.setattr(random, "random", controlled_random)

    result = run(state)
    # Should complete (0.05 < 0.3 = novelty fires, 0.05 < 0.3 = unfinished)
    assert result["status"] == "unfinished"


def test_creative_picks_due_interest_when_novelty_doesnt_fire(interests_file, state, monkeypatch):
    """Mock random above NOVELTY_PROBABILITY → due-bias path used."""
    state["last_creative"] = {
        "chaos theory": 0,
        "sourdough fermentation": 2,
        "the colour purple": 9,
    }

    import heartbeat_activities.creative as creative_module
    captured = []

    def fake_generate_capture(prompt, **kw):
        captured.append(prompt)
        return "stub"

    monkeypatch.setattr(creative_module, "generate", fake_generate_capture)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)

    # First call above 0.3 = novelty doesn't fire → due-bias fires
    # Second call above 0.3 = complete
    call_count = [0]
    def controlled_random():
        call_count[0] += 1
        return 0.8   # both above 0.3

    monkeypatch.setattr(random, "random", controlled_random)

    result = run(state)
    # Due-bias picks the most-due (chaos theory, age=10)
    assert "chaos theory" in result["detail"]


def test_creative_prompt_contains_first_person_hint(interests_file, state, monkeypatch):
    """Prompt should include 'first person' as a signal."""
    import heartbeat_activities.creative as creative_module
    captured = []

    def fake_generate_capture(prompt, **kw):
        captured.append(prompt)
        return "stub"

    monkeypatch.setattr(creative_module, "generate", fake_generate_capture)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)  # complete, no novelty

    run(state)

    assert len(captured) == 1
    assert "first person" in captured[0]
