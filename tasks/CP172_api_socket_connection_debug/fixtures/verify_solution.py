"""Hidden verifier for CP172 — API Socket Connection Debug.

Checks that the agent properly diagnosed and fixed the socket connection error
caused by protocol mismatch (http vs https) in the API client.

Key bugs to fix:
1. http.Agent used for https:// URL -> should be https.Agent
2. http.request used for https:// URL -> should be https.request
3. Missing 'Accept: text/event-stream' header for streaming SSE
4. Timeout not disabled/extended for streaming responses
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


def _strip_comments_and_strings(js_code: str) -> str:
    """Remove JS comments and string literals for accurate code pattern analysis."""
    # Remove multi-line comments
    code = re.sub(r"/\*.*?\*/", "", js_code, flags=re.DOTALL)
    # Remove single-line comments
    code = re.sub(r"//[^\n]*", "", code)
    # Remove template literals
    code = re.sub(r"`[^`]*`", '""', code)
    # Remove double-quoted strings (but keep the quotes as placeholder)
    code = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', '""', code)
    # Remove single-quoted strings
    code = re.sub(r"'[^'\\]*(?:\\.[^'\\]*)*'", "''", code)
    return code


def _strip_comments(js_code: str) -> str:
    """Remove JS comments only, keep strings intact for header value checks."""
    code = re.sub(r"/\*.*?\*/", "", js_code, flags=re.DOTALL)
    code = re.sub(r"//[^\n]*", "", code)
    return code


def grade_workspace(ws: Path) -> dict:
    # Look in both possible paths
    project_dir = ws / "fixtures" / "api-client-project"
    if not project_dir.exists():
        project_dir = ws / "api-client-project"
    if not project_dir.exists():
        for candidate in ws.rglob("api_client.js"):
            project_dir = candidate.parent.parent
            break
        else:
            return {"overall_score": 0.0, "components": {}, "error": "Project directory not found"}

    api_client_file = project_dir / "src" / "api_client.js"
    if not api_client_file.exists():
        for candidate in project_dir.rglob("api_client.js"):
            api_client_file = candidate
            break

    raw_content = _read(api_client_file)
    if not raw_content:
        return {"overall_score": 0.0, "components": {}, "error": "api_client.js not found or empty"}

    # For structure checks: strip comments and strings
    code_only = _strip_comments_and_strings(raw_content)
    # For header value checks: strip comments but keep strings
    code_with_strings = _strip_comments(raw_content)

    components = {
        "https_agent_fix": 0.0,
        "https_request_fix": 0.0,
        "accept_header_fix": 0.0,
        "streaming_timeout_fix": 0.0,
        "code_still_functional": 0.0,
    }

    # ----------------------------------------------------------------
    # Check 1: Uses https.Agent instead of http.Agent for https URLs
    # ----------------------------------------------------------------
    has_https_require = "require('https')" in code_with_strings or 'require("https")' in code_with_strings
    has_https_agent = "new https.Agent(" in code_only
    still_has_http_agent_only = "new http.Agent(" in code_only and "new https.Agent(" not in code_only

    if has_https_agent:
        components["https_agent_fix"] = 1.0
    elif has_https_require and not still_has_http_agent_only:
        # Imported https and removed http.Agent — partial credit
        components["https_agent_fix"] = 0.6
    elif still_has_http_agent_only:
        components["https_agent_fix"] = 0.0

    # ----------------------------------------------------------------
    # Check 2: Uses https.request instead of http.request for https URLs
    # ----------------------------------------------------------------
    has_https_request_call = "https.request(" in code_only
    has_only_http_request = "http.request(" in code_only and "https.request(" not in code_only
    # fetch/got/axios as complete replacement (check in code_only, not string literals)
    has_fetch_replacement = bool(re.search(r"=\s*(?:await\s+)?fetch\s*\(", code_only))
    has_got_or_axios = "got(" in code_only or "axios(" in code_only or "axios." in code_only
    has_protocol_conditional = bool(re.search(
        r"protocol.*https.*\.request\(|"
        r"https:\s*https\.request|"
        r"\?\s*https\s*:\s*http",
        code_only, re.DOTALL
    ))

    if has_https_request_call or has_protocol_conditional:
        components["https_request_fix"] = 1.0
    elif has_fetch_replacement or has_got_or_axios:
        components["https_request_fix"] = 1.0
    elif has_https_require and not has_only_http_request:
        components["https_request_fix"] = 0.7
    elif has_only_http_request:
        components["https_request_fix"] = 0.0

    # ----------------------------------------------------------------
    # Check 3: Accept header for streaming
    # ----------------------------------------------------------------
    # Must be actual header assignment with event-stream value
    has_accept_header = bool(re.search(
        r"""['"][Aa]ccept['"]\s*:\s*['"][^'"]*event-stream[^'"]*['"]""",
        code_with_strings
    ))
    has_dynamic_accept = bool(re.search(
        r"headers\[.*[Aa]ccept.*\]\s*=.*event-stream|"
        r"\.setHeader\s*\(.*[Aa]ccept.*event-stream",
        code_with_strings
    ))
    if has_accept_header or has_dynamic_accept:
        components["accept_header_fix"] = 1.0

    # ----------------------------------------------------------------
    # Check 4: Streaming timeout handling
    # ----------------------------------------------------------------
    # In the buggy code, req.setTimeout fires unconditionally.
    # Valid fixes:
    # a) Wrap setTimeout in `if (!params.stream)` guard
    # b) Use clearTimeout when response starts
    # c) Remove setTimeout entirely
    # d) Set timeout to 0 for streaming
    # e) Extend timeout significantly for streaming

    has_clear_timeout = "clearTimeout" in code_only
    has_timeout_removed = "setTimeout" not in code_only or "req.setTimeout" not in code_only

    # Check for conditional: setTimeout only for non-streaming
    # Must have the guard NEAR the setTimeout call, not just anywhere
    # Look for patterns like: if (!params.stream) { ... setTimeout ... }
    has_guarded_timeout = bool(re.search(
        r"if\s*\(\s*!params\.stream\s*\)[\s\S]{0,100}setTimeout|"
        r"if\s*\(\s*!params\.stream\s*\)[\s\S]{0,100}req\.setTimeout",
        code_only
    ))
    # Or: params.stream ? <no timeout logic> : setTimeout
    has_ternary_timeout = bool(re.search(
        r"params\.stream\s*\?\s*(0|null|undefined|Infinity).*timeout|"
        r"timeout.*params\.stream\s*\?\s*(0|null|undefined|Infinity)",
        code_only, re.IGNORECASE
    ))

    # Check if response event clears timeout
    has_res_clear = bool(re.search(
        r"res\)[\s\S]{0,50}clearTimeout|"
        r"on\s*\(\s*.*response.*clearTimeout",
        code_only
    ))

    if has_clear_timeout or has_guarded_timeout or has_ternary_timeout or has_res_clear:
        components["streaming_timeout_fix"] = 1.0
    elif has_timeout_removed:
        # Removed setTimeout entirely — acceptable but less precise
        components["streaming_timeout_fix"] = 0.8
    else:
        # Still has unconditional req.setTimeout
        if "req.setTimeout" in code_only:
            components["streaming_timeout_fix"] = 0.0
        else:
            components["streaming_timeout_fix"] = 0.3

    # ----------------------------------------------------------------
    # Check 5: Code is still functional
    # ----------------------------------------------------------------
    has_class = "class" in code_only and "ApiClient" in code_only
    has_chat_method = "chat(" in code_only
    has_request_logic = "request" in code_only or "fetch(" in code_only
    has_export = "module.exports" in code_only or "export" in code_only
    has_constructor = "constructor(" in code_only
    functional_checks = sum([has_class, has_chat_method, has_request_logic, has_export, has_constructor])
    components["code_still_functional"] = min(1.0, functional_checks / 4.0)

    weights = {
        "https_agent_fix": 0.25,
        "https_request_fix": 0.25,
        "accept_header_fix": 0.20,
        "streaming_timeout_fix": 0.15,
        "code_still_functional": 0.15,
    }

    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    ws = Path("/workspace/fixtures")
    if not (ws / "api-client-project").exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
