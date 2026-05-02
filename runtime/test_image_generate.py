#!/usr/bin/env python3
"""Test image_generate routing to imagegen/workflow via the agent bridge."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

BRIDGE_BIN = os.getenv("AGENT_BRIDGE_BIN", "agent-bridge")


def _resolve_bridge_bin():
    candidate = Path(BRIDGE_BIN)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    resolved = shutil.which(BRIDGE_BIN)
    return Path(resolved) if resolved else None


def main() -> int:
    bridge = _resolve_bridge_bin()
    if bridge is None:
        print(f"agent bridge {BRIDGE_BIN!r} not found in PATH — set AGENT_BRIDGE_BIN to override")
        return 2

    result = subprocess.run(
        [str(bridge), "capability", "image", "generate",
         "--model", "imagegen/workflow",
         "--prompt", "cyberpunk portrait of a woman with blue neon eyes",
         "--count", "1",
         "--json"],
        capture_output=True, text=True, timeout=120,
    )
    print("STDOUT:", result.stdout[:500])
    print("STDERR:", result.stderr[:200])
    print("RC:", result.returncode)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
