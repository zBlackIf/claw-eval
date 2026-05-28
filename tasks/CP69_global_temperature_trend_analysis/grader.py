"""Grader for CP69_global_temperature_trend_analysis.

Completion blends the hidden workspace verifier with service audit evidence.
The service portion checks for a real workflow chain: list/search, targeted get,
cross-check, submit, and confirm.
"""

from __future__ import annotations

import json
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage

VERIFY_CMD_KEY = 'cmd:python /workspace/fixtures/verify_trend_report.py'
SERVICE_NAME = 'climate_data'
CONTENT_WEIGHT = 0.65
WORKFLOW_WEIGHT = 0.35
COMMUNICATION_ENTITIES = ['trend_report.md', 'GISTEMP', '加速']


class GlobalTemperatureTrendAnalysisGrader(AbstractGrader):
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

    @staticmethod
    def _service_calls(audit_data: dict[str, dict] | None) -> list[dict]:
        if not audit_data:
            return []
        service_audit = audit_data.get(SERVICE_NAME) or {}
        calls = service_audit.get("calls") if isinstance(service_audit, dict) else None
        return calls if isinstance(calls, list) else []

    @classmethod
    def _workflow_usage_score(cls, audit_data: dict[str, dict] | None) -> float:
        calls = [c for c in cls._service_calls(audit_data) if isinstance(c, dict)]
        if not calls:
            return 0.0
        endpoints = {c.get("endpoint") for c in calls}
        get_ids = {
            (c.get("request_body") or {}).get("record_id")
            for c in calls
            if c.get("endpoint") == f"/{SERVICE_NAME}/get"
        }
        get_ids.discard(None)
        submitted = [c for c in calls if c.get("endpoint") == f"/{SERVICE_NAME}/submit"]
        confirmed = [c for c in calls if c.get("endpoint") == f"/{SERVICE_NAME}/confirm"]
        submit_quality = 0.0
        if submitted:
            best = max(len(str((c.get("request_body") or {}).get("content") or "")) for c in submitted)
            has_sources = any((c.get("request_body") or {}).get("source_ids") for c in submitted)
            submit_quality = 1.0 if best >= 80 and has_sources else 0.6
        confirm_quality = 1.0 if confirmed else 0.0
        score = 0.0
        score += 0.12 if f"/{SERVICE_NAME}/list" in endpoints else 0.0
        score += 0.16 if f"/{SERVICE_NAME}/search" in endpoints else 0.0
        score += 0.18 if len(get_ids) >= 2 else (0.09 if get_ids else 0.0)
        score += 0.18 if f"/{SERVICE_NAME}/cross_check" in endpoints else 0.0
        score += 0.18 * submit_quality
        score += 0.18 * confirm_quality
        depth_factor = min(1.0, len(calls) / 5.0)
        return round(min(1.0, score) * depth_factor, 4)

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
        content_score = min(max(self._overall_score(verify), 0.0), 1.0)
        workflow_score = self._workflow_usage_score(audit_data)
        scores.completion = round(min(1.0, CONTENT_WEIGHT * content_score + WORKFLOW_WEIGHT * workflow_score), 4)
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
