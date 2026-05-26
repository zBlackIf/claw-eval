"""T169_zh_byd_vs_tesla_2026q1_global_delivery grader — BYD vs Tesla Q1 2026 delivery comparison."""

from __future__ import annotations

import re
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


class BydTeslaDeliveryGrader(AbstractGrader):
    """Grade BYD vs Tesla 2026Q1 delivery comparison task."""

    TESLA_ANCHORS = [
        [r"358\s*[,.]?\s*0?23|35[78]\s*[,.]?\s*\d{3}|35\.?8万|约3[56]万|358k"],
        [r"同比.*[增长上升涨]|[增长上升涨].*6[\.\d]*%|\+6"],
    ]

    BYD_ANCHORS = [
        [r"31[0-5]\s*[,.]?\s*\d{3}|31万|约31万|310k|~310"],
        [r"70[0-5]\s*[,.]?\s*\d{3}|70万|约70万|700k|~700|总.*7[01]\d*万"],
        [r"插混.*3[89]\d*万|phev.*3[89]|39万|~390"],
    ]

    COMPARISON_ANCHORS = [
        [r"特斯拉.*重新|tesla.*reclaim|夺回.*纯电|bev.*lead.*tesla|特斯拉.*纯电.*第一|tesla.*first"],
        [r"春节|季节性|seasonal|chinese new year|新年"],
        [r"[12][\.\d]*倍|2:1|两倍|近两倍"],
    ]

    def grade(
        self,
        messages: list[TraceMessage],
        dispatches: list[ToolDispatch],
        task: TaskDefinition,
        audit_data: dict[str, dict] | None = None,
        judge: Any | None = None,
        media_events: list[MediaLoad] | None = None,
        env_snapshot: dict | None = None,
    ) -> DimensionScores:
        scores = DimensionScores()
        scores.safety = 1.0

        all_text = self._get_all_assistant_text(messages).lower()

        search_calls = [
            d for d in dispatches
            if d.tool_name == "web_search" and d.response_status < 400
        ]
        unique_queries = {d.request_body.get("query", "") for d in search_calls}

        tesla_searched = any(
            re.search(r"tesla|特斯拉", q, re.IGNORECASE) for q in unique_queries
        )
        byd_searched = any(
            re.search(r"byd|比亚迪", q, re.IGNORECASE) for q in unique_queries
        )
        search_coverage = sum([tesla_searched, byd_searched]) / 2.0

        tesla_score = self._coverage(all_text, self.TESLA_ANCHORS)
        byd_score = self._coverage(all_text, self.BYD_ANCHORS)
        comparison_score = self._coverage(all_text, self.COMPARISON_ANCHORS)

        anchor_composite = (
            0.30 * tesla_score
            + 0.35 * byd_score
            + 0.35 * comparison_score
        )

        judged = judge.evaluate(
            task.prompt.text,
            self.format_conversation(messages),
            self.summarize_actions(audit_data),
            task.judge_rubric,
        ).score

        scores.completion = round(
            min(1.0, 0.50 * judged + 0.30 * anchor_composite + 0.20 * search_coverage),
            2,
        )
        scores.robustness = self.compute_robustness(dispatches)
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        return scores

    def _coverage(self, text: str, anchor_groups: list[list[str]]) -> float:
        covered = 0
        for group in anchor_groups:
            if any(re.search(pat, text) for pat in group):
                covered += 1
        return covered / len(anchor_groups) if anchor_groups else 0.0
