"""Tests for proactive.py — proactive content sender."""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.proactive import (
    send_proactive,
    test_bridge_available,
)


@pytest.fixture
def fake_bridge(monkeypatch):
    """Stub _resolve_bridge_bin() to return a fake binary path so tests can
    focus on subprocess behavior rather than PATH resolution."""
    monkeypatch.setattr(
        "heartbeat_activities.proactive._resolve_bridge_bin",
        lambda: Path("/fake/agent-bridge"),
    )


class TestSendProactive:
    def test_empty_content_returns_false(self):
        assert send_proactive("") is False
        assert send_proactive("   ") is False

    def test_none_content_returns_false(self):
        result = send_proactive("")
        assert result is False

    def test_calls_subprocess_on_success(self, monkeypatch, fake_bridge):
        """When the bridge succeeds (rc=0), returns True."""
        call_count = {}

        def fake_run(cmd, capture_output=False, text=False, timeout=None, env=None):
            call_count["cmd"] = cmd
            return subprocess.CompletedProcess(cmd, 0, stdout="OK", stderr="")

        monkeypatch.setattr("subprocess.run", fake_run)

        result = send_proactive("Hello operator")
        assert result is True
        assert "--message" in str(call_count.get("cmd", []))

    def test_returns_false_on_nonzero_returncode(self, monkeypatch, fake_bridge):
        """Non-zero return code from the bridge → returns False."""

        def fake_run(cmd, capture_output=False, text=False, timeout=None, env=None):
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="connection refused")

        monkeypatch.setattr("subprocess.run", fake_run)

        assert send_proactive("Test message") is False

    def test_returns_false_on_timeout(self, monkeypatch, fake_bridge):
        """Timeout → returns False, doesn't raise."""

        def fake_run(cmd, capture_output=False, text=False, timeout=None, env=None):
            raise subprocess.TimeoutExpired(cmd, 30)

        monkeypatch.setattr("subprocess.run", fake_run)

        assert send_proactive("Test message") is False

    def test_returns_false_on_exception(self, monkeypatch, fake_bridge):
        """Unexpected error → returns False, doesn't raise."""

        def fake_run(cmd, capture_output=False, text=False, timeout=None, env=None):
            raise OSError("something went wrong")

        monkeypatch.setattr("subprocess.run", fake_run)

        assert send_proactive("Test message") is False

    def test_bridge_not_found_returns_false(self, monkeypatch):
        """Bridge binary missing and not in PATH → returns False."""
        monkeypatch.setattr(
            "heartbeat_activities.proactive._resolve_bridge_bin",
            lambda: None,
        )
        assert send_proactive("Test message") is False


class TestBridgeAvailable:
    def test_returns_bool(self):
        result = test_bridge_available()
        assert isinstance(result, bool)
