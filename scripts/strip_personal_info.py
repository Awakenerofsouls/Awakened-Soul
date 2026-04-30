#!/usr/bin/env python3
"""
strip_personal_info.py
========================
Idempotent re-templating pass over the entire repo. Replaces operator-specific
identity strings with the canonical template placeholders so the public push
is agent/user neutral.

Substitutions (in order — earlier rules match first):

  - "Caine YYYY" / "Caine et al." / similar neuroscience citations  → UNTOUCHED
    (these are real published authors, e.g. Harding-Halliday-Caine-Kril 2000)
  - "Caine" (as a name, word-boundary)                              → {{USER_NAME}}
  - "Mari" (as a name, word-boundary, not Marina/Mariner/etc)       → {{USER_NAME}}
  - "Nova" (as a name, word-boundary)                               → {{AGENT_NAME}}
  - "NOVA_HOME"                                                     → AGENT_HOME
  - ".nova" path component (in literals, not in domains/URLs)       → .agent
  - "nova.db"                                                       → agent.db
  - "/Users/dr.claw/..."                                            → templated $AGENT_HOME / $AGENT_WORKSPACE
  - "/USERS/CAINE/..."                                              → /Users/<youruser>/...
  - "/home/caine/..."                                               → /home/<youruser>/...

The script:
  - walks every tracked file in the repo (uses git ls-files)
  - skips binary files
  - skips files inside an opt-out list (this script itself, .git, etc.)
  - prints a summary at the end (files touched, substitutions applied)

Run:
    python3 scripts/strip_personal_info.py            # dry run (default)
    python3 scripts/strip_personal_info.py --apply    # actually rewrite files
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Files we never touch — this script itself, the README of strip rules, etc.
OPT_OUT = {
    "scripts/strip_personal_info.py",
}

# Citation pattern — Caine followed by a year (1900–2099). Used to mask citations
# before we apply the Caine→{{USER_NAME}} rule, then unmask after.
CITATION_PATTERN = re.compile(r'\bCaine\s+(?:et al\.\s+)?(?:19|20)\d{2}\b')

# Other citation forms — author lists like "Harding-Halliday-Caine-Kril 2000"
# or "Halliday Caine Kril 2000". We mask any "Caine" that's adjacent (with
# spaces or hyphens) to other capitalized author surnames followed by a year.
AUTHOR_LIST_PATTERN = re.compile(
    r'\b(?:[A-Z][a-z]+[-\s]+)+Caine(?:[-\s]+[A-Z][a-z]+)*\s+(?:19|20)\d{2}\b'
)

CITATION_TOKEN = "\x00CITATION_CAINE\x00"


def mask_citations(text: str) -> tuple[str, list[str]]:
    """Replace Caine citations with a sentinel token. Return (masked_text, originals)."""
    captured: list[str] = []

    def _replace(m: re.Match) -> str:
        captured.append(m.group(0))
        return f"{CITATION_TOKEN}{len(captured) - 1}{CITATION_TOKEN}"

    # Author-list form first (broader), then standalone "Caine YYYY"
    text = AUTHOR_LIST_PATTERN.sub(_replace, text)
    text = CITATION_PATTERN.sub(_replace, text)
    return text, captured


def unmask_citations(text: str, originals: list[str]) -> str:
    def _restore(m: re.Match) -> str:
        idx = int(m.group(1))
        return originals[idx]

    return re.sub(
        re.escape(CITATION_TOKEN) + r'(\d+)' + re.escape(CITATION_TOKEN),
        _restore,
        text,
    )


# Substitution rules applied in order. Each is (compiled_regex, replacement,
# label_for_summary).
RULES: list[tuple[re.Pattern[str], str, str]] = [
    # Names — word-boundary so we don't break "supernova", "Marina", etc.
    (re.compile(r'\bNova\b'),  "{{AGENT_NAME}}", "Nova → {{AGENT_NAME}}"),
    (re.compile(r'\bCaine\b'), "{{USER_NAME}}",  "Caine → {{USER_NAME}}"),
    (re.compile(r'\bMari\b'),  "{{USER_NAME}}",  "Mari → {{USER_NAME}}"),
    # Env var name
    (re.compile(r'\bNOVA_HOME\b'), "AGENT_HOME", "NOVA_HOME → AGENT_HOME"),
    # DB filename
    (re.compile(r'\bnova\.db\b'), "agent.db", "nova.db → agent.db"),
    # Path component .nova → .agent. Match in path-like contexts only:
    # preceded by ~, /, ", \\, or string start; bounded by `/`, `"`, end.
    (re.compile(r'(?<=["\'/\\\\])\.nova(?=[/"\'\\\\])'), ".agent",
     ".nova → .agent (path component)"),
    (re.compile(r'(?<=Path\.home\(\)\s/\s)["\']?\.nova["\']?'), '".agent"',
     'Path.home() / ".nova" → ".agent"'),
    # /Users/dr.claw → templated absolute path. Only as a hardcoded literal in code.
    # We use a placeholder substitution that's still a valid path string.
    (re.compile(r'/Users/dr\.claw/'), "/Users/<youruser>/",
     "/Users/dr.claw/ → /Users/<youruser>/"),
    # /USERS/CAINE → /Users/<youruser> (case fold)
    (re.compile(r'/USERS/CAINE/'), "/Users/<youruser>/",
     "/USERS/CAINE/ → /Users/<youruser>/"),
    # /home/caine → /home/<youruser>
    (re.compile(r'/home/caine/'), "/home/<youruser>/",
     "/home/caine/ → /home/<youruser>/"),
    (re.compile(r'/home/caine\b'), "/home/<youruser>",
     "/home/caine → /home/<youruser>"),
]


def list_tracked_files() -> list[Path]:
    out = subprocess.check_output(
        ["git", "ls-files"], cwd=REPO, text=True
    )
    return [REPO / line for line in out.splitlines() if line]


def is_text_file(path: Path) -> bool:
    """Heuristic: read 8KB, see if it decodes as utf-8 and has no NUL bytes."""
    try:
        chunk = path.read_bytes()[:8192]
    except Exception:
        return False
    if b"\x00" in chunk:
        return False
    try:
        chunk.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def process_file(path: Path, apply: bool) -> tuple[int, dict[str, int]]:
    """Process a single file. Returns (total_subs, per_rule_counts)."""
    rel = str(path.relative_to(REPO))
    if rel in OPT_OUT:
        return 0, {}
    if not is_text_file(path):
        return 0, {}

    try:
        original = path.read_text(encoding="utf-8")
    except Exception:
        return 0, {}

    text, captured = mask_citations(original)
    per_rule: dict[str, int] = {}
    for pat, repl, label in RULES:
        new_text, n = pat.subn(repl, text)
        if n:
            per_rule[label] = n
            text = new_text
    text = unmask_citations(text, captured)

    if text == original:
        return 0, {}

    total = sum(per_rule.values())
    if apply:
        path.write_text(text, encoding="utf-8")
    return total, per_rule


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="actually rewrite files (default: dry run)")
    args = ap.parse_args()

    mode = "APPLY" if args.apply else "DRY RUN (no changes written)"
    print(f"=== strip_personal_info.py — {mode} ===\n")

    files = list_tracked_files()
    print(f"Scanning {len(files)} tracked files...\n")

    files_touched = 0
    total_subs = 0
    rule_totals: dict[str, int] = {}

    for path in files:
        n, per_rule = process_file(path, apply=args.apply)
        if n:
            files_touched += 1
            total_subs += n
            for label, count in per_rule.items():
                rule_totals[label] = rule_totals.get(label, 0) + count
            rel = path.relative_to(REPO)
            summary = ", ".join(f"{k}={v}" for k, v in per_rule.items())
            print(f"  {rel}: {summary}")

    print(f"\n=== Summary ===")
    print(f"Files touched:        {files_touched}")
    print(f"Total substitutions:  {total_subs}\n")
    print("By rule:")
    for label in sorted(rule_totals, key=lambda k: -rule_totals[k]):
        print(f"  {rule_totals[label]:5d}  {label}")

    if not args.apply:
        print("\n(dry run — re-run with --apply to write changes)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
