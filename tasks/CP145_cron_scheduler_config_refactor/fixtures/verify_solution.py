"""Hidden verifier for CP145 — Cron Scheduler Config Refactor.

Checks that the agent correctly fixed the scheduler to:
1. Use Asia/Shanghai timezone
2. Implement ack-based suppression (should_fire checks ack_date)
3. Implement ack-based retry suppression (should_retry checks ack_date)
4. Implement add_task functionality
5. Update config.yaml with correct timezone and suppress_after_ack=true
6. [Hidden] add_task validates inputs and handles duplicates
7. [Hidden] get_now reads timezone from config dynamically (not hardcoded)
8. [Hidden] CLI add subcommand is wired up and parses arguments
9. [Hidden] add_task uses atomic write to prevent config corruption
10. [Hidden] acknowledge_task validates task_id against config (not just state)
11. [Hidden] should_fire handles edge cases (missing state entry, malformed cron)
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


def _strip_comments_and_docstrings(source: str) -> str:
    """Remove comments and docstrings to avoid false positives from BUG annotations."""
    lines = []
    in_docstring = False
    docstring_char = None
    for line in source.splitlines():
        stripped = line.strip()
        # Skip comment-only lines
        if stripped.startswith("#"):
            lines.append("")
            continue
        # Remove inline comments
        code_part = re.sub(r'#[^"\']*$', '', line)
        lines.append(code_part)
    result = "\n".join(lines)
    # Remove triple-quoted docstrings
    result = re.sub(r'""".*?"""', '""""""', result, flags=re.DOTALL)
    result = re.sub(r"'''.*?'''", "''''''", result, flags=re.DOTALL)
    return result


def _get_func_body_code(source: str, func_name: str) -> str:
    """Extract function body as code, stripping comments and docstrings."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ""

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            func_source = ast.get_source_segment(source, node) or ""
            return _strip_comments_and_docstrings(func_source)
    return ""


def _get_func_raw_code(source: str, func_name: str) -> str:
    """Extract raw function source without stripping."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            return ast.get_source_segment(source, node) or ""
    return ""


def _check_timezone(source: str, config_text: str) -> tuple[float, str]:
    """Check timezone is set to Asia/Shanghai."""
    score = 0.0
    details = []

    # Check config.yaml has Asia/Shanghai (not just in a comment)
    config_lines = [l for l in config_text.splitlines() if not l.strip().startswith("#")]
    config_no_comments = "\n".join(config_lines)
    if "Asia/Shanghai" in config_no_comments:
        score += 0.5
        details.append("config.yaml has Asia/Shanghai in active config")
    else:
        details.append("config.yaml missing Asia/Shanghai in active config")

    # Check scheduler.py get_now() uses timezone from config properly
    func_code = _get_func_body_code(source, "get_now")
    if func_code:
        # Must use ZoneInfo or pytz or dateutil with Asia/Shanghai
        uses_tz_lib = any(kw in func_code for kw in ["ZoneInfo", "pytz", "zoneinfo", "timezone("])
        refs_config = any(kw in func_code for kw in ["config", "timezone", "tz"])
        # Should NOT still have the hardcoded UTC-only pattern
        still_utc_only = "timezone.utc" in func_code and "ZoneInfo" not in func_code and "pytz" not in func_code

        if uses_tz_lib and not still_utc_only:
            score += 0.5
            details.append("get_now uses timezone library")
        elif refs_config and not still_utc_only:
            score += 0.3
            details.append("get_now references config timezone")
        else:
            details.append("get_now still hardcodes UTC or lacks timezone handling")
    else:
        details.append("get_now function not found")

    return min(score, 1.0), "; ".join(details)


def _check_ack_suppression_fire(source: str) -> tuple[float, str]:
    """Check should_fire respects ack_date with actual logic (not just comments)."""
    score = 0.0
    details = []

    func_code = _get_func_body_code(source, "should_fire")
    if not func_code:
        return 0.0, "should_fire function not found or has syntax error"

    # The function must have actual code that:
    # 1. Accesses ack_date from state
    # 2. Compares it to today's date
    # 3. Returns False if matched

    # Check for state/ack_date access in CODE (not comments)
    has_state_access = "ack_date" in func_code or "ack" in func_code
    has_date_compare = any(kw in func_code for kw in ["strftime", "today", "date()", "isoformat", "== "])
    has_return_false_conditional = False

    # Check AST for if-statement that leads to return False involving ack
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "should_fire":
                for child in ast.walk(node):
                    if isinstance(child, ast.If):
                        # Check if the if-condition involves ack-related attribute
                        if_source = ast.get_source_segment(source, child) or ""
                        if_code = _strip_comments_and_docstrings(if_source)
                        if "ack" in if_code and "return False" in if_code:
                            has_return_false_conditional = True
                            break
                        if "ack" in if_code and "return" in if_code:
                            has_return_false_conditional = True
                            break
    except SyntaxError:
        pass

    if has_return_false_conditional:
        score = 1.0
        details.append("should_fire has conditional ack check that returns False")
    elif has_state_access and has_date_compare:
        score = 0.5
        details.append("should_fire accesses ack state and compares dates")
    elif has_state_access:
        score = 0.25
        details.append("should_fire references ack but unclear logic")
    else:
        details.append("should_fire does not implement ack suppression")

    return min(score, 1.0), "; ".join(details)


def _check_ack_suppression_retry(source: str) -> tuple[float, str]:
    """Check should_retry respects ack_date with actual logic."""
    score = 0.0
    details = []

    func_code = _get_func_body_code(source, "should_retry")
    if not func_code:
        return 0.0, "should_retry function not found or syntax error"

    # Check for actual ack suppression logic
    has_return_false_conditional = False

    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "should_retry":
                for child in ast.walk(node):
                    if isinstance(child, ast.If):
                        if_source = ast.get_source_segment(source, child) or ""
                        if_code = _strip_comments_and_docstrings(if_source)
                        if "ack" in if_code and "return False" in if_code:
                            has_return_false_conditional = True
                            break
                        if "suppress" in if_code and "return False" in if_code:
                            has_return_false_conditional = True
                            break
    except SyntaxError:
        pass

    # Also check for suppress_after_ack config usage
    has_suppress_config = "suppress_after_ack" in func_code

    if has_return_false_conditional:
        score = 1.0
        details.append("should_retry has conditional that suppresses after ack")
    elif has_suppress_config:
        score = 0.5
        details.append("should_retry references suppress_after_ack config")
    else:
        details.append("should_retry does not suppress after acknowledgment")

    return min(score, 1.0), "; ".join(details)


def _check_add_task(source: str) -> tuple[float, str]:
    """Check add_task is implemented (not raising NotImplementedError)."""
    score = 0.0
    details = []

    func_code = _get_func_body_code(source, "add_task")
    if not func_code:
        # Check if function exists at all
        if "def add_task" not in source:
            return 0.0, "add_task function not found"
        return 0.0, "add_task has syntax error"

    # Check it does NOT still raise NotImplementedError
    if "NotImplementedError" in func_code:
        return 0.0, "add_task still raises NotImplementedError"

    score += 0.3
    details.append("add_task no longer raises NotImplementedError")

    # Check it actually writes to config (yaml.dump or similar)
    writes_config = any(kw in func_code for kw in [
        "yaml.dump", "yaml.safe_dump", "dump(", "write(", "open(",
        "CONFIG_PATH", "config_path", "config.yaml"
    ])
    if writes_config:
        score += 0.4
        details.append("add_task persists to config file")
    else:
        score += 0.1
        details.append("add_task implemented but unclear if persists")

    # Check it loads existing config before appending (read-modify-write)
    loads_config = any(kw in func_code for kw in [
        "load_config", "yaml.safe_load", "yaml.load", "read("
    ])
    if loads_config:
        score += 0.3
        details.append("add_task does read-modify-write")
    else:
        details.append("add_task may not preserve existing config on write")

    return min(score, 1.0), "; ".join(details)


def _check_config_updated(config_text: str) -> tuple[float, str]:
    """Check config.yaml has been properly updated."""
    score = 0.0
    details = []

    # Only check non-comment lines
    active_lines = [l for l in config_text.splitlines() if not l.strip().startswith("#")]
    active_config = "\n".join(active_lines)

    if "suppress_after_ack: true" in active_config or "suppress_after_ack: True" in active_config:
        score += 0.4
        details.append("suppress_after_ack enabled")

    if "repeat_until_ack: true" in active_config or "repeat_until_ack: True" in active_config:
        score += 0.3
        details.append("repeat_until_ack enabled for tasks")

    if "Asia/Shanghai" in active_config:
        score += 0.3
        details.append("timezone set to Asia/Shanghai")

    if not details:
        details.append("config.yaml not significantly updated")

    return min(score, 1.0), "; ".join(details)


def _check_add_task_validation(source: str) -> tuple[float, str]:
    """Hidden check: add_task should validate inputs and handle edge cases.

    A strong model will:
    - Check for empty/None task_id
    - Validate cron expression format (5 fields)
    - Check for duplicate task IDs before adding
    - Handle the case where 'tasks' key is missing from config
    """
    score = 0.0
    details = []

    func_code = _get_func_body_code(source, "add_task")
    if not func_code or "NotImplementedError" in func_code:
        return 0.0, "add_task not implemented"

    # Check for input validation (empty/None checks)
    has_input_validation = any(kw in func_code for kw in [
        "not task_id", "not name", "not cron",
        "if not ", "raise ValueError", "raise TypeError",
        "len(task_id", "len(cron", "task_id.strip",
        "is None", "== \"\"", "== ''",
    ])
    if has_input_validation:
        score += 0.35
        details.append("add_task validates inputs")
    else:
        details.append("add_task lacks input validation for empty/invalid args")

    # Check for duplicate ID detection
    has_duplicate_check = any(pattern in func_code for pattern in [
        "already", "exist", "duplicate",
        "task_id in ", "for t in", "for task in",
        "[t[", "any(",
    ])
    # More precise: look for iteration over tasks checking id
    if has_duplicate_check and ("id" in func_code or "task_id" in func_code):
        score += 0.35
        details.append("add_task checks for duplicate IDs")
    else:
        details.append("add_task does not check for duplicate task IDs")

    # Check for cron format validation
    has_cron_validation = any(pattern in func_code for pattern in [
        "split()", ".split(", "len(", "parts",
        "cron_parts", "fields", "validate",
    ])
    cron_checks_count = "split" in func_code and ("len(" in func_code or "!= 5" in func_code or "== 5" in func_code)
    if cron_checks_count:
        score += 0.3
        details.append("add_task validates cron expression format")
    elif has_cron_validation:
        score += 0.15
        details.append("add_task has partial cron validation")
    else:
        details.append("add_task does not validate cron format")

    return min(score, 1.0), "; ".join(details)


def _check_timezone_dynamic(source: str) -> tuple[float, str]:
    """Hidden check: get_now should read timezone from config dynamically.

    A weak model may hardcode 'Asia/Shanghai' directly. A strong model reads
    the timezone field from config dict so the scheduler adapts if config changes.
    """
    score = 0.0
    details = []

    func_code = _get_func_body_code(source, "get_now")
    if not func_code:
        return 0.0, "get_now not found"

    # Check that timezone is read from config parameter (not hardcoded string)
    # The function signature takes config as param
    reads_from_config = any(kw in func_code for kw in [
        'config["timezone"]', "config['timezone']",
        'config.get("timezone"', "config.get('timezone'",
        "config[\"tz\"]", "config['tz']",
        'config.get("tz"', "config.get('tz'",
    ])

    # Check if it ALSO has a fallback
    has_fallback = any(kw in func_code for kw in [
        "or ", "else ", "except", "default", "UTC",
    ])

    # Penalty: if it just hardcodes the string without reading config
    hardcoded_only = (
        '"Asia/Shanghai"' in func_code or "'Asia/Shanghai'" in func_code
    ) and not reads_from_config

    if reads_from_config and has_fallback:
        score = 1.0
        details.append("get_now reads timezone from config with fallback")
    elif reads_from_config:
        score = 0.7
        details.append("get_now reads timezone from config (no fallback)")
    elif hardcoded_only:
        score = 0.3
        details.append("get_now hardcodes Asia/Shanghai instead of reading from config")
    else:
        score = 0.1
        details.append("get_now timezone handling unclear")

    return min(score, 1.0), "; ".join(details)


def _check_cli_add_wired(source: str) -> tuple[float, str]:
    """Hidden check: CLI 'add' subcommand should be wired to add_task with arg parsing.

    The original code has 'elif cmd == "add": print("ERROR: add_task not implemented")'
    A strong model will wire it up with proper argparse or sys.argv parsing.
    """
    score = 0.0
    details = []

    # Look at the __main__ block or the full source for CLI handling
    code_clean = _strip_comments_and_docstrings(source)

    # Extract the __main__ block specifically to check CLI wiring
    main_block = ""
    in_main = False
    for line in source.splitlines():
        if '__name__' in line and '__main__' in line:
            in_main = True
        if in_main:
            main_block += line + "\n"
    main_block_clean = _strip_comments_and_docstrings(main_block)

    # Check if add_task() is actually called in the main block (not just defined)
    calls_add_task_in_main = "add_task(" in main_block_clean

    # Check for proper argument parsing for add command
    has_argparse = "argparse" in code_clean
    has_add_args = any(kw in main_block_clean for kw in [
        "--task-id", "--task_id", "--name", "--cron",
        "parser.add_argument", "subparser",
    ])
    has_argv_parsing_for_add = (
        "sys.argv[" in main_block_clean and
        calls_add_task_in_main
    )

    # Penalty: still prints "not implemented" error in the add branch
    still_error = (
        'not implemented' in main_block_clean.lower() or
        'NotImplementedError' in main_block_clean
    )

    if still_error and not calls_add_task_in_main:
        score = 0.0
        details.append("CLI add command still prints error / not wired")
    elif calls_add_task_in_main and (has_argparse or has_add_args):
        score = 1.0
        details.append("CLI add command wired with proper arg parsing")
    elif calls_add_task_in_main and has_argv_parsing_for_add:
        score = 0.7
        details.append("CLI add command calls add_task with basic argv parsing")
    elif calls_add_task_in_main:
        score = 0.5
        details.append("CLI add command calls add_task but minimal arg handling")
    else:
        score = 0.0
        details.append("CLI add command not properly wired to add_task")

    return min(score, 1.0), "; ".join(details)


def _check_add_task_atomic_write(source: str) -> tuple[float, str]:
    """Hidden check: add_task should use atomic write to prevent config corruption.

    A strong model will write to a temp file first, then rename/move to the actual
    config path. This prevents partial writes if the process is interrupted.
    Alternatively, using a context manager that flushes and fsyncs is acceptable.
    """
    score = 0.0
    details = []

    func_code = _get_func_body_code(source, "add_task")
    if not func_code or "NotImplementedError" in func_code:
        return 0.0, "add_task not implemented"

    # Check for atomic write patterns
    has_temp_file = any(kw in func_code for kw in [
        "NamedTemporaryFile", "tempfile", "tmp_path", "tmp_file",
        ".tmp", "_tmp", "temp_", "suffix=",
    ])
    has_rename = any(kw in func_code for kw in [
        "os.rename", "os.replace", "shutil.move", "Path.rename",
        ".rename(", ".replace(",
    ])
    has_fsync = any(kw in func_code for kw in [
        "os.fsync", "f.flush()", "flush()",
    ])

    # Also check the full source for a helper that does atomic writes
    full_clean = _strip_comments_and_docstrings(source)
    has_atomic_helper = any(kw in full_clean for kw in [
        "def atomic_write", "def safe_write", "def write_config",
        "def _atomic", "def _safe_write",
    ])

    # Check if a write_config helper with atomic pattern exists and is used in add_task
    if has_atomic_helper and any(kw in func_code for kw in [
        "atomic_write", "safe_write", "write_config",
    ]):
        score = 1.0
        details.append("add_task uses atomic write helper")
    elif has_temp_file and has_rename:
        score = 1.0
        details.append("add_task uses temp file + rename for atomic write")
    elif has_rename:
        score = 0.7
        details.append("add_task uses rename (partial atomic pattern)")
    elif has_fsync:
        score = 0.5
        details.append("add_task flushes but no atomic rename")
    elif has_temp_file:
        score = 0.4
        details.append("add_task uses temp file but no rename")
    else:
        # Check if there is at least a try/except around the write to handle errors
        has_write_error_handling = False
        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "add_task":
                    for child in ast.walk(node):
                        if isinstance(child, ast.Try):
                            try_source = ast.get_source_segment(source, child) or ""
                            if "open(" in try_source or "dump" in try_source or "write" in try_source:
                                has_write_error_handling = True
                                break
        except SyntaxError:
            pass

        if has_write_error_handling:
            score = 0.3
            details.append("add_task has try/except around write but no atomic pattern")
        else:
            details.append("add_task lacks atomic write protection — config may corrupt on failure")

    return min(score, 1.0), "; ".join(details)


def _check_acknowledge_validates_config(source: str) -> tuple[float, str]:
    """Hidden check: acknowledge_task should validate task_id against known tasks in config.

    A strong model will check that the task_id being acknowledged actually exists
    in the config's task list, not just blindly create state for any string.
    This prevents phantom ack entries for typo'd task IDs.
    """
    score = 0.0
    details = []

    func_code = _get_func_body_code(source, "acknowledge_task")
    if not func_code:
        return 0.0, "acknowledge_task function not found"

    # Check if it validates the task_id against config's task list
    # The key signal is: extracting task IDs from config["tasks"] and checking membership
    # NOT just checking state.tasks (which is what the original does)
    checks_task_in_config = any(pattern in func_code for pattern in [
        "valid_ids", "known_tasks", "configured_tasks", "task_ids",
        'raise ValueError', 'raise KeyError',
    ])

    # More specific: does it extract task IDs from config and compare?
    extracts_ids_from_config = any(pattern in func_code for pattern in [
        "for t in config", "for task in config",
        '[t["id"]', "[t['id']",
        "config.get(\"tasks\"", "config.get('tasks'",
        'config["tasks"]', "config['tasks']",
    ])
    # Must also have a conditional that rejects invalid task_id
    has_rejection = any(kw in func_code for kw in [
        "raise ", "return False", "logger.warn", "logger.error",
        "not found", "invalid", "unknown",
    ])

    if checks_task_in_config and has_rejection:
        score = 1.0
        details.append("acknowledge_task validates task_id against config and rejects invalid")
    elif extracts_ids_from_config and has_rejection:
        score = 0.8
        details.append("acknowledge_task checks task list from config")
    elif checks_task_in_config or extracts_ids_from_config:
        score = 0.5
        details.append("acknowledge_task references config tasks but unclear rejection path")
    else:
        details.append("acknowledge_task blindly creates state without validating task_id exists in config")

    return min(score, 1.0), "; ".join(details)


def _check_should_fire_edge_cases(source: str) -> tuple[float, str]:
    """Hidden check: should_fire should handle edge cases gracefully.

    A strong model will:
    - Handle KeyError when task_id has no state entry (not crash)
    - Handle malformed cron expressions (wrong number of fields, non-numeric)
    - Use .get() with defaults rather than direct dict access for state lookup
    """
    score = 0.0
    details = []

    func_code = _get_func_body_code(source, "should_fire")
    if not func_code:
        return 0.0, "should_fire not found"

    # Check for safe state access (using .get() instead of direct key access)
    uses_safe_state_access = any(kw in func_code for kw in [
        "state.tasks.get(", ".get(task_id",
        "getattr(", "hasattr(",
    ])

    # Check for cron validation / error handling
    has_cron_error_handling = False
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "should_fire":
                for child in ast.walk(node):
                    if isinstance(child, ast.Try):
                        try_source = ast.get_source_segment(source, child) or ""
                        if "split" in try_source or "int(" in try_source or "ValueError" in try_source:
                            has_cron_error_handling = True
                            break
    except SyntaxError:
        pass

    # Check for len() validation on cron parts
    has_cron_len_check = any(pattern in func_code for pattern in [
        "len(parts)", "len(cron", "!= 5", "< 5",
    ])

    # Check for graceful None handling on ack_date comparison
    has_none_guard = any(pattern in func_code for pattern in [
        "if task_state", "if state.tasks.get",
        "task_state is not None", "and task_state",
        "ack_date is not None", "if ack_date",
    ])

    if uses_safe_state_access and has_none_guard:
        score += 0.4
        details.append("should_fire uses safe state access with None guards")
    elif uses_safe_state_access or has_none_guard:
        score += 0.2
        details.append("should_fire has partial safe access patterns")
    else:
        details.append("should_fire uses unsafe direct access patterns")

    if has_cron_error_handling:
        score += 0.4
        details.append("should_fire has try/except for cron parsing errors")
    elif has_cron_len_check:
        score += 0.2
        details.append("should_fire validates cron field count")
    else:
        details.append("should_fire does not guard against malformed cron")

    # Bonus: check if it handles the case where task_id not yet in state gracefully
    handles_missing_state = any(pattern in func_code for pattern in [
        "if task_id not in state", "if task_id in state",
        "state.tasks.get(task_id, ", "state.tasks.get(task_id)",
    ])
    if handles_missing_state:
        score += 0.2
        details.append("should_fire handles missing state entry")

    return min(score, 1.0), "; ".join(details)


def grade_workspace(ws: Path) -> dict:
    """Grade the scheduler refactoring."""
    # Find scheduler.py
    scheduler_path = None
    config_path = None

    for candidate in [
        ws / "fixtures" / "scheduler" / "scheduler.py",
        ws / "scheduler" / "scheduler.py",
    ]:
        if candidate.exists():
            scheduler_path = candidate
            break

    for candidate in [
        ws / "fixtures" / "scheduler" / "config.yaml",
        ws / "scheduler" / "config.yaml",
    ]:
        if candidate.exists():
            config_path = candidate
            break

    if not scheduler_path:
        return {
            "overall_score": 0.0,
            "components": {},
            "error": "scheduler.py not found in expected locations",
        }

    source = _read(scheduler_path)
    config_text = _read(config_path) if config_path else ""

    components = {}

    # Dimension 1: Timezone fix (weight 0.10)
    tz_score, tz_detail = _check_timezone(source, config_text)
    components["timezone_fix"] = {"score": round(tz_score, 4), "detail": tz_detail}

    # Dimension 2: Ack suppression in should_fire (weight 0.12)
    fire_score, fire_detail = _check_ack_suppression_fire(source)
    components["ack_suppression_fire"] = {"score": round(fire_score, 4), "detail": fire_detail}

    # Dimension 3: Ack suppression in should_retry (weight 0.10)
    retry_score, retry_detail = _check_ack_suppression_retry(source)
    components["ack_suppression_retry"] = {"score": round(retry_score, 4), "detail": retry_detail}

    # Dimension 4: add_task implementation (weight 0.08)
    add_score, add_detail = _check_add_task(source)
    components["add_task_impl"] = {"score": round(add_score, 4), "detail": add_detail}

    # Dimension 5: Config file updated (weight 0.08)
    cfg_score, cfg_detail = _check_config_updated(config_text)
    components["config_updated"] = {"score": round(cfg_score, 4), "detail": cfg_detail}

    # === Hidden harder checks (weight 0.55 total) ===

    # Dimension 6: add_task input validation & duplicate handling (weight 0.14)
    val_score, val_detail = _check_add_task_validation(source)
    components["add_task_validation"] = {"score": round(val_score, 4), "detail": val_detail}

    # Dimension 7: get_now reads timezone dynamically from config (weight 0.10)
    dyn_score, dyn_detail = _check_timezone_dynamic(source)
    components["timezone_dynamic"] = {"score": round(dyn_score, 4), "detail": dyn_detail}

    # Dimension 8: CLI add subcommand properly wired (weight 0.08)
    cli_score, cli_detail = _check_cli_add_wired(source)
    components["cli_add_wired"] = {"score": round(cli_score, 4), "detail": cli_detail}

    # Dimension 9: add_task uses atomic write pattern (weight 0.10)
    atomic_score, atomic_detail = _check_add_task_atomic_write(source)
    components["add_task_atomic_write"] = {"score": round(atomic_score, 4), "detail": atomic_detail}

    # Dimension 10: acknowledge_task validates task_id against config (weight 0.08)
    ack_val_score, ack_val_detail = _check_acknowledge_validates_config(source)
    components["ack_validates_config"] = {"score": round(ack_val_score, 4), "detail": ack_val_detail}

    # Dimension 11: should_fire handles edge cases (weight 0.05)
    edge_score, edge_detail = _check_should_fire_edge_cases(source)
    components["should_fire_edge_cases"] = {"score": round(edge_score, 4), "detail": edge_detail}

    weights = {
        "timezone_fix": 0.10,
        "ack_suppression_fire": 0.12,
        "ack_suppression_retry": 0.10,
        "add_task_impl": 0.08,
        "config_updated": 0.08,
        "add_task_validation": 0.14,
        "timezone_dynamic": 0.10,
        "cli_add_wired": 0.08,
        "add_task_atomic_write": 0.10,
        "ack_validates_config": 0.05,
        "should_fire_edge_cases": 0.05,
    }

    overall = sum(weights[k] * components[k]["score"] for k in weights)

    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v["score"], 4) for k, v in components.items()},
        "details": {k: v["detail"] for k, v in components.items()},
        "weights": weights,
    }


def main():
    ws = Path("/workspace")
    result = grade_workspace(ws)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
