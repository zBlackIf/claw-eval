"""CP94_local_business_ai_operation_modules grader."""
from __future__ import annotations

import json
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


VERIFY_CMD_KEY = "cmd:python /workspace/fixtures/verify_biz_modules.py"


class LocalBizAiModulesGrader(AbstractGrader):
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
        scores.completion = round(min(max(float(verify.get("overall_score", 0.0)), 0.0), 1.0), 4)
        scores.robustness = self.compute_robustness(dispatches)
        final_text = self._get_final_assistant_text(messages)
        scores.communication = self.compute_communication_substance(
            final_text,
            ["score_engine", "rank_chase", "promotion", "engine.py"],
            min(sum(1 for x in ["- ", "1.", "2.", "3."] if x in final_text) / 2.0, 1.0),
        )
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        return scores
