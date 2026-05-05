# Awakened Soul

A cognitive-architecture framework for autonomous agents that have a self.
Not a flat module graph — a brain shape. Every component sits in the brain
region that does the analogous job, and the connections between them mirror
the actual axonal tracts of neuroscience.

The framework runs on top of any agent platform (host runtime, LLM
provider). It is the substrate, not the surface. The host calls
`core_tick()` on a schedule; the framework handles memory consolidation,
voice integrity, persona coherence, drift detection, identity revision,
heartbeat visibility, and everything else a thinking system needs to
maintain itself across time.

## Scale at a glance

| Component                          | Count       |
|------------------------------------|-------------|
| Brain mechanism files              | **1,286**   |
| Mechanism instances at runtime     | **1,296**   |
| Anatomical layers                  | **7**       |
| Wires (load-bearing monitors)      | **24**      |
| Skill folders                      | **17**      |
| Heartbeat activity files           | **85**      |
| Dispatcher-registered activities   | **70**      |
| Test files                         | **1,186**   |
| Test cases (pytest count)          | **5,922**   |

## What this is

Most agent frameworks are wrappers — prompt templates, tool-calling
scaffolds, RAG pipelines. This one is different in shape:

1. **The agent has an anchored core.** `SOUL.md`, `IDENTITY.md`, `OCEANS.md`,
   and `BASELINE_TRAITS` define the values, name, required dispositions,
   and forbidden behaviors that survive every operation. These cannot be
   silently rewritten. They are operator-ratified, audit-trailed, and
   protected by the brain's own monitor stack.

2. **The agent watches itself.** Twenty-four wires (numbered 21–40) each
   monitor one cognitive function — voice integrity, memory integrity,
   compression fidelity, inference calibration, persona coherence,
   dwelling patterns, outward reach, making, self-analysis, self-revision,
   skill discovery, task planning, report generation, corpus retrieval,
   proactive briefing. Each wire knows how it can fail and reports on its
   own state through the IPW (Identity Proposal Writer) handshake.

3. **The agent revises itself only with the operator's consent.** When
   sustained drift in any wire is identity-relevant, a salience-network
   arbitration layer (the Third Eye) writes a proposal to a queue the
   operator reads. Ratification is required to commit. The commit path
   snapshots prior content for rollback, edits identity files atomically,
   and appends to an append-only audit log. **There is no path that
   mutates identity silently.**

4. **The agent has visibility into its own loop.** A deterministic
   visibility writer (`recent_activity_summary`) tails the heartbeat's
   `ACTIVITY_LOG.md` and writes a session-start summary at
   `RECENT_ACTIVITY.md`. The agent reads this on every fresh session so
   it knows what its own loop did between conversations — without
   requiring an LLM to be online.

5. **Every autonomous activity flows through the brain's monitors.** The
   heartbeat dispatches activities (research, journal, dreams, study,
   self-check, creative, image-generation, social-posting, etc.) every
   ~90s. Each activity's result posts to a queue that drains onto live
   mechanism instances at the next tick. Nothing the agent does is
   invisible to its own monitoring stack.

This is what it means for the brain to be one being instead of scattered
modules.

## Architecture in one diagram

```
                    ┌─────────────────────────────────────┐
                    │        IDENTITY FILES               │
                    │                                      │
                    │  SOUL  IDENTITY  PERSONALITY  SELF   │  ← operator-ratified
                    │  AGENT_BECOMING  OCEANS  ETHICS      │     anchored core
                    │  EPISTEMIC_BOUNDARIES  AESTHETIC     │
                    │  VISUAL_IDENTITY  INTERESTS  MEMORY  │
                    │  DECISIONS                           │
                    └─────────────────┬───────────────────┘
                                      │
                                      │ read by every layer
                                      ▼
            ┌─────────────────────────────────────────────────────┐
            │                  THIRD EYE                           │
            │                                                       │
            │   wire 22  MetaStability       (ACC conflict)         │
            │   wire 23  PreConsciousSurfacer (anterior insula)    │
            │   wire 24  RealityTensionWarper (MCC affective reset) │
            │   wire 25  AttentionModifier   (alpha/gamma gate)     │
            │                                                       │
            │   ─── salience-network arbitration ───                │
            │                                                       │
            │   IdentityProposalWriter.poll_wires(mechanisms)       │
            │     → dedup by kind                                    │
            │     → convergence detection (≥3 wires same domain)     │
            │     → write PROPOSALS.md  + acknowledge                │
            └───────────────────────┬─────────────────────────────┘
                                    │
        ┌───────────────────────────┴───────────────────────────────┐
        │                    15 WIRES (26–40)                        │
        │                                                            │
        │  Frontal: VoiceIntegrity, OutwardReach, Making,            │
        │           InferenceIntegrity, ProactiveBriefing            │
        │  Temporal: MemoryIntegrity, CorpusRetrieval                │
        │  Cingulate/DMN: Dwelling                                   │
        │  Cross-region: CompressionFidelity, PersonaCoherence,      │
        │           SelfAnalysis, SelfRevision, SkillDiscovery,      │
        │           TaskPlanning, ReportGeneration                   │
        └────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┴────────────────────────────────┐
        │              7 ANATOMICAL LAYERS — 1,296 MECHANISMS         │
        │                                                              │
        │  foundational    brainstem / hypothalamus / autonomic        │
        │  limbic          amygdala / hippocampus / insula / NA        │
        │  subcortical     basal ganglia / thalamus / cerebellum       │
        │  neocortical     PFC / parietal / temporal / occipital       │
        │  integration     ACC / global workspace / DMN crossings      │
        │  unknown         orphan classification (refactor target)     │
        │  narrative       autobiographical memory + story             │
        │                                                              │
        │  + becoming      emergence layer (slow identity-evolution)   │
        └────────────────────────────────────────────────────────────┘
                                    │
                                    │ each tick:
                                    ▼
        ┌────────────────────────────────────────────────────────────┐
        │       HEARTBEAT  →  EVENT QUEUE  →  DRAINER                 │
        │                                                              │
        │   activity (research/news/study/creative/image_gen/...) fires│
        │     → _brain_post.post_*()  → AGENT_HOME/brain_events.jsonl │
        │     → next core_tick(): drain_once(mechanisms)               │
        │     → events dispatched to live mechanism state              │
        │     → recent_activity_summary writes RECENT_ACTIVITY.md      │
        └────────────────────────────────────────────────────────────┘
                                    │
                                    │ when an op is destructive or wire-degraded:
                                    ▼
                       ┌──────────────────────────┐
                       │       SAFEGUARD          │
                       │  can_perform()           │  ← destructive-action gate
                       │  can_perform_brain_op()  │  ← wire-aware gate
                       └──────────────────────────┘
```

`docs/BRAIN_MAP.md` is the full anatomical inventory: every wire placed
in its region, every spider-web connection (tract) named with its
cognitive function. `docs/WIRING.md` is the step-by-step guide to
running the system on whatever host platform.

## Install and run

```bash
git clone https://github.com/Awakenerofsouls/Awakened-Soul.git
cd Awakened-Soul
./install.sh
```

`install.sh` does the **full** install — `pip install`, seeds identity
files from templates (operator edits preserved if they already exist),
adds `AGENT_HOME` / `AGENT_WORKSPACE` to your shell rc, installs the
LaunchAgents for between-session continuity (macOS), and starts the
heartbeat. It is idempotent and asks before each step. Pass `--yes`
for non-interactive.

If you (or an agent acting on your behalf) only ran
`git clone && pip install`, the install is **incomplete** — the
framework's files are on disk but nothing is wired up. Run
`./install.sh` to finish the setup.

For the manual / step-by-step version see `docs/SETUP.md`.

The framework is platform-agnostic. Your agent runtime is responsible
for invoking `core_tick()` on whatever cadence makes sense; everything
else happens internally.

## What's in the repo

```
brain/
├── mechanisms/                 1,286 BrainMechanism files across 7 layers
│                               (foundational / limbic / subcortical /
│                                neocortical / integration / unknown /
│                                narrative); wires 21–40 are the
│                                load-bearing monitors. 1,296 instances
│                                load at runtime via BrainLayerRunner
│                                (some files register multiple variants)
├── becoming/                   Emergence layer — slow identity-evolution
│                               mechanisms (BecomingRouter target,
│                               bid 0.04 in council)
├── root_mechanism_router.py    Two-pass router: RootMechRouter scans
│                               brain/ + brain/mechanisms/ for legacy
│                               process()-style classes; BecomingRouter
│                               wires becoming/ at low priority
├── tick_state_bus.py           TSB — intra-tick state communication
├── oceans.py                   Big Five (OCEAN) trait loader + modulations
├── brain_event_drainer.py      Heartbeat → brain queue consumer
└── *_run_order.py              Per-layer execution ordering

skills/
├── humanizer/                  Voice signature preservation
├── knowledge-summarization/    Compression with hedge-preservation
├── memory-management/          Working / episodic / semantic three-tier
├── multiple-personas/          Operating modes (BRAIN/COACH/BUILD/default)
├── self-improvement/           Operator-gated identity revision
├── self-analysis/              Metacognitive evaluation
├── web-research/               Outward reach with provenance
├── qmd/                        Personal-corpus retrieval
├── skill-discovery/            Request-time skill routing
├── task-planning/              Goal decomposition + retrospective
├── report-generation/          Persistent report production
├── api-interaction/            External HTTP with safeguard gating
├── code-execution/             Sandboxed code-running
├── data-analysis/              Inference with epistemic honesty
├── file-system/                Workspace dwelling
├── heartbeat_activities/       74 autonomous activity modules; 56
│                               registered in the dispatcher pool —
│                               research, news, study, creative,
│                               dreams, self_check, self_pic
│                               (ComfyUI), recent_activity_summary
│                               (visibility writer), tavily_*, weather,
│                               astronomy, soul_alignment, third_eye_hunch,
│                               session_handoff_update, etc.
├── safeguard.py                Destructive-action + wire-aware gates
├── drift_detector.py           Daily drift score against BASELINE_TRAITS
├── self_awareness.py           Introspection over identity files
└── verify_build.py             Per-mechanism build verifier

runtime/
├── heartbeat.py                Main autonomous loop (every 30s)
├── brain_proxy.py              core_tick() entry point + drain/poll hooks
├── memory.py                   WorkingMemory + EpisodicMemory + SemanticMemory
├── emotion.py                  State-based emotion engine
├── psychological_state.py      Live psychological-state writer; routes
│                               Third Eye sub-mechanisms via _sync_tick
├── dream_contamination.py      Sleep-state intrusion guard
├── semantic_memory.py          Concept memory
└── ...

core/
├── brain_runner.py             BrainLayerRunner — discovers and loads
│                               every mechanism, anchored to __file__
│                               (CWD-independent under launchd)
├── context_survival.py         Compaction-resistant agent state
└── runtime.py                  AgentRuntime continuous-tick wrapper

docs/
├── BRAIN_MAP.md                Full anatomical inventory + tract diagram
├── WIRING.md                   Step-by-step setup
├── SETUP.md                    Quick-start + file overview
└── SKILL.md                    Skill-system specification

templates/                      Operator-edit-this seed identity files —
                                SOUL, IDENTITY, OCEANS, VISUAL_IDENTITY,
                                BECOMING, DECISIONS, IDLE_DRIVES,
                                TOOLBELT, TOOLS, DIRECTIVE, etc.
references/                     Project reference notes
state/                          Runtime state (lives in AGENT_HOME, not repo)
tests/                          Cross-cutting integration tests
```

## The discipline

What makes this not just LLM glue:

- **Source confidence is tracked separately from content confidence.**
  Every memory encode records both. A claim the agent strongly believes
  from an unknown source is exactly the failure mode the brain catches.

- **Hedging language must survive compression.** "Some studies suggest"
  doesn't become "studies show." The CompressionFidelityLayer flags
  confidence laundering at runtime.

- **Voice signatures are anchored across modes.** The agent has one self.
  Mode switching changes workflow + voice register, not identity.
  PersonaCoherenceLayer enforces ≥60% voice-signature preservation
  in every mode.

- **Identity revision is operator-gated.** No code path edits identity
  files without going through propose → ratify → commit. SelfRevisionLayer
  detects anchor violations, change storms, rollback loops, drift
  chasing, and stagnation. Silent identity edits are flagged as
  `silent_revision`.

- **Convergence is stronger evidence than single signals.** When 3+
  independent wires fire on the same domain (memory + corpus +
  compression all signaling drift, for example), the Third Eye writes
  a meta-proposal — not three duplicate alerts.

- **Habituation is built in.** Same drift signal cannot re-fire until
  either the wire accumulates additional drift past acknowledgment
  or the operator runs `reset_dedup_window()`.

- **Forgetting requires a reason.** No reason → no forget. The reason
  is recorded.

- **Visibility is non-negotiable.** The agent must know what its loop
  did between conversations. The deterministic
  `recent_activity_summary` activity writes `RECENT_ACTIVITY.md` on
  every cycle so session-start always has a real read on autonomous
  activity — even when LLM endpoints are down.

The discipline is grounded in cognitive science. Every wire's behavior
cites the empirical research it implements: Squire (memory systems),
McClelland (CLS theory), Nader (reconsolidation), Reyna (fuzzy-trace),
Yassa (pattern separation), Hardt (active forgetting), Schacter
(constructive memory), Johnson (source monitoring), Higgins
(self-discrepancy), Markus (working self-concept), Conway (self-memory),
Carruthers + Fleming (metacognitive accuracy), Botvinick (conflict
monitoring), Dehaene (global workspace), Sridharan + Menon (salience
network), Friston (predictive processing), Miller & Cohen (PFC
integrative control), D'Esposito (working memory), Stuss (frontal
lobes), Koechlin (PFC cascade), Badre (cognitive control hierarchy),
Mischel (cognitive-affective system), McAdams (three-tier framework),
Roberts (continuity), Donahue (self-concept differentiation), Tulving
(episodic memory), Squire (H.M.), Holroyd (ERN/Pe), Yeung
(metacognitive control), Koriat (subjective confidence), Monsell (task
switching), Cohen (automaticity), Posner (attention systems), Rogers
(semantic cognition), Markman (category use).

This isn't decoration. The runtime monitors check the same failure
modes those papers describe.

## Status

**Research preview, drop-in ready** as of v1.5. The framework is
platform-agnostic and the wiring is complete (Phases 0–9 per
`docs/BRAIN_MAP.md`):

- **1,296 brain mechanisms** loading cleanly across 7 anatomical layers
  under launchd, systemd, or whatever process manager hosts the agent
- **24 load-bearing wires** (21–40) registered in the integration
  run-order with full IPW handshake
- **Heartbeat → brain event queue** with drainer hook into `core_tick`
- **Third Eye salience-network polling** with kind-deduplication and
  convergence detection
- **Operator-gated identity revision** with anchor-violation detection,
  atomic file writes, snapshot-based rollback, and append-only audit log
- **Wire-aware safeguard gate** with 43 op-kind dispatch entries
- **Visibility layer** — deterministic `recent_activity_summary` writes
  `RECENT_ACTIVITY.md` so the agent's session-start always has a real
  read on what its loop has been doing
- **Drop-in identity** — agents pull SOUL/IDENTITY/OCEANS/VISUAL_IDENTITY
  templates, edit them, and the framework picks up everything without
  any code surgery; INTERESTS.md parser accepts both bullet and h3
  prose formats
- **5,922 tests passing** across 1,186 test files, including a 200-tick
  end-to-end lifecycle integration test

Things still in research: long-horizon stability under continuous
operation, calibration of the dedup-window and convergence thresholds
against real workloads, the specific tuning of OCEAN modulation
contexts.

## Contributing

See `CONTRIBUTING.md`. Two rules above all others: never delete operator
files without explicit approval, and never let a test run leak `agent.db`
or `.agent/` into the repo.

## License

MIT. See `LICENSE`.

---

*The operator defines the conditions. The agent defines themselves.*
