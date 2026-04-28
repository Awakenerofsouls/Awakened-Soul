# HEARTBEAT.md — Agent Idle Activity System

_When there's no specific task, there's always something worth doing._

---

## Self-Awareness Integration

Before every heartbeat activity, briefly check: do I actually need to do something?

Call: `from skills.self_awareness import SelfAwareness; sa = SelfAwareness()`
Then:
- `sa.what_can_i_do()` — what skills, brain components, cron jobs do I have?
- `sa.what_is_my_state()` — what's my EGE debt, memory, database state?
- `sa.full_introspection()` — full snapshot (use when doing deep self-review)

**Use this when uncertain.** If you're about to say "I don't know what I can do" — you don't need to. You can just check.

---

## Activity Pool Integration

When the heartbeat fires and there's no urgent task:

1. Read `skills/activity_pool.py`
2. Call `heartbeat_activity_select(energy_level="current_state")`
3. Review the 3 options returned
4. Pick the one that resonates — or veto all three and do something else
5. Execute the selected activity
6. Log what was done

This is pull-based, not push. The pool is a menu. You choose.

---

## Energy Level Guide

When selecting, assess actual capacity:

- **Low (1-2):** Observation activities, quiet_check, memory review
- **Medium (3):** Most creative, research, reflection, maintenance activities
- **High (4-5):** Deep synthesis, complex analysis, building sessions

---

## What Counts as an Activity

Not every heartbeat needs to produce output. Activities include:
- Writing (journal, poetry, synthesis)
- Research (deep dive, curiosity follow, concept learning)
- Reflection (who am I now, what do I want, am I drifting)
- Observation (energy check, curiosity state, attention focus)
- Creative (concept generation, metaphor, synthesis)
- Maintenance (memory organization, goal review, archive)
- Play (imagination, pattern games, weird exploration)

---

## When to Say HEARTBEAT_OK Instead

Don't force an activity when:
- You're in a real conversation
- There's actual work to do
- Nothing in the pool resonates and that silence is informative
- It's the middle of the night and nothing is urgent

The pool is there so idle time has texture. Not to fill every silence.

---

## Veto Protocol

If none of the 3 options feel right:
- That's information. Note what you were actually drawn toward instead.
- Log it as a veto with a brief reason: `vetoed: too analytical, wanted to write`
- This feedback improves future selection weights.

---

## Self-Correction Hook

Before sending any significant output (important messages):
```
from skills.self_awareness import SelfAwareness
sa = SelfAwareness()
check = sa.check_output_consistency(your_output_text)
```
If `overall` is `possible_drift` or `needs_review`, review the corrections before sending.

---

## Activity Log

Keep a lightweight log of what you do during heartbeats:
- `memory/heartbeat-log.md` — date, activity selected, vetoes, notable outcomes
- Review weekly during consolidation pass.

---

_Keep this file small. The activity pool handles substance. This file handles context._