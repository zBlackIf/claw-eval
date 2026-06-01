"""Hidden verifier for CP184 — WeChat Desktop Automation Framework."""
from __future__ import annotations

import ast
import json
import os
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _is_valid_json(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _check_python_syntax(p: Path) -> bool:
    """Check if a Python file has valid syntax."""
    try:
        ast.parse(_read(p))
        return True
    except SyntaxError:
        return False


def grade_workspace(ws: Path) -> dict:
    """Grade the WeChat automation framework implementation."""
    proj = ws / "wechatproject"
    if not proj.exists():
        # Fallback: try workspace root
        proj = ws

    components = {k: 0.0 for k in [
        "config_externalized",
        "host_bridge_module",
        "main_flow_complete",
        "test_suite_created",
        "human_simulation",
    ]}

    # =========================================================================
    # 1. config.json — coordinates must NOT be hardcoded in scripts (0.20)
    # =========================================================================
    config_file = proj / "config.json"
    if config_file.exists():
        cfg = _is_valid_json(config_file)
        if cfg:
            score = 0.0
            # Must have coordinates section with x/y values
            coords = cfg.get("coordinates", cfg.get("coords", {}))
            if isinstance(coords, dict) and len(coords) >= 3:
                # At least 3 coordinate entries (search box, chat area, moments)
                has_xy = sum(1 for v in coords.values()
                             if isinstance(v, dict) and "x" in v and "y" in v)
                score += 0.4 if has_xy >= 3 else (0.2 if has_xy >= 1 else 0.0)
            # Must have target groups list
            groups = cfg.get("target_groups", cfg.get("groups", []))
            if isinstance(groups, list) and len(groups) >= 3:
                score += 0.3
            elif isinstance(groups, list) and len(groups) >= 1:
                score += 0.1
            # Must have timings/delays
            timings = cfg.get("timings", cfg.get("delays", cfg.get("timing", {})))
            if isinstance(timings, dict) and len(timings) >= 2:
                score += 0.3
            elif isinstance(timings, dict) and len(timings) >= 1:
                score += 0.1
            components["config_externalized"] = min(1.0, score)

    # =========================================================================
    # 2. host_bridge module — sandbox-to-host communication layer (0.25)
    # =========================================================================
    bridge_file = None
    for name in ["host_bridge.py", "bridge.py", "sandbox_bridge.py", "host.py"]:
        candidate = proj / name
        if candidate.exists():
            bridge_file = candidate
            break
    if not bridge_file:
        # Search recursively
        for p in proj.rglob("*bridge*.py"):
            bridge_file = p
            break

    if bridge_file and bridge_file.exists() and _check_python_syntax(bridge_file):
        content = _read(bridge_file)
        score = 0.0
        # Must use flatpak-spawn or subprocess for host communication
        if "flatpak-spawn" in content or "flatpak_spawn" in content:
            score += 0.35
        elif "subprocess" in content:
            score += 0.20
        # Must have xdotool integration (window activation)
        if "xdotool" in content:
            score += 0.25
        # Must have clipboard functions
        if ("clipboard" in content.lower() or "pyperclip" in content.lower()
                or "xclip" in content.lower()):
            score += 0.20
        # Must have mouse/keyboard functions
        if ("mouse" in content.lower() or "click" in content.lower()
                or "hotkey" in content.lower() or "key" in content.lower()):
            score += 0.20
        components["host_bridge_module"] = min(1.0, score)

    # =========================================================================
    # 3. main_flow.py — complete implementation with 3 core functions (0.25)
    # =========================================================================
    main_file = proj / "main_flow.py"
    if main_file.exists() and _check_python_syntax(main_file):
        content = _read(main_file)
        score = 0.0

        # Must NOT have NotImplementedError (i.e., functions are implemented)
        has_not_impl = "NotImplementedError" in content
        if not has_not_impl:
            score += 0.15

        # Must have bring_wechat_to_front function with real body
        if re.search(r"def\s+bring_wechat_to_front", content):
            # Check it has a real implementation (more than just raise/pass)
            func_match = re.search(
                r"def\s+bring_wechat_to_front[^:]*:(.+?)(?=\ndef\s|\Z)",
                content, re.DOTALL
            )
            if func_match:
                body = func_match.group(1)
                if len(body.strip().splitlines()) >= 3 and "raise" not in body:
                    score += 0.25
                elif "raise" not in body:
                    score += 0.10

        # Must have scrape_group_messages with iteration over groups
        if re.search(r"def\s+scrape_group_messages", content):
            func_match = re.search(
                r"def\s+scrape_group_messages[^:]*:(.+?)(?=\ndef\s|\Z)",
                content, re.DOTALL
            )
            if func_match:
                body = func_match.group(1)
                if ("for" in body or "while" in body) and "raise" not in body:
                    score += 0.30
                elif "raise" not in body and len(body.strip().splitlines()) >= 3:
                    score += 0.15

        # Must have post_to_moments function
        if re.search(r"def\s+post_to_moments", content):
            func_match = re.search(
                r"def\s+post_to_moments[^:]*:(.+?)(?=\ndef\s|\Z)",
                content, re.DOTALL
            )
            if func_match:
                body = func_match.group(1)
                if len(body.strip().splitlines()) >= 3 and "raise" not in body:
                    score += 0.20
                elif "raise" not in body:
                    score += 0.10

        # Must load config from JSON (not hardcode coordinates)
        if ("config.json" in content or "CONFIG" in content) and "json" in content:
            score += 0.10

        components["main_flow_complete"] = min(1.0, score)

    # =========================================================================
    # 4. test_automation.py — test suite with 4 test cases (0.15)
    # =========================================================================
    test_file = None
    for name in ["test_automation.py", "tests.py", "test_main.py"]:
        candidate = proj / name
        if candidate.exists():
            test_file = candidate
            break
    if not test_file:
        for p in proj.rglob("test*.py"):
            test_file = p
            break

    if test_file and test_file.exists() and _check_python_syntax(test_file):
        content = _read(test_file)
        score = 0.0
        test_count = 0

        # Count test functions/cases
        test_funcs = re.findall(r"def\s+(test_\w+)", content)
        test_count = len(test_funcs)

        # Check for dependency verification test
        if any("depend" in t.lower() or "host" in t.lower() or "install" in t.lower()
               for t in test_funcs) or "xdotool" in content:
            score += 0.25

        # Check for window activation test
        if any("window" in t.lower() or "wechat" in t.lower() or "activat" in t.lower()
               for t in test_funcs):
            score += 0.25

        # Check for clipboard test
        if any("clip" in t.lower() or "copy" in t.lower() or "paste" in t.lower()
               for t in test_funcs):
            score += 0.25

        # Check for mouse trajectory test
        if any("mouse" in t.lower() or "trajector" in t.lower() or "move" in t.lower()
               or "human" in t.lower() for t in test_funcs):
            score += 0.25

        # Minimum: at least 3 distinct test functions
        if test_count < 3:
            score *= 0.5

        components["test_suite_created"] = min(1.0, score)

    # =========================================================================
    # 5. Human-like simulation — anti-detection measures (0.15)
    # =========================================================================
    # Check across all Python files for human simulation patterns
    all_py_content = ""
    for py_file in proj.rglob("*.py"):
        all_py_content += _read(py_file) + "\n"

    if all_py_content:
        score = 0.0
        # Random delays between actions
        if "random" in all_py_content and ("sleep" in all_py_content or "delay" in all_py_content):
            score += 0.30
        # Curve/bezier mouse movement (not instant teleport)
        if any(kw in all_py_content.lower() for kw in
               ["bezier", "curve", "human_move", "humanmove", "trajectory",
                "cubic", "easing", "interpolat"]):
            score += 0.35
        elif "random" in all_py_content and "move" in all_py_content.lower():
            score += 0.15
        # Variable typing speed
        if any(kw in all_py_content.lower() for kw in
               ["type_delay", "typing_speed", "char_delay", "keystroke"]):
            score += 0.20
        elif "uniform" in all_py_content or "randint" in all_py_content:
            score += 0.10
        # No hardcoded coordinates in main_flow (should use config)
        main_content = _read(proj / "main_flow.py") if (proj / "main_flow.py").exists() else ""
        hardcoded_coords = re.findall(r"(?:move|click|position)\s*\(\s*\d{2,4}\s*,\s*\d{2,4}\s*\)", main_content)
        if len(hardcoded_coords) == 0:
            score += 0.15

        components["human_simulation"] = min(1.0, score)

    # =========================================================================
    # Compute overall score
    # =========================================================================
    weights = {
        "config_externalized": 0.20,
        "host_bridge_module": 0.25,
        "main_flow_complete": 0.25,
        "test_suite_created": 0.15,
        "human_simulation": 0.15,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    # Check /workspace/fixtures/wechatproject first, then /workspace/wechatproject
    ws = Path("/workspace/fixtures/wechatproject")
    if not ws.exists():
        ws = Path("/workspace/wechatproject")
    if not ws.exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
