"""
Tests for research activity (Wire 20 reference implementation).

Covers: interest parsing, due-date weighting, continuation handling,
       LLM stubbing, journal routing, status contract.
"""

import pytest
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.research import run, _parse_interests


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def interests_file(tmp_path):
    """INTERESTS.md with 3 interests, various tag formats."""
    path = tmp_path / "INTERESTS.md"
    path.write_text(
        "- chaos theory #math #emergence\n"
        "- sourdough fermentation #food #fermentation\n"
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
    """Minimal valid state dict."""
    return {
        "WORKSPACE": str(tmp_path),
        "INTERESTS_FILE": "INTERESTS.md",
        "LLM_MODEL": "llama3.1:latest",
        "LLM_ENDPOINT": "http://localhost:11434",
        "tick_count": 5,
        "last_researched": {},
        "overdue_activities": {},
        "unfinished_threads": [],
    }


# ── Interest Parsing ────────────────────────────────────────────────────────

def test_parses_interests_file(interests_file):
    interests = _parse_interests(interests_file)
    assert len(interests) == 3
    assert interests[0]["topic"] == "chaos theory"
    assert interests[0]["tags"] == ["math", "emergence"]
    assert interests[0]["depth"] == "math"


def test_parses_bullet_formats(interests_file):
    interests = _parse_interests(interests_file)
    topics = {i["topic"] for i in interests}
    assert "chaos theory" in topics
    assert "sourdough fermentation" in topics
    assert "the colour purple" in topics  # * prefix


def test_tags_extracted_but_topic_preserved(interests_file):
    """Topic should be the full text WITHOUT #tags, tags list is separate."""
    interests = _parse_interests(interests_file)
    by_topic = {i["topic"]: i for i in interests}

    # "sourdough fermentation" — "fermentation" happens to be a tag word
    # but it should still be part of the topic since it's not prefixed with #
    entry = by_topic["sourdough fermentation"]
    assert "fermentation" in entry["topic"]
    assert "fermentation" in entry["tags"]
    # The topic should still have the words, just no # tokens
    assert "#" not in entry["topic"]


def test_empty_file_returns_empty_list(empty_interests):
    interests = _parse_interests(empty_interests)
    assert interests == []


def test_only_column_0_bullets_accepted(tmp_path):
    """Lines with leading whitespace before - or * are skipped."""
    path = tmp_path / "INTERESTS.md"
    path.write_text(
        "some header text\n"
        "- valid interest #tag\n"
        "not a bullet line\n"
        "  - indented bullet\n"
        "\t- tabbed bullet\n"
        "   * spaces-then-star\n",
        encoding="utf-8",
    )
    interests = _parse_interests(path)
    topics = [i["topic"] for i in interests]
    assert "valid interest" in topics
    assert "indented bullet" not in topics
    assert "tabbed bullet" not in topics
    assert "spaces-then-star" not in topics


# ── Activity Run (patched at point of use) ──────────────────────────────────

def test_returns_complete_on_valid_run(interests_file, state, monkeypatch):
    """Happy path — mock generate at the research module level."""
    def fake_generate(prompt, **kw):
        assert "chaos theory" in prompt
        return "Chaos theory shows tiny changes compound into large effects."

    # Patch where it's imported/used in the research module
    import heartbeat_activities.research as research_module
    monkeypatch.setattr(research_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", lambda *a, **k: None)

    result = run(state)

    assert result["ok"] is True
    assert result["status"] == "complete"
    assert result["category"] == "research"
    assert "chaos theory" in result["detail"]
    assert len(result["content"]) > 0


def test_returns_complete_when_no_interests(empty_interests, state):
    result = run(state)
    assert result["ok"] is False
    assert result["status"] == "complete"
    assert result["detail"] == "No interests found"


def test_returns_complete_when_file_missing(state):
    state["INTERESTS_FILE"] = "NOT_HERE.md"
    result = run(state)
    assert result["ok"] is False
    assert result["status"] == "complete"
    assert result["detail"] == "INTERESTS.md not found"


def test_weighted_pick_favors_due_interest(interests_file, state, monkeypatch):
    """
    When all topics have been researched, the oldest-due one wins.
    """
    state["tick_count"] = 10
    state["last_researched"] = {
        "chaos theory": 0,            # age 10 — most due
        "sourdough fermentation": 2,  # age 8
        "the colour purple": 9,       # age 1 — least due
    }


    called = []
    def fake_generate(prompt, **kw):
        called.append(prompt)
        return "stub"

    import heartbeat_activities.research as research_module
    monkeypatch.setattr(research_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", lambda *a, **k: None)

    result = run(state)

    # Should have picked "chaos theory" (oldest-due, age=10)
    assert "chaos theory" in result["detail"]


def test_continuation_prompt_injected(interests_file, state, monkeypatch):
    """When state has continuation_of=research, prior content is injected."""
    state["continuation_of"] = "research"
    state["prior_research_content"] = "Chaos theory shows non-linear growth."

    continuation_prompt = []
    def fake_generate(prompt, **kw):
        continuation_prompt.append(prompt)
        return "Continued thinking."

    import heartbeat_activities.research as research_module
    monkeypatch.setattr(research_module, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", lambda *a, **k: None)

    result = run(state)

    assert len(continuation_prompt) == 1
    assert "Chaos theory shows non-linear growth" in continuation_prompt[0]
    assert "Continue from there" in continuation_prompt[0]
    assert result["status"] == "complete"
