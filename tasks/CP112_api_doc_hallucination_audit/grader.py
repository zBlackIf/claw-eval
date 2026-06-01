"""CP112_api_doc_hallucination_audit grader."""
from __future__ import annotations

import json
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


VERIFY_CMD_KEY = "cmd:python /workspace/fixtures/verify_solution.py"


class ApiDocHallucinationAuditGrader(AbstractGrader):
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
        # Communication: agent should mention key findings (hallucinated params, wrong methods, etc.)
        keywords = [
            "province", "fabricat", "hallucin", "incorrect", "wrong",
            "POST", "DELETE", "MappingAddRequest", "MappingDeleteRequest",
            "FormData", "brand", "missing"
        ]
        keyword_hits = sum(1 for kw in keywords if kw.lower() in final_text.lower())
        keyword_ratio = min(keyword_hits / 5.0, 1.0)
        scores.communication = self.compute_communication_substance(
            final_text,
            ["province", "method", "body", "parameter", "field"],
            keyword_ratio,
        )
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        return scores
