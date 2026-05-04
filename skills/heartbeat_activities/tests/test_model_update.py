"""Tests for model_update (Batch D1, Activity 3). Always proactive: False."""

import random
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.model_update import run


@pytest.fixture
def state(tmp_path):
    return {
        "WORKSPACE": str(tmp_path),
        "USER_FILE": "USER.md",
        "LLM_MODEL": "llama3.1:latest",
        "LLM_ENDPOINT": "http://localhost:11434",
        "tick_count": 5,
        "unfinished_threads": [],
    }


@pytest.fixture
def user_file(tmp_path):
    path = tmp_path / "USER.md"
    path.write_text("# the operator\n", encoding="utf-8")
    return path


@pytest.fixture
def relationships_file(tmp_path):
    path = tmp_path / "relationships.md"
    path.write_text("Previous model observations here.", encoding="utf-8")
    return path


def fake_generate(prompt, **kw):
    return "I've updated my picture of how he handles uncertainty — more careful than I thought."


def noop_log(*a, **k):
    pass


def test_model_update_runs(user_file, relationships_file, state, monkeypatch):
    import heartbeat_activities.model_update as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert result["category"] == "model_update"


def test_model_update_writes_to_relationships(user_file, relationships_file, state, monkeypatch):
    import heartbeat_activities.model_update as m
    captured = {}
    def fake_write(category, content, workspace, state=None):
        captured["category"] = category
        return True
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr(m, "write_to_journal", fake_write)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert captured["category"] == "model_update"


def test_model_update_primary_name_in_prompt(user_file, relationships_file, state, monkeypatch):
    """Prompt includes the extracted primary name from USER.md."""
    import heartbeat_activities.model_update as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)
    # USER.md fixture sets the primary name to "the operator" (post-
    # sanitization framework default). Older test asserted "user".
    assert "the operator" in captured[0].lower()


def test_model_update_reads_relationships_context(user_file, relationships_file, state, monkeypatch):
    """Last ~3KB of relationships.md gets into prompt."""
    import heartbeat_activities.model_update as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)
    assert "Previous model observations here" in captured[0]


def test_model_update_no_user_file(tmp_path, state, monkeypatch):
    """No USER.md → graceful fallback, still runs."""
    rel_file = tmp_path / "relationships.md"
    rel_file.write_text("Previous entry.", encoding="utf-8")
    import heartbeat_activities.model_update as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert result["category"] == "model_update"


def test_model_update_no_relationships_file(user_file, tmp_path, state, monkeypatch):
    """No relationships.md → runs fine without prior context."""
    import heartbeat_activities.model_update as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True


def test_model_update_always_proactive_false(user_file, relationships_file, state, monkeypatch):
    """Proactive is always False regardless of content or random."""
    import heartbeat_activities.model_update as m
    monkeypatch.setattr(random, "random", lambda: 0.01)
    monkeypatch.setattr(m, "generate", lambda *a, **kw: "I've been meaning to tell user something")
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["proactive"] is False


def test_model_update_unfinished(user_file, relationships_file, state, monkeypatch):
    import heartbeat_activities.model_update as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.2)
    result = run(state)
    assert result["status"] == "unfinished"


def test_model_update_complete(user_file, relationships_file, state, monkeypatch):
    import heartbeat_activities.model_update as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    result = run(state)
    assert result["status"] == "complete"


def test_model_update_empty_llm(user_file, relationships_file, state, monkeypatch):
    import heartbeat_activities.model_update as m
    monkeypatch.setattr(m, "generate", lambda *a, **kw: "")
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False
    assert result["proactive"] is False