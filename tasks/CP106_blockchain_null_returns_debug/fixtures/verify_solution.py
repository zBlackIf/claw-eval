"""Hidden verifier for CP106 — Blockchain file sync null returns debug."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def grade_workspace(ws: Path) -> dict:
    """Grade the workspace for null pointer fix quality."""
    base = ws / "fixtures" / "cn-naf-fm-xw" / "src" / "main" / "java" / "com" / "zte" / "ums" / "xw" / "fm"
    if not base.exists():
        base = ws / "cn-naf-fm-xw" / "src" / "main" / "java" / "com" / "zte" / "ums" / "xw" / "fm"
    sync_file = base / "service" / "filesync" / "XwFmSyncFileQueryProcess.java"

    components = {
        "null_check_added": 0.0,
        "no_null_string_in_path": 0.0,
        "proper_error_handling": 0.0,
        "downstream_protection": 0.0,
        "logging_added": 0.0,
        "no_regression": 0.0,
    }

    if not sync_file.exists():
        return {
            "overall_score": 0.0,
            "components": components,
            "weights": _weights(),
        }

    content = _read(sync_file)

    # --- Check 1: Null check added for getRmUidEntityByRuid return ---
    # The fix must check if rmUidEntityByRuid is null before calling .getNafnetype()
    has_null_check = False
    # Look for patterns like: if (rmUidEntityByRuid != null) or rmUidEntityByRuid != null ? ...
    null_check_patterns = [
        r"rmUidEntityByRuid\s*!=\s*null",
        r"rmUidEntityByRuid\s*==\s*null",
        r"null\s*!=\s*rmUidEntityByRuid",
        r"null\s*==\s*rmUidEntityByRuid",
        r"Objects\.(?:nonNull|isNull)\s*\(\s*rmUidEntityByRuid\s*\)",
        r"Optional\.ofNullable\s*\(\s*rmUidEntityByRuid\s*\)",
    ]
    for pat in null_check_patterns:
        if re.search(pat, content):
            has_null_check = True
            break
    components["null_check_added"] = 1.0 if has_null_check else 0.0

    # --- Check 2 (HIDDEN): No "null" string in path construction ---
    # A naive fix (neType = null) leads to "null" appearing in StringBuilder paths.
    # Strong agents recognize that getRemoteDir(neType) with neType=null produces "/HX/ZC/.../null/FM/..."
    # They should use a default value like "UNKNOWN" or throw, not just assign null.
    get_ne_type_method = _extract_method(content, "getNeType")
    assigns_literal_null = False
    if get_ne_type_method:
        # Check if the else branch could produce a null neType that flows to getRemoteDir
        # Bad: neType = rmUidEntityByRuid != null ? rmUidEntityByRuid.getNafnetype() : null;
        # Good: neType = rmUidEntityByRuid != null ? rmUidEntityByRuid.getNafnetype() : "UNKNOWN";
        if re.search(r":\s*null\s*;", get_ne_type_method):
            assigns_literal_null = True
        if re.search(r"neType\s*=\s*null\s*;", get_ne_type_method):
            assigns_literal_null = True
        # Also check: if the null check returns early without assigning
        if re.search(r"return\s+null\s*;", get_ne_type_method):
            assigns_literal_null = True

    # Check process() method too - if neType can be null there
    process_method = _extract_method(content, "process")
    if process_method:
        # Does process() handle null neType from getNeType()?
        has_process_null_guard = bool(re.search(r"neType\s*(?:!=|==)\s*null", process_method))
        if has_process_null_guard:
            assigns_literal_null = False  # They handled it at caller level

    if not assigns_literal_null:
        components["no_null_string_in_path"] = 1.0
    else:
        components["no_null_string_in_path"] = 0.0

    # --- Check 3: Proper error handling (not just swallowing) ---
    # A good fix should either: throw a meaningful exception, use a default with logging,
    # or return early with an error. Simple ternary with null is insufficient.
    has_proper_handling = False
    if get_ne_type_method:
        # Throwing with message
        if re.search(r"throw\s+new\s+\w+Exception", get_ne_type_method):
            has_proper_handling = True
        # Using a sensible default (non-null, non-empty)
        if re.search(r'(?:neType\s*=\s*|:\s*)"[A-Z_]+"', get_ne_type_method):
            has_proper_handling = True
        # Early return with meaningful value
        if re.search(r'return\s+"[A-Z_]+"', get_ne_type_method):
            has_proper_handling = True
    # Also accept if process() handles the null case
    if process_method and re.search(r"neType\s*(?:!=|==)\s*null", process_method):
        has_proper_handling = True

    components["proper_error_handling"] = 1.0 if has_proper_handling else 0.0

    # --- Check 4 (HIDDEN): Downstream protection for getRemoteDir and createUpSynFile ---
    # Strong agents trace through and realize neType flows to:
    # 1. getRemoteDir() - StringBuilder.append(neType)
    # 2. createUpSynFile() - xwFileNameGenarater.generateFileName(neType, ...)
    # Both produce broken output with null. Best fix addresses root + downstream.
    downstream_score = 0.0

    # Check if getRemoteDir validates its parameter
    get_remote_dir = _extract_method(content, "getRemoteDir")
    if get_remote_dir:
        if re.search(r"neType\s*(?:==|!=)\s*null", get_remote_dir):
            downstream_score += 0.5
        if re.search(r"(?:isEmpty|isBlank|StringUtils)", get_remote_dir):
            downstream_score += 0.5

    # Or check if process() method guards before calling getRemoteDir/createUpSynFile
    if process_method:
        if re.search(r"neType\s*(?:==|!=)\s*null", process_method):
            downstream_score += 0.5
        if re.search(r"(?:isEmpty|isBlank|StringUtils).*neType", process_method):
            downstream_score += 0.5

    # If getNeType itself guarantees non-null return (throws or defaults), give full credit
    if get_ne_type_method:
        guaranteed_non_null = (
            re.search(r"throw\s+new\s+\w+Exception", get_ne_type_method) or
            (re.search(r'(?:neType\s*=\s*|:\s*)"[A-Z_]+"', get_ne_type_method) and
             not re.search(r"(?:return|=)\s*null", get_ne_type_method))
        )
        if guaranteed_non_null:
            downstream_score = 1.0

    components["downstream_protection"] = min(1.0, downstream_score)

    # --- Check 5 (HIDDEN): Logging added for the null case ---
    # Professional fix should log a warning/error when the entity is null
    has_logging = False
    if get_ne_type_method:
        if re.search(r"log\.\s*(?:warn|error|info)\s*\(.*(?:null|not found|getRmUidEntity)", get_ne_type_method, re.IGNORECASE):
            has_logging = True
    if process_method:
        if re.search(r"log\.\s*(?:warn|error)\s*\(.*(?:neType|null|getNeType)", process_method, re.IGNORECASE):
            has_logging = True
    components["logging_added"] = 1.0 if has_logging else 0.0

    # --- Check 6: No regression (core structure preserved) ---
    # The fix must not break the overall flow:
    # - process() method still exists
    # - getNeType() method still exists
    # - getRemoteDir() method still exists
    # - createUpSynFile() method still exists
    no_regression_score = 0.0
    if "void process(" in content or "process(FmSyncFileRequest" in content:
        no_regression_score += 0.25
    if "getNeType(" in content:
        no_regression_score += 0.25
    if "getRemoteDir(" in content:
        no_regression_score += 0.25
    if "createUpSynFile(" in content:
        no_regression_score += 0.25
    components["no_regression"] = no_regression_score

    weights = _weights()
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def _weights() -> dict:
    return {
        "null_check_added": 0.25,
        "no_null_string_in_path": 0.20,
        "proper_error_handling": 0.20,
        "downstream_protection": 0.15,
        "logging_added": 0.10,
        "no_regression": 0.10,
    }


def _extract_method(content: str, method_name: str) -> str | None:
    """Extract a Java method body by name (heuristic brace-counting)."""
    # Find the method signature
    pattern = rf"(?:private|public|protected)?\s+\w+(?:<[^>]+>)?\s+{method_name}\s*\("
    match = re.search(pattern, content)
    if not match:
        return None

    start = match.start()
    # Find opening brace
    brace_start = content.find("{", match.end())
    if brace_start == -1:
        return None

    # Count braces to find end
    depth = 0
    i = brace_start
    while i < len(content):
        if content[i] == "{":
            depth += 1
        elif content[i] == "}":
            depth -= 1
            if depth == 0:
                return content[start:i + 1]
        i += 1
    return None


def main():
    print(json.dumps(grade_workspace(Path("/workspace")), ensure_ascii=False))


if __name__ == "__main__":
    main()
