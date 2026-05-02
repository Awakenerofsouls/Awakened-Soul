#!/usr/bin/env python3
"""
skills/skill-discovery/discovery.py — request-time skill routing.

Pairs with skills/skill-discovery/SKILL.md.

Reads SKILL.md frontmatter across the registry (skills/<name>/SKILL.md),
parses name / description / triggers / tags / version, and provides a
matcher that scores each registered skill against an incoming request.

Usage as library:

    from skills.skill_discovery.discovery import SkillDiscovery
    sd = SkillDiscovery()
    sd.register_all()
    out = sd.route("research and summarize the consensus on this", mode="brain")
    print(out["chosen"], out["score"])

Usage as CLI:

    python -m skills.skill-discovery.discovery list
    python -m skills.skill-discovery.discovery match "research and summarize"
    python -m skills.skill-discovery.discovery route "ship the fix" --mode build
    python -m skills.skill-discovery.discovery status
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ── Paths ────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "skills"

# ── Scoring weights ──────────────────────────────────────────────────────

DEFAULT_WEIGHTS = {
    "trigger": 0.45,
    "tag": 0.20,
    "description": 0.30,
    "mode": 0.05,
}
DEFAULT_THRESHOLD = 0.30
AMBIGUITY_EPSILON = 0.05  # if 2nd-best within this of top, ambiguous

# Per-mode skill affinity (mode → set of skills that benefit from the bonus).
MODE_PREFERRED: Dict[str, set] = {
    "brain": {"web-research", "knowledge-summarization", "qmd"},
    "coach": {"humanizer"},
    "build": {"code-execution", "task-planning", "file-system"},
    "default": set(),
}

VALID_MODES = {"brain", "coach", "build", "default"}

# Tokens we ignore when deriving request tags.
STOPWORDS = {
    "a", "an", "and", "the", "or", "but", "of", "to", "for", "in", "on",
    "at", "is", "was", "are", "be", "by", "with", "from", "as", "if",
    "this", "that", "it", "i", "you", "we", "they", "my", "your", "do",
    "did", "does", "have", "has", "had", "can", "could", "should",
    "would", "will", "shall", "may", "might", "be", "been",
}

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9'-]+")


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    return [t.lower() for t in _TOKEN_RE.findall(text) if len(t) >= 2]


def _content_tokens(text: str) -> List[str]:
    return [t for t in _tokenize(text) if t not in STOPWORDS]


def parse_frontmatter(md_text: str) -> Dict[str, Any]:
    """Parse YAML-style frontmatter from a SKILL.md.

    Hand-rolled (no dependency on pyyaml). Supports the small subset
    used by this project: top-level scalars, simple `[a, b, c]` lists,
    quoted strings, and basic multi-line lists.
    """
    if not md_text.startswith("---"):
        return {}
    lines = md_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end == -1:
        return {}
    block = lines[1:end]

    out: Dict[str, Any] = {}
    current_key: Optional[str] = None
    current_list: Optional[List[str]] = None
    for raw in block:
        line = raw.rstrip()
        if not line.strip():
            continue
        # Continuation list item?
        m = re.match(r"^\s+-\s*(.*)$", line)
        if m and current_list is not None:
            current_list.append(m.group(1).strip().strip('"').strip("'"))
            continue
        # New key.
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if not m:
            continue
        key = m.group(1)
        rest = m.group(2).strip()
        current_key = key
        current_list = None

        if rest == "":
            # Block-list start.
            current_list = []
            out[key] = current_list
            continue

        # Inline list?
        if rest.startswith("[") and rest.endswith("]"):
            inner = rest[1:-1].strip()
            if not inner:
                out[key] = []
            else:
                items = []
                for piece in re.split(r",\s*", inner):
                    items.append(piece.strip().strip('"').strip("'"))
                out[key] = items
            current_list = None
            continue

        # Inline scalar.
        val = rest.strip().strip('"').strip("'")
        out[key] = val
        current_list = None

    return out


# ── SkillDiscovery ───────────────────────────────────────────────────────


class SkillDiscovery:
    """Request-time skill router. Library + CLI."""

    def __init__(
        self,
        skills_dir: Optional[Path] = None,
        weights: Optional[Dict[str, float]] = None,
    ):
        self.skills_dir = Path(skills_dir) if skills_dir else SKILLS_DIR
        self.weights = dict(DEFAULT_WEIGHTS)
        if weights:
            self.weights.update(weights)
        self.registry: Dict[str, Dict[str, Any]] = {}

    # ── Registry ───────────────────────────────────────────────────────

    def register(self, skill_path: Path) -> Dict[str, Any]:
        """Read a SKILL.md and add to the registry. Returns the entry."""
        skill_path = Path(skill_path)
        if not skill_path.exists():
            return {"ok": False, "reason": f"not found: {skill_path}"}
        try:
            text = skill_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return {"ok": False, "reason": str(e)}
        fm = parse_frontmatter(text)
        if not fm:
            return {"ok": False, "reason": "no frontmatter"}

        name = (fm.get("name") or skill_path.parent.name).strip()
        desc = (fm.get("description") or "").strip()
        triggers = list(fm.get("triggers") or [])
        tags = list(fm.get("tags") or [])
        version = (fm.get("version") or "").strip()

        try:
            mtime = skill_path.stat().st_mtime
        except FileNotFoundError:
            mtime = 0.0

        # Pre-tokenize the description for cosine matching.
        desc_tokens = Counter(_content_tokens(desc))

        entry = {
            "name": name,
            "path": str(skill_path),
            "version": version,
            "description": desc,
            "triggers": [t.lower() for t in triggers if t],
            "tags": [t.lower() for t in tags if t],
            "desc_tokens": dict(desc_tokens),
            "mtime": mtime,
            "registered_at": time.time(),
        }
        self.registry[name] = entry
        return {"ok": True, "entry": entry}

    def register_all(self, skills_dir: Optional[Path] = None) -> Dict[str, Any]:
        """Scan a directory and register every SKILL.md found."""
        directory = Path(skills_dir) if skills_dir else self.skills_dir
        added = 0
        skipped = 0
        if not directory.exists():
            return {"ok": False, "reason": f"missing: {directory}"}
        for skill_dir in sorted(directory.iterdir()):
            if not skill_dir.is_dir():
                continue
            md = skill_dir / "SKILL.md"
            if not md.exists():
                skipped += 1
                continue
            r = self.register(md)
            if r.get("ok"):
                added += 1
            else:
                skipped += 1
        return {
            "ok": True,
            "added": added,
            "skipped": skipped,
            "total_registered": len(self.registry),
        }

    def stale_entries(self) -> List[str]:
        """Return names of entries whose SKILL.md mtime is newer than what
        the registry has. Used by callers to refresh before matching."""
        out: List[str] = []
        for name, entry in self.registry.items():
            path = Path(entry["path"])
            try:
                mtime = path.stat().st_mtime
            except FileNotFoundError:
                continue
            if mtime > entry.get("mtime", 0.0) + 0.5:
                out.append(name)
        return out

    def refresh_stale(self) -> Dict[str, Any]:
        """Re-register entries whose disk mtime is newer than registry."""
        names = self.stale_entries()
        for name in names:
            path = Path(self.registry[name]["path"])
            self.register(path)
        return {"refreshed": len(names), "names": names}

    # ── Matching ───────────────────────────────────────────────────────

    def match(
        self,
        request: str,
        mode: str = "default",
        top_n: int = 5,
        min_score: float = 0.0,
        auto_refresh: bool = True,
    ) -> Dict[str, Any]:
        """Score every registered skill against the request."""
        if mode not in VALID_MODES:
            mode = "default"
        if auto_refresh:
            self.refresh_stale()
        if not request or not request.strip():
            return {
                "ok": False,
                "reason": "empty request",
                "candidates": [],
            }

        req_lower = request.lower()
        req_tokens = Counter(_content_tokens(request))
        req_token_set = set(req_tokens.keys())
        preferred = MODE_PREFERRED.get(mode, set())

        candidates: List[Dict[str, Any]] = []
        for name, entry in self.registry.items():
            scored = self._score(entry, req_lower, req_tokens, req_token_set, preferred)
            scored["skill"] = name
            candidates.append(scored)

        candidates.sort(key=lambda x: x["score"], reverse=True)
        if min_score > 0:
            candidates = [c for c in candidates if c["score"] >= min_score]
        candidates = candidates[: max(1, int(top_n))]

        ambiguous = (
            len(candidates) >= 2
            and candidates[0]["score"] > 0
            and (candidates[0]["score"] - candidates[1]["score"]) < AMBIGUITY_EPSILON
        )

        return {
            "ok": True,
            "request": request,
            "mode": mode,
            "candidates": candidates,
            "ambiguous": ambiguous,
            "stale_entries_refreshed": auto_refresh,
        }

    def _score(
        self,
        entry: Dict[str, Any],
        req_lower: str,
        req_tokens: Counter,
        req_token_set: set,
        preferred: set,
    ) -> Dict[str, Any]:
        # 1. Trigger hits — fraction of skill's triggers that appear in request.
        triggers = entry.get("triggers") or []
        if triggers:
            trigger_hits = sum(1 for t in triggers if t and t in req_lower)
            trigger_rate = trigger_hits / max(1, len(triggers))
        else:
            trigger_hits = 0
            trigger_rate = 0.0

        # 2. Tag overlap — Jaccard between request content tokens and skill tags.
        tags = set(entry.get("tags") or [])
        if tags:
            inter = tags & req_token_set
            union = tags | req_token_set
            tag_overlap = len(inter) / max(1, len(union)) if union else 0.0
        else:
            inter = set()
            tag_overlap = 0.0

        # 3. Description token cosine — TF-IDF-lite cosine between request and
        # skill description tokens.
        desc_tokens = entry.get("desc_tokens") or {}
        desc_cosine = self._cosine(req_tokens, desc_tokens)

        # 4. Mode bonus.
        mode_bonus = 1.0 if entry["name"] in preferred else 0.0

        # Composite.
        score = (
            self.weights["trigger"] * trigger_rate
            + self.weights["tag"] * tag_overlap
            + self.weights["description"] * desc_cosine
            + self.weights["mode"] * mode_bonus
        )

        return {
            "score": round(float(score), 4),
            "trigger_hits": trigger_hits,
            "trigger_rate": round(trigger_rate, 4),
            "tag_overlap": round(tag_overlap, 4),
            "tag_hits": sorted(inter),
            "description_cosine": round(desc_cosine, 4),
            "mode_bonus": int(mode_bonus),
        }

    @staticmethod
    def _cosine(a: Counter, b: Dict[str, int]) -> float:
        if not a or not b:
            return 0.0
        # Cosine of two raw-token bags. Sufficient for short request vs.
        # short description.
        dot = sum(a[k] * b[k] for k in a if k in b)
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    # ── Routing ────────────────────────────────────────────────────────

    def route(
        self,
        request: str,
        mode: str = "default",
        threshold: float = DEFAULT_THRESHOLD,
        auto_refresh: bool = True,
    ) -> Dict[str, Any]:
        """Pick one skill or fall back. Returns a routing decision."""
        m = self.match(request, mode=mode, top_n=5, auto_refresh=auto_refresh)
        if not m.get("ok"):
            return {
                "ok": False,
                "operation": "route",
                "reason": m.get("reason", "match failed"),
                "chosen": None,
            }
        candidates = m.get("candidates", [])
        if not candidates:
            return self.fallback(request, "no candidates", mode=mode)
        top = candidates[0]
        if top["score"] < threshold:
            return self.fallback(
                request, f"top score {top['score']:.3f} < threshold {threshold:.2f}",
                mode=mode,
                candidates=candidates,
            )

        routing_id = f"rt_{uuid.uuid4().hex[:10]}"
        return {
            "ok": True,
            "operation": "route",
            "routing_id": routing_id,
            "request": request,
            "mode": mode,
            "chosen": top["skill"],
            "score": top["score"],
            "ambiguous": m.get("ambiguous", False),
            "reason": self._format_reason(top),
            "candidates": candidates,
            "stale_entries": self.stale_entries(),
        }

    def fallback(
        self,
        request: str,
        reason: str,
        mode: str = "default",
        candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Explicit no-skill-applies decision."""
        routing_id = f"rt_{uuid.uuid4().hex[:10]}"
        return {
            "ok": True,
            "operation": "fallback",
            "routing_id": routing_id,
            "request": request,
            "mode": mode,
            "chosen": None,
            "score": 0.0,
            "reason": reason,
            "candidates": candidates or [],
        }

    @staticmethod
    def _format_reason(scored: Dict[str, Any]) -> str:
        bits = []
        if scored.get("trigger_hits"):
            bits.append(f"trigger hits {scored['trigger_hits']}")
        if scored.get("tag_hits"):
            bits.append(f"tag overlap {scored['tag_overlap']:.2f}")
        if scored.get("description_cosine", 0) > 0:
            bits.append(f"description cosine {scored['description_cosine']:.2f}")
        if scored.get("mode_bonus"):
            bits.append("mode-preferred")
        return "; ".join(bits) or "low overall match"

    # ── Status ─────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        return {
            "skills_dir": str(self.skills_dir),
            "registered": len(self.registry),
            "stale_count": len(self.stale_entries()),
            "weights": dict(self.weights),
            "names": sorted(self.registry.keys()),
        }

    def configure_weights(self, **kwargs: Any) -> Dict[str, float]:
        """Tune weights at runtime. Restricted per SKILL.md trust level."""
        for key, val in kwargs.items():
            if key in self.weights:
                self.weights[key] = float(val)
        return dict(self.weights)


# ── CLI ──────────────────────────────────────────────────────────────────


def _cli() -> int:
    parser = argparse.ArgumentParser(
        prog="skill-discovery",
        description="Request-time skill routing.",
    )
    parser.add_argument(
        "--skills-dir", default=None,
        help="Override the skills dir (default: REPO_ROOT/skills)",
    )
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="List registered skills")
    p_match = sub.add_parser("match", help="Show ranked candidates")
    p_match.add_argument("request", nargs="+")
    p_match.add_argument("--mode", default="default", choices=sorted(VALID_MODES))
    p_match.add_argument("-n", type=int, default=5)
    p_route = sub.add_parser("route", help="Pick one skill or fall back")
    p_route.add_argument("request", nargs="+")
    p_route.add_argument("--mode", default="default", choices=sorted(VALID_MODES))
    p_route.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    sub.add_parser("status", help="Show registry health")

    args = parser.parse_args()
    sd = SkillDiscovery(skills_dir=args.skills_dir)
    sd.register_all()

    def _emit(obj: Any) -> None:
        print(json.dumps(obj, indent=2, default=str))

    if args.cmd == "list":
        _emit({k: {
            "version": v.get("version"),
            "triggers": v.get("triggers"),
            "tags": v.get("tags"),
        } for k, v in sd.registry.items()})
    elif args.cmd == "match":
        _emit(sd.match(" ".join(args.request), mode=args.mode, top_n=args.n))
    elif args.cmd == "route":
        _emit(sd.route(
            " ".join(args.request), mode=args.mode, threshold=args.threshold,
        ))
    elif args.cmd == "status":
        _emit(sd.status())
    else:
        parser.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
