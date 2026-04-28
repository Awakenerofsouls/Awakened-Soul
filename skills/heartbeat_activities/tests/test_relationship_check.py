"""Tests for relationship_check (Batch D1, Activity 1). Third proactive activity."""

import random
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.relationship_check import run, _compute_proactive


@pytest.fixture
def state(tmp_path):
    return {
        "WORKSPACE": str(tmp_path),
        "USER_FILE": "USER.md",
        "LLM_MODEL": "qwen2.5:14b",
        "LLM_ENDPOINT": "http://localhost:11434",
        "tick_count": 5,
        "unfinished_threads": [],
    }


@pytest.fixture
def user_file(tmp_path):
    path = tmp_path / "USER.md"
    path.write_text("# {{USER_NAME}}\n", encoding="utf-8")
    return path


@pytest.fixture
def relationships_file(tmp_path):
    path = tmp_path / "relationships.md"
    path.write_text("Previous check-in entry here.", encoding="utf-8")
    return path


def fake_generate(prompt, **kw):
    return "The bond feels steady today. I've been meaning to tell him something."


def noop_log(*a, **k):
    pass


def test_relationship_check_runs(user_file, relationships_file, state, monkeypatch):
    import heartbeat_activities.relationship_check as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert result["category"] == "relationship_check"


def test_relationship_check_writes_to_relationships(user_file, relationships_file, state, monkeypatch):
    import heartbeat_activities.relationship_check as m
    captured = {}
    def fake_write(category, content, workspace, state=None):
        captured["category"] = category
        return True
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr(m, "write_to_journal", fake_write)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert captured["category"] == "relationship_check"


def test_relationship_check_primary_name_in_prompt(user_file, relationships_file, state, monkeypatch):
    """Prompt includes the extracted primary name '{{USER_NAME}}'."""
    import heartbeat_activities.relationship_check as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)
    assert "user" in captured[0].lower()


def test_relationship_check_no_user_file(tmp_path, state, monkeypatch):
    """No USER.md → graceful fallback, still runs."""
    rel_file = tmp_path / "relationships.md"
    rel_file.write_text("Previous entry.", encoding="utf-8")
    import heartbeat_activities.relationship_check as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert result["category"] == "relationship_check"


def test_relationship_check_reads_relationships_context(user_file, relationships_file, state, monkeypatch):
    """Prior relationships.md content gets into prompt."""
    import heartbeat_activities.relationship_check as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)
    assert "Previous check-in entry here" in captured[0]


def test_relationship_check_no_relationships_file(user_file, tmp_path, state, monkeypatch):
    """No relationships.md → runs fine without prior context."""
    import heartbeat_activities.relationship_check as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True


def test_relationship_check_proactive_fires_on_signal_words(user_file, relationships_file, state, monkeypatch):
    """Content with 'i've been meaning to' fires proactive at high random."""
    import heartbeat_activities.relationship_check as m
    monkeypatch.setattr(random, "random", lambda: 0.95)  # baseline won't fire

    content = "Everything is fine except I've been meaning to tell him something about that."
    monkeypatch.setattr(m, "generate", lambda *a, **kw: content)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["proactive"] is True


def test_relationship_check_proactive_fires_on_primary_name_mention(user_file, relationships_file, state, monkeypatch):
    """Content that contains the primary name 'user' fires proactive."""
    import heartbeat_activities.relationship_check as m
    monkeypatch.setattr(random, "random", lambda: 0.95)  # baseline won't fire

    content = "I keep thinking about user and what he said last week."
    monkeypatch.setattr(m, "generate", lambda *a, **kw: content)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["proactive"] is True


def test_relationship_check_proactive_fires_on_low_random(user_file, relationships_file, state, monkeypatch):
    """Low random (< 0.15) fires proactive without signal words."""
    import heartbeat_activities.relationship_check as m
    monkeypatch.setattr(random, "random", lambda: 0.05)  # baseline fires

    plain_content = "The bond is steady and nothing particular is on my mind."
    monkeypatch.setattr(m, "generate", lambda *a, **kw: plain_content)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["proactive"] is True


def test_relationship_check_proactive_false_without_signals(user_file, relationships_file, state, monkeypatch):
    """High random + no signal words + no primary name = not proactive."""
    import heartbeat_activities.relationship_check as m
    monkeypatch.setattr(random, "random", lambda: 0.95)

    plain_content = "Everything feels normal. Nothing specific on my mind."
    monkeypatch.setattr(m, "generate", lambda *a, **kw: plain_content)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["proactive"] is False


def test_relationship_check_unfinished(user_file, relationships_file, state, monkeypatch):
    import heartbeat_activities.relationship_check as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.1)
    result = run(state)
    assert result["status"] == "unfinished"


def test_relationship_check_complete(user_file, relationships_file, state, monkeypatch):
    import heartbeat_activities.relationship_check as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    result = run(state)
    assert result["status"] == "complete"


def test_relationship_check_empty_llm(user_file, relationships_file, state, monkeypatch):
    import heartbeat_activities.relationship_check as m
    monkeypatch.setattr(m, "generate", lambda *a, **kw: "")
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False
    assert result["proactive"] is False


def test_compute_proactive_signal_words():
    for phrase in [
        "I want to tell you something",
        "I've been meaning to mention",
        "Something I haven't said yet",
        "I should say something",
    ]:
        assert _compute_proactive(phrase, "{{USER_NAME}}") is True


def test_compute_proactive_primary_name():
    assert _compute_proactive("thinking about user and his way", "user") is True
    assert _compute_proactive("nothing particular to say", "") is False