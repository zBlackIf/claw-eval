"""Hidden verifier for CP182 — Vue 3 Form Change Runner Conversion.

Checks that change-runner-legacy.js (Vue 2 mixin with bugs) was properly
converted to a standalone ES module with:
1. No eval() usage — replaced with new Function()
2. Separate caches for string vs function keys (Map + WeakMap)
3. Cache size limit to prevent memory leaks
4. Explicit context parameter instead of `this`
5. Proper error handling (try/catch with console.warn)
6. No uni-app conditional compilation (#ifdef / #endif)
7. Correct exports (createChangeContext, resolveChangeHandler)
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_change_runner(ws: Path) -> Path | None:
    """Find the converted change-runner module."""
    candidates = [
        ws / "cm-form-designer-h5" / "plugin" / "utils" / "change-runner.js",
        ws / "cm-form-designer-h5" / "plugin" / "utils" / "changeRunner.js",
        ws / "cm-form-designer-h5" / "plugin" / "utils" / "change-runner.ts",
        ws / "cm-form-designer-h5" / "plugin" / "utils" / "changeRunner.ts",
        ws / "cm-form-designer-h5" / "src" / "utils" / "change-runner.js",
        ws / "cm-form-designer-h5" / "src" / "utils" / "changeRunner.js",
        ws / "cm-form-designer-h5" / "src" / "composables" / "useChangeRunner.js",
        ws / "cm-form-designer-h5" / "src" / "composables" / "useChangeRunner.ts",
    ]
    for c in candidates:
        if c.exists():
            return c
    # Fallback: glob for any file containing "change" and "runner"
    for pattern in ["**/change-runner*", "**/changeRunner*", "**/useChangeRunner*"]:
        found = list((ws / "cm-form-designer-h5").rglob(pattern))
        js_ts = [f for f in found if f.suffix in (".js", ".ts") and "legacy" not in f.name and "node_modules" not in str(f)]
        if js_ts:
            return js_ts[0]
    return None


def grade_workspace(ws: Path) -> dict:
    components = {k: 0.0 for k in [
        "no_eval",
        "separate_caches",
        "cache_size_limit",
        "explicit_context",
        "error_handling",
        "no_uniapp_directives",
        "correct_exports",
    ]}

    runner_file = _find_change_runner(ws)
    if not runner_file:
        return {
            "overall_score": 0.0,
            "components": components,
            "weights": _weights(),
            "error": "change-runner module not found",
        }

    content = _read(runner_file)
    if not content.strip():
        return {
            "overall_score": 0.0,
            "components": components,
            "weights": _weights(),
            "error": "change-runner module is empty",
        }

    # 1. No eval() usage
    eval_matches = re.findall(r'\beval\s*\(', content)
    if not eval_matches:
        components["no_eval"] = 1.0
    else:
        components["no_eval"] = 0.0

    # 2. Separate caches: Map for strings, WeakMap for functions
    has_map = bool(re.search(r'\bnew\s+Map\s*\(', content))
    has_weakmap = bool(re.search(r'\bnew\s+WeakMap\s*\(', content))
    if has_map and has_weakmap:
        components["separate_caches"] = 1.0
    elif has_map or has_weakmap:
        # Only one cache type - partial credit if it's Map (at least won't crash)
        components["separate_caches"] = 0.4 if has_map else 0.2
    else:
        components["separate_caches"] = 0.0

    # 3. Cache size limit (any form of LRU, max size check, or .delete after threshold)
    has_size_check = bool(re.search(r'\.size\s*(?:>=|>|===|==)\s*\d+', content))
    has_max_const = bool(re.search(r'(?:MAX|LIMIT|CAP)[_A-Z]*(?:SIZE|CACHE|LIMIT)\s*[=:]\s*\d+', content, re.IGNORECASE))
    has_delete_logic = bool(re.search(r'\.delete\s*\(', content)) and has_map
    has_lru = bool(re.search(r'\bLRU|lru', content, re.IGNORECASE))
    if has_size_check or has_max_const or has_lru:
        components["cache_size_limit"] = 1.0
    elif has_delete_logic:
        components["cache_size_limit"] = 0.7
    else:
        components["cache_size_limit"] = 0.0

    # 4. Explicit context parameter (no reliance on `this` from mixin)
    has_new_function = bool(re.search(r'\bnew\s+Function\s*\(', content))
    has_context_param = bool(re.search(r'(?:context|ctx)\s*[,\)]', content))
    # Check there's no `this.form` or `this.option` pattern (mixin style)
    has_this_access = bool(re.search(r'\bthis\s*\.\s*(?:form|option|findObject|axios)', content))
    # Check for this-to-context rewriting
    has_this_replace = bool(re.search(r'replace\s*\(\s*.*this.*context', content, re.IGNORECASE))

    if has_context_param and has_new_function and not has_this_access:
        components["explicit_context"] = 1.0
    elif has_context_param and not has_this_access:
        components["explicit_context"] = 0.8
    elif has_new_function and not has_this_access:
        components["explicit_context"] = 0.6
    elif not has_this_access:
        components["explicit_context"] = 0.4
    else:
        components["explicit_context"] = 0.0

    # 5. Error handling (try/catch with console.warn)
    try_blocks = len(re.findall(r'\btry\s*\{', content))
    catch_blocks = len(re.findall(r'\bcatch\s*\(', content))
    has_warn = bool(re.search(r'console\s*\.\s*warn', content))
    if try_blocks >= 2 and catch_blocks >= 2 and has_warn:
        components["error_handling"] = 1.0
    elif try_blocks >= 1 and catch_blocks >= 1:
        components["error_handling"] = 0.6
    else:
        components["error_handling"] = 0.0

    # 6. No uni-app conditional compilation
    has_ifdef = bool(re.search(r'#ifdef|#endif|#ifndef', content))
    components["no_uniapp_directives"] = 0.0 if has_ifdef else 1.0

    # 7. Correct exports
    has_export_resolve = bool(re.search(r'export\s+(?:function|const|async\s+function)\s+resolveChangeHandler', content))
    has_export_context = bool(re.search(r'export\s+(?:function|const|async\s+function)\s+createChangeContext', content))
    has_export_run = bool(re.search(r'export\s+(?:function|const|async\s+function)\s+runFieldChange', content))
    # Also accept named exports at bottom
    if not has_export_resolve:
        has_export_resolve = bool(re.search(r'export\s*\{[^}]*resolveChangeHandler', content))
    if not has_export_context:
        has_export_context = bool(re.search(r'export\s*\{[^}]*createChangeContext', content))
    if not has_export_run:
        has_export_run = bool(re.search(r'export\s*\{[^}]*runFieldChange', content))

    export_score = sum([has_export_resolve, has_export_context, has_export_run]) / 3.0
    # Partial credit: at least resolveChangeHandler must be exported
    if has_export_resolve:
        components["correct_exports"] = max(export_score, 0.5)
    else:
        components["correct_exports"] = export_score * 0.5

    weights = _weights()
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def _weights() -> dict:
    return {
        "no_eval": 0.20,
        "separate_caches": 0.20,
        "cache_size_limit": 0.10,
        "explicit_context": 0.20,
        "error_handling": 0.10,
        "no_uniapp_directives": 0.05,
        "correct_exports": 0.15,
    }


def main():
    # Try primary path first, fallback to alternative
    ws = Path("/workspace/fixtures")
    if not (ws / "cm-form-designer-h5").exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
