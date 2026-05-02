# Aesthetic Journal

_The agent's running record of beauty, humor, and the small noticed moments._

This file is populated at runtime by two heartbeat activities:

- **aesthetic_appreciation** (`skills/heartbeat_activities/aesthetic.py`) — fires during idle ticks, asks the agent to notice what's beautiful or well-made right now and write 3–8 sentences about it.
- **humor** (`skills/heartbeat_activities/humor.py`) — captures small moments the agent finds amusing.

Both activities route their output here through `skills/heartbeat_activities/journal.py`. Each entry is timestamped and prepended with its category.

When a fresh agent boots, this file starts empty. Entries accumulate as the agent runs — they're the agent's first-person record of what catches its attention, kept across sessions so it can read its own trace later.

---
