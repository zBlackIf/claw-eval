"""Grader for CP109 — NOTAM Text Wrap Tokenizer.

Parses the JSON output from verify_solution.py (run via env_snapshot_commands)
and returns normalized 0-1 score with component breakdown.
"""
from __future__ import annotations

import json
import re
from typing import Any


def grade(env_snapshot: dict[str, Any], **kwargs) -> dict[str, Any]:
    """
    Grade CP109 based on env_snapshot output.

    Expected env_snapshot structure:
    {
        "cmd:python /workspace/fixtures/verify_solution.py": "<json string>"
    }
    """
    cmd_key = "cmd:python /workspace/fixtures/verify_solution.py"
    raw_output = env_snapshot.get(cmd_key, "")

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
            "error": "No verify_solution.py output found in env_snapshot",
        }

    # Parse JSON from output (might have extra text around it)
    try:
        # Try direct parse first
        result = json.loads(raw_output.strip())
    except json.JSONDecodeError:
        # Try to extract JSON from output
        json_match = re.search(r'\{[^{}]*"overall_score"[^{}]*\}', raw_output, re.DOTALL)
        if not json_match:
            # Try multiline JSON
            json_match = re.search(r'\{.*"overall_score".*\}', raw_output, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
            except json.JSONDecodeError:
                return {
                    "overall_score": 0.0,
                    "components": {},
                    "error": f"Could not parse JSON from output: {raw_output[:200]}",
                }
        else:
            return {
                "overall_score": 0.0,
                "components": {},
                "error": f"No JSON found in output: {raw_output[:200]}",
            }

    overall = result.get("overall_score", 0.0)
    components = result.get("components", {})

    return {
        "overall_score": round(float(overall), 4),
        "components": {k: round(float(v), 4) for k, v in components.items()},
        "weights": result.get("weights", {}),
        "error": result.get("error"),
    }
