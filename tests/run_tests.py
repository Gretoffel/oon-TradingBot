#!/usr/bin/env python3
"""
Test runner that executes pytest and saves results to tests/result/.

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
    result_dir = os.path.join(project_root, "tests", "result")
    os.makedirs(result_dir, exist_ok=True)

    now = datetime.now()
    # Non-padded format: 2026-2-11 (not 2026-02-11)
    date_str = f"{now.year}-{now.month}-{now.day}"
    date_prefix = f"result_{date_str}_v"
    version = get_next_version(result_dir, date_prefix)
    filename = f"result_{date_str}_v{version}.txt"
    filepath = os.path.join(result_dir, filename)

    print(f"Running tests... Output -> {filepath}")

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "--tb=short", "tests/"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )

    output = result.stdout + "\n" + result.stderr

    # Build report
    report_lines = [
        f"Test Results: {filename}",
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
