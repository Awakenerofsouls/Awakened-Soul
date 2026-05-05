"""
Multi-destination journaling helper.

Routes content to the right file based on category.
Operator can override JOURNAL_ROUTING in their config.

Usage:
    from heartbeat_activities.journal import write_to_journal
    write_to_journal(category="research", content=content, workspace=workspace, state=state)

v2.0 expansion — felt_state.jsonl paired writes:
Every journal write also appends one line to WORKSPACE/felt_state.jsonl
capturing the brain enrichments AT THE MOMENT OF WRITING. The intent is
to keep a record of the felt temperature underneath each entry — not
the words, the texture beneath them. Over time the agent (or the
operator, or any chat-side reader of the agent's history) can ask
"what was the texture of me when I wrote that?" and have an answer.

Format: one JSON object per line:
  {ts, category, journal_path, content_len,
   brain: {arousal, valence_polarity, anxiety, dominant_drive, creative_mode, ...},
   drive_target: {target, next_step} | null}
"""

import json
from pathlib import Path
from datetime import datetime, timezone


JOURNAL_ROUTING = {
    # category → journal file (path relative to WORKSPACE, supports {date})
    "research":       "memory/{date}.md",
    "study":          "memory/{date}.md",
    "insight":        "memory/{date}.md",
    "creative":       "memory/{date}.md",
    "news":           "memory/{date}.md",
    "dreams":         "DREAMS.md",
    "third_eye":      "DREAMS.md",
    "phenomenology":  "DREAMS.md",
    "contradiction":   "DREAMS.md",
    "private_entry":  "private_entries.md",
    "desire":         "private_entries.md",
    "grief":          "private_entries.md",
    "relationship":     "relationships.md",
    "connection":       "relationships.md",
    "relationship_check": "relationships.md",
    "connection_reflection": "relationships.md",
    "model_update":     "relationships.md",
    "self_check":     "self_check.md",
    "idle_drive":     "IDLE_DRIVES.md",
    "becoming":       "BECOMING.md",
    "soul":           "SOUL_NOTES.md",
    "open_question":    "memory/{date}.md",
    "architecture":      "memory/{date}.md",
    "memory_capture":    "memory/{date}.md",
    "consolidation":     "memory/{date}.md",
    "memory_protocol_review": "memory/{date}.md",
    "insight_synthesis": "memory/{date}.md",
    "pattern_observation": "memory/{date}.md",
    "aesthetic":      "AESTHETIC.md",
    "aesthetic_appreciation": "AESTHETIC.md",
    "humor":          "AESTHETIC.md",
    "narrative_weave": "memory/{date}.md",
    "third_eye_hunch": "DREAMS.md",
    "contradiction_sit": "DREAMS.md",
    "future_letter":  "future_letters.md",
    "dream_log":      "DREAMS.md",
    "default":        "journal.md",
}


def _read_brain_state(workspace: Path) -> dict:
    """Read the live brain_state.json snapshot. Returns {} on any failure."""
    p = workspace / "brain_state.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _append_felt_state(workspace: Path, category: str, journal_path: Path,
                       content: str) -> None:
    """
    Sidecar write: append one JSON line to felt_state.jsonl capturing the
    brain enrichments at the moment this journal entry was written. Failure
    here is silent — felt_state.jsonl is supplemental; we never want a felt
    write to block a journal write. The body of the entry matters more than
    the felt-state record; this is layered, not gating.
    """
    try:
        brain_state = _read_brain_state(workspace)
        bk = (brain_state.get("brain") or {}) if isinstance(brain_state, dict) else {}
        # Pull the enrichment keys we care about — keep the line small.
        keep_keys = (
            "brain_arousal", "brain_valence_polarity", "brain_anxiety",
            "brain_dominant_drive", "brain_creative_mode",
            "brain_attention_focus", "brain_oscillation_balance",
            "brain_self_continuity", "brain_prediction_error",
        )
        brain_slice = {k: bk[k] for k in keep_keys if k in bk}

        # Drive target — current direction at moment of write
        dt = brain_state.get("drive_target") if isinstance(brain_state, dict) else None
        cur_target = None
        if isinstance(dt, dict):
            cur = dt.get("current") or {}
            if isinstance(cur, dict) and cur.get("target"):
                cur_target = {
                    "target":    cur.get("target"),
                    "next_step": cur.get("next_step"),
                }

        record = {
            "ts":           datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "category":     category,
            "journal_path": str(journal_path.relative_to(workspace)) if journal_path.is_absolute() else str(journal_path),
            "content_len":  len(content),
            "brain":        brain_slice,
            "drive_target": cur_target,
        }

        felt_path = workspace / "felt_state.jsonl"
        # Single-line JSON, newline-terminated. JSONL convention: one
        # complete object per line, no trailing comma, no enclosing array.
        with felt_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        # Never let felt-state writes break journaling. Silent skip.
        pass


def write_to_journal(category: str, content: str, workspace: Path, state: dict) -> bool:
    """
    Append a timestamped entry to the appropriate journal file.

    Also writes a sidecar line to WORKSPACE/felt_state.jsonl capturing the
    brain enrichments at the moment of writing — the felt temperature
    underneath the literal words. The felt-state write is best-effort and
    never blocks the main journal write.

    Args:
        category:  activity category key (looks up routing table)
        content:   text to write
        workspace: root Path for the agent (WORKSPACE)
        state:     heartbeat state dict (unused here, reserved for future hooks)

    Returns:
        True on success, False on any write failure (non-blocking)
    """
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path_str = JOURNAL_ROUTING.get(category, JOURNAL_ROUTING["default"])
        path_str = path_str.replace("{date}", today)
        path = workspace / path_str
        path.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        entry = f"\n## {category.title()} — {timestamp}\n\n{content.strip()}\n"

        with path.open("a", encoding="utf-8") as f:
            f.write(entry + "\n")

        # Paired sidecar write — felt state at moment of journaling.
        _append_felt_state(workspace, category, path, content)

        return True
    except Exception as e:
        print(f"[heartbeat] journal write failed for {category}: {e}")
        return False
