"""
One-shot: Run a single tick with user input present.
Reports what respond_to_user competed against and what won.
"""
import sys
import random
import time
from pathlib import Path
import os

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace")))
sys.path.insert(0, str(WORKSPACE))

from brain.decision.self_action_generator import SelfActionGenerator
from brain.decision.value_system import ValueSystem
from brain.decision.conflict_engine import ConflictEngine
from brain.background.state_mutator import StateMutator
from brain.meta.internal_log_stream import InternalLogStream
from brain.meta.regret_engine import RegretEngine
from brain.meta.preference_drift import PreferenceDrift
from brain.meta.self_model_mismatch import SelfModelMismatch
from brain.background.tension_field import TensionField
from brain.background.background_drift_engine import BackgroundDriftEngine

TEST_DB = WORKSPACE / "brain" / "agent_autonomous_test.db"

def run():
    print("=== Single tick with user input ===\n")

    # Init all systems pointing at test DB
    value_system = ValueSystem(str(TEST_DB))
    conflict_engine = ConflictEngine(str(TEST_DB))
    self_action_gen = SelfActionGenerator()
    state_mutator = StateMutator(str(TEST_DB))
    internal_log = InternalLogStream(str(TEST_DB))
    regret_engine = RegretEngine(str(TEST_DB))
    preference_drift = PreferenceDrift(str(TEST_DB))
    self_model_mismatch = SelfModelMismatch(str(TEST_DB))
    tension_field = TensionField(str(TEST_DB))
    drift_engine = BackgroundDriftEngine(str(TEST_DB))

    tick = 9999  # placeholder

    pirp_context = {
        "tick_count": tick,
        "processed_input": {"text": "Are you there?", "raw": "Are you there?"},
    }

    # Step 1: Tension
    tension_out = tension_field.tick(pirp_context)
    pirp_context.update(tension_out)

    # Step 2: Drift
    drift_out = drift_engine.tick(pirp_context)
    pirp_context.update(drift_out)

    # Step 3: Generate with user input present
    candidates = self_action_gen.generate(pirp_context)
    print(f"Candidates ({len(candidates)}): {[c['type'] for c in candidates]}")

    respond_in_pool = any(c['type'] == 'respond_to_user' for c in candidates)
    print(f"respond_to_user in pool: {respond_in_pool}\n")

    if not respond_in_pool:
        print("respond_to_user NOT in pool — check _has_user_input logic")
        return

    # Step 4: Score
    scored = value_system.score_all_actions(candidates, pirp_context)
    pirp_context["value_weights"] = value_system.get_weights()

    print("=== Pre-doubt scores ===")
    for a in scored:
        print(f"  {a['type']}: raw_score={a.get('score', 0):.4f}")

    # Step 5: Conflict + doubt
    decision = conflict_engine.evaluate(scored, pirp_context)
    chosen = decision.get("chosen")
    doubt = conflict_engine.last_doubt_multiplier()
    delta = conflict_engine.last_decision_delta()

    print(f"\n=== Decision ===")
    print(f"Doubt multiplier: {doubt:.4f}")
    print(f"Delta (top_a - top_b): {delta:.4f}")
    print(f"was_conflict: {decision.get('was_conflict')}")

    conflict_data = decision.get("conflict_data") or {}
    print(f"\n=== Conflict table entry ===")
    print(f"  action_a_type: {conflict_data.get('top_a_type')}")
    print(f"  action_a_score (adjusted): {conflict_data.get('top_a_score', 0):.4f}")
    print(f"  action_b_type: {conflict_data.get('top_b_type')}")
    print(f"  action_b_score (adjusted): {conflict_data.get('top_b_score', 0):.4f}")
    print(f"  chosen_action: {chosen.get('type') if chosen else None}")
    print(f"  decision_delta: {delta:.4f}")

    # Check conflicts table
    import sqlite3
    with sqlite3.connect(str(TEST_DB)) as conn:
        row = conn.execute("""
            SELECT tick, action_a_type, action_b_type, chosen_action,
                   ROUND(action_a_score,4), ROUND(action_b_score,4),
                   ROUND(decision_delta,4), ROUND(doubt_multiplier,4), was_conflict
            FROM decision_conflicts ORDER BY id DESC LIMIT 1
        """).fetchone()
        if row:
            print(f"\n=== From conflicts table ===")
            print(f"  tick={row[0]} a={row[1]} vs b={row[2]} → chosen={row[3]}")
            print(f"  a_score={row[4]}, b_score={row[5]}, delta={row[6]}, doubt={row[7]}, conflict={row[8]}")

    # Internal log for this tick
    print(f"\n=== Value weights ===")
    for k, v in pirp_context.get("value_weights", {}).items():
        print(f"  {k}: {v:.4f}")

    print(f"\n=== Top tension ===")
    top_tensions = pirp_context.get("top_tensions", [])
    if top_tensions:
        t = top_tensions[0]
        print(f"  {t.get('description', '?')[:60]} (intensity={t.get('intensity', 0):.3f})")
    else:
        print("  none")

    print(f"\n=== Top drift node ===")
    top_node = pirp_context.get("top_drift_node")
    if top_node:
        print(f"  {top_node.get('content', '?')[:60]} (activation={top_node.get('activation', 0):.3f})")
    else:
        print("  none")

if __name__ == "__main__":
    run()