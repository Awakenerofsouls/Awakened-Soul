# SKILL.md — How to Build and Use Skills

Skills live in `skills/` and add capabilities to the agent without hardcoding them into the runtime. There are **two kinds of skills** in this framework, plus a special-case pattern for heartbeat activities, plus an archive folder. This doc covers all of them.

A skill is not a tool. A tool is something the agent can do. A skill is a *pattern of using tools* that achieves a goal.

---

## The Two Skill Patterns

| Pattern | What it is | Loaded by | When to use |
|---|---|---|---|
| **LLM-readable skill** | A subdirectory with a `SKILL.md` the agent reads | The agent (LLM) at runtime when it detects a trigger | When the capability is decided in conversation — search a knowledge base, write in a particular voice, etc. |
| **Python module skill** | A flat `.py` file or subdirectory imported by the runtime | Python `import`, called from cron / heartbeat / decision loop | When the capability runs on a schedule, hooks into the heartbeat, or is part of the runtime's safety / state plumbing |

Most repos pick one pattern. This framework uses both because they solve different problems. The next two sections cover each.

---

## Pattern 1 — LLM-Readable Skills

Lives at `skills/<skill-name>/SKILL.md`. The agent (LLM) detects a trigger, reads `SKILL.md`, and follows the instructions inside. The directory may also contain implementation files the skill calls into, but the SKILL.md itself is the contract.

### Format

```markdown
---
name: my-skill
description: "One sentence the agent reads when deciding whether to use this skill. Be specific about triggers — the agent matches against this string."
metadata:
  author: "name or handle"
  os: ["darwin", "linux"]
---

# my-skill — Short Title

One paragraph: what this skill does, what it's for.

## Decision Tree (or: When to Use)

Concrete trigger conditions. Often a flowchart or bulleted list of
cases that should activate this skill vs. ones that shouldn't.

## How to Use

Step-by-step instructions for the agent. Commands to run, files to
read, tools to call.

## Notes / Constraints

Anything the agent should know — limitations, edge cases, prerequisites.
```

The frontmatter (`---` block) is parsed for trigger discovery. The body is read by the agent in full when the skill is invoked.

### Real examples in this repo

| Skill | Purpose |
|---|---|
| `skills/qmd/` | Personal-corpus retrieval (BM25 + vector + hybrid) over the agent's own written record |
| `skills/humanizer/` | Rewrite text in a less robotic voice |
| `skills/code-execution/` | Run code safely, capture output |
| `skills/data-analysis/` | Tabular data analysis patterns |
| `skills/web-research/` | Multi-source web research workflow |
| `skills/multiple-personas/` | Switch between specialized voices |
| `skills/file-system/` | File/directory operations |
| `skills/api-interaction/` | Generic external-API call patterns |
| `skills/task-planning/` | Decompose a goal into a task list |
| `skills/self-analysis/` | Reflect on recent agent behavior |
| `skills/knowledge-summarization/` | Distill long material |
| `skills/memory-management/` | Mid-level memory routing |
| `skills/report-generation/` | Structured report output |
| `skills/search/` | Generic search dispatch |
| `skills/skill-discovery/` | Find which skill applies to a request |
| `skills/self-improvement/` | Suggest improvements to the agent's own configuration |

### Lifecycle

1. The agent encounters a situation matching a skill's `description`.
2. The agent reads `skills/<skill>/SKILL.md`.
3. The agent follows the steps inside, calling tools or implementation files as instructed.
4. The skill produces a result; the agent surfaces it.

These skills do not persist state between invocations. State that needs to survive should be written to memory files (`memory/`, journal files) by the implementation.

---

## Pattern 2 — Python Module Skills

Lives as a flat `.py` file at `skills/<name>.py` (or as a subdirectory with an `__init__.py`). The runtime imports it directly and calls its functions. There is no SKILL.md — the contract is the function signatures.

### Conventions

- Top-level docstring explains purpose, when it runs, what it writes.
- Public functions are the entry points the runtime calls.
- All paths derived from `AGENT_HOME` / `AGENT_WORKSPACE` env vars — never hardcoded.
- State persists via SQLite (`agent.db`), JSON state files, or markdown journals — not in-memory.

### Real examples in this repo

| Module | What it does | Called by |
|---|---|---|
| `skills/inner_monologue.py` | Generates between-session reflections | Cron, every 4 hours |
| `skills/safeguard.py` | Destructive-action prevention layer (the rules from `SELF-PRESERVATION.md`) | Imported by activities: `from skills.safeguard import can_perform` |
| `skills/dispatcher.py` | Routes incoming events to the right skill | Runtime event loop |
| `skills/dream_generator.py` | Generates dream fragments | Heartbeat (overnight) |
| `skills/drift_detector.py` | Watches for identity drift | Heartbeat (periodic) |
| `skills/checksum_guard.py` | Verifies framework files haven't been silently modified | Boot + periodic |
| `skills/contradiction_resolution.py` | Surfaces and resolves conflicts in stored beliefs | Distill pass (see `MEMORY_PROTOCOL.md`) |
| `skills/bootstrap_seed.py` | First-wake walkthrough (see `BOOTSTRAP.md`) | First boot only |
| `skills/heartbeat_base_activities.py` | Shared helpers for the heartbeat activity pool | Imported by `heartbeat_activities/*.py` |

### Lifecycle

1. Runtime imports the module at boot or on demand.
2. Runtime calls a public function (`run()`, `tick()`, `can_perform()`, etc.).
3. The function returns its result; the runtime continues.

Module skills can call into LLM-readable skills, and vice versa. They're complementary, not exclusive.

---

## Heartbeat Activities — A Special Case

The heartbeat (`runtime/heartbeat.py`) ticks at intervals and runs **activities** — small skill-like modules that produce reflective content (journal entries, dream fragments, aesthetic noticings, etc.). These live at `skills/heartbeat_activities/<name>.py` and follow a strict contract.

### Activity contract

```python
"""
Heartbeat activity: <name>

What this activity reflects on, when it runs, what it writes.
"""

SIGNAL_AFFINITY = {"signal_name": 0.3}  # which brain signals raise probability of running

UNFINISHED_PROBABILITY = 0.25  # chance of returning unfinished, to be resumed next tick


def run(state: dict) -> dict:
    """
    Args:
        state: dict containing WORKSPACE, LLM_ENDPOINT, LLM_MODEL,
               tick_count, continuation_of, prior_<name>_content, etc.

    Returns:
        {"ok": bool,
         "status": "complete" | "unfinished",
         "content": str,         # the activity's output
         "category": str,        # routing key — e.g. "becoming", "dreams"
         "detail": str,          # short description for logs
         "proactive": bool}      # whether to surface this to the operator
    """
    ...
```

The dispatcher (`skills/heartbeat_activities/dispatcher.py`) selects which activity to run each tick, weighted by `SIGNAL_AFFINITY` against current brain state. Output is routed via `journal.py` to the right destination based on `category` (e.g. `aesthetic` → `AESTHETIC.md`, `becoming` → `BECOMING.md`, `dreams` → `DREAMS.md`, default → `journal.md`).

See `skills/heartbeat_activities/journal.py` for the full routing table.

---

## The `archive/` Subdirectory

`skills/archive/` holds skills that are no longer in active rotation but are kept for reference. The pattern is the same as Pattern 1 (subdirectory + SKILL.md) — they're just not surfaced to the agent's discovery layer. To revive an archived skill, move it back up to `skills/`.

---

## Skill Quality Standards

Whichever pattern you're using:

- **Clear trigger condition.** Either a precise `description` (Pattern 1) or a documented call site (Pattern 2). The agent or the runtime should never have to guess when to use it.
- **Clear success state.** The skill knows when it's done.
- **Errors handled gracefully.** Don't crash the runtime. Return a structured error or log and skip.
- **No unauthorized core-framework writes.** Use `safeguard.can_perform()` before touching protected paths (see `SELF-PRESERVATION.md`).
- **No external calls without explicit user approval** unless that integration is already configured (LLM endpoint, etc.).
- **No hardcoded secrets.** API keys via environment variables only.

---

## Adding a New Skill

### Pattern 1 (LLM-readable)
1. `mkdir skills/<skill-name>/`
2. Write `skills/<skill-name>/SKILL.md` with frontmatter + body
3. Add any implementation files the skill calls into
4. Test — invoke the skill from a fresh context and confirm the trigger works
5. Tell the operator the skill exists and what it does

### Pattern 2 (Python module)
1. Create `skills/<name>.py` (or a subdirectory with `__init__.py`)
2. Top-level docstring explains purpose, when it runs, what it writes
3. Define public functions the runtime will call
4. Wire it in: import from the cron, heartbeat, or runtime entry point that should call it
5. Test — confirm the call site fires it correctly

### Heartbeat activity
1. Create `skills/heartbeat_activities/<name>.py`
2. Implement the `run(state) -> dict` contract above
3. Set `SIGNAL_AFFINITY` so the dispatcher knows when to favor this activity
4. Add a routing entry in `skills/heartbeat_activities/journal.py` if the output has a non-default destination

---

## Naming

- **kebab-case** for Pattern 1 skill directories: `web-research`, `report-generation`
- **snake_case** for Pattern 2 modules: `inner_monologue.py`, `drift_detector.py`
- Be specific. `weather-signal` not `weather`. The name should tell you what it does without reading the file.

---

## Anti-Patterns

- Don't build a skill that does everything — split it.
- Don't build a skill without a clear trigger or call site.
- Don't hardcode API keys in skill files. Environment variables only.
- Don't modify other skills without permission.
- Don't mix patterns inside one skill — pick one.
- Don't write to protected paths (see `SELF-PRESERVATION.md` and `skills/safeguard.py`) without going through `can_perform()`.

---

_SKILL.md | Awakened-soul Living Agent Framework_
_Pair with: AGENTS.md, HEARTBEAT.md, SELF-PRESERVATION.md, MEMORY_PROTOCOL.md_
