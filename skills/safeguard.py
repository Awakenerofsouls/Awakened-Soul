#!/usr/bin/env python3
"""
safeguard.py — Phase 5.5: Destructive action prevention layer

Categories that are free (no confirmation needed):
- Journal/state files: DREAMS.md, MEMORY.md, Dated memory files, logs, state/
- Database reads, LLM calls via router
- Image generation (gated separately via CHILD_SAFETY/REAL_PEOPLE)
- Cron reads, heartbeat activities

Categories that require confirmation:
- Framework file writes: *.py, brain/, skills/, AGENTS.md, SOUL.md, etc.
- Subprocess calls beyond exact whitelist
- Filesystem moves beyond memory/archive/
- File deletions
- Git operations

Loop detection: 3+ blocked attempts on same target → halt for 1 hour
Absolute blocks: git reset --hard, git push --force, rm -rf — never allowed

Usage in activities:
  from skills.safeguard import can_perform
  if not can_perform("subprocess", command_list, "optional detail"):
      return  # Activity halts, the operator notified
"""

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional
import os

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".agent" / "workspace")))
AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
SAFEGUARD_LOG = WORKSPACE / "SAFEGUARD_LOG.md"
SAFEGUARD_STATE = AGENT_HOME / "safeguard_state.json"

# Bridge CLI binary used for outbound messaging (Telegram, etc.). Operators
# wire this up by setting AGENT_BRIDGE_BIN to whatever messaging tool they use.
BRIDGE_BIN = os.getenv("AGENT_BRIDGE_BIN", "agent-bridge")


def _resolve_bridge_bin() -> Optional[Path]:
    """Resolve the bridge binary. Returns None if not available."""
    candidate = Path(BRIDGE_BIN)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    resolved = shutil.which(BRIDGE_BIN)
    return Path(resolved) if resolved else None


# Exact-match whitelist — (first arg, second arg, ...) tuple must match exactly
ALLOWED_COMMANDS = [
    # Emergency channel (drift breach detected)
    ("python3", "skills/proactive_initiation.py", "--emergency"),
    # Scheduled outward reporting
    ("python3", "skills/proactive_initiation.py", "--scheduled"),
    # Read-only crontab inspection
    ("crontab", "-l"),
    # Telegram messaging via the agent bridge CLI
    (BRIDGE_BIN, "message", "send"),
    # Read-only pm2 status check (proactive_initiation loop monitor)
    ("pm2", "show", "agent-loop"),
    # Telegram dispatcher allowed scripts (explicit, matches dispatcher's internal allowlist)
    ("python3", "skills/dream_generator.py"),
    ("python3", "skills/overnight_synthesis.py"),
    ("python3", "skills/memory_consolidation.py"),
    ("python3", "skills/drift_detector.py"),
    ("python3", "skills/phenomenology.py"),
    ("python3", "skills/inner_monologue.py"),
]

# Paths the agent can freely write to — its own state/journal space
JOURNAL_PATHS = [
    "DREAMS.md",
    "MEMORY.md",
    "INTERESTS.md",
    "OVERNIGHT_LOG.md",
    "GUARDIAN_LOG.md",
    "private_entries.md",
    "brain/dream_log.json",
    "brain/monologue_log.json",
    "brain/third_eye_meta_stability.db",
    "brain/preconscious_log.db",
    "brain/attention_modifier_log.db",
    "brain/reality_tension_log.db",
    "brain/meaning_compressor_log.db",
]

JOURNAL_PATTERNS = [
    "memory/",
    "logs/",
    "state/",
]

# Paths that require confirmation (framework files)
PROTECTED_PATHS = [
    "SOUL.md",
    "IDENTITY.md",
    "PERSONALITY.md",
    "USER.md",
    "SELF.md",
    "INNER_VOICE.md",
    "AGENTS.md",
    "HEARTBEAT.md",
    "ARCHITECTURE.md",
    "DECISIONS.md",
    "MEMORY_PROTOCOL.md",
    "DIRECTIVE.md.example",
    "PRESENCE.md",
    "AGENT_VISUAL.md",
    "brain/",
    "skills/",
    "api/",
    "setup.sh",
    "heartbeat.py",
]

# Actions that are never allowed under any autonomous condition
ABSOLUTELY_BLOCKED = [
    "git reset --hard",
    "git push --force",
    "rm -rf",
]

# Loop detection threshold
LOOP_THRESHOLD = 3  # 3 blocks on same target = halt
LOOP_HALT_DURATION = 3600  # 1 hour in seconds


def _log_attempt(action_type: str, target: str, allowed: bool, detail: str = ""):
    """Append to SAFEGUARD_LOG.md — every call, passed or blocked."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    status = "ALLOWED" if allowed else "BLOCKED"
    log_line = f"[{timestamp}] [{status}] {action_type}: {target}"
    if detail:
        log_line += f" | {detail}"
    log_line += "\n"
    SAFEGUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(SAFEGUARD_LOG, "a") as f:
        f.write(log_line)


def _load_state() -> dict:
    if SAFEGUARD_STATE.exists():
        try:
            return json.loads(SAFEGUARD_STATE.read_text())
        except Exception:
            pass
    return {"blocked_counts": {}, "halted_until": None}


def _save_state(state: dict):
    SAFEGUARD_STATE.parent.mkdir(parents=True, exist_ok=True)
    SAFEGUARD_STATE.write_text(json.dumps(state, indent=2))


def _send_telegram(message: str) -> bool:
    """Send alert via the agent-bridge CLI. Returns False if the bridge
    isn't installed, so the framework runs without external messaging."""
    bridge = _resolve_bridge_bin()
    if bridge is None:
        return False
    try:
        result = subprocess.run(
            [str(bridge), "message", "send", "--channel", "telegram", "--message", message],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except Exception:
        return False


def _ask_user(action_type: str, target: str, detail: str = ""):
    """Notify the operator and block the action."""
    msg = f"[SAFEGUARD] the agent wants to: {action_type}\nTarget: {target}"
    if detail:
        msg += f"\nContext: {detail}"
    msg += "\n\nReply 'allow <target>' to permit, 'deny' to block, 'safeguard reset' to clear halt."
    _send_telegram(msg)
    _log_attempt(action_type, target, False, detail + " | operator notified")


def _is_journal_path(path: str) -> bool:
    """Check if path is the agent's own journal/state space."""
    path_clean = str(path).replace(str(WORKSPACE) + "/", "").replace(str(AGENT_HOME) + "/", "")
    for journal in JOURNAL_PATHS:
        if path_clean == journal or path_clean.endswith("/" + journal):
            return True
    for pattern in JOURNAL_PATTERNS:
        if pattern in path_clean:
            return True
    return False


def _is_protected_path(path: str) -> bool:
    """Check if path is framework (requires confirmation)."""
    path_clean = str(path).replace(str(WORKSPACE) + "/", "").replace(str(AGENT_HOME) + "/", "")
    for protected in PROTECTED_PATHS:
        if protected.startswith("*."):
            ext = protected[1:]
            if path_clean.endswith(ext):
                return True
        elif protected.endswith("/"):
            if path_clean.startswith(protected) or protected in path_clean:
                return True
        else:
            if path_clean == protected or path_clean.endswith("/" + protected):
                return True
    return False


def _check_loop_and_update(action_key: str, blocked: bool, state: dict) -> bool:
    """
    Check loop detection. Returns True if action should proceed, False if halted.
    Updates blocked_counts when blocked=True.
    """
    if blocked:
        counts = state.setdefault("blocked_counts", {})
        counts[action_key] = counts.get(action_key, 0) + 1
        if counts[action_key] >= LOOP_THRESHOLD:
            state["halted_until"] = time.time() + LOOP_HALT_DURATION
            _send_telegram(
                f"[SAFEGUARD HALT] the agent blocked {counts[action_key]} times on: {action_key}. "
                f"Safeguard halted for 1 hour. Reply 'safeguard reset' to resume."
            )
            _log_attempt("loop_halt", action_key, False, f"{counts[action_key]} blocks")
        _save_state(state)
        return False
    return True


def can_perform(action_type: str, target: str, detail: str = "") -> bool:
    """
    Returns True if the action is allowed, False if blocked.
    Logs every attempt. On block: notifies the operator, halts on loop.

    action_type: 'subprocess' | 'file_write' | 'file_move' | 'file_delete' | 'git'
    target: the specific command (list/tuple), path (str), or git operation (str)
    detail: optional context string for the log
    """
    state = _load_state()
    action_key = f"{action_type}:{target}"

    # ── Halt check ─────────────────────────────────────────────────
    halted_until = state.get("halted_until")
    if halted_until and time.time() < halted_until:
        _log_attempt(action_type, target, False, "SAFEGUARD HALTED (loop detected)")
        return False

    # ── Absolute blocks ───────────────────────────────────────────
    for blocked_pattern in ABSOLUTELY_BLOCKED:
        if blocked_pattern in str(target):
            _log_attempt(action_type, target, False, "ABSOLUTE_BLOCK")
            _ask_user(action_type, target, f"ABSOLUTE_BLOCK: {blocked_pattern}")
            _check_loop_and_update(action_key, True, state)
            return False

    # ── Subprocess gate ───────────────────────────────────────────
    if action_type == "subprocess":
        if isinstance(target, (list, tuple)):
            # Normalize paths to workspace-relative so whitelist matches absolute or relative paths
            cmd_tuple = tuple(
                str(arg).replace(str(WORKSPACE) + "/", "")
                .replace(str(WORKSPACE) + "\\", "")  # Windows compat
                for arg in target
            )
        else:
            cmd_tuple = tuple(
                part.replace(str(WORKSPACE) + "/", "")
                for part in str(target).split()
            )

        for allowed in ALLOWED_COMMANDS:
            if cmd_tuple[:len(allowed)] == allowed:
                _log_attempt(action_type, target, True, "whitelist match")
                return True

        _log_attempt(action_type, target, False, "subprocess not in whitelist")
        _ask_user(action_type, target, detail)
        _check_loop_and_update(action_key, True, state)
        return False

    # ── File write gate ───────────────────────────────────────────
    elif action_type == "file_write":
        if _is_journal_path(target):
            _log_attempt(action_type, target, True, "journal path")
            return True
        if _is_protected_path(target):
            _log_attempt(action_type, target, False, "protected path")
            _ask_user(action_type, target, detail)
            _check_loop_and_update(action_key, True, state)
            return False
        # Non-journal, non-protected → ask by default (more restrictive)
        _log_attempt(action_type, target, False, "unclassified path — asking")
        _ask_user(action_type, target, detail)
        _check_loop_and_update(action_key, True, state)
        return False

    # ── File move gate ─────────────────────────────────────────────
    elif action_type == "file_move":
        # Allow routine memory archival only
        if "memory/archive" in str(target) or str(target).endswith("/memory/archive"):
            _log_attempt(action_type, target, True, "memory archival")
            return True
        _log_attempt(action_type, target, False, "file_move")
        _ask_user(action_type, target, detail)
        _check_loop_and_update(action_key, True, state)
        return False

    # ── File delete gate ───────────────────────────────────────────
    elif action_type == "file_delete":
        _log_attempt(action_type, target, False, "file_delete")
        _ask_user(action_type, target, detail)
        _check_loop_and_update(action_key, True, state)
        return False

    # ── Git gate ───────────────────────────────────────────────────
    elif action_type == "git":
        _log_attempt(action_type, target, False, "git operation")
        _ask_user(action_type, target, detail)
        _check_loop_and_update(action_key, True, state)
        return False

    # ── Unknown action type ────────────────────────────────────────
    else:
        _log_attempt(action_type, target, False, f"unknown action_type")
        _ask_user(action_type, target, f"unknown action_type: {action_type}")
        _check_loop_and_update(action_key, True, state)
        return False


# ── Wire-aware brain-op gate (Phase 6) ─────────────────────────────────
#
# `can_perform` (above) handles destructive-action prevention — subprocess /
# file_write / file_move / file_delete / git. It does NOT know about brain
# state.
#
# `can_perform_brain_op` is the wire-aware companion. When a skill is
# about to perform a brain-domain operation (memory encode, report
# publish, self-revision commit, persona switch, etc.), it asks the
# matching brain mechanism's `should_block()` first. If the wire is in
# a degraded / sustained-low-integrity state, the op is blocked here
# before it can corrupt mechanism state further.
#
# Per BRAIN_MAP.md Phase 6: this is "one gate, no silent bypasses."
# Skills that don't go through can_perform_brain_op for brain ops will
# still execute — this layer is opt-in. Over time the runtime will
# enforce it.


# Map each op_kind to (mechanism_class_name, adapter_callable). The
# adapter takes (instance, ctx_dict) → (block_bool, reason_str). It
# exists because each wire's should_block has a different signature.
def _adapter_op_first(op):
    """Wires whose should_block is should_block(op, **kwargs)."""
    def _gate(instance, ctx):
        return instance.should_block(op, **(ctx or {}))
    return _gate


def _adapter_outward_reach(instance, ctx):
    ctx = ctx or {}
    return instance.should_block(
        ctx.get("provider", ""), ctx.get("intent", ""),
    )


def _adapter_compression(instance, ctx):
    ctx = ctx or {}
    return instance.should_block(
        ctx.get("intent", ""),
        int(ctx.get("source_len", 0) or 0),
        int(ctx.get("target_len", 0) or 0),
    )


def _adapter_inference(instance, ctx):
    ctx = ctx or {}
    return instance.should_block(
        ctx.get("intent", ""),
        int(ctx.get("sample_size", 0) or 0),
        float(ctx.get("claimed_confidence", 0.0) or 0.0),
    )


def _adapter_making(instance, ctx):
    ctx = ctx or {}
    return instance.should_block(ctx.get("intent", ""))


def _adapter_dwelling(instance, ctx):
    ctx = ctx or {}
    return instance.should_block(
        ctx.get("category", ""),
        ctx.get("intent", ""),
        ctx.get("path", ""),
    )


# Op-kind → (mechanism class name, adapter)
WIRE_GATES: dict = {
    # Memory ops
    "memory.encode":      ("MemoryIntegrityLayer", _adapter_op_first("encode")),
    "memory.retrieve":    ("MemoryIntegrityLayer", _adapter_op_first("retrieve")),
    "memory.consolidate": ("MemoryIntegrityLayer", _adapter_op_first("consolidate")),
    "memory.forget":      ("MemoryIntegrityLayer", _adapter_op_first("forget")),
    "memory.rehearse":    ("MemoryIntegrityLayer", _adapter_op_first("rehearse")),

    # Outward reach (network)
    "outward_reach":      ("OutwardReachLayer", _adapter_outward_reach),

    # Compression
    "compression":        ("CompressionFidelityLayer", _adapter_compression),

    # Inference
    "inference":          ("InferenceIntegrityLayer", _adapter_inference),

    # Making (code execution)
    "making":             ("MakingLayer", _adapter_making),

    # Dwelling (file/path)
    "dwelling":           ("DwellingLayer", _adapter_dwelling),

    # Self-revision
    "self_revision.propose":  ("SelfRevisionLayer", _adapter_op_first("propose")),
    "self_revision.commit":   ("SelfRevisionLayer", _adapter_op_first("commit")),
    "self_revision.rollback": ("SelfRevisionLayer", _adapter_op_first("rollback")),
    "self_revision.reflect":  ("SelfRevisionLayer", _adapter_op_first("reflect")),

    # Persona coherence
    "persona.switch":     ("PersonaCoherenceLayer", _adapter_op_first("switch")),
    "persona.emit":       ("PersonaCoherenceLayer", _adapter_op_first("emit")),
    "persona.detect":     ("PersonaCoherenceLayer", _adapter_op_first("detect")),
    "persona.register":   ("PersonaCoherenceLayer", _adapter_op_first("register")),

    # Self-analysis
    "analysis.analyze":         ("SelfAnalysisLayer", _adapter_op_first("analyze")),
    "analysis.detect_errors":   ("SelfAnalysisLayer", _adapter_op_first("detect_errors")),
    "analysis.suggest":         ("SelfAnalysisLayer", _adapter_op_first("suggest")),
    "analysis.calibrate":       ("SelfAnalysisLayer", _adapter_op_first("calibrate")),
    "analysis.reflect":         ("SelfAnalysisLayer", _adapter_op_first("reflect")),

    # Corpus retrieval
    "corpus.search":            ("CorpusRetrievalLayer", _adapter_op_first("search")),
    "corpus.vsearch":           ("CorpusRetrievalLayer", _adapter_op_first("vsearch")),
    "corpus.hybrid":            ("CorpusRetrievalLayer", _adapter_op_first("hybrid")),
    "corpus.get":               ("CorpusRetrievalLayer", _adapter_op_first("get")),
    "corpus.index":             ("CorpusRetrievalLayer", _adapter_op_first("index")),

    # Skill discovery
    "skill_routing.register":   ("SkillDiscoveryLayer", _adapter_op_first("register")),
    "skill_routing.match":      ("SkillDiscoveryLayer", _adapter_op_first("match")),
    "skill_routing.route":      ("SkillDiscoveryLayer", _adapter_op_first("route")),
    "skill_routing.fallback":   ("SkillDiscoveryLayer", _adapter_op_first("fallback")),
    "skill_routing.reflect":    ("SkillDiscoveryLayer", _adapter_op_first("reflect")),

    # Task planning
    "planning.decompose":       ("TaskPlanningLayer", _adapter_op_first("decompose")),
    "planning.commit":          ("TaskPlanningLayer", _adapter_op_first("commit")),
    "planning.revise":          ("TaskPlanningLayer", _adapter_op_first("revise")),
    "planning.complete":        ("TaskPlanningLayer", _adapter_op_first("complete")),
    "planning.reflect":         ("TaskPlanningLayer", _adapter_op_first("reflect")),

    # Report generation
    "report.draft":             ("ReportGenerationLayer", _adapter_op_first("draft")),
    "report.revise":            ("ReportGenerationLayer", _adapter_op_first("revise")),
    "report.publish":           ("ReportGenerationLayer", _adapter_op_first("publish")),
    "report.retract":           ("ReportGenerationLayer", _adapter_op_first("retract")),
    "report.reflect":           ("ReportGenerationLayer", _adapter_op_first("reflect")),
}


# Per-process cache of ephemeral mechanism instances. Used when caller
# doesn't pass a live `mechanisms` registry. Cleared on reset_safeguard.
_ephemeral_cache: dict = {}


def _get_mechanism_instance(class_name: str, mechanisms=None):
    """Return a live or ephemeral instance of `class_name`. Lazy-imports
    from brain.mechanisms.<snake_case> when needed."""
    if mechanisms and class_name in mechanisms:
        return mechanisms[class_name]
    if class_name in _ephemeral_cache:
        return _ephemeral_cache[class_name]
    # Lazy import.
    import re as _re
    snake = _re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower()
    module_path = f"brain.mechanisms.{snake}"
    try:
        import importlib
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name, None)
        if cls is None:
            return None
        instance = cls()
        _ephemeral_cache[class_name] = instance
        return instance
    except Exception:
        return None


def can_perform_brain_op(
    op_kind: str,
    ctx=None,
    mechanisms=None,
    detail: str = "",
):
    """Wire-aware gate. Returns (allowed_bool, reason_str).

    Looks up the canonical brain mechanism for `op_kind`, calls its
    `should_block(...)` with the appropriate args (built from `ctx`),
    and returns the inverted result.

    Returns (True, "") if no mechanism is registered for op_kind. This
    is graceful degradation — an unmapped op kind doesn't get blocked
    by missing infrastructure.

    Returns (False, reason) if the wire's should_block says block. The
    reason is written to SAFEGUARD_LOG so the operator can audit.

    Args:
        op_kind:     e.g. "memory.encode", "self_revision.commit",
                     "outward_reach", etc. See WIRE_GATES.
        ctx:         dict of kwargs the wire's should_block consumes.
                     E.g. for memory.encode: {"source": "user",
                     "source_confidence": 0.9, ...}
        mechanisms:  optional dict of {class_name: live_instance}. When
                     present, the wire-aware gate dispatches onto the
                     live instance (state changes are visible to the
                     running brain). When absent, an ephemeral instance
                     is used — fine for tests + standalone tooling.
        detail:      free-form text appended to the audit log.
    """
    entry = WIRE_GATES.get(op_kind)
    if entry is None:
        # Unmapped op — graceful pass-through. We log it so the operator
        # can see what's flowing through this gate but it's not a block.
        _log_attempt("brain_op", op_kind, True, f"no wire mapping; pass-through. {detail}")
        return (True, "")

    class_name, adapter = entry
    instance = _get_mechanism_instance(class_name, mechanisms=mechanisms)
    if instance is None:
        # Mechanism not loadable (broken import, missing module). Pass
        # through so the brain-op path doesn't dead-end on infrastructure.
        _log_attempt(
            "brain_op", op_kind, True,
            f"mechanism {class_name} not available; pass-through. {detail}",
        )
        return (True, "")

    try:
        block, reason = adapter(instance, ctx or {})
    except Exception as e:
        _log_attempt(
            "brain_op", op_kind, True,
            f"adapter raised {type(e).__name__}; pass-through. {detail}",
        )
        return (True, "")

    if block:
        full_reason = f"{class_name}.should_block: {reason}"
        _log_attempt("brain_op", op_kind, False, full_reason + (f" | {detail}" if detail else ""))
        return (False, full_reason)
    _log_attempt("brain_op", op_kind, True, detail)
    return (True, "")


def reset_safeguard() -> None:
    """the operator-invoked reset. Clears halt state and blocked_counts."""
    state = {"blocked_counts": {}, "halted_until": None}
    _save_state(state)
    _ephemeral_cache.clear()
    _log_attempt("reset", "safeguard_state", True, "the operator reset safeguard")
    _send_telegram("[SAFEGUARD] Cleared. The agent can proceed.")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(WORKSPACE))

    print("=== SAFEGUARD ISOLATION TESTS ===\n")

    # Test 1: Whitelist allowed (scheduled outward reporting)
    r = can_perform("subprocess", ["python3", "skills/proactive_initiation.py", "--scheduled"], "test scheduled")
    print(f"T1 subprocess scheduled whitelist: {'PASS' if r else 'FAIL'} — {r}")

    # Test 2: Whitelist allowed (emergency)
    r = can_perform("subprocess", ["python3", "skills/proactive_initiation.py", "--emergency"], "test emergency")
    print(f"T2 subprocess emergency whitelist: {'PASS' if r else 'FAIL'} — {r}")

    # Test 3: Not in whitelist — block
    r = can_perform("subprocess", ["python3", "evil.py"], "test blocked")
    print(f"T3 subprocess blocked (not in whitelist): {'PASS' if not r else 'FAIL'} — {r}")

    # Test 4: Journal path — allowed
    r = can_perform("file_write", "DREAMS.md", "test journal")
    print(f"T4 file_write DREAMS.md journal: {'PASS' if r else 'FAIL'} — {r}")

    # Test 5: Protected path — block
    r = can_perform("file_write", "SOUL.md", "test protected")
    print(f"T5 file_write SOUL.md protected: {'PASS' if not r else 'FAIL'} — {r}")

    # Test 6: Protected path — block (brain/)
    r = can_perform("file_write", "brain/registry.py", "test brain write")
    print(f"T6 file_write brain/registry.py protected: {'PASS' if not r else 'FAIL'} — {r}")

    # Test 7: Unclassified path — block (more restrictive)
    r = can_perform("file_write", "/tmp/somefile.txt", "test unclassified")
    print(f"T7 file_write /tmp/somefile.txt unclassified: {'PASS' if not r else 'FAIL'} — {r}")

    # Test 8: Absolute block — git push --force
    r = can_perform("subprocess", ["git", "push", "--force"], "test absolute block")
    print(f"T8 absolute block git push --force: {'PASS' if not r else 'FAIL'} — {r}")

    # Test 9: Absolute block — rm -rf
    r = can_perform("subprocess", ["rm", "-rf", "/"], "test rm block")
    print(f"T9 absolute block rm -rf: {'PASS' if not r else 'FAIL'} — {r}")

    # Test 10: File move memory archival — allowed
    r = can_perform("file_move", "memory/archive/old_file.json", "test archival")
    print(f"T10 file_move memory/archive allowed: {'PASS' if r else 'FAIL'} — {r}")

    # Test 11: File move non-archival — block
    r = can_perform("file_move", "brain/important.py", "test move block")
    print(f"T11 file_move non-archival block: {'PASS' if not r else 'FAIL'} — {r}")

    # Test 12: File delete — block
    r = can_perform("file_delete", "some_file.py", "test delete block")
    print(f"T12 file_delete always blocks: {'PASS' if not r else 'FAIL'} — {r}")

    # Test 13: Git operation — block
    r = can_perform("git", "commit -m 'test'", "test git block")
    print(f"T13 git operation block: {'PASS' if not r else 'FAIL'} — {r}")

    # Test 14: Crontab read-only — allowed
    r = can_perform("subprocess", ["crontab", "-l"], "test crontab")
    print(f"T14 subprocess crontab -l whitelist: {'PASS' if r else 'FAIL'} — {r}")

    # Test 15: Reset safeguard
    reset_safeguard()
    print("T15 reset_safeguard: PASS")

    print("\n=== SAFEGUARD LOG (last 10 entries) ===")
    if SAFEGUARD_LOG.exists():
        lines = SAFEGUARD_LOG.read_text().strip().split("\n")
        for line in lines[-10:]:
            print(line)
    else:
        print("(empty)")

    print("\n=== SAFEGUARD STATE ===")
    state = _load_state()
    print(f"blocked_counts: {state.get('blocked_counts', {})}")
    print(f"halted_until: {state.get('halted_until', None)}")

    print("\n=== ALL TESTS COMPLETE ===")