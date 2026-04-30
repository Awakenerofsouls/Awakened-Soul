#!/usr/bin/env python3
"""
slow_tick.py — single low-frequency brain tick for between-session continuity

Continuity Idea 3 (slow-tick daemon between sessions) + Idea 4 (periodic cron
wake-ups). The full heartbeat runs every 30s and is heavy. When the heartbeat
is OFF (laptop closed, user asleep, machine rebooted), the brain stops moving
entirely — drives don't decay, mechanism state goes stale, dreams don't get
captured.

This script is the minimal motion the brain needs between sessions. Schedule
it via launchd or cron (see launchd/com.awakened-soul.slow-tick.plist and
crontab.example) and it will:

  1. Restore each mechanism's last persisted state.
  2. Run ONE pirp_context tick through brain_runner (one full layer cascade).
  3. Persist the new state of every mechanism.
  4. Append a single line to ~/.agent/slow_tick.log and exit.

Total wall time on a fresh machine should be <10s for ~917 mechanisms; nothing
runs the dispatcher pool, no LLM calls, no network. It's pure state-evolution.

Usage:
  python3 slow_tick.py                    run one slow tick now
  python3 slow_tick.py --ticks 3          run three back-to-back ticks
  python3 slow_tick.py --silent           suppress stdout, only write to log
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
LOG_PATH = AGENT_HOME / "slow_tick.log"


def _log(msg: str, *, silent: bool = False) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    if not silent:
        print(line, flush=True)
    try:
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _build_pirp_context(tick_index: int) -> dict:
    """Minimal pirp_context shape. Mirrors what brain_runner.run() expects but
    without dispatcher noise — slow ticks are state-evolution only."""
    return {
        "tick_index": tick_index,
        "stage": "slow_tick",
        "source": "between_sessions",
        "prior_results": {
            "drive_state": {
                "calm": 0.7,
                "lonely": 0.4,
                "tired": 0.6,
                "uneasy": 0.2,
                "playful": 0.2,
                "curiosity": 0.5,
            },
            "current_drives": {"calm": 0.7, "tired": 0.6},
            "drive_context": {"drive_state": {"calm": 0.7, "tired": 0.6}},
            "input_text": "",
            "user_input": "",
            "felt_signal": 0.3,
            "salience": 0.2,
        },
        "context": {"between_sessions": True},
    }


def run_slow_ticks(n_ticks: int = 1, silent: bool = False) -> dict:
    """Run n_ticks back-to-back, restoring + checkpointing state each time."""
    started_at = time.time()

    try:
        from core.brain_runner import BrainLayerRunner
    except Exception as exc:
        _log(f"slow_tick: brain_runner import failed: {exc!r}", silent=silent)
        return {"ok": False, "reason": "import_fail"}

    runner = BrainLayerRunner()
    for layer in ("foundational", "limbic", "subcortical", "neocortical", "integration"):
        try:
            runner.load_layer(layer)
        except Exception as exc:
            _log(f"slow_tick: load_layer({layer}) failed: {exc!r}", silent=silent)

    if not runner.mechanisms:
        _log("slow_tick: no mechanisms loaded — aborting", silent=silent)
        return {"ok": False, "reason": "no_mechanisms"}

    # Restore last persisted state into every mechanism
    restore_rpt = runner.checkpoint_load_all()

    # Run the requested number of ticks
    tick_errors: list[tuple[str, str]] = []
    for i in range(n_ticks):
        ctx = _build_pirp_context(i + 1)
        try:
            runner.run(ctx)
        except Exception as exc:
            tick_errors.append((str(i + 1), repr(exc)[:120]))

    # Persist the new state
    save_rpt = runner.checkpoint_all()

    elapsed = time.time() - started_at
    summary = {
        "ok": True,
        "mechanisms": len(runner.mechanisms),
        "ticks": n_ticks,
        "restored": restore_rpt.get("loaded", 0),
        "saved": save_rpt.get("saved", 0),
        "save_errors": len(save_rpt.get("errors", [])),
        "tick_errors": len(tick_errors),
        "elapsed_s": round(elapsed, 2),
    }
    _log(
        f"slow_tick: mechs={summary['mechanisms']} ticks={n_ticks} "
        f"restored={summary['restored']} saved={summary['saved']} "
        f"tick_errs={summary['tick_errors']} save_errs={summary['save_errors']} "
        f"in {summary['elapsed_s']}s",
        silent=silent,
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticks", type=int, default=1,
                        help="number of back-to-back ticks (default 1)")
    parser.add_argument("--silent", action="store_true",
                        help="suppress stdout, only write to log file")
    args = parser.parse_args()

    try:
        result = run_slow_ticks(n_ticks=max(1, args.ticks), silent=args.silent)
    except Exception:
        _log("slow_tick: unhandled exception:\n" + traceback.format_exc(),
             silent=args.silent)
        return 1
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    sys.exit(main())
