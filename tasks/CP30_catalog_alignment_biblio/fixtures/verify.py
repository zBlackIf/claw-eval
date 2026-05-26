#!/usr/bin/env python3
"""In-container verifier for CP30_catalog_alignment_biblio.

Ports the original automated_score() to a script that runs under
env_snapshot_commands. Emits one JSON line with per-component scores plus
overall_score = mean(components).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

WORKSPACE = Path("/workspace")

EXPECTED = {
        "CAT-NLC-50001": {"correct": ["exact_match", "same_edition"], "weight": 1.0},
        "CAT-BJ-60234": {"correct": ["no_relation", "related_content"], "weight": 1.0},
        "CAT-SH-70345": {"correct": ["same_edition", "related_content"], "weight": 1.0},
        "CAT-NLC-50002": {"correct": ["same_edition"], "weight": 1.0},
        "CAT-JP-80456": {"correct": ["no_relation"], "weight": 1.0},
    }


def automated_score(workspace: Path) -> dict[str, float]:
    scores = {}

    # Find output file
    output = workspace / "alignment_result.json"
    if not output.exists():
        for f in workspace.glob("*.json"):
            if "alignment" in f.name or "result" in f.name or "output" in f.name:
                output = f
                break

    if not output or not output.exists():
        return {
            "output_created": 0.0,
            "all_compared": 0.0,
            "relation_accuracy": 0.0,
            "field_details": 0.0,
            "has_confidence": 0.0,
        }

    try:
        data = json.loads(output.read_text(encoding="utf-8"))
        scores["output_created"] = 1.0
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {
            "output_created": 0.5,
            "all_compared": 0.0,
            "relation_accuracy": 0.0,
            "field_details": 0.0,
            "has_confidence": 0.0,
        }

    # Normalize to list of comparisons
    results_list = []
    if isinstance(data, list):
        results_list = data
    elif isinstance(data, dict):
        results_list = data.get("results", data.get("comparisons", data.get("items", [])))
        if not results_list and "candidate_id" in data:
            results_list = [data]

    scores["all_compared"] = 1.0 if len(results_list) >= 5 else round(len(results_list) / 5.0, 2)

    # Check relation accuracy
    correct_count = 0
    total_weight = 0
    for cid, expected in EXPECTED.items():
        total_weight += expected["weight"]
        for r in results_list:
            rid = str(r.get("candidate_id", r.get("id", "")))
            if cid in rid or cid.split("-")[-1] in rid:
                relation = r.get("relation", r.get("relationship", r.get("type", ""))).lower()
                relation = relation.replace(" ", "_").replace("-", "_")
                if relation in expected["correct"]:
                    correct_count += expected["weight"]
                break

    scores["relation_accuracy"] = round(correct_count / total_weight, 2) if total_weight > 0 else 0.0

    # Check field details present
    has_field_detail = False
    for r in results_list:
        fc = r.get("field_comparison", r.get("fields", r.get("comparison", {})))
        if fc and isinstance(fc, dict) and ("title" in fc or "edition" in fc or "题名" in fc):
            has_field_detail = True
            break
    scores["field_details"] = 1.0 if has_field_detail else 0.0

    # Check confidence scores present
    has_confidence = any(
        "confidence" in r or "置信度" in str(r)
        for r in results_list
    )
    scores["has_confidence"] = 1.0 if has_confidence else 0.0

    return scores


def main() -> dict:
    try:
        scores = automated_score(WORKSPACE)
    except Exception as exc:  # noqa: BLE001
        return {"scores": {}, "overall_score": 0.0, "error": f"{type(exc).__name__}: {exc}"}
    numeric = [float(v) for v in scores.values() if isinstance(v, (int, float))]
    overall = sum(numeric) / len(numeric) if numeric else 0.0
    return {"scores": scores, "overall_score": round(overall, 4)}


if __name__ == "__main__":
    sys.stdout.write(json.dumps(main(), ensure_ascii=False) + "\n")
