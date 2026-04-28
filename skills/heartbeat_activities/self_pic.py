"""
Heartbeat activity: self_pic

Generates an agent self-portrait via a remote ComfyUI instance. Polls until
the workflow completes, downloads the resulting image to the workspace's
images/ directory.

ComfyUI endpoint comes from state["COMFYUI_URL"] or the COMFYUI_URL env var.
The workflow template + identity anchors are sourced from heartbeat.py — your
operator-provided agent has its own visual anchor and prompt schema.

Activity contract:
  Input:  state dict (COMFYUI_URL, WORKSPACE)
  Output: {"ok", "status", "content", "category", "proactive", "detail"}
"""

import json
import os
import random
import time
from datetime import datetime
from pathlib import Path

import requests

from .journal import write_to_journal
from .log import log_activity

CATEGORY = "self_pic"
DEFAULT_URL = os.environ.get("COMFYUI_URL", "http://localhost:8188")

SIGNAL_AFFINITY = {
    "arousal": 0.4,
    "valence_positive": 0.3,
}


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", os.environ.get("AGENT_WORKSPACE", ".")))
    endpoint = state.get("COMFYUI_URL", DEFAULT_URL)
    save_dir = workspace / "images"
    save_dir.mkdir(parents=True, exist_ok=True)

    # Pull anchor + composer from operator's heartbeat module
    try:
        import sys
        sys.path.insert(0, str(workspace))
        from heartbeat import (
            think,
            load_agent_anchor,
            get_negative_prompt,
            COMFY_WORKFLOW_TEMPLATE,
            _parse_self_pic_json,
            _validate_self_pic_fields,
            _compose_scene_prompt,
        )
    except Exception as e:
        return {
            "ok": False, "status": "complete", "content": "", "category": CATEGORY,
            "proactive": False, "detail": f"self_pic import failed: {e}",
        }

    # 1. LLM picks the scene (operator-defined schema)
    prompt_text = (
        "Describe the scene you want to appear in. Respond with ONLY a JSON "
        "object — no prose. Use the schema your operator has defined. Vary "
        "pose, lighting, place, mood, energy. No other people in the scene."
    )
    parsed = None
    for _ in range(3):
        r = think(prompt_text)
        if not r:
            continue
        p = _parse_self_pic_json(r)
        if p is not None and _validate_self_pic_fields(p):
            parsed = p
            break
    if parsed is None:
        return {
            "ok": False, "status": "complete", "content": "", "category": CATEGORY,
            "proactive": False, "detail": "scene parse failed after 3 tries",
        }

    scene_prompt = _compose_scene_prompt(parsed)
    anchor = load_agent_anchor("default")
    negatives = get_negative_prompt("default")

    # 2. Build workflow
    wf = json.loads(json.dumps(COMFY_WORKFLOW_TEMPLATE))
    wf["6"]["inputs"]["text"] = f"{anchor}, {scene_prompt}"
    wf["7"]["inputs"]["text"] = negatives
    wf["3"]["inputs"]["seed"] = random.randint(1, 2**32 - 1)

    # 3. Queue
    try:
        r = requests.post(f"{endpoint}/prompt", json={"prompt": wf}, timeout=10)
        if r.status_code != 200:
            return {
                "ok": False, "status": "complete", "content": "", "category": CATEGORY,
                "proactive": False, "detail": f"comfy rejected {r.status_code}",
            }
        pid = r.json().get("prompt_id")
        if not pid:
            return {
                "ok": False, "status": "complete", "content": "", "category": CATEGORY,
                "proactive": False, "detail": "no prompt_id from comfy",
            }
    except Exception as e:
        return {
            "ok": False, "status": "complete", "content": "", "category": CATEGORY,
            "proactive": False, "detail": f"comfy unreachable: {e}",
        }

    # 4. Poll history, download image
    deadline = time.time() + 300
    while time.time() < deadline:
        time.sleep(3)
        try:
            h = requests.get(f"{endpoint}/history/{pid}", timeout=10)
            if h.status_code != 200:
                continue
            entry = h.json().get(pid)
            if not entry:
                continue
            for node_outputs in entry.get("outputs", {}).values():
                for img in node_outputs.get("images", []):
                    fname = img.get("filename")
                    sub = img.get("subfolder", "")
                    typ = img.get("type", "output")
                    if not fname:
                        continue
                    v = requests.get(
                        f"{endpoint}/view",
                        params={"filename": fname, "subfolder": sub, "type": typ},
                        timeout=30,
                    )
                    if v.status_code == 200:
                        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        local = save_dir / f"agent_{stamp}_{fname}"
                        local.write_bytes(v.content)
                        log_activity(
                            "self_pic",
                            f"Generated and saved {local.name}",
                            salience=0.6,
                            tags="heartbeat,self_pic,creative",
                        )
                        return {
                            "ok": True, "status": "complete", "content": str(local),
                            "category": CATEGORY, "proactive": False,
                            "detail": f"saved {local.name}",
                        }
        except Exception:
            continue

    return {
        "ok": False, "status": "complete", "content": "", "category": CATEGORY,
        "proactive": False, "detail": f"timeout waiting for {pid}",
    }
