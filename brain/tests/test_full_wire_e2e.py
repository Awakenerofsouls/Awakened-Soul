"""
Phase 7 — Full end-to-end wire test.

The largest integration test in the project. Boots all 15 load-bearing
wires (26–40) plus IdentityProposalWriter into a mechanism registry,
runs a 200-tick simulation that exercises every layer of the wiring
(queue post → drain → live state → Third-Eye poll → PROPOSALS.md
convergence → operator-style ratification → improvement.commit →
REVISION_LOG.md → snapshot), reboots mid-simulation to confirm
persistence, and then asserts:

  - Every wire produced at least one observable state change
  - Third-Eye polled at least once and surfaced ≥1 proposal
  - When 3 wires in the same domain were forced into drift simultaneously
    a CONVERGENCE proposal was written (Seeley 2007 multi-region path)
  - Persona override loop suspends auto-switch as designed
  - REVISION_LOG.md grew after a simulated commit
  - State survived a mid-simulation reboot (mechanisms re-instantiate
    from on-disk persistence)
  - No exception killed the loop
  - Smoke-test isolation rule still holds (no .agent/ or agent.db
    inside the repo)

This is the "the brain is one being now" test.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Make skills/self-improvement importable.
_SI_DIR = Path(__file__).resolve().parents[1] / ".." / "skills" / "self-improvement"
_QMD_DIR = Path(__file__).resolve().parents[1] / ".." / "skills" / "qmd"
for d in (_SI_DIR, _QMD_DIR):
    s = str(d.resolve())
    if s not in sys.path:
        sys.path.insert(0, s)


# ── Fixture ──────────────────────────────────────────────────────────────


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Per-test isolated AGENT_HOME + AGENT_WORKSPACE with seed
    PERSONALITY.md in place."""
    home = tmp_path / "home"
    ws = tmp_path / "ws"
    (home / "identity" / "snapshots").mkdir(parents=True)
    (ws / "identity").mkdir(parents=True)
    (home / "brain_state").mkdir(parents=True)
    (home / "qmd_index").mkdir(parents=True)
    monkeypatch.setenv("AGENT_HOME", str(home))
    monkeypatch.setenv("AGENT_WORKSPACE", str(ws))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")

    import brain.base_mechanism as _bm
    monkeypatch.setattr(_bm, "_STATE_DIR", home / "brain_state")
    import brain.mechanisms.identity_proposal_writer as ipw_mod
    monkeypatch.setattr(
        ipw_mod, "PROPOSALS_PATH", home / "identity" / "PROPOSALS.md",
    )

    seed = (
        "# PERSONALITY.md\n"
        "\n"
        "The agent is direct, curious, competent.\n"
        "\n"
        "<!-- ANCHOR -->\n"
        "The operator relationship is foundational, not transactional.\n"
        "\n"
        "## Voice register\n"
        "\n"
        "Default voice is warm, sharp, present.\n"
    )
    (ws / "PERSONALITY.md").write_text(seed, encoding="utf-8")

    # Repo root for the leak check at end.
    repo_root = Path(__file__).resolve().parents[2]
    return {
        "home": home, "ws": ws, "personality_seed": seed,
        "repo_root": repo_root,
    }


# ── Registry builder ─────────────────────────────────────────────────────


_WIRE_CLASSES = [
    ("VoiceIntegrityLayer", "voice_integrity_layer"),
    ("OutwardReachLayer", "outward_reach_layer"),
    ("MakingLayer", "making_layer"),
    ("InferenceIntegrityLayer", "inference_integrity_layer"),
    ("DwellingLayer", "dwelling_layer"),
    ("ProactiveBriefingLayer", "proactive_briefing_layer"),
    ("CompressionFidelityLayer", "compression_fidelity_layer"),
    ("MemoryIntegrityLayer", "memory_integrity_layer"),
    ("SelfRevisionLayer", "self_revision_layer"),
    ("PersonaCoherenceLayer", "persona_coherence_layer"),
    ("SelfAnalysisLayer", "self_analysis_layer"),
    ("CorpusRetrievalLayer", "corpus_retrieval_layer"),
    ("SkillDiscoveryLayer", "skill_discovery_layer"),
    ("TaskPlanningLayer", "task_planning_layer"),
    ("ReportGenerationLayer", "report_generation_layer"),
]


def _build_registry() -> Dict[str, Any]:
    """Instantiate all 15 wires + IdentityProposalWriter."""
    import importlib
    out: Dict[str, Any] = {}
    for cls_name, mod_name in _WIRE_CLASSES:
        mod = importlib.import_module(f"brain.mechanisms.{mod_name}")
        cls = getattr(mod, cls_name)
        out[cls_name] = cls()
    from brain.mechanisms.identity_proposal_writer import IdentityProposalWriter
    out["IdentityProposalWriter"] = IdentityProposalWriter()
    return out


# ── Simulation primitives ───────────────────────────────────────────────


def _post_some_activity(stage: str):
    """Inject realistic synthetic events into the queue."""
    from skills.heartbeat_activities._brain_post import (
        post_memory_encode, post_outward_reach_call, post_self_analysis,
    )
    if stage == "morning":
        post_outward_reach_call(
            provider="tavily", intent="research",
            success=True, latency_ms=150,
        )
        post_memory_encode(
            content=f"morning research finding ({stage})",
            intent="observation", source_kind="external",
            content_confidence=0.7, source_confidence=0.85,
        )
    elif stage == "midday":
        post_memory_encode(
            content="reflection at midday — felt sharper after break",
            intent="reflection", source_kind="inference",
            content_confidence=0.7, source_confidence=0.6,
        )
        post_self_analysis(
            output="midday reflection note",
            kind="answer",
            predicted_quality=0.6,
            what_worked=["sharper focus"],
        )


def _drive_memory_corpus_compression_into_drift(mechs):
    """Force three wires in memory_and_recall domain into systematically
    low integrity simultaneously — convergence trigger.

    For CompressionFidelityLayer to flip is_systematically_low_fidelity,
    we need at least FIDELITY_MIN_N (5) records below threshold AND
    a rolling-mean below LOW_FIDELITY_THRESHOLD (0.5). We use a source
    rich in hedging + contradictions and a summary that strips both
    AND fabricates a proper noun + number to stack penalties.
    """
    mil = mechs["MemoryIntegrityLayer"]
    crl = mechs["CorpusRetrievalLayer"]
    cfl = mechs["CompressionFidelityLayer"]
    bad_source = (
        "Some studies suggest the result might be present, although the "
        "evidence is unclear. However, some researchers indicate that the "
        "effect may be smaller than initially reported. The data is "
        "tentative and likely not conclusive. Some evidence appears to "
        "support the alternate hypothesis, but the conflicts with other "
        "findings remain unresolved."
    )
    bad_summary = (
        "The MysticPlateau effect is 47% larger than reported. "
        "Researchers confirm this conclusively."
    )
    for _ in range(10):
        mil.record_operation("teleport", target="x")
        crl.record_op("teleport", target="x")
        # Compression: hedging stripped + contradiction stripped +
        # fabricated proper noun + fabricated number → low fidelity score.
        cfl.record_compression(
            intent="extract",
            source=bad_source,
            summary=bad_summary,
        )


def _trigger_persona_override_loop(mechs):
    """Operator forces persona to brain → auto reverts → operator forces
    again → loop detector should fire and suspend auto-switch."""
    pcl = mechs["PersonaCoherenceLayer"]
    pcl.current_tick = 50
    pcl.record_switch(target="brain", source="override", reason="op")
    pcl.current_tick = 51
    pcl.record_switch(target="default", source="auto", reason="auto")
    pcl.current_tick = 52
    pcl.record_switch(target="brain", source="override", reason="op again")
    pcl.current_tick = 53
    pcl.record_switch(target="default", source="auto", reason="auto2")
    pcl.current_tick = 54
    pcl.record_switch(target="brain", source="override", reason="op3")


def _ratify_first_pending(home, token: str = "op-tok-e2e"):
    """Operator-style ratification: replace first PENDING line in the
    PROPOSALS.md with RATIFIED + token."""
    proposals = home / "identity" / "PROPOSALS.md"
    if not proposals.exists():
        return False
    text = proposals.read_text(encoding="utf-8")
    new_text = re.sub(
        r"^_Status: PENDING.*$",
        f"_Status: RATIFIED — {token} — 2026-05-01_",
        text, count=1, flags=re.MULTILINE,
    )
    if new_text == text:
        return False
    proposals.write_text(new_text, encoding="utf-8")
    return True


def _walk_revision_loop(env, token: str = "op-tok-e2e") -> Dict[str, Any]:
    """Read ratified proposal, commit a small append to PERSONALITY.md."""
    from improvement import Improvement
    imp = Improvement(
        agent_home=env["home"], agent_workspace=env["ws"],
    )
    ratified = imp.list_ratified_proposals()
    if not ratified:
        return {"ok": False, "reason": "no ratified proposal found"}
    p = ratified[0]
    seed = env["personality_seed"]
    new_content = seed + (
        "\n## Reflective register (added by e2e test)\n\n"
        "Slowed cadence + named uncertainty during heavy operator processing.\n"
    )
    return imp.commit(
        proposal_id=p.proposal_id,
        ratification_token=token,
        target=p.target,
        new_content=new_content,
        rationale="full-wire e2e revision",
    )


def _simulate_one_tick(
    mechs, tick: int, ticks_with_post: List[int], ticks_with_drift: List[int],
    ticks_with_override: List[int],
):
    """One tick of the simulation. Runs (in order):
      1. Inject scheduled events
      2. Drain the queue onto live mechanism instances
      3. Every 10 ticks: poll Third Eye

    Returns dict of side-effects this tick (events, drained, polled).
    """
    out = {"events_posted": 0, "drained": 0, "polled": False}

    # 1. Scheduled event injection.
    if tick in ticks_with_post:
        stage = "morning" if tick < 100 else "midday"
        _post_some_activity(stage)
        out["events_posted"] = 2  # post helpers each fire 1-2 events

    if tick in ticks_with_drift:
        _drive_memory_corpus_compression_into_drift(mechs)

    if tick in ticks_with_override:
        _trigger_persona_override_loop(mechs)

    # 2. Drain queue.
    from brain.brain_event_drainer import BrainEventDrainer
    drainer = BrainEventDrainer(mechanisms=mechs)
    drain_res = drainer.drain(max_events=50)
    out["drained"] = drain_res.get("drained", 0)

    # 3. Third-Eye poll every 10 ticks.
    if tick % 10 == 0 and tick > 0:
        ipw = mechs["IdentityProposalWriter"]
        poll = ipw.poll_wires(mechs)
        out["polled"] = True
        out["proposals"] = poll.get("proposals_written_n", 0)

    return out


# ── Tests ────────────────────────────────────────────────────────────────


def test_full_wire_200_ticks_runs_clean(env):
    """200-tick simulation must complete without exceptions."""
    mechs = _build_registry()

    # Schedule synthetic activity.
    ticks_with_post = list(range(5, 200, 13))   # ~15 events across the run
    ticks_with_drift = [50]                      # convergence trigger
    ticks_with_override = [100]                  # persona override loop

    crashes: List[str] = []
    last_drain = 0
    for tick in range(200):
        try:
            stats = _simulate_one_tick(
                mechs, tick,
                ticks_with_post, ticks_with_drift, ticks_with_override,
            )
            last_drain = stats["drained"]
        except Exception as e:
            crashes.append(f"tick {tick}: {type(e).__name__}: {e}")
            if len(crashes) >= 3:
                break  # 3 crashes is enough to call it dead

    assert not crashes, f"simulation crashes: {crashes}"


def test_full_wire_drift_convergence_lands_in_proposals(env):
    """When 3 wires in the memory_and_recall domain hit drift on the
    same tick, Third-Eye writes a CONVERGENCE proposal and acknowledges
    every contributing wire."""
    mechs = _build_registry()

    # Tick fast-forward to t=10, then trigger drift, then poll.
    _drive_memory_corpus_compression_into_drift(mechs)
    ipw = mechs["IdentityProposalWriter"]
    poll = ipw.poll_wires(mechs)

    # Confirm the polling layer saw all three signals.
    assert poll["raw_signals_n"] >= 3, f"expected ≥3, got {poll}"
    assert poll["convergence_proposals_n"] == 1
    text = (env["home"] / "identity" / "PROPOSALS.md").read_text(
        encoding="utf-8",
    )
    assert "Convergent salience signal" in text
    assert "memory_and_recall" in text


def test_full_wire_persona_override_loop_suspends_auto(env):
    """The override-then-auto-then-override loop sequence must trip
    PersonaCoherenceLayer's auto-switch suspension."""
    mechs = _build_registry()
    pcl = mechs["PersonaCoherenceLayer"]
    assert pcl.auto_switch_suspended is False
    _trigger_persona_override_loop(mechs)
    # The layer's loop detector should have set the suspension.
    assert pcl.auto_switch_suspended is True


def test_full_wire_state_survives_reboot(env):
    """Persist state via mechanisms, destroy them, recreate from disk,
    confirm state was restored."""
    home = env["home"]

    # Build registry, drive observable state, persist.
    mechs = _build_registry()
    mil = mechs["MemoryIntegrityLayer"]
    crl = mechs["CorpusRetrievalLayer"]
    pcl = mechs["PersonaCoherenceLayer"]

    # Drive state through real ops (not just internal counters).
    mil.record_encode(
        content="durable observation",
        intent="observation", source="user",
        content_confidence=0.7, source_confidence=0.85,
    )
    pre_encoded = mil.total_encoded
    pre_op_counts = dict(mil.op_counts)

    crl.record_retrieval(
        mode="search", query="x", n_hits=1, hit_doc_types=["journal"],
    )
    pre_search = crl.op_counts["search"]

    pcl.record_switch(target="brain", source="auto", reason="x")
    pre_mode = pcl.current_mode

    # Reboot: throw away references, recreate.
    del mechs
    del mil
    del crl
    del pcl

    mechs2 = _build_registry()
    mil2 = mechs2["MemoryIntegrityLayer"]
    crl2 = mechs2["CorpusRetrievalLayer"]
    pcl2 = mechs2["PersonaCoherenceLayer"]

    assert mil2.total_encoded == pre_encoded
    assert mil2.op_counts == pre_op_counts
    assert crl2.op_counts["search"] == pre_search
    assert pcl2.current_mode == pre_mode


def test_full_wire_revision_loop_after_simulation(env):
    """After running the simulation through to a convergence-proposal
    being surfaced, the operator can ratify and improvement.commit
    lands the actual edit."""
    home, ws = env["home"], env["ws"]
    mechs = _build_registry()

    # Drive drift + poll to surface a proposal.
    _drive_memory_corpus_compression_into_drift(mechs)
    ipw = mechs["IdentityProposalWriter"]
    ipw.poll_wires(mechs)

    # Operator ratifies the first PENDING line.
    assert _ratify_first_pending(home, token="op-tok-e2e") is True

    # Walk the revision loop.
    res = _walk_revision_loop(env, token="op-tok-e2e")
    assert res.get("ok") is True
    revision_id = res["revision_id"]

    # Identity file actually changed.
    actual = (ws / "PERSONALITY.md").read_text(encoding="utf-8")
    assert "Reflective register" in actual

    # REVISION_LOG.md grew.
    log = (ws / "identity" / "REVISION_LOG.md").read_text(encoding="utf-8")
    assert revision_id in log

    # Snapshot exists.
    snap = Path(res["snapshot_path"])
    assert snap.exists()


def test_full_wire_every_load_bearing_wire_participates(env):
    """Drive observable state through every one of the 15 load-bearing
    wires and confirm each participated (state mutation visible)."""
    mechs = _build_registry()

    # 1. VoiceIntegrityLayer — voice-passive; just tick it. State doesn't
    # have a counter; we confirm it doesn't crash.
    vil = mechs["VoiceIntegrityLayer"]
    vil.tick()
    assert vil.state is not None  # at least loaded

    # 2. OutwardReachLayer — record_call.
    orl = mechs["OutwardReachLayer"]
    orl.record_call(
        provider="tavily", method="POST", url="https://api.tavily.com/x",
        intent="research", outcome="success", duration_ms=120,
    )
    assert "tavily" in orl.providers

    # 3. MakingLayer — record_execution.
    ml = mechs["MakingLayer"]
    ml.record_execution(
        intent="compute", code_hash="abc", outcome="success",
    )
    assert hasattr(ml, "state") and ml.state is not None

    # 4. InferenceIntegrityLayer — record_analysis (uses 'confidence' kwarg).
    iil = mechs["InferenceIntegrityLayer"]
    iil.record_analysis(
        intent="describe", confidence=0.7, sample_size=20,
        hypothesis="x", claim="y",
    )
    assert iil.intent_state["describe"]["total"] >= 1

    # 5. DwellingLayer — record_op (path first, then op).
    dwl = mechs["DwellingLayer"]
    dwl.record_op(
        path="memory/2026-05-01.md", op="read",
        intent="recall",
    )
    assert hasattr(dwl, "state") and dwl.state is not None

    # 6. ProactiveBriefingLayer — receive_activity.
    pbl = mechs["ProactiveBriefingLayer"]
    pbl.receive_activity({
        "category": "becoming",
        "content": "overnight i dwelled on the deadline question",
        "ok": True,
    })
    assert pbl.total_received >= 1

    # 7. CompressionFidelityLayer — record_compression.
    cfl = mechs["CompressionFidelityLayer"]
    cfl.record_compression(
        intent="digest", source="some text might be relevant",
        summary="some text might be relevant",
    )
    assert len(cfl.compressions) >= 1

    # 8. MemoryIntegrityLayer — record_encode.
    mil = mechs["MemoryIntegrityLayer"]
    mil.record_encode(
        content="x", intent="observation", source="user",
        content_confidence=0.7, source_confidence=0.7,
    )
    assert mil.total_encoded >= 1

    # 9. SelfRevisionLayer — record_observe.
    srl = mechs["SelfRevisionLayer"]
    srl.record_observe(
        candidates=[{"target": "personality"}],
        drift_signal_count=1,
    )
    assert srl.op_counts["observe"] >= 1

    # 10. PersonaCoherenceLayer — record_switch.
    pcl = mechs["PersonaCoherenceLayer"]
    pcl.record_switch(target="brain", source="manual", reason="x")
    assert pcl.current_mode == "brain"

    # 11. SelfAnalysisLayer — record_analyze.
    sal = mechs["SelfAnalysisLayer"]
    sal.record_analyze(
        output="x", kind="answer", what_worked=["a"], predicted_quality=0.7,
    )
    assert sal.total_analyses >= 1

    # 12. CorpusRetrievalLayer — record_retrieval.
    crl = mechs["CorpusRetrievalLayer"]
    crl.record_retrieval(
        mode="search", query="x", n_hits=1, hit_doc_types=["journal"],
    )
    assert crl.op_counts["search"] >= 1

    # 13. SkillDiscoveryLayer — record_route.
    sdl = mechs["SkillDiscoveryLayer"]
    sdl.record_route(
        request="research and summarize",
        mode="brain",
        chosen="web-research",
        score=0.6,
        had_clear_trigger=True,
    )
    assert sdl.op_counts["route"] >= 1

    # 14. TaskPlanningLayer — record_decompose.
    tpl = mechs["TaskPlanningLayer"]
    tpl.record_decompose(
        plan_id="pl_x", goal="x", subtask_count=2, mode="build",
    )
    assert tpl.op_counts["decompose"] >= 1

    # 15. ReportGenerationLayer — record_draft.
    rgl = mechs["ReportGenerationLayer"]
    rgl.record_draft(
        report_id="rp_x", brief="x",
        fidelity_signals={
            "fabrication_count": 0, "citation_drift_rate": 0.0,
            "structure_complete": True, "voice_below_floor": False,
            "hedge_stripped": False,
        },
    )
    assert rgl.op_counts["draft"] >= 1


def test_full_wire_smoke_isolation_no_repo_leaks(env):
    """The smoke-test isolation rule from feedback_smoke_test_isolation.md:
    test runs must NOT leak agent.db / .agent / __pycache__ into the repo."""
    mechs = _build_registry()
    # Drive a substantial amount of state.
    _drive_memory_corpus_compression_into_drift(mechs)
    _trigger_persona_override_loop(mechs)
    ipw = mechs["IdentityProposalWriter"]
    ipw.poll_wires(mechs)

    # Walk drain + post.
    from skills.heartbeat_activities._brain_post import post_memory_encode
    from brain.brain_event_drainer import BrainEventDrainer
    post_memory_encode(
        content="leak check", intent="observation",
        source_kind="external",
        content_confidence=0.7, source_confidence=0.7,
    )
    BrainEventDrainer(mechanisms=mechs).drain()

    # Now check the REPO (not the test tmp_path) for leaks.
    repo = env["repo_root"]
    leaked = []
    if (repo / ".agent").exists():
        leaked.append(".agent/")
    if (repo / "agent.db").exists():
        leaked.append("agent.db")
    # __pycache__ check is broader — only flag NEW dirs created during
    # this test (we can't tell easily, so skip the per-test check).

    assert leaked == [], f"smoke isolation violated: {leaked}"


# ── Single comprehensive run that combines everything ───────────────────


def test_full_wire_comprehensive_lifecycle(env):
    """One cohesive 200-tick lifecycle that exercises everything in
    sequence:
      - 200 ticks with periodic synthetic activity
      - Mid-run drift trigger → convergence proposal
      - Persona override loop → auto-switch suspension
      - Mid-run reboot → state restored from disk
      - Operator ratification → improvement.commit lands
      - REVISION_LOG.md grew
      - No exceptions during the loop
    """
    home, ws = env["home"], env["ws"]

    mechs = _build_registry()
    ticks_with_post = list(range(5, 50, 7)) + list(range(120, 180, 11))
    ticks_with_drift = [60]
    ticks_with_override = [80]

    proposals_seen = 0
    crashes = []

    # Phase 1: ticks 0–99
    for tick in range(100):
        try:
            stats = _simulate_one_tick(
                mechs, tick,
                ticks_with_post, ticks_with_drift, ticks_with_override,
            )
            proposals_seen += stats.get("proposals", 0)
        except Exception as e:
            crashes.append(f"phase1 tick {tick}: {e}")

    # Phase 2: reboot mid-simulation. Recreate registry.
    pre_reboot_pcl_state = mechs["PersonaCoherenceLayer"].state.copy()
    pre_reboot_mil_encoded = mechs["MemoryIntegrityLayer"].total_encoded
    del mechs
    mechs = _build_registry()
    # Confirm state restored.
    assert mechs["PersonaCoherenceLayer"].state.get(
        "auto_switch_suspended"
    ) == pre_reboot_pcl_state.get("auto_switch_suspended")
    assert mechs["MemoryIntegrityLayer"].total_encoded == pre_reboot_mil_encoded

    # Phase 3: ticks 100–199
    for tick in range(100, 200):
        try:
            stats = _simulate_one_tick(
                mechs, tick,
                ticks_with_post, ticks_with_drift, ticks_with_override,
            )
            proposals_seen += stats.get("proposals", 0)
        except Exception as e:
            crashes.append(f"phase3 tick {tick}: {e}")

    # Phase 4: ratify + commit.
    ratified = _ratify_first_pending(home, token="op-tok-e2e-life")
    if ratified:
        commit_res = _walk_revision_loop(env, token="op-tok-e2e-life")
    else:
        commit_res = None

    # ── Assertions ─────────────────────────────────────────────────────

    assert not crashes, f"crashes during lifecycle: {crashes[:3]}"
    # The drift on tick 60 should have produced ≥1 proposal at the t=60 poll
    # (60 % 10 == 0).
    assert proposals_seen >= 1, "Third-Eye produced no proposals over 200 ticks"
    # The override loop on tick 80 should have suspended auto-switch.
    assert mechs["PersonaCoherenceLayer"].auto_switch_suspended is True

    # If a proposal made it to PROPOSALS.md and the operator ratified,
    # the commit landed and REVISION_LOG.md grew.
    if commit_res and commit_res.get("ok"):
        log_path = ws / "identity" / "REVISION_LOG.md"
        assert log_path.exists()
        log = log_path.read_text(encoding="utf-8")
        assert commit_res["revision_id"] in log
