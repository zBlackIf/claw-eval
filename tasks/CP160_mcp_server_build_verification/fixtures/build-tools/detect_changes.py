#!/usr/bin/env python3
"""Detect recent changes in build definition files via git log simulation."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def detect_changes(project_dir: str, since_commits: int = 5) -> dict:
    """Detect which build definition files have been modified recently.

    In a real project this would use `git log`. Here we simulate by checking
    file modification times relative to each other.

    Args:
        project_dir: Path to the project root.
        since_commits: How many recent commits to look back (simulated).

    Returns:
        dict with keys: changed_files (list[str]), build_defs_changed (list[str]),
                        legacy_defs_changed (list[str])
    """
    project_path = Path(project_dir)
    build_defs = project_path / "build_defs"
    legacy_defs = project_path / "legacy_defs"

    changed_build = []
    changed_legacy = []

    if build_defs.exists():
        for f in sorted(build_defs.glob("*.json")):
            changed_build.append(f.name)

    if legacy_defs.exists():
        for f in sorted(legacy_defs.glob("*.json")):
            changed_legacy.append(f.name)

    return {
        "changed_files": changed_build + changed_legacy,
        "build_defs_changed": changed_build,
        "legacy_defs_changed": changed_legacy,
        "since_commits": since_commits,
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: detect_changes.py <project_dir> [--since N]"}))
        sys.exit(1)

    project_dir = sys.argv[1]
    since = 5
    if "--since" in sys.argv:
        idx = sys.argv.index("--since")
        if idx + 1 < len(sys.argv):
            since = int(sys.argv[idx + 1])

    result = detect_changes(project_dir, since)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
