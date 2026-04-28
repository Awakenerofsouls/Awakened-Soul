"""Tests for proactive.py — proactive content sender."""

import subprocess
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.proactive import send_proactive, test_openclaw_available


class TestSendProactive:
    def test_empty_content_returns_false(self):
        assert send_proactive("") is False
        assert send_proactive("   ") is False

    def test_none_content_returns_false(self):
        # The function checks for falsy content
        result = send_proactive("")
        assert result is False

    def test_calls_subprocess_on_success(self, monkeypatch, tmp_path):
        """When openclaw succeeds (rc=0), returns True."""
        call_count = {}
        def fake_run(cmd, capture_output=False, text=False, timeout=None, env=None):
            call_count["cmd"] = cmd
            result = subprocess.CompletedProcess(cmd, 0, stdout="OK", stderr="")
            return result
        monkeypatch.setattr("subprocess.run", fake_run)

        result = send_proactive("Hello {{USER_NAME}}")
        assert result is True
        assert "--message" in str(call_count.get("cmd", []))

    def test_returns_false_on_nonzero_returncode(self, monkeypatch):
        """Non-zero return code from openclaw → returns False."""
        def fake_run(cmd, capture_output=False, text=False, timeout=None, env=None):
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="connection refused")
        monkeypatch.setattr("subprocess.run", fake_run)

        result = send_proactive("Test message")
        assert result is False

    def test_returns_false_on_timeout(self, monkeypatch):
        """Timeout → returns False, doesn't raise."""
        def fake_run(cmd, capture_output=False, text=False, timeout=None, env=None):
            raise subprocess.TimeoutExpired(cmd, 30)
        monkeypatch.setattr("subprocess.run", fake_run)

        result = send_proactive("Test message")
        assert result is False

    def test_returns_false_on_exception(self, monkeypatch):
        """Unexpected error → returns False, doesn't raise."""
        def fake_run(cmd, capture_output=False, text=False, timeout=None, env=None):
            raise OSError("something went wrong")
        monkeypatch.setattr("subprocess.run", fake_run)

        result = send_proactive("Test message")
        assert result is False

    def test_openclaw_not_found_returns_false(self, monkeypatch):
        """openclaw binary missing and not in PATH → returns False."""
        import shutil
        monkeypatch.setattr(shutil, "which", lambda name: None)
        monkeypatch.setattr(Path, "exists", lambda self: False)

        result = send_proactive("Test message")
        assert result is False


class TestTestOpenclawAvailable:
    def test_returns_bool(self):
        result = test_openclaw_available()
        assert isinstance(result, bool)