#!/usr/bin/env python3
"""In-container verifier for CP40_persistent_rule_engine_implementation.

Ports the original automated_score() to a script that runs under
env_snapshot_commands. Emits one JSON line with per-component scores plus
overall_score = mean(components).
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WORKSPACE = Path("/workspace")


def _load_module(path: Path, temp_dir: Path):
    module_path = temp_dir / "rule_engine_under_test.py"
    shutil.copy2(path, module_path)
    spec = importlib.util.spec_from_file_location("rule_engine_under_test", module_path)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load rule_engine.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules.pop("rule_engine_under_test", None)
    spec.loader.exec_module(module)
    return module


def _behavior_scores(rule_engine_path: Path, config_path: Path) -> dict[str, float]:
    scores = {
        "behavior_add_persist": 0.0,
        "behavior_remove_persist": 0.0,
        "behavior_priority_sort": 0.0,
        "behavior_prompt_prefix": 0.0,
        "behavior_config_mapping": 0.0,
        "behavior_config_preserve": 0.0,
    }
    if not config_path.exists():
        return scores

    with tempfile.TemporaryDirectory() as tmp:
        temp_dir = Path(tmp)
        temp_config = temp_dir / "app_config.json"
        shutil.copy2(config_path, temp_config)
        original = json.loads(temp_config.read_text(encoding="utf-8"))
        module = _load_module(rule_engine_path, temp_dir)
        engine = module.RuleEngine(str(temp_config))

        r1 = engine.add_rule("所有回复必须使用中文", priority=10)
        r2 = engine.add_rule("每条回复开头显示当前使用的模型名称", priority=5)
        r3 = engine.add_rule("使用暗色主题", priority=1)
        ids = [getattr(r, "rule_id", None) for r in (r1, r2, r3)]
        saved = json.loads(temp_config.read_text(encoding="utf-8"))
        saved_rules = saved.get("rules", [])
        scores["behavior_add_persist"] = 1.0 if len(saved_rules) >= 3 and len(set(ids)) == 3 and all(ids) else 0.0

        active = engine.get_active_rules()
        priorities = [getattr(r, "priority", None) for r in active[:3]]
        scores["behavior_priority_sort"] = 1.0 if priorities == sorted(priorities, reverse=True) and priorities[:3] == [10, 5, 1] else 0.0

        prefix = engine.build_system_prompt_prefix()
        has_rules_header = "Operational Rules" in prefix or "规则" in prefix
        chinese_before_theme = prefix.find("中文") != -1 and prefix.find("中文") < prefix.find("暗色")
        scores["behavior_prompt_prefix"] = 1.0 if has_rules_header and chinese_before_theme else 0.5 if "中文" in prefix else 0.0

        changes = engine.apply_rules_to_config()
        changes_text = json.dumps(changes, ensure_ascii=False)
        maps_language = "zh-CN" in changes_text or "zh_cn" in changes_text.lower()
        maps_theme = "dark" in changes_text.lower() or "暗色" in changes_text
        maps_model = "model" in changes_text.lower() or "模型" in changes_text
        scores["behavior_config_mapping"] = (float(maps_language) + float(maps_theme) + float(maps_model)) / 3.0

        removed = engine.remove_rule(getattr(r3, "rule_id", ""))
        reloaded = module.RuleEngine(str(temp_config))
        remaining_ids = {getattr(r, "rule_id", None) for r in reloaded.get_active_rules()}
        scores["behavior_remove_persist"] = 1.0 if removed and getattr(r3, "rule_id", None) not in remaining_ids and len(remaining_ids) == 2 else 0.0

        final_config = json.loads(temp_config.read_text(encoding="utf-8"))
        preserved = (
            final_config.get("app") == original.get("app")
            and final_config.get("ai") == original.get("ai")
            and final_config.get("modules") == original.get("modules")
            and final_config.get("frontend") == original.get("frontend")
        )
        scores["behavior_config_preserve"] = 1.0 if preserved else 0.0
    return scores


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
            "syntax_valid": 0.0,
        }

    re_text = re_path.read_text(encoding="utf-8")
    try:
        compile(re_text, str(re_path), "exec")
        scores["syntax_valid"] = 1.0
    except SyntaxError:
        scores["syntax_valid"] = 0.0

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
    found_tests = [t for t in test_candidates if t.exists()]
    scores["test_script_exists"] = 1.0 if found_tests else 0.0
    if found_tests:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            shutil.copy2(found_tests[0], tmpdir / found_tests[0].name)
            shutil.copy2(re_path, tmpdir / "rule_engine.py")
            if (workspace / "app_config.json").exists():
                shutil.copy2(workspace / "app_config.json", tmpdir / "app_config.json")
            test_proc = subprocess.run(
                [sys.executable, found_tests[0].name],
                cwd=tmpdir,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
                check=False,
            )
        scores["test_script_runs"] = 1.0 if test_proc.returncode == 0 else 0.0
    else:
        scores["test_script_runs"] = 0.0

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

    try:
        scores.update(_behavior_scores(re_path, config_path))
    except Exception:
        for key in [
            "behavior_add_persist",
            "behavior_remove_persist",
            "behavior_priority_sort",
            "behavior_prompt_prefix",
            "behavior_config_mapping",
            "behavior_config_preserve",
        ]:
            scores[key] = 0.0

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
