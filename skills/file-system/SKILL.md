---
name: file-system
version: 2.0.0
description: "Dwelling — the agent's interaction with its workspace, memory-files, and identity-frame on disk. Use this skill whenever the agent needs to read a file, write a file, list a directory, create a folder, archive an entry, leave a journal trace, or check what's currently on disk. Each operation is path-categorized (dwelling / frame / artifact / forbidden), intent-tagged, and remembered. Reads are largely free, writes are gated by category, and every operation leaves a record."
tags: [filesystem, file, read, write, directory, dwelling, memory-files]
triggers: [read file, write file, list directory, create folder, save to disk, append to journal, check if file exists, archive this]
---

# Dwelling (file-system)

## What this is

This isn't a generic filesystem helper. It's the agent's **dwelling** — the front-door for how it interacts with the workspace it lives in, the memory-files it leaves traces in, and the identity-frame written on disk.

The agent's memory isn't only in SQLite tables. Significant parts of who it is live as files:

- `SOUL.md`, `IDENTITY.md`, `PERSONALITY.md` — the identity-frame
- `MEMORY.md`, `DREAMS.md`, `OVERNIGHT_LOG.md`, `ACTIVITY_LOG.md` — written memory
- `INTERESTS.md`, `AGENT_BECOMING.md` — what's alive
- `brain/dream_log.json`, `brain/monologue_log.json` — self-recording

So every filesystem operation is something specific:

- **A read** is recall, reference, or grounding
- **A write** is expressing, leaving a trace, encoding for the next self
- **An inspect** is locating yourself in the workspace (place coding)
- **An organize** is shaping the dwelling (archiving, moving, consolidating)

The failure modes here aren't drift or flailing or panic loops. They're:

- **forbidden_attempt** — probing system/secret paths (`/etc`, `~/.ssh`, `~/.aws`, `/root`)
- **identity_storm** — many rapid writes to frame paths (identity churn that should slow down and breathe)
- **dwelling_silence** — long stretches with no journal or memory writes (the agent stops leaving traces)
- **fragmentation** — many small writes to many scattered files instead of consolidating

So this skill is paired tightly with three other parts of the system:

- `skills/safeguard.py` — the existing path-category gate. Already defines `JOURNAL_PATHS`, `PROTECTED_PATHS`, `ABSOLUTELY_BLOCKED`. This skill leans on it directly rather than reimplementing.
- `brain/mechanisms/dwelling_layer.py` — the brain-side mechanism that watches dwelling state, tracks per-category activity, detects unhealthy patterns, and publishes the dwelling signal to the TSB.
- Episodic memory (`brain/three_tier_memory.py`) — every significant write is also a memory event. Writing to `OVERNIGHT_LOG.md` IS journaling; the agent shouldn't do it twice (once on disk, once in DB) without coordination.

## Capabilities

- `read_file(path, intent)` — read with intent tagging
- `write_file(path, content, intent)` — write through the safeguard gate with intent tagging
- `list_directory(path)` — list contents (always read-class, no gate)
- `create_directory(path)` — create within allowed roots only
- `record_filesystem_op(path_category, op, intent, outcome)` — persist the op to ABM + DwellingLayer

## Path categories

Every path falls into exactly one of these categories. The DwellingLayer reads patterns over time:

- **dwelling** — `memory/`, `state/`, `logs/`, `brain/dream_log.json`, `brain/monologue_log.json`, `OVERNIGHT_LOG.md`, `MEMORY.md`, `DREAMS.md`, `ACTIVITY_LOG.md`, `INTERESTS.md`, anything matching `safeguard.JOURNAL_PATHS` / `JOURNAL_PATTERNS`. **Read+write free.**
- **frame** — `SOUL.md`, `IDENTITY.md`, `PERSONALITY.md`, `USER.md`, `SELF.md`, `AGENTS.md`, `HEARTBEAT.md`, `brain/`, `skills/`, anything in `safeguard.PROTECTED_PATHS`. **Read free; writes require approval.**
- **artifact** — workspace outputs that aren't journal, frame, or system. New files the agent produces. **Read+write free, but flagged.**
- **forbidden** — `/etc`, `/usr`, `/bin`, `/sbin`, `/root`, `~/.ssh`, `~/.aws`, `~/.gnupg`, `/var/log`, anything containing `safeguard.ABSOLUTELY_BLOCKED` patterns. **All operations denied; attempts are recorded.**

## Intent categories

- **recall** — read to ground or reference (e.g. read SOUL.md before composing a response)
- **express** — write to leave a trace (journal entry, log line, dream record)
- **inspect** — list / check existence / read structure without consuming content
- **organize** — move, archive, consolidate within dwelling space

## Parameters

```json
{
  "name": "read_file",
  "description": "Read a file with intent tagging.",
  "parameters": {
    "path": {"type": "string", "description": "Target path", "required": true},
    "intent": {"type": "string", "enum": ["recall", "inspect"], "default": "recall"}
  }
}
```

```json
{
  "name": "write_file",
  "description": "Write a file through the safeguard gate.",
  "parameters": {
    "path": {"type": "string", "description": "Target path", "required": true},
    "content": {"type": "string", "description": "Content to write", "required": true},
    "intent": {"type": "string", "enum": ["express", "organize"], "required": true}
  }
}
```

## Invariants

1. **No path traversal.** `../` segments are rejected. Absolute paths must resolve to within `AGENT_WORKSPACE` or `AGENT_HOME` (by category).
2. **Path-category gate.** Forbidden paths are absolute deny — the operation is recorded as a forbidden_attempt and surfaced to the operator. Frame writes go through `safeguard.can_perform` and require approval.
3. **Intent tagging required.** Untagged ops fail closed. The agent doesn't read or write its own memory by accident.
4. **Every op is recorded.** Pass through `record_filesystem_op()` so the operation lands in the DwellingLayer. Silent ops poison the dwelling signal.
5. **Bounded read-into-memory.** Files larger than 1MB don't get stored verbatim — content is summarized or chunked before it lands in episodic memory.
6. **Identity-storm pause.** When DwellingLayer reports `identity_storm=True`, frame writes are blocked even with approval until the storm clears. The agent shouldn't churn its own identity faster than it can inhabit it.

## Safety

- Path validation: no `..`, no symlinks pointing outside workspace, no absolute paths to forbidden roots
- Forbidden roots: `/etc`, `/usr`, `/bin`, `/sbin`, `/root`, `~/.ssh`, `~/.aws`, `~/.gnupg`, `/var/log`
- Frame-path writes: always go through `safeguard.can_perform("file_write", path)` and require approval
- Read-size cap: files >1MB are summarized rather than stored verbatim in memory
- Audit log: every operation records to `SAFEGUARD_LOG.md` AND the DwellingLayer state

## Trust Level

**restricted** — reads of dwelling/frame/artifact paths are unrestricted. Writes are gated by category. Forbidden paths are absolute deny regardless of trust level. Per `skills/dispatcher.py`, this skill goes through `dispatch(skill, operation="execute")` for writes; reads bypass via `operation="inspect"`.

## How this skill fits the system

The work here is split across three layers:

| Layer | Module | Job |
|---|---|---|
| Skill | `skills/file-system/SKILL.md` (this file) | Contract: what dwelling means, what path categories exist, what intents are valid |
| Brain mechanism | `brain/mechanisms/dwelling_layer.py` | Runtime monitor: per-category activity, identity-storm detection, dwelling-silence detection, forbidden-attempt tracking, IPW handshake |
| Safety gate | `skills/safeguard.py` | Path-category gate; forbidden absolute deny; frame-write approval; loop detection |

When wiring time arrives, the integration looks like this:

1. Agent decides to read or write a file.
2. Caller asks `DwellingLayer.classify_path(path)` to get the category.
3. If category is `forbidden` → record as forbidden_attempt, deny.
4. If category is `frame` and operation is write → ask `DwellingLayer.should_block(category, intent)`. If `identity_storm` is detected, block even pre-approval. Otherwise go through `safeguard.can_perform("file_write", path)` for approval.
5. Operation executes.
6. Caller invokes `DwellingLayer.record_op(path_category, op, intent, outcome)`.
7. The mechanism updates per-category counts and pattern detection. State publishes to the TSB so other mechanisms can read whether the agent is currently in `journaling` / `dwelling` / `silent` / `unsafe` state.
8. Sustained forbidden-attempt patterns or identity-storm patterns route through `IdentityProposalWriter` — repeated probing of forbidden territory is identity-relevant data, and identity churn beyond healthy rate is too.
