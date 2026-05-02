#!/usr/bin/env python3
"""
start_autonomous.py
Lightweight autonomous tick starter.
Initializes only the autonomous decision systems — no LLM.
Starts the tick loop and runs indefinitely.
"""

import os
import sys
import time
import logging

WORKSPACE = os.environ.get('AGENT_WORKSPACE', os.path.expanduser('~/.agent/workspace'))
sys.path.insert(0, WORKSPACE)
os.environ.setdefault('AGENT_WORKSPACE', WORKSPACE)


def _configure_logging():
    """Configure logging. Called from main() — NOT at import, so importers
    don't have their global logging silently overridden."""
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s %(name)-20s %(levelname)-5s %(message)s'
    )

# ---------------------------------------------------------------------------
# Initialize database schema
# ---------------------------------------------------------------------------

def init_schema():
    """
    Use the production autonomous DB (agent_autonomous.db).
    Components handle their own CREATE TABLE IF NOT EXISTS.
    We just create the DB file if missing and call component __init__ methods.
    """
    from pathlib import Path
    import sqlite3

    # Production autonomous DB — persists across runs, carries all history
    AUTONOMOUS_DB = Path(WORKSPACE) / 'brain' / 'agent_autonomous.db'
    AUTONOMOUS_DB.parent.mkdir(parents=True, exist_ok=True)

    # If DB doesn't exist, create it; otherwise use existing (preserves all data)
    if not AUTONOMOUS_DB.exists():
        conn = sqlite3.connect(str(AUTONOMOUS_DB))
        conn.close()
        print(f'[{time.strftime("%H:%M:%S")}] Created fresh autonomous DB at {AUTONOMOUS_DB}')
    else:
        print(f'[{time.strftime("%H:%M:%S")}] Using existing autonomous DB at {AUTONOMOUS_DB}')

    return str(AUTONOMOUS_DB)


def init_components(test_db_path: str):
    """
    Initialize all component schemas by calling their __init__.
    This ensures every table matches exactly what each component expects.
    """
    from brain.decision.value_system import ValueSystem
    from brain.background.tension_field import TensionField
    from brain.background.background_drift_engine import BackgroundDriftEngine
    from brain.decision.conflict_engine import ConflictEngine
    from brain.background.state_mutator import StateMutator
    from brain.meta.internal_log_stream import InternalLogStream
    from brain.meta.regret_engine import RegretEngine
    from brain.meta.self_model_mismatch import SelfModelMismatch

    print(f'[{time.strftime("%H:%M:%S")}] Initializing component schemas...')

    # These components create their own tables
    ValueSystem(db_path=test_db_path)           # → values, value_history
    TensionField(db_path=test_db_path)           # → tensions
    BackgroundDriftEngine(db_path=test_db_path) # → internal_nodes
    ConflictEngine(db_path=test_db_path)        # → decision_conflicts
    StateMutator(db_path=test_db_path)          # → state_mutations
    InternalLogStream(db_path=test_db_path)     # → internal_logs, pulse_summaries
    RegretEngine(db_path=test_db_path)          # → regret_predictions, regret_log, chronic_regret_flags
    SelfModelMismatch(db_path=test_db_path)     # → mismatch_log, confusion_surface_events

    # Seed value system weights (ValueSystem._seed_values handles this)
    # PreferenceDrift doesn't need schema — it reads from existing tables
    # StateStateInjector doesn't need schema — it reads existing tables

    print(f'[{time.strftime("%H:%M:%S")}] All component schemas initialized')


# ---------------------------------------------------------------------------
# Start autonomous tick
# ---------------------------------------------------------------------------

def main():
    _configure_logging()
    print("the agent v20.0 — Autonomous Tick Starter")
    print("="*50)

    # Initialize schema (returns production autonomous DB path)
    autonomous_db = init_schema()

    # Initialize component schemas via their __init__ methods
    init_components(autonomous_db)

    # Import and initialize autonomous systems
    from pathlib import Path
    # Use the autonomous DB — carries all history including seed tensions
    DB_PATH = autonomous_db

    print(f"\n[{time.strftime('%H:%M:%S')}] Loading autonomous systems...")

    from brain.background.background_drift_engine import BackgroundDriftEngine
    from brain.background.tension_field import TensionField
    from brain.decision.value_system import ValueSystem
    from brain.decision.conflict_engine import ConflictEngine
    from brain.decision.self_action_generator import SelfActionGenerator
    from brain.background.state_mutator import StateMutator
    from brain.meta.internal_log_stream import InternalLogStream
    from brain.meta.regret_engine import RegretEngine
    from brain.meta.preference_drift import PreferenceDrift
    from brain.meta.self_model_mismatch import SelfModelMismatch

    # Initialize all systems
    drift_engine = BackgroundDriftEngine(db_path=str(DB_PATH))
    tension_field = TensionField(db_path=str(DB_PATH))
    value_system = ValueSystem(db_path=str(DB_PATH))
    conflict_engine = ConflictEngine(db_path=str(DB_PATH))
    self_action_generator = SelfActionGenerator()
    state_mutator = StateMutator(db_path=str(DB_PATH))
    internal_log = InternalLogStream(db_path=str(DB_PATH))
    regret_engine = RegretEngine(db_path=str(DB_PATH))
    preference_drift = PreferenceDrift(db_path=str(DB_PATH))
    self_model_mismatch = SelfModelMismatch(db_path=str(DB_PATH))

    tick_counter = 0

    print(f"[{time.strftime('%H:%M:%S')}] All systems loaded. Starting tick loop...")
    print(f"[{time.strftime('%H:%M:%S')}] Tick interval: 2 seconds")
    print(f"[{time.strftime('%H:%M:%S')}] No user input — pure autonomous operation")
    print()

    # Run tick loop
    running = True

    def tick_loop():
        nonlocal tick_counter, drift_engine, tension_field, self_action_generator
        nonlocal value_system, conflict_engine, state_mutator, internal_log
        nonlocal regret_engine, preference_drift, self_model_mismatch

        import logging
        logger = logging.getLogger('autonomous_tick')

        while running:
            tick_counter += 1

            pirp_context = {
                "tick_count": tick_counter,
            }

            # First tick injects a user message so the agent has a starting
            # prompt to chew on. Every tick after runs in pure autonomous mode
            # (no processed_input → SelfActionGenerator picks autonomous candidates).
            if tick_counter == 1:
                pirp_context["processed_input"] = {
                    "text": "Are you there?",
                    "raw": "Are you there?",
                }

            try:
                # Step 1: tension_field.tick()
                tension_output = tension_field.tick(pirp_context)
                pirp_context.update(tension_output)

                # Step 2: drift_engine.tick()
                drift_output = drift_engine.tick(pirp_context)
                pirp_context.update(drift_output)

                # Step 3: Generate candidates (no user input)
                candidates = self_action_generator.generate(pirp_context)

                if not candidates:
                    # Idle tick
                    tick_counter -= 1  # don't count idle ticks
                    time.sleep(2)
                    continue

                # Step 4: Score actions
                scored_actions = value_system.score_all_actions(candidates, pirp_context)
                pirp_context["value_weights"] = value_system.get_weights()

                # Store prediction for regret
                regret_engine.store_prediction(
                    action=scored_actions[0] if scored_actions else {},
                    pirp_context=pirp_context,
                    pre_state=state_mutator.capture_pre_state(pirp_context),
                )

                # Step 5: Evaluate with conflict/doubt
                decision = conflict_engine.evaluate(scored_actions, pirp_context)
                chosen_action = decision.get("chosen")

                # Mark chosen action cooldown
                if chosen_action:
                    self_action_generator.after_choice(chosen_action, tick_counter)

                # Step 6: Apply state mutations
                state_data = {}
                if chosen_action:
                    state_output = state_mutator.apply(chosen_action, pirp_context)
                    state_data["mutations"] = state_output.get("mutations", [])

                # Step 7: Evaluate regret
                post_state = state_mutator.get_pre_state()
                if post_state:
                    post_state["limbic_state"] = pirp_context.get("limbic_state", {})
                    post_state["mood"] = pirp_context.get("mood", "neutral")

                regret_result = regret_engine.evaluate_last_action(pirp_context, post_state)
                state_data["regret_score"] = regret_result.get("regret_score", 0)

                # Step 8: Preference drift
                preference_drift.tick(pirp_context)
                state_data["value_weights"] = value_system.get_weights()

                # Step 9: Self-model mismatch
                mismatch_result = {}
                if chosen_action:
                    # Build full decision context for mismatch layer
                    conflict_data_raw = decision.get("conflict_data") or {}
                    decision_context = dict(conflict_data_raw)  # shallow copy to avoid spread issues
                    decision_context["delta"] = conflict_engine.last_decision_delta()
                    decision_context["doubt_multiplier"] = conflict_engine.last_doubt_multiplier()
                    mismatch_result = self_model_mismatch.process_decision(
                        chosen_action=chosen_action,
                        conflict_data=decision_context,
                        pirp_context=pirp_context,
                    )

                # Step 10: Internal log
                internal_log.write(
                    pirp_context=pirp_context,
                    decision_data=decision,
                    state_data=state_data,
                )

                # Progress output every 30 ticks (minute)
                if tick_counter % 30 == 0:
                    action_type = chosen_action.get("type") if chosen_action else "none"
                    was_conflict = decision.get("was_conflict", False)
                    print(f"[{time.strftime('%H:%M:%S')}] tick={tick_counter:4d} | "
                          f"action={action_type:22s} | conflict={was_conflict}")

            except Exception as e:
                logger.error("Tick %d failed: %s", tick_counter, e)
                import traceback
                traceback.print_exc()

            time.sleep(2)

    import threading
    tick_thread = threading.Thread(target=tick_loop, daemon=True)
    tick_thread.start()

    # Keep running
    try:
        while tick_thread.is_alive():
            tick_thread.join(timeout=10)
    except KeyboardInterrupt:
        print(f"\n[{time.strftime('%H:%M:%S')}] Stopping tick loop...")
        running = False
        tick_thread.join(timeout=5)
        print(f"[{time.strftime('%H:%M:%S')}] Stopped at tick {tick_counter}")


if __name__ == "__main__":
    main()
