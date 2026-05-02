#!/usr/bin/env python3
"""
skills/verify_build.py — Build Verification Gate

Hard verification for mechanism builds.
Returns PASS only when ALL checks pass.
Returns FAIL with specific reasons on any failure.

Measurement standard (per industry tools: radon, cloc, pygount):
  - Lines of code = ALL non-blank, non-comment lines (docstrings COUNT as code)
  - Tests = pytest-discoverable in brain/tests/ directory (standard location)
  - Citations = academic references anywhere in the mechanism file

Usage: python3 skills/verify_build.py <MechanismName>
"""
from __future__ import print_function
import sys, re, json, os
from pathlib import Path

WORKSPACE = Path(os.environ.get("AGENT_WORKSPACE",
                                str(Path(__file__).resolve().parent.parent)))


def find_mechanism(name):
    """
    Find a mechanism file by class name.
    Priority: direct-named file (ClassName.py) first, then FoundationalNNN files.
    This ensures clean-named files take precedence over legacy numbered files.
    """
    candidates = []
    for region in ["mechanisms"]:
        for f in WORKSPACE.glob(f"brain/{region}/**/*.py"):
            if "__init__" in str(f) or f.name.startswith("test_"):
                continue
            try:
                content = f.read_text()
                # Match "class ClassName(" with any whitespace between name and paren
                if re.search(rf"class {re.escape(name)}\s*[:(]", content):
                    candidates.append(f)
            except Exception:
                pass

    if not candidates:
        return None

    # Prefer direct-named file (ClassName.py) over FoundationalNNN.py
    for f in candidates:
        if f.stem == name:
            return f
    return candidates[0]


def find_test_file(name):
    """Find the standard pytest test file for a mechanism in brain/tests/.

    Lookup order:
      1. CamelCase: brain/tests/test_<ClassName>.py (project convention)
      2. snake_case: brain/tests/test_<class_name>.py (pytest standard)

    Snake-case conversion:
      VitalCoreRegulator    -> test_vital_core_regulator.py
      CRHStressDispatcher   -> test_crh_stress_dispatcher.py
    """
    # CamelCase first
    cc = WORKSPACE / "brain" / "tests" / f"test_{name}.py"
    if cc.exists():
        return cc

    # snake_case fallback
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    snake_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    test_path = WORKSPACE / "brain" / "tests" / f"test_{snake_name}.py"
    if test_path.exists():
        return test_path
    return None


def count_code_lines(filepath):
    """
    Standard LOC counting (radon/cloc/pygount standard):
    Count all non-blank, non-comment lines.
    Docstrings ARE counted as implementation code.
    Only blank lines and pure comment-only lines (#) are excluded.
    """
    content = filepath.read_text()
    lines = content.split('\n')
    code_lines = 0
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            code_lines += 1
    return code_lines


def count_citations(filepath):
    """
    Count academic citations anywhere in the mechanism file.
    Looks for bracketed references: [Author Year, Journal info...]
    Matches any bracket containing a capitalized name + 4-digit year (1900-2099).
    Excludes Python dict/key refs like ["key_name"] which start with lowercase.
    """
    content = filepath.read_text()

    # [Author Year, Journal info...] — capitalized name, year, exclude dict keys
    citations = len(re.findall(
        r'\[(?:[A-Z][^\]]{3,50}?(?:19|20)\d{2}[^\]]*)\]',
        content
    ))
    return citations


def count_behavioral_tests(filepath):
    """
    Count behavioral tests: primary location is brain/tests/test_<mechanism>.py
    (standard pytest convention). Also checks for inline tests in the mechanism file.
    """
    name = filepath.stem  # e.g. "CRHStressDispatcher" or "OrexinWakePromoter"

    total_tests = 0

    # Check the standard test file location (primary)
    test_file = find_test_file(name)
    if test_file:
        try:
            content = test_file.read_text()
            test_methods = len(re.findall(r'def test_\w+\(', content))
            test_classes = len(re.findall(r'class Test\w+', content))
            total_tests += max(test_methods, test_classes)
        except Exception:
            pass

    # Also check for inline tests in the mechanism file (secondary)
    try:
        content = filepath.read_text()
        inline_test_methods = len(re.findall(r'def test_\w+\(', content))
        inline_test_classes = len(re.findall(r'class Test\w+', content))
        total_tests += max(inline_test_methods, inline_test_classes)
    except Exception:
        pass

    return total_tests


def main(name):
    reasons = []

    f = find_mechanism(name)
    if not f:
        reasons.append("file_not_found")
        print(f"FAIL: {name} | reasons: {reasons} | lines=0 citations=0 tests=0")
        return False

    lines = count_code_lines(f)
    citations = count_citations(f)
    tests = count_behavioral_tests(f)

    if lines < 200:
        reasons.append("lines_under_200")
    if citations < 3:
        reasons.append("not_citation_grounded")
    if tests < 1:
        reasons.append("no_behavioral_tests_only_imports")

    if reasons:
        print(f"FAIL: {name} | reasons: {reasons} | lines={lines} citations={citations} tests={tests}")
        return False
    else:
        print(f"PASS: {name} | lines={lines} citations={citations} tests={tests}")
        return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 skills/verify_build.py <MechanismName>")
        sys.exit(1)
    success = main(sys.argv[1])
    sys.exit(0 if success else 1)