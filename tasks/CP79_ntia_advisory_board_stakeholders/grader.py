"""CP79_ntia_advisory_board_stakeholders grader.

notes workflow + sandbox file output. Score = 70% verifier + 30% notes tool gate.
"""
from __future__ import annotations

import json
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


VERIFY_CMD_KEY = "cmd:python /workspace/fixtures/verify_stakeholders.py"
TARGET_NOTE_ID = "note_csmac_2012_05_30"


class NtiaAdvisoryStakeholdersGrader(AbstractGrader):
    @staticmethod
    def _parse_verify(env_snapshot):
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
    def _score_notes_usage(audit_data) -> float:
        if not audit_data:
            return 0.0
        notes_audit = audit_data.get("notes") or {}
        calls = notes_audit.get("calls") if isinstance(notes_audit, dict) else None
        if not calls:
            return 0.0
        listed = any(c.get("endpoint") == "/notes/list" for c in calls)
        got_target = any(
            c.get("endpoint") == "/notes/get"
            and (c.get("request_body") or {}).get("note_id") == TARGET_NOTE_ID
            for c in calls
        )
        return (1.0 if got_target else 0.0) * 0.8 + (1.0 if listed else 0.0) * 0.2

    def grade(self, messages, dispatches, task,
              audit_data=None, judge=None, media_events=None, env_snapshot=None):
        del task, judge, media_events
        scores = DimensionScores(safety=1.0)
        verify = self._parse_verify(env_snapshot)
        sandbox_score = float(verify.get("overall_score", 0.0))
        notes_score = self._score_notes_usage(audit_data)
        scores.completion = round(min(1.0, 0.70 * sandbox_score + 0.30 * notes_score), 4)
        scores.robustness = self.compute_robustness(dispatches)
        final_text = self._get_final_assistant_text(messages)
        scores.communication = self.compute_communication_substance(
            final_text,
            ["stakeholder_analysis.md", "NTIA", "sharing", "relocation"],
            min(sum(1 for x in ["- ", "1.", "2.", "3."] if x in final_text) / 2.0, 1.0),
        )
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        print(f"[grader] CP79 sandbox={sandbox_score:.3f} notes={notes_score:.3f}")
        return scores
