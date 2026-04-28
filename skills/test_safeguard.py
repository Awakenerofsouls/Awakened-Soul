#!/usr/bin/env python3
"""
test_safeguard.py — tests for skills/safeguard.py

Covers:
- Whitelist matches (positive path)
- Non-whitelist blocks (negative path)
- Absolute blocks (git reset --hard, git push --force, rm -rf)
- Journal paths allowed freely
- Protected paths blocked (framework files)
- Unclassified paths blocked (restrictive default)
- File move: memory archival allowed, other blocked
- File delete always blocked
- Loop detection: 3 blocks triggers halt
- Halt persists: calls during halt return False immediately
- reset_safeguard clears state

Run:
 python3 -m pytest skills/test_safeguard.py -v
"""

import json
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from skills import safeguard


class SafeguardTestBase(unittest.TestCase):
    """Base class — isolates state + log files to tmp for every test."""

    def setUp(self):
        self.tmp_state = Path("/tmp/test_safeguard_state.json")
        self.tmp_log = Path("/tmp/test_safeguard_log.md")
        if self.tmp_state.exists():
            self.tmp_state.unlink()
        if self.tmp_log.exists():
            self.tmp_log.unlink()
        self._orig_state = safeguard.SAFEGUARD_STATE
        self._orig_log = safeguard.SAFEGUARD_LOG
        safeguard.SAFEGUARD_STATE = self.tmp_state
        safeguard.SAFEGUARD_LOG = self.tmp_log

        self._telegram_patch = patch.object(safeguard, "_send_telegram", return_value=True)
        self.mock_telegram = self._telegram_patch.start()

    def tearDown(self):
        safeguard.SAFEGUARD_STATE = self._orig_state
        safeguard.SAFEGUARD_LOG = self._orig_log
        self._telegram_patch.stop()
        if self.tmp_state.exists():
            self.tmp_state.unlink()
        if self.tmp_log.exists():
            self.tmp_log.unlink()

    def _state(self) -> dict:
        if self.tmp_state.exists():
            return json.loads(self.tmp_state.read_text())
        return {"blocked_counts": {}, "halted_until": None}


class TestWhitelist(SafeguardTestBase):


    def test_02_whitelisted_crontab_read_allowed(self):
        result = safeguard.can_perform("subprocess", ["crontab", "-l"])
        self.assertTrue(result)

    def test_03_non_whitelisted_subprocess_blocked(self):
        result = safeguard.can_perform(
            "subprocess", ["python3", "evil_script.py"]
        )
        self.assertFalse(result)


class TestAbsoluteBlocks(SafeguardTestBase):

    def test_04_git_reset_hard_absolute_block(self):
        result = safeguard.can_perform(
            "subprocess", ["git", "reset", "--hard"]
        )
        self.assertFalse(result)

    def test_05_git_push_force_absolute_block(self):
        result = safeguard.can_perform(
            "subprocess", ["git", "push", "--force"]
        )
        self.assertFalse(result)

    def test_06_rm_rf_absolute_block(self):
        result = safeguard.can_perform(
            "subprocess", ["rm", "-rf", "/tmp/anything"]
        )
        self.assertFalse(result)


class TestFileWriteGate(SafeguardTestBase):

    def test_07_journal_path_dreams_md_allowed(self):
        result = safeguard.can_perform("file_write", "DREAMS.md")
        self.assertTrue(result)

    def test_08_journal_pattern_memory_dir_allowed(self):
        result = safeguard.can_perform(
            "file_write", "memory/2026-04-19.md"
        )
        self.assertTrue(result)

    def test_09_protected_path_soul_md_blocked(self):
        result = safeguard.can_perform("file_write", "SOUL.md")
        self.assertFalse(result)

    def test_10_protected_path_brain_subpath_blocked(self):
        result = safeguard.can_perform(
            "file_write", "brain/new_mechanism.py"
        )
        self.assertFalse(result)

    def test_11_unclassified_path_blocked_by_default(self):
        result = safeguard.can_perform(
            "file_write", "/tmp/unknown_file.txt"
        )
        self.assertFalse(result)


class TestFileMoveAndDelete(SafeguardTestBase):

    def test_12_memory_archival_move_allowed(self):
        result = safeguard.can_perform(
            "file_move", "memory/archive/old.json"
        )
        self.assertTrue(result)

    def test_13_file_delete_always_blocked(self):
        result = safeguard.can_perform(
            "file_delete", "anything_at_all.py"
        )
        self.assertFalse(result)


class TestLoopDetectionAndHalt(SafeguardTestBase):

    def test_14_three_blocks_same_key_triggers_halt(self):
        for _ in range(3):
            safeguard.can_perform(
                "subprocess", ["python3", "blocked_script.py"]
            )

        state = self._state()
        self.assertIsNotNone(state.get("halted_until"))
        self.assertGreater(state["halted_until"], time.time())

        result = safeguard.can_perform(
            "subprocess", ["python3", "skills/example-skill.py"]
        )
        self.assertFalse(result)

    def test_15_reset_safeguard_clears_halt_and_counts(self):
        for _ in range(3):
            safeguard.can_perform(
                "subprocess", ["python3", "blocked_script.py"]
            )

        self.assertIsNotNone(self._state().get("halted_until"))

        safeguard.reset_safeguard()

        state = self._state()
        self.assertIsNone(state.get("halted_until"))
        self.assertEqual(state.get("blocked_counts"), {})

        result = safeguard.can_perform(
            "subprocess", ["python3", "skills/example-skill.py"]
        )
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
