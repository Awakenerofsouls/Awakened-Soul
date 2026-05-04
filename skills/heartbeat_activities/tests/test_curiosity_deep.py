"""Tests for curiosity_deep_dive (Batch B, Activity 6)."""

import random
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.curiosity_deep import run, _pick_debt_topic


@pytest.fixture
def state(tmp_path):
    return {
        "WORKSPACE": str(tmp_path),
        "INTERESTS_FILE": "INTERESTS.md",
        "LLM_MODEL": "llama3.1:latest",
        "LLM_ENDPOINT": "http://localhost:11434",
        "tick_count": 10,
        "unfinished_threads": [],
        "last_deep_dive": {},
    }


@pytest.fixture
def interests_file(tmp_path):
    path = tmp_path / "INTERESTS.md"
    path.write_text(
        "- consciousness #mind\n"
        "- sourdough #food\n"
        "- the colour purple #aesthetic\n",
        encoding="utf-8",
    )
    return path


def fake_generate(prompt, **kw):
    return "I know the basics but I haven't gone deep. What's the interesting edge?"


def noop_log(*a, **k):
    pass


def test_deep_dive_runs(interests_file, state, monkeypatch):
    import heartbeat_activities.curiosity_deep as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert result["category"] == "curiosity_deep_dive"


def test_deep_dive_missing_interests(tmp_path, state, monkeypatch):
    import heartbeat_activities.curiosity_deep as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False


def test_deep_dive_writes_to_journal(interests_file, state, monkeypatch):
    import heartbeat_activities.curiosity_deep as m
    captured = {}
    def fake_write(category, content, workspace, state=None):
        captured["category"] = category
        return True
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr(m, "write_to_journal", fake_write)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert captured["category"] == "curiosity_deep_dive"


def test_deep_dive_debt_weighting_picks_least_touched(tmp_path):
    """Debt-weighting should pick the interest visited longest ago, not most recent."""
    interests = [
        {"topic": "consciousness"},
        {"topic": "sourdough"},
        {"topic": "the colour purple"},
    ]
    state_dict = {
        "last_deep_dive": {
            "consciousness": 9,       # age 1 — most recent
            "sourdough": 0,            # age 10 — most debt
            "the colour purple": 5,  # age 5
        },
        "tick_count": 10,
    }
    picked = _pick_debt_topic(interests, state_dict, 10)
    assert picked == "sourdough"  # highest debt (age 10)


def test_deep_dive_unfinished(interests_file, state, monkeypatch):
    import heartbeat_activities.curiosity_deep as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.2)  # below 0.35
    result = run(state)
    assert result["status"] == "unfinished"


def test_deep_dive_complete(interests_file, state, monkeypatch):
    import heartbeat_activities.curiosity_deep as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    result = run(state)
    assert result["status"] == "complete"


def test_deep_dive_empty_llm(interests_file, state, monkeypatch):
    import heartbeat_activities.curiosity_deep as m
    monkeypatch.setattr(m, "generate", lambda *a, **kw: "")
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False
    assert result["proactive"] is False