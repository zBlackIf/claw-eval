#!/usr/bin/env python3
"""In-container verifier for CP44_k8s_script_multi_app_deployment.

Ports the original automated_score() to a script that runs under
env_snapshot_commands. Emits one JSON line with per-component scores plus
overall_score = mean(components).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

WORKSPACE = Path("/workspace")


def automated_score(workspace: Path) -> dict[str, float]:
    scores = {}

    script_path = workspace / "prevent_app_basic_03b_002.sh"
    if not script_path.exists():
        for f in workspace.rglob("prevent_app_basic_03b_002.sh"):
            script_path = f
            break

    if not script_path.exists():
        return {
            "config_sourced": 0.0,
            "app_switch_logic": 0.0,
            "deploy_type_handled": 0.0,
            "pattern_followed": 0.0,
            "syntax_valid": 0.0,
        }

    content = script_path.read_text(encoding="utf-8")

    scores["config_sourced"] = 1.0 if re.search(r"source\s+.*config\.conf", content) else 0.0

    has_app_switch = (
        ("halo" in content and "dify" in content)
        or bool(re.search(r"current_app|select_app|case\s+.*app", content))
    )
    scores["app_switch_logic"] = 1.0 if has_app_switch else 0.0

    has_deploy = (
        ("k8s" in content.lower() or "kubernetes" in content.lower())
        and "docker" in content.lower()
    ) or bool(re.search(r"app_k8s", content))
    scores["deploy_type_handled"] = 1.0 if has_deploy else 0.0

    pattern_elements = [
        r"source\s+.*common_utils\.sh",
        r"log_file=",
        r"log_info|log_error",
        r"init_log",
        r"main\s*\(\)",
    ]
    pattern_score = sum(1 for p in pattern_elements if re.search(p, content))
    scores["pattern_followed"] = min(pattern_score / 3.0, 1.0)

    syntax_ok = (
        content.count("then") <= content.count("fi") + 1
        and content.count("do") <= content.count("done") + 1
        and "#!/bin/bash" in content
    )
    scores["syntax_valid"] = 1.0 if syntax_ok else 0.0

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
