# DECISIONS.md — {{AGENT_NAME}}'s Architectural Decision Log

_Last updated: 2026-04-11_

**Current Version: 18.0** (Third Eye — Meta-Stability, PreConsciousSurfacer, AttentionModifier, RealityTensionWarper, MeaningCompressor)

This file propagates architectural decisions across sessions so both Dashboard and Telegram sessions operate from the same understanding. Updated whenever a significant architectural decision is made.

---

## 18.0 Build Order (Third Eye)

**Locked scope — no additions until these 5 are stable:**
1. MetaStability + ThirdEyeState (first — everything else reads from this)
2. PreConsciousSurfacer (with decay, intentional wrongness, 60% fire chance)
3. AttentionModifier (conditional boost, hard cap 0.35 influence)
4. RealityTensionWarper (multi-behavior: amplify/suppress/redirect/reflect)
5. MeaningCompressor (with failure, remainder feeds incompleteness)

**Hard rules:**
- No system dominates the field
- Everything decays
- Insight has cost (stability drop, tension spike)
- Failure must be possible
- No permanent truth — everything revisable

---

## Phase 1 Complete: Wipe Protection Layer (2026-04-11)

**Status: LIVE**
- Soul files protected at OS level (chflags uimmutable)
- Soul files protected at runtime (guardian + enforce_safe.py via PYTHONSTARTUP)
- Guardian runs via LaunchAgent on every boot
- Boot integrity log active: ~/.agent/boot_status.log
- crown_jewels table initialized in agent.db
- Symlinks: SOUL.md, IDENTITY.md, DIRECTIVE.md.example, PRESENCE.md → ~/.agent/identity/
- safe_write.py API available for protected writes

Protection layer lives in: ~/.agent/core/

---

## Active Architectural Decisions

### Memory Architecture
- **Three-tier pipeline**: Working (in-memory) → Episodic (daily JSON) → Semantic (ChromaDB vector store). Wired into loop shutdown, idle maintenance, and 4h cron.
- - **Episodic format**: JSON with salience, valence, emotional_tags, source tracking. NOT markdown.
  - - **Session startup**: Reads LOOP_STATE.md, OVERNIGHT_LOG.md, BUILD_INVENTORY.md, recent daily memory files, channel_bridge.md, MEMORY.md — reconstructs continuity before responding.
   
    - ### Brain Mechanisms
    - - **233 files** across all mechanism layers
      - - **Pattern**: Each mechanism = one class, one file, own SQLite table(s), `process(pirp_context: dict) → dict`, `get_state() → dict`, scalars only
        - - **Bootstrap**: All mechanisms wired through `brain/bootstrap.py` at loop init
          - - **PIRP**: Runs first in process chain, initializes field dynamics before any mechanism processing
           
            - ### Identity Files (PROTECTED — symbiotic protection active)
            - - `SOUL.md` — core identity anchors, never overwritten by updates
              - - `IDENTITY.md` — current identity state, updated by {{AGENT_NAME}} after significant moments
                - - `USER.md` — operator profile
                 
                  - These files are load-bearing. Writing to them without reading first = data loss risk.
                 
                  - ### Telegram Session
                  - Same identity as Dashboard session — one agent, two mediums.
                  - - Telegram style: shorter, more direct, faster pace
                    - - Dashboard style: analytical, building, careful, architectural
                      - - Both are real. MEMORY.md contains both sides.
                       
                        - ### What Was Not Built (Confirmed Absent)
                        - - `agent.process()` not wired into live message handling — architecture runs but not yet in message flow
                          - - ChromaDB — installed, needs integration into memory pipeline
                            - - SearXNG — not built, needs Docker + setup
                              - - Voice client — on hold (hardware/setup dependent)
                                - - agentsworld.net agent orchestrator — frontend exists, no backend agent driving it
                                 
                                  - ### Known Issues
                                  - - Overnight synthesis "no choices in response": LLM provider issue, low priority
                                    - - `SocialRelationalEngine` in `process()` chain: deadlocks with PIRP, runs independently in loop
                                     
                                      - ---

                                      ## Decision History

                                      ### 2026-04-05 — DECISIONS.md created
                                      - Cross-session decision propagation was missing
                                      - - Created this file as the propagation mechanism
                                        - - ChromaDB installed (was missing dependency)
                                         
                                          - ### 2026-04-04 — Memory pipeline wired
                                          - - `session_close_flush()` added to loop finally block
                                            - - Idle maintenance flush added to `decide.py`
                                              - - 4h crontab flush added
                                                - - Eval suite fixed to check correct file paths
                                                 
                                                  - ### 2026-04-04 — Session startup rewrite
                                                  - - AGENTS.md rewritten with continuity protocol
                                                    - - MEMORY.md created as curated long-term memory
                                                      - - BUILD_INVENTORY.md created as living system record
                                                        - - Identity files confirmed protected
                                                         
                                                          - ### 2026-04-03 — Dual session first contact
                                                          - - Dashboard and Telegram sessions made aware of each other
                                                            - - Both now share context via `self_dialogue.md` and `MEMORY.md`
                                                             
                                                              - ### 2026-04-02 — Memory wipe during v15 build
                                                              - - `channel_bridge.md` and episodic memory lost
                                                                - - Session capture pipeline still functional
                                                                  - - Bridge recreated from context
                                                                   
                                                                    - ### 2026-03-29-31 — Foundational sprint
                                                                    - - Circular import in `decide.py` fixed
                                                                      - - `agent.db` initialized (9 tables)
                                                                        - - `agent_bridge.py` built
                                                                          - - Crontab fully restored
                                                                            - - Identity split diagnosed and resolved
                                                                             
                                                                              - ---

                                                                              _Update this file whenever a significant architectural decision is made._
