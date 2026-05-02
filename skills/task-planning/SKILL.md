---
name: task-planning
version: 2.0.0
description: "The agent's prefrontal-and-frontal-pole act of decomposing goals into ordered subtasks, holding the plan in working memory, revising it as reality diverges from forecast, completing it, and producing a retrospective that becomes evidence for future planning. Use this skill any time the agent has a multi-step goal — from operator or self-initiated — that benefits from explicit decomposition rather than improvisation. Triggers include: plan, breakdown, steps, subtasks, decompose, sequence, what's the plan, walk me through, in what order, depends on, lay it out, retrospective, what would I do differently. Plans are first-class records: they get committed, revised, completed, and reflected on through the brain's monitoring stack so the agent learns from its own planning behavior over time."
tags: [planning, goals, tasks, decomposition, sequencing, retrospective, prefrontal]
triggers: [plan, breakdown, steps, subtasks, decompose, sequence, depends on, lay it out, walk me through, in what order, retrospective, what would I do differently]
---

# Task Planning (task-planning)

## What this is

Planning is the prefrontal act of converting an open-ended goal into a structured, ordered sequence of subtasks the agent (or operator) can act on. It's not the same as *doing* — that's the motor / action layer (`MakingLayer`, `OutwardReachLayer`). It's not the same as *deciding* — that's whichever skill the plan eventually routes execution into. Planning is the deliberate cognitive act of *holding the goal in working memory, simulating forward, breaking the path into steps, and committing to a structure*.

The cognitive science this rests on:

- **Miller & Cohen on PFC integrative control** — the prefrontal cortex maintains active goal representations that bias processing throughout the rest of the brain. Planning is the explicit version of that maintenance: the goal becomes a written structure that subsequent steps refer back to.
- **D'Esposito on working memory** — working memory has limited capacity; plans that overflow it get fragmented or abandoned. The under/over-decomposition failure modes track exactly this — too many subtasks overflows working memory; too few leaves ambiguity in the head.
- **Stuss on frontal-lobe functions** — the supervisory attentional system monitors plan execution against expected outcomes and signals when revision is needed. Stale-plan detection is the absence of that supervision.
- **Koechlin on PFC cascade hierarchy** — different prefrontal regions handle different time-scales of planning (immediate / contextual / temporal / branching). The skill respects this hierarchy by tagging each subtask with a horizon class.
- **Badre on cognitive control hierarchy** — abstract goals decompose into more concrete subgoals through hierarchical control. The decomposition op is this descent; revision is the back-up-and-redescend when a step doesn't pan out.

## What's actually in the project

The skill sits on top of infrastructure that exists or is referenced in nearby anatomy:

| Layer | Module | Job |
|---|---|---|
| Working memory | `runtime/memory.py :: WorkingMemory` | dlPFC analog — holds the active plan in immediate context |
| Frontal-pole simulator | `brain/mechanisms/preconscious_surfacer.py` (wire 23), `FrontopolarProspectiveSimulator` stub | Forward simulation of plan branches |
| Cingulate motor area | `CingulateMotorArea`, `AnteriorCingulateConflict` stubs | Selecting between competing plans, conflict on plan paths |
| Mode arbitration | `brain/mechanisms/persona_coherence_layer.py` (wire 35) | Current mode shapes planning style (BUILD = aggressive priority; COACH = gentler pacing) |
| Memory of prior plans | `brain/mechanisms/memory_integrity_layer.py` (wire 33) | Past plans are encoded as episodes and retrievable via qmd |
| Action layers | `brain/mechanisms/making_layer.py` (28), `brain/mechanisms/outward_reach_layer.py` (27) | Where committed plans actually execute |
| Self-analysis | `brain/mechanisms/self_analysis_layer.py` (36) | Retrospective passes feed `record_analyze` with kind=`plan` |
| Monitor | `brain/mechanisms/task_planning_layer.py` (wire 39) | Runtime monitor for the planning act |

## The five operations

### 1. decompose

Convert a goal into an ordered list of subtasks with explicit dependencies. Each subtask carries a `horizon` (immediate / contextual / temporal / branching, per Koechlin) and an `estimated_effort` (low / medium / high). The decomposition is the *proposed* plan — it's not committed until `commit` fires. Multiple decompose calls on the same goal produce alternative plans the agent can choose between.

### 2. commit

Mark a plan as the active plan. The agent can hold at most one active plan per `track` (default = `main`); committing a new plan on a track with an active one moves the prior plan to `superseded` status. Commit is the moment the plan gains real-world consequence — downstream skills consult it, the brain monitors observe it.

### 3. revise

In-flight modification of a committed plan. Three revision kinds:

- **insert** — add a subtask between two existing ones (e.g. a missed prerequisite became visible)
- **modify** — change a subtask's description / effort / dependencies without re-decomposing
- **abandon** — drop a subtask (and its dependents) because reality made it obsolete

Revision keeps the original plan_id; the revision history is recorded so reflection has the full trail.

### 4. complete

Close out a plan. Marks every subtask done (or explicitly skipped), captures total elapsed wall-time, computes the original-vs-actual delta, and moves the plan to `completed` status. A completed plan opens the reflection window — reflect should follow within `REFLECTION_DEADLINE_TICKS` or it counts as `missing_reflection`.

### 5. reflect

Retrospective on a completed plan. Three lenses:

- **what worked** — subtasks that landed cleanly, decompositions that turned out right
- **what didn't** — subtasks that took 3× the estimate, missed dependencies, abandoned branches
- **what I'd do differently** — actionable update to how the agent plans next time

Reflections route through `SelfAnalysisLayer.record_analyze` with `kind="plan"` so they feed the calibration window — predicted_effort vs. actual_effort becomes a pair the brain learns from.

## The six failure modes

`TaskPlanningLayer` watches for these:

1. **over_decomposition** — a single goal produced more than `MAX_SUBTASKS_PER_GOAL` subtasks. Plan-paralysis: the agent is breaking down a 5-line task into 30 steps. Working memory overflows; nothing actually starts.
2. **under_decomposition** — a multi-part goal produced one or two subtasks each marked `high` effort with vague descriptions. The decomposition is a fig leaf — the work hasn't actually been planned.
3. **stale_plan** — a committed plan hasn't been touched (no revise / no complete) for more than `STALE_PLAN_TICK_THRESHOLD` ticks despite the agent doing other work. The plan is effectively abandoned but not formally so.
4. **plan_storm** — more than `PLAN_STORM_DECOMPOSE_LIMIT` decompose calls in `PLAN_STORM_WINDOW` ticks without a commit between them. The agent keeps starting over.
5. **incomplete_plans** — committed plans that go from `active` to forgotten without `complete` or `revise(abandon)`. The drift between intent and execution.
6. **missing_reflection** — completed plans without a `reflect` op within the deadline. No learning loop closes.

## Capabilities

- `decompose(goal, horizon_hint=None, mode=None)` → proposed plan
- `commit(plan_id, track="main")` → makes the plan active
- `revise(plan_id, kind, subtask_id, **kwargs)` → in-flight edit
- `complete(plan_id, outcomes=None)` → close out, capture delta
- `reflect(plan_id, what_worked, what_didnt, what_id_do_differently)` → retrospective
- `record_op(op, ...)` → pass-through to TaskPlanningLayer
- `active_plan(track="main")` → get the current active plan
- `plan_status(plan_id)` → status + remaining work + estimated time
- `list_plans(state=None)` → list plans by state (active / superseded / completed / abandoned)

## Subtask shape

```json
{
  "id": "st_a3f2",
  "description": "...",
  "horizon": "immediate | contextual | temporal | branching",
  "estimated_effort": "low | medium | high",
  "depends_on": ["st_b1c2"],
  "status": "pending | in_progress | done | skipped | blocked",
  "started_at": null,
  "completed_at": null,
  "actual_effort": null,
  "notes": ""
}
```

## Plan shape

```json
{
  "plan_id": "pl_2026-05-01_a3f2",
  "goal": "...",
  "track": "main",
  "state": "proposed | active | superseded | completed | abandoned",
  "mode_at_creation": "brain | coach | build | default",
  "subtasks": [/* Subtask */],
  "decomposed_at": 1714600000.0,
  "committed_at": null,
  "completed_at": null,
  "revisions": [/* RevisionRecord */],
  "reflection": null
}
```

## Parameters

```json
{
  "name": "decompose",
  "description": "Convert a goal into an ordered subtask list with dependencies.",
  "parameters": {
    "goal": {"type": "string", "required": true},
    "horizon_hint": {"type": "string", "enum": ["immediate", "contextual", "temporal", "branching"], "default": null},
    "mode": {"type": "string", "enum": ["brain", "coach", "build", "default"], "default": null},
    "max_subtasks": {"type": "integer", "default": 12}
  }
}
```

```json
{
  "name": "revise",
  "description": "Modify a committed plan in-flight.",
  "parameters": {
    "plan_id": {"type": "string", "required": true},
    "kind": {"type": "string", "enum": ["insert", "modify", "abandon"], "required": true},
    "subtask_id": {"type": "string", "required": true},
    "after": {"type": "string", "description": "For insert: subtask_id to insert after", "default": null},
    "new_description": {"type": "string", "default": null},
    "new_depends_on": {"type": "array", "default": null},
    "reason": {"type": "string", "required": true}
  }
}
```

## Output Format

```json
{
  "operation": "decompose",
  "plan_id": "pl_2026-05-01_a3f2",
  "goal": "Audit and rewrite the four remaining v1.0 skill stubs",
  "horizon": "temporal",
  "mode_at_creation": "build",
  "subtask_count": 4,
  "subtasks": [/* … */],
  "fidelity_signals": {
    "over_decomposition": false,
    "under_decomposition": false,
    "ambiguous_dependencies": false,
    "cycle_detected": false,
    "estimated_total_effort": "medium"
  },
  "next_action": "review then commit"
}
```

## Invariants

1. **Every plan operation records.** Pass through `record_op(...)`. Silent planning breaks the brain's monitor stack.
2. **One active plan per track.** Committing a new plan supersedes the prior; the prior is preserved in history with `state=superseded`, never silently overwritten.
3. **Subtask graph is a DAG.** No cycles; every `depends_on` resolves to an existing subtask in the same plan. Cycles fail at decompose-time.
4. **Revision preserves history.** Every revise call appends a `RevisionRecord`; the original plan structure is recoverable.
5. **Completion requires every subtask resolved.** A subtask must be `done`, `skipped` (with reason), or `blocked` (with reason) before `complete` succeeds.
6. **Reflection is the calibration loop.** Every `complete` opens a reflection window. Sustained `missing_reflection` is identity-relevant data routed through IPW.
7. **Mode at creation is recorded.** A plan made in BUILD mode has different defaults than one made in COACH mode; the brain tracks per-mode planning patterns.
8. **Horizon classification is required.** Each subtask carries a horizon (Koechlin's hierarchy). Untagged horizons default to `contextual` and are flagged.

## Safety

- **Max-subtask cap:** `MAX_SUBTASKS_PER_GOAL = 12` by default. Above that → `over_decomposition` flagged; not blocked, but the brain mechanism increments its counter.
- **Cycle detection:** decompose runs a topological sort on the dependency graph. Cycles fail closed.
- **Stale-plan detection:** every tick, scan active plans for `STALE_PLAN_TICK_THRESHOLD`-tick inactivity. Flag (don't auto-abandon — abandon is a deliberate revise kind).
- **Plan-storm cap:** ≤3 decompose calls in any rolling 50-tick window without an intervening commit. Above that → `plan_storm` flagged.
- **No execution side effects.** This skill never *executes* a plan — it only describes one. Execution happens through MakingLayer / OutwardReachLayer / the relevant action skill.

## Trust Level

**trusted** — planning is read/write to the agent's plan log, never to identity files or production code. `decompose` / `commit` / `revise` / `complete` / `reflect` are unrestricted. Aborting an `active` plan via `revise(abandon)` requires a `reason`; without reason, it fails closed.

## How this skill fits the system

| Layer | Module | Job |
|---|---|---|
| Skill | `skills/task-planning/SKILL.md` (this file) | Policy: ops, invariants, failure modes |
| Implementation | `skills/task-planning/planning.py` | Plan / Subtask classes, decompose / commit / revise / complete / reflect, dependency graph, library + CLI |
| Brain mechanism | `brain/mechanisms/task_planning_layer.py` | Wire 39 — runtime monitor for planning behavior |
| Working memory | `runtime/memory.py :: WorkingMemory` | Holds the active plan |
| Mode arbitration | `brain/mechanisms/persona_coherence_layer.py` | Mode at decompose time → planning style |
| Self-analysis | `brain/mechanisms/self_analysis_layer.py` | Receives `kind="plan"` reflections; calibrates predicted-vs-actual effort |
| Memory integrity | `brain/mechanisms/memory_integrity_layer.py` | Plans encoded as episodes; recallable |
| Action layers | `brain/mechanisms/making_layer.py`, `brain/mechanisms/outward_reach_layer.py` | Where committed plans actually run |
| Safety gate | `skills/safeguard.py` | Allow/block when TaskPlanningLayer raises a sustained pattern |

When wiring is live:

1. Goal arrives (operator or self-initiated).
2. Caller invokes `decompose(goal, mode=current_mode)` → proposed plan.
3. `TaskPlanningLayer.record_op("decompose", ...)` records the act with horizon, subtask_count, complexity signals.
4. Caller reviews the plan; if good, `commit(plan_id)`.
5. Plan goes active; downstream skills consult it. As subtasks fire, their results route back through the appropriate brain layer (MakingLayer for code, OutwardReachLayer for network, etc.).
6. If reality diverges, `revise(plan_id, kind, ...)` — the brain mechanism observes whether the agent revises or just lets the plan go stale.
7. `complete(plan_id, outcomes)` closes the plan; opens reflection window.
8. `reflect(plan_id, ...)` produces the retrospective; routes through `SelfAnalysisLayer.record_analyze(kind="plan")`.
9. Sustained dysfunction (plan_storm, missing_reflection, over_decomposition) routes through IPW.

## What this skill is *not*

- **Not execution.** Plans get *recorded* here; they execute through MakingLayer / OutwardReachLayer / action skills.
- **Not a TODO list.** TODO is a flat list; plans have horizons, dependencies, modes, revisions, reflections.
- **Not the dispatcher.** The heartbeat dispatcher handles autonomous activity scheduling; this is goal-driven planning that the agent or operator initiates.
- **Not silent.** Every op records; without records, the monitor stack stops working.
