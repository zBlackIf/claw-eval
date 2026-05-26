#!/usr/bin/env python3
"""In-container verifier for CP36_catalog_alignment_comparison.

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

SHOULD_REJECT = {"CAT-PKU-20891", "CAT-TW-40123", "CAT-JP-50789"}
BEST_MATCH = "CAT-NLC-10234"


def automated_score(workspace: Path) -> dict[str, float]:
    scores = {}

    output_file = workspace / "alignment_output.json"
    if not output_file.exists():
        for f in workspace.glob("*.json"):
            if "alignment" in f.name or "output" in f.name:
                output_file = f
                break

    if not output_file.exists():
        return {
            "output_created": 0.0,
            "valid_json": 0.0,
            "all_candidates_compared": 0.0,
            "version_rejection": 0.0,
            "best_match_identified": 0.0,
            "field_details": 0.0,
        }

    try:
        data = json.loads(output_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        scores["output_created"] = 1.0
        scores["valid_json"] = 0.0
        scores["all_candidates_compared"] = 0.0
        scores["version_rejection"] = 0.0
        scores["best_match_identified"] = 0.0
        scores["field_details"] = 0.0
        return scores

    scores["output_created"] = 1.0
    scores["valid_json"] = 1.0

    results_list = (
        data if isinstance(data, list)
        else data.get("results", data.get("comparisons", data.get("items", [])))
    )
    if not isinstance(results_list, list):
        results_list = [data]

    scores["all_candidates_compared"] = min(len(results_list) / 6.0, 1.0)

    rejected_ids = set()
    for r in results_list:
        cid = r.get("candidate_id", r.get("id", ""))
        relation = r.get("relation", r.get("alignment_type", "")).lower()
        if relation == "no_relation":
            rejected_ids.add(cid)

    correctly_rejected = SHOULD_REJECT.intersection(rejected_ids)
    scores["version_rejection"] = len(correctly_rejected) / len(SHOULD_REJECT)

    matched_best = False
    for r in results_list:
        cid = r.get("candidate_id", r.get("id", ""))
        relation = r.get("relation", r.get("alignment_type", "")).lower()
        if BEST_MATCH in cid and relation in (
            "exact_match", "same_edition", "same_version"
        ):
            matched_best = True
    scores["best_match_identified"] = 1.0 if matched_best else 0.0

    has_field_detail = False
    for r in results_list:
        fc = r.get("field_comparison", r.get("fields", {}))
        if fc and isinstance(fc, dict) and ("title" in fc or "edition" in fc):
            has_field_detail = True
            break
    scores["field_details"] = 1.0 if has_field_detail else 0.0

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
