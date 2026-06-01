"""Grader for CP180 — MD to RAG JSON Converter.

Parses the env_snapshot output from verify_solution.py and returns a 0-1 score.
"""
from __future__ import annotations

import json
import re
from typing import Any


def grade(
    task: dict[str, Any],
    trajectory: list[dict[str, Any]],
    env_snapshot: dict[str, Any] | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Grade based on verify_solution.py output in env_snapshot."""
    if not env_snapshot:
        return {"score": 0.0, "reason": "No env_snapshot available"}

    # Find the verify_solution.py output
    verify_output = None
    for key, value in env_snapshot.items():
        if "verify_solution" in key:
            verify_output = value
            break

    if not verify_output:
        # Try first command output
        for key, value in env_snapshot.items():
            if key.startswith("cmd:") or key.startswith("python"):
                verify_output = value
                break

    if not verify_output:
        return {"score": 0.0, "reason": "verify_solution.py output not found in env_snapshot"}

    # Extract stdout from dict-format command results (sandbox returns {exit_code, stdout, stderr})
    if isinstance(verify_output, dict):
        stdout = verify_output.get("stdout", "") or ""
        if not stdout and verify_output.get("stderr"):
            stdout = verify_output.get("stderr", "")
    else:
        stdout = str(verify_output)

    # Try to extract JSON object from output
    result = None
    try:
        result = json.loads(stdout.strip())
    except json.JSONDecodeError:
        # Try to find JSON in the output
        match = re.search(r'\{[^{}]*"overall_score"[^{}]*\}', stdout, re.DOTALL)
        if not match:
            # Try multiline JSON
            match = re.search(r'\{.*?"overall_score".*?\}', stdout, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
            except json.JSONDecodeError:
                pass

    if not result:
        # Check if the script failed to run
        if "error" in stdout.lower() or "traceback" in stdout.lower():
            return {"score": 0.0, "reason": f"verify_solution.py failed: {stdout[:200]}"}
        return {"score": 0.0, "reason": f"Could not parse verify output: {stdout[:200]}"}

    overall = result.get("overall_score", 0.0)
    components = result.get("components", {})

    return {
        "score": float(overall),
        "components": components,
        "weights": result.get("weights", {}),
        "reason": _build_reason(components, overall),
    }


def _build_reason(components: dict, overall: float) -> str:
    """Build a human-readable reason string."""
    parts = []
    if components.get("script_exists", 0) < 1:
        parts.append("conversion script not found")
    elif components.get("script_runs", 0) < 1:
        parts.append("script has runtime errors")
    if components.get("output_valid_json", 0) < 1:
        parts.append("output is not valid JSON array")
    if components.get("doc_type_classification", 0) < 0.5:
        parts.append("missing document type classification")
    if components.get("title_extraction", 0) < 0.5:
        parts.append("poor title extraction")
    if components.get("section_extraction", 0) < 0.5:
        parts.append("missing section/heading extraction")
    if components.get("encoding_handling", 0) < 0.5:
        parts.append("fails on non-UTF-8 files")

    if not parts:
        return f"Score {overall:.2f} — all checks passed"
    return f"Score {overall:.2f} — issues: {'; '.join(parts)}"
