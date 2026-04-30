"""
Identity helpers for heartbeat activities.

Provides per-agent identity extraction from workspace files.
Used to parameterize activities that reference the primary human
by name (self_check signal words, private_entry prompt, relational activities).

These functions read from workspace files at runtime — the agent's own
files, not shipped content. Framework stays agent-neutral.
"""

from pathlib import Path


def extract_primary_name(workspace: Path, user_file: str = "USER.md") -> str:
    """
    Extract the primary human's name from USER.md.

    Looks for the first H1 heading (# Name) in the file.
    Returns the name as a stripped string, or empty string if not found.

    Examples:
        "# {{USER_NAME}}"        → "{{USER_NAME}}"
        "# {{USER_NAME}}"         → "{{USER_NAME}}"
        "" (no file)     → ""
        "" (no heading)  → ""

    Args:
        workspace: root Path for the agent workspace
        user_file: filename of the identity file (USER.md by default)

    Returns:
        The primary human's name, or "" if not found.
    """
    try:
        path = workspace / user_file
        if not path.exists():
            return ""
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("# "):
                # First H1 heading is the primary human's name
                return line[2:].strip()
        return ""
    except Exception:
        return ""
