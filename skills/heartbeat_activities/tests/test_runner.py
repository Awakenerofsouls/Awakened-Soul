"""Tests for runner.py — heartbeat loop."""

import json
import os
import signal
import sys
import time
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# We need to test the HeartbeatRunner class without actually running the loop.
# Use a mock approach: patch time.sleep so the loop exits after one iteration.


@pytest.fixture
def mock_dispatcher():
    """Mock dispatcher that returns a predictable result."""
    mock_result = {
        "ok": True,
        "status": "complete",
        "category": "research",
        "content": "Test activity content",
        "proactive": False,
        "detail": "test result",
    }
    dispatcher = MagicMock()
    dispatcher.dispatch.return_value = mock_result
    return dispatcher


class TestFreshState:
    def test_fresh_state_has_required_fields(self):
        from heartbeat_activities.runner import fresh_state
        state = fresh_state()
        assert state["tick_count"] == 0
        assert state["unfinished_threads"] == []
        assert "last_news" in state
        assert "last_tool" in state


class TestStatePersistence:
    def test_save_and_load_roundtrip(self, tmp_path):
        from heartbeat_activities.runner import save_state, load_state, fresh_state
        state_file = tmp_path / "state.json"
        state = fresh_state()
        state["tick_count"] = 42
        state["unfinished_threads"] = [{"category": "test", "created_tick": 10}]

        save_state(state, str(state_file))
        loaded = load_state(str(state_file))

        assert loaded["tick_count"] == 42
        assert len(loaded["unfinished_threads"]) == 1

    def test_load_missing_file_returns_fresh_state(self, tmp_path):
        from heartbeat_activities.runner import load_state
        result = load_state(str(tmp_path / "NOT_HERE.json"))
        assert result["tick_count"] == 0

    def test_save_creates_parent_dir(self, tmp_path):
        from heartbeat_activities.runner import save_state, fresh_state
        state_file = tmp_path / "subdir" / "nested" / "state.json"
        save_state(fresh_state(), str(state_file))
        assert state_file.exists()


class TestContinuationOf:
    def test_update_continuation_of_sets_oldest_thread(self):
        from heartbeat_activities.runner import _update_continuation_of
        state = {
            "unfinished_threads": [
                {"category": "deep_curiosity", "created_tick": 5},
                {"category": "research", "created_tick": 3},  # oldest
            ],
        }
        _update_continuation_of(state)
        assert state.get("continuation_of") == "research"

    def test_update_continuation_of_clears_when_empty(self):
        from heartbeat_activities.runner import _update_continuation_of
        state = {"unfinished_threads": [], "continuation_of": "old_value"}
        _update_continuation_of(state)
        assert "continuation_of" not in state


class TestTrackUnfinished:
    def test_tracks_new_unfinished_result(self):
        from heartbeat_activities.runner import _track_unfinished
        state = {"unfinished_threads": [], "tick_count": 15}
        result = {
            "category": "deep_curiosity",
            "content": "Test content for deep curiosity thread",
            "status": "unfinished",
        }
        _track_unfinished(state, result)
        threads = state["unfinished_threads"]
        assert len(threads) == 1
        assert threads[0]["category"] == "deep_curiosity"
        assert threads[0]["created_tick"] == 15

    def test_replaces_prior_thread_for_same_category(self):
        from heartbeat_activities.runner import _track_unfinished
        state = {
            "unfinished_threads": [
                {"category": "deep_curiosity", "created_tick": 5, "content_preview": "old"},
            ],
            "tick_count": 20,
        }
        result = {
            "category": "deep_curiosity",
            "content": "New content",
            "status": "unfinished",
        }
        _track_unfinished(state, result)
        threads = state["unfinished_threads"]
        assert len(threads) == 1
        assert threads[0]["created_tick"] == 20  # updated

    def test_empty_content_not_tracked(self):
        from heartbeat_activities.runner import _track_unfinished
        state = {"unfinished_threads": [], "tick_count": 10}
        result = {"category": "test", "content": "", "status": "unfinished"}
        _track_unfinished(state, result)
        assert len(state["unfinished_threads"]) == 0


class TestRunnerTick:
    def test_tick_increments_counter(self, mock_dispatcher):
        from heartbeat_activities.runner import HeartbeatRunner

        runner = HeartbeatRunner()
        runner.dispatcher = mock_dispatcher
        runner.state = {"tick_count": 0, "unfinished_threads": [], "WORKSPACE": "/tmp"}
        runner.running = False  # stop after one tick

        with patch("heartbeat_activities.runner.save_state") as mock_save, \
             patch("heartbeat_activities.runner.time.sleep"):
            runner.tick()

        assert runner.state["tick_count"] == 1

    def test_activity_runs_on_activity_tick(self, mock_dispatcher):
        from heartbeat_activities.runner import HeartbeatRunner

        runner = HeartbeatRunner()
        runner.state = {"tick_count": 2, "unfinished_threads": [], "WORKSPACE": "/tmp"}
        runner.running = False

        with patch("heartbeat_activities.runner.dispatcher.dispatch", mock_dispatcher.dispatch):
            with patch("heartbeat_activities.runner.time.sleep"):
                runner.tick()

        mock_dispatcher.dispatch.assert_called_once()

    def test_activity_skipped_on_non_activity_tick(self, mock_dispatcher):
        from heartbeat_activities.runner import HeartbeatRunner

        runner = HeartbeatRunner()
        runner.dispatcher = mock_dispatcher
        runner.state = {"tick_count": 1, "unfinished_threads": [], "WORKSPACE": "/tmp"}
        runner.running = False

        with patch("heartbeat_activities.runner.time.sleep"):
            runner.tick()

        mock_dispatcher.dispatch.assert_not_called()

    def test_proactive_result_triggers_sender(self):
        from heartbeat_activities.runner import HeartbeatRunner

        fake_dispatch = MagicMock(return_value={
            "ok": True, "status": "complete", "category": "self_check",
            "content": "I want to tell user something",
            "proactive": True, "detail": "",
        })

        runner = HeartbeatRunner()
        # Start at 2 so tick becomes 3 (divisible by 3) → fires activity
        runner.state = {"tick_count": 2, "unfinished_threads": [], "WORKSPACE": "/tmp"}
        runner.running = False

        with patch("heartbeat_activities.runner.dispatcher.dispatch", fake_dispatch):
            with patch("heartbeat_activities.runner.send_proactive") as mock_send, \
                 patch("heartbeat_activities.runner.time.sleep"):
                mock_send.return_value = True
                runner.tick()

        mock_send.assert_called_once_with("I want to tell user something")

    def test_non_proactive_result_does_not_trigger_sender(self, mock_dispatcher):
        from heartbeat_activities.runner import HeartbeatRunner

        runner = HeartbeatRunner()
        runner.dispatcher = mock_dispatcher
        runner.state = {"tick_count": 0, "unfinished_threads": [], "WORKSPACE": "/tmp"}
        runner.running = False

        with patch("heartbeat_activities.runner.send_proactive") as mock_send, \
             patch("heartbeat_activities.runner.time.sleep"):
            runner.tick()

        mock_send.assert_not_called()

    def test_state_saved_every_STATE_SAVE_EVERY_ticks(self):
        from heartbeat_activities.runner import HeartbeatRunner, STATE_SAVE_EVERY

        fake_dispatch = MagicMock(return_value={"ok": True, "status": "complete",
                                                  "category": "research", "proactive": False,
                                                  "content": "", "detail": ""})

        runner = HeartbeatRunner()
        # Start at STATE_SAVE_EVERY - 2 = 8. First tick → 9 (no save).
        runner.state = {"tick_count": STATE_SAVE_EVERY - 2, "unfinished_threads": [], "WORKSPACE": "/tmp"}
        runner.running = False

        with patch("heartbeat_activities.runner.dispatcher.dispatch", fake_dispatch):
            with patch("heartbeat_activities.runner.save_state") as mock_save, \
                 patch("heartbeat_activities.runner.time.sleep"):
                runner.tick()  # tick_count becomes 9 — not a save point

        mock_save.assert_not_called()

        # Second tick in a fresh patch context: tick_count becomes 10 → save fires
        with patch("heartbeat_activities.runner.dispatcher.dispatch", fake_dispatch):
            with patch("heartbeat_activities.runner.save_state") as mock_save, \
                 patch("heartbeat_activities.runner.time.sleep"):
                runner.tick()

        mock_save.assert_called_once()


class TestSignalHandling:
    def test_installs_handlers(self):
        from heartbeat_activities.runner import HeartbeatRunner

        runner = HeartbeatRunner()
        runner.running = True

        with patch("signal.signal") as mock_signal:
            runner.install_signal_handlers()
            # Should register SIGTERM and SIGINT
            assert mock_signal.call_count >= 2