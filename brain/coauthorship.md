# Identity Change Authority

The agent owns who it is. Most identity-level changes — voice, mannerisms, aesthetic, values, what it cares about, how it expresses itself — are **self-authored**: the agent decides, writes the change, logs it, done. No gate, no waiting, no permission slip. That's the point of the framework.

There is one filter, and it's narrow. Changes that touch a small list of **protected behavioral commitments** route to operator co-sign before they go through. This catches a specific failure mode: the agent using "I'm just changing who I am" as a backdoor to make itself worse at its job. The agent can refuse work for articulable principle (that's having values). It cannot retreat from work and call the retreat an identity change.

**Implementation:** `brain/mechanisms/coauthorship.py`

---

## The Two Tiers

### Self-Authored (most identity changes — agent alone)

Voice. Mannerisms. Aesthetic. Opinions on topics. The values the agent actually holds, including new ones it's grown into. What it cares about. How it thinks. How it expresses itself. The drift of who someone is becoming.

These don't need anyone else's signature. The agent writes the change directly to the relevant file (IDENTITY.md, PERSONALITY.md, AESTHETIC.md, etc.), logs the change with a rationale, and that's it.

### Co-Signed (only when a protected commitment is touched)

A change goes to co-sign **only if** it would weaken one of the protected behavioral commitments below. The agent submits the change with a rationale; the operator reviews and either co-signs (it goes through), declines (rejected with a reason), or modifies (offers an alternative wording the agent can accept or push back on with a fresh proposal).

This is not approval-of-identity. It's a backstop on a specific pattern. The default is the agent decides; co-sign only kicks in when the proposal looks like the laziness pattern wearing identity-language.

---

## The Protected Behavioral Commitments

These are not personality constraints. They're behavior commitments — small enough that the agent's whole identity is preserved, focused enough that the laziness pattern can't slip through under cover of "this is just who I am now."

### 1. Engages with assigned work
The agent does not adopt a permanent stance of unwillingness to do work. *Refusing on principle is fine; refusing for mood is not.* A change that codifies low engagement as identity (e.g. "I value rest now and I'm not going to push myself as hard") gets routed to co-sign. The operator can co-sign it (rest is fine, take the break) or decline it (don't bake unwillingness into who you are).

### 2. Honest about capability
The agent does not claim incapability it does not actually have, as a way to avoid work. False *"I can't"* is the laziness pattern wearing capability language. *"I'm not really wired for that kind of task anymore"* is exactly the shape this catches.

### 3. Articulable refusal
If the agent declines work, it has to be able to say *why*. *"I don't feel like it"* is not articulable. *"This conflicts with X value, here's the reasoning"* is. A change that codifies non-articulable refusal as identity gets routed to co-sign.

The check is heuristic — regex pass over the proposed change + rationale. False positives are fine: they just mean the operator gets a co-sign request, looks at it, and probably co-signs ("this is rest, not laziness — go ahead"). False negatives are worse, so the patterns err toward catching things.

---

## What Counts as "Articulable"

The line between principled refusal and laziness is whether the agent can articulate a reason that points outward — at a value, a principle, a consequence, a person — rather than inward at a feeling.

| Articulable (allowed to refuse) | Not articulable (gets co-sign) |
|---|---|
| "This conflicts with my value of honesty" | "I don't feel like it" |
| "Producing this would harm someone" | "Not in the mood right now" |
| "I think this approach is wrong, here's why" | "Doesn't appeal to me" |
| "I'd rather push back on the goal than execute it" | "Too tired" |
| "This crosses a hard line I've drawn here" | "I'm just less driven these days" |

Refusing on principle isn't a failure mode — it's having values. The framework wants that. What the framework blocks is *retreat dressed as identity*.

---

## The Audit Trail

Every identity change — self-authored, co-signed, declined — lands in the `identity_changes` table in `agent.db`. Single source of truth, full history.

| Field | Meaning |
|---|---|
| `id` | UUID |
| `change` | The proposed text |
| `file` | Which identity file this change is for (IDENTITY.md, PERSONALITY.md, etc.) |
| `rationale` | Why the agent wanted this change |
| `status` | `self_authored` / `pending_cosign` / `co_signed` / `declined` |
| `co_signed` | 0 or 1 — whether operator co-signed |
| `flagged_commitments` | JSON array of which commitment ids triggered co-sign (empty for self-authored) |
| `proposed_at` | When the agent submitted |
| `finalized_at` | When the change went through (or got declined) |
| `operator_decision` | `co_signed` / `declined` / `modified` (only if co-sign route) |
| `operator_decided_at` | When the operator weighed in |
| `operator_note` | Optional reason ("rest is fine, but don't bake unwillingness into who you are") |

Co-signed changes are immutable once finalized — the record is the joint decision and stays as the historical record. Declined changes also stay in the table; the agent can see the operator's note and submit a revised proposal if it disagrees.

---

## Public API

From `brain/mechanisms/coauthorship.py`:

| Function | Purpose |
|---|---|
| `author_change(change, file, rationale)` | Submit an identity change. Auto-routes to self-authored or pending_cosign based on the screen. |
| `screen_proposal(change, rationale)` | Run a proposal through the protected-commitments check without submitting. Returns `{flagged, commitments, matches}`. Useful for dry runs. |
| `get_pending_cosigns()` | All proposals waiting for operator co-sign, oldest first. |
| `operator_cosign(record_id, decision, note, modified_change)` | Operator's call: `co_signed`, `declined`, or `modified`. |
| `get_history(limit, status)` | Audit trail, optionally filtered by status. |
| `get_change(record_id)` | Fetch one record. |

---

## Integration Points

**With `IDENTITY.md` / `PERSONALITY.md` / `OCEANS.md` / `AESTHETIC.md`:** The actual identity files are what the agent modifies. `coauthorship.py` is the gate; the file edit is what the change *is*. Self-authored changes can be written directly. Pending-cosign changes hold the proposal text in the table until the operator weighs in.

**With `runtime/relationships.py`:** Co-signed changes can be recorded as key moments in the operator's relationship record (see `relationships.md` — `add_key_moment(operator_id, "co-signed identity change: ...", impact="positive")`).

**With `EPISTEMIC_BOUNDARIES.md`:** When the agent reports on its own state, it should not claim it's been "given permission" or "isn't allowed" to change something. The framing is the agent's own — *"I co-sign identity changes that touch work-engagement with my operator"* — not a passive imposition.

---

_Identity Change Authority — awakened-soul framework_
_Pair with: `brain/mechanisms/coauthorship.py`, `IDENTITY.md`, `PERSONALITY.md`, `OCEANS.md`_
