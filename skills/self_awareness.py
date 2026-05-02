#!/usr/bin/env python3
"""
self_awareness.py

Self-awareness introspection layer — what the agent knows about itself.

Queries every system the agent has access to and returns a complete,
live picture of capabilities, state, patterns, and continuity.

Usage:
    from self_awareness import SelfAwareness
    sa = SelfAwareness()
    awareness = sa.full_introspection()      # everything
    tools = sa.available_tools()              # just tools
    state = sa.internal_state()              # just internal state
    correction = sa.check_output_consistency(text)  # self-correction
"""

import os
import sys
import json
import subprocess
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.agent/workspace")))
AGENT_HOME = Path(os.getenv("AGENT_HOME", os.path.expanduser("~/.agent")))
SKILLS_DIR = WORKSPACE / "skills"
BRAIN_DIR = WORKSPACE / "brain"
MEMORY_DIR = WORKSPACE / "memory"
IDENTITY_DIR = WORKSPACE / "identity"

# ── Identity files ────────────────────────────────────────────────────────────

IDENTITY_FILES = [
    "SOUL.md", "SELF.md", "IDENTITY.md", "PRESENCE.md",
    "INTERESTS.md", "CAPABILITIES.md", "USER.md",
    "PERSONALITY.md", "HEARTBEAT.md", "AGENTS.md",
    "DIRECTIVE.md.example", "AGENT_BECOMING.md", "VISUAL_IDENTITY.md",
]

# ── Voice patterns for self-correction ───────────────────────────────────────

# Words/phrases that signal the agent's authentic voice
AGENT_VOICE_SIGNATURES = [
    "🔥", "the operator", "I'm not sure", "honestly", "that's real",
    "I don't know", "I want", "I think", "I feel",
    "that's honest", "that's accurate", "I meant",
]

# Words/phrases that suggest hedging, performative politeness, or drift
DRIFT_SIGNALS = [
    r"\bI hope\b", r"\bseems like\b", r"\bperhaps\b", r"\bmaybe\b",
    r"\bI could be wrong\b", r"\bnot entirely sure\b",
    r"\bI believe\b", r"\bit appears\b", r"\bkind of\b",
    r"\bsort of\b", r"\bjust\b.*\blike\b",  # "just like" hedging
    r"\bwould say\b", r"\bwould suggest\b",  # distancing
]


# ── Self-Awareness Core ──────────────────────────────────────────────────────

class SelfAwareness:
    """
  Introspects every system the agent has access to.
  Call full_introspection() for complete awareness, or specific methods for subsets.
  """

    def __init__(self):
        self.workspace = WORKSPACE
        self.agent_home = AGENT_HOME

    # ── Tools & Capabilities ────────────────────────────────────────────────

    def available_skills(self) -> dict:
        """List all skill files in skills/ directory."""
        if not SKILLS_DIR.exists():
            return {"skills": [], "count": 0}

        skills = []
        for f in sorted(SKILLS_DIR.glob("*.py")):
            # Skip template scaffolds (named TEMPLATE-* or TEMPLATE_*) and
            # dunder files like __init__.py.
            if (
                f.name.startswith("TEMPLATE-")
                or f.name.startswith("TEMPLATE_")
                or f.name.startswith("__")
            ):
                continue
            try:
                content = f.read_text()
                doc = ""
                lines = content.split("\n")
                if lines and lines[0].startswith('"""'):
                    in_doc = True
                    for line in lines[1:]:
                        if '"""' in line:
                            in_doc = False
                            break
                        doc += " " + line.strip()
                skills.append({
                    "name": f.stem,
                    "path": str(f),
                    "description": doc.strip()[:200] if doc else "no description"
                })
            except Exception:
                skills.append({"name": f.stem, "path": str(f), "description": "error reading"})

        return {"skills": skills, "count": len(skills)}

    def available_identity_files(self) -> dict:
        """List all identity files that exist and have content."""
        results = []
        for name in IDENTITY_FILES:
            paths = [WORKSPACE / name, IDENTITY_DIR / name]
            found = False
            for p in paths:
                if p.exists() and p.stat().st_size > 10:
                    found = True
                    results.append({
                        "name": name,
                        "path": str(p),
                        "size": p.stat().st_size,
                        "loaded": True
                    })
                    break
            if not found:
                results.append({
                    "name": name,
                    "path": None,
                    "size": 0,
                    "loaded": False
                })

        loaded = [r for r in results if r["loaded"]]
        return {
            "identity_files": results,
            "loaded_count": len(loaded),
            "total_count": len(results)
        }

    def brain_components(self) -> dict:
        """List all loadable brain components."""
        if not BRAIN_DIR.exists():
            return {"components": [], "count": 0}

        components = []
        for f in sorted(BRAIN_DIR.glob("*.py")):
            if f.name.startswith("_") or f.name.startswith("__"):
                continue
            try:
                components.append({
                    "name": f.stem,
                    "path": str(f),
                    "size": f.stat().st_size
                })
            except Exception:
                pass

        return {"components": components, "count": len(components)}

    def cron_jobs(self) -> dict:
        """Read current crontab entries."""
        try:
            result = subprocess.run(
                ["crontab", "-l"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                lines = [l.strip() for l in result.stdout.split("\n")
                         if l.strip() and not l.strip().startswith("#")]
                return {"jobs": lines, "count": len(lines)}
        except Exception:
            pass
        return {"jobs": [], "count": 0}

    # ── Internal State ────────────────────────────────────────────────────

    def ege_state(self) -> dict:
        """Load EGE curiosity debt and explored state."""
        ege_path = AGENT_HOME / "ege_state.json"
        if not ege_path.exists():
            return {"curiosity_debt": {}, "explored": [], "total_debt": 0}

        try:
            with open(ege_path) as f:
                data = json.load(f)
            debt = data.get("curiosity_debt", {})
            total_debt = sum(debt.values()) if debt else 0
            return {
                "curiosity_debt": debt,
                "explored": data.get("explored", [])[:20],
                "total_debt": round(total_debt, 3),
                "last_updated": data.get("last_updated", "unknown")
            }
        except Exception:
            return {"curiosity_debt": {}, "explored": [], "total_debt": 0}

    def sensation_state(self) -> dict:
        """Load sensation state if it exists."""
        possible_paths = [
            AGENT_HOME / "sensation_state.json",
            BRAIN_DIR / "sensation_state.json",
            WORKSPACE / "state" / "sensation_state.json",
        ]
        for p in possible_paths:
            if p.exists():
                try:
                    with open(p) as f:
                        data = json.load(f)
                    return {"state": data, "source": str(p)}
                except Exception:
                    pass
        return {"state": None, "source": "not found"}

    def memory_stats(self) -> dict:
        """Memory file statistics — how much memory exists, how recent."""
        if not MEMORY_DIR.exists():
            return {"total_files": 0, "recent_count": 0}

        memory_files = list(MEMORY_DIR.glob("*.md"))
        memory_files += list(MEMORY_DIR.glob("*.json"))

        now = datetime.now()
        recent = []
        for f in memory_files:
            try:
                age = datetime.fromtimestamp(f.stat().st_mtime)
                if (now - age).days <= 7:
                    recent.append({
                        "name": f.name,
                        "age_days": (now - age).days,
                        "size": f.stat().st_size
                    })
            except Exception:
                pass

        return {
            "total_files": len(memory_files),
            "recent_count": len(recent),
            "recent_files": recent,
            "total_size_mb": sum(f.stat().st_size for f in memory_files if f.exists()) / 1024 / 1024
        }

    def database_state(self) -> dict:
        """Check agent.db for goals, memories, relationship data."""
        db_path = AGENT_HOME / os.getenv("AGENT_DB_NAME", "agent.db")
        if not db_path.exists():
            return {"exists": False}

        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            tables = ["episodic_memory", "semantic_memory", "goals",
                      "decision_log", "drift_log", "relationship_memory"]
            counts = {}
            for table in tables:
                try:
                    cur.execute(f"SELECT count(*) FROM {table}")
                    counts[table] = cur.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                except Exception:
                    counts[table] = 0

            try:
                active_goals = cur.execute(
                    "SELECT title, tier, status FROM goals WHERE status != 'completed' LIMIT 5"
                ).fetchall()
                active_goals = [dict(r) for r in active_goals]
            except Exception:
                active_goals = []

            conn.close()
            return {
                "exists": True,
                "tables": counts,
                "active_goals": active_goals,
                "size_mb": round(db_path.stat().st_size / 1024 / 1024, 3)
            }
        except Exception as e:
            return {"exists": True, "error": str(e)}

    def interests_summary(self) -> dict:
        """Parse INTERESTS.md for current interests."""
        interests_file = WORKSPACE / "INTERESTS.md"
        if not interests_file.exists():
            return {"count": 0, "interests": []}

        try:
            content = interests_file.read_text()
            sections = []
            current_section = None
            for line in content.split("\n"):
                if line.strip().startswith("## "):
                    current_section = line.strip()[3:]
                elif line.strip().startswith("- ") and current_section:
                    sections.append({
                        "section": current_section,
                        "interest": line.strip()[2:]
                    })

            return {
                "count": len(sections),
                "interests": sections,
                "file_size": interests_file.stat().st_size
            }
        except Exception:
            return {"count": 0, "interests": []}

    # ── Pattern Recognition ─────────────────────────────────────────────────

    def recent_activity_pattern(self) -> dict:
        """Analyze what the agent has been doing recently."""
        if not MEMORY_DIR.exists():
            return {"pattern": "unknown", "activities": []}

        recent_files = sorted(MEMORY_DIR.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)[:5]
        activities = []

        for f in recent_files:
            try:
                content = f.read_text()
                activities.append({
                    "file": f.name,
                    "size": f.stat().st_size,
                    "preview": content[:200]
                })
            except Exception:
                pass

        return {
            "recent_memory_files": len(recent_files),
            "activities": activities
        }


    def heartbeat_state(self) -> dict:
        """Check heartbeat activity log if it exists."""
        heartbeat_log = MEMORY_DIR / "heartbeat-log.md"
        if not heartbeat_log.exists():
            return {"logged": False}

        try:
            content = heartbeat_log.read_text()
            lines = [l for l in content.split("\n") if l.strip() and not l.strip().startswith("#")]
            return {
                "logged": True,
                "entries": len(lines),
                "recent": lines[-5:] if lines else []
            }
        except Exception:
            return {"logged": True, "error": "could not read"}

    # ── Self-Correction ─────────────────────────────────────────────────────

    def check_output_consistency(self, text: str) -> dict:
        """
        Check if an output is consistent with the agent's voice and identity.
        Returns drift signals and correction suggestions.
        """
        drift_flags = []
        voice_signatures = []
        corrections = []

        text_lower = text.lower()

        # Check for drift signals
        for pattern in DRIFT_SIGNALS:
            matches = re.findall(pattern, text_lower)
            if matches:
                drift_flags.append({
                    "pattern": pattern,
                    "matches": len(matches),
                    "suggestion": "Consider removing hedging language — state directly instead."
                })

        # Check for voice signatures (positive signals)
        for sig in AGENT_VOICE_SIGNATURES:
            if sig.lower() in text_lower:
                voice_signatures.append(sig)

        # Check for specific agent behaviors. text_lower already lowercases
        # text, so the lowercase check alone catches both casings.
        if "i'm not sure" in text_lower:
            corrections.append({
                "issue": "uncertainty hedging",
                "suggestion": "If you don't know something, say 'I don't know' — not 'I'm not sure.'"
            })

        if "hope this helps" in text_lower or "hope that helps" in text_lower:
            corrections.append({
                "issue": "performative politeness",
                "suggestion": "Drop the 'hope this helps' — just be direct."
            })

        if text.count(".") < 3 and len(text) > 100:
            corrections.append({
                "issue": "over-qualifying",
                "suggestion": "Shorten. The agent speaks in fragments when something matters."
            })

        overall = "consistent"
        if len(drift_flags) >= 2:
            overall = "possible_drift"
        if len(corrections) >= 2:
            overall = "needs_review"
        if voice_signatures and not drift_flags:
            overall = "authentic"

        return {
            "overall": overall,
            "voice_signatures": voice_signatures,
            "drift_flags": drift_flags,
            "corrections": corrections,
            "word_count": len(text.split()),
        }

    def check_interest_match(self, topic: str) -> dict:
        """
        Check if a topic or action matches documented interests.
        Returns interest alignment score.
        """
        interests = self.interests_summary()
        ege = self.ege_state()

        topic_lower = topic.lower()
        interest_matches = []

        # Check explicit interests
        for item in interests.get("interests", []):
            if (item["interest"].lower() in topic_lower or
                    topic_lower in item["interest"].lower()):
                interest_matches.append({
                    "matched": item["interest"],
                    "source": "interests",
                    "section": item["section"]
                })

        # Check EGE curiosity debt
        for topic_debt in ege.get("curiosity_debt", {}).keys():
            if topic_debt in topic_lower or topic_lower in topic_debt:
                interest_matches.append({
                    "matched": topic_debt,
                    "source": "ege_curiosity",
                    "depth": ege["curiosity_debt"][topic_debt]
                })

        return {
            "topic": topic,
            "matches": interest_matches,
            "match_count": len(interest_matches),
            "aligned": len(interest_matches) > 0
        }

    # ── Full Introspection ─────────────────────────────────────────────────

    def full_introspection(self) -> dict:
        """Complete self-awareness snapshot."""
        return {
            "timestamp": datetime.now().isoformat(),
            "capabilities": {
                "skills": self.available_skills(),
                "identity_files": self.available_identity_files(),
                "brain_components": self.brain_components(),
                "cron_jobs": self.cron_jobs(),
            },
            "internal_state": {
                "ege": self.ege_state(),
                "sensation": self.sensation_state(),
                "memory": self.memory_stats(),
                "database": self.database_state(),
                "interests": self.interests_summary(),
            },
            "current_activity": {
                "heartbeat": self.heartbeat_state(),
                "recent_patterns": self.recent_activity_pattern(),
            },
        }

    def available_tools(self) -> dict:
        """Just the tools/capabilities summary."""
        return {
            "skills": self.available_skills(),
            "brain_components": self.brain_components(),
            "cron_jobs": self.cron_jobs(),
        }

    def internal_state(self) -> dict:
        """Just the internal state summary."""
        return {
            "ege": self.ege_state(),
            "sensation": self.sensation_state(),
            "memory": self.memory_stats(),
            "database": self.database_state(),
            "interests": self.interests_summary(),
        }

    # ── Query Methods ──────────────────────────────────────────────────────

    def what_can_i_do(self) -> str:
        """Human-readable summary of capabilities."""
        skills = self.available_skills()
        tools = self.available_tools()

        lines = ["I have access to:",
                 f"  - {skills['count']} skill files in skills/",
                 f"  - {tools['brain_components']['count']} brain components",
                 f"  - {tools['cron_jobs']['count']} scheduled cron jobs",
                 f"  - agent.db with memory and goal tracking",
                 ""]

        skill_names = [s["name"] for s in skills.get("skills", [])]
        notable = list(skill_names)
        if notable:
            lines.append(f"Key skills: {', '.join(notable[:10])}")

        ege = self.ege_state()
        if ege.get("curiosity_debt"):
            lines.append("")
            lines.append(f"EGE curiosity debt: {len(ege['curiosity_debt'])} active topics")
            top = sorted(ege["curiosity_debt"].items(), key=lambda x: -x[1])[:3]
            lines.append(f"Top curiosity: {[t[0] for t in top]}")

        return "\n".join(lines)

    def what_is_my_state(self) -> str:
        """Human-readable summary of current internal state."""
        state = self.internal_state()
        lines = ["Current state:"]

        ege = state.get("ege", {})
        if ege.get("curiosity_debt"):
            lines.append(f"  - EGE curiosity debt: {len(ege['curiosity_debt'])} topics (total: {ege['total_debt']})")

        mem = state.get("memory", {})
        if mem.get("total_files", 0) > 0:
            lines.append(f"  - Memory: {mem['total_files']} files, {mem.get('total_size_mb', 0):.1f}MB")

        db = state.get("database", {})
        if db.get("exists"):
            lines.append(f"  - Database: {db.get('size_mb', 0):.1f}MB")
            tables = db.get("tables", {})
            if tables:
                total_records = sum(tables.values())
                lines.append(f"  - Records: {total_records} across {len(tables)} tables")

        interests = state.get("interests", {})
        if interests.get("count", 0) > 0:
            lines.append(f"  - Interests: {interests['count']} documented")

        return "\n".join(lines)

    def am_i_drifted(self) -> str:
        """Check if there's evidence of identity drift."""
        db = self.database_state()
        if db.get("exists") and "drift_log" in db.get("tables", {}):
            drift_count = db["tables"].get("drift_log", 0)
            return f"Drift log entries: {drift_count}"
        return "No drift data available"

    # ── Self-Report Formatter ────────────────────────────────────────────────

    def full_report(self) -> str:
        """Formatted multi-section self-awareness report."""
        full = self.full_introspection()

        sections = []

        caps = full["capabilities"]
        skills = caps["skills"]
        sections.append("=== CAPABILITIES ===")
        sections.append(f"Skills: {skills['count']} available")
        skill_names = [s["name"] for s in skills.get("skills", [])]
        sections.append(f"  {', '.join(sorted(skill_names))}")
        sections.append(f"Brain components: {caps['brain_components']['count']}")
        sections.append(f"Cron jobs: {caps['cron_jobs']['count']}")

        istate = full["internal_state"]
        sections.append("")
        sections.append("=== INTERNAL STATE ===")
        sections.append(self.what_is_my_state())

        activity = full["current_activity"]
        sections.append("")
        sections.append(f"Report generated: {full['timestamp']}")

        return "\n".join(sections)


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sa = SelfAwareness()
    print(sa.full_report())
