"""
{{AGENT_NAME}} heartbeat runner.

Boot:    load state → load operator plugins → log registered activities
Loop:    tick → dispatch activity → if proactive, send to dashboard
         → save state periodically → sleep → repeat
Shutdown: save state on SIGTERM/SIGINT

Tick structure:
  TICK_INTERVAL = 30s
  Activity every 3 ticks (90s between activities) — matches {{AGENT_NAME}}'s historical cadence
  State saved every 10 ticks (5 min)
  Status logged every 60 ticks (30 min)
"""

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Ensure workspace is on sys.path before any module imports ───────────────
# runner.py lives at skills/heartbeat_activities/runner.py
# brain_proxy lives at workspace/brain_proxy.py
# heartbeat_activities lives at workspace/skills/heartbeat_activities/
# Need BOTH workspace/skills/ AND workspace/ on the path
_SKILLS_ROOT = os.path.expanduser("~/.openclaw/workspace/skills")
_WORKSPACE_ROOT = os.path.expanduser("~/.openclaw/workspace")
for _p in (_SKILLS_ROOT, _WORKSPACE_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import heartbeat_activities.dispatcher as dispatcher
from heartbeat_activities.plugin_loader import load_operator_plugins
from heartbeat_activities.proactive import send_proactive

# Brain integration — runs registered mechanisms every tick
from brain_proxy import core_tick as _brain_core_tick


# ── Configuration ────────────────────────────────────────────

TICK_INTERVAL = 30          # seconds between ticks
ACTIVITY_EVERY = 3          # fire activity every N ticks
STATE_SAVE_EVERY = 10       # save state every N ticks
STATUS_LOG_EVERY = 60       # log status every N ticks

WORKSPACE = os.environ.get("AGENT_WORKSPACE", "~/.openclaw/workspace")
STATE_FILE = os.environ.get("AGENT_STATE_FILE", "~/.agent/heartbeat_state.json")
OPERATOR_PLUGIN_DIR = os.environ.get("AGENT_PLUGIN_DIR", "~/.agent/activities")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M UTC",
)
log = logging.getLogger("heartbeat.runner")


# ── State management ─────────────────────────────────────────

def load_state(path: str) -> dict:
    """Load heartbeat state from JSON file. Returns fresh state if missing."""
    state_path = Path(path).expanduser()
    if state_path.exists():
        try:
            with state_path.open() as f:
                raw = json.load(f)
                return {
                    "tick_count": raw.get("tick_count", 0),
                    "unfinished_threads": raw.get("unfinished_threads", []),
                    "last_news": raw.get("last_news", {}),
                    "last_tool": raw.get("last_tool", {}),
                    "last_skill": raw.get("last_skill", {}),
                    "last_deep_curiosity": raw.get("last_deep_curiosity", {}),
                    "last_deep_dive": raw.get("last_deep_dive", {}),
                    "prior_contents": raw.get("prior_contents", {}),
                }
        except Exception as e:
            log.warning("Could not load state file: %s — starting fresh", e)
    return fresh_state()


def save_state(state: dict, path: str) -> None:
    """Persist heartbeat state to JSON file."""
    state_path = Path(path).expanduser()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {
        "tick_count": state.get("tick_count", 0),
        "unfinished_threads": state.get("unfinished_threads", []),
        "last_news": state.get("last_news", {}),
        "last_tool": state.get("last_tool", {}),
        "last_skill": state.get("last_skill", {}),
        "last_deep_curiosity": state.get("last_deep_curiosity", {}),
        "last_deep_dive": state.get("last_deep_dive", {}),
        "prior_contents": state.get("prior_contents", {}),
    }
    tmp = state_path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(serializable, f, indent=2)
    tmp.rename(state_path)


def fresh_state() -> dict:
    """Return a fresh heartbeat state dict."""
    return {
        "tick_count": 0,
        "unfinished_threads": [],
        "last_news": {},
        "last_tool": {},
        "last_skill": {},
        "last_deep_curiosity": {},
        "last_deep_dive": {},
        "prior_contents": {},
    }


# ── Runner ───────────────────────────────────────────────────

class HeartbeatRunner:
    """Main heartbeat loop."""

    def __init__(self):
        self.running = False
        self.state: dict = {}

    def boot(self) -> None:
        """Initialize: load state, load plugins, register with dispatcher."""
        log.info("{{AGENT_NAME}} heartbeat starting...")
        log.info("Workspace: %s", WORKSPACE)

        self.state = load_state(STATE_FILE)
        self.state["WORKSPACE"] = WORKSPACE

        # Merge brain signal config from boot_config.json (if present)
        boot_config_path = Path("~/.agent/state/boot_config.json").expanduser()
        if boot_config_path.exists():
            try:
                with boot_config_path.open() as f:
                    boot_cfg = json.load(f)
                for key in ("BRAIN_SIGNAL_FILES", "AROUSAL_SIGNAL", "TEMPERATURE_RANGE"):
                    if key in boot_cfg:
                        self.state[key] = boot_cfg[key]
                log.info("Loaded brain signal config from %s", boot_config_path)
            except Exception as e:
                log.warning("Could not load boot_config.json: %s — signal wiring inactive", e)

        # Load operator plugins into the dispatcher's registry
        plugins_loaded = load_operator_plugins(OPERATOR_PLUGIN_DIR)

        # Register operator plugins with the dispatcher
        registry = dispatcher.ACTIVITY_REGISTRY
        from heartbeat_activities.plugin_loader import get_registry
        operator_plugins = get_registry()
        for category, run_fn in operator_plugins.items():
            if category not in registry:
                dispatcher.register_plugin(category, run_fn)

        activity_count = len(dispatcher.ACTIVITY_REGISTRY)
        log.info(
            "Registered %d activities (framework + operator plugins)",
            activity_count,
        )
        log.info(
            "Tick interval: %ds, activity every %d ticks (%.0fs between activities)",
            TICK_INTERVAL, ACTIVITY_EVERY, TICK_INTERVAL * ACTIVITY_EVERY,
        )

    def tick(self) -> None:
        """Run one tick: advance brain mechanisms, dispatch an activity, update state."""
        self.state["tick_count"] += 1
        tick = self.state["tick_count"]

        # Advance AgentBrainCore: all registered mechanisms run in one pass.
        # brain_runner is registered FIRST (brain_integration.py _register_components);
        # it publishes brain_layer before VIF/PDS/SS/MRE read it — no lag.
        try:
            _brain_core_tick()
        except Exception as e:
            log.warning("Brain core tick error (tick %d): %s", tick, e)

        _update_continuation_of(self.state)

        if tick % ACTIVITY_EVERY == 0:
            self._run_activity(tick)

        if tick % STATE_SAVE_EVERY == 0:
            save_state(self.state, STATE_FILE)

        if tick % STATUS_LOG_EVERY == 0:
            self._log_status(tick)

    def _run_activity(self, tick: int) -> None:
        """Dispatch one activity and handle the result."""
        try:
            result = dispatcher.dispatch(self.state)
            category = result.get("category", "?")
            status = result.get("status", "?")
            proactive = result.get("proactive", False)
            ok = result.get("ok", False)

            log.info(
                "Tick %d: [%s] %s (%s) ok=%s proactive=%s",
                tick, category, status,
                result.get("detail", ""), ok, proactive,
            )

            if proactive and result.get("content"):
                content = result.get("content", "")
                sent = send_proactive(content)
                log.info("Proactive sent to dashboard: %s", "OK" if sent else "FAILED")

            if status.startswith("unfinished") or status.startswith("followup"):
                _track_unfinished(self.state, result)

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            log.error("Activity dispatch error (tick %d): %s\n%s", tick, e, tb)

    def _log_status(self, tick: int) -> None:
        """Emit a status heartbeat log line."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        threads = len(self.state.get("unfinished_threads", []))
        log.info(
            "Status @ tick %d (%s): uptime=%.1f min, unfinished_threads=%d, activities_total=%d",
            tick, now, tick * TICK_INTERVAL / 60, threads, len(dispatcher.ACTIVITY_REGISTRY),
        )

    def install_signal_handlers(self) -> None:
        """Install SIGTERM/SIGINT handlers for graceful shutdown."""
        def shutdown(signum, frame):
            log.info("Shutdown signal %d — saving state and exiting...", signum)
            self.running = False
        signal.signal(signal.SIGTERM, shutdown)
        signal.signal(signal.SIGINT, shutdown)

    def run(self) -> None:
        """Start the heartbeat loop."""
        self.boot()
        self.install_signal_handlers()
        self.running = True

        log.info("Heartbeat loop running. PID=%d", os.getpid())
        log.info("Press Ctrl+C or send SIGTERM to stop gracefully.")

        while self.running:
            try:
                self.tick()
                time.sleep(TICK_INTERVAL)
            except Exception as e:
                log.error("Tick error: %s", e)
                time.sleep(TICK_INTERVAL)

        save_state(self.state, STATE_FILE)
        log.info("Heartbeat stopped. State saved.")


# ── Helpers ──────────────────────────────────────────────────

def _update_continuation_of(state: dict) -> None:
    """Set continuation_of from oldest unfinished thread."""
    threads = state.get("unfinished_threads", [])
    if threads:
        oldest = min(threads, key=lambda t: t.get("created_tick", 0))
        state["continuation_of"] = oldest.get("category", "")
    else:
        state.pop("continuation_of", None)


def _track_unfinished(state: dict, result: dict) -> None:
    """Track an unfinished result in the unfinished_threads list."""
    category = result.get("category", "")
    content = result.get("content", "")
    tick = state.get("tick_count", 0)

    threads = state.setdefault("unfinished_threads", [])
    threads = [t for t in threads if t.get("category") != category]
    state["unfinished_threads"] = threads

    if content:
        threads.append({
            "category": category,
            "created_tick": tick,
            "content_preview": content[:200],
        })


# ── Entry point ──────────────────────────────────────────────

def main():
    runner = HeartbeatRunner()
    runner.run()


if __name__ == "__main__":
    main()