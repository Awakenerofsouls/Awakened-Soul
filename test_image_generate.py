#!/usr/bin/env python3
"""Test image_generate routing to imagegen/workflow"""
import subprocess, json, sys

result = subprocess.run(
    ["openclaw", "capability", "image", "generate",
     "--model", "imagegen/workflow",
     "--prompt", "cyberpunk portrait of a woman with blue neon eyes",
     "--count", "1",
     "--json"],
    capture_output=True, text=True, timeout=120
)
print("STDOUT:", result.stdout[:500])
print("STDERR:", result.stderr[:200])
print("RC:", result.returncode)