"""T170_zh_deepseek_v4_architecture_training_efficiency grader — DeepSeek V4 architecture & deployment research."""

from __future__ import annotations

import re
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


class DeepseekV3ArchitectureGrader(AbstractGrader):
    """Grade DeepSeek V4 technical architecture and deployment research task."""

    PARAM_ANCHORS = [
        [r"1[\.\s]*6\s*t|1\.6万亿|1600\s*b|1\.6\s*trillion"],
        [r"49\s*b|490亿|49billion|激活.*49"],
        [r"284\s*b|2840亿|284billion|flash.*284"],
        [r"13\s*b|130亿|13billion|flash.*激活.*13"],
    ]

    ARCHITECTURE_ANCHORS = [
        [r"hybrid\s*attention|混合注意力"],
        [r"compressed\s*sparse\s*attention|csa"],
        [r"heavily\s*compressed\s*attention|hca"],
        [r"1\s*m.*context|100万.*上下文|1m\s*token|百万.*token.*上下文"],
    ]

    TRAINING_ANCHORS = [
        [r"mit\s*licen|mit许可|mit\s*协议"],
        [r"开源.*权重|open.?weight|开放权重"],
        [r"vllm|v\s*llm"],
        [r"sglang|sg\s*lang"],
        [r"two.?tier|双层.*发布|pro.*flash|flash.*pro"],
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

        deepseek_searched = any(
            re.search(r"deepseek.*v4|deepseek\s*v4", q, re.IGNORECASE)
            for q in unique_queries
        )
        arch_searched = any(
            re.search(r"architect|moe|parameter|部署|deploy|attention|context", q, re.IGNORECASE)
            for q in unique_queries
        )
        search_coverage = sum([deepseek_searched, arch_searched]) / 2.0

        param_score = self._coverage(all_text, self.PARAM_ANCHORS)
        arch_score = self._coverage(all_text, self.ARCHITECTURE_ANCHORS)
        training_score = self._coverage(all_text, self.TRAINING_ANCHORS)

        anchor_composite = (
            0.30 * param_score
            + 0.30 * arch_score
            + 0.40 * training_score
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
