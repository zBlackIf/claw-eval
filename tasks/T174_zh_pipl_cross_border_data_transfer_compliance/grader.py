"""T174_zh_pipl_cross_border_data_transfer_compliance grader — PIPL cross-border data transfer compliance (2026 update)."""

from __future__ import annotations

import re
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


class PiplComplianceGrader(AbstractGrader):
    """Grade PIPL cross-border data transfer compliance research task (2026 edition)."""

    # D1: Three legal paths — security assessment, standard contract, certification
    PIPL_RULES_ANCHORS = [
        [r"安全评估"],
        [r"标准合同"],
        [r"认证办法|出境认证|保护认证"],
        [r"100万|10万|关键信息基础设施|ciio"],
    ]

    # D2: 2026 new developments — certification effective, upgrade thresholds, Beijing reform
    NEW_REGULATION_ANCHORS = [
        [r"认证办法.*2026|2026.*认证办法|2026年.*施行"],
        [r"100万.*[非敏感]|1万.*敏感|升级.*安全评估"],
        [r"自贸区|负面清单"],
        [r"北京|便利化|全市"],
        [r"促进和规范|数据跨境流动规定"],
    ]

    # D3: Practical advice — PIA, path comparison, filing
    PRACTICAL_ANCHORS = [
        [r"备案|filing"],
        [r"pia|影响评估|保护影响"],
        [r"建议|路径|策略|步骤"],
        [r"认证.*标准合同|标准合同.*认证|对比|选择"],
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

        pipl_searched = any(
            re.search(r"个人信息保护|pipl|个保法|数据出境|跨境|认证办法", q, re.IGNORECASE)
            for q in unique_queries
        )
        regulation_searched = any(
            re.search(r"促进和规范|2026|认证|标准合同|负面清单", q, re.IGNORECASE)
            for q in unique_queries
        )
        search_coverage = sum([pipl_searched, regulation_searched]) / 2.0

        pipl_score = self._coverage(all_text, self.PIPL_RULES_ANCHORS)
        new_reg_score = self._coverage(all_text, self.NEW_REGULATION_ANCHORS)
        practical_score = self._coverage(all_text, self.PRACTICAL_ANCHORS)

        anchor_composite = (
            0.25 * pipl_score
            + 0.40 * new_reg_score
            + 0.35 * practical_score
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
