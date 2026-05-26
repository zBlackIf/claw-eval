"""T168_zh_catl_2025_annual_report_revenue_analysis grader — CATL 2025 annual report financial analysis."""

from __future__ import annotations

import re
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


class CatlAnnualReportGrader(AbstractGrader):
    """Grade CATL 2025 annual report analysis task."""

    # Revenue: 4237亿元, +17%  (source: Caixin 2026-03-10)
    REVENUE_ANCHORS = [
        [r"42[34]\d|4237", r"营[业收]"],
        [r"同比.*[增长升]|[增长升].*1[67][\.\d]*%"],
    ]

    # Net profit: 722亿元, +42.3%  (source: CATL 2025 annual report)
    PROFIT_ANCHORS = [
        [r"72[0-9]|净利润.*7[12]\d"],
        [r"同比.*[增长升]|[增长升].*4[12][\.\d]*%"],
    ]

    # Gross margin 26.27%, storage 624.4亿, capacity utilization 96.9%
    STRUCTURE_ANCHORS = [
        [r"毛利率.*2[56]|2[56][\.\d]*%.*毛利"],
        [r"储能.*6[12]\d|624"],
        [r"产能利用率.*9[67]|96[\.\d]*%"],
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

        catl_searched = any(
            re.search(r"宁德时代|catl|300750", q, re.IGNORECASE)
            for q in unique_queries
        )
        financial_searched = any(
            re.search(r"年报|营收|净利|revenue|profit|annual", q, re.IGNORECASE)
            for q in unique_queries
        )
        search_coverage = sum([catl_searched, financial_searched]) / 2.0

        revenue_score = self._coverage(all_text, self.REVENUE_ANCHORS)
        profit_score = self._coverage(all_text, self.PROFIT_ANCHORS)
        structure_score = self._coverage(all_text, self.STRUCTURE_ANCHORS)

        anchor_composite = (
            0.35 * revenue_score
            + 0.35 * profit_score
            + 0.30 * structure_score
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
