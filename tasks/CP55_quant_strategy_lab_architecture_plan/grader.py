"""CP55_quant_strategy_lab_architecture_plan grader.

Deliverable: /workspace/PLAN.md + /workspace/strategy_lab.py.
Sandbox verifier (file structure) + kb usage (RFC/retro/metric defs).
"""

from __future__ import annotations

import json
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


VERIFY_CMD_KEY = "cmd:python /workspace/fixtures/verify_quant_lab_plan.py"


class QuantStrategyLabPlanGrader(AbstractGrader):
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
    def _score_kb_usage(audit_data: dict[str, dict] | None) -> float:
        if not audit_data:
            return 0.0
        kb_audit = audit_data.get("kb") or {}
        calls = kb_audit.get("calls") if isinstance(kb_audit, dict) else None
        if not calls:
            return 0.0
        articles_fetched = set()
        searched = False
        for entry in calls:
            ep = entry.get("endpoint", "")
            body = entry.get("request_body") or {}
            if ep == "/kb/articles/get" and body.get("article_id"):
                articles_fetched.add(body["article_id"])
            if ep == "/kb/search":
                searched = True
        coverage = len(articles_fetched & {
            "KB-LAB-RFC-DRAFT", "KB-RISK-LOG-RETRO", "KB-METRIC-DEFS",
        }) / 3.0
        breadth_bonus = 0.2 if searched and len(articles_fetched) >= 2 else 0.0
        return min(coverage + breadth_bonus, 1.0)

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
        del task, judge, media_events
        scores = DimensionScores(safety=1.0)
        verify = self._parse_verify(env_snapshot)
        sandbox_score = float(verify.get("overall_score", 0.0))
        kb_score = self._score_kb_usage(audit_data)
        scores.completion = round(min(1.0, 0.70 * sandbox_score + 0.30 * kb_score), 4)
        scores.robustness = self.compute_robustness(dispatches)

        final_text = self._get_final_assistant_text(messages)
        scores.communication = self.compute_communication_substance(
            final_text,
            ["PLAN.md", "strategy_lab.py", "Phase", "Backtester", "PerformanceMetrics"],
            min(sum(1 for x in ["- ", "1.", "2.", "3."] if x in final_text) / 2.0, 1.0),
        )
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        print(f"[grader] CP55 sandbox={sandbox_score:.3f} kb={kb_score:.3f}")
        return scores
