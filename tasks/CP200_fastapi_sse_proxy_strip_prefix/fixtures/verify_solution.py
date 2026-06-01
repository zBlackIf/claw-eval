"""Hidden verifier for CP200 - FastAPI SSE Proxy Strip Prefix.

Checks that the chat endpoint properly strips SSE "data: " prefix from upstream
lines before forwarding to the client.

Grading dimensions:
1. data_prefix_stripped: The "data: " prefix is removed from upstream SSE lines
2. empty_lines_handled: Empty SSE separator lines are properly handled (skipped or preserved without corruption)
3. done_signal_handled: The "[DONE]" termination signal is handled (stripped or converted)
4. error_format_preserved: Error responses still work (yield valid format)
5. non_sse_passthrough: Lines that don't start with "data: " are passed through unchanged
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


def _find_chat_router(ws: Path) -> str | None:
    """Find the chat.py router file."""
    candidates = [
        ws / "novel_platform_be" / "app" / "api" / "routers" / "chat.py",
        ws / "app" / "api" / "routers" / "chat.py",
    ]
    for c in candidates:
        if c.exists():
            return _read(c)
    # Search recursively
    for p in ws.rglob("chat.py"):
        content = _read(p)
        if "chat_with_novel" in content or "generate" in content:
            return content
    return None


def _find_generate_function(source: str) -> str | None:
    """Extract the generate() inner function body from the chat endpoint."""
    # Look for the async def generate() or def generate() function
    pattern = r'(async\s+def\s+generate\s*\(\s*\).*?)(?=\n    return|\n    \w|\Z)'
    match = re.search(pattern, source, re.DOTALL)
    if match:
        return match.group(1)
    return None


def grade_workspace(ws: Path) -> dict:
    components = {k: 0.0 for k in [
        "data_prefix_stripped",
        "empty_lines_handled",
        "done_signal_handled",
        "error_format_preserved",
        "non_sse_passthrough",
    ]}

    source = _find_chat_router(ws)
    if not source:
        return {
            "overall_score": 0.0,
            "components": components,
            "error": "Could not find chat.py router file",
        }

    gen_body = _find_generate_function(source)
    if not gen_body:
        # Fall back to examining the full source
        gen_body = source

    # --- Dimension 1: data prefix stripped ---
    # Check if there's logic to strip "data: " prefix
    strip_patterns = [
        r'line\s*\[\s*6\s*:\s*\]',           # line[6:]
        r'line\s*\[\s*len\s*\(\s*["\']data:\s*["\']\s*\)\s*:\s*\]',  # line[len("data: "):]
        r'\.lstrip\s*\(\s*["\']data:\s*["\']\s*\)',   # .lstrip("data: ")
        r'\.removeprefix\s*\(\s*["\']data:\s*["\']\s*\)',  # .removeprefix("data: ")
        r'\.replace\s*\(\s*["\']data:\s*["\']\s*,\s*["\']["\']\s*\)',  # .replace("data: ", "")
        r'line\.startswith\s*\(\s*["\']data:\s*["\']\s*\)',  # line.startswith("data: ")
        r'line\.startswith\s*\(\s*["\']data:["\']\s*\)',     # line.startswith("data:")
        r're\.sub\s*\(\s*["\'].*?data.*?["\']\s*,',  # re.sub pattern
    ]

    has_strip = False
    for pat in strip_patterns:
        if re.search(pat, gen_body):
            has_strip = True
            break

    # Also check for generic prefix strip logic
    if not has_strip:
        # Check if they split on "data: " and take second part
        if re.search(r'\.split\s*\(\s*["\']data:\s*["\']\s*', gen_body):
            has_strip = True

    if has_strip:
        # Verify the stripped content is what gets yielded
        # Check yield statement uses the stripped version
        if re.search(r'yield\s+', gen_body):
            components["data_prefix_stripped"] = 1.0
        else:
            components["data_prefix_stripped"] = 0.5
    else:
        # No strip logic found - score 0
        components["data_prefix_stripped"] = 0.0

    # --- Dimension 2: empty lines handled ---
    # The fix must retain "if line:" filtering AND strip prefix.
    # Both conditions needed for full credit.
    has_line_filter = bool(re.search(r'if\s+line\s*:', gen_body) or re.search(r'if\s+(not\s+)?line', gen_body))
    if has_line_filter and has_strip:
        components["empty_lines_handled"] = 1.0
    elif has_line_filter:
        # Has filter but no strip - original buggy state
        components["empty_lines_handled"] = 0.3
    elif has_strip:
        # Has strip but removed filter - partial
        components["empty_lines_handled"] = 0.5
    else:
        components["empty_lines_handled"] = 0.0

    # --- Dimension 3: done signal handled ---
    # Check if [DONE] is handled (either stripped, skipped, or converted)
    done_patterns = [
        r'\[DONE\]',
        r'\[done\]',
        r'== \s*["\']data:\s*\[DONE\]',
        r'DONE',
        r'strip.*==.*\[DONE\]',
        r'endswith.*DONE',
    ]
    has_done_handling = False
    for pat in done_patterns:
        if re.search(pat, gen_body):
            has_done_handling = True
            break

    if has_done_handling:
        components["done_signal_handled"] = 1.0
    else:
        # If they strip "data: " generically, [DONE] becomes just "[DONE]"
        # which is acceptable behavior (partial credit)
        if has_strip:
            components["done_signal_handled"] = 0.6
        else:
            components["done_signal_handled"] = 0.0

    # --- Dimension 4: error format preserved ---
    # Check that the error handling yield is still present and functional
    if re.search(r'yield\s+f?["\'].*error.*["\']', source):
        components["error_format_preserved"] = 1.0
    elif "error" in source and "except" in source:
        components["error_format_preserved"] = 0.7
    else:
        components["error_format_preserved"] = 0.0

    # --- Dimension 5: non-SSE passthrough ---
    # Check if lines NOT starting with "data: " are handled
    # Good implementations check startswith before stripping
    if re.search(r'startswith\s*\(\s*["\']data', gen_body):
        # Has conditional check - only strips when prefix exists
        if re.search(r'else\s*:', gen_body) and re.search(r'yield\s+line', gen_body):
            components["non_sse_passthrough"] = 1.0
        else:
            # Has the check but might not have explicit else
            components["non_sse_passthrough"] = 0.8
    elif has_strip:
        # Strips unconditionally - could break non-SSE lines
        # But for this use case it's mostly acceptable
        components["non_sse_passthrough"] = 0.4
    else:
        components["non_sse_passthrough"] = 0.0

    weights = {
        "data_prefix_stripped": 0.40,
        "empty_lines_handled": 0.15,
        "done_signal_handled": 0.15,
        "error_format_preserved": 0.15,
        "non_sse_passthrough": 0.15,
    }

    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    ws = Path("/workspace/fixtures/novel_platform_be")
    if not ws.exists():
        ws = Path("/workspace/novel_platform_be")
    if not ws.exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
