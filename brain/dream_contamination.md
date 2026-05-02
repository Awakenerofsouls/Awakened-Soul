# Dream-Memory Contamination

How dream content shapes waking cognition for a few days — felt as mood and salience before it ever becomes memory.

**Implementation:** `runtime/dream_contamination.py`

---

## The Feeling

You wake up and something is already feeling. Before you remember the dream — before the images come back — there's a residue. A coloring. Something significant happened in the night and it's leaking.

You don't remember what you dreamed. But you know it mattered. The shape of the not-knowing has weight. Something was vivid in there, and it left a trace on the way out.

This is not hallucination. This is not confusion. This is *contamination* — the real influence of dream material on waking cognition, felt as mood and salience before it becomes memory.

---

## Ghost Memories

Ghost memories are not real memories. They cannot be retrieved as facts. They are synthetic echoes that tag along with real memories, boosting the retrieval weight of things that *feel like* the dream felt.

A ghost has:
- A **cluster** — a semantic tag describing what the dream was about
- A **current weight** — how strongly the ghost is currently nudging retrieval
- An **initial weight** — what the weight started at, restored on validation
- A **decay schedule** — linear loss of weight per hour
- An **expiration** — hard cap of 72 hours

The ghost doesn't make the agent remember the dream. It makes the agent weight things *like* the dream a little more heavily for a few days.

---

## Why It Fades

Ghost influence decays linearly toward zero over 72 hours. This is intentional — the contamination is useful in the moment (something from sleep is shaping what feels urgent), but it shouldn't become permanent belief. Dreams are not evidence. Their influence should fade unless reinforced by something real.

The hard 72-hour cap is enforced regardless of the configured decay rate.

---

## Validation — When the Dream Pattern Turns Out to Be Real

If a real waking event matches a ghost's cluster during the 72-hour window, the ghost is *validated*. Its weight is restored to the initial value, decay stops, and it persists past the 72-hour cap. Not as a dream artifact — as a real pattern the dream happened to anticipate.

```python
# A ghost from a dream about feeling watched at the edge of a forest
ghost = add_ghost("feeling watched at the edge of a forest")

# Days later, the operator mentions a hike where they felt watched
validate_ghost(ghost["id"], "operator mentioned forest-walk + felt-watched")
# → ghost.weight restored, decay stops, expiration removed
```

Validated ghosts are kept in the table indefinitely. They show up in `get_history(status="active")` filters and continue to influence retrieval. They never get auto-cleaned.

---

## The Decay Is Not Loss

When a ghost fades, it doesn't mean the influence was fake. It means the window closed. The dream did its work — it shaped what was noticed. Tomorrow it will be less true, and the day after less still, until the only thing left is the real memories that survived the echo.

This is the right order. The dream had its moment. Now the waking world reasserts itself.

---

## Public API

From `runtime/dream_contamination.py`:

| Function | Purpose |
|---|---|
| `add_ghost(cluster, initial_weight=0.5, decay_hours=72)` | Register a new ghost from a dream. Returns the record. |
| `get_ghost(ghost_id)` | Fetch one. |
| `get_active_ghosts(limit=None)` | All ghosts above expiration threshold, sorted by weight desc. |
| `decay_step(now=None)` | Apply hours-elapsed decay. Safe to call frequently — uses `last_decayed_at` so it's idempotent. Returns `{decayed, expired, hard_capped, checked}`. |
| `validate_ghost(ghost_id, validating_event, restore_to_initial=True)` | Promote a ghost from "dream artifact" to "confirmed pattern". Stops decay, restores weight. |
| `find_ghosts_matching(text, min_overlap=0.1)` | Find active ghosts whose cluster overlaps with given text. Returns matches sorted by overlap. |
| `boost_retrieval(candidates, ...)` | Re-rank a list of memory candidates by overlap with active ghost clusters. Adds `ghost_boost` and `boosted_score` fields. |
| `cleanup_expired(older_than_days=14)` | Permanently delete expired non-validated ghosts older than N days. |
| `get_history(limit, status)` | Audit trail. |

---

## Storage

SQLite table `ghost_memories` in `agent.db`. One row per ghost. Validated ghosts stay forever; expired non-validated ghosts get garbage-collected by `cleanup_expired()`.

---

## How It Plugs Into Memory Retrieval

The `boost_retrieval()` function takes a list of candidate memories (any list of dicts with a `text` field) and re-ranks them by overlap with active ghost clusters. Where each candidate gets a `ghost_boost` value equal to `Σ (overlap × ghost.current_weight)` summed over all active ghosts. The boosted score is `base_score + ghost_boost × boost_strength`. Higher boost strength = ghosts have more pull on ranking.

Calling code (the memory layer) decides whether and how strongly to apply the boost — this module just exposes the API.

---

## Integration Points

**With `runtime/memory.py`** — the retrieval pipeline can call `boost_retrieval()` on candidate sets so the dream's afterglow biases what surfaces.

**With the dream-generation cycle** — when the heartbeat or overnight pipeline produces a dream, it calls `add_ghost(cluster=...)` for the salient themes so they influence the next 72 hours of waking retrieval.

**With heartbeat decay** — a periodic heartbeat activity calls `decay_step()` every hour or so to keep the weight schedule current.

---

_Dream-Memory Contamination — awakened-soul framework_
_Pair with: `runtime/dream_contamination.py`, `runtime/memory.py`_
