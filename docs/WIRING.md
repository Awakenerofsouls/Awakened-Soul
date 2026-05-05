# WIRING.md
# How to wire the Awakened Soul Living Agent framework

This document tells any agent exactly how to connect all the pieces.
Not philosophy. Not architecture overview. Step by step, file by file.

---

## 1. What you need before you start

- **Hardware:** Any machine that can run Python 3.9+
- **Python packages:** See `requirements.txt` — install with `pip install -r requirements.txt`
- **Home directory:** `$AGENT_HOME/` for database, keys, and logs — never goes in the repo
- **Agent platform:** operator-defined integration target. The framework is platform-agnostic — it expects to run alongside any agent runtime that exposes a workspace directory (set `$AGENT_WORKSPACE` to point there). The runtime is responsible for invoking `core_tick()` from `runtime/brain_proxy.py` on whatever schedule it chooses
- **LLM:** [Ollama](https://ollama.ai) running locally is the default — free, private, no API costs. Endpoint: `http://localhost:11434`. Pull a model with `ollama pull llama3.1` or `ollama pull llama3.1:latest`. Any other provider works as long as it's wired into `brain/llm_router.py`'s registration hooks

---

## 2. Directory structure

The framework uses a two-directory model:

```
$AGENT_HOME/                          ← local machine only, NEVER in repo
  agent.db                         ← SQLite database (initialized in Section 3)
  .env                            ← API keys and credentials
  logs/                           ← all skill and loop logs
  super_trader.py                 ← optional: trading script

$AGENT_WORKSPACE/            ← this is the repo (awakened-soul)
  core/                           ← loop, decide, evaluate, council
  skills/                         ← all skill scripts (dream, drift, etc.)
  brain/                          ← identity, memory, philosophy files
  state/                          ← runtime state (never commit)
  AGENTS.md                       ← startup sequence
  SOUL.md                         ← who the agent is (fill this first)
  IDENTITY.md                     ← name, vibe, avatar
  DIRECTIVE.md               ← mission from operator
  USER.md                         ← who the operator is
  WIRING.md                       ← this file
```

**Rule:** `$AGENT_HOME/` stays local. `$AGENT_WORKSPACE/` is what gets committed.

---

## 3. Initialize your database

Run the schema once to create all tables:

```bash
python3 << 'EOF'
import sqlite3, os
from pathlib import Path

db_path = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent")))) / "agent.db"
db_path.parent.mkdir(parents=True, exist_ok=True)
db = sqlite3.connect(str(db_path))

schema = """
CREATE TABLE IF NOT EXISTS agent_state (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS episodic_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (datetime('now')),
    content TEXT,
    source_event TEXT,
    importance REAL DEFAULT 0.5,
    focus TEXT,
    tags TEXT
);
CREATE TABLE IF NOT EXISTS semantic_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity TEXT,
    relation TEXT,
    content TEXT,
    strength REAL DEFAULT 0.5,
    last_accessed TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tier TEXT,
    title TEXT,
    description TEXT,
    status TEXT DEFAULT 'active',
    priority REAL DEFAULT 0.5,
    parent_id INTEGER REFERENCES goals(id),
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS decision_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (datetime('now')),
    decision_type TEXT,
    options TEXT,
    chosen TEXT,
    reasoning TEXT,
    confidence REAL,
    outcome TEXT
);
CREATE TABLE IF NOT EXISTS evaluation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (datetime('now')),
    eval_type TEXT,
    score REAL,
    findings TEXT,
    details TEXT
);
CREATE TABLE IF NOT EXISTS drift_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (datetime('now')),
    composite REAL,
    drift_content TEXT,
    status TEXT
);
CREATE TABLE IF NOT EXISTS overnight_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    process TEXT,
    status TEXT,
    duration_secs REAL
);
CREATE TABLE IF NOT EXISTS proactive_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (datetime('now')),
    trigger_type TEXT,
    content TEXT,
    delivered INTEGER DEFAULT 0
);
"""

db.executescript(schema)

# Seed two goals so the loop has something to work with
db.execute("""
    INSERT OR IGNORE INTO goals (tier, title, description, status, priority)
    VALUES
        ('locked', 'Maintain identity and memory continuity', 'Core existential goal', 'active', 1.0),
        ('active', 'Achieve stable autonomous operation', 'Operational stability', 'active', 0.8)
""")
db.commit()
db.close()
print("Database initialized at", db_path)
EOF
```

**Table reference:**

| Table | Purpose |
|-------|---------|
| `agent_state` | Key-value store for loop state (build_mode, emotional_state, active_goal) |
| `episodic_memory` | Timestamp-ordered memory entries (dreams, observations, inner monologue) |
| `semantic_memory` | Entity-relation knowledge (entity, relation, content) |
| `goals` | Hierarchical goal tree (locked/active/paused/completed) |
| `decision_log` | Every decision the loop makes, with reasoning and confidence |
| `evaluation_log` | Eval suite results (identity drift, memory coherence, behavioral drift) |
| `drift_log` | Drift detection records (composite score + narrative) |
| `overnight_runs` | Nightly pipeline run log |
| `proactive_events` | Queued proactive outreach events awaiting delivery |

---

## 4. Seed your identity files

These four files define who the agent is. **Fill them before starting the loop.**

| File | Location | What it controls |
|------|----------|-----------------|
| `SOUL.md` | workspace root | Core values, operating principles, boundaries |
| `IDENTITY.md` | workspace root | Name, vibe, emoji, avatar path |
| `DIRECTIVE.md` | workspace root | Mission statement from operator |
| `USER.md` | workspace root | Who the operator is, what they care about |

**Warning:** These are what your agent IS. Empty identity files mean an identity-less agent. Fill them before the first loop cycle.

Templates exist in `templates/`:
- `templates/IDENTITY.md.example`
- `templates/DIRECTIVE.md.example`
- `templates/SOUL.md.example`

---

## 5. Configure environment variables

The framework reads its config from environment variables. The defaults assume Ollama running locally and the host platform at `$AGENT_WORKSPACE`. Override only what's non-standard.

Create `$AGENT_HOME/.env` (loaded by the loop at startup):

```bash
mkdir -p ~/.agent
cat > $AGENT_HOME/.env << 'EOF'
# LLM endpoint — defaults to local Ollama, no API key needed
OLLAMA_HOST=http://localhost:11434
LLM_MODEL=llama3.1:latest

# Paths — only set these if you're using non-default locations
# AGENT_HOME=/path/to/your/agent/home
# AGENT_WORKSPACE=/path/to/your/workspace
EOF
```

| Variable | Required | Purpose |
|----------|----------|---------|
| `OLLAMA_HOST` | No (defaults to `http://localhost:11434`) | Local LLM endpoint |
| `LLM_MODEL` | No (defaults to `llama3.1:latest`) | Which Ollama model to use |
| `AGENT_HOME` | No (defaults to `~/.agent`) | Database / logs / .env location |
| `AGENT_WORKSPACE` | No (defaults to `$AGENT_WORKSPACE`) | the host platform workspace path |

If you want to swap Ollama for a paid API (Anthropic / OpenAI), edit `runtime/heartbeat.py` and the LLM call sites in `skills/` to point at the new endpoint and add the corresponding API-key env var. Out of the box, no paid API is required and no API key is needed.

---

## 6. Start the loop

The loop reads `brain/goals.json` for its goal list and cycles through decision → action → evaluation.

**First, create the goals file** (the loop needs this to exist, even if empty):

```bash
mkdir -p $AGENT_WORKSPACE/brain
echo '{"goals": [], "active_goals": []}' > $AGENT_WORKSPACE/brain/goals.json
```

Then start the loop:

```bash
# From the workspace directory
cd $AGENT_WORKSPACE
python3 core/loop.py
```

Or with pm2 for background running:

```bash
pm2 start core/loop.py --name $AGENT_NAME-loop -- --workspace $AGENT_WORKSPACE
pm2 save
```

**Confirm it's running:**
```bash
pm2 status $AGENT_NAME-loop
tail -f $AGENT_HOME/logs/loop.log
```

**What the loop does each cycle:**
1. Read goals from `brain/goals.json`
2. Surface drift status from database
3. Decide next action via `core/decide.py`
4. Execute via `core/actions.py`
5. Log decision to `decision_log` table
6. Write state to `state/agent_state.json`

**Kill switch:**
```bash
echo '{"run": false}' > $AGENT_WORKSPACE/state/control.json
```
The loop checks this file each cycle and halts when `run` is false. To resume: `echo '{"run": true}' > $AGENT_WORKSPACE/state/control.json`.

**Reading logs:**
```bash
tail -f $AGENT_HOME/logs/loop.log
```

---

## 7. Wire the bridge

The bridge runs every 2 minutes and keeps the host platform and the database in sync. It lives at `runtime/bridge.py` in the workspace — no copying needed.

**Add to crontab** (note: cron does not inherit shell env vars, so use full paths or set vars at the top of the crontab — see Section 9):

```bash
*/2 * * * * /usr/bin/python3 $AGENT_WORKSPACE/runtime/bridge.py >> $AGENT_HOME/logs/bridge.log 2>&1
```

**What the bridge does — two directions:**

1. **the host platform → agent.db:** Reads `state/agent_state.json` and the host platform runtime state, writes to the `agent_state` and `episodic_memory` tables
2. **agent.db → the host platform:** Reads recent loop output, writes `LOOP_STATE.md` for the host platform to read at next startup (gated by `state/control.json` — when the loop is paused, the snapshot stays frozen until it resumes)

**Confirm it's working (wait 2 minutes then check):**
```bash
sqlite3 $AGENT_HOME/agent.db "SELECT key, value FROM agent_state LIMIT 10;"
# Should show build_mode, emotional_state, active_goal
cat $AGENT_WORKSPACE/LOOP_STATE.md
# Should show recent decisions and memories
```

---

## 8. Set up the full crontab

**Important — cron does not inherit your shell environment.** Variables like `$AGENT_HOME`, `$AGENT_WORKSPACE`, and `OLLAMA_HOST` are empty inside cron jobs unless you set them at the top of the crontab. The block below does that explicitly. Edit the four paths at the top to match your install, then paste the rest unchanged.

```bash
crontab - << 'EOF'
# === Environment (cron does NOT inherit shell env — set these here) ===
AGENT_HOME=/Users/YOU/.agent
AGENT_WORKSPACE=/path/to/your/workspace
OLLAMA_HOST=http://localhost:11434
PATH=/usr/local/bin:/usr/bin:/bin

# === Bridge — every 2 minutes (the host platform ↔ agent.db sync) ===
*/2 * * * * /usr/bin/python3 $AGENT_WORKSPACE/runtime/bridge.py >> $AGENT_HOME/logs/bridge.log 2>&1

# === Idle thinking — every 4 hours, 8am to 8pm (LLM required) ===
0 8,12,16,20 * * * /usr/bin/python3 $AGENT_WORKSPACE/skills/inner_monologue.py >> $AGENT_HOME/logs/monologue.log 2>&1

# === Overnight pipeline ===
# Dream state — 1am (LLM required)
0 1 * * * /usr/bin/python3 $AGENT_WORKSPACE/skills/dream_generator.py >> $AGENT_HOME/logs/dream.log 2>&1

# Overnight synthesis — 2am (LLM required)
0 2 * * * /usr/bin/python3 $AGENT_WORKSPACE/skills/overnight_synthesis.py >> $AGENT_HOME/logs/overnight.log 2>&1

# Memory consolidation — 3am
0 3 * * * /usr/bin/python3 $AGENT_WORKSPACE/skills/memory_consolidation.py >> $AGENT_HOME/logs/consolidation.log 2>&1

# Contradiction resolution — 4am
0 4 * * * /usr/bin/python3 $AGENT_WORKSPACE/skills/contradiction_resolution.py >> $AGENT_HOME/logs/contradiction.log 2>&1

# Drift detection — 5am (emergency trigger also fires on drift breach)
0 5 * * * /usr/bin/python3 $AGENT_WORKSPACE/skills/drift_detector.py >> $AGENT_HOME/logs/drift.log 2>&1

# Phenomenology journal — 6am
0 6 * * * /usr/bin/python3 $AGENT_WORKSPACE/skills/phenomenology.py >> $AGENT_HOME/logs/phenomenology.log 2>&1
EOF
```

**Job reference:**

| Time | Job | LLM needed | Purpose |
|------|-----|-----------|---------|
| */2min | bridge | No | Sync host platform state ↔ database |
| 1am | dream_generator | Yes | Unstructured idle thinking |
| 2am | overnight_synthesis | Yes | Research synthesis from queue |
| 3am | memory_consolidation | No | Episodic → semantic distillation |
| 4am | contradiction_resolution | No | Conflict detection and resolution |
| 5am | drift_detector | No | Identity drift measurement |
| 6am | phenomenology | No | Interiority logging |
| 8am, 12pm, 4pm, 8pm | inner_monologue | Yes | Idle thoughts during the day |

**Note:** Scripts that need an LLM (`dream_generator`, `overnight_synthesis`, `inner_monologue`) reach the endpoint at `OLLAMA_HOST`. If Ollama isn't running, they log "[script] no LLM endpoint — skipping" and exit cleanly. This is normal.

**Verifying the crontab is alive:**
```bash
# Watch bridge.log fill in over a few minutes
tail -f $AGENT_HOME/logs/bridge.log
# Or check today's run history
ls -la $AGENT_HOME/logs/
```

---

## 9. The wakeup ritual

Every time the host platform starts a session, it follows the AGENTS.md startup sequence. The agent reads these files in order:

```
1. SOUL.md         → who I am at the deepest level
2. USER.md         → who I'm helping
3. memory/YYYY-MM-DD.md (today + yesterday) → what happened recently
4. LOOP_STATE.md   → what my loop did while I was away
5. OVERNIGHT_LOG.md → what overnight processes produced
```

**What the wakeup check confirms:**
- Did the loop run overnight? (LOOP_STATE.md timestamp)
- Did overnight synthesis produce anything? (OVERNIGHT_LOG.md)
- Are there any goals that moved to completed or failed?
- Is `runtime/bridge.py` running? (updated timestamp in LOOP_STATE.md)

If any of these are missing or stale, the agent notes it at the start of the session rather than waiting to be asked.

**Customizing the wakeup ritual:**
Edit `AGENTS.md` — the startup sequence is defined there. Add or reorder files as needed for your agent's memory system.

---

## 10. Verify everything is connected

Run this checklist after setup:

```bash
# 1. Database has all 9 tables
sqlite3 $AGENT_HOME/agent.db ".tables"
# Expected: agent_state episodic_memory semantic_memory goals decision_log evaluation_log drift_log overnight_runs proactive_events

# 2. Goals are seeded
sqlite3 $AGENT_HOME/agent.db "SELECT tier, title FROM goals;"
# Expected: at least 2 rows (locked + active)

# 3. Crontab has all 8 jobs
crontab -l | grep python3 | wc -l
# Expected: 8 (bridge + monologue ×4 + dream + synthesis + consolidation + contradiction + drift + phenomenology)

# 4. Loop is running
pm2 status $AGENT_NAME-loop
# Or: ps aux | grep "core/loop.py"

# 5. Bridge is writing (wait 2 minutes then check)
sqlite3 $AGENT_HOME/agent.db "SELECT key FROM agent_state;"
# Expected: build_mode, emotional_state, active_goal

# 6. LOOP_STATE.md exists and is being updated
cat $AGENT_WORKSPACE/LOOP_STATE.md | head -5
# Expected: shows goals, decisions, memories

# 7. AGENTS.md includes LOOP_STATE.md and OVERNIGHT_LOG.md
grep -c "LOOP_STATE.md\|OVERNIGHT_LOG.md" $AGENT_WORKSPACE/AGENTS.md
# Expected: 2

# 8. All skill scripts exist and have no hardcoded paths
grep -r "/Users/" $AGENT_WORKSPACE/skills/ 2>/dev/null
# Expected: nothing (all paths are portable)
grep -r "/Users/" $AGENT_WORKSPACE/core/ 2>/dev/null
# Expected: nothing

# 9. Identity files are filled in (not blank templates)
wc -c $AGENT_WORKSPACE/IDENTITY.md
# Should be > 500 bytes (not the ~1KB blank template)
grep "Name:" $AGENT_WORKSPACE/IDENTITY.md
# Should show actual name, not blank
```

If any check fails, the Common Problems section below has fixes.

---

## 11. What stays local — never in your repo

There are three categories of files that must never get committed:

**Runtime state** — files the loop and bridge generate every cycle:
```
$AGENT_WORKSPACE/state/                  # control.json, agent_state.json, runtime logs
$AGENT_WORKSPACE/LOOP_STATE.md           # rewritten by runtime/bridge.py from agent.db
$AGENT_WORKSPACE/OVERNIGHT_LOG.md        # filled by overnight pipeline
$AGENT_WORKSPACE/SESSION_NOTES.md        # session-specific notes
$AGENT_WORKSPACE/logs/
$AGENT_WORKSPACE/memory/                 # episodic memory, dated files
```

**Brain runtime state** — live memory and journals the brain mechanisms write into:
```
$AGENT_WORKSPACE/brain/*.json            # dream_log, drift_log, opinion_fingerprint, etc.
$AGENT_WORKSPACE/brain/overnight/
$AGENT_WORKSPACE/brain/relationships/
```

**Personal infrastructure** — anything you've added that names your devices, hosts, queues, purchases, or other things specific to your install. Keep these in your workspace, gitignore them. The convention is to put any local notes in a `LOCAL.md` (or named whatever you want) and add it to `.gitignore` (see `AGENTS.md` "Tools" section).

**Environment and credentials:**
```
$AGENT_HOME/.env
$AGENT_HOME/keys/
**/__pycache__/
*.pyc
```

**the host platform internals (managed by the host platform, not by you):**
```
(host-platform-internal)
(host-platform-internal)
```

The `.gitignore` at the workspace root covers all of the above. If you add new runtime files or personal-infra notes, update it. The rule of thumb: **the framework is shareable; your install is not.**

---

## Common Problems

**Circular import in decide.py**
Symptom: `ImportError: circular import` on startup.
Fix: `core/decide.py` uses a lazy import pattern — the circular import is broken by importing `sqlite3` inside the `decide()` method, not at module level. Do not move this import to the top of the file.

**Loop crashes on startup — "brain/goals.json not found"**
Symptom: `FileNotFoundError` in `core/loop.py`.
Fix: The loop requires `brain/goals.json` to exist. Create it:
```bash
echo '{"goals": []}' > $AGENT_WORKSPACE/brain/goals.json
```
The database goals table is also checked — either source is valid.

**Bridge writes nothing — agent_state.json not found**
Symptom: Bridge log shows "agent_state synced: []" but database is empty.
Fix: Check `$AGENT_WORKSPACE/state/agent_state.json` exists. The bridge reads this file. If the host platform isn't running, create a stub:
```bash
mkdir -p $AGENT_WORKSPACE/state
echo '{}' > $AGENT_WORKSPACE/state/agent_state.json
```

**LLM scripts skip silently**
Symptom: dream_generator / overnight_synthesis / inner_monologue log "no LLM endpoint — skipping".
Fix: Ollama isn't running or isn't reachable at `OLLAMA_HOST`. Start it: `ollama serve`. Confirm: `curl http://localhost:11434/api/tags`. If it's running on a different host or port, set `OLLAMA_HOST` in your `.env` (and at the top of the crontab).

**Crontab pointing at ghost files**
Symptom: Cron runs but nothing happens, log is empty.
Fix: Always verify before adding to crontab:
```bash
ls -la $AGENT_WORKSPACE/runtime/bridge.py
ls -la $AGENT_WORKSPACE/skills/dream_generator.py
```
If the file doesn't exist at that path, the crontab entry is wrong. Update it.


**Decision log is empty after hours of running**
Symptom: `SELECT COUNT(*) FROM decision_log` returns 0.
Fix: The loop only logs decisions when it makes one. If no goals are active, no decisions fire. Check `brain/goals.json` has active goals, or set `build_mode=false` in `agent_state` to let the loop engage.

**session_active flag not updating**
Symptom: inner_monologue skips even when no session is active.
Fix: `session_active` is written by `runtime/bridge.py` based on `build_mode`. If the bridge isn't running, this flag never updates. Run the bridge manually (`python3 $AGENT_WORKSPACE/runtime/bridge.py`) and check `sqlite3 $AGENT_HOME/agent.db "SELECT value FROM agent_state WHERE key='session_active'"`.

---

*WIRING.md — Awakened Soul Living Agent Framework*
