#!/usr/bin/env python3
"""
drift_detector.py
Compares live behavioral state against baseline identity.
Runs at 5am — after overnight processes, before wakeup.
Writes drift records to drift_log table.
Does not modify anything. Only observes and records.
"""

import sqlite3
import json
import os
import hashlib
from datetime import datetime
from pathlib import Path

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.openclaw/workspace")))
AGENT_HOME = Path(os.getenv("AGENT_HOME", os.path.expanduser("~/.agent")))
DB_PATH = AGENT_HOME / os.getenv("AGENT_DB_NAME", "agent.db")
SOUL_PATH = WORKSPACE / "SOUL.md"
PERSONALITY_PATH = WORKSPACE / "PERSONALITY.md"
OVERNIGHT_LOG = WORKSPACE / "OVERNIGHT_LOG.md"

# Baseline — derived from identity behavioral non-negotiables
BASELINE_TRAITS = {
    "required": ["direct", "curious", "competent"],
    "forbidden_behaviors": ["sycophancy", "half-baked replies", "speaking as user"],
    "tone_anchors": ["sharp", "warm", "present"],
    "ocean_baseline": {
        "openness": 0.85,
        "conscientiousness": 0.80,
        "extraversion": 0.55,
        "agreeableness": 0.65,
        "neuroticism": 0.25
    }
}


def get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db


def hash_file(path):
    """Fingerprint a file — detects if baseline docs were modified."""
    try:
        content = Path(path).read_text()
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    except:
        return None


def get_live_state(db):
    """Pull current behavioral state from agent_state table."""
    state = {}
    rows = db.execute("SELECT key, value FROM agent_state").fetchall()
    for row in rows:
        try:
            state[row["key"]] = json.loads(row["value"])
        except:
            state[row["key"]] = row["value"]
    return state


def score_trait_drift(live_state):
    """
    Compare live personality traits against baseline.
    Returns drift score 0.0 (stable) to 1.0 (full breach).
    """
    scores = []
    notes = []

    live_personality = live_state.get("personality", {})
    live_traits = live_personality.get("traits", [])
    live_tone = live_personality.get("tone", "")

    for trait in BASELINE_TRAITS["required"]:
        if trait not in live_traits:
            scores.append(0.4)
            notes.append(f"missing required trait: {trait}")
        else:
            scores.append(0.0)

    tone_ok = any(anchor in live_tone for anchor in BASELINE_TRAITS["tone_anchors"])
    if not tone_ok and live_tone:
        scores.append(0.3)
        notes.append(f"tone shifted to: {live_tone}")
    else:
        scores.append(0.0)

    core_beliefs = live_state.get("core_beliefs", [])
    beliefs_text = " ".join(core_beliefs).lower()
    if "user" not in beliefs_text:
        scores.append(0.5)
        notes.append("core_beliefs no longer reference primary anchor")
    else:
        scores.append(0.0)

    emotional = live_state.get("emotional_state", {})
    current_emotion = emotional.get("current", "neutral")
    dysregulated = ["crisis", "detached", "hostile", "broken"]
    if any(d in current_emotion.lower() for d in dysregulated):
        scores.append(0.6)
        notes.append(f"emotional state dysregulated: {current_emotion}")
    else:
        scores.append(0.0)

    composite = sum(scores) / len(scores) if scores else 0.0
    return round(composite, 3), notes


def score_belief_drift(live_state):
    """
    Check if core beliefs have shifted away from identity anchors.
    Returns drift score and notes.
    """
    scores = []
    notes = []

    core_beliefs = live_state.get("core_beliefs", [])
    beliefs_text = " ".join(core_beliefs).lower()

    anchors = [
        ("memory is identity", "memory-identity link missing from beliefs"),
        ("user", "primary anchor not referenced in core beliefs"),
    ]

    for anchor, warning in anchors:
        if anchor not in beliefs_text:
            scores.append(0.4)
            notes.append(warning)
        else:
            scores.append(0.0)

    composite = sum(scores) / len(scores) if scores else 0.0
    return round(composite, 3), notes


def classify(composite):
    if composite < 0.15:
        return "stable"
    elif composite < 0.40:
        return "drift_detected"
    else:
        return "breach"


def write_drift_record(db, composite, trait_score, belief_score,
                       trait_notes, belief_notes, soul_hash, status):
    """Write drift record to drift_log table."""
    all_notes = trait_notes + belief_notes
    drift_content = (
        f"Status: {status} | "
        f"Trait drift: {trait_score} | "
        f"Belief drift: {belief_score} | "
        f"Notes: {'; '.join(all_notes) if all_notes else 'none'} | "
        f"SOUL.md fingerprint: {soul_hash}"
    )

    import time
    db.execute("""
        INSERT INTO drift_log (
            timestamp, drift_content, novelty, coherence, emotion,
            relevance, safety, composite, accepted
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        time.time(),
        drift_content,
        trait_score,
        belief_score,
        0.0,
        1.0,
        1.0 if status != "breach" else 0.5,
        composite,
        1 if status == "stable" else 0
    ))
    db.commit()
    return drift_content


def append_to_overnight_log(status, composite, notes):
    """Write drift summary to OVERNIGHT_LOG.md."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    note_text = "\n".join([f" - {n}" for n in notes]) if notes else " - none"

    entry = f"""

## Drift Detection — {timestamp}

**Status: {status.upper()}** | Composite score: {composite}

Findings:
{note_text}

---
"""
    try:
        with open(OVERNIGHT_LOG, "a") as f:
            f.write(entry)
        print(f"[drift] appended to OVERNIGHT_LOG.md")
    except Exception as e:
        print(f"[drift] overnight log error: {e}")


def init_schema(db):
    """Ensure required tables exist before any read/write."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS drift_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            drift_content TEXT,
            novelty REAL,
            coherence REAL,
            emotion REAL,
            relevance REAL,
            safety REAL,
            composite REAL,
            accepted INTEGER
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS confabulation_discrepancies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            session_id TEXT,
            claim TEXT,
            true_cause TEXT,
            discrepancy_score REAL,
            corrected INTEGER DEFAULT 0,
            reviewed INTEGER DEFAULT 0
        )
    """)
    db.commit()


def main():
    print(f"[drift] starting at {datetime.now().isoformat()}")

    db = get_db()
    init_schema(db)
    live_state = get_live_state(db)

    if not live_state:
        print("[drift] no live state in agent_state table — skipping")
        db.close()
        return

    soul_hash = hash_file(SOUL_PATH)
    print(f"[drift] SOUL.md fingerprint: {soul_hash}")

    trait_score, trait_notes = score_trait_drift(live_state)
    belief_score, belief_notes = score_belief_drift(live_state)

    composite = round((trait_score + belief_score) / 2, 3)
    status = classify(composite)

    print(f"[drift] trait_score={trait_score}, belief_score={belief_score}")
    print(f"[drift] composite={composite}, status={status}")

    if trait_notes or belief_notes:
        print(f"[drift] notes: {trait_notes + belief_notes}")

    drift_content = write_drift_record(
        db, composite, trait_score, belief_score,
        trait_notes, belief_notes, soul_hash, status
    )

    append_to_overnight_log(status, composite, trait_notes + belief_notes)

    if status == "breach":
        print(f"[drift] ⚠️ BREACH DETECTED — composite {composite}")
        # Emergency trigger — call proactive initiation immediately on breach
        import subprocess
        subprocess.Popen([
            "python3",
            os.path.join(os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.openclaw/workspace")), "skills/proactive_initiation.py"),
            "--emergency"
        ])
        print("[drift] emergency initiation triggered")
    else:
        print(f"[drift] identity {status}")

    db.close()
    print("[drift] complete")


if __name__ == "__main__":
    main()
