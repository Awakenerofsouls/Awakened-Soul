"""
Heartbeat activity: image_make

Wraps a per-operator image_engine.make_one() so the dispatcher's softmax
pick can fire image generation autonomously, not just via the legacy
self_pic activity.

The framework does not ship an image engine — image generation is
operator-specific (model choices, category sets, prompt styles, weights).
Operators who want autonomous image generation place a Python module
named `image_engine` in their workspace at:

    $AGENT_WORKSPACE/skills/image_engine.py

The module is expected to expose:

    make_one(forced_category: str | None = None) -> dict
      → returns {"ok": bool, "category": str, "saved": str, "axes": dict, ...}

If no image_engine is present, this activity fails gracefully and the
dispatcher continues to the next pick.

Activity contract:
  Input:  state dict (WORKSPACE — read by the engine itself via env vars
          or state hint; passing through state is harmless redundancy)
  Output: {"ok": bool, "status": "complete", "content": str, "category": str,
           "proactive": False, "detail": str, "saved": str}
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict

from .log import log_activity

CATEGORY = "image_make"
SIGNAL_AFFINITY = {
    "valence_positive": 0.3,   # more output when valence is up
    "arousal":          0.4,   # higher arousal → more creative output
    "rce_coherence":    0.2,   # coherent state → better composition
}


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fire one image generation. The engine picks the category internally
    (whatever weighting it implements). Saves wherever the engine saves
    and returns a standard activity result dict.
    """
    workspace = Path(state.get("WORKSPACE", os.environ.get("AGENT_WORKSPACE", "."))).expanduser()

    # Ensure workspace/skills is on sys.path so we can import image_engine.
    skills_dir = str(workspace / "skills")
    if skills_dir not in sys.path:
        sys.path.insert(0, skills_dir)

    try:
        import image_engine  # type: ignore[import-not-found]
    except ImportError as e:
        return {
            "ok": False,
            "status": "complete",
            "category": CATEGORY,
            "content": "",
            "proactive": False,
            "detail": f"no image_engine module in workspace/skills/ ({e})",
        }
    except Exception as e:
        return {
            "ok": False,
            "status": "complete",
            "category": CATEGORY,
            "content": "",
            "proactive": False,
            "detail": f"image_engine import failed: {e}",
        }

    try:
        result = image_engine.make_one()
    except Exception as e:
        return {
            "ok": False,
            "status": "complete",
            "category": CATEGORY,
            "content": "",
            "proactive": False,
            "detail": f"make_one() raised: {e}",
        }

    if not result.get("ok"):
        return {
            "ok": False,
            "status": "complete",
            "category": CATEGORY,
            "content": "",
            "proactive": False,
            "detail": result.get("detail", "engine returned ok=False"),
        }

    sub_category = result.get("category", "?")
    saved = result.get("saved", "")
    saved_name = Path(saved).name if saved else ""

    # Log via journal so this lands in ACTIVITY_LOG.md alongside other activities.
    log_activity(
        sub_category,
        f"Generated {sub_category} image: {saved_name}",
        salience=0.55,
        tags=f"heartbeat,image,{sub_category}",
    )

    return {
        "ok":         True,
        "status":     "complete",
        "category":   CATEGORY,
        "sub_category": sub_category,
        "content":    f"Generated {sub_category} image",
        "saved":      saved,
        "axes":       result.get("axes", {}),
        "proactive":  False,
        "detail":     f"saved {saved_name} ({sub_category})",
    }
