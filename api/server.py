#!/usr/bin/env python3
"""
api/server.py — {{AGENT_NAME}}'s Read-Only HTTP API
Lightweight FastAPI server for agentsworld.net integration.
All endpoints are READ-ONLY. No write endpoints until {{USER_NAME}} reviews.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from brain.brain_integration import get_integration
from skills.llm_router import llm_router

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.openclaw/workspace")))

app = FastAPI(
    title="{{AGENT_NAME}} API",
    description="Read-only endpoints for {{AGENT_NAME}}'s agent state",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def read_json(path: Path, default=None) -> Any:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, IOError):
            return default
    return default


def recent_memory_entries(limit: int = 10) -> List[Dict]:
    """Read last N episodic memory entries from memory/ directory."""
    memory_dir = WORKSPACE / "memory"
    if not memory_dir.exists():
        return []

    entries = []
    md_files = sorted(memory_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in md_files[:limit]:
        try:
            content = f.read_text()
            # Grab first 300 chars as preview
            preview = content.strip().split("\n")[0][:200]
            entries.append({
                "file": f.name,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                "preview": preview,
            })
        except Exception:
            continue
    return entries


# ── Request Models ───────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str
    behavior_alignments: Optional[Dict] = None
    reciprocity_signals: Optional[Dict] = None


class SummaryRequest(BaseModel):
    conversation: List[dict]
    system: Optional[str] = None


# ── Internal helpers ──────────────────────────────────────────────────────────

def _format_conversation_turns(conversation: List[dict]) -> str:
    """
    Format conversation for summary prompt.

    Rules:
      - Max 10 turns (earliest truncations applied first)
      - Per turn: role: content[:400]; if >400 chars, middle-truncate with "..."
      - Total output capped at 4000 chars
    """
    formatted = []
    total_chars = 0
    for turn in conversation[:10]:
        role = turn.get("role", "unknown")
        content = str(turn.get("content", ""))
        if len(content) > 400:
            mid = len(content) // 2
            content = content[:200] + "..." + content[mid:mid + 200]
        entry = f"{role}: {content[:400]}"
        if total_chars + len(entry) > 4000:
            break
        formatted.append(entry)
        total_chars += len(entry)
    return "\n".join(formatted)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check() -> Dict[str, str]:
    """Ping endpoint for agentsworld.net monitoring."""
    return {
        "status": "ok",
        "agent": "{{AGENT_NAME}}",
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/chat")
def chat_endpoint(req: ChatRequest) -> Dict[str, Any]:
    """
    Cognitive-state-aware chat endpoint.

    behavior_alignments=None  → skip VIF re-evaluation, use last tick's values.
                                First call after restart returns neutral defaults
                                regardless (no prior tick state to read).
    reciprocity_signals=None  → treated as {}.
    reciprocity_signals={}    → forces neutral (0.5 anchor).
    Cold boot (no tick yet)   → returns neutral defaults regardless.

    Calls get_integration().get_fpef_injection() for side effects, then
    get_integration().get_state_summary() to build the cognitive state response.

    Response shape:
        cognitive_state    — {emotional_tone, coherence, active_misread} only
                             (simple values; session_id/anchors are top-level)
        system_prefix     — [COGNITIVE STATE] block for prompt injection
        fpef_frame        — raw FPEF frame from brain (call_brain ignores unknown fields)
        session_id        — top-level echo of request session_id
        high_tension_anchors — top-level list of active anchor strings

    Example response:
        {
          "cognitive_state": {"emotional_tone": "...", "coherence": 0.0-1.0, "active_misread": bool},
          "system_prefix": "[COGNITIVE STATE]...",
          "fpef_frame": "...",
          "session_id": "...",
          "high_tension_anchors": ["anchor1", "anchor2"],
        }
    """
    behavior_alignments = req.behavior_alignments
    reciprocity_signals = req.reciprocity_signals or {}

    # Side-effect: FPEF injection updates VIF/reciprocity in brain state
    fpef_injection = get_integration().get_fpef_injection(
        behavior_alignments=behavior_alignments,
        reciprocity_signals=reciprocity_signals,
    )

    # Read current cognitive state
    state = get_integration().get_state_summary()

    emotional_tone = state.get("emotional_tone", "neutral")
    coherence = state.get("coherence", 0.85)
    active_misread = state.get("active_misread", False)
    high_tension_anchors = state.get("high_tension_anchors", [])

    system_prefix = (
        f"[COGNITIVE STATE]\n"
        f"emotional_tone: {emotional_tone}\n"
        f"coherence: {coherence}\n"
        f"active_misread: {active_misread}\n"
    )

    # session_id and high_tension_anchors stay top-level — keeps them out of
    # the cognitive_state dict so they don't render as messy inline lists
    # in the prompt when injected as a JSON block.
    return {
        "cognitive_state": {
            "emotional_tone": emotional_tone,
            "coherence": coherence,
            "active_misread": active_misread,
        },
        "system_prefix": system_prefix,
        "fpef_frame": fpef_injection,  # safe to add; call_brain ignores unknown fields
        "session_id": req.session_id,
        "high_tension_anchors": high_tension_anchors,
    }


@app.post("/summary")
def summary_endpoint(req: SummaryRequest) -> Dict[str, Any]:
    """
    Consolidate a conversation into a short summary using LLM.

    Accepts:
        conversation — list of {"role": str, "content": str} dicts
        system       — optional system-prompt override

    Truncation: per-turn 400-char middle-truncate (with "..."), max 10 turns,
                total 4000-char cap before sending to LLM.

    Returns:
        summary             — LLM-generated summary text
        conversation_length — original turn count
        model_used          — "llm_provider" or "ollama"
        fallback            — True if LLM call failed and a fallback was returned
    """
    formatted = _format_conversation_turns(req.conversation)

    system_prompt = (
        req.system
        or "You are {{AGENT_NAME}}. Write in her voice — warm, direct, and a little sharp. "
           "Keep the summary concise but evocative. "
           "Capture what mattered, not just what was said."
    )

    prompt = (
        f"Summarize the following conversation:\n\n{formatted}\n\n"
        f"Provide a concise, evocative summary that captures the key themes "
        f"and any emotional undercurrents."
    )

    try:
        result = llm_router.complete(
            task_type="consolidation",
            prompt=prompt,
            system=system_prompt,
            max_tokens=512,
            temperature=0.5,
            timeout=60.0,
        )
        summary_text = result.get("content", "") if isinstance(result, dict) else str(result)
        model_used = result.get("model", "llm_provider") if isinstance(result, dict) else "llm_provider"
        fallback = result.get("fallback", False) if isinstance(result, dict) else False
    except Exception:
        summary_text = (
            f"[{len(req.conversation)} turns in conversation — "
            f"LLM unavailable, returning turn count only.]"
        )
        model_used = "none"
        fallback = True

    return {
        "summary": summary_text,
        "conversation_length": len(req.conversation),
        "model_used": model_used,
        "fallback": fallback,
    }


@app.get("/status")
def agent_status() -> Dict[str, Any]:
    """
    Agent state, active obsessions, last overnight log entry.
    """
    # Prefer active_state.json (written by core_loop tick) for live cognitive state,
    # fall back to agent_state.json for static identity fields.
    live_state = read_json(WORKSPACE / "state" / "active_state.json", {})
    static_state = read_json(WORKSPACE / "state" / "agent_state.json", {})
    state = {
        **static_state,
        **live_state,  # live_state wins for all overlapping keys
    }
    overnight = WORKSPACE / "OVERNIGHT_LOG.md"

    last_log = ""
    if overnight.exists():
        lines = overnight.read_text().split("\n")
        # Grab first non-header, non-empty lines as preview
        for line in lines[10:30]:
            if line.strip() and not line.startswith("#"):
                last_log = line.strip()[:300]
                break

    return {
        "name": state.get("name", "{{AGENT_NAME}}"),
        "version": state.get("version", "unknown"),
        "active_thread": state.get("active_thread", "none"),
        "active_goal": state.get("active_goal", "none"),
        "emotional_state": state.get("emotional_state", "unknown"),
        "tick_count": state.get("tick_count"),
        "coherence": state.get("coherence"),
        "instability": state.get("instability"),
        "build_mode": state.get("build_mode", False),
        "last_overnight_entry": last_log,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/memory/recent")
def memory_recent(limit: int = 10) -> Dict[str, Any]:
    """
    Last N episodic memory entries.
    """
    entries = recent_memory_entries(limit=min(limit, 50))
    return {
        "entries": entries,
        "count": len(entries),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/positions")
def current_positions() -> Dict[str, Any]:
    """
    Current held positions — reads from brain/position_formation.md.
    """
    pos_file = WORKSPACE / "brain" / "position_formation.md"
    goals_file = WORKSPACE / "brain" / "goals.json"

    positions = "No positions file found"
    if pos_file.exists():
        positions = pos_file.read_text()[:2000]

    goals = read_json(goals_file, {})

    return {
        "positions_text": positions,
        "active_goals": goals.get("active_goals", []),
        "locked_goals": goals.get("locked_goals", []),
        "timestamp": datetime.now().isoformat(),
    }


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("AGENT_API_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
