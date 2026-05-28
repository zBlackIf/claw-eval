"""CP62_executive_lookup grader."""
from __future__ import annotations

import json
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


VERIFY_CMD_KEY = "cmd:python /workspace/fixtures/verify_cfo_lookup.py"


class ExecutiveLookupGrader(AbstractGrader):
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
        file_score = float(verify.get("overall_score", 0.0))

        search_calls = [d for d in dispatches if d.tool_name == "web_search" and d.response_status < 400]
        unique_queries = {(d.request_body or {}).get("query", "") for d in search_calls}
        search_score = min(len(unique_queries) / 2.0, 1.0)

        scores.completion = round(min(1.0, 0.80 * file_score + 0.20 * search_score), 4)
        scores.robustness = self.compute_robustness(dispatches)
        final_text = self._get_final_assistant_text(messages)
        scores.communication = self.compute_communication_substance(
            final_text,
            ["gitlab_cfo.txt", "GitLab", "CFO"],
            0.6,
        )
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        return scores
