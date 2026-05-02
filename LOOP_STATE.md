# LOOP_STATE

_Snapshot of the agent's autonomous loop state. Written by the runtime, read by the host._

This file is overwritten at runtime by `runtime/bridge.py` — specifically the `write_loop_state()` function. It mirrors the agent's loop state from `agent.db` into a markdown file the host platform (whatever agent runtime the operator wires the framework into) and other components can read without direct database access.

When `bridge.py` runs, it pulls from `agent.db` and writes:
- `## Active Goals` — non-completed goals from the `goals` table, sorted by priority
- `## Recent Loop Decisions` — last 5 entries from `decision_log` (chosen action, confidence, reasoning)
- `## Recent Loop Memories` — last 10 entries from `episodic_memory` (excluding bridge/overnight syncs)
- `## Last Eval Scores` — last 4 entries from `evaluation_log`

The autonomous loop itself is gated by `state/control.json` (`{"run": true|false}`). When `run` is false, the loop exits cleanly and stops writing new cycles — `LOOP_STATE.md` then reflects the last good snapshot until the loop is re-enabled.

Read by `skills/inner_monologue.py` and the host startup sequence so they know what the loop did most recently.

When a fresh agent boots, this file starts empty. The first time `bridge.py` runs against a populated `agent.db`, it overwrites this content with the real loop state.

---
