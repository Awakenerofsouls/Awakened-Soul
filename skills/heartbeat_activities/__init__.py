"""
heartbeat_activities — neutral activity pool for Nexus {{AGENT_NAME}} framework.

Each module is one activity. Each activity follows the same contract:

    run(state: dict) -> dict:
        Input:  heartbeat state dict
        Output: {
            "ok": bool,
            "status": "complete" | "unfinished" | "followup_due:N",
            "content": str,
            "category": str,
            "detail": str,
        }

Registry is in dispatcher.py. Plugin loader appends operator-specific activities
at startup via register_plugin().
"""

from .dispatcher import ACTIVITY_REGISTRY, dispatch, register_plugin

__all__ = [
    "ACTIVITY_REGISTRY",
    "dispatch",
    "register_plugin",
]
