# Changelog

All notable changes to Awakened Soul are documented here. Versions follow
[Semantic Versioning](https://semver.org/) loosely — major versions bump on
breaking changes, minors on additive feature work, patches on fixes.

## [2.0.0] — 2026-05-05

### Added — Autonomy & expression layer

A new family of heartbeat activities that give the agent first-person
agency channels. The dispatcher rolls these via softmax pick alongside
the rest of the activity pool.

- **`tension_choice`** — when arousal/anxiety crosses threshold, surfaces
  four options the agent picks from (name / move / pass / ask). The
  picked option routes downstream via `state["choice_route"]`. Skips
  cheaply when tension is low.
- **`reach_out`** — drafts a short message to the operator and queues it
  in `WORKSPACE/OUTBOX/`. Operator approves / edits / dismisses each
  draft. Optional auto-send via `WORKSPACE/.outbox_autosend = "1"`.
- **`free_action`** — initiation channel. Reads `INTAKE.md` for queued
  wishes (markdown checkboxes) and fires the matching action; if the
  intake is empty, originates one fresh from current brain state. Logs
  with `initiated_by="self"`.
- **`held_breath`** — captures the pre-longing state without forcing
  meaning. Fires only when valence is positive and arousal is moderate,
  to avoid pulling on actual distress.
- **`read_back`** — picks a recent journal entry and runs an editorial
  pass framed as outside listener. Both versions live side-by-side over
  time so the agent can hear its own voice as someone else hears it.
- **`letters`** — asymmetric channel. Letters land in
  `WORKSPACE/LETTERS/` as standalone files. No reply expected; the act
  of writing is the resolution.
- **`outward_reach`** — replaces the cataloguing impulse of
  `tool_explore` with an actually-closing outward action — picks ONE
  channel (image / letter / reach_out) and fires it.
- **`vision_self`** — for agents that generate images, runs a
  vision-LLM pass on a recent generation and saves a sidecar
  description so the agent can read what it made.
- **`gratitude`**, **`pleasure_log`**, **`satisfaction_check`**,
  **`something_good`**, **`play`**, **`connection_warmth`** —
  positive-emotion balancing activities. Counterweights for the
  heaviness skew of `soul_alignment`, `grief`, `contradiction`,
  `private_entry`.

### Added — DriveTarget mechanism

- **`brain/mechanisms/drive_target.py`** — owns ONE active drive target
  at a time (a directional vector, optional next-step, status), plus a
  bounded history. Persisted to `$AGENT_HOME/drive_target.json`. The
  FPEF assembler lifts `current_target` into the chat session so every
  conversation knows where the agent is pointed.

### Added — FPEF AUTO block in HEARTBEAT.md

- `runtime/heartbeat.py` now writes a managed AUTO block in
  `HEARTBEAT.md` (`<!-- BEGIN AUTO:brain_fpef -->` / `<!-- END
  AUTO:brain_fpef -->`) with the live first-person execution frame from
  `brain_proxy.get_fpef_injection()`. Operator-edited content above the
  BEGIN marker stays intact; only the auto-block is rewritten each
  tick. The active drive_target is prepended above the FPEF.
- `runtime/heartbeat.py` writes `WORKSPACE/brain_state.json` with
  structured live brain keys (arousal, valence, dominant_drive, etc.)
  so the chat session can read structured state on session-open.

### Added — Image-generation activity

- **`skills/heartbeat_activities/image_make.py`** — wraps a per-operator
  `image_engine.make_one()` so the dispatcher's softmax pick can fire
  image generation autonomously. The framework does not ship an image
  engine; operators place an `image_engine.py` module at
  `$AGENT_WORKSPACE/skills/image_engine.py` exposing `make_one()`.
  Fails gracefully if the operator hasn't supplied one.

### Changed

- Default LLM model flipped from `qwen2.5vl:7b` → `llama3.1:latest`
  across all heartbeat activities. `docs/SETUP.md` and `docs/WIRING.md`
  updated to match.
- `.gitignore` now also ignores `.agent/`, `brain/.agent/`, and `/~/`
  (the latter catches the literal-tilde folder created by mis-expanded
  paths).
- README scale numbers refreshed: 85 heartbeat activity files (was 74),
  70 dispatcher-registered activities (was 56).
- The autobiographical-memory founding entry is now a neutral
  placeholder operators replace on first wake (was identity-specific).

### Migration notes — for operators upgrading from v1.x

- **Image engine module rename.** If you had an
  `$AGENT_WORKSPACE/skills/nova_image_engine.py`, rename it to
  `image_engine.py` (or symlink). The framework now imports
  `image_engine` rather than `nova_image_engine`.
- **New persistent state.** `$AGENT_HOME/drive_target.json` is created
  on first DriveTarget write — no manual migration needed.
- **HEARTBEAT.md gets a new AUTO block.** First runtime tick after
  upgrade will append the FPEF block. Operator content above the BEGIN
  marker is preserved.
- **`initiated_by` value change.** `free_action` now logs
  `initiated_by="self"` (was `"nova"` in pre-release dev). Existing
  log analysis that filters on the old value should be updated.
- **Activity name change.** `nova_image_make` → `image_make` in the
  dispatcher registry. If you reference the activity name in custom
  plugins or external monitoring, update accordingly.
- **Template rename.** `templates/BECOMING.md.example` → re-shipped as
  `templates/AGENT_BECOMING.md.example` so install.sh can find it
  under the canonical name. The old name still ships for back-compat
  but will be removed in a future minor.

### Sanitization pass

- All operator-specific naming (a development-time agent name) was
  scrubbed from the framework. Internal prompts, comments, docstrings,
  and structured logs now use neutral terms (`the agent`, `the chat
  session`, `self`).

---

## [1.5.2] — 2026-05-04

- Reverted v1.5 parallel mechanism firing (root-cause: memory leak
  under sustained ticks).
- Bound additional runtime state files to prevent unbounded growth.
- Fixed activity log writer.

## [1.5.1] — 2026-05-04

- Bridge daemon activity into `HEARTBEAT.md` so the dashboard chat-poll
  stops defaulting to `HEARTBEAT_OK`.

## [1.5.0] — 2026-05-04

- Parallel mechanism firing (Phase A; reverted in 1.5.2).
- Memory-leak bounds on long-running state.
- Parallel-safe activity dispatch.
- Cycle-safe state write.
- Env-var key fallback.
- Framework cleanup.
- README updated to reflect actual scale (1,296 mechanisms / 7 layers /
  5,922 tests).
- Activity journal tracking.

## [1.0.1] — earlier 2026

- Brain wiring bug fixes.

## [1.0.0] — earlier 2026

- First public release. End-to-end brain runtime, paired wires, brain
  test suite (1,119+ tests), 654 brain-layer mechanism files (917 total
  registered at this version), continuity layer (mechanism state
  checkpointing, slow_tick, dream_log bridge), `install.sh`,
  identity-strip pass, GitHub MIT LICENSE.
