"""T173_zh_rust_2024_edition_migration_assessment grader — Rust 2024 edition migration assessment."""

from __future__ import annotations

import re
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


class RustEditionMigrationGrader(AbstractGrader):
    """Grade Rust 2024 Edition migration assessment task."""

    LANGUAGE_CHANGES_ANCHORS = [
        [r"gen.*关键字|gen.*keyword|gen.*保留|reserved.*gen"],
        [r"unsafe_op_in_unsafe_fn|unsafe.*fn.*deny"],
        [r"impl\s*trait.*lifetime|rpit.*capture|lifetime.*capture"],
        [r"unsafe\s*extern|extern.*unsafe"],
    ]

    TOOLING_ANCHORS = [
        [r"cargo\s*fix|cargo.*--edition"],
        [r"自动.*迁移|auto.*migrat"],
        [r"互操作|interop|混用|cross.*edition"],
    ]

    BENEFITS_ANCHORS = [
        [r"async.*closure|异步.*闭包"],
        [r"安全|safety|更.*safe"],
    ]

    RECOMMENDATION_ANCHORS = [
        [r"建议.*升|推荐.*迁移|suggest.*upgrade"],
        [r"策略|strategy|渐进|incremental"],
        [r"风险.*可控|risk.*manage|低风险"],
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

        rust_searched = any(
            re.search(r"rust.*2024.*edition|rust.*1\.85", q, re.IGNORECASE)
            for q in unique_queries
        )
        search_coverage = 1.0 if rust_searched else 0.0

        changes_score = self._coverage(all_text, self.LANGUAGE_CHANGES_ANCHORS)
        tooling_score = self._coverage(all_text, self.TOOLING_ANCHORS)
        benefits_score = self._coverage(all_text, self.BENEFITS_ANCHORS)
        recommendation_score = self._coverage(all_text, self.RECOMMENDATION_ANCHORS)

        anchor_composite = (
            0.30 * changes_score
            + 0.20 * tooling_score
            + 0.20 * benefits_score
            + 0.30 * recommendation_score
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
