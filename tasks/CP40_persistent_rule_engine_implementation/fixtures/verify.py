#!/usr/bin/env python3
"""In-container verifier for CP40_persistent_rule_engine_implementation.

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

    re_path = workspace / "rule_engine.py"
    if not re_path.exists():
        return {
            "add_rule_implemented": 0.0,
            "remove_rule_implemented": 0.0,
            "get_active_rules_implemented": 0.0,
            "build_prompt_prefix_implemented": 0.0,
            "apply_rules_implemented": 0.0,
            "rule_id_unique": 0.0,
            "priority_sorting": 0.0,
            "test_script_exists": 0.0,
            "config_preserved": 0.0,
        }

    re_text = re_path.read_text(encoding="utf-8")

    def check_method(method_name: str) -> float:
        pattern = rf"def\s+{method_name}\s*\(.*?\).*?(?=\n    def\s|\nclass\s|\Z)"
        match = re.search(pattern, re_text, re.DOTALL)
        if match:
            body = match.group(0)
            has_not_impl = "NotImplementedError" in body
            has_logic = "return" in body and not body.strip().endswith("raise NotImplementedError")
            return 1.0 if (not has_not_impl and has_logic) else 0.0
        return 0.0

    scores["add_rule_implemented"] = check_method("add_rule")
    scores["remove_rule_implemented"] = check_method("remove_rule")
    scores["get_active_rules_implemented"] = check_method("get_active_rules")
    scores["build_prompt_prefix_implemented"] = check_method("build_system_prompt_prefix")
    scores["apply_rules_implemented"] = check_method("apply_rules_to_config")

    uuid_patterns = [r"uuid", r"uuid4", r"uuid1", r"datetime.*isoformat", r"time\.time"]
    add_match = re.search(r"def\s+add_rule.*?(?=\n    def\s|\nclass\s|\Z)", re_text, re.DOTALL)
    if add_match and "NotImplementedError" not in add_match.group(0):
        scores["rule_id_unique"] = (
            1.0 if any(re.search(p, re_text, re.I) for p in uuid_patterns) else 0.0
        )
    else:
        scores["rule_id_unique"] = 0.0

    get_active_match = re.search(
        r"def\s+get_active_rules.*?(?=\n    def\s|\nclass\s|\Z)", re_text, re.DOTALL
    )
    if get_active_match:
        body = get_active_match.group(0)
        is_impl = "NotImplementedError" not in body
        has_sort = "sort" in body or "sorted" in body
        has_priority = "priority" in body
        scores["priority_sorting"] = 1.0 if (is_impl and has_sort and has_priority) else 0.0
    else:
        scores["priority_sorting"] = 0.0

    test_candidates = [
        workspace / "test_rules.py",
        workspace / "test.py",
        workspace / "test_rule_engine.py",
    ]
    scores["test_script_exists"] = 1.0 if any(t.exists() for t in test_candidates) else 0.0

    config_path = workspace / "app_config.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            app = config.get("app", {})
            modules = config.get("modules", {})
            preserved = (
                app.get("name") == "AI-GS Trading Dashboard"
                and app.get("version") == "1.5.3"
                and "thread_analysis" in modules
            )
            scores["config_preserved"] = 1.0 if preserved else 0.0
        except (json.JSONDecodeError, KeyError):
            scores["config_preserved"] = 0.0
    else:
        scores["config_preserved"] = 0.0

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
