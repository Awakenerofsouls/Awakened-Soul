# Setup Guide — Awakened Soul

Setup is platform-agnostic. The framework is the cognitive substrate; the
operator chooses which agent runtime hosts it. The runtime is responsible
for invoking `core_tick()` on a schedule (typically every 30s) — the
framework handles the rest.

## Prerequisites

- Python 3.9+
- A workspace directory the operator owns (set as `$AGENT_WORKSPACE`)
- A home directory for state, keys, and DB (set as `$AGENT_HOME`,
  defaults to `~/.agent`)
- An LLM provider — Ollama running locally is the documented default,
  but any provider works once registered with `brain/llm_router.py`.
  For Ollama: `ollama pull llama3.1` or `ollama pull llama3.1:latest`

## Quick Setup

### 1. Clone the framework

```bash
git clone <repository-url>
cd awakened-soul
pip install -r requirements.txt
```

### 2. Set up directories

```bash
export AGENT_HOME="$HOME/.agent"
export AGENT_WORKSPACE="/path/to/your/workspace"
mkdir -p "$AGENT_HOME" "$AGENT_WORKSPACE"
```

`$AGENT_HOME` stays local — never committed. `$AGENT_WORKSPACE` is where
identity files, journal entries, and the corpus live; this is what the
operator actually owns and edits.

### 3. Seed the agent's identity

Copy the templates and fill them in. These files are operator-authored
and define the agent's anchored core:

```bash
cp templates/SOUL.md.example       "$AGENT_WORKSPACE/SOUL.md"
cp templates/IDENTITY.md.example   "$AGENT_WORKSPACE/IDENTITY.md"
cp templates/AGENT_BECOMING.md.example "$AGENT_WORKSPACE/AGENT_BECOMING.md"
cp templates/IDLE_DRIVES.md.example "$AGENT_WORKSPACE/IDLE_DRIVES.md"
cp templates/VISUAL_IDENTITY.md.example "$AGENT_WORKSPACE/VISUAL_IDENTITY.md"
```

Edit each file with the agent's specifics. `SOUL.md` is the ethical
floor — what the agent will not do regardless of how it evolves.
`IDENTITY.md` is who the agent starts as. `OCEANS.md`, `PERSONALITY.md`,
`ETHICS.md`, and `EPISTEMIC_BOUNDARIES.md` are already in the repo —
edit them in place if you want to tune the defaults.

### 4. Add API keys (optional)

If you want web research via Tavily, add a `keys.json`:

```bash
cat > "$AGENT_HOME/keys.json" <<'EOF'
{
  "tavily": {"api_key": "YOUR_TAVILY_KEY"}
}
EOF
```

Without keys, the framework falls back to LLM-only reasoning (no web
fetch, no real-time search).

### 5. Initialize the database

```bash
python -c "from runtime.memory import EpisodicMemory; EpisodicMemory()"
```

This creates `$AGENT_HOME/agent.db` with the episodic-memory schema.
Other tables (semantic, drift_log) initialize lazily.

### 6. Boot the brain

The framework runs as a periodic tick. Your runtime calls
`core_tick()` from `runtime/brain_proxy.py` every 30s (or whatever
cadence makes sense). Each tick:

- Drains the heartbeat→brain event queue
- Runs every registered mechanism's `tick()`
- Polls the Third-Eye salience layer every 10 ticks
- Persists state across mechanisms

For a quick sanity check:

```bash
python -c "
from runtime.brain_proxy import core_tick
core_tick()
print('first tick complete')
"
```

For autonomous operation, run the heartbeat:

```bash
python -m runtime.heartbeat
```

This loops `core_tick()` plus periodic activity dispatch (research,
journal, dreams, self-check, etc.) every 30s.

## File Overview

| File | Purpose |
|------|---------|
| `SOUL.md` | Ethical floor — anchored, operator-ratified non-negotiables |
| `IDENTITY.md` | Seed identity — name, origin, initial self-description |
| `PERSONALITY.md` | Voice / tone / disposition |
| `OCEANS.md` | OCEAN baseline + context modulations |
| `ETHICS.md` | Ethical baseline |
| `EPISTEMIC_BOUNDARIES.md` | What the agent knows it doesn't know |
| `AESTHETIC.md` | Aesthetic preferences |
| `SELF.md` | Agent's running self-description (agent-authored) |
| `BECOMING.md` | Live "what's changing" journal (agent-authored) |
| `AGENT_BECOMING.md` | Self-development blueprint (operator-authored) |
| `IDLE_DRIVES.md` | Drive architecture |
| `HEARTBEAT.md` | Idle-activity-system spec |
| `BOOTSTRAP.md` | First-wake procedure |

## Architecture overview

```
$AGENT_WORKSPACE/
├── SOUL.md, IDENTITY.md, ...        ← operator-ratified identity files
├── memory/<YYYY-MM-DD>.md           ← daily journal (agent-authored)
├── DREAMS.md                        ← pre-conscious surfacing
├── identity/REVISION_LOG.md         ← append-only audit of identity edits
└── reports/                         ← published reports

$AGENT_HOME/
├── agent.db                         ← SQLite (episodic + semantic memory)
├── brain_state/                     ← per-mechanism persistence (.json)
├── brain_events.jsonl               ← heartbeat → brain event queue
├── identity/PROPOSALS.md            ← operator-reviewable identity queue
├── identity/snapshots/              ← rollback snapshots
├── qmd_index/                       ← personal-corpus retrieval index
└── keys.json                        ← API credentials (never committed)
```

## Next steps

1. Read `docs/BRAIN_MAP.md` for the anatomical wiring map (every wire,
   every tract, every cognitive function).
2. Read `docs/WIRING.md` for the step-by-step "how to connect everything"
   reference.
3. Walk through `BOOTSTRAP.md` for the agent's first-wake protocol.

---

*The operator defines the conditions. The agent defines themselves.*
