#!/usr/bin/env python3
"""
Contradiction Resolution — the agent's Nightly Conflict Resolver
Scheduled via cron / launchd; the timezone is read from $AGENT_TZ
(defaults to UTC). Pick whatever overnight slot fits your schedule.

Reads memory/contradictions.json,
resolves resolvable conflicts via LLM,
flags unresolvable ones for the operator.
Writes summary to OVERNIGHT_LOG.md.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.agent/workspace")))
OVERNIGHT_LOG = WORKSPACE / "OVERNIGHT_LOG.md"
CONTRADICTIONS_FILE = WORKSPACE / "memory" / "contradictions.json"
PENDING_FOR_USER = WORKSPACE / "memory" / "pending_for_user.md"
SLEEP_RUNS = WORKSPACE / "brain" / "sleep_runs.json"

LOCAL_TZ = os.getenv("AGENT_TZ", "UTC")

sys.path.insert(0, str(WORKSPACE))
from brain.llm_router import llm_extract
from brain.three_tier_memory import memory_write, memory_edit

# ── Timestamp helpers ─────────────────────────────────────────────────────────

def get_local_time():
    from datetime import datetime as dt
    import zoneinfo
    local_tz = zoneinfo.ZoneInfo(LOCAL_TZ)
    return dt.now(local_tz).strftime("%Y-%m-%d %H:%M:%S")


def load_json(path, default=None):
    if Path(path).exists():
        try:
            return json.loads(Path(path).read_text())
        except Exception:
            return default or {}
    return default or {}


def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2))


# ── Logging ───────────────────────────────────────────────────────────────────

def log_to_overnight_log(process_name, status, duration, output, changes, carry_forward, errors=None):
    entry = f"""
### [{get_local_time()}] {process_name.upper()} {status.upper()}
**At:** {get_local_time()}
**Process:** contradiction_resolution
**Status:** {status}
**Duration:** {duration}s

**Output:**
{output}

**Changes Made:**
{chr(10).join(f"- {c}" for c in changes) if changes else "- (none)"}

**Carry Forward:**
{carry_forward}

**Errors:**
{errors if errors else "None."}

---
"""
    if OVERNIGHT_LOG.exists():
        content = OVERNIGHT_LOG.read_text()
    else:
        content = ""

    marker = "<!-- Processes append below this line. -->"
    if marker in content:
        content = content.replace(marker, marker + "\n" + entry.strip())
    else:
        content = content + "\n" + entry

    OVERNIGHT_LOG.write_text(content)


def record_sleep_run(duration_sec, completed, findings, flags=None):
    data = load_json(SLEEP_RUNS, {"runs": []})
    run = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "contradiction_resolution",
        "duration_seconds": duration_sec,
        "completed": completed,
        "findings": findings,
        "flags": flags or []
    }
    data["runs"].insert(0, run)
    data["runs"] = data["runs"][:100]
    save_json(SLEEP_RUNS, data)


# ── Resolution prompt ─────────────────────────────────────────────────────────

RESOLUTION_SYSTEM = """You are the agent's contradiction resolution engine. Two beliefs or facts conflict. Your job is to determine:

1. Which one is more likely correct based on: recency, specificity, emotional weight, source reliability
2. Whether the conflict is RESOLVABLE (you can pick a winner or synthesize a new version) or UNRESOLVABLE (genuinely ambiguous, needs human judgment)
3. If resolvable: provide the RESOLVED VERSION — a rewritten belief/fact that supersedes both

Be direct. Don't waffle. If you can't decide, say so and flag for the operator.
If both could be true in different contexts, say so and note the context split.

Format:
RESOLVABLE: yes / no
REASONING: <2-3 sentences>
RESOLVED_VERSION: <the winning or synthesized belief, or "n/a">
FOR_USER: <if unresolvable — what specific question needs human input, or "n/a">"""


def resolve_contradiction(contradiction_entry: dict) -> dict:
    """Use LLM to resolve a single contradiction."""
    c_text = contradiction_entry.get("contradiction", "")
    source = contradiction_entry.get("source", "unknown")

    prompt = f"""Resolve this contradiction detected in the agent's memory:

Contradiction: {c_text}
Detected in: {source}

Two beliefs or facts from the agent's memory conflict. Determine which wins or if this needs human input."""

    try:
        result_text = llm_extract(prompt, system=RESOLUTION_SYSTEM, max_tokens=512)
        return parse_resolution(result_text, contradiction_entry)
    except Exception as e:
        return {
            **contradiction_entry,
            "resolved": False,
            "resolution": None,
            "resolution_error": str(e),
            "for_user": f"Resolution failed: {e}. Original contradiction: {c_text}",
        }


def parse_resolution(raw_text: str, original: dict) -> dict:
    """Parse LLM resolution output."""
    result = {
        **original,
        "resolved": False,
        "resolution": None,
        "for_user": None,
        "resolved_version": None,
    }

    for line in raw_text.split("\n"):
        line = line.strip()
        if line.startswith("RESOLVABLE:"):
            val = line.split("RESOLVABLE:")[1].strip().lower()
            result["resolved"] = val == "yes"
        elif line.startswith("RESOLVED_VERSION:"):
            rv = line.split("RESOLVED_VERSION:")[1].strip()
            if rv != "n/a":
                result["resolved_version"] = rv
        elif line.startswith("FOR_USER:"):
            fc = line.split("FOR_USER:")[1].strip()
            if fc != "n/a":
                result["for_user"] = fc
        elif line.startswith("RESOLUTION:"):
            # Fallback if resolved_version not used
            res = line.split("RESOLUTION:")[1].strip()
            if res != "n/a" and not result.get("resolved_version"):
                result["resolved_version"] = res

    if not result["resolved"] and not result["for_user"]:
        # Mark unresolvable if LLM didn't clearly say yes/no
        result["for_user"] = f"Could not determine resolution. Contradiction: {original.get('contradiction', '')}"

    return result


def append_pending_for_user(entry: dict):
    """Append unresolvable contradiction to pending_for_user.md."""
    timestamp = get_local_time()
    section = f"""

## Contradiction: {entry.get('contradiction', '')[:100]}
**Detected:** {entry.get('detected_at', 'unknown')}
**Source:** {entry.get('source', 'unknown')}

{entry.get('for_user', 'No additional context provided.')}

---
"""
    if PENDING_FOR_USER.exists():
        content = PENDING_FOR_USER.read_text()
    else:
        content = "# Pending for the operator\n\nContradictions and decisions requiring human judgment.\n\n---\n"

    content = content + section
    PENDING_FOR_USER.write_text(content)


# ── Main ─────────────────────────────────────────────────────────────────────

def run_resolution():
    start = datetime.now()
    changes = []
    findings = []
    errors = []
    flags = []

    data = load_json(CONTRADICTIONS_FILE, {"contradictions": []})
    contradictions = data.get("contradictions", [])
    unresolved = [c for c in contradictions if not c.get("resolved", False)]

    if not unresolved:
        output = (
            "No unresolved contradictions. "
            "the agent's beliefs are consistent — or at least, no conflicts have been flagged."
        )
        carry_forward = "Nothing to carry forward."
        status = "skipped"
        findings.append("No contradictions to resolve")
    else:
        resolved_ids = []
        pending_user_ids = []

        for c in unresolved:
            print(f"  Resolving: {c.get('id', 'unknown')} — {c.get('contradiction', '')[:60]}...")
            result = resolve_contradiction(c)

            if result.get("resolved") and result.get("resolved_version"):
                # Write resolved version to semantic memory
                try:
                    memory_write(
                        content=result["resolved_version"],
                        entry_type="belief",
                        salience=0.8,
                        valence=0.5,
                        emotional_tags=["resolved_contradiction"],
                        source=f"resolved: {c.get('source', 'unknown')}",
                    )
                except Exception as e:
                    print(f"    Warning: could not write resolved belief: {e}")

                resolved_ids.append(c.get("id"))
                changes.append(f"resolved: '{c.get('contradiction', '')[:60]}' → semantic memory updated")
                findings.append(f"Resolved: {c.get('id', 'unknown')}")

            elif result.get("for_user"):
                append_pending_for_user(result)
                pending_user_ids.append(c.get("id"))
                changes.append(f"flagged for the operator: '{c.get('contradiction', '')[:60]}'")
                findings.append(f"Flagged for the operator: {c.get('id', 'unknown')}")

        # Remove resolved items from contradictions.json
        remaining = [c for c in contradictions if c.get("id") not in resolved_ids]
        data["contradictions"] = remaining
        save_json(CONTRADICTIONS_FILE, data)

        output_lines = [
            f"Processed {len(unresolved)} contradiction(s):",
            f"  Resolved: {len(resolved_ids)}",
            f"  Flagged for the operator: {len(pending_user_ids)}",
            "",
            f"Remaining unresolved in contradictions.json: {len(remaining)}",
        ]
        output = "\n".join(output_lines)
        carry_forward = (
            f"{len(resolved_ids)} contradiction(s) resolved and written to semantic memory. "
            f"{len(pending_user_ids)} sent to pending_for_user.md for the operator to decide."
        )
        status = "completed"

        if pending_user_ids:
            flags.append(f"{len(pending_user_ids)} contradiction(s) need the operator's judgment")

    duration = (datetime.now() - start).total_seconds()
    duration_str = f"{duration:.1f}s"

    log_to_overnight_log(
        "contradiction_resolution",
        status,
        duration_str,
        output,
        changes,
        carry_forward,
        errors[0] if errors else None
    )
    record_sleep_run(duration, status == "completed", findings, flags)

    print(f"Contradiction resolution complete. Status: {status}. Duration: {duration_str}")
    for f in findings:
        print(f"  - {f}")
    if flags:
        for fl in flags:
            print(f"  ⚠ {fl}")


if __name__ == "__main__":
    try:
        run_resolution()
    except Exception as e:
        duration = "unknown"
        log_to_overnight_log(
            "contradiction_resolution",
            "failed",
            duration,
            f"Contradiction resolution failed with error: {e}",
            [],
            "Check sleep_runs.json for error details.",
            str(e)
        )
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
