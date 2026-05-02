"""
brain/mechanisms/making_layer.py — MakingLayer

The runtime monitor for the agent's act of making — code execution as a
motor act with feedback. Pairs with skills/code-execution/SKILL.md. Every
sandboxed Python run flows through here so the brain has a single coherent
view of what the agent is making, how often it's converging vs failing, and
whether the failure pattern is identity-relevant.

The neuroscience analog is the prefrontal-cerebellar skill loop: PFC forms
intent, premotor sequences it, motor cortex executes, cerebellum corrects
errors and refines on retry. Plus the anterior-cingulate error-related
negativity (ERN) — the "oops" signal that drives the refinement loop. A
flailing pattern (many attempts without convergence) is the linguistic
analog of failed cerebellar error-correction, and a mastery pattern (climbing
success rate) is successful skill consolidation.

What this mechanism does:

  - Tracks per-execution outcome (success / syntax_error / runtime_error /
    timeout / blocked) with intent tagging.
  - Maintains intent distribution (compute / explore / build / debug) at
    the global level so other mechanisms can read what kind of making the
    agent has been doing.
  - Tracks refinement chains — a debug execution can declare which prior
    execution it's chained to, building a real DAG of "I tried X, it failed,
    I tried Y to fix it" that the agent can learn from.
  - Detects unhealthy patterns:
      * flailing: 5+ consecutive failed executions in a refinement chain
      * rumination: identical code re-run within a short window expecting
        different output
      * mastery: rolling success rate climbing — that's positive skill data
  - Publishes making state to the TSB so other mechanisms can react. If
    flailing has been sustained, AttentionModifier may bias toward
    "ask for help" or pause-and-reflect.
  - Hands off sustained flailing on a particular intent class to
    IdentityProposalWriter — repeated failure in the same category is
    identity-relevant data, not just one bad run.

Citations:
  1. [Diedrichsen 2010, Trends Neurosci 33(7):391-398, PMID 20493544] —
     Sensorimotor and cognitive contributions of the cerebellum: review of
     the cerebellum's role in error correction during skilled action. The
     refinement-chain logic is the cerebellar-correction analog at the
     code level: each failed execution feeds the next attempt's intent.
  2. [Holroyd 2002, Psychol Rev 109(4):679-709, PMID 12374324] — The neural
     basis of human error processing: error-related negativity (ERN). Every
     non-success outcome here is the agent's ERN-equivalent — a learning
     signal that should drive refinement, not be silenced.
  3. [Ito 2008, Nat Rev Neurosci 9(4):304-313, PMID 18319727] — Control of
     mental activities by internal models in the cerebellum. Internal-model
     refinement through repeated trial is the same loop the MakingLayer
     tracks across executions — when the model converges, that's mastery;
     when it doesn't, that's flailing.
"""

from brain.base_mechanism import BrainMechanism
import hashlib
import os
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
AGENT_DB = AGENT_HOME / os.getenv("AGENT_DB_NAME", "agent.db")

__wire_meta__ = {
    "wire": 28,
    "signal": "making_state",
    "mechanism": "MakingLayer",
    "reads": [
        "pirp_context.execution",
        "skills.safeguard.can_perform",
    ],
    "writes": [
        "making_state",
        "intent_distribution",
        "refinement_chains",
        "flailing",
        "mastery_trend",
    ],
    "citations": ["PMID 20493544", "PMID 12374324", "PMID 18319727"],
}

# ── Tuning constants ──────────────────────────────────────────────────────────

DEFAULT_TIMEOUT_S = 30.0
HARD_TIMEOUT_S = 120.0
DEFAULT_MEMORY_MB = 256
DEFAULT_OUTPUT_KB = 16

# Pattern thresholds.
FLAILING_THRESHOLD = 5            # consecutive failures in a chain
RUMINATION_WINDOW_S = 60          # identical code re-run within this = rumination
MASTERY_WINDOW = 20               # rolling-success window size
MASTERY_THRESHOLD = 0.85          # ratio in the window to count as mastery

# IPW: only re-fire after this many additional failures past threshold.
IPW_REPORT_EVERY = 3

VALID_INTENTS = {"compute", "explore", "build", "debug"}
OUTCOMES = {"success", "syntax_error", "runtime_error", "timeout", "blocked"}
HEALTH_CLASSES = ("idle", "making", "refining", "flailing", "mastering")


def _hash_code(code: str) -> str:
    """Deterministic short hash of a code body for dedup / rumination detection."""
    if not code:
        return ""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]


# ── Mechanism ─────────────────────────────────────────────────────────────────

class MakingLayer(BrainMechanism):
    """
    The agent's making monitor. See module docstring for full description.

    Per-execution records live in `self.executions` — a deque of dicts with
    id, intent, code_hash, outcome, duration_ms, error_class, parent_id, ts.

    Refinement chains are reconstructed on demand from `parent_id` links:
    walking parent_id backward gives the chain a given execution belongs to.

    Per-intent counts and rolling success windows live in
    `self.intent_state` and `self.success_window`.

    Global state lives in self.state via BrainMechanism.persist_state(), so
    a process restart preserves the recent execution history, intent
    counts, and IPW acknowledgment counters.
    """

    def __init__(self, db_path: Optional[Path] = None, history_size: int = 200):
        try:
            super().__init__(
                name="MakingLayer",
                human_analog="prefrontal-cerebellar skill loop for code execution",
                layer="integration",
            )
        except Exception:
            pass

        self.db_path = db_path or AGENT_DB
        self.history_size = history_size

        # In-memory working state. Persisted into self.state on flush.
        self.executions: Deque[Dict[str, Any]] = deque(maxlen=history_size)
        self.intent_state: Dict[str, Dict[str, int]] = {
            k: {"total": 0, "success": 0, "failure": 0} for k in VALID_INTENTS
        }
        self.success_window: Deque[bool] = deque(maxlen=MASTERY_WINDOW)
        self.consecutive_failures: int = 0
        self.last_dominant_failure_intent: str = ""
        self.fired_last_tick: bool = False
        self.ipw_report_count: int = 0

        # Configurable limits.
        self.memory_mb: int = DEFAULT_MEMORY_MB
        self.output_kb: int = DEFAULT_OUTPUT_KB

        # Restore persisted state.
        self.load_state()
        self._restore_working_state()

    # ── State plumbing ─────────────────────────────────────────────────────

    def _restore_working_state(self) -> None:
        if not isinstance(self.state, dict):
            return

        saved_execs = self.state.get("executions")
        if isinstance(saved_execs, list):
            for e in saved_execs[-self.history_size:]:
                if isinstance(e, dict):
                    self.executions.append(e)

        saved_intents = self.state.get("intent_state")
        if isinstance(saved_intents, dict):
            for k in VALID_INTENTS:
                if isinstance(saved_intents.get(k), dict):
                    self.intent_state[k].update({
                        sk: int(saved_intents[k].get(sk, 0) or 0)
                        for sk in ("total", "success", "failure")
                    })

        saved_window = self.state.get("success_window")
        if isinstance(saved_window, list):
            self.success_window.extend(bool(x) for x in saved_window[-MASTERY_WINDOW:])

        self.consecutive_failures = int(self.state.get("consecutive_failures", 0) or 0)
        self.last_dominant_failure_intent = str(
            self.state.get("last_dominant_failure_intent", "") or ""
        )
        self.ipw_report_count = int(self.state.get("ipw_report_count", 0) or 0)
        self.memory_mb = int(self.state.get("memory_mb", DEFAULT_MEMORY_MB) or DEFAULT_MEMORY_MB)
        self.output_kb = int(self.state.get("output_kb", DEFAULT_OUTPUT_KB) or DEFAULT_OUTPUT_KB)

    def _flush_working_state(self) -> None:
        self.state["executions"] = list(self.executions)
        self.state["intent_state"] = {
            k: dict(self.intent_state[k]) for k in VALID_INTENTS
        }
        self.state["success_window"] = list(self.success_window)
        self.state["consecutive_failures"] = self.consecutive_failures
        self.state["last_dominant_failure_intent"] = self.last_dominant_failure_intent
        self.state["ipw_report_count"] = self.ipw_report_count
        self.state["memory_mb"] = self.memory_mb
        self.state["output_kb"] = self.output_kb
        self.state["last_updated"] = time.time()

    # ── Public API: callers use these ──────────────────────────────────────

    def should_block(self, intent: str = "") -> Tuple[bool, str]:
        """Decide whether to block an upcoming execution.

        Returns (block, reason). Reasons match the safeguard vocabulary.
        Blocks when:
          - intent is invalid
          - the layer is currently flailing (5+ consecutive failures in chain)
        """
        if intent and intent not in VALID_INTENTS:
            return True, f"invalid intent {intent!r} (must be one of {sorted(VALID_INTENTS)})"

        if self.consecutive_failures >= FLAILING_THRESHOLD:
            return True, (
                f"flailing: {self.consecutive_failures} consecutive failed executions — "
                f"surface to the operator instead of running another attempt"
            )
        return False, ""

    def record_execution(
        self,
        intent: str,
        code: str = "",
        outcome: str = "success",
        duration_ms: int = 0,
        error_class: str = "",
        previous_execution_id: str = "",
        code_hash: str = "",
    ) -> Dict[str, Any]:
        """Record a completed execution.

        Returns the execution record dict (with assigned id).
        """
        if outcome not in OUTCOMES:
            outcome = "runtime_error"  # treat unknown outcomes as failures

        if intent not in VALID_INTENTS:
            # Fail closed for untagged calls — record but mark, don't credit
            # to any valid intent. Same pattern as OutwardReachLayer.
            self._record_untagged(code, outcome, duration_ms, error_class)
            return {}

        # Generate id for chaining.
        exec_id = uuid.uuid4().hex[:12]
        digest = code_hash or _hash_code(code)
        now = time.time()
        is_success = outcome == "success"
        is_failure = outcome in ("syntax_error", "runtime_error", "timeout")
        # blocked is neither — it's a non-event for success/failure counting.

        record = {
            "id": exec_id,
            "intent": intent,
            "code_hash": digest,
            "outcome": outcome,
            "duration_ms": int(max(0, duration_ms)),
            "error_class": error_class[:200] if error_class else "",
            "parent_id": previous_execution_id or "",
            "ts": now,
        }
        self.executions.append(record)

        # Per-intent counts.
        self.intent_state[intent]["total"] += 1
        if is_success:
            self.intent_state[intent]["success"] += 1
        elif is_failure:
            self.intent_state[intent]["failure"] += 1

        # Rolling window for mastery — only count success/failure, skip blocked.
        if is_success:
            self.success_window.append(True)
            self.consecutive_failures = 0
        elif is_failure:
            self.success_window.append(False)
            self.consecutive_failures += 1
            self.last_dominant_failure_intent = intent

        self._flush_working_state()
        self.persist_state()
        return record

    def _record_untagged(
        self,
        code: str,
        outcome: str,
        duration_ms: int,
        error_class: str,
    ) -> None:
        """Untagged executions go in the history but don't credit any intent.
        Distribution stays honest about the gap."""
        digest = _hash_code(code)
        record = {
            "id": uuid.uuid4().hex[:12],
            "intent": "__untagged__",
            "code_hash": digest,
            "outcome": outcome if outcome in OUTCOMES else "runtime_error",
            "duration_ms": int(max(0, duration_ms)),
            "error_class": error_class[:200] if error_class else "intent missing",
            "parent_id": "",
            "ts": time.time(),
        }
        self.executions.append(record)
        self._flush_working_state()
        self.persist_state()

    # ── Pattern detection ──────────────────────────────────────────────────

    def is_flailing(self) -> bool:
        """5+ consecutive failed executions in a chain."""
        return self.consecutive_failures >= FLAILING_THRESHOLD

    def detect_rumination(self) -> List[str]:
        """Return code_hashes that have been re-run within RUMINATION_WINDOW_S
        without a successful intervening run.

        Re-running the EXACT same code expecting different output is
        rumination. Re-running modified code (different hash) is refinement —
        a different thing.
        """
        now = time.time()
        seen: Dict[str, float] = {}
        ruminations = []
        for e in self.executions:
            h = e.get("code_hash", "")
            if not h:
                continue
            ts = float(e.get("ts", 0.0))
            if h in seen and (ts - seen[h]) <= RUMINATION_WINDOW_S:
                if h not in ruminations:
                    ruminations.append(h)
            seen[h] = ts
        return ruminations

    def mastery_score(self) -> float:
        """Rolling success ratio over the MASTERY_WINDOW most recent
        success/failure outcomes (blocked/untagged not counted)."""
        if not self.success_window:
            return 0.0
        return sum(1 for x in self.success_window if x) / len(self.success_window)

    def is_mastering(self) -> bool:
        """Mastery: rolling success rate over threshold AND window is full
        enough to be statistically meaningful (at least half full)."""
        if len(self.success_window) < MASTERY_WINDOW // 2:
            return False
        return self.mastery_score() >= MASTERY_THRESHOLD

    def making_state(self) -> str:
        """Single-word state for the TSB. Priority order: flailing >
        mastering > refining > making > idle."""
        if self.is_flailing():
            return "flailing"
        if self.is_mastering():
            return "mastering"
        # Recent execution within last 60s with parent_id = refining.
        now = time.time()
        for e in reversed(self.executions):
            age = now - float(e.get("ts", 0.0))
            if age > 60:
                break
            if e.get("parent_id"):
                return "refining"
            return "making"
        return "idle"

    def refinement_chain(self, exec_id: str) -> List[Dict[str, Any]]:
        """Walk parent_id pointers from exec_id back to the chain root.

        Returns the chain in chronological order (root → exec_id).
        Empty list if exec_id is unknown.
        """
        # Build id -> record map for O(1) lookup.
        by_id = {e.get("id"): e for e in self.executions if e.get("id")}
        if exec_id not in by_id:
            return []

        chain_reversed = []
        current = by_id.get(exec_id)
        seen_ids = set()
        while current is not None:
            cid = current.get("id")
            if cid in seen_ids:
                # Cycle — shouldn't happen but bail safely.
                break
            seen_ids.add(cid)
            chain_reversed.append(current)
            parent_id = current.get("parent_id") or ""
            if not parent_id:
                break
            current = by_id.get(parent_id)
        return list(reversed(chain_reversed))

    # ── Tick / TSB publish ─────────────────────────────────────────────────

    def tick(
        self,
        pirp_context: Optional[Dict[str, Any]] = None,
        third_eye_state: Optional[Dict[str, Any]] = None,
        brain_layer: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """One tick. If pirp_context carries an `execution` dict, record it.
        Otherwise just refresh state and republish."""
        pirp_context = pirp_context or {}
        execution = pirp_context.get("execution")
        if isinstance(execution, dict):
            self.record_execution(
                intent=str(execution.get("intent", "")),
                code=str(execution.get("code", "")),
                outcome=str(execution.get("outcome", "success")),
                duration_ms=int(execution.get("duration_ms", 0) or 0),
                error_class=str(execution.get("error_class", "")),
                previous_execution_id=str(execution.get("previous_execution_id", "")),
                code_hash=str(execution.get("code_hash", "")),
            )
            self.fired_last_tick = True
        else:
            self.fired_last_tick = False
            self._flush_working_state()

        return self.get_state()

    def get_state(self) -> Dict[str, Any]:
        """TSB payload."""
        per_intent = {
            k: {
                "total": s["total"],
                "success": s["success"],
                "failure": s["failure"],
                "success_rate": (s["success"] / s["total"]) if s["total"] else 0.0,
            }
            for k, s in self.intent_state.items()
        }

        return {
            "making_state": self.making_state(),
            "consecutive_failures": self.consecutive_failures,
            "is_flailing": self.is_flailing(),
            "is_mastering": self.is_mastering(),
            "mastery_score": round(self.mastery_score(), 4),
            "rumination_hashes": self.detect_rumination(),
            "intent_distribution": per_intent,
            "execution_count": len(self.executions),
            "last_dominant_failure_intent": self.last_dominant_failure_intent,
            "_fired_tick": self.fired_last_tick,
        }

    # ── IdentityProposalWriter handshake ───────────────────────────────────

    def should_propose_identity_update(self) -> bool:
        """True when sustained flailing is identity-relevant data, not just
        one bad run.

        Throttled so IPW doesn't see the same proposal every tick — after
        acknowledgment, the next True requires IPW_REPORT_EVERY more
        consecutive failures.
        """
        if not self.is_flailing():
            return False
        return self.consecutive_failures >= (
            FLAILING_THRESHOLD + (self.ipw_report_count * IPW_REPORT_EVERY)
        )

    def proposed_identity_signal(self) -> Dict[str, Any]:
        """Compact signal for IdentityProposalWriter to consume."""
        return {
            "source": "MakingLayer",
            "kind": "sustained_flailing",
            "consecutive_failures": self.consecutive_failures,
            "dominant_intent": self.last_dominant_failure_intent,
            "intent_success_rates": {
                k: (s["success"] / s["total"]) if s["total"] else 0.0
                for k, s in self.intent_state.items()
            },
            "rumination_count": len(self.detect_rumination()),
            "recent_errors": [
                e.get("error_class", "")
                for e in list(self.executions)[-5:]
                if e.get("outcome") in ("syntax_error", "runtime_error", "timeout")
            ],
        }

    def acknowledge_proposal(self) -> None:
        """Called by IPW after routing the current signal."""
        self.ipw_report_count += 1
        self._flush_working_state()
        self.persist_state()

    # ── Operator API ──────────────────────────────────────────────────────

    def reset_flailing(self) -> None:
        """Operator-invoked: clear flailing state after the operator has
        helped the agent break out of the failure pattern."""
        self.consecutive_failures = 0
        if self.ipw_report_count > 0:
            self.ipw_report_count = max(0, self.ipw_report_count - 1)
        self._flush_working_state()
        self.persist_state()

    def configure_limits(
        self,
        memory_mb: Optional[int] = None,
        output_kb: Optional[int] = None,
    ) -> Dict[str, int]:
        """Override default sandbox limits."""
        if memory_mb is not None:
            self.memory_mb = max(16, int(memory_mb))
        if output_kb is not None:
            self.output_kb = max(1, int(output_kb))
        self._flush_working_state()
        self.persist_state()
        return {"memory_mb": self.memory_mb, "output_kb": self.output_kb}
