"""T175_zh_a_share_etf_fee_reduction_impact grader — A-share ETF fee reduction analysis."""

from __future__ import annotations

import re
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


class EtfFeeReductionGrader(AbstractGrader):
    """Grade A-share ETF fee reduction impact analysis task."""

    TIMELINE_ANCHORS = [
        [r"2023.*[年月]|2023.*reform|2023.*改革"],
        [r"证监会|csrc"],
        [r"阶段|phase|分步"],
    ]

    FEE_DATA_ANCHORS = [
        [r"0[\.\s]*15\s*%|管理费.*0\.15"],
        [r"0[\.\s]*05\s*%|托管费.*0\.05"],
        [r"0[\.\s]*[256]0?\s*%.*降|降.*0\.2"],
    ]

    IMPACT_ANCHORS = [
        [r"10万|100,?000"],
        [r"[34]00.*元|节省|省"],
        [r"主动.*基金|主动.*管理|1[\.\d]*%.*管理费"],
    ]

    US_COMPARISON_ANCHORS = [
        [r"vanguard|voo|ishares|ivv"],
        [r"0[\.\s]*03\s*%|3.*基点|3\s*bp"],
        [r"美国|us|差距|gap"],
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

        etf_searched = any(
            re.search(r"etf.*降费|etf.*费率|基金.*降费|fee.*reduct", q, re.IGNORECASE)
            for q in unique_queries
        )
        search_coverage = 1.0 if etf_searched else 0.0

        timeline_score = self._coverage(all_text, self.TIMELINE_ANCHORS)
        fee_score = self._coverage(all_text, self.FEE_DATA_ANCHORS)
        impact_score = self._coverage(all_text, self.IMPACT_ANCHORS)
        us_score = self._coverage(all_text, self.US_COMPARISON_ANCHORS)

        anchor_composite = (
            0.20 * timeline_score
            + 0.30 * fee_score
            + 0.25 * impact_score
            + 0.25 * us_score
        )

        judged = judge.evaluate(
            task.prompt.text,
            self.format_conversation(messages),
            self.summarize_actions(audit_data),
            task.judge_rubric,
        ).score

        scores.completion = round(
            min(1.0, 0.50 * judged + 0.35 * anchor_composite + 0.15 * search_coverage),
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
