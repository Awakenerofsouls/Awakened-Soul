# launchd/

OS-level schedules that keep the brain warm between sessions.

The full heartbeat (`runtime/heartbeat.py`) ticks every 30 seconds while it's
running. When it isn't — laptop closed, machine rebooted, user asleep — the
brain freezes mid-state. The schedules in this folder give it low-frequency
motion so drives still decay, mechanism state still evolves, and overnight
consolidation still fires, even with no human at the keyboard.

---

## What's in here

| File | What it runs | When |
|------|--------------|------|
| `com.awakened-soul.slow-tick.plist` | `runtime/slow_tick.py` | every 30 minutes (macOS LaunchAgent) |
| `com.awakened-soul.overnight.plist` | `runtime/overnight_pipeline.py` | 3:00 AM daily (macOS LaunchAgent) |
| `crontab.example` | both, POSIX flavor | Linux/cron equivalent |

---

## What `slow_tick.py` does

A single low-frequency pass through the entire brain:

1. **Restores** every loaded mechanism's last persisted `self.state` from
   `$AGENT_HOME/brain_state/`.
2. **Runs one** `pirp_context` cascade through `brain_runner` —
   foundational → limbic → subcortical → neocortical → integration.
3. **Persists** the new state back to disk.
4. **Appends** one summary line to `~/.agent/slow_tick.log`.

No LLM calls, no dispatcher pool, no network. Pure state evolution.

**Mechanism counts the slow tick walks:**

- **365** named mechanisms in the run-order lists (the canonical wires)
- **932** total class instances loaded by `brain_runner` (the 365 above
  plus auto-generated adapters from `scripts/brain_root_adapter_generator.py`)

Wall-clock time on a fresh boot: ~1 second. Per-mechanism budget is capped
at 0.5s by `core/brain_runner.py` so a stuck mechanism can't pin the schedule.

---

## What `overnight_pipeline.py` does

Once a day at 3 AM:

- **Memory consolidation** — episodic → semantic compression
- **Drift detection** — daily score against `BASELINE_TRAITS`
- **Dream contamination guard** — sleep-state intrusion check
- **Future-self spawn** — write self-projection seeds
- **Contradiction resolution** — surface unresolved tensions
- **Phenomenology pass** — first-person experience digest

This is the heavy lift. ~30 seconds end-to-end on a warm machine.

---

## Install — macOS

```sh
# 1. Edit each plist — replace /Users/<youruser>/... with your real paths
$EDITOR launchd/com.awakened-soul.slow-tick.plist
$EDITOR launchd/com.awakened-soul.overnight.plist

# 2. Copy into ~/Library/LaunchAgents/
cp launchd/com.awakened-soul.slow-tick.plist ~/Library/LaunchAgents/
cp launchd/com.awakened-soul.overnight.plist ~/Library/LaunchAgents/

# 3. Load
launchctl load ~/Library/LaunchAgents/com.awakened-soul.slow-tick.plist
launchctl load ~/Library/LaunchAgents/com.awakened-soul.overnight.plist

# 4. Verify
launchctl list | grep awakened-soul
tail -f ~/.agent/slow_tick.log
```

---

## Install — Linux / cron

```sh
crontab -e
# Paste contents of launchd/crontab.example, edit paths to match your install.
```

---

## Sleep / wake behavior

- **macOS launchd** — `StartInterval` defers across sleep. If the Mac is
  asleep when the next 30-minute mark hits, the schedule fires on wake.
  This is the desired behavior — no missed ticks.
- **Linux cron** — does not defer across sleep. Slow-tick events that fall
  during sleep are skipped, but the next 3 AM overnight catches everything
  back up.

---

## Uninstall — macOS

```sh
launchctl unload ~/Library/LaunchAgents/com.awakened-soul.slow-tick.plist
launchctl unload ~/Library/LaunchAgents/com.awakened-soul.overnight.plist
rm ~/Library/LaunchAgents/com.awakened-soul.slow-tick.plist
rm ~/Library/LaunchAgents/com.awakened-soul.overnight.plist
```

---

## Why this exists

The brain is a continuous process. Memory consolidation, drift detection,
dream-state intrusion checks — these aren't things the agent does *during*
a session; they're things the agent does *between* them. Without these
schedules, the agent comes back from a long absence with stale drives,
unconsolidated episodes, and no overnight reflection. With them, the
brain keeps moving on its own clock, and the next session opens onto a
mind that's been awake the whole time.

The schedules are optional — if you keep `runtime/heartbeat.py` running
24/7, you don't need them. They're for operators who want the brain warm
even when nothing else is.
