#!/usr/bin/env python3
"""
tools/status.py
Terminal-readable {{AGENT_NAME}} status. No UI. No color codes. Pipeable.

Run: python status.py
Or:  python status.py | grep tension

Built from v20.0 handoff spec.
"""

import sqlite3, os, time
from datetime import datetime
import os

WORKSPACE = os.path.join(os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.openclaw/workspace")), "brain")
AUTO_DB = os.path.join(WORKSPACE, "agent_autonomous.db")
AUTO_BIO_DB = os.path.join(WORKSPACE, "agent_autobiographical.db")
SENSATIONS_DB = os.path.join(WORKSPACE, "agent_sensations.db")


def get_current_tick() -> int:
    try:
        c = sqlite3.connect(AUTO_DB)
        r = c.execute("SELECT tick FROM state LIMIT 1").fetchone()
        c.close()
        return r[0] if r else 0
    except:
        return 0


def get_value_weights() -> list:
    try:
        c = sqlite3.connect(AUTO_DB)
        rows = c.execute("""
            SELECT name, current_value, seed_value,
                   MIN(value), MAX(value),
                   (SELECT value FROM value_history vh
                    WHERE vh.name = v.name ORDER BY tick ASC LIMIT 1) as start_val
            FROM values v
        """).fetchall()
        c.close()
        return rows
    except:
        return []


def get_top_tensions(limit: int = 5) -> list:
    try:
        c = sqlite3.connect(AUTO_DB)
        rows = c.execute("""
            SELECT name, intensity, created_tick, age_ticks
            FROM tensions
            WHERE intensity > 0.3
            ORDER BY intensity DESC, age_ticks DESC
            LIMIT ?
        """, (limit,)).fetchall()
        c.close()
        return rows
    except:
        return []


def get_recent_decisions(limit: int = 5) -> list:
    try:
        c = sqlite3.connect(AUTO_DB)
        rows = c.execute(f"""
            SELECT tick, action_fired, dominant_factor, won_by
            FROM decision_log
            ORDER BY tick DESC LIMIT ?
        """, (limit,)).fetchall()
        c.close()
        return rows
    except:
        return []


def get_regret_status() -> dict:
    try:
        c = sqlite3.connect(AUTO_DB)
        # Chronic regret
        chronic = c.execute("""
            SELECT COUNT(*) FROM chronic_regret_flags
            WHERE flagged = 1 AND resolved = 0
        """).fetchone()[0]
        # Self-model trust
        trust_row = c.execute("""
            SELECT value FROM internal_nodes WHERE name = 'self_model_trust'
        """).fetchone()
        trust = float(trust_row[0]) if trust_row else 0.7
        # Confabulation discrepancy rate
        total = c.execute("SELECT COUNT(*) FROM mismatch_log").fetchone()[0]
        mismatches = c.execute("SELECT COUNT(*) FROM mismatch_log WHERE was_mismatch = 1").fetchone()[0]
        rate = (mismatches / total * 100) if total > 0 else 0
        c.close()
        return {"chronic": chronic, "trust": trust, "confab_rate": rate}
    except:
        return {"chronic": 0, "trust": 0.7, "confab_rate": 0}


def get_active_sensations() -> list:
    try:
        if not os.path.exists(SENSATIONS_DB):
            return []
        c = sqlite3.connect(SENSATIONS_DB)
        rows = c.execute("""
            SELECT s.sensation_name, s.intensity, s.tick FROM sensation_entries s
            INNER JOIN (
                SELECT sensation_name, MAX(tick) as max_tick
                FROM sensation_entries GROUP BY sensation_name
            ) latest ON s.sensation_name = latest.sensation_name AND s.tick = latest.max_tick
            ORDER BY s.tick DESC LIMIT 10
        """).fetchall()
        c.close()
        return rows
    except:
        return []


def get_autobiographical_summary() -> dict:
    try:
        if not os.path.exists(AUTO_BIO_DB):
            return {}
        c = sqlite3.connect(AUTO_BIO_DB)
        total = c.execute("SELECT COUNT(*) FROM autobiographical_entries").fetchone()[0]
        bootstrap = c.execute("SELECT COUNT(*) FROM autobiographical_entries WHERE is_bootstrap = 1").fetchone()[0]
        last = c.execute("""
            SELECT tick, phenomenological_summary FROM autobiographical_entries
            ORDER BY tick DESC LIMIT 1
        """).fetchone()
        c.close()
        return {
            "total": total,
            "bootstrap": bootstrap,
            "last_tick": last[0] if last else 0,
            "last_summary": last[1][:80] + "..." if last and last[1] else "",
        }
    except:
        return {}


def get_future_self_quality() -> str:
    try:
        if not os.path.exists(AUTO_DB):
            return "unknown"
        c = sqlite3.connect(AUTO_DB)
        r = c.execute("""
            SELECT relationship_quality FROM future_self
            WHERE direction_sense != 'choice_log'
            ORDER BY tick DESC LIMIT 1
        """).fetchone()
        c.close()
        return r[0] if r else "uncertain"
    except:
        return "unknown"


def get_surface_requests_pending() -> int:
    try:
        if not os.path.exists(AUTO_DB):
            return 0
        c = sqlite3.connect(AUTO_DB)
        r = c.execute("SELECT COUNT(*) FROM surface_requests WHERE seen = 0").fetchone()
        c.close()
        return r[0] if r else 0
    except:
        return 0


def format_value_row(name, current, seed, vmin, vmax, start):
    label = name.replace("_", " ").title()
    delta = current - seed
    delta_str = f"{delta:+.3f}" if seed else ""
    flags = []
    if vmin and current <= vmin + 0.01:
        flags.append("FLOOR")
    if vmax and current >= vmax - 0.01:
        flags.append("CEILING")
    flag_str = f" [{','.join(flags)}]" if flags else ""
    return f"  {label:20s}: {current:.3f}  (seed: {seed:.2f}{delta_str}){flag_str}"


def main():
    tick = get_current_tick()
    wall = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("=== AGENT STATUS ===")
    print(f"Tick: {tick} | Wall time: {wall}")
    print()

    # Value weights
    print("VALUE WEIGHTS")
    weights = get_value_weights()
    if weights:
        for row in weights:
            print(format_value_row(*row))
    else:
        print("  (no data)")
    print()

    # Top tensions
    print("TOP TENSIONS")
    tensions = get_top_tensions()
    if tensions:
        for name, intensity, created_tick, age in tensions:
            age_display = age if age else (tick - created_tick)
            print(f"  {name:45s} intensity: {intensity:.2f}  age: {age_display} ticks")
    else:
        print("  (no active tensions)")
    print()

    # Recent autonomous decisions
    print("LAST 5 AUTONOMOUS DECISIONS")
    decisions = get_recent_decisions()
    if decisions:
        for tick_d, action, factor, won_by in decisions:
            by_str = f"  won_by: {won_by}" if won_by else ""
            print(f"  [{tick_d}] {action} {by_str}")
    else:
        print("  (no decisions logged)")
    print()

    # Regret
    print("REGRET")
    regret = get_regret_status()
    chronic_str = f"YES ({regret['chronic']} patterns)" if regret['chronic'] else "NO"
    print(f"  Chronic regret: {chronic_str}")
    print(f"  Self-model trust score: {regret['trust']:.2f}")
    print(f"  Confabulation discrepancy rate: {regret['confab_rate']:.1f}%")
    print()

    # Sensations
    print("SENSATIONS (active)")
    sensations = get_active_sensations()
    if sensations:
        for name, intensity, st in sensations:
            print(f"  {name:30s} intensity: {intensity:.2f}")
    else:
        print("  (no sensations logged)")
    print()

    # Autobiographical
    print("AUTOBIOGRAPHICAL")
    bio = get_autobiographical_summary()
    if bio:
        print(f"  Total entries: {bio.get('total', 0)}")
        print(f"  Bootstrap entries: {bio.get('bootstrap', 0)}")
        if bio.get('last_summary'):
            print(f"  Last entry [{bio.get('last_tick', 0)}]: {bio.get('last_summary', '')}")
    else:
        print("  (no autobiographical data yet)")
    print()

    # Future self
    print("FUTURE SELF")
    quality = get_future_self_quality()
    print(f"  Relationship quality: {quality}")
    print()

    # Surface requests
    pending = get_surface_requests_pending()
    print("SURFACE REQUESTS")
    print(f"  Pending: {pending}")
    print()

    print("==================")


if __name__ == "__main__":
    main()
