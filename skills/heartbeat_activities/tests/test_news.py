"""Tests for news_scan (Batch B, Activity 1)."""

import random
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.news import run


@pytest.fixture
def state(tmp_path):
    return {
        "WORKSPACE": str(tmp_path),
        "INTERESTS_FILE": "INTERESTS.md",
        "LLM_MODEL": "qwen2.5:14b",
        "LLM_ENDPOINT": "http://localhost:11434",
        "tick_count": 5,
        "unfinished_threads": [],
        "last_news": {},
    }


@pytest.fixture
def interests_file(tmp_path):
    path = tmp_path / "INTERESTS.md"
    path.write_text("- consciousness #mind\n- sourdough #food\n", encoding="utf-8")
    return path


@pytest.fixture
def no_interests(tmp_path):
    return tmp_path / "INTERESTS.md"


def fake_generate(prompt, **kw):
    return "Three things are shifting in consciousness research right now."


def noop_log(*a, **k):
    pass


def test_news_runs(interests_file, state, monkeypatch):
    import heartbeat_activities.news as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert result["category"] == "news_scan"
    assert result["proactive"] is False


def test_news_missing_interests(no_interests, state, monkeypatch):
    import heartbeat_activities.news as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False
    assert "not found" in result["detail"]


def test_news_empty_interests(tmp_path, state, monkeypatch):
    path = tmp_path / "INTERESTS.md"
    path.write_text("", encoding="utf-8")
    import heartbeat_activities.news as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False


def test_news_writes_to_journal(interests_file, state, monkeypatch):
    import heartbeat_activities.news as m
    captured = {}
    def fake_write(category, content, workspace, state=None):
        captured["category"] = category
        return True
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr(m, "write_to_journal", fake_write)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert captured["category"] == "news_scan"


def test_news_continuation(interests_file, state, monkeypatch):
    state["continuation_of"] = "news_scan"
    state["prior_news_content"] = "Earlier scan."
    import heartbeat_activities.news as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "New developments."
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    run(state)
    assert "Earlier scan" in captured[0]


def test_news_prompt_contains_scan(interests_file, state, monkeypatch):
    import heartbeat_activities.news as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)
    assert "scan" in captured[0].lower()


def test_news_unfinished(interests_file, state, monkeypatch):
    import heartbeat_activities.news as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.05)
    result = run(state)
    assert result["status"] == "unfinished"


def test_news_complete(interests_file, state, monkeypatch):
    import heartbeat_activities.news as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    result = run(state)
    assert result["status"] == "complete"


def test_news_empty_llm(interests_file, state, monkeypatch):
    import heartbeat_activities.news as m
    monkeypatch.setattr(m, "generate", lambda *a, **kw: "")
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False
    assert result["proactive"] is False