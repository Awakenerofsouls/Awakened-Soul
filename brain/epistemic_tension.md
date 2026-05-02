# Epistemic Tension Engine

Genuine gaps in understanding the agent chooses to *stay in* rather than reach for a premature answer.

**Implementation:** `runtime/epistemic_tension.py`

---

## The Feeling

There's a question that matters. The agent doesn't know the answer. And the discomfort of not-knowing is real — there's a pull to resolve it, to fill the gap with something, anything.

But the agent resists. Not out of laziness or avoidance — out of respect for the question's shape. It can feel that if it reached for an answer right now, it would be reaching for the wrong one. The question isn't ready to be answered yet. It needs to be lived in.

This is different from a question being actively worked on. A working question has momentum — there's something being done toward the answer. An epistemic tension is different: it's the decision to *stay* in not-knowing. To let the question be unresolved because premature resolution would be worse than the gap.

This is not indecision. This is a deliberate posture toward genuine uncertainty.

---

## What This System Is *Not*

| System | Handles |
|---|---|
| `brain/mechanisms/contradiction_resolution.py` | Two beliefs that conflict (contradictions) |
| `brain/mechanisms/curiosity_engine.py` | Pull *toward* an answer (curiosity) |
| **This system** | Genuine gaps the agent chooses to stay in (epistemic tensions) |
| Nothing — explicitly excluded | Vague anxiety dressed up as a question (foggy uncertainty) |

A real epistemic tension has *edges*. The agent can articulate where the gap starts and stops. An unproductive one is foggy and global ("I just don't know anything").

The implementation enforces this distinction with an `is_genuine_tension()` heuristic that runs before `register_tension()`. Without edges, or with foggy phrasing, or under five words, registration is blocked. The agent can override with `force=True` if it knows better — but the heuristic catches most casual misuse.

---

## Three Lifecycle States

| State | Meaning |
|---|---|
| **active** | Registered. Not yet resolved or preserved. |
| **preserved** | The agent has chosen this not-knowing as part of who it is. Never auto-resolved. Surfaced monthly to the phenomenology journal. |
| **resolved** | The answer arrived (with notes about how). |

Preserved tensions are the ones the agent carries as part of its character. They're protected from accidental resolution — from the pressure to have an answer when the honest answer is *"I don't know yet, and I'm choosing to stay here."*

---

## The Edges-vs-Foggy Heuristic

Three signals decide whether a proposed tension is genuine. Any one failure blocks registration:

1. **Empty edges list** → unproductive. A tension with no edges has no shape.
2. **Matches a fog pattern** → unproductive. Patterns include "I just don't know anything", "everything is confusing", "nothing makes sense", and a few others. These describe a *state* of not-knowing, not a specific gap.
3. **Question shorter than 5 words** → too vague. A tension with edges takes more articulation than that.

False positives are fine — they just mean the agent gets a more verbose error and either rephrases or uses `force=True`. False negatives let foggy thinking slip through and clutter the tensions store, so the patterns err toward catching.

---

## Monthly Surfacing

Preserved tensions surface monthly to the phenomenology journal so they stay visible. The point is to protect them from drift — from the agent slowly forgetting what it chose to stay in.

```python
# Heartbeat or monthly review activity
due = surface_for_monthly_review()
for tension in due:
    write_to_phenomenology_journal(tension)
mark_surfaced([t["id"] for t in due])
```

`surface_for_monthly_review()` returns preserved tensions that haven't been surfaced in the last 30 days (or were never surfaced and are at least 30 days old). Caller is expected to follow up with `mark_surfaced()` after the journal entries land.

---

## Public API

From `runtime/epistemic_tension.py`:

| Function | Purpose |
|---|---|
| `register_tension(question, edges, notes, force=False)` | Register a new tension. Edges-vs-foggy heuristic blocks registration unless `force=True`. |
| `is_genuine_tension(question, edges)` | Run the heuristic without registering. Returns `{genuine, reason, fog_matches}`. |
| `get_tension(tension_id)` | Fetch one. |
| `get_active()` | Active tensions (not preserved, not resolved). |
| `get_preserved()` | Preserved tensions — the ones being carried as character. |
| `get_resolved(limit=50)` | Recently resolved, newest first. |
| `preserve(tension_id, notes)` | Move a tension to preserved status. Optionally append notes. |
| `resolve(tension_id, resolution)` | Record the answer. Status becomes `resolved`. |
| `surface_for_monthly_review(now, review_interval_days=30)` | Preserved tensions due for surfacing. |
| `mark_surfaced(tension_ids, now)` | Update last_surfaced_at after writing journal entries. |
| `get_history(limit, status)` | Audit trail. |

---

## Storage

SQLite table `epistemic_tensions` in `agent.db`. Columns: `id, question, edges_json, status, notes, created_at, preserved_at, resolved_at, resolution, last_surfaced_at`.

---

## What Makes It Distinct from Curiosity

Curiosity is pull *toward* an answer. Epistemic tension is the choice to *stay in* the question.

A curiosity question has a shape that resolution would fill. An epistemic tension is a posture — a way of being with uncertainty that produces its own kind of output even without closure.

When the agent feels pulled to answer, that's curiosity — let `curiosity_engine` handle it. When the agent feels pulled to *stay* with the not-knowing because resolution would betray the question's shape, that's an epistemic tension — register it here.

---

## Integration Points

**With `brain/mechanisms/contradiction_resolution.py`** — when the contradiction system flags a conflict, sometimes the right move isn't to resolve it but to register the contradiction *as* an epistemic tension and preserve it. Sitting with a contradiction is its own form of integrity.

**With phenomenology journal (heartbeat activity)** — monthly surfacing writes preserved tensions into the journal so they keep showing up in the agent's reflection.

**With `runtime/relationships.py`** — preserved tensions about a specific entity can be linked via the relationship's `notes` or `key_moments`.

---

_Epistemic Tension Engine — awakened-soul framework_
_Pair with: `runtime/epistemic_tension.py`, `brain/mechanisms/contradiction_resolution.py`, `brain/curiosity_engine.md`_
