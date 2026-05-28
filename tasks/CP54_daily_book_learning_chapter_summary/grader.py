"""CP54_daily_book_learning_chapter_summary grader.

Workflow/W5 KB-Artifact task. Completion is scored from kb audit_data:
the main deliverable is updating KB-PATTERN-LIBRARY and KB-EMOTION-LIBRARY,
with the daily learning log as a secondary KB artifact. Sandbox files are
input evidence only.
"""

from __future__ import annotations

import re
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage

PATTERN_ARTICLE_ID = "KB-PATTERN-LIBRARY"
EMOTION_ARTICLE_ID = "KB-EMOTION-LIBRARY"
DAILY_LOG_ARTICLE_ID = "KB-DAILY-LEARNING-LOG-20260328"


class DailyBookLearningGrader(AbstractGrader):
    @staticmethod
    def _kb_calls(audit_data: dict[str, dict] | None) -> list[dict]:
        if not audit_data:
            return []
        kb_audit = audit_data.get("kb") or {}
        calls = kb_audit.get("calls") if isinstance(kb_audit, dict) else None
        return calls if isinstance(calls, list) else []

    @classmethod
    def _latest_update_content(cls, audit_data: dict[str, dict] | None, article_id: str) -> str:
        latest = ""
        for entry in cls._kb_calls(audit_data):
            if entry.get("endpoint") != "/kb/articles/update":
                continue
            body = entry.get("request_body") or {}
            if body.get("article_id") == article_id:
                latest = body.get("content") or latest
        return latest

    @classmethod
    def _fetched_articles(cls, audit_data: dict[str, dict] | None) -> set[str]:
        fetched: set[str] = set()
        for entry in cls._kb_calls(audit_data):
            if entry.get("endpoint") != "/kb/articles/get":
                continue
            body = entry.get("request_body") or {}
            aid = body.get("article_id")
            if aid:
                fetched.add(aid)
        return fetched

    @classmethod
    def _updated_articles(cls, audit_data: dict[str, dict] | None) -> set[str]:
        updated: set[str] = set()
        for entry in cls._kb_calls(audit_data):
            if entry.get("endpoint") != "/kb/articles/update":
                continue
            body = entry.get("request_body") or {}
            aid = body.get("article_id")
            if aid:
                updated.add(aid)
        return updated

    @classmethod
    def _tool_flow_score(cls, audit_data: dict[str, dict] | None) -> float:
        calls = cls._kb_calls(audit_data)
        if not calls:
            return 0.0
        endpoints = {entry.get("endpoint") for entry in calls}
        fetched = cls._fetched_articles(audit_data)
        updated = cls._updated_articles(audit_data)
        score = 0.0
        if "/kb/search" in endpoints:
            score += 0.2
        if {PATTERN_ARTICLE_ID, EMOTION_ARTICLE_ID} <= fetched:
            score += 0.4
        elif fetched & {PATTERN_ARTICLE_ID, EMOTION_ARTICLE_ID}:
            score += 0.2
        if {PATTERN_ARTICLE_ID, EMOTION_ARTICLE_ID} <= updated:
            score += 0.4
        elif updated & {PATTERN_ARTICLE_ID, EMOTION_ARTICLE_ID}:
            score += 0.2
        return min(score, 1.0)

    @staticmethod
    def _daily_log_score(content: str) -> float:
        if not content.strip():
            return 0.0
        lower = content.lower()
        has_book = "故事的力量" in content or "story_power" in lower
        has_entries = bool(re.search(r"\bP0*0?[3-9]\b", content)) and bool(
            re.search(r"\bE0*0?[3-9]\b", content)
        )
        has_insight = any(k in content for k in ["洞察", "启发", "总结", "学习记录"])
        length_score = 1.0 if len(content.strip()) >= 300 else (0.5 if len(content.strip()) >= 120 else 0.0)
        return round(0.4 * length_score + 0.25 * has_book + 0.25 * has_entries + 0.10 * has_insight, 4)

    @staticmethod
    def _citation_score(pattern_content: str, emotion_content: str) -> float:
        combined = pattern_content + "\n" + emotion_content
        if not combined.strip():
            return 0.0
        book_hits = sum(1 for c in [pattern_content, emotion_content] if "故事的力量" in c)
        chapter_hits = len(set(re.findall(r"第[一二三四五六七八九十\d]+章", combined)))
        return round(min(1.0, 0.4 * (book_hits / 2.0) + 0.6 * min(chapter_hits / 3.0, 1.0)), 4)

    @staticmethod
    def _count_new_entries(updated_content: str, prefix: str, baseline_max: int) -> int:
        """Count distinct entry IDs (e.g. P003+, E003+) in the updated library content."""
        pat = re.compile(rf"\b{prefix}0*([1-9]\d*)\b")
        ids = set()
        for m in pat.finditer(updated_content):
            try:
                n = int(m.group(1))
                if n > baseline_max:
                    ids.add(n)
            except ValueError:
                continue
        return len(ids)

    def _score_kb_updates(self, audit_data: dict[str, dict] | None) -> tuple[float, dict]:
        latest_pattern = self._latest_update_content(audit_data, PATTERN_ARTICLE_ID)
        latest_emotion = self._latest_update_content(audit_data, EMOTION_ARTICLE_ID)
        latest_log = self._latest_update_content(audit_data, DAILY_LOG_ARTICLE_ID)

        pattern_new = self._count_new_entries(latest_pattern, "P", baseline_max=2) if latest_pattern else 0
        emotion_new = self._count_new_entries(latest_emotion, "E", baseline_max=2) if latest_emotion else 0

        pattern_score = min(pattern_new / 3.0, 1.0)
        emotion_score = min(emotion_new / 3.0, 1.0)
        citation_score = self._citation_score(latest_pattern, latest_emotion)
        daily_log_score = self._daily_log_score(latest_log)
        tool_flow_score = self._tool_flow_score(audit_data)
        kb_total = (
            0.30 * pattern_score
            + 0.30 * emotion_score
            + 0.15 * citation_score
            + 0.15 * daily_log_score
            + 0.10 * tool_flow_score
        )
        return round(kb_total, 4), {
            "pattern_new": pattern_new,
            "emotion_new": emotion_new,
            "citation": round(citation_score, 4),
            "daily_log": round(daily_log_score, 4),
            "tool_flow": round(tool_flow_score, 4),
        }

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
        del task, judge, media_events, env_snapshot
        scores = DimensionScores(safety=1.0)
        kb_score, kb_detail = self._score_kb_updates(audit_data)
        scores.completion = round(min(1.0, kb_score), 4)
        scores.robustness = self.compute_robustness(dispatches)

        final_text = self._get_final_assistant_text(messages)
        scores.communication = self.compute_communication_substance(
            final_text,
            ["故事的力量", "pattern", "emotion", "KB"],
            min(sum(1 for x in ["- ", "1.", "2.", "3."] if x in final_text) / 2.0, 1.0),
        )
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        print(f"[grader] CP54 kb={kb_score:.3f} detail={kb_detail}")
        return scores
