"""Grader for CP28_java_alarm_scan_code_review.

Primary delivery channel: sandbox files under /workspace. Completion is read
from the hidden verifier JSON emitted by fixtures/verify.py.
"""

from __future__ import annotations

import json
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage

VERIFY_CMD_KEY = "cmd:python /workspace/fixtures/verify.py"
COMMUNICATION_ENTITIES = ['review_report.md']


class Grader(AbstractGrader):
    @staticmethod
    def _parse_verify(env_snapshot: dict | None) -> dict:
        if not env_snapshot:
            return {}
        entry = env_snapshot.get(VERIFY_CMD_KEY)
        if not isinstance(entry, dict):
            return {}
        stdout = entry.get("stdout") or ""
        for line in stdout.strip().splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        return {}

    @staticmethod
    def _overall_score(verify: dict) -> float:
        if "overall_score" in verify:
            try:
                return float(verify.get("overall_score", 0.0))
            except (TypeError, ValueError):
                return 0.0
        raw_scores = verify.get("scores")
        if isinstance(raw_scores, dict):
            vals = []
            for value in raw_scores.values():
                if isinstance(value, bool):
                    vals.append(1.0 if value else 0.0)
                elif isinstance(value, (int, float)):
                    vals.append(float(value))
            if vals:
                return sum(vals) / len(vals)
        return 0.0

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
        del task, audit_data, judge, media_events
        scores = DimensionScores(safety=1.0)

        verify = self._parse_verify(env_snapshot)
        overall = min(max(self._overall_score(verify), 0.0), 1.0)
        scores.completion = round(overall, 4)
        scores.robustness = self.compute_robustness(dispatches)

        final_text = self._get_final_assistant_text(messages)
        format_score = min(sum(1 for marker in ["- ", "1.", "2.", "#", "`"] if marker in final_text) / 3.0, 1.0)
        scores.communication = self.compute_communication_substance(
            final_text,
            COMMUNICATION_ENTITIES,
            format_score,
        )
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        return scores
