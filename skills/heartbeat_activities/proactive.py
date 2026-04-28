"""
Proactive content sender.

Called by the runner when an activity returns proactive: True.
Uses the openclaw CLI to send a message into the main agent session.

The three proactive activities (self_check, insight_synthesis, relationship_check)
signal things {{AGENT_NAME}} wants to tell {{USER_NAME}}. This bridges heartbeat → dashboard.
"""

import logging
import subprocess
import sys
from pathlib import Path

log = logging.getLogger("heartbeat.proactive")


SESSION_ID = "agent:main:main"
OPENCLAW_BIN = "/opt/homebrew/bin/openclaw"


def send_proactive(content: str, session: str = SESSION_ID) -> bool:
    """
    Send proactive content to the main agent session.

    Args:
        content: text to send
        session: target session (default: agent:main:main)

    Returns:
        True if sent successfully, False on any error.
    """
    if not content or not content.strip():
        return False

    # Resolve openclaw binary path
    openclaw_path = Path(OPENCLAW_BIN)
    if not openclaw_path.exists():
        import shutil
        resolved = shutil.which("openclaw")
        if resolved:
            openclaw_path = Path(resolved)
        else:
            log.warning("openclaw binary not found at %s or in PATH", OPENCLAW_BIN)
            return False

    cmd = [str(openclaw_path), "agent", "--session-id", session, "--message", content.strip()]
    # Ensure node/openclaw tools are on PATH for the subprocess
    import os
    subprocess_env = {**os.environ, "PATH": "/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "")}

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            env=subprocess_env,
        )
        if result.returncode == 0:
            log.info("Proactive message sent to %s (%d chars)", session, len(content))
            return True
        else:
            log.warning("Proactive send failed (rc=%d): %s", result.returncode, result.stderr[:200])
            return False
    except subprocess.TimeoutExpired:
        log.warning("Proactive send timed out after 30s")
        return False
    except Exception as e:
        log.warning("Proactive send error: %s", e)
        return False


def test_openclaw_available() -> bool:
    """Check if openclaw binary is accessible."""
    import shutil
    return shutil.which("openclaw") is not None or Path(OPENCLAW_BIN).exists()