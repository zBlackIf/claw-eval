"""CP181_rsdd_multi_skill_doc_generation grader."""
from __future__ import annotations

import json
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


VERIFY_CMD_KEY = "cmd:python /workspace/fixtures/verify_solution.py"


class RsddMultiSkillDocGenerationGrader(AbstractGrader):
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

        # Completion score from hidden verifier
        scores.completion = round(
            min(max(float(verify.get("overall_score", 0.0)), 0.0), 1.0), 4
        )

        # Robustness from dispatch patterns
        scores.robustness = self.compute_robustness(dispatches)

        # Communication: check that agent explains its approach
        final_text = self._get_final_assistant_text(messages)
        key_terms = ["RSDD", "chapter", "skill", "requirement", "voc"]
        scores.communication = self.compute_communication_substance(
            final_text,
            key_terms,
            min(
                sum(1 for x in ["Chapter 1", "Chapter 2", "Chapter 3", "Chapter 4", "Chapter 5",
                                "1.", "2.", "3.", "4.", "5."] if x in final_text) / 4.0,
                1.0,
            ),
        )

        # Track efficiency
        scores.efficiency_turns = len(
            [m for m in messages if m.message.role == "assistant"]
        )

        return scores
