"""T172_zh_sora_kling_video_generation_comparison grader — Sora 2 vs Kling 3.0 AI video generation comparison (2026)."""

from __future__ import annotations

import re
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


class SoraKlingComparisonGrader(AbstractGrader):
    """Grade Sora 2 vs Kling 3.0 AI video generation comparison task (2026 data)."""

    SORA_ANCHORS = [
        [r"sora.*2"],
        [r"openai|chatgpt"],
        [r"\$20|plus|pro|200"],
    ]

    KLING_ANCHORS = [
        [r"可灵.*3|kling.*3"],
        [r"快手|kuaishou"],
        [r"4k|motion.*brush|运动笔刷"],
        [r"\$6\.99|免费|66.*credits"],
    ]

    COMPARISON_ANCHORS = [
        [r"seedance|veo"],
        [r"中文.*support|中文.*支持|国内"],
        [r"对比|vs"],
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

        sora_searched = any(
            re.search(r"sora", q, re.IGNORECASE) for q in unique_queries
        )
        kling_searched = any(
            re.search(r"可灵|kling", q, re.IGNORECASE) for q in unique_queries
        )
        search_coverage = sum([sora_searched, kling_searched]) / 2.0

        sora_score = self._coverage(all_text, self.SORA_ANCHORS)
        kling_score = self._coverage(all_text, self.KLING_ANCHORS)
        comparison_score = self._coverage(all_text, self.COMPARISON_ANCHORS)

        anchor_composite = (
            0.30 * sora_score
            + 0.30 * kling_score
            + 0.40 * comparison_score
        )

        judged = judge.evaluate(
            task.prompt.text,
            self.format_conversation(messages),
            self.summarize_actions(audit_data),
            task.judge_rubric,
        ).score

        scores.completion = round(
            min(1.0, 0.55 * judged + 0.25 * anchor_composite + 0.20 * search_coverage),
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
