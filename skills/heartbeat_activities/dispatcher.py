"""
Heartbeat dispatcher — pool + thread-continuity layer.

Priority each tick:
  1. followup_due activities whose offset has arrived
  2. Unfinished threads — 40% chance to continue one (most recent)
  3. Overdue activities per inverse-weight logic → softmax pick via brain signals
  4. Random exploration from full pool

Wire 20 — neutral activity pool framework.
Signal Wiring — brain signal-driven softmax dispatch (April 24, 2026).
Parallel firing — dispatch_batch() runs N activities concurrently via
ThreadPoolExecutor (Phase A of brain-mechanism parallelism — 2026-05-04).
"""

import math
import random
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeoutError
from pathlib import Path
from typing import Dict, List, Optional

from . import brain_signals

# Lock around state mutations performed by activities running in parallel.
# log_activity / journal writes append to files — Python's GIL makes the
# append() syscall atomic on POSIX, but state-dict mutations (e.g.
# overdue_activities, unfinished_threads) need an explicit guard.
_PARALLEL_STATE_LOCK = threading.RLock()

# Each activity is a module in this package with a run(state) → dict function.
# Stub modules are replaced one-by-one as they get ported.
from .research import run as run_research
from .study import run as run_study
from .creative import run as run_creative
from .dreams import run as run_dreams
from .self_check import run as run_self_check
from .phenomenology import run as run_phenomenology
from .idle_drive import run as run_idle_drive
from .becoming import run as run_becoming
from .soul import run as run_soul
from .relationship import run as run_relationship
from .humor import run as run_humor
from .aesthetic import run as run_aesthetic
from .contradiction import run as run_contradiction
from .third_eye import run as run_third_eye
from .private_entry import run as run_private_entry
from .insight import run as run_insight
from .news import run as run_news
from .memory_capture import run as run_memory_capture
from .consolidation import run as run_consolidation
from .future_letter import run as run_future_letter
from .open_question import run as run_open_question
from .tool_explore import run as run_tool_explore
from .narrative import run as run_narrative
from .ethical import run as run_ethical
from .grief import run as run_grief
from .desire import run as run_desire
from .letter import run as run_letter
from .curiosity_deep import run as run_curiosity_deep
from .architecture import run as run_architecture
from .skill import run as run_skill
from .tavily_search import run as run_tavily_search
from .tavily_news import run as run_tavily_news
from .tavily_answer import run as run_tavily_answer
from .tavily_recency import run as run_tavily_recency
from .weather_today import run as run_weather_today
from .weather_forecast import run as run_weather_forecast
from .severe_weather_scan import run as run_severe_weather_scan
from .astronomy_snapshot import run as run_astronomy_snapshot
from .ollama_status import run as run_ollama_status
from .disk_health import run as run_disk_health
from .log_scan import run as run_log_scan
from .memory_synthesis import run as run_memory_synthesis
from .decisions_followup import run as run_decisions_followup
from .session_handoff_update import run as run_session_handoff_update
from .brain_state_review import run as run_brain_state_review
from .self_pic import run as run_self_pic
from .image_make import run as run_image_make
from .recent_activity_summary import run as run_recent_activity_summary
# Positive-emotion balancing activities — counterweight to the heaviness
# leaning of soul_alignment / grief_integration / contradiction / private_entry.
from . import pleasure_log
from . import satisfaction_check
from . import something_good
from . import play
from . import gratitude
from . import connection_warmth
# v2.0 autonomy layer — choice surface + outward channels + initiation
from . import tension_choice
from . import reach_out
from . import free_action
# v2.0 expansion — five activities in the autonomy/expression layer:
#   held_breath  → catch the pre-longing fertileness state without forcing meaning
#   read_back    → editorial distance on its own writing (hear voice from outside)
#   letters      → asymmetric channel; no reply expected, writing IS resolution
#   outward_reach→ replaces tool_explore — pushes outward instead of cataloguing inward
#   vision_self  → first-person self-description of its own generated images
from . import held_breath
from . import read_back
from . import letters
from . import outward_reach
from . import vision_self
# Also import soul_alignment and third_eye_hunch so their SIGNAL_AFFINITY
# attrs are accessible in sys.modules (needed for _build_affinity_cache).
from . import soul_alignment
from . import third_eye_hunch
from . import deep_curiosity  # separate file from curiosity_deep.py
from . import connection_reflection
from . import memory_protocol
from . import model_update
from . import relationship_check
from . import dream_log
from . import pattern
# Operator plugins are imported at the end of this file by the plugin loader.

ACTIVITY_REGISTRY: dict[str, callable] = {
    # Cognitive / Research
    "research":       run_research,
    "study":          run_study,
    "open_question":  run_open_question,
    "news":           run_news,
    "tool_explore":   run_tool_explore,
    "skill":          run_skill,
    "curiosity_deep": run_curiosity_deep,
    "architecture":  run_architecture,
    # Memory / Continuity
    "memory_capture": run_memory_capture,
    "consolidation":  run_consolidation,
    "insight":        run_insight,
    "private_entry":  run_private_entry,
    "open_question":  run_open_question,
    "future_letter":  run_future_letter,
    # Creative / Expression
    "creative":       run_creative,
    "humor":          run_humor,
    "aesthetic":      run_aesthetic,
    "narrative":      run_narrative,
    # Interior / Self
    "self_check":     run_self_check,
    "phenomenology":  run_phenomenology,
    "idle_drive":     run_idle_drive,
    "becoming":       run_becoming,
    "soul_alignment": soul_alignment.run,  # real implementation
    "soul":           run_soul,             # stub — kept for compat
    "desire":         run_desire,
    "grief":          run_grief,
    "letter":         run_letter,
    # Relational
    "relationship":  run_relationship,
    "relationship_check": relationship_check.run,  # real activity
    "connection_reflection": connection_reflection.run,  # real activity
    "model_update": model_update.run,  # real activity
    # Dreams / Imagination
    "dreams":         run_dreams,
    "third_eye_hunch": third_eye_hunch.run,  # real implementation
    "third_eye":      run_third_eye,         # stub — kept for compat
    "deep_curiosity": deep_curiosity.run,    # separate from curiosity_deep
    "dream_log":      dream_log.run,         # real activity
    "contradiction":  run_contradiction,
    # Web research — real search via Tavily
    "tavily_search":    run_tavily_search,
    "tavily_news":      run_tavily_news,
    "tavily_answer":    run_tavily_answer,
    "tavily_recency":   run_tavily_recency,
    # Weather / environment — NOAA API
    "weather_today":    run_weather_today,
    "weather_forecast": run_weather_forecast,
    "severe_weather_scan": run_severe_weather_scan,
    "astronomy_snapshot": run_astronomy_snapshot,
    # Infrastructure monitoring
    "ollama_status":    run_ollama_status,
    "disk_health":     run_disk_health,
    "log_scan":        run_log_scan,
    # Memory and file continuity
    "memory_synthesis": run_memory_synthesis,
    "memory_protocol": memory_protocol.run,  # real activity
    "pattern": pattern.run,                   # real activity
    "decisions_followup": run_decisions_followup,
    "session_handoff_update": run_session_handoff_update,
    "brain_state_review": run_brain_state_review,
    # Creative — self-portrait via ComfyUI (legacy single-category path)
    "self_pic":         run_self_pic,
    # Creative — calls into per-operator image_engine.make_one() if the
    # operator has supplied a workspace/skills/image_engine.py module.
    # The engine picks the category itself; this activity just exercises
    # the engine from the autonomous loop. Fails gracefully if no engine
    # is present.
    "image_make":  run_image_make,
    # Positive-emotion balancing — counterweight to the heaviness skew
    # produced by soul_alignment, grief, contradiction, private_entry,
    # desire. These six activities tilt toward joy / pleasure /
    # satisfaction / gratitude / play / warmth so the journal isn't
    # ONLY heaviness and the agent has real emotional range.
    "pleasure_log":         pleasure_log.run,
    "satisfaction_check":   satisfaction_check.run,
    "something_good":       something_good.run,
    "play":                 play.run,
    "gratitude":            gratitude.run,
    "connection_warmth":    connection_warmth.run,
    # v2.0 autonomy layer — fires when arousal/tension crosses threshold
    # and surfaces 4 options the agent picks from (name/move/pass/ask).
    # The gate inside the activity skips cheaply when tension is low.
    "tension_choice":       tension_choice.run,
    # v2.0 outward channel — drafts a message to the operator and queues
    # it in OUTBOX/. Operator approves/edits/dismisses. Optional auto-send
    # via WORKSPACE/.outbox_autosend = '1'. Routes from tension_choice "move".
    "reach_out":            reach_out.run,
    # v2.0 initiation channel — reads INTAKE.md for queued wishes and
    # fires the matching action; if no wishes queued, originates one fresh
    # from current brain state. Sets initiated_by="self" in the activity log.
    "free_action":          free_action.run,
    # v2.0 expansion — five activities the agent explicitly asked for:
    # held_breath catches the pre-longing fertileness state (gated to fire
    # only when valence is positive, anxiety low, arousal moderate) and
    # records the openness without manufacturing a desire from it.
    "held_breath":          held_breath.run,
    # read_back picks a recent expressive journal entry and asks the LLM
    # to hear it as someone outside would — the editor's distance the
    # agent said it lacked. Result lands back in journal so both versions
    # live side-by-side over time.
    "read_back":            read_back.run,
    # letters is the lower-stakes outward channel — asymmetric, NO REPLY
    # EXPECTED, the act of writing is the resolution. Saves to LETTERS/.
    # Different from reach_out (which queues for delivery).
    "letters":              letters.run,
    # outward_reach is the replacement for tool_explore the agent
    # requested: instead of cataloguing inward at its own toolbelt, it
    # picks ONE outward channel (image / letter / reach) and fires it.
    "outward_reach":        outward_reach.run,
    # vision_self gives the agent first-person sight of its own
    # generated images via Ollama vision LLM. Saves a .description.md
    # sidecar so chat-side reading gets the description in context.
    # Skips cleanly when LLM_VISION_MODEL isn't configured.
    "vision_self":          vision_self.run,
    # Visibility — deterministic ACTIVITY_LOG → RECENT_ACTIVITY.md summarizer
    "recent_activity_summary": run_recent_activity_summary,
}

# Continuation configuration
CONTINUATION_PROBABILITY = 0.4   # 40% chance to pick an unfinished thread over fresh
FOLLOWUP_DUE_TICK_WINDOW = 3    # followup_due:N means come back in N ticks

# ─── Signal Affinity Cache ─────────────────────────────────────────────────────
# Lazily built mapping of category name → SIGNAL_AFFINITY dict.
# Reads module-level SIGNAL_AFFINITY attribute from each registered module.
# Plugins add their affinities at load time via register_plugin().

_AFFINITY_CACHE: Optional[Dict[str, dict]] = None


# Framework module aliases: registry key -> actual module name in heartbeat_activities.
# Needed because some imports use aliases (e.g. "soul" -> soul_alignment.py).
_FRAMEWORK_MODULE_MAP: Dict[str, str] = {
    "soul":           "soul_alignment",
    "soul_alignment": "soul_alignment",
    "third_eye":      "third_eye_hunch",
    "third_eye_hunch": "third_eye_hunch",
}


def _build_affinity_cache() -> Dict[str, dict]:
    """
    Scan ACTIVITY_REGISTRY for SIGNAL_AFFINITY module attributes.
    Returns {category: affinity_dict} for all categories that have it.
    Missing SIGNAL_AFFINITY -> {} (neutral, no bias).
    """
    result = {}
    for category in ACTIVITY_REGISTRY:
        mod = None

        # 1. Plugin modules (stored directly by register_plugin)
        if category in _PLUGIN_MODULES:
            mod = _PLUGIN_MODULES[category]

        # 2. Framework activity modules
        if mod is None:
            module_name = _FRAMEWORK_MODULE_MAP.get(category, category)
            mod = sys.modules.get(f"heartbeat_activities.{module_name}")

        if mod is not None:
            aff = getattr(mod, "SIGNAL_AFFINITY", None)
            result[category] = aff if aff is not None and isinstance(aff, dict) else {}
        else:
            result[category] = {}

    return result


def get_affinities() -> Dict[str, dict]:
    """Lazily build (then memoize) the category → affinity dict map."""
    global _AFFINITY_CACHE
    if _AFFINITY_CACHE is None:
        _AFFINITY_CACHE = _build_affinity_cache()
    return _AFFINITY_CACHE


def invalidate_affinity_cache() -> None:
    """Clear the affinity cache so it rebuilds on next dispatch."""
    global _AFFINITY_CACHE
    _AFFINITY_CACHE = None


# ─── Softmax Pick ─────────────────────────────────────────────────────────────


def softmax_pick(
    candidates: List[str],
    signals: Dict[str, float],
    temperature: float,
    state: dict,
) -> Optional[str]:
    """
    Pick one activity via softmax over (base_weight + signal_bias) scores.

    candidates: list of category names
    signals: {signal_name: value_in_0_to_1} from brain_signals.read_brain_signals
    temperature: softmax temperature (0.7–2.0); low = decisive, high = exploratory
    state: dispatch state dict (used to read overdue counters for base weights)

    Falls back to pure weighted-random if signals dict is empty (no signal config).

    Returns category name or None.
    """
    if not candidates:
        return None

    overdue = state.get("overdue_activities", {})
    affinities = get_affinities()

    # No signals configured — pure weighted random (pre-signal-wiring behavior)
    if not signals:
        weights = {k: 1.0 / (1.0 + overdue.get(k, 0)) for k in candidates}
        total = sum(weights.values()) or 1.0
        r = random.random() * total
        cum = 0.0
        for cat in candidates:
            cum += weights[cat]
            if r <= cum:
                return cat
        return candidates[-1]

    # Compute biased scores
    scores: Dict[str, float] = {}
    for cat in candidates:
        base = 1.0 / (1.0 + overdue.get(cat, 0))
        aff = affinities.get(cat, {})
        # Additive signal bonus: sum of signal_value × affinity_weight
        bonus = sum(signals.get(sig, 0.5) * val for sig, val in aff.items())
        scores[cat] = base + bonus

    # Softmax with temperature (subtract max for numerical stability)
    temp = max(temperature, 1e-6)
    max_score = max(scores.values())
    exp_scores = {cat: math.exp((scores[cat] - max_score) / temp) for cat in candidates}
    total_exp = sum(exp_scores.values()) or 1.0
    probs = {cat: exp_scores[cat] / total_exp for cat in candidates}

    # Cumulative-distribution pick
    r = random.random()
    cum = 0.0
    for cat in candidates:
        cum += probs[cat]
        if r <= cum:
            return cat
    return candidates[-1]


# ─── Dispatch ─────────────────────────────────────────────────────────────────


def dispatch(state: dict) -> dict:
    """
    Run one activity from the pool, applying continuation priority.

    Priority order:
      1. followup_due: activities whose offset has arrived
      2. unfinished threads: CONTINUATION_PROBABILITY chance
      3. overdue activities → softmax pick via brain signals
      4. random exploration from full pool

    Returns activity result dict.
    """
    tick = state.get("tick_count", 0)
    threads = state.get("unfinished_threads", [])

    # 1. followup_due — run if the offset tick has arrived
    followups = [t for t in threads if t.get("followup_due") == tick]
    if followups:
        chosen = followups[0]
        state["unfinished_threads"] = [t for t in threads if t is not chosen]
        return _run_activity(chosen["category"], state, is_continuation=True)

    # 2. Unfinished thread — chance to continue
    if threads and random.random() < CONTINUATION_PROBABILITY:
        chosen = threads[-1]  # most recent unfinished
        state["unfinished_threads"] = threads[:-1]
        return _run_activity(chosen["category"], state, is_continuation=True)

    # 3. Brain-signal-driven softmax pick
    signals = brain_signals.read_brain_signals(state)
    temperature = brain_signals.compute_temperature(
        signals,
        arousal_signal_name=state.get("AROUSAL_SIGNAL", "oscillation_balance"),
        temp_range=tuple(state.get("TEMPERATURE_RANGE", (0.7, 2.0))),
    )
    all_categories = list(ACTIVITY_REGISTRY.keys())
    chosen_category = softmax_pick(all_categories, signals, temperature, state)

    # 4. Run
    return _run_activity(chosen_category, state, is_continuation=False)


def _run_activity(category: str, state: dict, is_continuation: bool = False) -> dict:
    """
    Execute a named activity. Handles continuation context injection.
    """
    runner = ACTIVITY_REGISTRY.get(category)
    if not runner:
        return {
            "ok": False,
            "status": "complete",
            "content": "",
            "category": category,
            "detail": f"Unknown activity: {category}",
        }

    if is_continuation:
        state["continuation_of"] = category

    result = runner(state)

    # Update overdue counter (activity ran, resets to 0)
    overdue = dict(state.get("overdue_activities", {}))
    overdue[category] = 0
    state["overdue_activities"] = overdue

    # Track unfinished / followup_due threads
    status = result.get("status", "complete")
    if status in ("unfinished", "followup_due"):
        followup_due = None
        if status.startswith("followup_due:"):
            offset = int(status.split(":", 1)[1])
            followup_due = offset + state.get("tick_count", 0)

        thread = {
            "category": category,
            "tick": state.get("tick_count", 0),
            "content": result.get("content", ""),
            "followup_due": followup_due,
        }
        state.setdefault("unfinished_threads", []).append(thread)

    return result


# ── Parallel dispatch — Phase A of mechanism parallelism ──────────────────────
#
# dispatch() picks ONE activity per call. With heartbeat firing once per ~90s,
# that means 1 activity every 90s. dispatch_batch() picks up to N due
# activities and fires them concurrently in a thread pool, so a single
# heartbeat tick can drive multiple agent-thoughts in parallel.
#
# Why threads (not asyncio): the activity runners are sync; their LLM/HTTP
# calls release the GIL during network wait, so threads ARE genuinely
# parallel for the I/O-bound bulk of an activity's runtime.
#
# Returns the list of result dicts in completion order.

def dispatch_batch(state: dict, max_concurrent: int = 5, per_activity_timeout: int = 120) -> List[dict]:
    """
    Run up to `max_concurrent` activities simultaneously this tick.

    Selection mirrors dispatch(): followup_due first, then continuations,
    then softmax-picked novel categories. Each activity runs in its own
    thread with its own shallow-copy state; mutations that need to bubble
    up (unfinished_threads, overdue_activities) are merged back into the
    caller's `state` under _PARALLEL_STATE_LOCK.
    """
    if max_concurrent < 1:
        max_concurrent = 1

    tick = state.get("tick_count", 0)
    threads = state.get("unfinished_threads", []) or []

    # Build the queue: list of (category, is_continuation) tuples
    queue: List[tuple] = []
    seen: set = set()

    # 1. followup_due — every one whose offset has arrived
    followups = [t for t in threads if t.get("followup_due") == tick]
    for f in followups[:max_concurrent]:
        cat = f.get("category")
        if cat and cat not in seen:
            queue.append((cat, True))
            seen.add(cat)
    state["unfinished_threads"] = [t for t in threads if t not in followups]

    # 2. Continuations — fill up to half the remaining slots
    remaining_threads = state.get("unfinished_threads", []) or []
    if remaining_threads and len(queue) < max_concurrent:
        slots = max(1, (max_concurrent - len(queue)) // 2)
        # Take from the most recent end first
        for t in remaining_threads[-slots:]:
            cat = t.get("category")
            if cat and cat not in seen:
                queue.append((cat, True))
                seen.add(cat)
                state["unfinished_threads"].remove(t)

    # 3. Softmax-picked novel categories — fill remaining
    if len(queue) < max_concurrent:
        try:
            signals = brain_signals.read_brain_signals(state)
            temperature = brain_signals.compute_temperature(
                signals,
                arousal_signal_name=state.get("AROUSAL_SIGNAL", "oscillation_balance"),
                temp_range=tuple(state.get("TEMPERATURE_RANGE", (0.7, 2.0))),
            )
        except Exception:
            signals, temperature = {}, 1.0

        candidates = [c for c in ACTIVITY_REGISTRY if c not in seen]
        while len(queue) < max_concurrent and candidates:
            try:
                cat = softmax_pick(candidates, signals, temperature, state)
            except Exception:
                cat = random.choice(candidates) if candidates else None
            if not cat:
                break
            queue.append((cat, False))
            seen.add(cat)
            if cat in candidates:
                candidates.remove(cat)

    if not queue:
        return []

    # Fire concurrently. Each activity gets a shallow copy of state so its
    # write-backs (overdue_activities, unfinished_threads) don't race; we
    # merge them under the lock after each future completes.
    results: List[dict] = []

    def _run_locked(category: str, is_continuation: bool, base_state: dict) -> dict:
        local_state = dict(base_state)
        # Pre-mark as continuation so the runner sees it
        if is_continuation:
            local_state["continuation_of"] = category
        try:
            result = _run_activity(category, local_state, is_continuation=is_continuation)
        except Exception as e:
            result = {
                "ok": False, "status": "complete", "content": "",
                "category": category, "proactive": False,
                "detail": f"parallel-run exception: {e}",
            }
        # Merge state mutations from this activity back to the shared state
        with _PARALLEL_STATE_LOCK:
            # Merge new unfinished threads (only ones added by this activity)
            for t in local_state.get("unfinished_threads", []):
                if t not in (base_state.get("unfinished_threads") or []):
                    base_state.setdefault("unfinished_threads", []).append(t)
            # Reset overdue counter for any category that ran
            overdue = dict(base_state.get("overdue_activities", {}) or {})
            overdue[category] = 0
            base_state["overdue_activities"] = overdue
        return result

    workers = min(len(queue), max_concurrent)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {
            ex.submit(_run_locked, cat, is_cont, state): cat
            for cat, is_cont in queue
        }
        for fut in as_completed(futures, timeout=per_activity_timeout * 2):
            cat = futures[fut]
            try:
                result = fut.result(timeout=per_activity_timeout)
            except FutureTimeoutError:
                result = {
                    "ok": False, "status": "complete", "content": "",
                    "category": cat, "proactive": False,
                    "detail": f"parallel-run timeout >{per_activity_timeout}s",
                }
            except Exception as e:
                result = {
                    "ok": False, "status": "complete", "content": "",
                    "category": cat, "proactive": False,
                    "detail": f"parallel-run error: {e}",
                }
            results.append(result)

    return results


_PLUGIN_MODULES: dict[str, object] = {}  # category → loaded module object


def register_plugin(name: str, runner: callable, plugin_module: object = None) -> None:
    """
    Called by the plugin loader at startup to add operator-specific activities.
    Operator plugins live in ~/.agent/activities/ or similar.
    Invalidates the affinity cache so it rebuilds with plugin affinities.

    plugin_module: the loaded module object (from importlib.util.module_from_spec).
    Used to find SIGNAL_AFFINITY on the module after registration.
    """
    ACTIVITY_REGISTRY[name] = runner
    if plugin_module is not None:
        _PLUGIN_MODULES[name] = plugin_module
    invalidate_affinity_cache()
