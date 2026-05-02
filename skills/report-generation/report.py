#!/usr/bin/env python3
"""
skills/report-generation/report.py — structured report production.

Pairs with skills/report-generation/SKILL.md.

Implements:
  - Report + Section + Source dataclasses
  - draft(brief, sources, structure_spec, mode) → proposed Report
  - revise(report_id, kind, ...) → in-flight or post-publish revision
  - publish(report_id, target_path) → save to disk + return path
  - retract(report_id, reason) → mark retracted, preserve audit trail
  - reflect(report_id, fit, notes, actual_outcome) → retrospective
  - Fidelity signals: fabrication, citation_drift, structure_complete,
    voice_preservation, hedge_preservation, potential_hallucinations
  - Persistence to AGENT_HOME/reports_log/
  - Library + CLI

Usage as library:

    from skills.report_generation.report import Reporter, Source
    r = Reporter()
    sources = [Source(source_id="src_1", uri="...", source_type="qmd",
                      source_confidence=0.85, excerpt="...")]
    rep = r.draft(brief="Q1 audit", sources=sources,
                  structure_spec=["Findings","Caveats"], mode="brain")
    r.publish(rep.report_id)
    r.retract(rep.report_id, reason="source_changed")
    r.reflect(rep.report_id, fit=False, notes="claims didn't hold")

Usage as CLI:

    python -m skills.report-generation.report list
    python -m skills.report-generation.report status rp_xxx
    python -m skills.report-generation.report retract rp_xxx --reason source_changed
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

# ── Paths and constants ──────────────────────────────────────────────────

AGENT_HOME = Path(os.environ.get("AGENT_HOME", str(Path.home() / ".agent")))
AGENT_WORKSPACE = Path(os.environ.get(
    "AGENT_WORKSPACE", str(Path.home() / ".agent" / "workspace")
))
REPORTS_LOG = AGENT_HOME / "reports_log"
REPORTS_OUTPUT = AGENT_WORKSPACE / "reports"

VALID_STATES = ("draft", "published", "retracted", "superseded")
VALID_MODES = ("brain", "coach", "build", "default")
VALID_REVISION_KINDS = ("section_edit", "add_section", "drop_section")
VALID_SOURCE_TYPES = ("qmd", "web", "memory", "operator", "external")
VALID_RETRACT_REASONS = (
    "source_changed",
    "factually_wrong",
    "operator_request",
    "superseded_by",
    "safety_concern",
)

# Hedging / contradiction patterns — same vocabulary as
# CompressionFidelityLayer so the report-generation skill keeps the same
# discipline.
HEDGE_PATTERNS = [
    r"\bmight\b", r"\bmay\b", r"\bcould\b", r"\bperhaps\b", r"\bpossibly\b",
    r"\bsomewhat\b", r"\bapproximately\b", r"\babout\b", r"\bsome\b",
    r"\bsuggests?\b", r"\bappears?\b", r"\bseems?\b", r"\bindicates?\b",
    r"\blikely\b", r"\bunlikely\b", r"\bprobably\b", r"\bevidence suggests\b",
    r"\bin many cases\b", r"\bin some cases\b", r"\bnot conclusive\b",
    r"\bunclear\b", r"\buncertain\b", r"\btentative\b",
]

# Specific-content extractors for fabrication detection.
_PROPER_NOUN_RE = re.compile(r"\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]+)*)\b")
_NUMBER_RE = re.compile(r"\b(\d{2,}(?:[.,]\d+)?(?:\s*%)?)\b")

# Voice signatures — hard-default, override by importing
# AGENT_VOICE_SIGNATURES from runtime.self_awareness when available.
DEFAULT_VOICE_SIGNATURES = {
    "the operator", "i'm not sure", "honestly", "that's real",
    "i don't know", "i want", "i think", "i feel",
}
VOICE_PRESERVATION_FLOOR = 0.60
HEDGE_PRESERVATION_FLOOR = 0.50
CITATION_DRIFT_RATE_FLOOR = 0.40

# Floor below which fabrication count is ignored.
FABRICATION_REPORT_LEN_FLOOR = 50


def _hid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _hash_text(text: str) -> str:
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _slugify(s: str, max_len: int = 40) -> str:
    s = (s or "report").lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    return (s or "report")[:max_len]


def _load_voice_signatures() -> Set[str]:
    try:
        from runtime.self_awareness import AGENT_VOICE_SIGNATURES  # type: ignore
        if AGENT_VOICE_SIGNATURES:
            return {s.lower() for s in AGENT_VOICE_SIGNATURES if isinstance(s, str)}
    except Exception:
        pass
    return set(DEFAULT_VOICE_SIGNATURES)


# ── Dataclasses ──────────────────────────────────────────────────────────


@dataclass
class Source:
    source_id: str
    uri: str = ""
    source_type: str = "qmd"
    source_confidence: float = 0.7
    excerpt: str = ""


@dataclass
class Section:
    name: str
    body: str = ""
    source_ids: List[str] = field(default_factory=list)


@dataclass
class RevisionRecord:
    ts: float
    kind: str
    section_name: Optional[str] = None
    new_body: Optional[str] = None
    new_source_ids: Optional[List[str]] = None
    after: Optional[str] = None
    reason: str = ""


@dataclass
class Report:
    report_id: str
    title: str
    brief: str
    state: str
    mode_at_creation: str
    structure_spec: List[str] = field(default_factory=list)
    sections: List[Section] = field(default_factory=list)
    sources: List[Source] = field(default_factory=list)
    drafted_at: float = field(default_factory=time.time)
    published_at: Optional[float] = None
    retracted_at: Optional[float] = None
    retraction_reason: Optional[str] = None
    output_path: Optional[str] = None
    revisions: List[RevisionRecord] = field(default_factory=list)
    reflection: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["sections"] = [asdict(s) for s in self.sections]
        d["sources"] = [asdict(src) for src in self.sources]
        d["revisions"] = [asdict(r) for r in self.revisions]
        return d


# ── Fidelity signal helpers ──────────────────────────────────────────────


def _count_hits(text: str, patterns: List[str]) -> int:
    if not text or not patterns:
        return 0
    lower = text.lower()
    n = 0
    for pat in patterns:
        n += len(re.findall(pat, lower))
    return n


def _candidate_specifics(text: str) -> Set[str]:
    """Same heuristic as CompressionFidelityLayer — proper nouns + specific
    numbers that will be checked against source excerpts."""
    if not text:
        return set()
    nouns: Set[str] = set()
    for phrase in _PROPER_NOUN_RE.findall(text):
        phrase = phrase.strip()
        if not phrase:
            continue
        nouns.add(phrase)
        for word in phrase.split():
            w = word.strip()
            if w and w[0].isupper():
                nouns.add(w)
    numbers = set(_NUMBER_RE.findall(text))
    return {s.strip() for s in nouns | numbers if s.strip()}


def _voice_preservation_rate(
    body: str,
    signatures: Optional[Set[str]] = None,
) -> float:
    sigs = signatures if signatures is not None else _load_voice_signatures()
    if not sigs:
        return 1.0
    if not body:
        return 0.0
    lower = body.lower()
    hits = sum(1 for s in sigs if s in lower)
    return round(hits / len(sigs), 4)


def _hedge_preservation_rate(
    source_text: str,
    report_body: str,
) -> float:
    s_h = _count_hits(source_text, HEDGE_PATTERNS)
    if s_h == 0:
        return 1.0  # no hedging to preserve
    r_h = _count_hits(report_body, HEDGE_PATTERNS)
    return round(min(1.0, r_h / s_h), 4)


def compute_report_fidelity_signals(
    report: Report,
    voice_signatures: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Compute the fidelity signal payload for a report."""
    body = "\n\n".join(s.body for s in report.sections if s.body)
    all_excerpts = "\n\n".join(src.excerpt for src in report.sources if src.excerpt)
    excerpt_specifics: Set[str] = set()
    for src in report.sources:
        excerpt_specifics |= _candidate_specifics(src.excerpt)

    body_specifics = _candidate_specifics(body)
    potential_hallucinations = sorted(body_specifics - excerpt_specifics)

    # Fabrication: count how many specifics in the body don't appear in any source.
    # Filter out very short or generic words to reduce noise.
    fabrication_count = 0
    if len(body) >= FABRICATION_REPORT_LEN_FLOOR:
        fabrication_count = len([
            s for s in potential_hallucinations
            if len(s) >= 4
        ])

    # Citation drift: fraction of sections that have at least one cited
    # source whose specifics don't intersect with the section body's
    # specifics.
    drift_sections = 0
    sourced_sections = 0
    for sec in report.sections:
        if not sec.source_ids:
            continue
        sourced_sections += 1
        sec_specifics = _candidate_specifics(sec.body)
        sec_source_specifics: Set[str] = set()
        for src in report.sources:
            if src.source_id in sec.source_ids:
                sec_source_specifics |= _candidate_specifics(src.excerpt)
        # Drift = section has specifics but very few overlap with cited
        # sources' specifics.
        if sec_specifics:
            overlap = sec_specifics & sec_source_specifics
            if not overlap or (len(overlap) / max(1, len(sec_specifics)) < 0.20):
                drift_sections += 1
    citation_drift_rate = (
        round(drift_sections / sourced_sections, 4) if sourced_sections else 0.0
    )

    # Structure complete: every spec'd section exists and is non-empty.
    structure_complete = True
    if report.structure_spec:
        existing_names = {s.name for s in report.sections if s.body.strip()}
        missing = [n for n in report.structure_spec if n not in existing_names]
        structure_complete = (len(missing) == 0)
    else:
        missing = []
        structure_complete = bool(report.sections)

    # Voice preservation across the body.
    voice_rate = _voice_preservation_rate(body, voice_signatures)

    # Hedge preservation against the union of source excerpts.
    hedge_rate = _hedge_preservation_rate(all_excerpts, body)

    return {
        "fabrication_count": fabrication_count,
        "potential_hallucinations": potential_hallucinations[:10],
        "citation_drift_rate": citation_drift_rate,
        "structure_complete": structure_complete,
        "missing_sections": list(missing) if report.structure_spec else [],
        "voice_preservation_rate": voice_rate,
        "voice_below_floor": voice_rate < VOICE_PRESERVATION_FLOOR,
        "hedge_preservation_rate": hedge_rate,
        "hedge_stripped": hedge_rate < HEDGE_PRESERVATION_FLOOR and _count_hits(all_excerpts, HEDGE_PATTERNS) >= 3,
        "section_count": len(report.sections),
        "source_count": len(report.sources),
        "body_length": len(body),
    }


# ── Reporter ─────────────────────────────────────────────────────────────


class Reporter:
    """Report lifecycle manager. Library + CLI."""

    def __init__(
        self,
        log_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
    ):
        self.log_dir = Path(log_dir) if log_dir else REPORTS_LOG
        self.output_dir = Path(output_dir) if output_dir else REPORTS_OUTPUT
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.reports: Dict[str, Report] = {}
        self._load_all()

    # ── Persistence ────────────────────────────────────────────────────

    def _log_path(self, report_id: str) -> Path:
        return self.log_dir / f"{report_id}.json"

    def _persist(self, report: Report) -> None:
        try:
            self._log_path(report.report_id).write_text(
                json.dumps(report.to_dict(), indent=2, default=str)
            )
        except Exception:
            pass

    def _load_all(self) -> None:
        if not self.log_dir.exists():
            return
        for path in sorted(self.log_dir.glob("rp_*.json")):
            try:
                data = json.loads(path.read_text())
            except Exception:
                continue
            try:
                rep = Report(
                    report_id=str(data.get("report_id", path.stem)),
                    title=str(data.get("title", "")),
                    brief=str(data.get("brief", "")),
                    state=str(data.get("state", "draft")),
                    mode_at_creation=str(data.get("mode_at_creation", "default")),
                    structure_spec=list(data.get("structure_spec") or []),
                    drafted_at=float(data.get("drafted_at", time.time())),
                    published_at=data.get("published_at"),
                    retracted_at=data.get("retracted_at"),
                    retraction_reason=data.get("retraction_reason"),
                    output_path=data.get("output_path"),
                    reflection=data.get("reflection"),
                )
                for s in data.get("sections") or []:
                    rep.sections.append(Section(
                        name=s.get("name", ""),
                        body=s.get("body", ""),
                        source_ids=list(s.get("source_ids") or []),
                    ))
                for src in data.get("sources") or []:
                    rep.sources.append(Source(
                        source_id=src.get("source_id", _hid("src")),
                        uri=src.get("uri", ""),
                        source_type=src.get("source_type", "external"),
                        source_confidence=float(src.get("source_confidence", 0.5)),
                        excerpt=src.get("excerpt", ""),
                    ))
                for r in data.get("revisions") or []:
                    rep.revisions.append(RevisionRecord(
                        ts=float(r.get("ts", time.time())),
                        kind=str(r.get("kind", "section_edit")),
                        section_name=r.get("section_name"),
                        new_body=r.get("new_body"),
                        new_source_ids=r.get("new_source_ids"),
                        after=r.get("after"),
                        reason=str(r.get("reason", "")),
                    ))
                self.reports[rep.report_id] = rep
            except Exception:
                continue

    # ── draft ──────────────────────────────────────────────────────────

    def draft(
        self,
        brief: str,
        sources: List[Source],
        title: Optional[str] = None,
        structure_spec: Optional[List[str]] = None,
        mode: Optional[str] = None,
        sections_override: Optional[List[Section]] = None,
    ) -> Report:
        """Produce a first-pass report."""
        report_id = _hid("rp")
        m = mode if mode in VALID_MODES else "default"
        spec = list(structure_spec or [])
        actual_title = (title or brief or "Untitled report").strip()[:120]

        # Convert raw dicts to Source objects if needed (caller convenience).
        norm_sources: List[Source] = []
        for s in sources or []:
            if isinstance(s, Source):
                norm_sources.append(s)
            elif isinstance(s, dict):
                norm_sources.append(Source(
                    source_id=s.get("source_id") or _hid("src"),
                    uri=s.get("uri", ""),
                    source_type=s.get("source_type", "external"),
                    source_confidence=float(s.get("source_confidence", 0.5)),
                    excerpt=s.get("excerpt", ""),
                ))

        rep = Report(
            report_id=report_id,
            title=actual_title,
            brief=brief.strip(),
            state="draft",
            mode_at_creation=m,
            structure_spec=spec,
            sources=norm_sources,
        )

        if sections_override is not None:
            rep.sections = list(sections_override)
        else:
            rep.sections = self._heuristic_sections(spec, brief, norm_sources)

        self.reports[report_id] = rep
        self._persist(rep)
        return rep

    @staticmethod
    def _heuristic_sections(
        spec: List[str],
        brief: str,
        sources: List[Source],
    ) -> List[Section]:
        """Pure-Python initial sectioning. Generates one section per
        structure_spec entry; if no spec, generates Findings + Sources sections.

        Each section is seeded with placeholder text that includes excerpts
        from each cited source to help the operator review what's there.
        Real composition is the caller's job (likely an LLM call). The
        contract here is: a valid sectioned report shape with each section
        carrying source_ids."""
        sections: List[Section] = []
        all_source_ids = [s.source_id for s in sources]

        if spec:
            for name in spec:
                # Synthesize a scaffold body so the structure-complete
                # check has something to look at; the caller is expected
                # to overwrite via revise(section_edit).
                body_lines = [f"_{name} (draft scaffold for: {brief[:80]})_"]
                if all_source_ids:
                    body_lines.append("")
                    body_lines.append(f"Drawing from {len(all_source_ids)} source(s).")
                sections.append(Section(
                    name=name,
                    body="\n".join(body_lines),
                    source_ids=list(all_source_ids),
                ))
        else:
            # Default: Findings + Sources sections.
            findings_body = f"_Findings (draft scaffold for: {brief[:80]})_"
            sections.append(Section(
                name="Findings",
                body=findings_body,
                source_ids=list(all_source_ids),
            ))
            if sources:
                lines = ["Sources cited:"]
                for src in sources:
                    lines.append(
                        f"- [{src.source_type}] {src.uri or src.source_id} "
                        f"(confidence {src.source_confidence:.2f})"
                    )
                sections.append(Section(
                    name="Sources",
                    body="\n".join(lines),
                    source_ids=list(all_source_ids),
                ))
        return sections

    # ── revise ─────────────────────────────────────────────────────────

    def revise(
        self,
        report_id: str,
        kind: str,
        section_name: Optional[str] = None,
        new_body: Optional[str] = None,
        new_source_ids: Optional[List[str]] = None,
        after: Optional[str] = None,
        reason: str = "",
    ) -> Dict[str, Any]:
        rep = self.reports.get(report_id)
        if not rep:
            return {"ok": False, "reason": f"unknown report_id {report_id!r}"}
        if rep.state in ("retracted", "superseded"):
            return {"ok": False, "reason": f"report state is {rep.state!r}; not revisable"}
        if kind not in VALID_REVISION_KINDS:
            return {"ok": False, "reason": f"invalid revision kind {kind!r}"}

        if kind == "section_edit":
            if not section_name:
                return {"ok": False, "reason": "section_edit requires section_name"}
            target = next((s for s in rep.sections if s.name == section_name), None)
            if not target:
                return {"ok": False, "reason": f"unknown section {section_name!r}"}
            if new_body is not None:
                target.body = new_body
            if new_source_ids is not None:
                # Validate.
                known = {s.source_id for s in rep.sources}
                bad = [sid for sid in new_source_ids if sid not in known]
                if bad:
                    return {"ok": False, "reason": f"unknown source_ids: {bad}"}
                target.source_ids = list(new_source_ids)
        elif kind == "add_section":
            if not section_name:
                return {"ok": False, "reason": "add_section requires section_name"}
            if any(s.name == section_name for s in rep.sections):
                return {"ok": False, "reason": f"section {section_name!r} already exists"}
            new_sec = Section(
                name=section_name,
                body=new_body or f"_{section_name}_",
                source_ids=list(new_source_ids or []),
            )
            if after:
                idx = next((i for i, s in enumerate(rep.sections) if s.name == after), -1)
                if idx >= 0:
                    rep.sections.insert(idx + 1, new_sec)
                else:
                    rep.sections.append(new_sec)
            else:
                rep.sections.append(new_sec)
        elif kind == "drop_section":
            if not section_name:
                return {"ok": False, "reason": "drop_section requires section_name"}
            before_n = len(rep.sections)
            rep.sections = [s for s in rep.sections if s.name != section_name]
            if len(rep.sections) == before_n:
                return {"ok": False, "reason": f"section {section_name!r} not found"}

        rep.revisions.append(RevisionRecord(
            ts=time.time(),
            kind=kind,
            section_name=section_name,
            new_body=new_body,
            new_source_ids=new_source_ids,
            after=after,
            reason=reason,
        ))
        self._persist(rep)
        return {
            "ok": True,
            "report_id": report_id,
            "kind": kind,
            "section_name": section_name,
        }

    # ── publish ────────────────────────────────────────────────────────

    def publish(
        self,
        report_id: str,
        target_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        rep = self.reports.get(report_id)
        if not rep:
            return {"ok": False, "reason": f"unknown report_id {report_id!r}"}
        if rep.state != "draft":
            return {"ok": False, "reason": f"only draft state can be published; got {rep.state!r}"}

        # Resolve path. Restrict to within output_dir unless an absolute
        # target_path was supplied AND it's inside output_dir.
        if target_path:
            p = Path(target_path)
            if not p.is_absolute():
                p = self.output_dir / p
            try:
                p.resolve().relative_to(self.output_dir.resolve())
            except ValueError:
                return {
                    "ok": False,
                    "reason": "target_path resolves outside AGENT_WORKSPACE/reports/",
                }
            out_path = p
        else:
            slug = _slugify(rep.title)
            stamp = datetime.utcfromtimestamp(rep.drafted_at).strftime("%Y-%m-%d")
            out_path = self.output_dir / f"{stamp}_{slug}.md"
            # Avoid overwriting on collision.
            if out_path.exists():
                out_path = self.output_dir / f"{stamp}_{slug}_{report_id[-6:]}.md"

        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            out_path.write_text(self.render_markdown(rep), encoding="utf-8")
        except Exception as e:
            return {"ok": False, "reason": f"write failed: {e}"}

        rep.state = "published"
        rep.published_at = time.time()
        rep.output_path = str(out_path)
        self._persist(rep)
        return {
            "ok": True,
            "report_id": report_id,
            "output_path": str(out_path),
            "state": rep.state,
        }

    @staticmethod
    def render_markdown(rep: Report) -> str:
        """Render a Report to markdown."""
        lines = [f"# {rep.title}", ""]
        lines.append(f"_Brief: {rep.brief}_")
        lines.append("")
        if rep.state == "retracted":
            lines.insert(2, f"**RETRACTED** — {rep.retraction_reason or '(no reason)'}")
            lines.insert(3, "")
        for sec in rep.sections:
            lines.append(f"## {sec.name}")
            if sec.body:
                lines.append("")
                lines.append(sec.body)
            if sec.source_ids:
                lines.append("")
                lines.append(f"_Sources: {', '.join(sec.source_ids)}_")
            lines.append("")
        if rep.sources:
            lines.append("## Bibliography")
            lines.append("")
            for src in rep.sources:
                ref = src.uri or "(no uri)"
                lines.append(
                    f"- `{src.source_id}` [{src.source_type}] {ref} "
                    f"— confidence {src.source_confidence:.2f}"
                )
            lines.append("")
        lines.append("---")
        ts = datetime.utcfromtimestamp(rep.published_at or rep.drafted_at).isoformat()
        lines.append(f"_report_id={rep.report_id} state={rep.state} ts={ts}_")
        return "\n".join(lines) + "\n"

    # ── retract ────────────────────────────────────────────────────────

    def retract(self, report_id: str, reason: str) -> Dict[str, Any]:
        rep = self.reports.get(report_id)
        if not rep:
            return {"ok": False, "reason": f"unknown report_id {report_id!r}"}
        if rep.state != "published":
            return {"ok": False, "reason": f"only published can be retracted; got {rep.state!r}"}
        if reason not in VALID_RETRACT_REASONS:
            return {
                "ok": False,
                "reason": f"invalid retraction reason {reason!r} "
                          f"(must be one of {sorted(VALID_RETRACT_REASONS)})",
            }
        rep.state = "retracted"
        rep.retracted_at = time.time()
        rep.retraction_reason = reason

        # Rewrite the file with the retracted header so anyone reading
        # the file sees the retraction.
        if rep.output_path:
            try:
                Path(rep.output_path).write_text(
                    self.render_markdown(rep), encoding="utf-8",
                )
            except Exception:
                pass

        self._persist(rep)
        return {"ok": True, "report_id": report_id, "state": rep.state}

    # ── reflect ────────────────────────────────────────────────────────

    def reflect(
        self,
        report_id: str,
        fit: bool = True,
        notes: str = "",
        actual_outcome: Optional[float] = None,
    ) -> Dict[str, Any]:
        rep = self.reports.get(report_id)
        if not rep:
            return {"ok": False, "reason": f"unknown report_id {report_id!r}"}
        if rep.state not in ("published", "retracted"):
            return {"ok": False, "reason": f"only published/retracted can be reflected on; got {rep.state!r}"}
        rep.reflection = {
            "fit": bool(fit),
            "notes": (notes or "").strip(),
            "actual_outcome": (
                max(0.0, min(1.0, float(actual_outcome)))
                if actual_outcome is not None else None
            ),
            "ts": time.time(),
        }
        self._persist(rep)
        return {"ok": True, "report_id": report_id, "reflection": rep.reflection}

    # ── Status / queries ───────────────────────────────────────────────

    def report_status(self, report_id: str) -> Dict[str, Any]:
        rep = self.reports.get(report_id)
        if not rep:
            return {"ok": False, "reason": f"unknown report_id {report_id!r}"}
        sigs = compute_report_fidelity_signals(rep)
        return {
            "ok": True,
            "report_id": report_id,
            "title": rep.title,
            "state": rep.state,
            "mode_at_creation": rep.mode_at_creation,
            "section_count": len(rep.sections),
            "source_count": len(rep.sources),
            "revision_count": len(rep.revisions),
            "has_reflection": rep.reflection is not None,
            "output_path": rep.output_path,
            "fidelity_signals": sigs,
        }

    def list_reports(self, state: Optional[str] = None) -> List[Dict[str, Any]]:
        out = []
        for rid, rep in self.reports.items():
            if state and rep.state != state:
                continue
            out.append({
                "report_id": rid,
                "title": rep.title[:80],
                "state": rep.state,
                "mode": rep.mode_at_creation,
                "section_count": len(rep.sections),
                "drafted_at": rep.drafted_at,
                "published_at": rep.published_at,
            })
        return sorted(
            out, key=lambda x: x.get("published_at") or x["drafted_at"], reverse=True,
        )


# ── CLI ──────────────────────────────────────────────────────────────────


def _cli() -> int:
    parser = argparse.ArgumentParser(prog="report-generation", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_l = sub.add_parser("list", help="List reports")
    p_l.add_argument("--state", choices=list(VALID_STATES), default=None)

    p_s = sub.add_parser("status", help="Show report status + fidelity signals")
    p_s.add_argument("report_id")

    p_r = sub.add_parser("retract", help="Retract a published report")
    p_r.add_argument("report_id")
    p_r.add_argument(
        "--reason", choices=list(VALID_RETRACT_REASONS), required=True,
    )

    p_pub = sub.add_parser("publish", help="Publish a draft")
    p_pub.add_argument("report_id")
    p_pub.add_argument("--path", default=None)

    args = parser.parse_args()
    r = Reporter()

    def _emit(obj: Any) -> None:
        print(json.dumps(obj, indent=2, default=str))

    if args.cmd == "list":
        _emit(r.list_reports(state=args.state))
    elif args.cmd == "status":
        _emit(r.report_status(args.report_id))
    elif args.cmd == "retract":
        _emit(r.retract(args.report_id, reason=args.reason))
    elif args.cmd == "publish":
        _emit(r.publish(args.report_id, target_path=args.path))
    else:
        parser.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
