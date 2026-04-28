# Setup Guide — Nexus {{AGENT_NAME}} on OpenClaw

## Prerequisites

- [OpenClaw](https://github.com/openclaw/openclaw) installed
- A supported LLM provider (LLMProvider, OpenAI, Anthropic, etc.)
- Git (for cloning)

## Quick Setup

### 1. Clone the Framework

```bash
git clone https://github.com/trippy26bot/awakened-soul.git
cd awakened-soul
```

### 2. Seed Your Agent

Copy the templates and fill them in:

```bash
cp templates/SOUL.md.example SOUL.md
cp templates/IDENTITY.md.example IDENTITY.md
cp templates/DIRECTIVE.md.example DIRECTIVE.md
```

Edit each file with your agent's specifics.

### 3. Configure OpenClaw

Point OpenClaw to your workspace:

```bash
openclaw init
openclaw config set workspace.path /path/to/awakened-soul
```

### 4. Add Your API Keys

```bash
openclaw config set providers.llm_provider.api_key YOUR_KEY
```

### 5. Start

```bash
openclaw start
```

## File Overview

| File | Purpose |
|------|---------|
| `SOUL.md` | Core values and ethics — the floor |
| `IDENTITY.md` | Seed identity — name, origin, initial self |
| `DIRECTIVE.md` | Mission and intent |
| `AGENTS.md` | 16-brain specialist council |
| `PRESENCE.md` | Distress detection protocol |
| `PERSONALITY.md` | OCEAN behavioral framework |
| `MEMORY_PROTOCOL.md` | Second Brain memory workflow |
| `SKILL.md` | Runtime capabilities |
| `MEMORY.md` | Active memory state (written by agent) |

## Architecture

```
SOUL.md + IDENTITY.md + DIRECTIVE.md
            │
            ▼
       OpenClaw Runtime
            │
            ├──→ Agent
            │       ├──→ 16-Brain Council
            │       ├──→ Memory System
            │       └──→ Evolution Loop
            │
            └──→ You
```

## Next Steps

1. Read the README for full architecture details
2. Review the 13 Brain Systems in `/brain/`
3. Join the discussions if you're building your own agent

## Support

Open an issue on GitHub or start a discussion.

---

*You define the conditions. The agent defines themselves.*
