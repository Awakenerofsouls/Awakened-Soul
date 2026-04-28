#!/usr/bin/env python3
"""
fix_brain_init.py — Fix missing human_analog and layer args in BrainMechanism subclasses.

Usage:
 python3 fix_brain_init.py /path/to/brain

Finds every super().__init__("ClassName") call that's missing human_analog and layer,
and rewrites it to super().__init__("ClassName", "human_analog", "layer").

Layer is inferred from directory name.
Human analog is derived from class name by splitting on capitals.
"""

import re
import sys
from pathlib import Path

# Map directory names to layer strings
LAYER_MAP = {
    "foundational": "foundational",
    "limbic": "limbic",
    "subcortical": "subcortical",
    "neocortical": "neocortical",
    "integration": "integration",
}

def class_name_to_human_analog(class_name: str) -> str:
    """Convert CamelCase class name to readable human analog description."""
    # Insert space before capitals that follow lowercase letters
    spaced = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', class_name)
    # Insert space before capitals that follow multiple capitals (e.g. DlPFC -> Dl PFC)
    spaced = re.sub(r'(?<=[A-Z])(?=[A-Z][a-z])', ' ', spaced)
    return spaced.lower().strip()

def fix_file(filepath: Path, layer: str) -> tuple[bool, str]:
    """
    Fix super().__init__ call in a single file.
    Returns (was_modified, reason).
    """
    content = filepath.read_text(encoding='utf-8')

    # Find class name
    class_match = re.search(r'^class\s+(\w+)\s*\(', content, re.MULTILINE)
    if not class_match:
        return False, "no class found"

    class_name = class_match.group(1)

    # Find super().__init__ call — match ones with only one string arg (name only)
    # Pattern: super().__init__("SomeName") — with optional whitespace
    # Must NOT already have a second argument
    pattern = re.compile(
        r'(super\(\)\.__init__\(\s*"' + re.escape(class_name) + r'"\s*\))',
        re.MULTILINE
    )

    match = pattern.search(content)
    if not match:
        # Check if it already has all 3 args
        full_pattern = re.compile(
            r'super\(\)\.__init__\(\s*"' + re.escape(class_name) + r'"\s*,',
            re.MULTILINE
        )
        if full_pattern.search(content):
            return False, "already has full signature"
        return False, f"no matching super().__init__ found for class {class_name}"

    human_analog = class_name_to_human_analog(class_name)
    replacement = f'super().__init__("{class_name}", "{human_analog}", "{layer}")'

    new_content = content[:match.start()] + replacement + content[match.end():]
    filepath.write_text(new_content, encoding='utf-8')
    return True, f"{class_name} -> layer={layer}"

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 fix_brain_init.py /path/to/brain")
        sys.exit(1)

    brain_dir = Path(sys.argv[1])
    if not brain_dir.exists():
        print(f"ERROR: {brain_dir} does not exist")
        sys.exit(1)

    fixed = []
    skipped = []
    errors = []

    for layer_name, layer_str in LAYER_MAP.items():
        layer_dir = brain_dir / layer_name
        if not layer_dir.exists():
            print(f"  SKIP: {layer_dir} not found")
            continue

        py_files = sorted(layer_dir.glob("*.py"))
        for filepath in py_files:
            if filepath.name.startswith("__"):
                continue
            try:
                was_fixed, reason = fix_file(filepath, layer_str)
                if was_fixed:
                    fixed.append(f"  FIXED: {filepath.name} — {reason}")
                else:
                    skipped.append(f"  skip: {filepath.name} — {reason}")
            except Exception as e:
                errors.append(f"  ERROR: {filepath.name} — {e}")

    print(f"\n=== FIXED ({len(fixed)}) ===")
    for line in fixed:
        print(line)

    print(f"\n=== SKIPPED ({len(skipped)}) ===")
    for line in skipped:
        print(line)

    if errors:
        print(f"\n=== ERRORS ({len(errors)}) ===")
        for line in errors:
            print(line)

    print(f"\nTotal: {len(fixed)} fixed, {len(skipped)} skipped, {len(errors)} errors")

if __name__ == "__main__":
    main()
