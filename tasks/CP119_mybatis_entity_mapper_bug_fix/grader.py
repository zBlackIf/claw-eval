"""Grader for CP119 — MyBatis Entity + Mapper XML Bug Fix.

Parses the JSON output from verify_solution.py (run via env_snapshot_commands)
and returns a 0-1 overall score with per-dimension breakdown.
"""
from __future__ import annotations

import json


def grade(audit_data: dict, dispatches: list, env_snapshot: dict) -> dict:
    """Grade the task based on env_snapshot output from verify_solution.py."""

    # Extract the verifier output
    cmd_key = "cmd:python /workspace/fixtures/verify_solution.py"
    raw = env_snapshot.get(cmd_key, "")

    # Try to parse JSON from stdout
    result = None
    for line in raw.strip().splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                result = json.loads(line)
                break
            except json.JSONDecodeError:
                continue

    if result is None:
        return {
            "overall_score": 0.0,
            "components": {
                "product_tablefield_annotations": 0.0,
                "mapper_xml_exists": 0.0,
                "mapper_xml_namespace": 0.0,
                "mapper_xml_select_page": 0.0,
                "mapper_xml_select_by_supplier": 0.0,
            },
            "error": "Failed to parse verify_solution.py output",
        }

    return {
        "overall_score": result.get("overall_score", 0.0),
        "components": result.get("components", {}),
        "weights": result.get("weights", {}),
    }
