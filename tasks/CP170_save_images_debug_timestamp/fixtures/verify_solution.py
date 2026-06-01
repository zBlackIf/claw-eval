"""Hidden verifier for CP170 — _save_images debug timestamp conditional logic.

Checks:
1. timestamp_used_in_debug: When logger level is DEBUG, filenames include timestamp
2. fixed_name_in_non_debug: When logger level is NOT DEBUG, filenames are fixed (raw.jpg, det.jpg)
3. uses_config_logger: Uses the project's config-based logger (not Python logging module level)
4. ts_format_correct: Timestamp format includes date+time with milliseconds
5. no_import_logging_level: Does NOT use `import logging` or `logging.DEBUG` for the level check
6. both_branches_covered: Both raw AND det paths get conditional timestamp treatment
7. function_signature_intact: _save_images signature unchanged (color, det_img, cfg)
8. conditional_inside_function: The debug check lives inside _save_images, not refactored out
9. preserves_save_guards: save_raw/save_det gating logic still intact (not collapsed)
10. reuses_existing_ts: Uses the existing `ts` variable rather than duplicating datetime call
11. no_unconditional_ts_leak: Timestamp doesn't leak into non-debug path
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def find_inspector(ws: Path) -> Path | None:
    """Find inspector.py in workspace."""
    candidates = [
        ws / "realman_arm" / "src" / "core" / "inspector.py",
        ws / "fixtures" / "realman_arm" / "src" / "core" / "inspector.py",
        ws / "src" / "core" / "inspector.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    # fallback: search recursively
    for p in ws.rglob("inspector.py"):
        if "core" in str(p):
            return p
    return None


def _extract_save_images_func(code: str) -> str:
    """Extract _save_images function body precisely."""
    # Match from def _save_images to the next top-level def/class or end of file
    save_images_match = re.search(
        r"(def\s+_save_images\s*\(.*?\n(?:.*?\n)*?)(?=\ndef\s|\nclass\s|\Z)",
        code,
        re.MULTILINE,
    )
    return save_images_match.group(1) if save_images_match else ""


def grade_workspace(ws: Path) -> dict:
    inspector_path = find_inspector(ws)
    if not inspector_path:
        return {
            "overall_score": 0.0,
            "components": {},
            "error": "inspector.py not found",
        }

    code = _read(inspector_path)
    components = {k: 0.0 for k in [
        "timestamp_used_in_debug",
        "fixed_name_in_non_debug",
        "uses_config_logger",
        "ts_format_correct",
        "no_stdlib_logging_level_check",
        "both_branches_covered",
        "function_signature_intact",
        "conditional_inside_function",
        "preserves_save_guards",
        "reuses_existing_ts",
        "no_unconditional_ts_leak",
    ]}

    func_code = _extract_save_images_func(code)
    if not func_code:
        # Function might have been removed or renamed
        return {
            "overall_score": 0.0,
            "components": components,
            "error": "_save_images function not found",
        }

    # --- Check 1: timestamp used in debug mode ---
    # Look for patterns like: f"raw_{ts}.jpg" or f"{ts}_raw.jpg" or similar
    ts_in_filename = bool(re.search(
        r"""(f["'].*\{ts\}.*\.jpg|f["'].*\{ts\}.*\.png|["'].*["']\s*%\s*ts|ts\s*\+|"""
        r"""format\(.*ts|join\(.*ts|f["'].*ts.*\.(jpg|png)|"""
        r"""save_dir\s*/\s*f["'].*ts)""",
        func_code,
    ))

    # Check there's a conditional around the ts usage (if debug -> ts, else -> fixed)
    has_conditional_ts = bool(re.search(
        r"(if.*(?:debug|DEBUG|level).*:.*\n.*(?:ts|timestamp)|"
        r"if.*logger.*level.*(?:debug|DEBUG|10).*:.*\n.*ts|"
        r"if.*(?:cfg|config).*(?:logging|log).*level.*(?:==|<=|in).*(?:debug|DEBUG|\"debug\"|\"DEBUG\"))",
        func_code,
        re.IGNORECASE,
    ))

    if ts_in_filename and has_conditional_ts:
        components["timestamp_used_in_debug"] = 1.0
    elif ts_in_filename:
        components["timestamp_used_in_debug"] = 0.5  # ts used but no proper conditional
    elif has_conditional_ts:
        components["timestamp_used_in_debug"] = 0.2  # conditional but ts not in filename

    # --- Check 2: fixed name in non-debug mode ---
    has_fixed_fallback = bool(re.search(
        r"""(else\s*:.*\n.*(?:raw\.jpg|det\.jpg|"raw"|"det")|"""
        r"""(?:raw\.jpg|det\.jpg).*(?:else|not.*debug|!=.*DEBUG)|"""
        r"""else\s*:\s*\n\s*.*(?:raw_path|det_path)\s*=\s*.*(?:raw|det)\.(jpg|png))""",
        func_code,
        re.IGNORECASE,
    ))

    has_ternary_or_ifelse = bool(re.search(
        r"((?:raw_path|det_path|filename|fname|name)\s*=.*if.*(?:debug|DEBUG|level).*else|"
        r"if.*(?:debug|DEBUG).*ts.*else.*(?:raw|det)|"
        r"(?:raw|det).*=.*(?:ts|timestamp).*if.*else.*(?:raw|det)\.jpg)",
        func_code,
        re.IGNORECASE,
    ))

    if has_fixed_fallback or has_ternary_or_ifelse:
        components["fixed_name_in_non_debug"] = 1.0
    elif "raw.jpg" in func_code or "det.jpg" in func_code:
        if has_conditional_ts:
            components["fixed_name_in_non_debug"] = 0.6
        else:
            components["fixed_name_in_non_debug"] = 0.1  # unchanged code

    # --- Check 3: uses config logger (not stdlib logging module) ---
    # Best: cfg.logging.level == "DEBUG" (uses project config string directly)
    # Good: logger.level / logger.getEffectiveLevel() (uses project logger object)
    # The task explicitly says "use project's config logger" — so cfg.logging.level
    # is the ideal approach. Using logger.getEffectiveLevel() <= 10 or logger.level
    # is acceptable but less ideal because it couples to numeric stdlib constants.
    uses_cfg_level_str = bool(re.search(
        r"cfg\s*\.\s*logging\s*\.\s*level\s*(?:==|!=|\.lower\(\)|\.upper\(\)|in\b)",
        func_code,
    ))
    uses_config_level_str = bool(re.search(
        r"config\s*\.\s*logging\s*\.\s*level",
        func_code,
    ))
    uses_logger_level = bool(re.search(
        r"(logger\s*\.\s*(?:level|isEnabledFor|getEffectiveLevel))",
        func_code,
    ))
    uses_logger_effective = bool(re.search(
        r"logger\s*\.\s*getEffectiveLevel\(\)",
        func_code,
    ))
    # Check if they compare against a numeric literal (10) which is stdlib DEBUG value
    uses_numeric_debug = bool(re.search(
        r"(?:<=|==|<|>=)\s*10\b",
        func_code,
    ))

    if uses_cfg_level_str or uses_config_level_str:
        # Best: directly uses config string comparison
        components["uses_config_logger"] = 1.0
    elif uses_logger_level and not uses_numeric_debug:
        # Good: uses logger object but not hardcoded numeric
        components["uses_config_logger"] = 0.8
    elif uses_logger_level and uses_numeric_debug:
        # Acceptable: uses logger but hardcodes DEBUG numeric value
        components["uses_config_logger"] = 0.6
    else:
        if re.search(r"logger.*level.*(?:10|DEBUG)", func_code):
            components["uses_config_logger"] = 0.3

    # --- Check 4: timestamp format correctness ---
    # The original ts format is: datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    # Must preserve: date + time + milliseconds (the [:-3] slice for ms)
    has_ts_format = bool(re.search(
        r"""strftime\s*\(\s*["'].*%[YyHMSf]""",
        func_code,
    ))
    has_datetime_usage = bool(re.search(
        r"(datetime\.now\(\)|datetime\.utcnow\(\)|time\.time\(\)|time\.strftime)",
        func_code,
    ))
    # Stricter: check millisecond truncation pattern is preserved
    has_ms_truncation = bool(re.search(
        r"""\[:-3\]|\[:3\]|%f.*\[.*3|microsecond.*//.*1000""",
        func_code,
    ))
    if has_ts_format and has_datetime_usage and has_ms_truncation:
        components["ts_format_correct"] = 1.0
    elif has_ts_format and has_datetime_usage:
        components["ts_format_correct"] = 0.35  # lost millisecond precision
    elif has_datetime_usage:
        components["ts_format_correct"] = 0.15

    # --- Check 5: does NOT use stdlib logging.DEBUG constant directly ---
    # Check both inside function AND at file level for new logging imports
    uses_stdlib_in_func = bool(re.search(
        r"(^import\s+logging\b|from\s+logging\s+import)",
        func_code,
        re.MULTILINE,
    ))
    # Check if the file added a NEW import logging (the original file does NOT have it
    # in inspector.py — it's in logger.py and config_loader.py, not here)
    uses_stdlib_in_file = bool(re.search(
        r"(^import\s+logging\b|^from\s+logging\s+import)",
        code,
        re.MULTILINE,
    ))
    # Check if logging.DEBUG is used as comparison target inside the function
    uses_logging_debug_const = bool(re.search(
        r"logging\s*\.\s*DEBUG",
        func_code,
    ))
    bad_pattern = bool(re.search(
        r"logging\s*\.\s*(?:getLogger|basicConfig|root\s*\.\s*level)",
        func_code,
    ))
    # Also check for hardcoded numeric 10 (which IS logging.DEBUG value)
    uses_hardcoded_debug_num = bool(re.search(
        r"(?:<=|==|<|>=|!=)\s*10\b",
        func_code,
    ))
    if not uses_stdlib_in_file and not uses_stdlib_in_func and not bad_pattern and not uses_hardcoded_debug_num:
        components["no_stdlib_logging_level_check"] = 1.0
    elif not uses_stdlib_in_file and uses_hardcoded_debug_num:
        # No import but uses magic number 10 — still implicitly using stdlib convention
        components["no_stdlib_logging_level_check"] = 0.6
    elif uses_stdlib_in_file and uses_logging_debug_const:
        # Added import logging + uses logging.DEBUG as constant for comparison
        # This is the common weak-model pattern: import logging then compare
        if uses_cfg_level_str or uses_config_level_str:
            components["no_stdlib_logging_level_check"] = 0.4
        else:
            components["no_stdlib_logging_level_check"] = 0.15
    elif uses_stdlib_in_file and not uses_logging_debug_const:
        # Imported logging but doesn't use DEBUG constant — possibly for other reasons
        if uses_cfg_level_str or uses_config_level_str:
            components["no_stdlib_logging_level_check"] = 0.6
        else:
            components["no_stdlib_logging_level_check"] = 0.2

    # --- Check 6 (HIDDEN): both raw AND det get timestamp treatment ---
    # Weak models often only fix one branch (raw or det) or apply the timestamp
    # unconditionally. Both save_raw and save_det blocks should have conditional filenames.
    # Count how many of raw/det paths have timestamp in debug mode
    raw_ts_pattern = bool(re.search(
        r"""(raw.*\{ts\}|raw.*ts.*\.jpg|f["'].*raw.*\{ts\}|f["'].*\{ts\}.*raw)""",
        func_code,
    ))
    det_ts_pattern = bool(re.search(
        r"""(det.*\{ts\}|det.*ts.*\.jpg|f["'].*det.*\{ts\}|f["'].*\{ts\}.*det)""",
        func_code,
    ))
    # Also check both have fixed fallback
    raw_fixed = bool(re.search(r"""["']raw\.jpg["']""", func_code))
    det_fixed = bool(re.search(r"""["']det\.jpg["']""", func_code))

    if raw_ts_pattern and det_ts_pattern and raw_fixed and det_fixed:
        components["both_branches_covered"] = 1.0
    elif (raw_ts_pattern and det_ts_pattern):
        components["both_branches_covered"] = 0.5  # timestamps but missing fallback
    elif (raw_ts_pattern or det_ts_pattern) and (raw_fixed or det_fixed):
        components["both_branches_covered"] = 0.2  # only one branch handled
    else:
        components["both_branches_covered"] = 0.0

    # --- Check 7 (HIDDEN): function signature unchanged ---
    # The function must still accept (color, det_img, cfg) — no extra params added,
    # no removed params. This ensures the fix is surgical.
    sig_match = re.search(
        r"def\s+_save_images\s*\((.*?)\)\s*(?:->.*?)?:",
        func_code,
        re.DOTALL,
    )
    if sig_match:
        params_str = sig_match.group(1)
        # Remove type annotations and defaults for comparison
        param_names = [p.strip().split(":")[0].strip().split("=")[0].strip()
                       for p in params_str.split(",") if p.strip()]
        # Original: (color, det_img, cfg) — possibly with self or type hints
        param_names_clean = [p for p in param_names if p and p != "self"]
        if param_names_clean == ["color", "det_img", "cfg"]:
            components["function_signature_intact"] = 1.0
        elif set(["color", "det_img", "cfg"]).issubset(set(param_names_clean)):
            components["function_signature_intact"] = 0.4  # added extra params
        else:
            components["function_signature_intact"] = 0.0
    else:
        components["function_signature_intact"] = 0.0

    # --- Check 8 (HIDDEN): conditional logic lives inside _save_images ---
    # The debug level check must be inside _save_images body, not factored out
    # into a helper or moved to the caller. This checks that the function itself
    # contains the level/debug conditional.
    has_level_check_in_func = bool(re.search(
        r"(if.*(?:level|debug|DEBUG|isEnabledFor|getEffectiveLevel))",
        func_code,
        re.IGNORECASE,
    ))
    # Also verify the function still calls cv2.imwrite (not delegated)
    has_imwrite_in_func = bool(re.search(r"cv2\.imwrite", func_code))

    if has_level_check_in_func and has_imwrite_in_func:
        components["conditional_inside_function"] = 1.0
    elif has_level_check_in_func:
        components["conditional_inside_function"] = 0.4  # check exists but imwrite moved
    else:
        components["conditional_inside_function"] = 0.0

    # --- Check 9 (HIDDEN): preserves save_raw/save_det guard conditions ---
    # The original code has `if cfg.service.save_raw:` and `if cfg.service.save_det:`
    # gating the two save operations. Weak models often restructure the function and
    # lose these guards, or merge them into the debug conditional. The guards MUST
    # remain as separate checks around the actual cv2.imwrite calls.
    has_save_raw_guard = bool(re.search(
        r"if\s+cfg\s*\.\s*service\s*\.\s*save_raw\s*:",
        func_code,
    ))
    has_save_det_guard = bool(re.search(
        r"if\s+cfg\s*\.\s*service\s*\.\s*save_det\s*:",
        func_code,
    ))
    # Also check that the guards are NOT nested inside the debug conditional
    # (they should be outer guards, with the debug conditional inside or vice versa,
    # but both must still exist)
    if has_save_raw_guard and has_save_det_guard:
        components["preserves_save_guards"] = 1.0
    elif has_save_raw_guard or has_save_det_guard:
        components["preserves_save_guards"] = 0.3  # lost one guard
    else:
        components["preserves_save_guards"] = 0.0

    # --- Check 10 (HIDDEN): reuses existing ts variable ---
    # The function already has: ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    # BEFORE any conditional block (it's at the function top, alongside save_dir setup).
    # A correct solution keeps this assignment at the top level of the function and
    # simply references `ts` inside the debug conditional.
    # Weak models often:
    #   a) Delete the original ts line and create a new one inside the if-block
    #   b) Duplicate the datetime.now() call inside the conditional
    #   c) Move ts assignment inside the if-block (only computed when debug)
    #   d) Create a completely different timestamp variable name
    #
    # Strategy: check that ts assignment appears BEFORE the debug conditional,
    # not nested inside it.
    datetime_calls = re.findall(r"datetime\.now\(\)", func_code)
    ts_assignments = re.findall(
        r"^\s*ts\s*=\s*datetime\.now\(\)",
        func_code,
        re.MULTILINE,
    )
    # Check if ts is assigned at top-level of function (not indented inside if/else)
    # Top-level means same indent as save_dir or the first real statement
    ts_at_top_level = bool(re.search(
        r"^    ts\s*=\s*datetime\.now\(\)",
        func_code,
        re.MULTILINE,
    ))
    # Check if ts is only inside an if-block (indented further)
    ts_inside_conditional = bool(re.search(
        r"^        ts\s*=\s*datetime\.now\(\)|^\s{8,}ts\s*=\s*datetime\.now\(\)",
        func_code,
        re.MULTILINE,
    ))
    # Also check for new timestamp variable names that duplicate the work
    alt_ts_vars = re.findall(
        r"^\s*(?:timestamp|time_str|ts_str|dt_str|now_str|fname_ts)\s*=\s*datetime\.now\(\)",
        func_code,
        re.MULTILINE,
    )

    if ts_at_top_level and len(datetime_calls) == 1 and len(alt_ts_vars) == 0:
        # Perfect: ts at function top level, one datetime.now() call, no duplicates
        components["reuses_existing_ts"] = 1.0
    elif ts_at_top_level and len(datetime_calls) <= 2:
        # ts at top but maybe a duplicate call somewhere
        components["reuses_existing_ts"] = 0.7
    elif ts_inside_conditional and not ts_at_top_level:
        # Moved ts inside the if-block — technically works but not reusing original
        components["reuses_existing_ts"] = 0.3
    elif len(ts_assignments) >= 1 and len(datetime_calls) <= 2:
        # ts exists somewhere but not ideal placement
        components["reuses_existing_ts"] = 0.4
    elif len(alt_ts_vars) > 0:
        # Created alternative variable names
        components["reuses_existing_ts"] = 0.15
    else:
        # Major restructuring or no ts at all
        components["reuses_existing_ts"] = 0.1

    # --- Check 11 (HIDDEN): no timestamp leaks into non-debug filenames ---
    # Verify that the code structure ensures timestamps ONLY appear in debug mode.
    # Weak models sometimes write code where the ts ends up in filenames unconditionally
    # due to variable scoping issues or incorrect else branches.
    # Strategy: look for the else/non-debug branch and verify it uses fixed names
    # without any ts/timestamp interpolation.
    #
    # Find the else branch content (or the non-debug path)
    else_blocks = re.findall(
        r"else\s*:\s*\n((?:\s+.*\n)*?)(?=\s*(?:if|def|class|\S)|\Z)",
        func_code,
    )
    # Also check for ternary patterns like: x = ts_name if debug else fixed_name
    ternary_patterns = re.findall(
        r"=\s*.*if.*(?:debug|DEBUG|level).*else\s+(.*)",
        func_code,
        re.IGNORECASE,
    )

    ts_leak_in_else = False
    for block in else_blocks:
        if re.search(r"\{ts\}|ts\s*\+|\bts\b.*\.jpg|format\(.*ts", block):
            ts_leak_in_else = True
            break

    ts_leak_in_ternary_else = False
    for tern_else in ternary_patterns:
        if re.search(r"\{ts\}|ts\s*\+|\bts\b", tern_else):
            ts_leak_in_ternary_else = True
            break

    # Check that the raw.jpg/det.jpg fixed names still appear somewhere
    # (ensuring non-debug path produces fixed names)
    fixed_names_present = "raw.jpg" in func_code and "det.jpg" in func_code

    if fixed_names_present and not ts_leak_in_else and not ts_leak_in_ternary_else:
        components["no_unconditional_ts_leak"] = 1.0
    elif fixed_names_present and (ts_leak_in_else or ts_leak_in_ternary_else):
        components["no_unconditional_ts_leak"] = 0.1  # fixed names exist but ts leaks
    elif not fixed_names_present and not ts_leak_in_else:
        # No fixed names at all — possibly always timestamped
        components["no_unconditional_ts_leak"] = 0.0
    else:
        components["no_unconditional_ts_leak"] = 0.2

    # --- Scoring with rebalanced weights ---
    # Hard/hidden checks get higher weight to separate strong from weak models.
    # Strong model target: 0.7-0.85, Weak model target: 0.4-0.6
    weights = {
        "timestamp_used_in_debug": 0.09,
        "fixed_name_in_non_debug": 0.06,
        "uses_config_logger": 0.16,
        "ts_format_correct": 0.09,
        "no_stdlib_logging_level_check": 0.14,
        "both_branches_covered": 0.11,
        "function_signature_intact": 0.03,
        "conditional_inside_function": 0.04,
        "preserves_save_guards": 0.11,
        "reuses_existing_ts": 0.11,
        "no_unconditional_ts_leak": 0.06,
    }
    overall = sum(weights[k] * components[k] for k in weights)

    # Apply a strictness penalty: if any of the first 3 core checks is 0, cap at 0.4
    core_checks = [
        components["timestamp_used_in_debug"],
        components["fixed_name_in_non_debug"],
        components["uses_config_logger"],
    ]
    if any(c == 0.0 for c in core_checks):
        overall = min(overall, 0.4)

    # Additional penalty: if preserves_save_guards is 0, cap at 0.6
    # (strong models won't break existing guards)
    if components["preserves_save_guards"] == 0.0:
        overall = min(overall, 0.6)

    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    ws = Path("/workspace/fixtures/realman_arm")
    if not ws.exists():
        ws = Path("/workspace/realman_arm")
    if not ws.exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
