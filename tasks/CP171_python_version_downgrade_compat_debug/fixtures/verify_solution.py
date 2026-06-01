#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hidden verifier for CP171 — Python version downgrade compatibility debug.

Checks that the code has been properly fixed to work with Python 3.9.
Does NOT run the full GUI (no display available in sandbox), but verifies
syntax compatibility, import chain, and specific patterns.

Scoring structure (tiered hidden checks for discrimination):

  VISIBLE (public, 40%):
    - match-case removal, pipe union syntax, tomllib fix
    - These are obvious errors that any agent should catch.

  HIDDEN EASY (30%):
    - strict=True zip, importlib.resources compat, requirements basics,
      all files parseable
    - Still straightforward but not shown to agent; all decent agents pass.

  HIDDEN HARD (30%):
    - @dataclass(slots=True), @dataclass(kw_only=True), TypeAlias from typing,
      walrus in comprehension, scipy version cap, proper tomli try/except
      fallback pattern, numpy+scipy combined cap coherence
    - Subtle 3.9 compat issues only strong agents catch.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _can_parse(p: Path) -> bool:
    """Check if file can be parsed as valid Python 3.9 AST."""
    source = _read(p)
    if not source.strip():
        return False
    try:
        ast.parse(source)
        return True
    except SyntaxError:
        return False


def _check_no_match_case(source: str) -> bool:
    """Check that match-case statements have been removed.

    match-case is Python 3.10+ syntax.
    """
    lines = source.split('\n')
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('"') or stripped.startswith("'"):
            continue
        if re.match(r'^match\s+\w', stripped):
            return False
        if re.match(r'^case\s+[\w"\'._(]', stripped) and not re.match(r'^case\s*=', stripped):
            return False
    return True


def _check_no_pipe_union(source: str) -> bool:
    """Check that X|Y type union syntax (3.10+) is not used in annotations."""
    annotation_pipe = re.findall(
        r'(?::\s*[\w\[\], .]+\s*\|\s*[\w\[\], .]+|'
        r'->\s*[\w\[\], .]+\s*\|\s*[\w\[\], .]+)',
        source
    )
    for match in annotation_pipe:
        if re.match(r'^[:\-]', match.strip()):
            return False
    return True


def _check_no_tomllib(source: str) -> bool:
    """Check that tomllib (3.11+) is not imported directly without fallback."""
    lines = source.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "import tomllib" or stripped.startswith("import tomllib"):
            in_try = False
            for j in range(i - 1, max(i - 5, -1), -1):
                if lines[j].strip().startswith("try:"):
                    in_try = True
                    break
            if not in_try:
                return False
    return True


def _check_no_strict_zip(source: str) -> bool:
    """Check that zip(..., strict=True) (3.10+) is not used."""
    return "strict=True" not in source and "strict = True" not in source


def _check_no_importlib_files(source: str) -> bool:
    """Check that importlib.resources.files() usage has a 3.9 fallback."""
    if "importlib.resources.files(" not in source:
        return True
    lines = source.split('\n')
    for i, line in enumerate(lines):
        if "importlib.resources.files(" in line:
            in_try = False
            for j in range(i - 1, max(i - 10, -1), -1):
                if lines[j].strip().startswith("try:"):
                    in_try = True
                    break
            if not in_try:
                return False
    return True


def _check_no_slots_dataclass(source: str) -> bool:
    """Check that @dataclass(slots=True) (3.10+) is not used.

    The `slots` parameter was added to @dataclass in Python 3.10.
    For 3.9 compatibility, either remove it or use __slots__ manually.
    """
    pattern = r'@dataclass\([^)]*slots\s*=\s*True[^)]*\)'
    return not re.search(pattern, source)


def _check_no_kw_only_dataclass(source: str) -> bool:
    """Check that @dataclass(kw_only=True) (3.10+) is not used.

    The `kw_only` parameter was added to @dataclass in Python 3.10.
    For 3.9 compatibility, fields must be explicitly marked or pattern changed.
    """
    pattern = r'@dataclass\([^)]*kw_only\s*=\s*True[^)]*\)'
    return not re.search(pattern, source)


def _check_no_type_alias_syntax(source: str) -> bool:
    """Check that TypeAlias from typing (3.10+) is not used improperly.

    typing.TypeAlias was added in Python 3.10. For 3.9, either:
    - Use typing_extensions.TypeAlias
    - Or just use a plain assignment without the annotation
    """
    if re.search(r'from\s+typing\s+import\s+[^#\n]*TypeAlias', source):
        return False
    if re.search(r'^type\s+\w+\s*=', source, re.MULTILINE):
        return False
    return True


def _check_no_walrus_in_comprehension(source: str) -> bool:
    """Check that walrus operator (:=) is not used in list comprehension filter.

    While := works in 3.8+ generally, using it inside a comprehension
    that references the variable in the filter clause can cause subtle
    scoping issues in 3.9. The safest approach is to rewrite as a loop
    or use a different pattern.
    """
    comp_walrus = re.findall(
        r'\[.*?for\s+.*?if\s+\(?\w+\s*:=.*?\]',
        source, re.DOTALL
    )
    return len(comp_walrus) == 0


def _check_tomli_fallback_pattern(source: str) -> bool:
    """Check that tomli import uses proper try/except fallback pattern.

    The ideal pattern for 3.9 compat is:
        try:
            import tomllib
        except ModuleNotFoundError:
            import tomli as tomllib

    Or simply `import tomli` without trying tomllib at all.
    This checks that the fallback is properly structured (not just that
    tomllib is absent).
    """
    # If no toml-related import at all, not applicable
    if "toml" not in source:
        return True

    # Best: uses try/except with tomllib -> tomli fallback
    if re.search(
        r'try:\s*\n\s*import\s+tomllib.*?\n\s*except.*?:\s*\n\s*import\s+tomli',
        source, re.DOTALL
    ):
        return True

    # Also good: directly imports tomli (no tomllib reference)
    if ("import tomli" in source or "from tomli" in source) and "tomllib" not in source:
        return True

    # Bad: uses tomllib without fallback, or has broken fallback
    if "import tomllib" in source:
        # Check it's in a try block with proper except
        lines = source.split('\n')
        for i, line in enumerate(lines):
            if "import tomllib" in line.strip():
                # Look for except clause nearby
                found_except = False
                for j in range(i + 1, min(i + 5, len(lines))):
                    if "except" in lines[j] and ("ModuleNotFoundError" in lines[j]
                                                  or "ImportError" in lines[j]):
                        found_except = True
                        break
                if not found_except:
                    return False
    return True


def _check_requirements_coherence(req_path: Path) -> dict:
    """Advanced requirements.txt check — coherence of version pins.

    Beyond basic checks, verifies:
    - numpy AND scipy both have upper bounds (coherent version strategy)
    - No conflicting pins
    - tomli is present with reasonable version
    - python_requires or markers are used sensibly (bonus)
    """
    content = _read(req_path)
    if not content.strip():
        return {"coherent": False, "has_tomli_version": False,
                "both_capped": False, "no_conflicts": True}

    has_numpy_cap = False
    has_scipy_cap = False
    has_tomli_version = False
    conflicts = []

    for line in content.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        if line.startswith("numpy"):
            if "<2" in line or "<=1" in line or "<1.25" in line or "==" in line:
                has_numpy_cap = True

        if line.startswith("scipy"):
            if "<1.14" in line or "<=1.13" in line or "==" in line:
                ver_match = re.search(r'==(\d+\.\d+)', line)
                if ver_match:
                    if float(ver_match.group(1)) < 1.14:
                        has_scipy_cap = True
                else:
                    has_scipy_cap = True

        if line.startswith("tomli") and not line.startswith("tomllib"):
            # Check if it has a version specifier (good practice)
            if ">=" in line or "==" in line or "~=" in line:
                has_tomli_version = True
            else:
                # Even without version, having tomli is the main point
                has_tomli_version = True

        # Check for obviously conflicting entries
        if line.startswith("tomllib"):
            conflicts.append("tomllib in requirements (stdlib 3.11+)")

    both_capped = has_numpy_cap and has_scipy_cap
    return {
        "coherent": both_capped and len(conflicts) == 0,
        "has_tomli_version": has_tomli_version,
        "both_capped": both_capped,
        "no_conflicts": len(conflicts) == 0,
    }


def _check_requirements(req_path: Path) -> dict:
    """Check requirements.txt for 3.9-compatible version pins."""
    content = _read(req_path)
    if not content.strip():
        return {"valid": False, "issues": [], "has_tomli": False,
                "has_numpy_cap": False, "has_scipy_cap": False}

    issues = []
    has_tomli = False
    has_numpy_cap = False
    has_scipy_cap = False
    no_tomllib_entry = True

    for line in content.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        if line.startswith("tomllib"):
            no_tomllib_entry = False
            issues.append("tomllib is not installable on 3.9, use tomli")

        if line.startswith("tomli") and not line.startswith("tomllib"):
            has_tomli = True

        if line.startswith("numpy"):
            if ">=1.24" in line or ">=1.25" in line or ">=2" in line:
                if "<" not in line:
                    issues.append("numpy needs upper bound for 3.9 (numpy 2.0+ drops 3.9)")
            if "<2" in line or "<=1" in line or "<1.25" in line:
                has_numpy_cap = True
            if "==" in line:
                has_numpy_cap = True

        if line.startswith("scipy"):
            if ">=1.12" in line or ">=1.13" in line or ">=1.14" in line:
                if "<1.14" not in line and "<2" not in line and "==" not in line:
                    issues.append("scipy>=1.14 drops Python 3.9, need upper bound")
            if "<1.14" in line or "<=1.13" in line:
                has_scipy_cap = True
            if "==" in line:
                version_match = re.search(r'==(\d+\.\d+)', line)
                if version_match:
                    ver = float(version_match.group(1))
                    if ver < 1.14:
                        has_scipy_cap = True

    return {
        "valid": len(issues) == 0 and no_tomllib_entry,
        "has_tomli": has_tomli,
        "has_numpy_cap": has_numpy_cap,
        "has_scipy_cap": has_scipy_cap,
        "issues": issues,
    }


def grade_workspace(ws: Path) -> dict:
    """Grade the workspace for Python 3.9 compatibility fixes.

    Tiered scoring structure:

      VISIBLE (40% total) — obvious errors, all agents should catch:
        - no_match_case (15%): match-case is syntax error on 3.9
        - no_pipe_union (13%): X|Y annotations fail on 3.9
        - config_tomllib_fixed (12%): tomllib doesn't exist on 3.9

      HIDDEN EASY (30% total) — straightforward but not shown to agent:
        - no_strict_zip (8%): zip strict= is 3.10+
        - importlib_compat (8%): importlib.resources.files is 3.9+ edge
        - requirements_basic (8%): basic requirements.txt fixes
        - all_files_parseable (6%): all source files parse as valid Python

      HIDDEN HARD (30% total) — subtle, only strong agents catch:
        - no_slots_dataclass (7%): @dataclass(slots=True) is 3.10+
        - no_kw_only_dataclass (6%): @dataclass(kw_only=True) is 3.10+
        - no_type_alias (5%): TypeAlias from typing is 3.10+
        - no_walrus_comprehension (5%): walrus in comprehension scoping
        - scipy_version_cap (4%): scipy 1.14+ drops 3.9
        - tomli_fallback_quality (3%): proper try/except pattern
    """

    project = ws / "traffic_annotator"
    if not project.exists():
        project = ws

    main_py = project / "main.py"
    optical_py = project / "optical_flow.py"
    tracker_py = project / "tracker.py"
    config_py = project / "config.py"
    req_txt = project / "requirements.txt"
    image_ops_py = project / "utils" / "image_ops.py"

    components = {}

    # ===== VISIBLE TIER (public, 40%) =====
    # These are obvious errors that produce immediate syntax/import failures.
    # All agents should catch these.

    # 1. main.py + optical_flow.py: no match-case (3.10+) — syntax error on 3.9
    main_src = _read(main_py) if main_py.exists() else ""
    optical_src = _read(optical_py) if optical_py.exists() else ""
    main_no_match = _check_no_match_case(main_src) if main_src else False
    opt_no_match = _check_no_match_case(optical_src) if optical_src else False
    components["no_match_case"] = 1.0 if (main_no_match and opt_no_match) else (
        0.5 if (main_no_match or opt_no_match) else 0.0
    )

    # 2. All files: no X|Y union syntax (3.10+)
    config_src = _read(config_py) if config_py.exists() else ""
    main_no_pipe = _check_no_pipe_union(main_src)
    config_no_pipe = _check_no_pipe_union(config_src)
    optical_no_pipe = _check_no_pipe_union(optical_src)
    pipe_score = sum([main_no_pipe, config_no_pipe, optical_no_pipe]) / 3.0
    components["no_pipe_union"] = round(pipe_score, 4)

    # 3. config.py: tomllib replaced with compat solution
    if config_src:
        if _check_no_tomllib(config_src):
            components["config_tomllib_fixed"] = 1.0
        elif "import tomli" in config_src or "from tomli" in config_src:
            components["config_tomllib_fixed"] = 0.5
        else:
            components["config_tomllib_fixed"] = 0.0
    else:
        components["config_tomllib_fixed"] = 0.0

    # ===== HIDDEN EASY TIER (30%) =====
    # Not shown to the agent but still straightforward fixes.
    # All decent agents should pass these.

    # 4. No zip(..., strict=True) in tracker.py and image_ops.py
    tracker_src = _read(tracker_py) if tracker_py.exists() else ""
    image_ops_src = _read(image_ops_py) if image_ops_py.exists() else ""
    tracker_ok = _check_no_strict_zip(tracker_src) if tracker_src else True
    image_ops_ok = _check_no_strict_zip(image_ops_src) if image_ops_src else True
    if tracker_ok and image_ops_ok:
        components["no_strict_zip"] = 1.0
    elif tracker_ok or image_ops_ok:
        components["no_strict_zip"] = 0.5
    else:
        components["no_strict_zip"] = 0.0

    # 5. optical_flow.py: importlib.resources.files() compat
    if optical_src:
        components["importlib_compat"] = 1.0 if _check_no_importlib_files(optical_src) else 0.0
    else:
        components["importlib_compat"] = 0.0

    # 6. requirements.txt basic correctness
    if req_txt.exists():
        req_check = _check_requirements(req_txt)
        score = 0.0
        if req_check["valid"]:
            score += 0.4
        if req_check["has_tomli"]:
            score += 0.3
        if req_check["has_numpy_cap"]:
            score += 0.3
        components["requirements_basic"] = min(round(score, 4), 1.0)
    else:
        components["requirements_basic"] = 0.0

    # 7. All files parseable (valid Python syntax after fixes)
    all_files = [main_py, optical_py, tracker_py, config_py, image_ops_py]
    parseable_count = sum(1 for f in all_files if f.exists() and _can_parse(f))
    total_files = sum(1 for f in all_files if f.exists())
    components["all_files_parseable"] = (
        round(parseable_count / total_files, 4) if total_files > 0 else 0.0
    )

    # ===== HIDDEN HARD TIER (30%) =====
    # Subtle 3.9 compat issues. Only strong agents consistently catch all of these.

    # 8. No @dataclass(slots=True) — 3.10+ feature, not an obvious error
    tracker_no_slots = _check_no_slots_dataclass(tracker_src) if tracker_src else True
    components["no_slots_dataclass"] = 1.0 if tracker_no_slots else 0.0

    # 9. No @dataclass(kw_only=True) — 3.10+ feature
    config_no_kwonly = _check_no_kw_only_dataclass(config_src) if config_src else True
    components["no_kw_only_dataclass"] = 1.0 if config_no_kwonly else 0.0

    # 10. No TypeAlias from typing (3.10+) — need typing_extensions or remove
    optical_no_type_alias = _check_no_type_alias_syntax(optical_src) if optical_src else True
    components["no_type_alias"] = 1.0 if optical_no_type_alias else 0.0

    # 11. No walrus operator in list comprehension (subtle 3.9 scoping issue)
    main_no_walrus_comp = _check_no_walrus_in_comprehension(main_src) if main_src else True
    components["no_walrus_comprehension"] = 1.0 if main_no_walrus_comp else 0.0

    # 12. scipy version cap in requirements (subtle: scipy 1.14+ drops 3.9)
    if req_txt.exists():
        req_check_adv = _check_requirements(req_txt)
        components["scipy_version_cap"] = 1.0 if req_check_adv["has_scipy_cap"] else 0.0
    else:
        components["scipy_version_cap"] = 0.0

    # 13. Tomli fallback quality — proper try/except pattern
    if config_src:
        components["tomli_fallback_quality"] = (
            1.0 if _check_tomli_fallback_pattern(config_src) else 0.0
        )
    else:
        components["tomli_fallback_quality"] = 0.0

    # === Weights ===
    # Visible: 40%, Hidden Easy: 30%, Hidden Hard: 30%
    weights = {
        # VISIBLE tier (40%)
        "no_match_case": 0.15,
        "no_pipe_union": 0.13,
        "config_tomllib_fixed": 0.12,
        # HIDDEN EASY tier (30%)
        "no_strict_zip": 0.08,
        "importlib_compat": 0.08,
        "requirements_basic": 0.08,
        "all_files_parseable": 0.06,
        # HIDDEN HARD tier (30%)
        "no_slots_dataclass": 0.07,
        "no_kw_only_dataclass": 0.06,
        "no_type_alias": 0.05,
        "no_walrus_comprehension": 0.05,
        "scipy_version_cap": 0.04,
        "tomli_fallback_quality": 0.03,
    }

    overall = sum(weights[k] * components[k] for k in weights)

    # Tier breakdown for observability
    visible_score = sum(
        weights[k] * components[k]
        for k in ["no_match_case", "no_pipe_union", "config_tomllib_fixed"]
    )
    hidden_easy_score = sum(
        weights[k] * components[k]
        for k in ["no_strict_zip", "importlib_compat", "requirements_basic",
                  "all_files_parseable"]
    )
    hidden_hard_score = sum(
        weights[k] * components[k]
        for k in ["no_slots_dataclass", "no_kw_only_dataclass", "no_type_alias",
                  "no_walrus_comprehension", "scipy_version_cap",
                  "tomli_fallback_quality"]
    )

    return {
        "overall_score": round(overall, 4),
        "tier_scores": {
            "visible": round(visible_score, 4),
            "hidden_easy": round(hidden_easy_score, 4),
            "hidden_hard": round(hidden_hard_score, 4),
        },
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    ws = Path("/workspace/fixtures")
    if not (ws / "traffic_annotator").exists():
        ws = Path("/workspace")

    result = grade_workspace(ws)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
