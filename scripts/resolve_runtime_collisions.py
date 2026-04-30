#!/usr/bin/env python3
"""
resolve_runtime_collisions.py
==============================
After importing runtime brain files into the repo, some classes collide
with existing scaffold/legacy registrations. This script finds every
collision and renames the NEWER (just-imported) file's `name=` to a
distinct value (suffix `Runtime`).

Usage: python3 scripts/resolve_runtime_collisions.py
"""
from __future__ import annotations
import re
import sys
import pkgutil
import importlib
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def find_collisions():
    sys.path.insert(0, str(REPO))
    collisions = defaultdict(list)
    for layer in ["foundational", "limbic", "subcortical",
                      "neocortical", "integration"]:
        for _, modname, ispkg in pkgutil.iter_modules([str(REPO / "brain" / layer)]):
            if ispkg or modname.startswith("_"):
                continue
            try:
                module = importlib.import_module(f"brain.{layer}.{modname}")
            except Exception:
                continue
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type)
                        and attr.__name__ != "BrainMechanism"
                        and hasattr(attr, "tick")
                        and callable(getattr(attr, "tick", None))):
                    try:
                        inst = attr()
                    except Exception:
                        continue
                    collisions[inst.name].append(
                        (layer, modname, str(REPO / "brain" / layer / f"{modname}.py"))
                    )
    return {k: v for k, v in collisions.items() if len(v) > 1}


def rename_in_file(path: Path, old_name: str, new_name: str) -> bool:
    text = path.read_text(encoding="utf-8")
    # Pattern A: positional super().__init__("X", ...)
    pat_pos = re.compile(
        r'super\(\)\.__init__\(\s*[\"\']' + re.escape(old_name) + r'[\"\']'
    )
    # Pattern B: keyword name="X"
    pat_kw = re.compile(
        r'name\s*=\s*[\"\']' + re.escape(old_name) + r'[\"\']'
    )
    # Pattern C: parameterized default — def __init__(self, name: str = "X", ...)
    pat_default = re.compile(
        r'(name\s*:\s*str\s*=\s*)[\"\']' + re.escape(old_name) + r'[\"\']'
    )
    if pat_pos.search(text):
        text = pat_pos.sub(f'super().__init__("{new_name}"', text, count=1)
    elif pat_default.search(text):
        text = pat_default.sub(rf'\1"{new_name}"', text, count=1)
    elif pat_kw.search(text):
        text = pat_kw.sub(f'name="{new_name}"', text, count=1)
    else:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def pick_winner(file_list):
    """
    Return (winner_path, losers_list). Winner is the file we keep with the
    canonical `name=`. Losers are the ones we rename.

    Heuristic: prefer the numbered scaffold (filename starts with a layer
    prefix like Foundational#, Limbic#, etc.). Otherwise prefer the file
    that is alphabetically first (deterministic).
    """
    def is_numbered(name: str) -> bool:
        prefixes = ("Foundational", "Limbic", "Subcortical",
                    "Neocortical", "Integration")
        return any(name.startswith(p) and len(name) > len(p)
                       and name[len(p)].isdigit() for p in prefixes)
    numbered = [t for t in file_list if is_numbered(t[1])]
    if numbered:
        winner = min(numbered, key=lambda t: t[1])
    else:
        winner = min(file_list, key=lambda t: t[1])
    losers = [t for t in file_list if t != winner]
    return winner, losers


def main() -> int:
    collisions = find_collisions()
    print(f"Found {len(collisions)} colliding registry names")
    n_renamed = 0
    n_failed = 0
    for name, file_list in sorted(collisions.items()):
        winner, losers = pick_winner(file_list)
        for layer, modname, path in losers:
            new_name = f"{name}_{modname}"
            if rename_in_file(Path(path), name, new_name):
                print(f"[RENAMED] {layer}/{modname}.py: {name} -> {new_name}")
                n_renamed += 1
            else:
                print(f"[FAILED]  {layer}/{modname}.py: {name} (no pattern match)")
                n_failed += 1
    print()
    print(f"Renamed: {n_renamed}")
    print(f"Failed:  {n_failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
