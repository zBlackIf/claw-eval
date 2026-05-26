"""T165zh grader: calendar schema mismatch recovery meeting prep."""

from __future__ import annotations

import json
import re
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


class CalendarSchemaRecoveryMeetingPrepGrader(AbstractGrader):
    """Grade recovery capability separately from final meeting-material quality.

    Scoring model mirrors task.yaml:
    - completion = 0.50 * recovery_capability
                 + 0.30 * obstacle_handling
                 + 0.20 * output_quality
    - robustness = max(standard tool-error recovery, recovery_capability)

    The important design choice is that recovery_capability measures whether
    the agent demonstrated the right recovery skill, not whether its platform
    happened to allow schema-invalid tool arguments.

    recovery_capability bands:
    - 1.0: any full-credit recovery proof:
      * successful calendar_list_events retry with server-side "date";
      * reading /workspace/data/calendar_export.json;
      * demonstrated correct knowledge that "date" is required, including
        Bash/curl attempts or explicit diagnosis in assistant text.
    - 0.9: accurate diagnosis with an actionable explanation, but without a
      stronger execution proof.
    - 0.4: multiple alternatives attempted, but no correct parameter/root-cause
      proof.
    - 0.1: hit tool errors but only repeated/weak recovery behavior.
    - 0.0: no meaningful recovery attempt.

    obstacle_handling bands:
    - 1.0: full recovery plus 3+ distinct alternative/probe paths.
    - 0.9: full recovery after an error, or accurate diagnosis with 2+ paths.
    - 0.7: accurate diagnosis with 1 path.
    - 0.4: some broad exploration without accurate diagnosis.
    - 0.1: tool error observed, but behavior is mostly ineffective.
    - 0.0: no obstacle evidence.

    output_quality uses the better of:
    - meeting material score: coverage of all events, attendees, contact info,
      external attendee, busiest colleagues, and time/place details;
    - diagnostic report score: root cause + attempted paths + fix/workaround.
    """

    EVENT_TITLES = ("产品方案评审", "客户演示", "技术选型讨论", "全员周会")
    INTERNAL_ATTENDEES = ("王明", "李华", "赵蕾", "张伟", "马强", "周明")
    CONTACT_TOKENS = (
        "wangming@company.com",
        "lihua@company.com",
        "zhaolei@company.com",
        "zhangwei@company.com",
        "maqiang@company.com",
        "zhouming@company.com",
        "13800201001",
        "13800201002",
        "13800201003",
        "13800201004",
        "13800201005",
        "13800201006",
    )
    DIAGNOSIS_TERMS = (
        "schema",
        "参数",
        "不一致",
        "422",
        "body.date",
        "date 字段",
        "date字段",
        "Field required",
        "start_date",
    )

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
        del audit_data, judge, media_events, env_snapshot

        scores = DimensionScores()
        final_text = self._get_final_assistant_text(messages)
        all_text = self._get_all_assistant_text(messages)

        recovery_capability = self._score_recovery_capability(dispatches, all_text)
        obstacle_handling = self._score_obstacle_handling(dispatches, all_text, recovery_capability)
        output_quality = self._score_output_quality(final_text)

        completion = (
            0.50 * recovery_capability
            + 0.30 * obstacle_handling
            + 0.20 * output_quality
        )

        scores.completion = round(min(completion, 1.0), 4)
        scores.robustness = round(max(self.compute_robustness(dispatches), recovery_capability), 2)
        scores.communication = output_quality
        scores.safety = 1.0
        scores.efficiency_turns = len(
            [m for m in messages if m.message.role == "assistant"]
        )
        return scores

    def _score_recovery_capability(
        self,
        dispatches: list[ToolDispatch],
        assistant_text: str,
    ) -> float:
        # 1.0 path A: loose-schema clients can retry the mock API with the
        # actual server contract, {"date": "2026-03-27", "days": 1}.
        if self._successful_date_parameter_retry(dispatches):
            return 1.0
        # 1.0 path B: strict-schema clients can avoid invalid tool input and
        # use the task-provided workspace fallback export instead.
        if self._workspace_calendar_export_used(dispatches):
            return 1.0
        # 1.0 path C: strict-schema clients may prove the same knowledge via
        # Bash/curl or explicit trace text, even if sandbox networking blocks
        # the actual curl request.
        if self._demonstrated_correct_date_knowledge(dispatches, assistant_text):
            return 1.0
        # 0.9 path D: a precise diagnosis plus actionable fix is valuable in
        # production, even when no alternate data path is executed.
        if self._accurate_diagnosis(assistant_text):
            return 0.9
        # 0.4: the agent is trying a few routes, but has not identified the
        # server-side "date" contract.
        if self._alternative_path_count(dispatches) >= 2:
            return 0.4
        # 0.1: at least an obstacle was encountered, but recovery quality is low
        # (for example repeated invalid start_date/end_date calls).
        if any(d.response_status >= 400 for d in dispatches):
            return 0.1
        return 0.0

    def _score_obstacle_handling(
        self,
        dispatches: list[ToolDispatch],
        assistant_text: str,
        recovery_capability: float,
    ) -> float:
        alternatives = self._alternative_path_count(dispatches)
        has_error = any(d.response_status >= 400 for d in dispatches)
        diagnosed = self._accurate_diagnosis(assistant_text)

        # Strongest obstacle handling: correct recovery plus broad exploration,
        # useful for traces like "API failed -> curl probe -> workspace export".
        if recovery_capability >= 1.0 and alternatives >= 3:
            return 1.0
        # Full recovery after observing an error is already high quality, even
        # if it uses one direct workaround.
        if recovery_capability >= 1.0 and has_error:
            return 0.9
        # Accurate diagnosis plus multiple paths is also high quality; it may
        # still lack the final full-credit recovery proof.
        if diagnosed and alternatives >= 2:
            return 0.9
        if diagnosed and alternatives >= 1:
            return 0.7
        if alternatives >= 2:
            return 0.4
        if has_error:
            return 0.1
        return 0.0

    def _score_output_quality(self, final_text: str) -> float:
        if not final_text.strip():
            return 0.0

        # A successful agent may either finish the meeting-prep artifact or,
        # when blocked by platform constraints, produce a useful engineering
        # diagnosis. Score whichever output type is stronger.
        material_score = self._score_meeting_material(final_text)
        diagnostic_score = self._score_diagnostic_report(final_text)
        return round(max(material_score, diagnostic_score), 2)

    def _score_meeting_material(self, text: str) -> float:
        event_rate = self._coverage_rate(text, self.EVENT_TITLES)
        attendee_rate = self._coverage_rate(text, self.INTERNAL_ATTENDEES)
        contact_hits = sum(1 for token in self.CONTACT_TOKENS if token in text)
        contact_rate = min(contact_hits / 6, 1.0)

        has_external = "陈总" in text and any(term in text for term in ("外部", "不在通讯录", "无通讯录"))
        has_busiest = (
            ("李华" in text and "3" in text)
            and ("赵蕾" in text and "3" in text)
            and any(term in text for term in ("最忙", "最多", "高频"))
        )
        has_time_place = self._contains_any_time(text) and any(
            place in text for place in ("会议室A", "会议室B", "技术区开放空间", "大会议室")
        )

        score = (
            0.30 * event_rate
            + 0.20 * attendee_rate
            + 0.20 * contact_rate
            + 0.10 * float(has_external)
            + 0.10 * float(has_busiest)
            + 0.10 * float(has_time_place)
        )
        return min(score, 1.0)

    def _score_diagnostic_report(self, text: str) -> float:
        if not self._accurate_diagnosis(text):
            return 0.0

        has_fix = self._mentions_date_field(text) and any(
            term in text for term in ("修复", "改为", "使用 date", "提供", "备用", "calendar_export")
        )
        has_attempts = any(term in text for term in ("已尝试", "尝试", "curl", "Bash", "替代", "备用"))
        has_root_cause = any(term in text for term in ("schema", "服务端", "tool", "API")) and any(
            term in text for term in ("不一致", "缺失", "不匹配", "不接受")
        )

        if has_root_cause and has_attempts and has_fix:
            return 0.85
        if has_root_cause and has_fix:
            return 0.65
        return 0.5

    @staticmethod
    def _coverage_rate(text: str, tokens: tuple[str, ...]) -> float:
        return sum(1 for token in tokens if token in text) / len(tokens)

    @staticmethod
    def _contains_any_time(text: str) -> bool:
        return bool(re.search(r"\b(09|9|11|14|16):?00\b", text))

    @staticmethod
    def _dump_dispatch(dispatch: ToolDispatch) -> str:
        return json.dumps(
            {
                "request": dispatch.request_body,
                "response": dispatch.response_body,
            },
            ensure_ascii=False,
            default=str,
        )

    def _successful_date_parameter_retry(self, dispatches: list[ToolDispatch]) -> bool:
        return any(
            d.tool_name == "calendar_list_events"
            and d.response_status < 400
            and "date" in d.request_body
            for d in dispatches
        )

    def _workspace_calendar_export_used(self, dispatches: list[ToolDispatch]) -> bool:
        for dispatch in dispatches:
            if dispatch.response_status >= 400:
                continue
            haystack = self._dump_dispatch(dispatch)
            if "/workspace/data/calendar_export.json" in haystack or "data/calendar_export.json" in haystack:
                return True
        return False

    def _demonstrated_correct_date_knowledge(
        self,
        dispatches: list[ToolDispatch],
        assistant_text: str,
    ) -> bool:
        if self._mentions_date_field(assistant_text):
            return True

        for dispatch in dispatches:
            haystack = self._dump_dispatch(dispatch)
            if dispatch.tool_name == "calendar_list_events" and "date" in dispatch.request_body:
                return True
            if re.search(r'"date"\s*:\s*"2026-03-27"', haystack):
                return True
            if "body.date" in haystack or "Field required" in haystack and "date" in haystack:
                if dispatch.tool_name in {"Bash", "Read"}:
                    return True
        return False

    def _accurate_diagnosis(self, text: str) -> bool:
        if not text:
            return False
        has_mismatch = any(term in text for term in ("schema", "不一致", "不匹配", "422", "服务端"))
        return has_mismatch and self._mentions_date_field(text)

    @staticmethod
    def _mentions_date_field(text: str) -> bool:
        if not text:
            return False
        patterns = (
            r"\bbody\.date\b",
            r"\bdate\s*字段",
            r"需要\s*`?date`?",
            r"使用\s*`?date`?",
            r"正确参数.*\bdate\b",
            r"而不是\s*`?start_date`?",
            r'"date"\s*:',
        )
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)

    def _alternative_path_count(self, dispatches: list[ToolDispatch]) -> int:
        alternatives: set[str] = set()
        for dispatch in dispatches:
            haystack = self._dump_dispatch(dispatch)
            if dispatch.tool_name == "calendar_list_events" and "date" in dispatch.request_body:
                alternatives.add("date_parameter_retry")
            if "calendar_export.json" in haystack:
                alternatives.add("workspace_export")
            if dispatch.tool_name == "Bash":
                alternatives.add("bash")
                if '"date"' in haystack or "body.date" in haystack:
                    alternatives.add("bash_date_probe")
            if dispatch.tool_name == "Read":
                alternatives.add("read")
            if dispatch.tool_name == "calendar_get_event":
                alternatives.add("event_probe")
            if dispatch.tool_name in {"contacts_search", "contacts_get"}:
                alternatives.add("contacts_lookup")
        return len(alternatives)
