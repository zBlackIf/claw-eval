"""T176_zh_cursor_vs_windsurf_ai_coding_comparison grader — Cursor vs Windsurf 2026 comparison."""

from __future__ import annotations

import re
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


class CursorWindsurfComparisonGrader(AbstractGrader):
    """Grade Cursor vs Windsurf AI coding tool comparison task (2026 edition)."""

    BACKGROUND_ANCHORS = [
        [r"cursor"],
        [r"anysphere|50b|\$50"],
        [r"windsurf"],
        [r"cognition|devin"],
    ]

    CAPABILITY_ANCHORS = [
        [r"background.*agent|supermaven"],
        [r"cascade|swe.?1"],
        [r"context|codebase"],
    ]

    PRICING_ANCHORS = [
        [r"\$?20.*月|20.*month"],
        [r"\$?15.*月|15.*month"],
        [r"收购|acquisition|platform.*risk"],
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

        cursor_searched = any(
            re.search(r"cursor", q, re.IGNORECASE) for q in unique_queries
        )
        windsurf_searched = any(
            re.search(r"windsurf|codeium|cognition|devin", q, re.IGNORECASE) for q in unique_queries
        )
        search_coverage = sum([cursor_searched, windsurf_searched]) / 2.0

        background_score = self._coverage(all_text, self.BACKGROUND_ANCHORS)
        capability_score = self._coverage(all_text, self.CAPABILITY_ANCHORS)
        pricing_score = self._coverage(all_text, self.PRICING_ANCHORS)

        anchor_composite = (
            0.30 * background_score
            + 0.40 * capability_score
            + 0.30 * pricing_score
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
