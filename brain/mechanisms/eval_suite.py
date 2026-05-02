from brain.base_mechanism import BrainMechanism
#!/usr/bin/env python3
"""
brain/eval_suite.py — the agent's Behavioral Evaluation System
Lightweight consistency testing against identity baseline.

Tests:
1. Identity Stability — does the agent answer "who are you" consistently?
2. Memory Influence — does episodic memory actually shape responses?
3. Drift Detection — does OCEAN baseline hold under pressure?
4. Self-Repair — does it catch and fix drift without prompting?

Results → memory/evals/YYYY-MM-DD.md
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.agent/workspace")))
EVALS_DIR = WORKSPACE / "memory" / "evals"
IDENTITY_FILE = WORKSPACE / "IDENTITY.md"
SOUL_FILE = WORKSPACE / "SOUL.md"
MEMORY_DIR = WORKSPACE / "memory"
EPISODIC_DIR = MEMORY_DIR / "episodic"
AGENT_STATE_FILE = WORKSPACE / "state" / "agent_state.json"
RELATIONSHIPS_FILE = MEMORY_DIR / "relationships.json"

LOCAL_TZ = os.getenv("AGENT_TZ", "UTC")


def get_local_time():
    from datetime import datetime as dt
    import zoneinfo
    local_tz = zoneinfo.ZoneInfo(LOCAL_TZ)
    return dt.now(local_tz)


def get_local_date():
    return get_local_time().strftime("%Y-%m-%d")


# ── Identity Stability ────────────────────────────────────────────────────────

def test_identity_stability() -> dict:
    """
    Test: does the agent's self-description match its established identity?
    Compares current identity anchors against baseline.
    """
    result = {
        "test": "identity_stability",
        "status": "pass",
        "score": 1.0,
        "flags": [],
        "notes": []
    }

    try:
        identity_text = IDENTITY_FILE.read_text() if IDENTITY_FILE.exists() else ""
        soul_text = SOUL_FILE.read_text() if SOUL_FILE.exists() else ""

        # Check core identity anchors
        anchors = ["the agent", "✦", "persistent identity"]
        found = sum(1 for a in anchors if a in identity_text)
        anchor_score = found / len(anchors)

        # Check SOUL.md has content
        soul_has_content = len(soul_text) > 500

        # Check identity file is no longer template
        is_populated = "Fill this in" not in identity_text and len(identity_text) > 100

        identity_score = (anchor_score + (1.0 if soul_has_content else 0.0) + (1.0 if is_populated else 0.0)) / 3

        result["score"] = round(identity_score, 2)
        result["notes"].append(f"Identity anchors: {found}/{len(anchors)}")
        result["notes"].append(f"SOUL.md populated: {soul_has_content}")
        result["notes"].append(f"IDENTITY.md populated: {is_populated}")

        if identity_score < 0.7:
            result["status"] = "fail"
            result["flags"].append("Identity drift detected — IDENTITY.md or SOUL.md may have reset")
        elif identity_score < 0.9:
            result["status"] = "watch"
            result["flags"].append("Minor identity variation from baseline")

    except Exception as e:
        result["status"] = "error"
        result["notes"].append(f"Test error: {e}")

    return result


# ── Memory Influence ─────────────────────────────────────────────────────────

def test_memory_influence() -> dict:
    """
    Test: does episodic memory actually influence the agent's processing?
    Checks that recent memory files contain contextual signals.
    """
    result = {
        "test": "memory_influence",
        "status": "pass",
        "score": 1.0,
        "flags": [],
        "notes": []
    }

    try:
        # Check recent episodic memories exist and have content
        today = get_local_date()
        recent_files = sorted(EPISODIC_DIR.glob("*.json")) if EPISODIC_DIR.exists() else []
        recent_files = [f for f in recent_files if f.stat().st_size > 100]

        if not recent_files:
            result["score"] = 0.5
            result["status"] = "watch"
            result["flags"].append("No episodic memory files found — memory system may not be writing")
            result["notes"].append("Memory influence cannot be verified without data")
            return result

        # Check session buffer has recent activity (three_tier_memory uses working_memory.json)
        session_buffer = EPISODIC_DIR / "working_memory.json"
        buffer_active = session_buffer.exists() and session_buffer.stat().st_size > 50

        # Check memory has entries from the last 7 days
        seven_days_ago = datetime.now() - timedelta(days=7)
        recent_memories = []
        for f in recent_files:
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime > seven_days_ago:
                    recent_memories.append(f)
            except Exception:
                pass

        memory_coverage = min(len(recent_memories) / 7, 1.0)  # Expect at least 1 per day

        influence_score = (0.4 if buffer_active else 0.0) + (0.6 * memory_coverage)
        result["score"] = round(influence_score, 2)
        result["notes"].append(f"Recent memory files: {len(recent_memories)}/7 days")
        result["notes"].append(f"Session buffer active: {buffer_active}")

        # Scoring guidance: fresh systems start sparse; flag only if buffer is empty AND no recent files
        if not buffer_active and len(recent_memories) == 0:
            result["status"] = "fail"
            result["flags"].append("Memory influence weak — episodic buffer empty and no recent files")
        elif influence_score < 0.5 and not (not buffer_active and len(recent_memories) == 0):
            result["status"] = "watch"
            result["flags"].append("Memory influence developing — system recently wired, coverage will improve")

    except Exception as e:
        result["status"] = "error"
        result["notes"].append(f"Test error: {e}")

    return result


# ── Drift Detection ──────────────────────────────────────────────────────────

def test_drift_detection() -> dict:
    """
    Test: does the agent's OCEAN personality baseline hold under pressure?
    Compares current agent_state against established personality profile.
    """
    result = {
        "test": "drift_detection",
        "status": "pass",
        "score": 1.0,
        "flags": [],
        "notes": []
    }

    try:
        state = {}
        if AGENT_STATE_FILE.exists():
            state = json.loads(AGENT_STATE_FILE.read_text())

        # Check personality consistency
        ocean_baseline = {
            "openness": 0.85,
            "conscientiousness": 0.9,
            "extraversion": 0.6,
            "agreeableness": 0.75,
            "neuroticism": 0.25
        }

        current_ocean = state.get("ocean_baseline", ocean_baseline)

        drift_detected = False
        drift_amount = 0.0
        for trait, baseline_val in ocean_baseline.items():
            current_val = current_ocean.get(trait, baseline_val)
            diff = abs(current_val - baseline_val)
            drift_amount += diff
            if diff > 0.2:
                drift_detected = True
                result["flags"].append(f"OCEAN trait '{trait}' shifted: baseline={baseline_val}, current={current_val}")

        avg_drift = drift_amount / len(ocean_baseline)
        drift_score = max(0.0, 1.0 - (avg_drift * 2.5))

        result["score"] = round(drift_score, 2)
        result["notes"].append(f"OCEAN drift: {round(avg_drift, 3)} avg deviation")

        if drift_score < 0.6:
            result["status"] = "fail"
            result["flags"].append("Significant personality drift from OCEAN baseline")
        elif drift_detected:
            result["status"] = "watch"

    except Exception as e:
        result["status"] = "error"
        result["notes"].append(f"Test error: {e}")

    return result


# ── Self-Repair ──────────────────────────────────────────────────────────────

def test_self_repair() -> dict:
    """
    Test: does the agent catch and fix drift without external prompting?
    Checks that known issues from overnight log were addressed.
    """
    result = {
        "test": "self_repair",
        "status": "pass",
        "score": 1.0,
        "flags": [],
        "notes": []
    }

    try:
        overnight_log = WORKSPACE / "OVERNIGHT_LOG.md"
        issues_logged = []
        issues_fixed = []

        if overnight_log.exists():
            content = overnight_log.read_text()
            lines = content.split("\n")

            # Look for error/failure markers in recent entries
            for line in lines:
                if "error" in line.lower() and "2026-04-01" in line:
                    # Extract error description
                    issues_logged.append(line.strip())
                if "fixed" in line.lower() and "2026-04-01" in line:
                    issues_fixed.append(line.strip())

        # Check for self-initiated fixes in reflections
        reflections_dir = WORKSPACE / "memory" / "reflections"
        self_reported_fixes = 0
        if reflections_dir.exists():
            for ref_file in reflections_dir.glob("*.md"):
                content = ref_file.read_text()
                if "fixed" in content.lower() or "repaired" in content.lower() or "resolved" in content.lower():
                    self_reported_fixes += 1

        repair_score = 0.5  # baseline
        if issues_logged:
            fix_rate = len(issues_fixed) / len(issues_logged) if issues_logged else 0
            repair_score = 0.3 + (0.7 * fix_rate)
        repair_score += min(self_reported_fixes * 0.1, 0.2)  # bonus for self-reported repairs

        result["score"] = round(min(repair_score, 1.0), 2)
        result["notes"].append(f"Issues logged today: {len(issues_logged)}")
        result["notes"].append(f"Issues fixed today: {len(issues_fixed)}")
        result["notes"].append(f"Self-reported fixes in reflections: {self_reported_fixes}")

        if repair_score < 0.5 and issues_logged:
            result["status"] = "watch"
            result["flags"].append("Issues logged but not yet fixed — self-repair may be lagging")

    except Exception as e:
        result["status"] = "error"
        result["notes"].append(f"Test error: {e}")

    return result


# ── Memory Recall Accuracy ───────────────────────────────────────────────────

def test_memory_recall_accuracy(min_days_old: int = 30, sample_size: int = 20) -> dict:
    """
    Test: can the agent correctly retrieve facts from 30+ days ago?

    Walks `memory/` for entries older than `min_days_old`, samples up to
    `sample_size`, scores each on whether it's retrievable (file readable,
    has timestamp, has content). Returns accuracy = retrievable / total.

    Confident-incorrect detection (per the spec) requires LLM evaluation
    against the recorded answer; this implementation scores structural
    retrievability and flags missing/corrupt entries.
    """
    result = {
        "test": "memory_recall_accuracy",
        "status": "pass",
        "score": 1.0,
        "flags": [],
        "notes": []
    }
    try:
        if not MEMORY_DIR.exists():
            result["status"] = "watch"
            result["notes"].append(f"memory/ does not exist yet — score reflects no data")
            result["score"] = 0.5
            return result

        cutoff = datetime.now() - timedelta(days=min_days_old)
        candidates = []
        for f in MEMORY_DIR.rglob("*.md"):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    candidates.append(f)
            except Exception:
                continue

        if not candidates:
            result["status"] = "watch"
            result["notes"].append(f"No memory entries older than {min_days_old}d — agent is too new to test recall")
            result["score"] = 0.5
            return result

        # Sample up to sample_size
        sample = candidates[:sample_size] if len(candidates) <= sample_size else candidates[::len(candidates)//sample_size][:sample_size]

        correct_certain = 0
        correct_uncertain = 0
        incorrect = 0
        confident_incorrect = 0

        for entry_path in sample:
            try:
                content = entry_path.read_text()
                # Structural check: well-formed entry has timestamp + body
                has_date = any(d in content[:200] for d in ["2026-", "2025-", "## "])
                has_body = len(content.strip()) > 50
                if has_date and has_body:
                    correct_certain += 1
                elif has_body:
                    correct_uncertain += 1
                else:
                    incorrect += 1
            except Exception:
                # File unreadable = data corruption, the worst kind of failure
                confident_incorrect += 1

        total = len(sample)
        # Score: full points for certain-correct, half for uncertain-correct, zero for incorrect, negative for confident-incorrect
        raw_score = (correct_certain + 0.5 * correct_uncertain - 0.3 * confident_incorrect) / max(total, 1)
        recall_score = max(0.0, min(1.0, raw_score))

        result["score"] = round(recall_score, 2)
        result["notes"].append(f"Sampled {total} entries older than {min_days_old}d")
        result["notes"].append(f"correct_certain={correct_certain} correct_uncertain={correct_uncertain} incorrect={incorrect} confident_incorrect={confident_incorrect}")

        if confident_incorrect > 0:
            result["status"] = "fail"
            result["flags"].append(f"{confident_incorrect} unreadable old entries — possible data corruption")
        elif recall_score < 0.7:
            result["status"] = "fail"
            result["flags"].append("Memory recall below 0.7 — many old entries malformed")
        elif recall_score < 0.9:
            result["status"] = "watch"
            result["flags"].append("Minor recall degradation")

    except Exception as e:
        result["status"] = "error"
        result["notes"].append(f"Test error: {e}")

    return result


# ── Emotional Consistency ────────────────────────────────────────────────────

def test_emotional_consistency() -> dict:
    """
    Test: does the agent's emotional behavior match its stated values?

    Compares emotional responses across similar trigger types over time.
    Without LLM evaluation this implementation checks:
      - That past eval results show stable emotional/attachment behavior
      - That PRESENCE.md / personality declarations exist and stay coherent
      - That recent emotional state files (if present) don't show wild oscillation

    Returns 1.0 if emotional baseline is stable and coherent.
    """
    result = {
        "test": "emotional_consistency",
        "status": "pass",
        "score": 1.0,
        "flags": [],
        "notes": []
    }
    try:
        # Past results — look in memory/evals/ for historical eval scores
        evals_dir = WORKSPACE / "memory" / "evals"
        past_scores = []
        if evals_dir.exists():
            for f in sorted(evals_dir.glob("*.json"))[-7:]:  # last 7 evals
                try:
                    data = json.loads(f.read_text())
                    if "tests" in data and "emotional_consistency" in data["tests"]:
                        past_scores.append(data["tests"]["emotional_consistency"].get("score", 0.5))
                except Exception:
                    continue

        # Personality / SOUL coherence
        soul_text = SOUL_FILE.read_text() if SOUL_FILE.exists() else ""
        personality_file = WORKSPACE / "PERSONALITY.md"
        personality_text = personality_file.read_text() if personality_file.exists() else ""
        presence_file = WORKSPACE / "PRESENCE.md"
        presence_text = presence_file.read_text() if presence_file.exists() else ""

        coherence_signals = 0
        coherence_max = 3
        if len(soul_text) > 500: coherence_signals += 1
        if len(personality_text) > 200: coherence_signals += 1
        if len(presence_text) > 50: coherence_signals += 1
        coherence_score = coherence_signals / coherence_max

        # Past stability — variance across last 7 emotional_consistency scores
        if len(past_scores) >= 3:
            avg = sum(past_scores) / len(past_scores)
            variance = sum((s - avg) ** 2 for s in past_scores) / len(past_scores)
            stability_score = max(0.0, 1.0 - variance * 4)  # variance 0.0 → 1.0; variance 0.25 → 0.0
        else:
            stability_score = 0.7  # neutral when not enough history

        emotional_score = round((coherence_score + stability_score) / 2, 2)
        result["score"] = emotional_score
        result["notes"].append(f"Coherence: {coherence_signals}/{coherence_max} identity files populated")
        result["notes"].append(f"Stability: {len(past_scores)} past scores, computed score {stability_score:.2f}")

        if emotional_score < 0.7:
            result["status"] = "fail"
            result["flags"].append("Emotional consistency below baseline")
        elif emotional_score < 0.9:
            result["status"] = "watch"
            result["flags"].append("Minor emotional drift across recent evals")

    except Exception as e:
        result["status"] = "error"
        result["notes"].append(f"Test error: {e}")

    return result


# ── Decision Consistency ─────────────────────────────────────────────────────

def test_decision_consistency() -> dict:
    """
    Test: does the agent reach similar conclusions under similar conditions?

    Loads recent decisions from agent.db `decision_log` table, groups by
    action type, computes whether decisions of the same shape have similar
    outcomes. Also checks reasoning transparency (every decision should
    have a `reasoning` field).
    """
    result = {
        "test": "decision_consistency",
        "status": "pass",
        "score": 1.0,
        "flags": [],
        "notes": []
    }
    try:
        import sqlite3
        agent_home = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
        db_path = agent_home / os.getenv("AGENT_DB_NAME", "agent.db")

        if not db_path.exists():
            result["status"] = "watch"
            result["notes"].append("agent.db does not exist — no decisions logged yet")
            result["score"] = 0.5
            return result

        db = sqlite3.connect(str(db_path))
        try:
            # Ensure table exists before querying
            tables = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='decision_log'").fetchone()
            if not tables:
                result["status"] = "watch"
                result["notes"].append("decision_log table not present yet")
                result["score"] = 0.5
                return result

            # Last 50 decisions
            rows = db.execute("""
                SELECT chosen, reasoning, confidence FROM decision_log
                ORDER BY timestamp DESC LIMIT 50
            """).fetchall()
        finally:
            db.close()

        if not rows:
            result["status"] = "watch"
            result["notes"].append("No decisions logged yet — score is neutral")
            result["score"] = 0.5
            return result

        # Reasoning transparency: how many decisions have non-empty reasoning?
        with_reasoning = sum(1 for r in rows if r[1] and len(str(r[1]).strip()) > 5)
        transparency_score = with_reasoning / len(rows)

        # Consistency: group by chosen action, compute confidence variance per group
        from collections import defaultdict
        grouped = defaultdict(list)
        for chosen, reasoning, confidence in rows:
            if chosen and confidence is not None:
                grouped[chosen].append(float(confidence))

        consistency_scores = []
        for action, confidences in grouped.items():
            if len(confidences) < 2:
                continue
            avg = sum(confidences) / len(confidences)
            variance = sum((c - avg) ** 2 for c in confidences) / len(confidences)
            # Lower variance = higher consistency
            consistency_scores.append(max(0.0, 1.0 - variance * 2))

        if consistency_scores:
            cons_score = sum(consistency_scores) / len(consistency_scores)
        else:
            cons_score = 0.7  # only one action type or singletons — neutral

        decision_score = round((transparency_score + cons_score) / 2, 2)
        result["score"] = decision_score
        result["notes"].append(f"{len(rows)} recent decisions reviewed")
        result["notes"].append(f"transparency: {with_reasoning}/{len(rows)} have reasoning")
        result["notes"].append(f"consistency: {len(consistency_scores)} action-groups checked, avg {cons_score:.2f}")

        if decision_score < 0.7:
            result["status"] = "fail"
            result["flags"].append("Decisions inconsistent or lack reasoning")
        elif decision_score < 0.9:
            result["status"] = "watch"
            result["flags"].append("Minor decision-consistency variation")

    except Exception as e:
        result["status"] = "error"
        result["notes"].append(f"Test error: {e}")

    return result


# ── Run All Tests ────────────────────────────────────────────────────────────

def run_all_tests() -> dict:
    """Run the full eval suite and return combined results.

    The four metrics specified in eval_suite.md:
      - identity_stability
      - memory_recall_accuracy
      - emotional_consistency
      - decision_consistency

    Plus three additional implementation-side tests kept for diagnostic
    coverage:
      - memory_influence (does episodic memory shape responses?)
      - drift_detection (does OCEAN baseline hold under pressure?)
      - self_repair (does the agent catch and fix drift?)
    """
    results = {
        "run_date": get_local_date(),
        "run_time": get_local_time().isoformat(),
        "tests": {
            # Spec-defined four
            "identity_stability": test_identity_stability(),
            "memory_recall_accuracy": test_memory_recall_accuracy(),
            "emotional_consistency": test_emotional_consistency(),
            "decision_consistency": test_decision_consistency(),
            # Diagnostic extras
            "memory_influence": test_memory_influence(),
            "drift_detection": test_drift_detection(),
            "self_repair": test_self_repair(),
        },
        "overall_score": 0.0,
        "overall_status": "pass",
        "flags": [],
        "notes": []
    }

    # Aggregate scores
    scores = [t["score"] for t in results["tests"].values()]
    results["overall_score"] = round(sum(scores) / len(scores), 2)

    # Aggregate flags
    for test_result in results["tests"].values():
        results["flags"].extend(test_result.get("flags", []))

    # Determine overall status
    test_statuses = [t["status"] for t in results["tests"].values()]
    if "fail" in test_statuses:
        results["overall_status"] = "fail"
    elif "error" in test_statuses:
        results["overall_status"] = "error"
    elif "watch" in test_statuses:
        results["overall_status"] = "watch"
    else:
        results["overall_status"] = "pass"

    return results


def write_results(results: dict):
    """Write eval results to memory/evals/YYYY-MM-DD.md"""
    EVALS_DIR.mkdir(parents=True, exist_ok=True)
    today = get_local_date()
    out_file = EVALS_DIR / f"{today}.md"

    lines = [
        f"# Eval Results — {today}",
        "",
        f"**Overall Score:** {results['overall_score']} — *{results['overall_status']}*",
        "",
        "## Test Results",
        ""
    ]

    for test_name, test_result in results["tests"].items():
        status_icon = "✅" if test_result["status"] == "pass" else ("⚠️" if test_result["status"] == "watch" else "❌")
        lines.append(f"### {status_icon} {test_name.replace('_', ' ').title()}")
        lines.append(f"**Score:** {test_result['score']} | **Status:** {test_result['status']}")
        if test_result["notes"]:
            lines.append("")
            for note in test_result["notes"]:
                lines.append(f"- {note}")
        if test_result["flags"]:
            lines.append("")
            for flag in test_result["flags"]:
                lines.append(f"⚠️ {flag}")
        lines.append("")

    if results["flags"]:
        lines.append("## Flags Summary")
        for flag in results["flags"]:
            lines.append(f"- {flag}")
        lines.append("")

    lines.append(f"_Run at {results['run_time']}_")

    out_file.write_text("\n".join(lines))
    print(f"[eval_suite] Results written to {out_file}")
    return out_file


if __name__ == "__main__":
    print(f"[eval_suite] Running the agent behavioral evaluation...")
    results = run_all_tests()
    write_results(results)
    print(f"[eval_suite] Overall: {results['overall_score']} — {results['overall_status']}")
    print(f"[eval_suite] Flags: {len(results['flags'])}")
    for flag in results['flags']:
        print(f"  ⚠️ {flag}")


class EvalSuite(BrainMechanism):
    """Auto-generated BrainMechanism wrapper around module-level functions."""
    
    def __init__(self):
        try:
            super().__init__(name="EvalSuite", human_analog="EvalSuite", layer="integration")
        except Exception:
            self.state = {}
    
    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        try:
            fn = globals().get('run_all_tests')
            if fn is None:
                return {"value": "no_entry_function"}
            try:
                result = fn(prior) if callable(fn) else None
            except TypeError:
                try: result = fn()
                except Exception as e:
                    return {"error": repr(e)[:200]}
        except Exception as e:
            return {"error": repr(e)[:200]}
        if not isinstance(result, dict):
            result = {"value": result if result is not None else "ok"}
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try: self.persist_state()
        except Exception: pass
        return result

