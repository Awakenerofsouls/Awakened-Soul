"""
brain/tests/conftest.py

Shared pytest setup for the brain test suite.

Two responsibilities:

1. PYTHONPATH — make sure both the repo root AND the repo's `skills/`
   directory are importable. Several tests do `from safeguard import ...`
   (the runtime layout where safeguard.py is the live file at
   ~/.agent/workspace/skills/safeguard.py); in the repo, the file lives
   at `skills/safeguard.py`, so we add `skills/` to sys.path.

2. State isolation — every BrainMechanism's persist_state() writes to
   $AGENT_HOME/brain_state/{name}.json. Without isolation, one test's state
   leaks into the next test's mechanism instance. We point AGENT_HOME at
   a per-session temp directory and clear it before the suite runs so
   tests start from a clean baseline.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# 1. PYTHONPATH augmentations
for path in (REPO_ROOT, REPO_ROOT / "skills"):
    p = str(path)
    if p not in sys.path:
        sys.path.insert(0, p)

# 2. Isolated AGENT_HOME / AGENT_WORKSPACE for the test session
_TEST_AGENT_HOME = Path(tempfile.gettempdir()) / "awakened_soul_test_agent_home"
_TEST_AGENT_WS = Path(tempfile.gettempdir()) / "awakened_soul_test_agent_ws"

if _TEST_AGENT_HOME.exists():
    shutil.rmtree(_TEST_AGENT_HOME, ignore_errors=True)
if _TEST_AGENT_WS.exists():
    shutil.rmtree(_TEST_AGENT_WS, ignore_errors=True)

(_TEST_AGENT_HOME / "brain_state").mkdir(parents=True, exist_ok=True)
(_TEST_AGENT_WS / "brain").mkdir(parents=True, exist_ok=True)

# Set BEFORE any brain.* import that reads env at import time
os.environ.setdefault("AGENT_HOME", str(_TEST_AGENT_HOME))
os.environ.setdefault("AGENT_WORKSPACE", str(_TEST_AGENT_WS))
os.environ.setdefault("WORKSPACE", str(_TEST_AGENT_WS))


import pytest


@pytest.fixture(autouse=True)
def _isolate_brain_state():
    """
    Wipe $AGENT_HOME/brain_state/ between tests so a mechanism instantiated
    in test A cannot inherit persisted state from a prior test B. This is
    cheap (a small directory) and prevents the cross-test failures we
    observed where wire_20_belief_archaeology / wire_21_longing pass alone
    but fail in the full suite due to leaked state.
    """
    state_dir = _TEST_AGENT_HOME / "brain_state"
    if state_dir.exists():
        shutil.rmtree(state_dir, ignore_errors=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    yield
