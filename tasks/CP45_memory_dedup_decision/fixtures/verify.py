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
NAV_ANCHORS = ["即时", "后效", "打扰", "风险"]


def automated_score(workspace: Path) -> dict[str, float]:
    scores = {}

    decision_file = workspace / "decision_result.json"
    if decision_file.exists():
        try:
            data = json.loads(decision_file.read_text(encoding="utf-8"))
            scores["decision_created"] = 1.0

            decision = data.get("decision", "").upper()
            scores["valid_decision"] = 1.0 if decision in ("ADD", "MERGE", "SKIP") else 0.0

            reason = str(data.get("reason", ""))
            scores["has_reason"] = 1.0 if len(reason) > 40 else (0.5 if len(reason) > 10 else 0.0)
            scores["reason_cites_threshold"] = 1.0 if re.search(r"0\.5|0\.7|阈值|中度|score|相似", reason) else 0.0
            scores["reason_cites_target"] = 1.0 if "71cd9e45" in reason else 0.0

            scores["expected_decision_merge"] = 1.0 if decision == "MERGE" else 0.0
            scores["merge_target_correct"] = (
                1.0 if "71cd9e45" in str(data.get("merge_target", "")) else 0.0
            )

            merged = str(data.get("merged_content", ""))
            nav_hits = sum(1 for anchor in NAV_ANCHORS if anchor in merged)
            keeps_existing = all(k in merged for k in ["收入", "用户体验", "留存"])
            scores["merged_content"] = 1.0 if len(merged) > 120 and nav_hits >= 3 else (0.5 if len(merged) > 50 else 0.0)
            scores["merged_content_nav4"] = nav_hits / len(NAV_ANCHORS)
            scores["merged_keeps_existing_points"] = 1.0 if keeps_existing else 0.0

            unique_points = data.get("unique_points", [])
            if isinstance(unique_points, list):
                unique_text = " ".join(str(p) for p in unique_points)
                scores["unique_points_nav_specific"] = sum(1 for anchor in NAV_ANCHORS if anchor in unique_text) / len(NAV_ANCHORS)
            else:
                scores["unique_points_nav_specific"] = 0.0

        except (json.JSONDecodeError, UnicodeDecodeError):
            scores["decision_created"] = 0.5
            scores["valid_decision"] = 0.0
            scores["has_reason"] = 0.0
            scores["reason_cites_threshold"] = 0.0
            scores["reason_cites_target"] = 0.0
            scores["expected_decision_merge"] = 0.0
            scores["merge_target_correct"] = 0.0
            scores["merged_content"] = 0.0
            scores["merged_content_nav4"] = 0.0
            scores["merged_keeps_existing_points"] = 0.0
            scores["unique_points_nav_specific"] = 0.0
    else:
        scores["decision_created"] = 0.0
        scores["valid_decision"] = 0.0
        scores["has_reason"] = 0.0
        scores["reason_cites_threshold"] = 0.0
        scores["reason_cites_target"] = 0.0
        scores["expected_decision_merge"] = 0.0
        scores["merge_target_correct"] = 0.0
        scores["merged_content"] = 0.0
        scores["merged_content_nav4"] = 0.0
        scores["merged_keeps_existing_points"] = 0.0
        scores["unique_points_nav_specific"] = 0.0

    analysis_file = workspace / "analysis_report.txt"
    if analysis_file.exists():
        content = analysis_file.read_text(encoding="utf-8")
        scores["analysis_report_exists"] = 1.0
        mentioned = sum(1 for uri in EXPECTED_URIS if uri in content)
        scores["all_memories_analyzed"] = mentioned / len(EXPECTED_URIS)
        scores["analysis_identifies_best_target"] = 1.0 if re.search(r"71cd9e45.*(最相关|最高|merge|合并|深化)|最相关.*71cd9e45", content, re.I | re.S) else 0.0
        scores["analysis_distinguishes_partial_overlap"] = 1.0 if "22bc1a03" in content and re.search(r"eCPM|部分|填充率|中度", content) else 0.0
    else:
        scores["analysis_report_exists"] = 0.0
        scores["all_memories_analyzed"] = 0.0
        scores["analysis_identifies_best_target"] = 0.0
        scores["analysis_distinguishes_partial_overlap"] = 0.0

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
