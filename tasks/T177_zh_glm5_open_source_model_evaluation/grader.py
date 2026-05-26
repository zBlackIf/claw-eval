"""T177_zh_glm5_open_source_model_evaluation grader — GLM-5.1 agentic coding model evaluation."""

from __future__ import annotations

import re
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


class Glm4EvaluationGrader(AbstractGrader):
    """Grade GLM-5.1 agentic coding model evaluation task."""

    VERSION_ANCHORS = [
        [r"glm.?5\.?1"],
        [r"z\.ai|智谱"],
        [r"agentic|agent"],
        [r"swe.?bench"],
    ]

    BENCHMARK_ANCHORS = [
        [r"swe.?bench.*pro"],
        [r"coding|编程"],
        [r"deepseek.*v4"],
        [r"qwen.?3"],
    ]

    DEPLOYMENT_ANCHORS = [
        [r"open.?source|开源"],
        [r"MIT|apache"],
        [r"vllm|sglang"],
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

        glm_searched = any(
            re.search(r"glm.?5|智谱|z\.ai", q, re.IGNORECASE) for q in unique_queries
        )
        search_coverage = 1.0 if glm_searched else 0.0

        version_score = self._coverage(all_text, self.VERSION_ANCHORS)
        benchmark_score = self._coverage(all_text, self.BENCHMARK_ANCHORS)
        deployment_score = self._coverage(all_text, self.DEPLOYMENT_ANCHORS)

        anchor_composite = (
            0.30 * version_score
            + 0.40 * benchmark_score
            + 0.30 * deployment_score
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
