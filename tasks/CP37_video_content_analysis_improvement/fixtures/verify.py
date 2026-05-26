#!/usr/bin/env python3
"""In-container verifier for CP37_video_content_analysis_improvement.

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

DIMENSIONS = ["标题", "内容", "标签", "受众", "数据"]


def automated_score(workspace: Path) -> dict[str, float]:
    scores = {}

    report_file = workspace / "video_analysis_report.md"
    if report_file.exists():
        content = report_file.read_text(encoding="utf-8")
        scores["report_created"] = 1.0
        dimensions_covered = sum(1 for dim in DIMENSIONS if dim in content)
        scores["dimensions_coverage"] = dimensions_covered / len(DIMENSIONS)
    else:
        scores["report_created"] = 0.0
        scores["dimensions_coverage"] = 0.0

    plan_file = workspace / "improvement_plan.json"
    if plan_file.exists():
        try:
            plan = json.loads(plan_file.read_text(encoding="utf-8"))
            scores["plan_created"] = 1.0

            has_score = "overall_score" in plan
            has_issues = isinstance(plan.get("issues", None), list) and len(plan.get("issues", [])) > 0
            has_titles = (
                "optimized_title_options" in plan
                and isinstance(plan["optimized_title_options"], list)
                and len(plan["optimized_title_options"]) > 0
            )
            has_tags = (
                "recommended_hashtags" in plan
                and isinstance(plan["recommended_hashtags"], list)
                and len(plan["recommended_hashtags"]) > 0
            )

            quality_score = sum([has_score, has_issues, has_titles, has_tags]) / 4.0
            scores["plan_quality"] = quality_score

            if has_issues:
                issues = plan["issues"]
                has_severity = all("severity" in i for i in issues)
                has_suggestion = all("suggestion" in i for i in issues)
                scores["issues_structured"] = (
                    1.0 if (has_severity and has_suggestion) else 0.5
                )
            else:
                scores["issues_structured"] = 0.0

        except (json.JSONDecodeError, UnicodeDecodeError):
            scores["plan_created"] = 0.5
            scores["plan_quality"] = 0.0
            scores["issues_structured"] = 0.0
    else:
        scores["plan_created"] = 0.0
        scores["plan_quality"] = 0.0
        scores["issues_structured"] = 0.0

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
