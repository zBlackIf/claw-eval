"""Hidden verifier for CP85 — Python module CLI split."""
from __future__ import annotations

import json
import re
from pathlib import Path


TOOL_FUNCTIONS = {
    "extract_tool": {
        "function": "extract_skill_metadata",
        "name_hints": [r"extract", r"metadata"],
        "arg_hints": [r"skill[_-]?path", r"SKILL\.md"],
    },
    "permissions_tool": {
        "function": "analyze_skill_permissions",
        "name_hints": [r"permission", r"risk", r"analy[sz]e"],
        "arg_hints": [r"permission", r"risk"],
    },
    "report_tool": {
        "function": "generate_report",
        "name_hints": [r"report"],
        "arg_hints": [r"format", r"json", r"text"],
    },
    "compare_tool": {
        "function": "compare_skills",
        "name_hints": [r"compare", r"diff"],
        "arg_hints": [r"skill[_-]?[ab]", r"two", r"2"],
    },
}


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _tool_scripts(tools_dir: Path) -> list[Path]:
    if not tools_dir.is_dir():
        return []
    return sorted(
        p for p in tools_dir.rglob("*.py")
        if p.is_file() and p.name != "__init__.py" and "__pycache__" not in p.parts
    )


def _script_cli_score(content: str) -> float:
    has_argparse = "argparse" in content or "ArgumentParser" in content
    has_main = "__name__" in content and "__main__" in content
    has_entry = bool(re.search(r"def\s+main\s*\(", content)) or "sys.argv" in content
    if has_argparse and (has_main or has_entry):
        return 1.0
    if has_argparse or has_main or has_entry:
        return 0.5
    return 0.0


def _classify_script(path: Path, content: str) -> set[str]:
    lower = content.lower()
    name_lower = path.name.lower()
    matched: set[str] = set()
    for key, spec in TOOL_FUNCTIONS.items():
        if spec["function"] in content:
            matched.add(key)
            continue
        if any(re.search(pat, name_lower) for pat in spec["name_hints"]) and any(
            re.search(pat, lower) for pat in spec["arg_hints"]
        ):
            matched.add(key)
    return matched


def _original_score(ws: Path) -> float:
    candidates = [ws / "skill_analyzer.py", ws / "fixtures" / "skill_analyzer.py"]
    expected = ["extract_skill_metadata", "analyze_skill_permissions", "generate_report", "compare_skills"]
    best = 0.0
    for p in candidates:
        c = _read(p)
        if not c:
            continue
        preserved = sum(1 for f in expected if f"def {f}" in c)
        best = max(best, preserved / len(expected))
    return round(best, 2)


def grade_workspace(ws: Path) -> dict:
    tools_dir = ws / "tools"
    components = {k: 0.0 for k in [
        "tools_dir_exists", "extract_tool", "permissions_tool",
        "report_tool", "compare_tool", "imports_original",
        "original_unchanged",
    ]}

    scripts = _tool_scripts(tools_dir)
    if tools_dir.is_dir():
        components["tools_dir_exists"] = 1.0 if (tools_dir / "__init__.py").exists() else 0.7

    import_hits = 0
    for script in scripts:
        content = _read(script)
        if not content.strip():
            continue
        cli_score = _script_cli_score(content)
        matched = _classify_script(script, content)
        if matched:
            if "skill_analyzer" in content:
                import_hits += 1
        for key in matched:
            components[key] = max(components[key], cli_score)

    covered = [k for k in TOOL_FUNCTIONS if components[k] > 0]
    components["imports_original"] = round(import_hits / max(len(covered), 1), 2)
    components["original_unchanged"] = _original_score(ws)

    weights = {
        "tools_dir_exists": 0.10,
        "extract_tool": 0.15,
        "permissions_tool": 0.15,
        "report_tool": 0.15,
        "compare_tool": 0.15,
        "imports_original": 0.15,
        "original_unchanged": 0.15,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "scripts_seen": [str(p.relative_to(ws)) for p in scripts],
    }


def main():
    print(json.dumps(grade_workspace(Path("/workspace")), ensure_ascii=False))


if __name__ == "__main__":
    main()
