"""Hidden verifier for CP168 — SQLite health check severity misclassification fix."""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_file(ws: Path, filename: str) -> Path | None:
    """Find a file in workspace, checking expected paths first."""
    candidates = [
        ws / "fixtures" / "report-server" / "app" / filename,
        ws / "report-server" / "app" / filename,
        ws / "app" / filename,
    ]
    for c in candidates:
        if c.exists():
            return c
    # Fallback: recursive search
    for p in ws.rglob(filename):
        return p
    return None


def check_health_function_separation(db_code: str) -> dict:
    """Check that check_db_health separates issues from warnings."""
    result = {"has_warnings_field": False, "size_not_in_issues": False, "wal_not_in_issues": False}

    # Check if the function returns a 'warnings' key (separate from issues)
    if "warnings" in db_code:
        # Look for pattern where warnings list is created and size/wal appended to it
        # Could be: warnings = [], result["warnings"], etc.
        if re.search(r'warnings\s*[=:]\s*\[', db_code) or re.search(r'["\']warnings["\']\s*:', db_code):
            result["has_warnings_field"] = True

    # Check that size threshold no longer causes healthy=False
    # The key fix: size > X should NOT be appended to issues
    try:
        tree = ast.parse(db_code)
    except SyntaxError:
        return result

    # Look at the check_db_health function
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "check_db_health":
            func_code = ast.get_source_segment(db_code, node) or ""

            # Check if size comparison still appends to issues
            # Pattern: if size_mb > X: issues.append(...)
            size_in_issues = bool(re.search(
                r'size.*>.*\d+.*\n\s*issues\.append', func_code, re.MULTILINE
            ))
            # Also check inline pattern: issues.append(...size...too large...)
            size_in_issues = size_in_issues or bool(re.search(
                r'issues\.append\([^)]*(?:size|too large|MB)', func_code
            ))

            result["size_not_in_issues"] = not size_in_issues

            # Check WAL file SIZE no longer in issues (note: "journal mode != WAL" IS a valid issue)
            wal_size_in_issues = bool(re.search(
                r'wal_size.*>.*\d+.*\n\s*issues\.append', func_code, re.MULTILINE
            ))
            wal_size_in_issues = wal_size_in_issues or bool(re.search(
                r'issues\.append\([^)]*(?:WAL file|wal.*large|WAL.*too)', func_code
            ))
            result["wal_not_in_issues"] = not wal_size_in_issues
            break

    return result


def check_recovery_safety(db_code: str) -> dict:
    """Check that recover_database no longer deletes WAL/SHM files."""
    result = {"no_wal_deletion": False, "no_shm_deletion": False}

    try:
        tree = ast.parse(db_code)
    except SyntaxError:
        return result

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "recover_database":
            func_code = ast.get_source_segment(db_code, node) or ""

            # Check for os.remove on WAL path
            has_wal_remove = bool(re.search(
                r'os\.remove\([^)]*wal', func_code, re.IGNORECASE
            ))
            # Also check Path.unlink or shutil.rmtree patterns
            has_wal_remove = has_wal_remove or bool(re.search(
                r'unlink\([^)]*wal', func_code, re.IGNORECASE
            ))

            has_shm_remove = bool(re.search(
                r'os\.remove\([^)]*shm', func_code, re.IGNORECASE
            ))
            has_shm_remove = has_shm_remove or bool(re.search(
                r'unlink\([^)]*shm', func_code, re.IGNORECASE
            ))

            result["no_wal_deletion"] = not has_wal_remove
            result["no_shm_deletion"] = not has_shm_remove
            break

    return result


def check_healthy_logic(db_code: str) -> dict:
    """Check that healthy flag only depends on functional issues, not size.

    The key insight: healthy should be True even when size is large. We check that:
    1. The healthy flag is derived from issues/errors (not directly from size)
    2. Size-related checks do NOT influence the healthy flag
    """
    result = {"healthy_correct": False}

    try:
        tree = ast.parse(db_code)
    except SyntaxError:
        return result

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "check_db_health":
            func_code = ast.get_source_segment(db_code, node) or ""

            # Check that size is NOT in the issues list that determines healthy
            size_in_issues = bool(re.search(
                r'issues\.append\([^)]*(?:size|too large|MB)', func_code
            )) or bool(re.search(
                r'size.*>.*\d+.*\n\s*issues\.append', func_code, re.MULTILINE
            ))

            # healthy must depend on issues (or critical/functional errors)
            has_healthy_derivation = bool(re.search(
                r'healthy.*(?:len\(issues\)\s*==\s*0|not\s+issues)', func_code
            )) or bool(re.search(
                r'["\']healthy["\']\s*:\s*(?:len\(issues\)\s*==\s*0|not\s+issues)', func_code
            )) or bool(re.search(
                r'healthy.*(?:critical|functional|error)', func_code, re.IGNORECASE
            ))

            # Both conditions must be met: size NOT in issues AND healthy derived correctly
            result["healthy_correct"] = (not size_in_issues) and has_healthy_derivation
            break

    return result


def check_main_handles_warnings(main_code: str) -> dict:
    """Check if main.py properly handles the new warnings field."""
    result = {"logs_warnings": False}

    # Check if main.py references warnings from health check
    if re.search(r'health.*(?:get|\.)\s*\(?["\']warnings', main_code):
        result["logs_warnings"] = True
    elif re.search(r'warnings.*=.*health', main_code):
        result["logs_warnings"] = True

    return result


def check_syntax_valid(db_code: str, main_code: str) -> dict:
    """Check that both files are valid Python."""
    result = {"db_valid": False, "main_valid": False}
    try:
        ast.parse(db_code)
        result["db_valid"] = True
    except SyntaxError:
        pass
    try:
        ast.parse(main_code)
        result["main_valid"] = True
    except SyntaxError:
        pass
    return result


# ---------------------------------------------------------------------------
# HIDDEN CHECKS — These verify deeper code quality that only strong models get
# ---------------------------------------------------------------------------


def check_recovery_uses_checkpoint(db_code: str) -> dict:
    """Check that recover_database uses WAL checkpoint as a safer alternative.

    The correct fix for strategy 2 is not just removing WAL deletion, but replacing
    it with a safer approach: using PRAGMA wal_checkpoint to safely flush the WAL
    to the main database file. This is the standard SQLite best practice.
    """
    result = {"has_checkpoint": False}

    try:
        tree = ast.parse(db_code)
    except SyntaxError:
        return result

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "recover_database":
            func_code = ast.get_source_segment(db_code, node) or ""

            # Check for wal_checkpoint pragma (the correct safe approach)
            has_checkpoint = bool(re.search(
                r'wal_checkpoint', func_code, re.IGNORECASE
            ))
            # Also accept PRAGMA checkpoint variants
            has_checkpoint = has_checkpoint or bool(re.search(
                r'PRAGMA\s+wal_checkpoint', func_code, re.IGNORECASE
            ))
            # Also accept sqlite3 backup API as alternative safe approach
            has_checkpoint = has_checkpoint or bool(re.search(
                r'\.backup\s*\(', func_code
            ))

            result["has_checkpoint"] = has_checkpoint
            break

    return result


def check_warnings_in_all_return_paths(db_code: str) -> dict:
    """Check that the warnings field is included in ALL return paths of check_db_health.

    A common weak-model mistake: only add 'warnings' to the final return dict
    but forget the early-return paths (e.g., when file doesn't exist, or read fails).
    A robust fix ensures every return path includes warnings=[] for consistent API.
    """
    result = {"all_paths_have_warnings": False}

    try:
        tree = ast.parse(db_code)
    except SyntaxError:
        return result

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "check_db_health":
            func_code = ast.get_source_segment(db_code, node) or ""

            # Count return statements in the function
            return_count = len(re.findall(r'\breturn\b', func_code))
            if return_count == 0:
                break

            # Count return statements that include 'warnings' key
            # Pattern: return {..., "warnings": ..., ...} or return dict with warnings
            returns_with_warnings = len(re.findall(
                r'return\s*\{[^}]*["\']warnings["\']', func_code
            ))
            # Also check for variable-based returns where warnings is set earlier
            # If warnings var is defined at top and all returns use a dict that includes it
            has_warnings_var_early = bool(re.search(
                r'warnings\s*=\s*\[\]', func_code[:len(func_code)//3]
            ))

            if has_warnings_var_early and returns_with_warnings >= return_count - 1:
                # Acceptable: warnings var defined early and most returns include it
                result["all_paths_have_warnings"] = True
            elif returns_with_warnings >= return_count:
                result["all_paths_have_warnings"] = True
            break

    return result


def check_connection_cleanup_on_error(db_code: str) -> dict:
    """Check that database connections are properly closed on error paths.

    The original code has a resource leak: if check 3 or 4 fails, the connection
    opened in check 2 may not be closed. A strong fix uses try/finally or context
    manager to ensure cleanup.
    """
    result = {"has_proper_cleanup": False}

    try:
        tree = ast.parse(db_code)
    except SyntaxError:
        return result

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "check_db_health":
            func_code = ast.get_source_segment(db_code, node) or ""

            # Check for try/finally with conn.close()
            has_try_finally = bool(re.search(
                r'finally\s*:\s*\n\s*.*(?:conn|connection).*close', func_code
            ))
            # Check for context manager (with sqlite3.connect(...) as conn:)
            has_context_mgr = bool(re.search(
                r'with\s+sqlite3\.connect', func_code
            ))
            # Check for contextlib.closing
            has_closing = bool(re.search(
                r'closing\s*\(\s*sqlite3\.connect', func_code
            ))

            result["has_proper_cleanup"] = has_try_finally or has_context_mgr or has_closing
            break

    return result


def check_no_hardcoded_thresholds(db_code: str) -> dict:
    """Check that size thresholds are defined as named constants, not magic numbers.

    A well-written fix extracts the 500MB and 100MB thresholds into module-level
    constants or function parameters, making them configurable and self-documenting.
    Magic numbers scattered in conditionals are a code quality red flag.
    """
    result = {"thresholds_named": False}

    try:
        tree = ast.parse(db_code)
    except SyntaxError:
        return result

    # Check for module-level constants related to thresholds
    # Pattern: DB_SIZE_THRESHOLD = 500, MAX_WAL_SIZE = 100, etc.
    has_size_constant = bool(re.search(
        r'^[A-Z][A-Z_0-9]*\s*(?::\s*\w+\s*)?=\s*(?:500|1000|1024)',
        db_code, re.MULTILINE
    ))
    has_wal_constant = bool(re.search(
        r'^[A-Z][A-Z_0-9]*\s*(?::\s*\w+\s*)?=\s*100',
        db_code, re.MULTILINE
    ))

    # Also accept function parameters with defaults
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "check_db_health":
            # Check if function accepts threshold parameters
            args = [a.arg for a in node.args.args]
            if any("threshold" in a or "limit" in a or "max_size" in a for a in args):
                has_size_constant = True
                has_wal_constant = True
            break

    result["thresholds_named"] = has_size_constant or has_wal_constant
    return result


def check_main_no_recovery_on_warnings_only(main_code: str) -> dict:
    """Check that main.py does NOT trigger recovery when only warnings are present.

    The fix must ensure that recovery is only triggered when health["healthy"] is False
    due to actual issues, and that the presence of warnings alone does not lead to
    recovery. A weak fix might check warnings but still accidentally trigger recovery
    if the logic isn't carefully separated.
    """
    result = {"recovery_guarded": False}

    # The key: recovery should ONLY be called when healthy is False
    # Check that there's no path where warnings alone trigger recovery

    # Look for pattern: if not health["healthy"] or if health["healthy"] == False
    # followed by recovery, which is correct
    has_healthy_guard = bool(re.search(
        r'if\s+not\s+health\s*\[\s*["\']healthy["\']\s*\]', main_code
    )) or bool(re.search(
        r'if\s+health\s*\[\s*["\']healthy["\']\s*\]\s*(?:==\s*False|is\s+False)', main_code
    )) or bool(re.search(
        r'if\s+not\s+health\s*\.get\s*\(\s*["\']healthy["\']', main_code
    ))

    # Check that warnings are NOT used as a trigger for recovery
    # Exclude comments/strings that explicitly say "do not trigger" or "not trigger"
    warnings_trigger_recovery = bool(re.search(
        r'if\s+.*warning.*:\s*\n\s*.*recover', main_code, re.IGNORECASE
    )) or bool(re.search(
        r'if\s+.*warning.*recover_database', main_code, re.IGNORECASE
    ))
    # But don't count comments that say "do not trigger recovery" as a negative signal
    has_negation_comment = bool(re.search(
        r'#.*(?:do not|don\'t|not).*trigger.*recover', main_code, re.IGNORECASE
    )) or bool(re.search(
        r'#.*warning.*(?:do not|don\'t|not).*recover', main_code, re.IGNORECASE
    ))
    if has_negation_comment:
        warnings_trigger_recovery = False

    result["recovery_guarded"] = has_healthy_guard and not warnings_trigger_recovery
    return result


def check_docstring_updated(db_code: str) -> dict:
    """Check that check_db_health's docstring reflects the new return type.

    After adding the 'warnings' field, the docstring must be updated to document
    the new return value shape. A strong model updates docs alongside code; a weak
    model only changes logic and leaves stale documentation.
    """
    result = {"docstring_updated": False}

    try:
        tree = ast.parse(db_code)
    except SyntaxError:
        return result

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "check_db_health":
            docstring = ast.get_docstring(node) or ""

            # The docstring must mention 'warnings' in the return description
            mentions_warnings_return = bool(re.search(
                r'warnings', docstring, re.IGNORECASE
            ))
            # Should no longer claim size > 500MB is "abnormal" in a way that
            # implies it's a failure - or should clarify it's informational
            # The old docstring says "5. Database file size is not abnormal (>500MB considered abnormal)"
            # A good fix removes or rewords this to indicate it's a warning, not a failure
            still_says_abnormal_as_check = bool(re.search(
                r'(?:5|6)\.\s*(?:Database|WAL|SHM).*(?:abnormal|considered abnormal)',
                docstring
            ))
            # If old language remains unchanged, docstring was not updated
            has_stale_return_doc = bool(re.search(
                r'Returns:.*healthy.*issues.*size_mb', docstring, re.DOTALL
            )) and not mentions_warnings_return

            result["docstring_updated"] = mentions_warnings_return and not has_stale_return_doc
            break

    return result


def check_recovery_strategy2_explains_skip(db_code: str) -> dict:
    """Check that recover_database strategy 2 has a comment or log explaining why
    WAL/SHM deletion was removed.

    A strong model doesn't just delete dangerous code silently - it leaves a comment
    or log explaining why the operation was removed and what safer alternative is used.
    This is critical for incident response: future developers need to understand WHY
    the dangerous code was removed to avoid re-introducing it.
    """
    result = {"explains_removal": False}

    try:
        tree = ast.parse(db_code)
    except SyntaxError:
        return result

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "recover_database":
            func_code = ast.get_source_segment(db_code, node) or ""

            # Check for comment explaining WHY WAL deletion is removed/dangerous
            has_explanation_comment = bool(re.search(
                r'#.*(?:dangerous|corrupt|data loss|removed|do not|never|unsafe|'
                r'skip.*wal|wal.*skip|not.*delet|avoid.*delet)',
                func_code, re.IGNORECASE
            ))
            # Also accept a print/log statement explaining the skip
            has_explanation_log = bool(re.search(
                r'(?:print|log|logger)\s*\([^)]*(?:skip|dangerous|unsafe|corrupt|'
                r'not.*remov|avoid|checkpoint instead)',
                func_code, re.IGNORECASE
            ))

            result["explains_removal"] = has_explanation_comment or has_explanation_log
            break

    return result


def check_health_returns_issue_count(db_code: str) -> dict:
    """Check that the health check return value includes explicit issue/warning counts.

    A production-quality fix adds numeric counts to the return dict for easy
    monitoring/alerting integration (e.g., issue_count, warning_count). This enables
    downstream consumers to threshold on counts without parsing lists. Strong models
    think about API consumers; weak models only fix the immediate bug.
    """
    result = {"has_counts": False}

    try:
        tree = ast.parse(db_code)
    except SyntaxError:
        return result

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "check_db_health":
            func_code = ast.get_source_segment(db_code, node) or ""

            # Check for explicit count fields in return dict
            has_issue_count = bool(re.search(
                r'["\'](?:issue_count|num_issues|error_count|issues_count)["\']\s*:', func_code
            ))
            has_warning_count = bool(re.search(
                r'["\'](?:warning_count|num_warnings|warnings_count)["\']\s*:', func_code
            ))
            # Also accept len() being stored in a variable used in return
            has_len_pattern = bool(re.search(
                r'len\(issues\)', func_code
            )) and bool(re.search(
                r'len\(warnings\)', func_code
            ))

            result["has_counts"] = (has_issue_count and has_warning_count) or has_len_pattern
            break

    return result


def grade_workspace(ws: Path) -> dict:
    """Grade the workspace fix."""
    db_file = _find_file(ws, "database.py")
    main_file = _find_file(ws, "main.py")

    db_code = _read(db_file) if db_file else ""
    main_code = _read(main_file) if main_file else ""

    components = {}

    # --- BASIC CHECKS (reduced weight) ---

    # Dimension 1: Syntax validity (baseline, easy)
    syntax = check_syntax_valid(db_code, main_code)
    components["syntax_valid"] = 1.0 if (syntax["db_valid"] and syntax["main_valid"]) else 0.0

    # Dimension 2: Severity separation (issues vs warnings)
    separation = check_health_function_separation(db_code)
    sep_score = 0.0
    if separation["has_warnings_field"]:
        sep_score += 0.4
    if separation["size_not_in_issues"]:
        sep_score += 0.3
    if separation["wal_not_in_issues"]:
        sep_score += 0.3
    components["severity_separation"] = round(sep_score, 4)

    # Dimension 3: Recovery safety (no WAL/SHM deletion)
    recovery = check_recovery_safety(db_code)
    rec_score = 0.0
    if recovery["no_wal_deletion"]:
        rec_score += 0.5
    if recovery["no_shm_deletion"]:
        rec_score += 0.5
    components["recovery_safety"] = round(rec_score, 4)

    # Dimension 4: Healthy logic correctness
    healthy = check_healthy_logic(db_code)
    components["healthy_logic"] = 1.0 if healthy["healthy_correct"] else 0.0

    # Dimension 5: Main.py integration (handles warnings)
    main_check = check_main_handles_warnings(main_code)
    components["main_integration"] = 1.0 if main_check["logs_warnings"] else 0.0

    # --- HIDDEN HARDER CHECKS (higher weight, distinguish strong from weak) ---

    # Dimension 6: Recovery uses checkpoint (safer WAL handling)
    checkpoint = check_recovery_uses_checkpoint(db_code)
    components["recovery_checkpoint"] = 1.0 if checkpoint["has_checkpoint"] else 0.0

    # Dimension 7: Warnings field in ALL return paths (API consistency)
    all_paths = check_warnings_in_all_return_paths(db_code)
    components["warnings_all_paths"] = 1.0 if all_paths["all_paths_have_warnings"] else 0.0

    # Dimension 8: Connection cleanup on error (resource management)
    cleanup = check_connection_cleanup_on_error(db_code)
    components["connection_cleanup"] = 1.0 if cleanup["has_proper_cleanup"] else 0.0

    # Dimension 9: Named constants for thresholds (code quality)
    thresholds = check_no_hardcoded_thresholds(db_code)
    components["thresholds_named"] = 1.0 if thresholds["thresholds_named"] else 0.0

    # Dimension 10: Main.py recovery only on actual failures
    guard = check_main_no_recovery_on_warnings_only(main_code)
    components["recovery_guarded"] = 1.0 if guard["recovery_guarded"] else 0.0

    # Dimension 11: Docstring updated to reflect new return type
    docstring = check_docstring_updated(db_code)
    components["docstring_updated"] = 1.0 if docstring["docstring_updated"] else 0.0

    # Dimension 12: Strategy 2 has comment/log explaining why WAL deletion removed
    explains = check_recovery_strategy2_explains_skip(db_code)
    components["recovery_explains_skip"] = 1.0 if explains["explains_removal"] else 0.0

    # Dimension 13: Health check returns explicit issue/warning counts
    counts = check_health_returns_issue_count(db_code)
    components["health_has_counts"] = 1.0 if counts["has_counts"] else 0.0

    # Weights: basic checks reduced, hidden checks dominate (total 0.62)
    # Target: weak model gets basic (0.38 max) = ~0.4-0.6
    #          strong model gets basic + most hidden = ~0.7-0.85
    weights = {
        "syntax_valid": 0.04,
        "severity_separation": 0.10,
        "recovery_safety": 0.09,
        "healthy_logic": 0.08,
        "main_integration": 0.07,
        # Hidden harder checks (total 0.62)
        "recovery_checkpoint": 0.12,
        "warnings_all_paths": 0.10,
        "connection_cleanup": 0.09,
        "thresholds_named": 0.05,
        "recovery_guarded": 0.07,
        "docstring_updated": 0.08,
        "recovery_explains_skip": 0.06,
        "health_has_counts": 0.05,
    }

    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    print(json.dumps(grade_workspace(Path("/workspace")), ensure_ascii=False))


if __name__ == "__main__":
    main()
