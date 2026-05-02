"""
Proactive content sender.

Called by the runner when an activity returns proactive: True.
Uses an agent-bridge CLI to send a message into the main agent session.

The bridge binary is resolved from `AGENT_BRIDGE_BIN` env (default
"agent-bridge"). If the binary isn't on PATH, send_proactive returns
False and logs a warning — the framework continues running without
proactive messaging.

The three proactive activities (self_check, insight_synthesis,
relationship_check) signal things the agent wants to tell the operator.
This bridges heartbeat → dashboard.
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

log = logging.getLogger("heartbeat.proactive")


SESSION_ID = "agent:main:main"

#: Name (or absolute path) of the bridge CLI binary. Operators wire this
#: to whatever messaging tool they use by setting AGENT_BRIDGE_BIN.
DEFAULT_BRIDGE_BIN = os.getenv("AGENT_BRIDGE_BIN", "agent-bridge")


def _resolve_bridge_bin() -> Optional[Path]:
    """
    Resolve the bridge binary. Looks at:
      1. AGENT_BRIDGE_BIN as an absolute path (if it exists)
      2. AGENT_BRIDGE_BIN as a name on PATH
    Returns None if neither resolves.
    """
    candidate = Path(DEFAULT_BRIDGE_BIN)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    resolved = shutil.which(DEFAULT_BRIDGE_BIN)
    return Path(resolved) if resolved else None


def send_proactive(content: str, session: str = SESSION_ID) -> bool:
    """
    Send proactive content to the main agent session via the bridge CLI.

    Args:
        content: text to send
        session: target session (default: agent:main:main)

    Returns:
        True if sent successfully, False on any error (no bridge installed,
        non-zero return code, timeout, etc.).
    """
    if not content or not content.strip():
        return False

    bridge = _resolve_bridge_bin()
    if bridge is None:
        log.warning(
            "agent bridge binary %r not found in PATH — set AGENT_BRIDGE_BIN to override",
            DEFAULT_BRIDGE_BIN,
        )
        return False

    cmd = [str(bridge), "agent", "--session-id", session, "--message", content.strip()]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            log.info("Proactive message sent to %s (%d chars)", session, len(content))
            return True
        log.warning("Proactive send failed (rc=%d): %s", result.returncode, result.stderr[:200])
        return False
    except subprocess.TimeoutExpired:
        log.warning("Proactive send timed out after 30s")
        return False
    except Exception as e:
        log.warning("Proactive send error: %s", e)
        return False


def test_bridge_available() -> bool:
    """Check if the bridge binary is accessible."""
    return _resolve_bridge_bin() is not None
