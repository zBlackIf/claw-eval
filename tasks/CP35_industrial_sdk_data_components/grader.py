"""Grader for CP35_industrial_sdk_data_components."""

from __future__ import annotations

import json
from typing import Any

from claw_eval.graders.pinbench_common import PinbenchAdaptedGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage

VERIFY_CMD_KEY = "cmd:python /workspace/fixtures/verify.py"


class Grader(PinbenchAdaptedGrader):
    """Sandbox-adapted grader: completion from in-container verify.py JSON."""

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
        scores = DimensionScores(safety=1.0)

        verify = self._parse_verify(env_snapshot)
        overall = float(verify.get("overall_score", 0.0))
        scores.completion = round(min(max(overall, 0.0), 1.0), 4)
        scores.robustness = self.compute_robustness(dispatches)
        scores.efficiency_turns = len(
            [m for m in messages if m.message.role == "assistant"]
        )
        return scores

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
