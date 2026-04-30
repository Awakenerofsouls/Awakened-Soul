#!/usr/bin/env python3
"""
migrate_outputs.py — one-shot migration of mechanism files from Claude
Cowork outputs scratchpad into the awakened-soul-repo.

Reads the `layer="..."` keyword in each module file's __init__ to decide
which subfolder of brain/ to drop it in. Test files always go to
brain/tests/.

Usage:
    cd ~/awakened-soul-repo
    python3 migrate_outputs.py [--dry-run] [--force]

By default, will NOT overwrite files that already exist in the repo —
prints "SKIP exists" instead. Pass --force to overwrite.

By default, moves all batches: batch_10 + batch_11_subcortical + batch_12_neocortical.
The agent-built files have been audited and citation-fixed.

Multi-line citations are auto-collapsed into single lines during copy
(verify_build regex requires single-line citations). This fix runs on
every copy and is safe — it only affects whitespace inside `[...]` blocks
containing a year.
"""

import re
import shutil
import sys
from pathlib import Path
from typing import Optional

# Citation auto-fix: collapse multi-line [Author Year, ...] citations
# onto a single line so they pass the verify_build regex
# `[A-Z][^\]]{3,50}?(?:19|20)\d{2}[^\]]*]`. Multi-line citations were
# the primary source of FAIL on regex compliance.
_MULTILINE_CITE_RE = re.compile(
    r"\[([^\[\]]*?(?:19|20)\d{2}[^\[\]]*?)\]",
    re.DOTALL,
)


def _collapse_citation(match: "re.Match") -> str:
    inner = match.group(1)
    # Replace any whitespace block (including newlines) with a single space
    collapsed = re.sub(r"\s+", " ", inner).strip()
    return f"[{collapsed}]"


def normalize_citations(text: str) -> str:
    """Collapse multi-line citations onto one line per occurrence.

    Multi-line citations break the verify_build single-line regex.
    This is safe: it only affects the contents of `[...]` brackets that
    contain a 19xx/20xx year, and merely removes newlines + extra
    whitespace.
    """
    return _MULTILINE_CITE_RE.sub(_collapse_citation, text)

OUTPUTS_ROOT = Path.home() / "Library/Application Support/Claude/local-agent-mode-sessions"
REPO_BRAIN = Path.home() / "awakened-soul-repo" / "brain"

# All audited batches. Subagent files have been citation-checked + fixed,
# six were rewritten by Claude after the audit (PVN, ArcuateAgRP, SNc, STN,
# DLS, DMS in batch_11_subcortical). Six in batch_12 were Claude-built.
ALL_BATCHES = [
    "batch_10",
    "batch_11_subcortical",
    "batch_12_neocortical",
    "batch_13_integration",
    "batch_14_foundational",
]

LAYER_RE = re.compile(r'layer\s*=\s*["\']([a-z_]+)["\']')


def find_outputs_dir() -> Path:
    """Locate the most recent Claude Cowork outputs/ folder."""
    if not OUTPUTS_ROOT.exists():
        sys.exit(f"Cowork outputs root not found: {OUTPUTS_ROOT}")
    candidates = []
    for session_dir in OUTPUTS_ROOT.glob("*/"):
        for sub in session_dir.glob("*/"):
            for inner in sub.glob("*/outputs"):
                if inner.is_dir():
                    candidates.append(inner)
    if not candidates:
        sys.exit("No outputs/ folder found under Cowork sessions.")
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def detect_layer(file_path: Path) -> Optional[str]:
    """Read the file's content and find the layer="..." string."""
    try:
        text = file_path.read_text(encoding="utf-8")
    except Exception:
        return None
    m = LAYER_RE.search(text)
    return m.group(1) if m else None


def is_test_file(file_path: Path) -> bool:
    return file_path.name.startswith("test_") and file_path.name.endswith(".py")


def migrate(outputs_dir: Path, dry_run: bool = False,
              force: bool = False) -> None:
    moved = 0
    skipped_exists = 0
    skipped_unknown_layer = 0
    failed = 0

    for batch in ALL_BATCHES:
        batch_dir = outputs_dir / batch
        if not batch_dir.exists():
            print(f"[SKIP batch missing] {batch}")
            continue

        for file_path in sorted(batch_dir.glob("*.py")):
            if is_test_file(file_path):
                target_dir = REPO_BRAIN / "tests"
            else:
                layer = detect_layer(file_path)
                if not layer:
                    print(f"[SKIP no layer=] {file_path.name}")
                    skipped_unknown_layer += 1
                    continue
                target_dir = REPO_BRAIN / layer

            target = target_dir / file_path.name

            if target.exists() and not force:
                print(f"[SKIP exists] {target.relative_to(REPO_BRAIN.parent)}")
                skipped_exists += 1
                continue

            target_dir.mkdir(parents=True, exist_ok=True)

            if dry_run:
                print(f"[DRY] {file_path.name} -> {target.relative_to(REPO_BRAIN.parent)}")
            else:
                try:
                    # Read source, normalize multi-line citations, write target
                    src_text = file_path.read_text(encoding="utf-8")
                    fixed_text = normalize_citations(src_text)
                    target.write_text(fixed_text, encoding="utf-8")
                    note = " (citations normalized)" if fixed_text != src_text else ""
                    print(f"[MOVED] {file_path.name} -> {target.relative_to(REPO_BRAIN.parent)}{note}")
                    moved += 1
                except Exception as e:
                    print(f"[FAIL]  {file_path.name}: {e}")
                    failed += 1

    print()
    print("=" * 60)
    print(f"Moved:                  {moved}")
    print(f"Skipped (already exist): {skipped_exists}")
    print(f"Skipped (no layer=):    {skipped_unknown_layer}")
    print(f"Failed:                 {failed}")
    if dry_run:
        print("(dry-run — no files actually copied)")
    elif skipped_exists > 0:
        print()
        print("To overwrite already-existing files (e.g. apply citation"
              " normalization to ones copied earlier without it),"
              " re-run with --force.")


def main() -> None:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    force = "--force" in args

    outputs_dir = find_outputs_dir()
    print(f"Outputs dir: {outputs_dir}")
    print(f"Repo brain:  {REPO_BRAIN}")
    print(f"Mode:        dry_run={dry_run}, force={force}")
    print()

    if not REPO_BRAIN.exists():
        sys.exit(f"Repo brain folder missing: {REPO_BRAIN}")

    migrate(outputs_dir, dry_run=dry_run, force=force)


if __name__ == "__main__":
    main()
