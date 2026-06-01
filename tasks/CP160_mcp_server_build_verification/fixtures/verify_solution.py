#!/usr/bin/env python3
"""Hidden verifier for CP160 - MCP Server Build Verification Tools.

Checks that the agent created a valid MCP server exposing build verification tools.
Grading dimensions:
  1. server_exists: server.py file exists and is importable
  2. uses_mcp_library: properly imports and uses the mcp package
  3. tools_registered: all 5 required tools are defined
  4. stdio_transport: server uses stdio transport for communication
  5. tool_parameters: tools have proper parameter definitions with types/descriptions
  6. error_handling: tools handle errors gracefully (try/except, error returns)
  7. full_verify_orchestration: full_verify properly sequences build->ref->compare
  8. subprocess_invocation: tools correctly invoke CLI scripts via subprocess
  9. async_subprocess_correctness: uses async subprocess (not blocking) in async handlers
  10. mcp_return_protocol: returns MCP-compliant TextContent/structured responses
  11. server_metadata_quality: Server has name/version, tools have docstrings/descriptions
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_server_py(ws: Path) -> Path | None:
    """Find server.py in the workspace - check multiple locations."""
    candidates = [
        ws / "build-tools" / "server.py",
        ws / "fixtures" / "build-tools" / "server.py",
        ws / "server.py",
        ws / "mcp_server" / "server.py",
        ws / "build-tools" / "mcp_server.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    # Fallback: glob for any server*.py that imports mcp
    for p in ws.rglob("server*.py"):
        content = _read(p)
        if "mcp" in content.lower() and ("tool" in content.lower() or "server" in content.lower()):
            return p
    # Another fallback: any .py file importing mcp
    for p in ws.rglob("*.py"):
        if p.name in ("verify_solution.py", "build_project.py", "reference_build.py",
                       "compare_artifacts.py", "detect_changes.py"):
            continue
        content = _read(p)
        if "from mcp" in content or "import mcp" in content:
            if "Server" in content or "server" in content:
                return p
    return None


def _extract_tool_bodies(content: str) -> dict[str, str]:
    """Extract function bodies for each tool handler using AST."""
    tool_bodies = {}
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Get the source lines for this function
            start = node.lineno - 1
            end = node.end_lineno if hasattr(node, 'end_lineno') and node.end_lineno else start + 20
            lines = content.splitlines()
            body = "\n".join(lines[start:end])
            tool_bodies[node.name] = body
    return tool_bodies


def grade_workspace(ws: Path) -> dict:
    components = {
        "server_exists": 0.0,
        "uses_mcp_library": 0.0,
        "tools_registered": 0.0,
        "stdio_transport": 0.0,
        "tool_parameters": 0.0,
        "error_handling": 0.0,
        "full_verify_orchestration": 0.0,
        "subprocess_invocation": 0.0,
        "async_subprocess_correctness": 0.0,
        "mcp_return_protocol": 0.0,
        "server_metadata_quality": 0.0,
    }

    server_file = _find_server_py(ws)
    if not server_file:
        return {
            "overall_score": 0.0,
            "components": components,
            "weights": _weights(),
            "notes": "server.py not found in workspace",
        }

    content = _read(server_file)
    if not content.strip():
        return {
            "overall_score": 0.0,
            "components": components,
            "weights": _weights(),
            "notes": "server.py is empty",
        }

    # 1. server_exists: file exists and is syntactically valid Python
    try:
        tree = ast.parse(content)
        components["server_exists"] = 1.0
    except SyntaxError:
        components["server_exists"] = 0.3
        return {
            "overall_score": _compute_overall(components),
            "components": components,
            "weights": _weights(),
            "notes": "server.py has syntax errors",
        }

    # 2. uses_mcp_library: imports mcp package properly
    mcp_score = 0.0
    if "from mcp" in content or "import mcp" in content:
        mcp_score += 0.3
    # Must specifically import from mcp.server or mcp.server.stdio
    if re.search(r'from\s+mcp\.server', content) or re.search(r'from\s+mcp\s+import\s+.*Server', content):
        mcp_score += 0.4
    # Must instantiate Server
    if re.search(r'Server\s*\(', content):
        mcp_score += 0.3
    components["uses_mcp_library"] = min(1.0, mcp_score)

    # 3. tools_registered: check for all 5 required tools using decorator pattern
    tool_aliases = {
        "build": ["build", "build_project"],
        "reference_build": ["reference_build", "ref_build"],
        "compare": ["compare", "compare_artifacts"],
        "detect_changes": ["detect_changes"],
        "full_verify": ["full_verify", "full_verification"],
    }

    tools_found = 0
    # Strict: require either decorator registration or explicit tool name in decorator
    for tool_key, aliases in tool_aliases.items():
        found = False
        for alias in aliases:
            # Decorator with explicit name: @server.tool("name") or @app.tool(name="...")
            if re.search(rf'@\w+\.(?:tool|call_tool)\s*\(\s*["\']' + re.escape(alias), content):
                found = True
                break
            # Function def with decorator on preceding line
            if re.search(rf'@\w+\.(?:tool|list_tools|call_tool).*\n\s*(?:async\s+)?def\s+{re.escape(alias)}\s*\(', content):
                found = True
                break
            # Looser: function def with matching name that has a tool-related decorator nearby
            if re.search(rf'(?:async\s+)?def\s+{re.escape(alias)}\s*\(', content):
                # Only count if there's a decorator pattern somewhere for tools
                if re.search(r'@\w+\.(tool|call_tool)', content) or re.search(r'\.tool\s*\(', content):
                    found = True
                    break
        if found:
            tools_found += 1

    components["tools_registered"] = min(1.0, tools_found / 5.0)

    # 4. stdio_transport: uses stdio for communication
    stdio_score = 0.0
    # Must have explicit stdio transport usage
    if re.search(r'stdio', content, re.IGNORECASE):
        stdio_score += 0.3
    # Specifically: stdio_server or run.*stdio or StdioServerTransport
    if re.search(r'(stdio_server|run_stdio|StdioServerTransport|stdio_transport|read_stream|write_stream)', content):
        stdio_score += 0.4
    # Must have __main__ block that actually runs the server
    if re.search(r'if\s+__name__\s*==\s*["\']__main__["\']\s*:', content):
        # Check that the main block calls run or similar
        main_block = content[content.find('if __name__'):]
        if re.search(r'(\.run\(|run_stdio|asyncio\.run|server\.run)', main_block):
            stdio_score += 0.3
        else:
            stdio_score += 0.1
    components["stdio_transport"] = min(1.0, stdio_score)

    # 5. tool_parameters: tools have proper parameter definitions with types AND descriptions
    param_score = 0.0
    # Count distinct type-annotated parameters across tool functions (not just any annotation)
    tool_functions = _extract_tool_bodies(content)
    annotated_params = re.findall(r'(\w+)\s*:\s*(str|int|bool|Optional\[.*?\]|list|dict|float)', content)
    unique_annotated = set(p[0] for p in annotated_params if p[0] not in ('self', 'cls', 'return'))
    if len(unique_annotated) >= 8:
        param_score += 0.3
    elif len(unique_annotated) >= 5:
        param_score += 0.2
    elif len(unique_annotated) >= 2:
        param_score += 0.1

    # Check for Field() descriptions or docstring param descriptions
    field_descriptions = len(re.findall(r'Field\s*\(.*?description\s*=', content))
    docstring_params = len(re.findall(r'(?:Args|Parameters|:param)\s*.*?:', content, re.IGNORECASE))
    desc_annotations = len(re.findall(r'description\s*[=:]', content))
    if field_descriptions >= 4 or desc_annotations >= 4:
        param_score += 0.4
    elif field_descriptions >= 2 or desc_annotations >= 2 or docstring_params >= 3:
        param_score += 0.25
    elif field_descriptions >= 1 or desc_annotations >= 1 or docstring_params >= 1:
        param_score += 0.1

    # Check that tools have default values matching the CLI signatures
    # build/reference_build should default config to "Release", detect_changes should default since to 5
    has_release_default = bool(re.search(r'config.*=.*["\']Release["\']', content))
    has_since_default = bool(re.search(r'since.*=\s*5', content))
    if has_release_default and has_since_default:
        param_score += 0.3
    elif has_release_default or has_since_default:
        param_score += 0.15

    components["tool_parameters"] = min(1.0, param_score)

    # 6. error_handling: tools handle errors gracefully
    err_score = 0.0
    content_lower = content.lower()

    # Check for try/except blocks - require coverage across multiple tools
    try_blocks = len(re.findall(r'\btry\s*:', content))
    except_blocks = len(re.findall(r'\bexcept\b', content))
    if try_blocks >= 5 and except_blocks >= 5:
        err_score += 0.25
    elif try_blocks >= 3 and except_blocks >= 3:
        err_score += 0.15
    elif try_blocks >= 1:
        err_score += 0.05

    # Check for specific exception types (not bare except)
    specific_excepts = len(re.findall(r'except\s+\w+', content))
    if specific_excepts >= 3:
        err_score += 0.15
    elif specific_excepts >= 1:
        err_score += 0.05

    # Check for error return patterns (returning error info in JSON rather than raising)
    json_error_returns = len(re.findall(r'["\']error["\']\s*:', content))
    if json_error_returns >= 4:
        err_score += 0.2
    elif json_error_returns >= 2:
        err_score += 0.1

    # Check for timeout handling (subprocess.TimeoutExpired or timeout parameter)
    has_timeout = bool(re.search(r'(TimeoutExpired|timeout\s*=\s*\d+)', content))
    if has_timeout:
        err_score += 0.15

    # Check for input validation (checking paths exist, validating params)
    path_checks = len(re.findall(r'(exists\(\)|is_dir\(\)|is_file\(\)|not\s+.*path|not\s+.*dir)', content))
    if path_checks >= 3:
        err_score += 0.15
    elif path_checks >= 1:
        err_score += 0.05

    # Check for logging or structured error reporting
    has_logging = bool(re.search(r'(import\s+logging|logger\.|logging\.)', content))
    has_traceback = bool(re.search(r'(traceback\.|format_exc|exc_info)', content))
    if has_logging or has_traceback:
        err_score += 0.1

    components["error_handling"] = min(1.0, err_score)

    # 7. full_verify_orchestration: full_verify properly sequences build->ref->compare
    orch_score = 0.0

    # Find the full_verify function body
    fv_body = ""
    for fname, body in tool_functions.items():
        if "full_verify" in fname or "verify" == fname:
            fv_body = body
            break

    if not fv_body:
        # Try regex approach
        fv_match = re.search(
            r'(?:async\s+)?def\s+(?:full_verify|full_verification)\s*\(.*?\).*?(?=\n(?:async\s+)?def\s|\nclass\s|\Z)',
            content, re.DOTALL
        )
        if fv_match:
            fv_body = fv_match.group()

    if fv_body:
        fv_lower = fv_body.lower()
        # Must reference build, reference_build/ref, and compare in sequence
        has_build_call = bool(re.search(r'(build_project|build)', fv_lower))
        has_ref_call = bool(re.search(r'(reference_build|ref_build|legacy_build)', fv_lower))
        has_compare_call = bool(re.search(r'(compare_artifact|compare)', fv_lower))

        if has_build_call and has_ref_call and has_compare_call:
            orch_score += 0.4
        elif (has_build_call and has_ref_call) or (has_build_call and has_compare_call):
            orch_score += 0.2

        # Check sequential execution: uses await, or sequential calls, or checks result before continuing
        sequential_patterns = [
            r'await\s+.*build.*\n.*await\s+.*ref',  # async sequential
            r'result.*=.*build.*\n.*result.*=.*ref',  # sync sequential
            r'if.*(?:success|error|result).*:',  # checks intermediate result
            r'(?:build|reference).*\n\s*(?:if|result)',  # sequential with check
        ]
        has_sequential = any(re.search(p, fv_body, re.DOTALL | re.IGNORECASE) for p in sequential_patterns)

        # Simpler sequential check: all three operations appear in order
        build_pos = re.search(r'build', fv_lower)
        ref_pos = re.search(r'ref', fv_lower)
        compare_pos = re.search(r'compare', fv_lower)
        if build_pos and ref_pos and compare_pos:
            if build_pos.start() < ref_pos.start() < compare_pos.start():
                orch_score += 0.2

        if has_sequential:
            orch_score += 0.2

        # Check for early-exit on failure (strong models check if build succeeded before comparing)
        if re.search(r'if\s+.*(?:not\s+.*success|error|fail|stderr)', fv_body, re.IGNORECASE):
            orch_score += 0.2

    components["full_verify_orchestration"] = min(1.0, orch_score)

    # 8. subprocess_invocation: tools correctly invoke CLI scripts via subprocess
    sub_score = 0.0

    # Check for subprocess import
    if re.search(r'import\s+subprocess|from\s+subprocess', content):
        sub_score += 0.15

    # Check for subprocess.run or asyncio.create_subprocess_exec usage
    if re.search(r'subprocess\.(run|Popen|check_output|call)', content):
        sub_score += 0.25
    elif re.search(r'asyncio\.(create_subprocess|subprocess)', content) or \
         re.search(r'create_subprocess_(exec|shell)', content):
        sub_score += 0.25

    # Check that subprocess calls reference the actual script filenames
    scripts = ["build_project.py", "reference_build.py", "compare_artifacts.py", "detect_changes.py"]
    scripts_referenced = sum(1 for s in scripts if s in content)
    if scripts_referenced >= 4:
        sub_score += 0.3
    elif scripts_referenced >= 3:
        sub_score += 0.2
    elif scripts_referenced >= 2:
        sub_score += 0.1

    # Check for proper stdout/JSON parsing of subprocess results
    if re.search(r'(stdout|json\.loads|result\.stdout|process\.stdout|communicate)', content):
        sub_score += 0.15

    # Check for proper working directory or path construction for subprocess calls
    if re.search(r'(cwd\s*=|Path\s*\(|__file__|os\.path\.dirname)', content):
        sub_score += 0.15

    components["subprocess_invocation"] = min(1.0, sub_score)

    # 9. async_subprocess_correctness: tool handlers should use async subprocess
    #    (not blocking subprocess.run inside async def), demonstrating proper
    #    understanding of async MCP server architecture
    async_score = 0.0

    # Check if tool functions are async
    async_defs = re.findall(r'async\s+def\s+(\w+)', content)
    tool_like_async = [d for d in async_defs if any(
        alias in d for aliases in tool_aliases.values() for alias in aliases
    ) or "handle" in d or "tool" in d]

    if len(tool_like_async) >= 3:
        async_score += 0.2
    elif len(tool_like_async) >= 1:
        async_score += 0.1

    # Critical: using asyncio subprocess (non-blocking) instead of subprocess.run in async context
    uses_async_subprocess = bool(re.search(
        r'(asyncio\.create_subprocess_exec|asyncio\.create_subprocess_shell|'
        r'create_subprocess_exec|create_subprocess_shell|'
        r'await\s+.*process|await\s+.*communicate|'
        r'proc\.communicate|process\.communicate)',
        content
    ))
    uses_blocking_subprocess_in_async = bool(
        re.search(r'async\s+def\s+\w+.*?subprocess\.(run|call|check_output)', content, re.DOTALL)
    ) and not uses_async_subprocess

    if uses_async_subprocess:
        async_score += 0.5
    elif uses_blocking_subprocess_in_async:
        # Penalty: blocking call inside async def is an anti-pattern
        async_score += 0.1

    # Check for proper await usage with subprocess results
    if re.search(r'await\s+\w+\.communicate\(\)', content):
        async_score += 0.15

    # Check for asyncio.run or proper async entry point
    if re.search(r'asyncio\.run\s*\(', content) or re.search(r'async\s+def\s+main', content):
        async_score += 0.15

    components["async_subprocess_correctness"] = min(1.0, async_score)

    # 10. mcp_return_protocol: tools should return MCP-compliant structured responses
    #     (TextContent/list[TextContent] or similar), not raw dicts/strings
    mcp_ret_score = 0.0

    # Check for TextContent import (the correct MCP response type)
    has_text_content_import = bool(re.search(
        r'(from\s+mcp\.types\s+import.*TextContent|'
        r'from\s+mcp\s+import.*TextContent|'
        r'from\s+mcp\.server\.models\s+import.*TextContent|'
        r'import.*TextContent)',
        content
    ))
    # Also accept Tool return patterns like content=[TextContent(...)]
    has_content_list_return = bool(re.search(
        r'(TextContent\s*\(|content\s*=\s*\[|CallToolResult|ToolResult)',
        content
    ))
    # Alternative: returning list of content objects
    has_list_return = bool(re.search(
        r'return\s+\[.*TextContent|return\s+\[.*type.*=.*"text"',
        content, re.DOTALL
    ))

    if has_text_content_import:
        mcp_ret_score += 0.4
    if has_content_list_return:
        mcp_ret_score += 0.3
    if has_list_return:
        mcp_ret_score += 0.3

    # Alternatively, if they use json.dumps in returns with proper structure
    # (weaker signal, but shows structured intent)
    if not has_text_content_import and not has_content_list_return:
        # Partial credit for at least json.dumps-ing the return value consistently
        json_dumps_in_returns = len(re.findall(r'return\s+.*json\.dumps', content))
        if json_dumps_in_returns >= 3:
            mcp_ret_score += 0.3
        elif json_dumps_in_returns >= 1:
            mcp_ret_score += 0.15

    components["mcp_return_protocol"] = min(1.0, mcp_ret_score)

    # 11. server_metadata_quality: Server instantiation with proper name/version,
    #     and tool functions have docstrings that serve as MCP tool descriptions
    meta_score = 0.0

    # Server instantiation with name parameter
    server_name_match = re.search(r'Server\s*\(\s*["\'][\w\-]+["\']', content)
    if server_name_match:
        meta_score += 0.2

    # Server with version parameter
    if re.search(r'Server\s*\(.*version\s*=', content, re.DOTALL):
        meta_score += 0.15

    # Tool functions should have docstrings (MCP uses these as tool descriptions)
    tool_func_count = 0
    tool_docstring_count = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Check if this looks like a tool function
            is_tool_func = False
            for decorator in node.decorator_list:
                dec_str = ast.dump(decorator)
                if 'tool' in dec_str.lower():
                    is_tool_func = True
                    break
            if not is_tool_func:
                # Check by name
                for aliases in tool_aliases.values():
                    if node.name in aliases:
                        is_tool_func = True
                        break
            if is_tool_func:
                tool_func_count += 1
                # Check for docstring
                if (node.body and isinstance(node.body[0], ast.Expr) and
                        isinstance(node.body[0].value, (ast.Constant, ast.Str))):
                    tool_docstring_count += 1

    if tool_func_count > 0:
        docstring_ratio = tool_docstring_count / tool_func_count
        if docstring_ratio >= 0.8:
            meta_score += 0.35
        elif docstring_ratio >= 0.5:
            meta_score += 0.2
        elif docstring_ratio > 0:
            meta_score += 0.1

    # Check for tool description in decorator args (alternative to docstrings)
    tool_desc_in_decorator = len(re.findall(
        r'@\w+\.tool\s*\(.*?description\s*=', content, re.DOTALL
    ))
    if tool_desc_in_decorator >= 4:
        meta_score += 0.3
    elif tool_desc_in_decorator >= 2:
        meta_score += 0.15

    components["server_metadata_quality"] = min(1.0, meta_score)

    overall = _compute_overall(components)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": _weights(),
    }


def _weights() -> dict:
    return {
        "server_exists": 0.03,
        "uses_mcp_library": 0.07,
        "tools_registered": 0.10,
        "stdio_transport": 0.07,
        "tool_parameters": 0.10,
        "error_handling": 0.10,
        "full_verify_orchestration": 0.12,
        "subprocess_invocation": 0.09,
        "async_subprocess_correctness": 0.13,
        "mcp_return_protocol": 0.11,
        "server_metadata_quality": 0.08,
    }


def _compute_overall(components: dict) -> float:
    weights = _weights()
    return sum(weights[k] * components.get(k, 0.0) for k in weights)


def main():
    # Try primary path first, then fallback
    ws = Path("/workspace/fixtures/build-tools")
    if not ws.exists():
        ws = Path("/workspace/build-tools")
    if not ws.exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
