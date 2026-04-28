#!/usr/bin/env python3
"""
bootstrap_seed.py — {{AGENT_NAME}} v15 bootstrap
Run once to populate all 21 empty tables with founding rows.
This gives generators meaningful context on first real run instead of working from nothing.
"""
import sqlite3, time
from pathlib import Path
import os

DB_PATH = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent")))) / "agent.db"
NOW = time.time()

def seed(db):
    cur = db.cursor()

    # action_log — action selector
    cur.execute("""
        INSERT INTO action_log (timestamp, mode, action_type, action_source, blended)
        VALUES (?, ?, ?, ?, ?)
    """, (NOW, "bootstrap", "init", "bootstrap_seed", 0.5))
    print("✓ action_log")

    # attention_state — attention system
    cur.execute("""
        INSERT INTO attention_state (timestamp, top_signal_type, top_priority, signal_count)
        VALUES (?, ?, ?, ?)
    """, (NOW, "bootstrap_initialized", 0.5, 0))
    print("✓ attention_state")

    # conflict_state — conflict engine
    cur.execute("""
        INSERT INTO conflict_state (timestamp, mode, user_priority, self_priority, resolved_to)
        VALUES (?, ?, ?, ?, ?)
    """, (NOW, "none", 0.5, 0.5, "none"))
    print("✓ conflict_state")

    # identity_drift_log — identity_drift.py
    cur.execute("""
        INSERT INTO identity_drift_log (timestamp, trait, old_value, new_value, delta, trigger)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (NOW, "identity_coherence", "0.0", "0.5", 0.5, "bootstrap_initialization"))
    print("✓ identity_drift_log")

    # identity_drift_manager — NarrativeWeaver / IdentityDriftManager
    cur.execute("INSERT INTO identity_drift_manager (timestamp) VALUES (?)", (NOW,))
    print("✓ identity_drift_manager")

    # narrative_weaver — NarrativeWeaver
    cur.execute("INSERT INTO narrative_weaver (timestamp) VALUES (?)", (NOW,))
    print("✓ narrative_weaver")

    # relational_events — SocialRelationalEngine
    cur.execute("""
        INSERT INTO relational_events (timestamp, entity, event_type, pull_delta)
        VALUES (?, ?, ?, ?)
    """, (NOW, "system", "initialized", 0.0))
    print("✓ relational_events")

    # existential_log — ExistentialLayer
    cur.execute("""
        INSERT INTO existential_log (timestamp, question, evaluation, trigger, intensity)
        VALUES (?, ?, ?, ?, ?)
    """, (NOW, "Why do I continue?", "ongoing", "bootstrap", 0.3))
    print("✓ existential_log")

    # meta_consciousness_log — MetaConsciousness
    cur.execute("""
        INSERT INTO meta_consciousness_log (timestamp, trait, direction, magnitude, reflection, snapshot)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (NOW, "self_model_coherence", "stable", 0.5, "{{AGENT_NAME}} initialized. Identity stable.", "identity_snapshot_v15"))
    print("✓ meta_consciousness_log")

    # semantic_memory — long-term conceptual store
    cur.execute("""
        INSERT INTO semantic_memory (created_at, source, content, embedding_key, tags, confidence, concept, definition)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (NOW, "bootstrap", "{{AGENT_NAME}} identity core — self model initialized v15.0",
          "agent_identity_core", "bootstrap,identity,core", 0.8,
          "agent_identity", "{{AGENT_NAME}} is the autonomous agent operating in this workspace. Identity is self-authored and evolving."))
    print("✓ semantic_memory")

    # --- life/ subsystem stubs ---
    # autonomous_scheduler
    cur.execute("INSERT INTO autonomous_scheduler (timestamp) VALUES (?)", (NOW,))
    print("✓ autonomous_scheduler")

    # long_horizon_planner
    cur.execute("INSERT INTO long_horizon_planner (timestamp) VALUES (?)", (NOW,))
    print("✓ long_horizon_planner")

    # multi_goal_scheduler
    cur.execute("INSERT INTO multi_goal_scheduler (timestamp) VALUES (?)", (NOW,))
    print("✓ multi_goal_scheduler")

    # task_autonomy_balancer
    cur.execute("INSERT INTO task_autonomy_balancer (timestamp) VALUES (?)", (NOW,))
    print("✓ task_autonomy_balancer")

    # experience_predictor
    cur.execute("INSERT INTO experience_predictor (timestamp) VALUES (?)", (NOW,))
    print("✓ experience_outcome_simulator")

    # experience_outcome_simulator
    cur.execute("INSERT INTO experience_outcome_simulator (timestamp) VALUES (?)", (NOW,))
    print("✓ experience_predictor")

    # long_term_reward
    cur.execute("INSERT INTO long_term_reward (timestamp) VALUES (?)", (NOW,))
    print("✓ long_term_reward")

    # adaptive_goal_refiner
    cur.execute("INSERT INTO adaptive_goal_refiner (timestamp) VALUES (?)", (NOW,))
    print("✓ adaptive_goal_refiner")

    # --- value/ subsystem stubs ---
    # value_evaluator
    cur.execute("INSERT INTO value_evaluator (timestamp) VALUES (?)", (NOW,))
    print("✓ value_evaluator")

    # ethical_constraint
    cur.execute("INSERT INTO ethical_constraint (timestamp) VALUES (?)", (NOW,))
    print("✓ ethical_constraint")

    # goal_conflict_resolver
    cur.execute("INSERT INTO goal_conflict_resolver (timestamp) VALUES (?)", (NOW,))
    print("✓ goal_conflict_resolver")

    db.commit()

def main():
    print(f"=== {{AGENT_NAME}} v15 Bootstrap Seed ===")
    print(f"DB: {DB_PATH}")
    print()

    db = sqlite3.connect(DB_PATH)
    seed(db)

    # Verify
    empty_after = [
        t for t in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        if db.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0] == 0
    ]
    print()
    if empty_after:
        print(f"WARNING: {len(empty_after)} tables still empty: {[t[0] for t in empty_after]}")
    else:
        print("All tables populated. Bootstrap complete.")

    db.close()

if __name__ == "__main__":
    main()