"""Hidden verifier for CP183 — C++ State Machine Logging Unification.

Checks that the agent properly:
1. Removed custom log/logError/logDebug methods from BaseState and SequenceManager
2. Created a unified types header (htvstartsequence_types.h) with DEV_ENV conditional
3. Updated CMakeLists.txt to include lib/loglib path for htvstartsequence
4. .cpp files define TAG macro (following htvclone pattern)
5. No references to custom log() method calls remain in state implementations
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_file(base: Path, name_pattern: str) -> Path | None:
    """Find a file matching pattern recursively."""
    for p in base.rglob(name_pattern):
        return p
    return None


def grade_workspace(ws: Path) -> dict:
    """Grade the workspace for logging unification task."""

    # Try multiple possible base paths
    hsm_base = ws / "htvstartsequence"
    if not hsm_base.exists():
        hsm_base = ws / "fixtures" / "htvstartsequence"

    cmake_path = ws / "CMakeLists.txt"
    if not cmake_path.exists():
        cmake_path = ws / "fixtures" / "CMakeLists.txt"

    components = {
        "custom_log_removed": 0.0,
        "types_header_created": 0.0,
        "dev_env_conditional": 0.0,
        "cmake_loglib_include": 0.0,
        "tag_macro_defined": 0.0,
        "states_use_unified_log": 0.0,
    }

    # ------------------------------------------------------------------
    # 1. Custom log methods removed from BaseState (0.20 weight)
    # ------------------------------------------------------------------
    base_state_h = hsm_base / "states" / "base_state.h"
    base_state_cpp = hsm_base / "states" / "base_state.cpp"

    if base_state_h.exists():
        h_content = _read(base_state_h)
        # Check that log/logError/logDebug declarations are removed
        has_log_decl = bool(re.search(r'void\s+log\s*\(\s*const\s+std::string', h_content))
        has_logError_decl = bool(re.search(r'void\s+logError\s*\(\s*const\s+std::string', h_content))
        has_logDebug_decl = bool(re.search(r'void\s+logDebug\s*\(\s*const\s+std::string', h_content))

        removed_count = sum([not has_log_decl, not has_logError_decl, not has_logDebug_decl])
        components["custom_log_removed"] = removed_count / 3.0
    else:
        components["custom_log_removed"] = 0.0

    # Also check SequenceManager
    seq_mgr_h = hsm_base / "manager" / "sequence_manager.h"
    if seq_mgr_h.exists():
        sm_content = _read(seq_mgr_h)
        sm_has_log = bool(re.search(r'void\s+log\s*\(\s*const\s+std::string', sm_content))
        sm_has_logError = bool(re.search(r'void\s+logError\s*\(\s*const\s+std::string', sm_content))
        if not sm_has_log and not sm_has_logError:
            components["custom_log_removed"] = min(1.0, components["custom_log_removed"] + 0.34)

    # ------------------------------------------------------------------
    # 2. Unified types header created (0.20 weight)
    # ------------------------------------------------------------------
    types_header = None
    # Look for a types header in include/ or at various locations
    candidates = [
        hsm_base / "include" / "htvstartsequence_types.h",
        hsm_base / "include" / "types.h",
        hsm_base / "htvstartsequence_types.h",
    ]
    for c in candidates:
        if c.exists():
            types_header = c
            break

    # Also search recursively
    if types_header is None and hsm_base.exists():
        for p in hsm_base.rglob("*types*.h"):
            if "startsequence" in p.name.lower() or "types" in p.name.lower():
                types_header = p
                break

    if types_header:
        tc = _read(types_header)
        # Should include logger.h reference
        has_logger_include = "logger.h" in tc
        # Should have LOG macros or include that provides them
        has_log_macro_def = bool(re.search(r'#define\s+(LOG_INFO|LOG_ERROR|LOG_WARN|LOG_DEBUG)', tc))
        has_log_ref = has_logger_include or has_log_macro_def

        components["types_header_created"] = 0.5 + (0.5 if has_log_ref else 0.0)
    else:
        # Maybe they added includes directly in base_state.h
        if base_state_h.exists():
            h_content = _read(base_state_h)
            # Must be an actual #include, not just a comment
            if re.search(r'#include\s*[<"].*logger\.h[>"]', h_content):
                components["types_header_created"] = 0.3

    # ------------------------------------------------------------------
    # 3. DEV_ENV conditional compilation (0.15 weight)
    # ------------------------------------------------------------------
    if types_header:
        tc = _read(types_header)
        has_dev_env_ifdef = bool(re.search(r'#ifdef\s+DEV_ENV', tc))
        has_else = "#else" in tc
        has_soc_in_else = bool(re.search(r'SocMwLog|SOC_MW_LOG', tc))

        if has_dev_env_ifdef and has_else:
            components["dev_env_conditional"] = 0.7
            if has_soc_in_else:
                components["dev_env_conditional"] = 1.0
        elif has_dev_env_ifdef:
            components["dev_env_conditional"] = 0.5
    elif base_state_h.exists():
        h_content = _read(base_state_h)
        if "#ifdef DEV_ENV" in h_content:
            components["dev_env_conditional"] = 0.4

    # ------------------------------------------------------------------
    # 4. CMakeLists.txt includes lib/loglib for htvstartsequence (0.15 weight)
    # ------------------------------------------------------------------
    if cmake_path.exists():
        cmake_content = _read(cmake_path)
        # Check that htvstartsequence target includes loglib path
        # Pattern: target_include_directories for htvstartsequence includes loglib
        hsm_section = ""
        # Find htvstartsequence include dirs section
        match = re.search(
            r'target_include_directories\s*\(\s*htvstartsequence[^)]*\)',
            cmake_content, re.DOTALL
        )
        if match:
            hsm_section = match.group(0)

        has_loglib = bool(re.search(r'lib/loglib|loglib', hsm_section))
        has_dev_env_def = bool(re.search(r'DEV_ENV', cmake_content))

        if has_loglib:
            components["cmake_loglib_include"] = 0.7
            if has_dev_env_def:
                components["cmake_loglib_include"] = 1.0
        elif not hsm_section and "loglib" in cmake_content.lower():
            # loglib exists somewhere in cmake but NOT in htvstartsequence section
            components["cmake_loglib_include"] = 0.0

    # ------------------------------------------------------------------
    # 5. TAG macro defined in .cpp files (0.15 weight)
    # ------------------------------------------------------------------
    cpp_files = []
    if hsm_base.exists():
        cpp_files = list(hsm_base.rglob("*.cpp"))

    if cpp_files:
        tag_count = 0
        for cpp in cpp_files:
            content = _read(cpp)
            if re.search(r'#define\s+TAG\s+', content):
                tag_count += 1
        # At least 2 .cpp files should define TAG
        components["tag_macro_defined"] = min(1.0, tag_count / max(2, len(cpp_files) * 0.5))
    else:
        components["tag_macro_defined"] = 0.0

    # ------------------------------------------------------------------
    # 6. State implementations use unified LOG macros (0.15 weight)
    # ------------------------------------------------------------------
    state_cpp_files = []
    if (hsm_base / "states").exists():
        state_cpp_files = list((hsm_base / "states").rglob("*.cpp"))
    elif hsm_base.exists():
        state_cpp_files = [p for p in hsm_base.rglob("*.cpp") if "state" in p.name.lower()]

    if state_cpp_files:
        unified_count = 0
        old_style_count = 0
        for cpp in state_cpp_files:
            content = _read(cpp)
            # Check for new-style LOG_INFO(TAG, ...) usage
            uses_new = bool(re.search(r'LOG_(INFO|ERROR|DEBUG|WARN)\s*\(', content))
            # Check for old-style this->log(...) or just log(...)
            uses_old = bool(re.search(r'\blog\s*\(\s*"', content)) or \
                       bool(re.search(r'\blogError\s*\(\s*"', content)) or \
                       bool(re.search(r'\blogDebug\s*\(\s*"', content))

            if uses_new and not uses_old:
                unified_count += 1
            elif uses_old:
                old_style_count += 1

        total = len(state_cpp_files)
        if total > 0:
            components["states_use_unified_log"] = unified_count / total

    # ------------------------------------------------------------------
    # Compute overall score
    # ------------------------------------------------------------------
    weights = {
        "custom_log_removed": 0.20,
        "types_header_created": 0.20,
        "dev_env_conditional": 0.15,
        "cmake_loglib_include": 0.15,
        "tag_macro_defined": 0.15,
        "states_use_unified_log": 0.15,
    }

    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    ws = Path("/workspace")
    # Try fixtures subdir first (where sandbox_files land)
    if (ws / "fixtures" / "htvstartsequence").exists():
        result = grade_workspace(ws / "fixtures")
    elif (ws / "htvstartsequence").exists():
        result = grade_workspace(ws)
    else:
        # Fallback: look in both
        result = grade_workspace(ws)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
