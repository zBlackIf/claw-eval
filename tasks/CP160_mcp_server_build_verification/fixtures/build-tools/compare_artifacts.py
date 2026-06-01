#!/usr/bin/env python3
"""Compare build artifacts between new and legacy toolchains."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def compare_artifacts(project_dir: str, module: str | None = None, config: str = "Release") -> dict:
    """Compare build_output vs reference_output artifacts.

    Args:
        project_dir: Path to the project root.
        module: Optional specific module/target name to compare. If None, compares all.
        config: Build configuration (Release/Debug). Default: Release.

    Returns:
        dict with keys: match (bool), total (int), matched (int), mismatched (int),
                        details (list of per-target diffs)
    """
    project_path = Path(project_dir)
    build_dir = project_path / "build_output" / config
    ref_dir = project_path / "reference_output" / config

    if not build_dir.exists():
        return {"match": False, "total": 0, "matched": 0, "mismatched": 0,
                "details": [], "error": "build_output not found - run build first"}
    if not ref_dir.exists():
        return {"match": False, "total": 0, "matched": 0, "mismatched": 0,
                "details": [], "error": "reference_output not found - run reference_build first"}

    build_artifacts = {p.stem: p for p in build_dir.glob("*.artifact")}
    ref_artifacts = {p.stem: p for p in ref_dir.glob("*.artifact")}

    if module:
        build_artifacts = {k: v for k, v in build_artifacts.items() if k == module}
        ref_artifacts = {k: v for k, v in ref_artifacts.items() if k == module}

    all_targets = sorted(set(build_artifacts.keys()) | set(ref_artifacts.keys()))
    details = []
    matched = 0
    mismatched = 0

    for target in all_targets:
        if target not in build_artifacts:
            details.append({"target": target, "status": "missing_in_build", "diffs": []})
            mismatched += 1
        elif target not in ref_artifacts:
            details.append({"target": target, "status": "missing_in_reference", "diffs": []})
            mismatched += 1
        else:
            build_data = json.loads(build_artifacts[target].read_text())
            ref_data = json.loads(ref_artifacts[target].read_text())
            diffs = []
            for key in ["sources", "dependencies", "flags"]:
                b_set = set(build_data.get(key, []))
                r_set = set(ref_data.get(key, []))
                if b_set != r_set:
                    diffs.append({
                        "field": key,
                        "only_in_build": sorted(b_set - r_set),
                        "only_in_reference": sorted(r_set - b_set),
                    })
            if diffs:
                details.append({"target": target, "status": "mismatch", "diffs": diffs})
                mismatched += 1
            else:
                details.append({"target": target, "status": "match", "diffs": []})
                matched += 1

    return {
        "match": mismatched == 0 and len(all_targets) > 0,
        "total": len(all_targets),
        "matched": matched,
        "mismatched": mismatched,
        "details": details,
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"match": False, "error": "Usage: compare_artifacts.py <project_dir> [--module name] [--config Release|Debug]"}))
        sys.exit(1)

    project_dir = sys.argv[1]
    module = None
    config = "Release"
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--module" and i + 1 < len(sys.argv):
            module = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--config" and i + 1 < len(sys.argv):
            config = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    result = compare_artifacts(project_dir, module, config)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("match") else 1)


if __name__ == "__main__":
    main()
