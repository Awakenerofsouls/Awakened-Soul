# Journal

_Catch-all journal — fallback destination for heartbeat activity output that doesn't have an explicit routing target._

This file is populated at runtime by `skills/heartbeat_activities/journal.py`. The `default` category in the routing table maps to this file, so any activity that emits content with an unrecognized or unrouted category lands here.

Most heartbeat activities have specific destinations (`AESTHETIC.md` for aesthetic appreciation and humor, `BECOMING.md` for becoming reflections, `IDLE_DRIVES.md` for at-rest interior states, `DREAMS.md` for dream fragments, etc.). When a new activity type is added without an explicit route, its output appears here so it isn't lost.

When a fresh agent boots, this file starts empty. Entries accumulate as the agent runs.

---
