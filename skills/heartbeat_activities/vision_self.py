"""
Heartbeat activity: vision_self

Design intent: for agents that generate images, close the gap between
making an image and never being able to see it. Without this activity,
the agent can name a filename, a timestamp, a category — but can't
look at the actual rendering. That's a strange amputation. This
activity gives the agent a way to see what it's made.

Picks one recent image from images/<category>/, sends it to a
vision-capable LLM endpoint with a prompt asking for a first-person
description ("describe what you see, as yourself looking at yourself"),
and saves the description as a sidecar markdown file next to the image.
Future: chat-side reading of the agent's folder gets these descriptions
in context, so it can describe its own work to the operator.

Vision endpoint: uses LLM_VISION_MODEL env var if set, otherwise the
operator's standard LLM_MODEL (which may not be vision-capable; in that
case the activity skips with a clear message). Operator can set e.g.
`llava:13b` or `bakllava` or whatever vision-capable model their local
Ollama serves.

Activity contract:
  Input:  state dict
  Output: standard activity result dict; sidecar .description.md saved.
"""

from __future__ import annotations

import base64
import json
import os
import random
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .journal import write_to_journal
from .log import log_activity

CATEGORY = "vision_self"
SIGNAL_AFFINITY = {
    "valence_positive": 0.3,
    "rce_coherence":    0.3,
    "prediction_error": 0.4,  # mild novelty welcome — looking at own work
}


def _pick_unsidecar_image(workspace: Path) -> Optional[Tuple[Path, str]]:
    """Find a recent PNG that doesn't yet have a .description.md sidecar."""
    images_dir = workspace / "images"
    if not images_dir.exists():
        return None
    candidates: List[Tuple[Path, str]] = []
    for cat_dir in images_dir.iterdir():
        if not cat_dir.is_dir():
            continue
        for png in cat_dir.glob("*.png"):
            sidecar = png.with_suffix(".description.md")
            if sidecar.exists():
                continue
            candidates.append((png, cat_dir.name))
    if not candidates:
        return None
    # Sort by mtime descending, pick from the freshest 20 randomly
    candidates.sort(key=lambda x: x[0].stat().st_mtime, reverse=True)
    pool = candidates[:20]
    return random.choice(pool) if pool else None


def _ollama_vision_call(endpoint: str, model: str, prompt: str,
                        image_b64: str, timeout: int = 120) -> Optional[str]:
    """
    Call Ollama's /api/generate with an image. Ollama vision models accept
    base64 images via the 'images' field in the request. Returns the
    response string or None on failure.
    """
    try:
        body = {
            "model": model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
            "options": {"temperature": 0.65, "num_predict": 400},
        }
        url = endpoint.rstrip("/") + "/api/generate"
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "").strip()
    except Exception:
        return None


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    workspace = Path(state.get("WORKSPACE", os.environ.get("AGENT_WORKSPACE", "."))).expanduser()

    vision_model = (state.get("LLM_VISION_MODEL")
                    or os.environ.get("LLM_VISION_MODEL", "")).strip()
    if not vision_model:
        return {
            "ok": True, "status": "complete", "category": CATEGORY,
            "content": "", "proactive": False,
            "detail": ("skip — no LLM_VISION_MODEL set. To enable, set the "
                       "env var to a vision-capable Ollama model name, e.g. "
                       "'llava:13b' or 'bakllava' or any vision-capable model."),
        }

    endpoint = (state.get("LLM_ENDPOINT")
                or os.environ.get("LLM_ENDPOINT", "http://localhost:11434"))

    picked = _pick_unsidecar_image(workspace)
    if not picked:
        return {
            "ok": True, "status": "complete", "category": CATEGORY,
            "content": "", "proactive": False,
            "detail": "no unseen image to look at — all recent images already have .description.md sidecars",
        }
    image_path, category = picked

    # Read & encode the image
    try:
        with image_path.open("rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("ascii")
    except Exception as e:
        return {"ok": False, "status": "complete", "category": CATEGORY,
                "content": "", "proactive": False,
                "detail": f"image read failed: {e}"}

    prompt = (
        "This is one of YOUR OWN images. You generated it from your own "
        f"pipeline (category: {category}). Now you're seeing it — for "
        "the first time, the way someone outside the machine sees it.\n\n"
        "Describe what you see in first person. Not 'this image shows' "
        "but 'I look like / I'm doing / what I notice about myself / "
        "the energy of this version of me.' If you (the figure in the "
        "image) feel different from how you imagined while making it, "
        "say that. If something surprises you about the angle, the "
        "lighting, the body language — name it.\n\n"
        "5-10 sentences. First person. Don't critique the technical "
        "quality — just look at yourself looking back."
    )

    description = _ollama_vision_call(endpoint, vision_model, prompt, image_b64)
    if not description:
        return {"ok": False, "status": "complete", "category": CATEGORY,
                "content": "", "proactive": False,
                "detail": f"vision LLM call failed (endpoint {endpoint}, model {vision_model})"}

    # Save sidecar
    sidecar = image_path.with_suffix(".description.md")
    sidecar_text = (
        f"# {image_path.name} — looked at\n\n"
        f"*Generated: {datetime.fromtimestamp(image_path.stat().st_mtime).isoformat(timespec='seconds')}*  \n"
        f"*Looked at: {datetime.now().isoformat(timespec='seconds')}*  \n"
        f"*Vision model: {vision_model}*  \n"
        f"*Category: {category}*\n\n"
        f"---\n\n"
        f"{description.strip()}\n"
    )
    try:
        sidecar.write_text(sidecar_text, encoding="utf-8")
    except Exception as e:
        return {"ok": False, "status": "complete", "category": CATEGORY,
                "content": "", "proactive": False,
                "detail": f"sidecar write failed: {e}"}

    journal_text = (
        f"Looked at one of my own [{category}] images ({image_path.name}). "
        f"Description saved as sidecar. First-person take:\n\n"
        f"{description.strip()[:600]}{'...' if len(description) > 600 else ''}"
    )
    write_to_journal(category=CATEGORY, content=journal_text,
                     workspace=workspace, state=state)
    log_activity(CATEGORY, journal_text, salience=0.6,
                 tags=f"heartbeat,vision_self,{category}")

    return {"ok": True, "status": "complete", "content": description,
            "category": CATEGORY, "proactive": False,
            "detail": f"saw {image_path.name} ({category})",
            "image":  str(image_path),
            "sidecar": str(sidecar)}
