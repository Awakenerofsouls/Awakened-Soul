"""
core/decide_with_council.py
Council-enhanced decision wrapper.

Sits in front of core.decide.decide(): runs the base decision logic, scores
the result for risk, and — if COUNCIL_MODE is "always" or risk crosses
COUNCIL_RISK_THRESHOLD — fires the 16-brain council.

When the council fires, this wrapper pulls the most recent brain-runner
snapshot (the digested brain_* signals + raw per-mechanism outputs from
all 1287 mechanisms) and hands it to the council so each specialist
votes informed by what the brain is actually feeling, not by dice alone.

Usage in core/loop.py:
    from core.decide_with_council import decide_with_council
    decision = decide_with_council() or idle_maintenance()
"""

from core.decide import decide as base_decide
from core.council import Council
from core.brain_runner import get_last_brain_state, get_last_mechanism_outputs
from core import settings


_HIGH_RISK_PREFIXES = ("deploy", "delete", "rm", "sudo", "exec", "push", "publish")
_HIGH_RISK_ACTIONS = ("http_request", "send", "post", "put")


# Council instance — initialised lazily so importing this module doesn't
# build the council if it's never going to fire.
_council: Council | None = None


def _get_council() -> Council:
    global _council
    if _council is None:
        _council = Council()
    return _council


def _score_risk(decision) -> float:
    """Heuristic risk score 0.0–1.0. Mirrors the original logic."""
    if decision is None:
        return 0.0
    try:
        subtask_id = decision.get("subtask_id", "") or ""
        action = decision.get("action") or ""
    except AttributeError:
        return 0.0

    risk = 0.1
    if action == "execute":
        risk += 0.2
    for prefix in _HIGH_RISK_PREFIXES:
        if subtask_id.startswith(prefix):
            risk += 0.4
            break
    if action in _HIGH_RISK_ACTIONS:
        risk += 0.25
    return min(risk, 1.0)


def decide_with_council():
    """Run the base decision and, if risk warrants it, run the council.

    Returns either the base decision dict (council not fired) or the
    council-enriched dict (with council_verdict / council_confidence /
    council_votes / council_recommendation / council_brain_state_used).
    """
    base = base_decide()

    if base is None:
        return None

    if getattr(settings, "COUNCIL_MODE", "off") == "off":
        return base

    risk = _score_risk(base)
    threshold = getattr(settings, "COUNCIL_RISK_THRESHOLD", 0.5)

    if settings.COUNCIL_MODE == "always" or risk > threshold:
        # Pull the latest tick snapshot so the council can vote informed.
        # If the runner isn't booted (tests, isolated decisions, fresh
        # process), the helpers return {} and the council falls back to
        # heuristic voting without crashing.
        brain_state = get_last_brain_state()
        mechanism_outputs = get_last_mechanism_outputs()
        return _get_council().decide(base, brain_state, mechanism_outputs)

    return base
