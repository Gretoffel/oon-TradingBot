#!/usr/bin/env python3
"""
Test runner that executes pytest and saves results.

Usage:
    python tests/run_tests.py              # run ALL tests  -> tests/result/
    python tests/run_tests.py core         # run core tests -> tests/core/result/
    python tests/run_tests.py services     # run services   -> tests/services/result/
    python tests/run_tests.py trading      # run trading    -> tests/trading/result/
    python tests/run_tests.py ai_providers # run ai_provid  -> tests/ai_providers/result/

Output file naming: result_YYYY-M-D_vN.txt
  - Date uses non-padded month/day to match the requested format.
  - Version counter (v0, v1, v2, ...) increments per day.
"""

import os
import re
import subprocess
import sys
from datetime import datetime


def get_next_version(result_dir, date_prefix):
    """Find the next available version number for today."""
    if not os.path.isdir(result_dir):
        return 0
    existing = [f for f in os.listdir(result_dir) if f.startswith(date_prefix)]
    if not existing:
        return 0
    versions = []
    for f in existing:
        match = re.search(r'_v(\d+)', f)
        if match:
            versions.append(int(match.group(1)))
    return max(versions) + 1 if versions else 0


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Determine module scope
    module = sys.argv[1] if len(sys.argv) > 1 else None

    if module:
        test_path = os.path.join("tests", module)
        result_dir = os.path.join(project_root, "tests", module, "result")
        label = module
    else:
        test_path = "tests/"
        result_dir = os.path.join(project_root, "tests", "result")
        label = "all"

    os.makedirs(result_dir, exist_ok=True)

    now = datetime.now()
    date_str = f"{now.year}-{now.month}-{now.day}"
    date_prefix = f"result_{date_str}_v"
    version = get_next_version(result_dir, date_prefix)
    filename = f"result_{date_str}_v{version}.txt"
    filepath = os.path.join(result_dir, filename)

    print(f"Running [{label}] tests... Output -> {filepath}")

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "--tb=short", test_path],
        capture_output=True,
        text=True,
        cwd=project_root,
    )

    output = result.stdout + "\n" + result.stderr

    report_lines = [
        f"Test Results: {filename}",
        f"Scope: {label}",
        f"Date: {now.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Exit Code: {result.returncode}",
        "=" * 70,
        "",
        output,
    ]
    report = "\n".join(report_lines)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)

    print(output)
    print(f"\nResults saved to: {filepath}")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
