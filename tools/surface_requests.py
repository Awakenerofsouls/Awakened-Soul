#!/usr/bin/env python3
"""
tools/surface_requests.py
Lists pending surface requests. Marks them seen.

Run: python surface_requests.py
     python surface_requests.py --all    (show all, not just pending)
     python surface_requests.py --clear  (mark all seen)

Built from v20.0 handoff spec.
"""

import sys, os
import os
sys.path.insert(0, os.path.join(os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.openclaw/workspace")), "brain"))

from meta.surface_request import SurfaceRequestSystem, Significance
from datetime import datetime


def main():
    show_all = "--all" in sys.argv
    clear = "--clear" in sys.argv

    sr = SurfaceRequestSystem()

    if clear:
        sr.mark_all_seen()
        print("All surface requests marked as seen.")
        return

    pending = sr.get_pending()

    if not pending:
        print("No pending surface requests.")
        return

    print(f"=== SURFACE REQUESTS ({len(pending)} pending) ===\n")

    for req in pending:
        wall = datetime.fromtimestamp(req.timestamp).strftime("%Y-%m-%d %H:%M")
        sig_marker = {
            Significance.HIGH: "***",
            Significance.MEDIUM: "**",
            Significance.LOW: "*",
        }.get(req.significance, "")

        print(f"[{sig_marker}] {req.event_type.upper()} | tick {req.tick} | {wall}")
        print(f"  {req.summary}")
        if req.private_log_reference:
            print(f"  Log ref: tick {req.private_log_reference}")
        print(f"  ID: {req.request_id}")
        print()

    print(f"Mark seen: python surface_requests.py --mark <id>")
    print(f"Mark all:  python surface_requests.py --clear")


if __name__ == "__main__":
    main()
