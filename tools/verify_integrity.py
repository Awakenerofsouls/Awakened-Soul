#!/usr/bin/env python3
"""
verify_integrity.py — {{AGENT_NAME}} workspace integrity check
Reads MANIFEST.sha256 from workspace root and verifies each listed file.
Exit 0: all files match. Exit non-zero: missing or tampered files.
"""

import hashlib
import sys
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent
MANIFEST_PATH = WORKSPACE / "MANIFEST.sha256"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if not MANIFEST_PATH.exists():
        print(f"[verify-integrity] MANIFEST.sha256 not found at {MANIFEST_PATH}", file=sys.stderr)
        sys.exit(1)

    lines = MANIFEST_PATH.read_text().splitlines()
    entries = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("  ", 1)
        if len(parts) != 2:
            print(f"[verify-integrity] Malformed manifest line: {line!r}", file=sys.stderr)
            sys.exit(1)
        expected_hash, rel_path = parts
        entries.append((expected_hash, rel_path))

    if not entries:
        print("[verify-integrity] Manifest is empty — nothing to verify.", file=sys.stderr)
        sys.exit(1)

    failures = []
    for expected_hash, rel_path in entries:
        fpath = WORKSPACE / rel_path
        if not fpath.exists():
            failures.append(f"MISSING: {rel_path}")
            continue
        actual_hash = sha256_file(fpath)
        if actual_hash != expected_hash:
            failures.append(f"TAMPERED: {rel_path}")

    if failures:
        print("[verify-integrity] INTEGRITY CHECK FAILED:", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        sys.exit(1)

    print(f"[verify-integrity] OK — {len(entries)} files verified.")
    sys.exit(0)


if __name__ == "__main__":
    main()
