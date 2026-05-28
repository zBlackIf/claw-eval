"""CP76_ntia_advisory_board_attendee_list grader.

notes workflow + sandbox file output.
- 70% sandbox verifier score (attendees.md content)
- 30% notes tool gate (agent must notes_list + notes_get the transcript note)
"""
from __future__ import annotations

import json
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


VERIFY_CMD_KEY = "cmd:python /workspace/fixtures/verify_attendees.py"
TARGET_NOTE_ID = "note_csmac_2012_05_30"


class NtiaAdvisoryBoardAttendeeListGrader(AbstractGrader):
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
        got_target = False
        for c in calls:
            if c.get("endpoint") != "/notes/get":
                continue
            body = c.get("request_body") or {}
            if body.get("note_id") == TARGET_NOTE_ID:
                got_target = True
                break
        # Heavily weight get_target — that's how agent reads transcript
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
            ["attendees.md", "Fontes", "Chair", "remote"],
            min(sum(1 for x in ["- ", "1.", "2.", "3."] if x in final_text) / 2.0, 1.0),
        )
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        print(f"[grader] CP76 sandbox={sandbox_score:.3f} notes={notes_score:.3f}")
        return scores
