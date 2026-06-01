"""Grader for CP129_project_report_generator.

Parses verify_solution.py JSON output from env_snapshot and returns 0-1 score.
"""
from __future__ import annotations

import json
import re
from typing import Any


def grade(audit_data: dict, dispatches: list, env_snapshot: dict, **kwargs) -> dict:
    """Grade the task based on env_snapshot from verify_solution.py."""

    # Extract the verify_solution.py output from env_snapshot
    snapshot_key = "cmd:python /workspace/fixtures/verify_solution.py"
    raw_output = env_snapshot.get(snapshot_key, "")

    if not raw_output:
        # Try alternative key formats
        for k, v in env_snapshot.items():
            if "verify_solution" in k:
                raw_output = v
                break

    if not raw_output:
        return {
            "overall_score": 0.0,
            "components": {},
            "explanation": "verify_solution.py produced no output",
        }

    # Parse JSON output
    try:
        result = json.loads(raw_output.strip().split("\n")[-1])
    except (json.JSONDecodeError, IndexError):
        # Try to find JSON in the output
        json_match = re.search(r'\{[^{}]*"overall_score"[^{}]*\}', raw_output, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
            except json.JSONDecodeError:
                return {
                    "overall_score": 0.0,
                    "components": {},
                    "explanation": f"Could not parse verify output: {raw_output[:200]}",
                }
        else:
            return {
                "overall_score": 0.0,
                "components": {},
                "explanation": f"Could not parse verify output: {raw_output[:200]}",
            }

    overall = result.get("overall_score", 0.0)
    components = result.get("components", {})

    # Build explanation
    explanation_parts = []
    for dim, score in components.items():
        if score < 1.0:
            explanation_parts.append(f"{dim}: {score:.2f}")

    explanation = "All checks passed." if overall >= 0.95 else f"Partial: {'; '.join(explanation_parts)}"

    return {
        "overall_score": round(overall, 4),
        "components": components,
        "explanation": explanation,
    }
