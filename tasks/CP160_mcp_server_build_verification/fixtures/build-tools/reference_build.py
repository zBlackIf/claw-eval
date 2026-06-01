#!/usr/bin/env python3
"""Reference build - generates reference artifacts using legacy toolchain."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def reference_build(project_dir: str, config: str = "Release") -> dict:
    """Run reference (legacy) build generation for comparison.

    Args:
        project_dir: Path to the project root containing legacy_defs/.
        config: Build configuration (Release/Debug). Default: Release.

    Returns:
        dict with keys: success (bool), artifacts (list[str]), errors (list[str])
    """
    project_path = Path(project_dir)
    if not project_path.exists():
        return {"success": False, "artifacts": [], "errors": [f"Project dir not found: {project_dir}"]}

    legacy_dir = project_path / "legacy_defs"
    if not legacy_dir.exists():
        return {"success": False, "artifacts": [], "errors": ["No legacy_defs/ directory found"]}

    output_dir = project_path / "reference_output" / config
    output_dir.mkdir(parents=True, exist_ok=True)

    artifacts = []
    errors = []

    for def_file in sorted(legacy_dir.glob("*.json")):
        try:
            spec = json.loads(def_file.read_text())
            target_name = spec.get("target", def_file.stem)
            artifact_path = output_dir / f"{target_name}.artifact"
            artifact_path.write_text(json.dumps({
                "target": target_name,
                "config": config,
                "sources": spec.get("sources", []),
                "dependencies": spec.get("dependencies", []),
                "flags": spec.get("flags", []),
            }, indent=2))
            artifacts.append(str(artifact_path))
        except Exception as e:
            errors.append(f"Failed to process {def_file.name}: {e}")

    return {
        "success": len(errors) == 0,
        "artifacts": artifacts,
        "errors": errors,
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "artifacts": [], "errors": ["Usage: reference_build.py <project_dir> [config]"]}))
        sys.exit(1)

    project_dir = sys.argv[1]
    config = sys.argv[2] if len(sys.argv) > 2 else "Release"
    result = reference_build(project_dir, config)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
