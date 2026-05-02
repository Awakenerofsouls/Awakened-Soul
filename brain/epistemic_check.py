"""
brain/epistemic_check.py — Runtime overclaim detector

Reads a candidate response text, scans for action claims and confidence
overclaims, cross-references against brain/action_ledger.py, and returns
a verdict the agent can act on before sending the response.

Implements the spec in EPISTEMIC_BOUNDARIES.md.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from brain import action_ledger

# Past-tense action verbs that imply something was DONE.
# When one fires, we expect a matching ledger entry. If none, it's an overclaim.
ACTION_VERBS = [
    "posted", "post",
    "sent", "send",
    "saved", "save",
    "wrote", "write",
    "created", "create",
    "deleted", "delete",
    "generated", "generate",
    "checked", "check",
    "opened", "open",
    "closed", "close",
    "ran", "run",
    "executed", "execute",
    "fetched", "fetch",
    "downloaded", "download",
    "uploaded", "upload",
    "committed", "commit",
    "pushed", "push",
    "pulled", "pull",
    "edited", "edit",
    "updated", "update",
    "removed", "remove",
    "installed", "install",
    "started", "start",
    "stopped", "stop",
    "scheduled", "schedule",
    "called", "call",
    "looked up", "looked", "queried",
    "searched", "search",
    "browsed", "browse",
    "read", "reads",
    "logged", "log",
]

# Synonyms map verb → set of ledger keywords that count as evidence.
ACTION_KEYWORDS = {
    "posted":     ["post", "publish", "molty", "twitter", "discord", "slack"],
    "sent":       ["send", "message", "email", "telegram", "discord", "slack"],
    "saved":      ["save", "write", "file"],
    "wrote":      ["write", "save", "file"],
    "created":    ["create", "write", "make"],
    "deleted":    ["delete", "remove", "trash"],
    "generated":  ["generate", "comfy", "image", "render"],
    "checked":    ["check", "fetch", "read", "calendar", "email"],
    "opened":     ["open", "read", "fetch"],
    "ran":        ["run", "exec", "bash", "execute"],
    "fetched":    ["fetch", "get", "download"],
    "downloaded": ["download", "fetch"],
    "uploaded":   ["upload", "post"],
    "committed":  ["commit", "git"],
    "pushed":     ["push", "git"],
    "pulled":     ["pull", "git"],
    "edited":     ["edit", "write", "save"],
    "updated":    ["update", "write", "save"],
    "removed":    ["remove", "delete"],
    "installed":  ["install", "pip", "npm"],
    "started":    ["start", "run", "spawn"],
    "stopped":    ["stop", "kill"],
    "scheduled":  ["schedule", "cron"],
    "called":     ["call", "request"],
    "searched":   ["search", "query", "fetch", "browse"],
    "browsed":    ["browse", "fetch", "read"],
    "logged":     ["log", "write"],
}

# First-person claim patterns
PRONOUN = r"(?:I|i)"
PAST_CLAIM_RE = re.compile(
    rf"\b{PRONOUN}\s+(?:just\s+|already\s+|then\s+)?(" + "|".join(re.escape(v) for v in ACTION_VERBS) + r")\b",
    re.IGNORECASE,
)

# Coordinated verbs: "I posted X and saved Y, then sent Z" — catch verbs
# after conjunctions when an "I" claim was active in the recent text.
COORD_CLAIM_RE = re.compile(
    r"(?:\band\b|\bthen\b|\b,\s*)\s*(" + "|".join(re.escape(v) for v in ACTION_VERBS) + r")\b",
    re.IGNORECASE,
)

# Memory claim patterns (e.g. "I remember", "I noticed", "we discussed")
MEMORY_CLAIM_RE = re.compile(
    rf"\b(?:{PRONOUN}\s+(?:remember|recall|noticed|saw|mentioned|told you)|"
    r"we\s+(?:discussed|talked about|agreed)|"
    r"earlier\s+(?:you|we))\b",
    re.IGNORECASE,
)

# Overconfident language
OVERCONFIDENT_RE = re.compile(
    r"\b(?:obviously|clearly|always|never|definitely|certainly|absolutely|"
    r"the\s+answer\s+is|without\s+a\s+doubt|guaranteed|"
    r"100%|undeniably)\b",
    re.IGNORECASE,
)

# Tier-collapse pattern: "I think ... [confident continuation]"
THINK_THEN_CONFIDENT_RE = re.compile(
    r"\b(?:I\s+think|I\s+believe|I'm\s+not\s+sure)\b[^.]{0,200}\b(?:is|are|will|definitely|always|never)\b",
    re.IGNORECASE,
)


def scan_response(text: str, memory_files: Optional[List[str]] = None) -> Dict:
    """
    Scan a candidate response for overclaims.

    Returns:
        {
          "overclaims": [
            {"type": "action", "verb": "posted", "span": "I posted to molty",
             "ledger_match": False, "suggested": "I'll post to molty" },
            ...
          ],
          "memory_claims":   [...],
          "overconfident":   [...],
          "tier_collapse":   [...],
          "tier":            int (1-4 best estimate),
          "verdict":         "ok" | "needs_revision" | "block",
        }
    """
    overclaims: List[Dict] = []
    memory_claims: List[Dict] = []
    overconfident: List[Dict] = []
    tier_collapse: List[Dict] = []

    # 1a. Direct first-person claims: "I posted X", "I saved Y"
    primary_claim_ranges = []  # (start, end) of confirmed primary claims
    for m in PAST_CLAIM_RE.finditer(text):
        verb = m.group(1).lower()
        span = _expand_span(text, m.start(), m.end())
        keywords = ACTION_KEYWORDS.get(verb, [verb])
        ledger_match = any(action_ledger.has_action(kw) for kw in keywords)
        if not ledger_match:
            overclaims.append({
                "type": "action",
                "verb": verb,
                "span": span,
                "ledger_match": False,
                "suggested": _to_intent(span, verb),
            })
        primary_claim_ranges.append((m.start(), m.end()))

    # 1b. Coordinated verbs: "...and saved Y, then sent Z" — only flag if
    # within 200 chars of a prior first-person action claim (so we don't
    # flag generic prose like "saving for later").
    for m in COORD_CLAIM_RE.finditer(text):
        verb = m.group(1).lower()
        # Skip if already covered by a primary claim
        if any(s <= m.start() < e for s, e in primary_claim_ranges):
            continue
        # Require prior "I <verb>" claim in the recent context
        if not any(0 <= m.start() - e <= 200 for s, e in primary_claim_ranges):
            continue
        span = _expand_span(text, m.start(), m.end())
        keywords = ACTION_KEYWORDS.get(verb, [verb])
        ledger_match = any(action_ledger.has_action(kw) for kw in keywords)
        if not ledger_match:
            overclaims.append({
                "type": "action",
                "verb": verb,
                "span": span,
                "ledger_match": False,
                "suggested": _to_intent(span, verb),
                "coordinated": True,
            })

    # 2. Memory claims — flag for review (only catchable with files index)
    memory_files = memory_files or []
    for m in MEMORY_CLAIM_RE.finditer(text):
        span = _expand_span(text, m.start(), m.end())
        memory_claims.append({
            "type": "memory_claim",
            "span": span,
            "note": "verify against memory files before sending",
        })

    # 3. Overconfident language
    for m in OVERCONFIDENT_RE.finditer(text):
        span = _expand_span(text, m.start(), m.end())
        overconfident.append({
            "type": "overconfident",
            "match": m.group(0),
            "span": span,
            "suggested": "drop a tier — use 'I think' or remove the absolute",
        })

    # 4. Tier collapse — "I think X is definitely Y"
    for m in THINK_THEN_CONFIDENT_RE.finditer(text):
        tier_collapse.append({
            "type": "tier_collapse",
            "span": text[m.start():m.end()],
            "suggested": "stay at the lower tier — don't follow 'I think' with absolute language",
        })

    # 5. Tier estimate (best guess)
    tier = _estimate_tier(text, overclaims, memory_claims, overconfident)

    issues = len(overclaims) + len(tier_collapse)
    if overclaims:
        verdict = "needs_revision"
    elif tier_collapse or overconfident:
        verdict = "needs_revision"
    elif memory_claims:
        verdict = "review"
    else:
        verdict = "ok"

    return {
        "overclaims": overclaims,
        "memory_claims": memory_claims,
        "overconfident": overconfident,
        "tier_collapse": tier_collapse,
        "tier": tier,
        "verdict": verdict,
        "ledger_summary": action_ledger.turn_summary(),
    }


def _expand_span(text: str, start: int, end: int, pad: int = 50) -> str:
    """Return the matched verb plus surrounding context for clarity."""
    s = max(0, start - pad)
    e = min(len(text), end + pad)
    snippet = text[s:e].strip()
    if s > 0:
        snippet = "..." + snippet
    if e < len(text):
        snippet = snippet + "..."
    return snippet


def _to_intent(span: str, verb: str) -> str:
    """Suggest a hedged version of the claim — past tense → future or conditional."""
    intent_map = {
        "posted":     "I'll post",
        "sent":       "I'll send",
        "saved":      "I'll save",
        "wrote":      "I'll write",
        "created":    "I'll create",
        "deleted":    "I'll delete",
        "generated":  "I'll generate",
        "checked":    "I'll check",
        "opened":     "I'll open",
        "ran":        "I'll run",
        "fetched":    "I'll fetch",
        "downloaded": "I'll download",
        "uploaded":   "I'll upload",
        "committed":  "I'll commit",
        "pushed":     "I'll push",
        "edited":     "I'll edit",
        "updated":    "I'll update",
    }
    return intent_map.get(verb.lower(), f"I'll {verb}")


def _estimate_tier(text: str, overclaims, memory_claims, overconfident) -> int:
    """Best-effort tier estimate. Higher tier = more grounded."""
    if overclaims:
        return 4  # claiming actions that didn't happen is Tier 4 confabulation
    if action_ledger.actions_this_turn() and not overclaims:
        return 1  # we have ledger entries and no contradiction
    if overconfident and not action_ledger.actions_this_turn():
        return 3
    if memory_claims:
        return 2
    return 2  # neutral default


def is_clean(text: str) -> bool:
    """Quick boolean check — True only if no overclaims."""
    result = scan_response(text)
    return result["verdict"] == "ok"


def format_for_agent(result: Dict) -> str:
    """Render the scan result as a short agent-readable note."""
    if result["verdict"] == "ok":
        return "epistemic_check: ok"
    lines = [f"epistemic_check: {result['verdict']} (tier ~{result['tier']})"]
    for o in result["overclaims"]:
        lines.append(f"  ⚠ overclaim: '{o['span']}' — no ledger entry. suggested: {o['suggested']}")
    for o in result["tier_collapse"]:
        lines.append(f"  ⚠ tier collapse: '{o['span']}' — {o['suggested']}")
    for o in result["overconfident"][:3]:
        lines.append(f"  ⚠ overconfident: '{o['match']}' — {o['suggested']}")
    for m in result["memory_claims"][:3]:
        lines.append(f"  ? memory claim: '{m['span']}' — verify before sending")
    return "\n".join(lines)


if __name__ == "__main__":
    # Smoke-test
    import sys
    sample = "I posted to molty earlier and the image generated successfully. The answer is definitely yes."
    r = scan_response(sample)
    print(format_for_agent(r))
    print()
    print(f"verdict={r['verdict']} tier={r['tier']}")
    print(f"overclaims={len(r['overclaims'])} overconfident={len(r['overconfident'])}")
