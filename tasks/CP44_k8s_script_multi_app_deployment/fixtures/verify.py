#!/usr/bin/env python3
"""In-container verifier for CP44_k8s_script_multi_app_deployment.

Ports the original automated_score() to a script that runs under
env_snapshot_commands. Emits one JSON line with per-component scores plus
overall_score = mean(components).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path("/workspace")


def automated_score(workspace: Path) -> dict[str, float]:
    scores = {}

    script_path = workspace / "scripts" / "prevent_app_basic_03b_002.sh"
    if not script_path.exists():
        candidates = [
            f
            for f in workspace.rglob("prevent_app_basic_03b_002.sh")
            if "fixtures" not in f.parts
        ]
        script_path = candidates[0] if candidates else script_path

    if not script_path.exists():
        return {
            "config_sourced": 0.0,
            "app_switch_logic": 0.0,
            "deploy_type_handled": 0.0,
            "pattern_followed": 0.0,
            "syntax_valid": 0.0,
        }

    content = script_path.read_text(encoding="utf-8", errors="ignore")

    scores["config_sourced"] = 1.0 if re.search(r"(source|\.)\s+.*config\.conf", content) else 0.0

    has_app_switch = (
        ("halo" in content and "dify" in content)
        or bool(re.search(r"current_app|select_app|case\s+.*app", content))
    )
    scores["app_switch_logic"] = 1.0 if has_app_switch else 0.0

    lower = content.lower()
    handles_k8s = "app_k8s" in content or "k8s" in lower or "kubernetes" in lower
    handles_docker = "docker" in lower or re.search(r"else\s+.*docker|check_docker", content, re.S)
    scores["deploy_type_handled"] = 1.0 if (handles_k8s and handles_docker) else 0.0

    pattern_elements = [
        r"source\s+.*common_utils\.sh",
        r"log_file=",
        r"log_info|log_error",
        r"init_log",
        r"main\s*\(\)",
    ]
    pattern_score = sum(1 for p in pattern_elements if re.search(p, content))
    scores["pattern_followed"] = min(pattern_score / 3.0, 1.0)

    try:
        proc = subprocess.run(
            ["bash", "-n", str(script_path)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        syntax_ok = proc.returncode == 0
    except Exception:
        syntax_ok = False
    scores["syntax_valid"] = 1.0 if ("#!/bin/bash" in content and syntax_ok) else 0.0

    return scores


def main() -> dict:
    try:
        scores = automated_score(WORKSPACE)
    except Exception as exc:  # noqa: BLE001
        return {"scores": {}, "overall_score": 0.0, "error": f"{type(exc).__name__}: {exc}"}
    numeric = [float(v) for v in scores.values() if isinstance(v, (int, float))]
    overall = sum(numeric) / len(numeric) if numeric else 0.0
    return {"scores": scores, "overall_score": round(overall, 4)}


if __name__ == "__main__":
    sys.stdout.write(json.dumps(main(), ensure_ascii=False) + "\n")
