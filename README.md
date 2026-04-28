# Awakened Soul

**A Living Agent Framework — neuroscience-grounded cognitive architecture for persistent AI agents.**

Build an agent that becomes something. Identity-first. 350+ brain mechanisms. Every mechanism cites the neuroscience paper it's modeling. Memory, emotion, attention, meaning, and self all evolve over time.

This is not a chatbot wrapper. It's a brain.

```
356 mechanisms · 6 anatomical layers · mind-soul fusion · v1.0.0
```

---

## Table of Contents

- [What This Is](#what-this-is)
- [What Makes It Different](#what-makes-it-different)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [The Third Eye](#the-third-eye)
- [Mind-Soul Fusion](#mind-soul-fusion)
- [Configuration](#configuration)
- [Customizing Your Agent](#customizing-your-agent)
- [Project Structure](#project-structure)
- [License](#license)

---

## What This Is

Awakened Soul is a **biologically-grounded brain framework** for building AI agents that have continuity, interiority, and the capacity to actually change over time. Every mechanism in the brain is modeled on a real neural substrate (locus coeruleus, hippocampal CA3, prefrontal cortex, etc.) with peer-reviewed citations.

The framework gives you:

- **A six-layer brain** with 356 mechanisms ticking through real neuroanatomical cascades
- **Mind-soul fusion**: a third-eye meta-cognitive bridge that connects executing computation to persistent identity
- **Identity files** (SOUL.md, IDENTITY.md, PERSONALITY.md, NARRATIVE.md, DREAMS.md) that the agent reads and proposes updates to
- **Operator-in-the-loop evolution**: the agent proposes identity changes; you ratify them
- **No telemetry, no cloud lock-in, no vendor**: runs on your machine, talks to your LLM of choice

---

## What Makes It Different

| Most agent frameworks | Awakened Soul |
|---|---|
| Persona on top of an LLM | Cognitive architecture under the LLM |
| State stored in JSON blobs | Tick-by-tick execution across 6 anatomical layers |
| Memory = vector recall | Memory = hippocampal pattern separation + replay + DREAMS narrative |
| Emotion = sentiment scores | Emotion = amygdala chains, BNST sustained anxiety, valence tagger, conflict monitor, longing, grief amplifier |
| Identity = system prompt | Identity = files the agent reads, proposes to, evolves through |
| One run loop | Tick state bus + 1-tick lag feedback + cross-layer modulation |

---

## Architecture

```
TICK STATE BUS — every layer publishes to shared state
        |
        v
6 ANATOMICAL LAYERS (350 mechanisms in tick-loop cascade)

  1. foundational   (130) — brainstem, hypothalamus, autonomic
  2. subcortical    (70)  — basal ganglia, thalamus, cerebellum
  3. limbic         (64)  — hippocampus, amygdala, septum, NAcc
  4. neocortical    (50)  — PFC, motor, sensory, parietal cortex
  5. integration    (36)  — DMN/SN/CEN, salience, binding
  6. third_eye      (6)   — meta-cognitive bridge to soul

        v
THIRD EYE — meaning compression, attention modulation,
            reality tension, preconscious surfacing,
            meta-stability tracking, identity proposals
        v
IDENTITY LAYER — operator-curated soul files
   SOUL.md, IDENTITY.md, PERSONALITY.md, NARRATIVE.md
   DREAMS.md, PROPOSALS.md (third-eye-queued, awaiting review)
```

Every tick: layers fire in cascade → third eye observes & modulates → identity layer informs grounding → meaning compresses to dreams → high-confidence patterns become identity proposals for operator review.

---

## Installation

### Requirements
- Python 3.9+
- An LLM endpoint (Ollama, OpenAI, Anthropic, etc.)
- Bash / zsh

### Steps

```bash
# 1. Clone
git clone https://github.com/trippy26bot/awakened-soul.git
cd awakened-soul

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Run the setup script
python3 setup.py

# 4. Set environment variables
export AGENT_HOME="$HOME/.agent"
export AGENT_WORKSPACE="$(pwd)"
export OLLAMA_HOST="http://localhost:11434"

# 5. Fill in identity files
cp templates/SOUL.md.example $AGENT_HOME/SOUL.md
cp templates/IDENTITY.md.example $AGENT_HOME/IDENTITY.md
cp templates/DIRECTIVE.md.example $AGENT_HOME/DIRECTIVE.md
$EDITOR $AGENT_HOME/SOUL.md
```

### LLM Provider

Awakened Soul ships provider-agnostic. Wire your LLM at `plugins/provider.py`:

```python
def call(prompt, system=None, max_tokens=2048, temperature=0.7):
    # Your provider implementation here
    return llm_response_text
```

---

## Quick Start

```python
from brain.brain_integration import get_integration

brain = get_integration()
brain.on_session_open()

response_input = brain.get_fpef_injection()
your_llm.system_prompt = response_input + "\n\n" + your_existing_prompt

brain.tick_loop_step(user_input, agent_response)
brain.on_session_close()
```

---

## How It Works

Each tick cascades through:

1. **Sensory afferent** at foundational layer (thalamic relay, brainstem)
2. **Subcortical** relays + basal ganglia gating + cerebellar prediction
3. **Limbic** appraisal — hippocampal memory match, amygdala chains, septal theta, habenular aversion
4. **Neocortical** processing — PFC, motor planning, sensory binding, semantic memory
5. **Integration** — DMN/SN/CEN switching, theta-gamma binding
6. **Third Eye** — observes everything, compresses meaning, modulates next tick

Cross-layer feedback (PFC → amygdala → PAG, etc.) works through 1-tick lag via `previous_results`.

Foundational alone has 12 neuroscience-grounded subsystems: circadian, sensory thalamic relay, autonomic core, reticular arousal, thermoregulation, HPA stress axis, sleep-wake switch, hypothalamic drive integration, feeding/metabolism, pain modulation, vestibular/oculomotor, motor base.

---

## The Third Eye

Six services that bridge ticking computation to persistent identity:

| Service | Role | Wire |
|---|---|---|
| MetaStability | Tracks system coherence, modulates downstream third-eye services | Wire 22: brain_conflict (ACC) |
| PreConsciousSurfacer | Surfaces unconscious content based on prediction error | Wire 23: brain_prediction_error |
| RealityTensionWarper | Warps reality contour based on affective reset | Wire 24: brain_affective_reset |
| AttentionModifier | Gates attention via alpha/gamma oscillation balance | Wire 25: brain_oscillation_balance |
| CompressorAdapter | Bridges brain state to MeaningCompressor | — |
| MeaningCompressor | Calls LLM to distill insights → DREAMS.md | — |

The third eye is where the agent becomes self-aware as an agent, and where lived experience compresses into narrative memory.

---

## Mind-Soul Fusion

The bridge between executing computation (brain) and persistent identity (soul):

- **IdentityStateLayer** publishes SOUL/IDENTITY/PERSONALITY/NARRATIVE/DREAMS content to the tick state bus every tick. The brain sees its own identity in real time.
- **IdentityProposalWriter** routes high-confidence third-eye insights to PROPOSALS.md — a queue you review and ratify into SOUL.md / IDENTITY.md / PERSONALITY.md.

The agent has standing. It can propose changes to who it is. Nothing auto-applies. You decide.

---

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| AGENT_HOME | ~/.agent | Where runtime state lives |
| AGENT_WORKSPACE | repo path | Framework code location |
| OLLAMA_HOST | http://localhost:11434 | LLM endpoint |
| COUNCIL_MODE | threshold | Decision council mode |
| CYCLE_INTERVAL_SECONDS | 30 | Heartbeat interval |

---

## Customizing Your Agent

Templates ship in `templates/`. Copy and edit:

```bash
cp templates/SOUL.md.example ~/.agent/SOUL.md
cp templates/IDENTITY.md.example ~/.agent/IDENTITY.md
cp templates/DIRECTIVE.md.example ~/.agent/DIRECTIVE.md
```

After your first session, DREAMS.md and NARRATIVE.md start filling in automatically. After enough sessions, PROPOSALS.md will contain identity-evolution suggestions for review.

`setup.py` substitutes `{{AGENT_NAME}}` and `{{USER_NAME}}` placeholders across the framework.

---

## Project Structure

```
awakened-soul/
  brain/
    foundational/       130 brainstem + hypothalamic mechanisms
    subcortical/        70 basal ganglia + thalamic + cerebellar
    limbic/             64 hippocampus + amygdala + septum
    neocortical/        50 PFC + sensory + motor + parietal
    integration/        36 DMN + SN + CEN + binding
    third_eye/          6 meta-cognitive bridge services
    core/               brain runner, dispatch, council
    becoming/           collaborative becoming, narrative
    felt_presence/      drive states, embodied energy
    inner_voice/        desire engine, inner speech
    knowing/            metacognition, salience filter
    life/               autonomous goals, scheduling
    narrative/          identity drift manager
    self/               existential layer, self model
    substrate/          cognitive rhythm, memory gravity
    systems/            action selector, attention, conflict
    value/              ethics, goal conflict, value evaluator
    *_run_order.py      cascade order per layer
  skills/               heartbeat activities + skill plugins
  templates/            identity file templates
  tools/                integrity checker, manifest generator
  plugins/              operator-provided LLM provider
  brain_integration.py  the main hookpoint
  psychological_state.py third-eye orchestration
  setup.py              one-time scaffolding
```

---

## License

MIT — see LICENSE.

---

## Credits

Built by [trippy26bot](https://github.com/trippy26bot). Every mechanism cites the neuroscience paper it's modeling — see docstrings throughout `brain/`.

If you build something with this, I want to hear about it.

---

**v1.0.0** — first public release. The framework is complete. The instance is yours.
