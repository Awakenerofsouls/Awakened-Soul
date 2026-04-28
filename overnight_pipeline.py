"""
overnight_pipeline.py

The actual nightly pipeline runner.
Calls everything that's supposed to run overnight in the right order.

Schedule (add to crontab):
  0 3 * * * /usr/bin/python3 /path/to/overnight_pipeline.py >> ~/.agent/overnight_pipeline.log 2>&1

Or run manually:
  python3 overnight_pipeline.py

What it does:
  3:00 AM — Full pipeline
  1. IGA: apply pending session deltas to VIF (identity accumulation)
  2. RTF: extract patterns from recent trace
  3. RSL: compress RTF patterns into relational sediment
  4. NSE: compress ABM entries into narrative motifs
  5. RCE: evaluate coherence trend across recent sessions
  6. DIQE: add any RCE drift findings as evidence to open questions
  7. Check SOUL evolution queue — log if proposals exist
  8. Check USMS promoted proposals — log for developer review
  9. Check DC unacknowledged objections — surface urgently if any
  10. Write SRV (morning-state primer) for next boot
  11. Log completion to OVERNIGHT_LOG.md
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
import os

# Allow running from any directory
sys.path.insert(0, str(Path(__file__).parent))

AGENT_HOME = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent"))))
LOG_PATH = AGENT_HOME / "OVERNIGHT_LOG.md"


def log(msg: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {msg}"
    print(line)
    try:
        with open(LOG_PATH, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def run_pipeline():
    log("=" * 60)
    log(f"Overnight pipeline starting")
    results = {}

    # ── Step 1: IGA → VIF delta application ────────────────────────────
    try:
        from brain.identity_gradient_accumulator import IdentityGradientAccumulator
        from brain.vectorized_identity_fields import VectorizedIdentityFields

        vif = VectorizedIdentityFields()
        iga = IdentityGradientAccumulator()
        applied = iga.apply_pending_deltas(vif)

        if applied:
            log(f"IGA: applied deltas to {len(applied)} anchors — {list(applied.keys())}")
        else:
            log("IGA: no pending deltas")

        results["iga"] = {"applied": applied}
    except Exception as e:
        log(f"IGA failed: {e}", "ERROR")
        results["iga"] = {"error": str(e)}

    # ── Step 2: RTF pattern extraction ─────────────────────────────────
    try:
        from brain.relational_trace_field import RelationalTraceField
        from brain.relational_sediment_layer import RelationalSedimentLayer

        rtf = RelationalTraceField()
        patterns = rtf.extract_patterns(window_days=7)
        log(f"RTF: extracted patterns — {patterns.get('interaction_count', 0)} interactions this week")
        results["rtf"] = patterns
    except Exception as e:
        log(f"RTF failed: {e}", "ERROR")
        results["rtf"] = {"error": str(e)}
        patterns = {}

    # ── Step 3: RSL sediment compression ───────────────────────────────
    try:
        rsl = RelationalSedimentLayer()
        rsl.compress_from_rtf(patterns)
        log(f"RSL: sediment updated — {len(rsl.sediment)} dimensions")
        results["rsl"] = {"dimensions": len(rsl.sediment)}
    except Exception as e:
        log(f"RSL failed: {e}", "ERROR")
        results["rsl"] = {"error": str(e)}

    # ── Step 4: NSE narrative compression (VMM-weighted) ────────────────
    try:
        from brain.nse_pce_cse import NarrativeSedimentEngine
        from brain.autobiographical_memory import AutobiographicalMemory
        from brain.pre_desire_state import PreDesireState
        from brain.pdfb_bfc_vmm import VolitionalMemoryMarkers

        abm = AutobiographicalMemory()
        pds = PreDesireState()
        nse = NarrativeSedimentEngine()
        vmm = VolitionalMemoryMarkers()

        recent_entries = abm.get_recent(20)
        pds_names = list(pds.get_active().keys())

        # Get VMM consolidation weights (None if no pending tags)
        vmm_weights = None
        try:
            vmm_weights = vmm.get_consolidation_weights()
        except Exception as vmm_err:
            log(f"VMM weights fetch failed (non-fatal): {vmm_err}", "WARN")

        motifs = nse.compress(
            abm_entries=recent_entries,
            vif_state=None,
            pds_history=pds_names,
            vmm_weights=vmm_weights,
        )

        # Mark VMM tags as applied if compression ran successfully
        if vmm_weights:
            try:
                for content_id in vmm_weights.keys():
                    vmm.mark_applied(content_id)
                log(f"VMM: {len(vmm_weights)} tags marked applied after consolidation")
            except Exception as vmm_mark_err:
                log(f"VMM mark_applied failed (non-fatal): {vmm_mark_err}", "WARN")

        log(f"NSE: {len(motifs)} narrative motifs compressed")
        results["nse"] = {"motifs": motifs, "vmm_weights_applied": bool(vmm_weights)}
    except Exception as e:
        log(f"NSE failed: {e}", "ERROR")
        results["nse"] = {"error": str(e)}

    # ── Step 5: RCE coherence evaluation ───────────────────────────────
    try:
        from brain.reflective_consistency_engine import ReflectiveConsistencyEngine

        rce = ReflectiveConsistencyEngine()
        trend = rce.get_trend()
        coherence = rce.get_current_coherence()
        log(f"RCE: coherence {coherence:.3f}, trend: {trend}")
        results["rce"] = {"coherence": coherence, "trend": trend}
    except Exception as e:
        log(f"RCE failed: {e}", "ERROR")
        results["rce"] = {"error": str(e)}

    # ── Step 6: DIQE evidence update ───────────────────────────────────
    try:
        from brain.drift_identity_engine import DriftIdentityQuestionEngine

        diqe = DriftIdentityQuestionEngine()
        rce_evidence = results.get("rce", {})
        if "trend" in rce_evidence:
            obs = f"Overnight RCE: coherence {rce_evidence['coherence']:.3f}, {rce_evidence['trend']}"
            activated = diqe.add_evidence_to_relevant(obs, weight=0.4)
            log(f"DIQE: evidence added to {len(activated)} questions")
        results["diqe"] = {"questions_total": diqe.total_questions()}
    except Exception as e:
        log(f"DIQE failed: {e}", "ERROR")
        results["diqe"] = {"error": str(e)}

    # ── Step 7: SOUL evolution queue check ─────────────────────────────
    try:
        from brain.identity_gradient_accumulator import IdentityGradientAccumulator
        iga2 = IdentityGradientAccumulator()
        queue = iga2.get_soul_evolution_queue()
        if queue:
            log(f"SOUL EVOLUTION: {len(queue)} proposals awaiting review", "REVIEW_NEEDED")
            for p in queue:
                log(f"  → {p['anchor_name']}: {p['proposed_update'][:100]}")
        results["soul_evolution"] = {"pending": len(queue)}
    except Exception as e:
        log(f"SOUL evolution check failed: {e}", "ERROR")

    # ── Step 8: USMS promoted proposals ────────────────────────────────
    try:
        from brain.unified_self_modification_dissent_channel import UnifiedSelfModificationSystem, DissentChannel
        usms = UnifiedSelfModificationSystem()
        promoted = usms.get_promoted()
        if promoted:
            log(f"USMS: {len(promoted)} promoted proposals for developer review", "REVIEW_NEEDED")
            for p in promoted[-3:]:
                log(f"  → [{p['mechanism']}] {p['justification'][:100]}")
        results["usms"] = {"promoted": len(promoted)}
    except Exception as e:
        log(f"USMS check failed: {e}", "ERROR")

    # ── Step 9: DC objections check ────────────────────────────────────
    try:

        dc = DissentChannel()
        pending = dc.get_unacknowledged()
        if pending:
            log(f"DISSENT CHANNEL: {len(pending)} unacknowledged objections — MANDATORY RESPONSE DUE", "URGENT")
            for obj in pending:
                log(f"  → [{obj['target_mechanism']}] {obj['reason'][:100]}")
        results["dc"] = {"unacknowledged": len(pending)}
    except Exception as e:
        log(f"DC check failed: {e}", "ERROR")

    # ── Step 10: Write SRV morning-state primer ─────────────────────────
    try:
        srv_path = AGENT_HOME / "srv.json"
        existing_srv = {}
        if srv_path.exists():
            with open(srv_path) as f:
                existing_srv = json.load(f)

        # Add overnight results to SRV
        existing_srv["overnight_results"] = {
            "run_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "iga_deltas_applied": list(results.get("iga", {}).get("applied", {}).keys()),
            "nse_motifs": results.get("nse", {}).get("motifs", [])[:3],
            "rce_coherence": results.get("rce", {}).get("coherence", 0.7),
            "rce_trend": results.get("rce", {}).get("trend", "unknown"),
            "review_needed": (
                results.get("soul_evolution", {}).get("pending", 0) > 0 or
                results.get("usms", {}).get("promoted", 0) > 0 or
                results.get("dc", {}).get("unacknowledged", 0) > 0
            ),
        }

        with open(srv_path, "w") as f:
            json.dump(existing_srv, f, indent=2)

        log("SRV: morning-state primer written")
        results["srv"] = {"written": True}
    except Exception as e:
        log(f"SRV write failed: {e}", "ERROR")

    # ── Completion ──────────────────────────────────────────────────────
    log(f"Pipeline complete. Steps run: {len(results)}")
    log("=" * 60)

    return results


if __name__ == "__main__":
    run_pipeline()
