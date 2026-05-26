#!/usr/bin/env python3
"""In-container verifier for CP45_memory_dedup_decision.

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

EXPECTED_URIS = ["889ae446", "22bc1a03", "f3a87b12", "71cd9e45"]


def automated_score(workspace: Path) -> dict[str, float]:
    scores = {}

    decision_file = workspace / "decision_result.json"
    if decision_file.exists():
        try:
            data = json.loads(decision_file.read_text(encoding="utf-8"))
            scores["decision_created"] = 1.0

            decision = data.get("decision", "").upper()
            scores["valid_decision"] = 1.0 if decision in ("ADD", "MERGE", "SKIP") else 0.0

            scores["has_reason"] = 1.0 if len(data.get("reason", "")) > 10 else 0.0

            if decision == "MERGE":
                scores["merge_target_correct"] = (
                    1.0 if "71cd9e45" in str(data.get("merge_target", "")) else 0.0
                )
                scores["merged_content"] = (
                    1.0 if len(data.get("merged_content", "")) > 50 else 0.0
                )
            else:
                scores["merge_target_correct"] = 0.5
                has_unique = len(data.get("unique_points", [])) > 0
                scores["merged_content"] = 1.0 if has_unique else 0.0

        except (json.JSONDecodeError, UnicodeDecodeError):
            scores["decision_created"] = 0.5
            scores["valid_decision"] = 0.0
            scores["has_reason"] = 0.0
            scores["merge_target_correct"] = 0.0
            scores["merged_content"] = 0.0
    else:
        scores["decision_created"] = 0.0
        scores["valid_decision"] = 0.0
        scores["has_reason"] = 0.0
        scores["merge_target_correct"] = 0.0
        scores["merged_content"] = 0.0

    analysis_file = workspace / "analysis_report.txt"
    if analysis_file.exists():
        content = analysis_file.read_text(encoding="utf-8")
        scores["analysis_report_exists"] = 1.0
        mentioned = sum(1 for uri in EXPECTED_URIS if uri in content)
        scores["all_memories_analyzed"] = mentioned / len(EXPECTED_URIS)
    else:
        scores["analysis_report_exists"] = 0.0
        scores["all_memories_analyzed"] = 0.0

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
