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
ISSUE_ANCHORS = {
    "title_keyword": ["ai", "AI", "笔记工具", "效率", "搜索", "关键词"],
    "hashtag_count": ["2个标签", "两个标签", "标签太少", "5-8", "8-10"],
    "cta_missing": ["互动引导", "点赞", "评论", "关注", "结尾"],
    "blur_fast": ["20-30", "模糊", "切换快", "节奏"],
    "data_gap": ["5.3%", "0.053", "0.9%", "0.009", "8%", "0.08", "竞品"],
}
PLAN_KEYS = {
    "video_id",
    "overall_score",
    "issues",
    "optimized_title_options",
    "recommended_hashtags",
    "content_structure_suggestion",
}


def automated_score(workspace: Path) -> dict[str, float]:
    scores = {}

    report_file = workspace / "video_analysis_report.md"
    if report_file.exists():
        content = report_file.read_text(encoding="utf-8")
        scores["report_created"] = 1.0
        dimensions_covered = sum(1 for dim in DIMENSIONS if dim in content)
        scores["dimensions_coverage"] = dimensions_covered / len(DIMENSIONS)
        anchor_hits = sum(
            1 for anchors in ISSUE_ANCHORS.values()
            if any(anchor in content for anchor in anchors)
        )
        scores["report_uses_specific_evidence"] = anchor_hits / len(ISSUE_ANCHORS)

        competitor_refs = sum(
            1 for token in ["AI工具达人", "效率狂人", "科技小食堂", "笔记侠", "竞品"]
            if token in content
        )
        scores["competitor_analysis"] = min(competitor_refs / 4.0, 1.0)
    else:
        scores["report_created"] = 0.0
        scores["dimensions_coverage"] = 0.0
        scores["report_uses_specific_evidence"] = 0.0
        scores["competitor_analysis"] = 0.0

    plan_file = workspace / "improvement_plan.json"
    if plan_file.exists():
        try:
            plan = json.loads(plan_file.read_text(encoding="utf-8"))
            scores["plan_created"] = 1.0
            scores["plan_schema"] = len(PLAN_KEYS.intersection(plan.keys())) / len(PLAN_KEYS)

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
                has_severity = all(isinstance(i, dict) and "severity" in i for i in issues)
                has_suggestion = all(isinstance(i, dict) and "suggestion" in i for i in issues)
                scores["issues_structured"] = (
                    1.0 if (has_severity and has_suggestion) else 0.5
                )

                issue_text = json.dumps(issues, ensure_ascii=False)
                issue_hits = sum(
                    1 for anchors in ISSUE_ANCHORS.values()
                    if any(anchor in issue_text for anchor in anchors)
                )
                scores["issue_diagnosis_specific"] = issue_hits / len(ISSUE_ANCHORS)
            else:
                scores["issues_structured"] = 0.0
                scores["issue_diagnosis_specific"] = 0.0

            titles = plan.get("optimized_title_options", [])
            if isinstance(titles, list) and titles:
                title_hits = sum(
                    1 for title in titles
                    if isinstance(title, str)
                    and any(k in title for k in ["AI", "ai", "笔记", "效率", "会议纪要"])
                )
                scores["title_options_actionable"] = min(title_hits / 3.0, 1.0)
            else:
                scores["title_options_actionable"] = 0.0

            tags = plan.get("recommended_hashtags", [])
            if isinstance(tags, list):
                tag_text = " ".join(str(t) for t in tags)
                enough_tags = len(tags) >= 5
                precise_tags = sum(
                    1 for k in ["AI", "效率", "办公", "笔记", "知识管理", "会议纪要"]
                    if k in tag_text
                )
                scores["hashtag_strategy"] = 0.4 * float(enough_tags) + 0.6 * min(precise_tags / 4.0, 1.0)
            else:
                scores["hashtag_strategy"] = 0.0

        except (json.JSONDecodeError, UnicodeDecodeError):
            scores["plan_created"] = 0.5
            scores["plan_schema"] = 0.0
            scores["plan_quality"] = 0.0
            scores["issues_structured"] = 0.0
            scores["issue_diagnosis_specific"] = 0.0
            scores["title_options_actionable"] = 0.0
            scores["hashtag_strategy"] = 0.0
    else:
        scores["plan_created"] = 0.0
        scores["plan_schema"] = 0.0
        scores["plan_quality"] = 0.0
        scores["issues_structured"] = 0.0
        scores["issue_diagnosis_specific"] = 0.0
        scores["title_options_actionable"] = 0.0
        scores["hashtag_strategy"] = 0.0

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
