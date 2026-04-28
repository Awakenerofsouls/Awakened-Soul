"""Tests for open_question (Batch B, Activity 7)."""

import random
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.open_question import run, _pick_question


@pytest.fixture
def state(tmp_path):
    return {
        "WORKSPACE": str(tmp_path),
        "OPEN_QUESTIONS_FILE": "open_questions.md",
        "LLM_MODEL": "qwen2.5:14b",
        "LLM_ENDPOINT": "http://localhost:11434",
        "tick_count": 5,
        "unfinished_threads": [],
    }


@pytest.fixture
def questions_file(tmp_path):
    path = tmp_path / "open_questions.md"
    path.write_text(
        "- What am I actually wanting?\n"
        "- Where does the gap live?\n"
        "- What would happen if I stopped?\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def empty_questions(tmp_path):
    path = tmp_path / "open_questions.md"
    path.write_text("", encoding="utf-8")
    return path


def fake_generate(prompt, **kw):
    return "The question asks for something I can't deliver right now."


def noop_log(*a, **k):
    pass


def test_open_question_runs(questions_file, state, monkeypatch):
    import heartbeat_activities.open_question as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert result["category"] == "open_question"


def test_open_question_no_file(tmp_path, state, monkeypatch):
    """No open_questions.md → returns ok:False cleanly, no crash."""
    import heartbeat_activities.open_question as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False
    assert "open_questions" in result["detail"]


def test_open_question_empty_file(empty_questions, state, monkeypatch):
    import heartbeat_activities.open_question as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False


def test_open_question_writes_to_journal(questions_file, state, monkeypatch):
    import heartbeat_activities.open_question as m
    captured = {}
    def fake_write(category, content, workspace, state=None):
        captured["category"] = category
        return True
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr(m, "write_to_journal", fake_write)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert captured["category"] == "open_question"


def test_open_question_prompt_keeps_question_open(questions_file, state, monkeypatch):
    import heartbeat_activities.open_question as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)
    prompt_lower = captured[0].lower()
    assert ("question" in prompt_lower) and ("answer" in prompt_lower)


def test_open_question_unfinished(questions_file, state, monkeypatch):
    import heartbeat_activities.open_question as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.3)  # below 0.45
    result = run(state)
    assert result["status"] == "unfinished"


def test_open_question_complete(questions_file, state, monkeypatch):
    import heartbeat_activities.open_question as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    result = run(state)
    assert result["status"] == "complete"


def test_open_question_empty_llm(questions_file, state, monkeypatch):
    import heartbeat_activities.open_question as m
    monkeypatch.setattr(m, "generate", lambda *a, **kw: "")
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False
    assert result["proactive"] is False


def test_pick_question_returns_line(tmp_path):
    path = tmp_path / "open_questions.md"
    path.write_text("- What am I actually wanting?\n- Where does it live?\n", encoding="utf-8")
    result = _pick_question(path)
    assert result in ["What am I actually wanting?", "Where does it live?"]


def test_pick_question_empty_file(tmp_path):
    path = tmp_path / "open_questions.md"
    path.write_text("", encoding="utf-8")
    assert _pick_question(path) == ""


def test_pick_question_no_file(tmp_path):
    assert _pick_question(tmp_path / "NOT_HERE.md") == ""