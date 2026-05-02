#!/usr/bin/env python3
"""
test_autonomous_tick.py
Test harness for the agent v20.0 autonomous tick loop.
Run in isolation — no LLM, no user input.
Verifies the heartbeat is real before trusting anything built on top.
"""

import os
import sys
import sqlite3
import time
import json
from datetime import datetime, timezone, timedelta

WORKSPACE = os.environ.get('AGENT_WORKSPACE', os.path.expanduser('~/.agent/workspace'))
sys.path.insert(0, WORKSPACE)

# Use test DB (same as start_autonomous.py)
DB_PATH = os.path.join(WORKSPACE, 'brain', 'agent_autonomous_test.db')
MDT = timezone(timedelta(hours=-6))

def now_mdt():
    return datetime.now(MDT).strftime('%Y-%m-%d %H:%M:%S %Z')

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_subheader(title):
    print(f"\n--- {title} ---")

def count_table(db, table, where="1=1"):
    # 'values' is a reserved word — quote it
    safe_table = f'"{table}"' if table == 'values' else table
    row = db.execute(f"SELECT COUNT(*) FROM {safe_table} WHERE {where}").fetchone()
    return row[0] if row else 0

def query_recent(db, table, limit=5, order="id DESC"):
    return db.execute(f"SELECT * FROM {table} ORDER BY {order} LIMIT {limit}").fetchall()

def summarize_actions(db, limit=50):
    """Summarize action distribution from recent internal_logs."""
    # internal_logs has 'chosen_action' column (action type as string)
    rows = db.execute("""
        SELECT chosen_action, COUNT(*) as count
        FROM internal_logs
        WHERE chosen_action IS NOT NULL
        GROUP BY chosen_action
        ORDER BY count DESC
    """).fetchall()
    return rows

def conflict_rate(db, limit=100):
    """was_conflict rate from recent entries."""
    rows = db.execute("""
        SELECT was_conflict, COUNT(*) as count
        FROM decision_conflicts
        ORDER BY id DESC LIMIT ?
    """, (limit,)).fetchall()
    return rows

def check_tick_interval(db):
    """Check that entries are roughly 2 seconds apart."""
    rows = db.execute("""
        SELECT id, timestamp FROM internal_logs
        ORDER BY id DESC LIMIT 20
    """).fetchall()
    if len(rows) < 2:
        return None, "Not enough entries"

    from datetime import datetime
    times = []
    for rid, ts in reversed(rows):
        try:
            t = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            times.append(t)
        except:
            pass

    if len(times) < 2:
        return None, "Could not parse timestamps"

    intervals = []
    for i in range(1, len(times)):
        diff = (times[i] - times[i-1]).total_seconds()
        intervals.append(diff)

    avg = sum(intervals) / len(intervals) if intervals else 0
    return avg, intervals[:5]

def run_test():
    print_header(f"the agent v20.0 Autonomous Tick — Isolation Test")
    print(f"Started: {now_mdt()}")
    print(f"DB: {DB_PATH}")
    print(f"Duration: 5 minutes")

    # Check DB exists
    if not os.path.exists(DB_PATH):
        print(f"\nERROR: DB not found at {DB_PATH}")
        print("Run bootstrap first to initialize the database.")
        return

    conn = sqlite3.connect(DB_PATH)

    # Check tables exist
    tables = conn.execute("""
        SELECT name FROM sqlite_master WHERE type='table'
    """).fetchall()
    table_names = [t[0] for t in tables]
    print(f"\nTables found: {', '.join(sorted(table_names))}")

    # Check autonomous systems initialized
    has_internal_logs = 'internal_logs' in table_names
    has_conflicts = 'conflicts' in table_names
    has_tensions = 'tensions' in table_names
    has_values = 'values' in table_names

    print(f"\nCore tables: "
          f"internal_logs={'✓' if has_internal_logs else '✗'}, "
          f"conflicts={'✓' if has_conflicts else '✗'}, "
          f"tensions={'✓' if has_tensions else '✗'}, "
          f"values={'✓' if has_values else '✗'}")

    # Initial counts
    initial_logs = count_table(conn, 'internal_logs') if has_internal_logs else 0
    initial_conflicts = count_table(conn, 'conflicts') if has_conflicts else 0
    initial_tensions = count_table(conn, 'tensions', 'unresolved=1') if has_tensions else 0
    initial_values = count_table(conn, 'values') if has_values else 0

    print(f"\nInitial state ({now_mdt()}):")
    print(f"  internal_logs: {initial_logs}")
    print(f"  conflicts: {initial_conflicts}")
    print(f"  unresolved tensions: {initial_tensions}")
    print(f"  values: {initial_values}")

    # Show current value weights
    if has_values:
        print_subheader("Current Value Weights")
        weights = conn.execute("SELECT name, weight FROM \"values\" ORDER BY name").fetchall()
        for name, weight in weights:
            print(f"  {name}: {weight:.4f}")

    conn.close()

    print(f"\n\nWaiting 5 minutes for tick loop to populate tables...")
    print("(Tick interval = 2 seconds, expecting ~150 entries)")

    # Wait and check progress periodically
    total_wait = 300  # 5 minutes
    check_interval = 30  # every 30 seconds
    elapsed = 0

    while elapsed < total_wait:
        time.sleep(check_interval)
        elapsed += check_interval
        remaining = total_wait - elapsed

        conn = sqlite3.connect(DB_PATH)
        current_logs = count_table(conn, 'internal_logs') if has_internal_logs else 0
        current_conflicts = count_table(conn, 'conflicts') if has_conflicts else 0
        current_tensions = count_table(conn, 'tensions', 'unresolved=1') if has_tensions else 0

        interval_info = ""
        if has_internal_logs:
            avg_int, sample_ints = check_tick_interval(conn)
            if avg_int:
                interval_info = f" | avg interval: {avg_int:.1f}s"

        print(f"  [{elapsed}s remaining] logs={current_logs}, conflicts={current_conflicts}, tensions={current_tensions}{interval_info}")
        conn.close()

    # Final analysis
    print_header("FINAL ANALYSIS")

    conn = sqlite3.connect(DB_PATH)

    # 1. Tick interval
    print_subheader("1. Tick Interval (heartbeat verification)")
    avg_int, sample_ints = check_tick_interval(conn)
    if avg_int:
        print(f"  Average interval: {avg_int:.2f} seconds")
        print(f"  Sample intervals: {[round(i, 1) for i in sample_ints]}")
        if 1.5 <= avg_int <= 2.5:
            print("  ✓ Tick is running at expected 2-second interval")
        else:
            print(f"  ⚠ Interval outside expected range (1.5-2.5s)")
    else:
        print(f"  {sample_ints}")

    # 2. Action distribution
    print_subheader("2. Action Distribution (internal_logs)")
    total_actions = count_table(conn, 'internal_logs')
    print(f"  Total entries: {total_actions}")
    if total_actions > 0:
        action_dist = summarize_actions(conn)
        for action, count in action_dist:
            pct = (count / total_actions) * 100
            print(f"  {action}: {count} ({pct:.1f}%)")

        # Check do_nothing won
        do_nothing_count = next((c for a, c in action_dist if a == 'do_nothing'), 0)
        if do_nothing_count > 0:
            print(f"  ✓ do_nothing won at least {do_nothing_count} times")
        else:
            print(f"  ⚠ do_nothing never won — possible priority leak or scoring bias")

        # Check respond_to_user is absent
        respond_count = next((c for a, c in action_dist if a == 'respond_to_user'), 0)
        if respond_count == 0:
            print(f"  ✓ respond_to_user not in pool (no user input — correct)")
        else:
            print(f"  ⚠ respond_to_user appeared {respond_count} times without user input")

    # 3. Conflict rate
    print_subheader("3. Conflict Rate (was_conflict in recent decisions)")
    conflict_rows = conflict_rate(conn, limit=100)
    total_recent = sum(r[1] for r in conflict_rows)
    conflict_count = 0
    for was_c, count in conflict_rows:
        if was_c == 1 or was_c == '1':
            conflict_count = count
    if total_recent > 0:
        conflict_pct = (conflict_count / total_recent) * 100
        print(f"  Recent decisions analyzed: {total_recent}")
        print(f"  Conflicts: {conflict_count} ({conflict_pct:.1f}%)")
        if 20 <= conflict_pct <= 45:
            print(f"  ✓ Conflict rate in target range (20-45%)")
        elif conflict_pct < 20:
            print(f"  ⚠ Conflict rate below target — scores may be converging")
        else:
            print(f"  ⚠ Conflict rate above target — possible thrashing")
    else:
        print("  No recent decision data")

    # 4. Conflicts table detail
    print_subheader("4. Conflict Table Detail")
    conflict_entries = query_recent(conn, 'conflicts', limit=10, order='id DESC')
    if conflict_entries:
        cols = [d[0] for d in conn.execute("PRAGMA table_info(conflicts)").fetchall()]
        print(f"  Recent entries:")
        for row in conflict_entries[:5]:
            row_dict = dict(zip(cols, row))
            print(f"    tick={row_dict.get('tick')} | "
                  f"{row_dict.get('action_a_type')} ({row_dict.get('action_a_score', 0):.3f}) "
                  f"vs {row_dict.get('action_b_type', 'none')} ({row_dict.get('action_b_score', 0):.3f}) | "
                  f"chosen={row_dict.get('chosen_action')} | "
                  f"delta={row_dict.get('decision_delta', 0):.3f} | "
                  f"doubt={row_dict.get('doubt_multiplier', 1.0):.3f}")
    else:
        print("  No conflict entries yet")

    # 5. Tensions
    print_subheader("5. Tension Field")
    tension_total = count_table(conn, 'tensions')
    tension_unresolved = count_table(conn, 'tensions', 'unresolved=1')
    print(f"  Total tensions: {tension_total}")
    print(f"  Unresolved: {tension_unresolved}")

    if tension_unresolved > 0:
        top_tensions = conn.execute("""
            SELECT id, description, intensity, decay_rate, unresolved
            FROM tensions
            ORDER BY intensity DESC LIMIT 5
        """).fetchall()
        print(f"  Top tensions:")
        for t in top_tensions:
            print(f"    [{t[0]}] intensity={t[2]:.3f} decay_rate={t[3]:.4f} unresolved={t[4]}: {t[1][:50]}")

        # Check for doubt_about tensions
        doubt_tensions = conn.execute("""
            SELECT COUNT(*) FROM tensions
            WHERE description LIKE 'doubt_about_%'
        """).fetchone()[0]
        print(f"  doubt_about_* tensions: {doubt_tensions}")
        if doubt_tensions > 0:
            print(f"  ✓ doubt_about_ tensions appearing (post-resolution mechanic working)")
    else:
        print("  ⚠ No unresolved tensions — spontaneous generation may not be firing")

    # 6. Values
    print_subheader("6. Value System")
    weights = conn.execute("SELECT name, weight FROM \"values\" ORDER BY name").fetchall()
    total = sum(w[1] for w in weights)
    print(f"  Weights (sum={total:.4f}):")
    for name, weight in weights:
        print(f"    {name}: {weight:.4f}")
    if 3.45 <= total <= 3.55:
        print(f"  ✓ Sum normalized close to 3.50")
    else:
        print(f"  ⚠ Sum outside expected range (3.45-3.55)")

    # 7. Sample internal log entries
    print_subheader("7. Sample Internal Log Entries")
    log_entries = query_recent(conn, 'internal_logs', limit=5, order='id DESC')
    if log_entries:
        cols = [d[0] for d in conn.execute("PRAGMA table_info(internal_logs)").fetchall()]
        print(f"  Most recent entries:")
        for row in log_entries[:3]:
            row_dict = dict(zip(cols, row))
            tick = row_dict.get('tick', '?')
            action = row_dict.get('chosen_action', 'none')
            was_conflict = row_dict.get('was_conflict', '?')
            doubt = row_dict.get('doubt_modifier', 1.0)
            regret = row_dict.get('regret_score', 0)
            print(f"    tick={tick} | action={action} | conflict={was_conflict} | doubt={doubt:.3f} | regret={regret:.3f}")
    else:
        print("  No entries — tick loop may not be writing to internal_logs")

    conn.close()

    print_header("TEST COMPLETE")
    print(f"Finished: {now_mdt()}")


if __name__ == "__main__":
    run_test()
