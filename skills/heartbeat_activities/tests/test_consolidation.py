"""Tests for consolidation (Batch C, Activity 2)."""

import random
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.consolidation import run


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
def memory_dir(tmp_path):
    d = tmp_path / "memory"
    d.mkdir()
    return d


def fake_generate(prompt, **kw):
    return "The through-line is around language and how it shapes questions."


def noop_log(*a, **k):
    pass


def test_consolidation_runs(memory_dir, state, monkeypatch):
    import heartbeat_activities.consolidation as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert result["category"] == "consolidation"


def test_consolidation_writes_to_journal(memory_dir, state, monkeypatch):
    import heartbeat_activities.consolidation as m
    captured = {}
    def fake_write(category, content, workspace, state=None):
        captured["category"] = category
        return True
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr(m, "write_to_journal", fake_write)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True
    assert captured["category"] == "consolidation"


def test_consolidation_reads_yesterday_when_today_thin(memory_dir, state, monkeypatch):
    """Today's file is < 200 chars → consolidation should read yesterday."""
    from datetime import datetime, timezone, timedelta

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    # Today's is thin
    (memory_dir / f"{today}.md").write_text(
        "One short entry.", encoding="utf-8"
    )
    # Yesterday has rich content
    (memory_dir / f"{yesterday}.md").write_text(
        "Yesterday was productive. " * 50,  # big enough
        encoding="utf-8"
    )

    import heartbeat_activities.consolidation as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)

    # Prompt should reference yesterday's content
    assert len(captured) == 1
    assert "yesterday" in captured[0].lower() or "productive" in captured[0].lower()


def test_consolidation_reads_today_when_sufficient(memory_dir, state, monkeypatch):
    """Today's file is >= 200 chars → uses today's."""
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (memory_dir / f"{today}.md").write_text("X " * 150, encoding="utf-8")  # ~300 chars

    import heartbeat_activities.consolidation as m
    captured = []
    def fake_gen(prompt, **kw):
        captured.append(prompt)
        return "stub"
    monkeypatch.setattr(m, "generate", fake_gen)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    run(state)

    assert len(captured) == 1
    # Should NOT reference yesterday fallback
    assert "yesterday" not in captured[0].lower()


def test_consolidation_empty_memory(memory_dir, state, monkeypatch):
    """No memory files → runs fine."""
    import heartbeat_activities.consolidation as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is True


def test_consolidation_unfinished(memory_dir, state, monkeypatch):
    import heartbeat_activities.consolidation as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.1)
    result = run(state)
    assert result["status"] == "unfinished"


def test_consolidation_complete(memory_dir, state, monkeypatch):
    import heartbeat_activities.consolidation as m
    monkeypatch.setattr(m, "generate", fake_generate)
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    monkeypatch.setattr(random, "random", lambda: 0.9)
    result = run(state)
    assert result["status"] == "complete"


def test_consolidation_empty_llm(memory_dir, state, monkeypatch):
    import heartbeat_activities.consolidation as m
    monkeypatch.setattr(m, "generate", lambda *a, **kw: "")
    monkeypatch.setattr("heartbeat_activities.log.log_activity", noop_log)
    result = run(state)
    assert result["ok"] is False
    assert result["proactive"] is False