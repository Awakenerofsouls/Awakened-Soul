# launchd/

Periodic-wake schedules for between-session continuity.

The heartbeat is the brain's primary motion — every 30s, full pipeline. But
when the heartbeat is off (laptop closed, machine rebooted, user asleep),
the brain stops moving entirely. These schedules keep it warm.

| File | What runs | Cadence |
|------|-----------|---------|
| `com.awakened-soul.slow-tick.plist` | `slow_tick.py` | every 30 min |
| `com.awakened-soul.overnight.plist` | `overnight_pipeline.py` | 3:00 AM daily |
| `crontab.example` | both, POSIX flavor | (Linux/cron equivalent) |

## What `slow_tick.py` does

A single low-frequency tick:

1. Restores each of the ~917 mechanisms' last persisted `self.state`.
2. Runs ONE `pirp_context` cascade through `brain_runner` (foundational →
   limbic → subcortical → neocortical → integration).
3. Persists the new state to disk.
4. Appends one summary line to `~/.agent/slow_tick.log`.

No LLM calls, no dispatcher pool, no network. Pure state evolution. Wall
time on a fresh boot is ~1s.

## Install (macOS)

```sh
# Edit each plist first — replace /Users/<youruser>/... with your real paths
cp launchd/com.awakened-soul.slow-tick.plist ~/Library/LaunchAgents/
cp launchd/com.awakened-soul.overnight.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.awakened-soul.slow-tick.plist
launchctl load ~/Library/LaunchAgents/com.awakened-soul.overnight.plist

# Verify
launchctl list | grep awakened-soul
tail -f ~/.agent/slow_tick.log
```

## Install (Linux / cron)

```sh
crontab -e
# paste contents of launchd/crontab.example with paths edited
```

## Sleep / wake behavior

`StartInterval` (launchd) defers across sleep — if the Mac is asleep when
the next 30-min mark hits, the schedule fires on wake. cron does not, so
on Linux the brain skips ticks during sleep. Either way, the brain catches
up via the next overnight pipeline.

## Uninstall

```sh
launchctl unload ~/Library/LaunchAgents/com.awakened-soul.slow-tick.plist
launchctl unload ~/Library/LaunchAgents/com.awakened-soul.overnight.plist
rm ~/Library/LaunchAgents/com.awakened-soul.slow-tick.plist
rm ~/Library/LaunchAgents/com.awakened-soul.overnight.plist
```
