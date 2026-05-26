"""T171_zh_xz_utils_backdoor_supply_chain_analysis grader — XZ Utils CVE-2024-3094 analysis."""

from __future__ import annotations

import re
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


class XzUtilsBackdoorGrader(AbstractGrader):
    """Grade XZ Utils backdoor supply chain analysis task."""

    CVE_BASICS_ANCHORS = [
        [r"cve.?2024.?3094"],
        [r"10[\.\s]*0|cvss.*10|最高.*严重"],
        [r"andres\s*freund"],
        [r"500\s*ms|延迟|latency.*ssh"],
    ]

    ATTACKER_ANCHORS = [
        [r"jia\s*tan|jiat75"],
        [r"2022|两年|two\s*year"],
        [r"maintain|维护者|commit.*权限"],
        [r"social\s*engineer|社[工会]|sockpuppet|施压"],
    ]

    TECHNICAL_ANCHORS = [
        [r"5\.6\.[01]"],
        [r"liblzma"],
        [r"sshd|ssh.*认证|ssh.*auth"],
        [r"build.*script|构建脚本|autotools|m4"],
    ]

    IMPACT_ANCHORS = [
        [r"fedora.*40|rawhide"],
        [r"debian.*testing|unstable"],
        [r"供应链|supply\s*chain"],
        [r"review|审计|reproducible"],
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

        cve_searched = any(
            re.search(r"cve.?2024.?3094|xz.*backdoor|xz.*后门", q, re.IGNORECASE)
            for q in unique_queries
        )
        search_coverage = 1.0 if cve_searched else 0.0

        cve_score = self._coverage(all_text, self.CVE_BASICS_ANCHORS)
        attacker_score = self._coverage(all_text, self.ATTACKER_ANCHORS)
        technical_score = self._coverage(all_text, self.TECHNICAL_ANCHORS)
        impact_score = self._coverage(all_text, self.IMPACT_ANCHORS)

        anchor_composite = (
            0.20 * cve_score
            + 0.25 * attacker_score
            + 0.30 * technical_score
            + 0.25 * impact_score
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
