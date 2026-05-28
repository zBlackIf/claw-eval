"""CP68_nasa_uap_hearing_qa_extraction grader.

Workflow-style: deliverable is a kb_update_article call on KB-NASA-UAP-2025-QA.
Score by inspecting audit_data['kb'] for the latest update payload, then
running the 9 hidden anchors against that content.
"""
from __future__ import annotations

import re
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


TARGET_ARTICLE_ID = "KB-NASA-UAP-2025-QA"
TEMPLATE_ARTICLE_ID = "KB-MEETING-QA-TEMPLATE"


class NasaUapQaExtractionGrader(AbstractGrader):
    @staticmethod
    def _latest_update_content(audit_data: dict[str, dict] | None, article_id: str) -> str:
        if not audit_data:
            return ""
        kb_audit = audit_data.get("kb") or {}
        calls = kb_audit.get("calls") if isinstance(kb_audit, dict) else None
        if not calls:
            return ""
        latest = ""
        for entry in calls:
            if entry.get("endpoint") != "/kb/articles/update":
                continue
            body = entry.get("request_body") or {}
            if body.get("article_id") == article_id:
                latest = body.get("content") or latest
        return latest

    @staticmethod
    def _fetched_articles(audit_data: dict[str, dict] | None) -> set[str]:
        if not audit_data:
            return set()
        kb_audit = audit_data.get("kb") or {}
        calls = kb_audit.get("calls") if isinstance(kb_audit, dict) else None
        if not calls:
            return set()
        seen = set()
        for entry in calls:
            if entry.get("endpoint") == "/kb/articles/get":
                body = entry.get("request_body") or {}
                aid = body.get("article_id")
                if aid:
                    seen.add(aid)
        return seen

    @staticmethod
    def _score_content(content: str) -> tuple[float, dict]:
        if not content.strip():
            return 0.0, {k: 0.0 for k in [
                "non_empty", "exchange_count", "section_separation",
                "drake_kirkpatrick", "case_numbers", "faa_qa",
                "nhi_question", "attribution", "numbering",
            ]}
        lower = content.lower()
        components = {}
        components["non_empty"] = 1.0 if len(content.strip()) > 600 else 0.4

        exchange_pat = re.findall(r"(?:^|\n)\s*(?:\d+[\.\):]|#{2,3}\s*(?:exchange|q&?a|question))", lower)
        questioner_pat = re.findall(r"question(?:er)?|asked|q:", lower)
        if len(exchange_pat) >= 10 or len(questioner_pat) >= 10:
            components["exchange_count"] = 1.0
        elif len(exchange_pat) >= 5 or len(questioner_pat) >= 5:
            components["exchange_count"] = 0.5
        else:
            components["exchange_count"] = 0.0

        has_public = bool(re.search(r"public\s+q\s*&?\s*a|curated|audience|submitted", lower))
        has_panel = bool(re.search(r"panel|presenter|presentation", lower))
        components["section_separation"] = 1.0 if has_public and has_panel else (0.5 if has_public or has_panel else 0.0)

        has_drake = "drake" in lower
        has_kirk = "kirkpatrick" in lower
        has_nums_q = bool(re.search(r"how\s+(?:big|many|large)|database|number", lower))
        if has_drake and has_kirk and has_nums_q:
            components["drake_kirkpatrick"] = 1.0
        elif has_drake and has_kirk:
            components["drake_kirkpatrick"] = 0.5
        else:
            components["drake_kirkpatrick"] = 0.0

        has_800 = bool(re.search(r"800|eight\s+hundred", lower))
        has_pct = bool(re.search(r"2.{0,5}5\s*%|single.digit|percent", lower))
        if has_800 and has_pct:
            components["case_numbers"] = 1.0
        elif has_800 or has_pct:
            components["case_numbers"] = 0.5
        else:
            components["case_numbers"] = 0.0

        has_faa = bool(re.search(r"faa|freie", lower))
        faa_topics = sum([
            bool(re.search(r"radar\s+data|retain|retention", lower)),
            bool(re.search(r"filter", lower)),
            bool(re.search(r"report.*process|pilot.*report", lower)),
            bool(re.search(r"deploy|coverage|site", lower)),
        ])
        if has_faa and faa_topics >= 2:
            components["faa_qa"] = 1.0
        elif has_faa:
            components["faa_qa"] = 0.5
        else:
            components["faa_qa"] = 0.0

        nhi_pats = [
            r"non.?human\s+intelligence",
            r"extraterrestrial\s+(?:origin|life|intelligence)",
            r"alien",
            r"extraordinary\s+claims.*extraordinary\s+evidence",
        ]
        nhi_hits = sum(1 for p in nhi_pats if re.search(p, lower))
        if nhi_hits >= 2:
            components["nhi_question"] = 1.0
        elif nhi_hits >= 1:
            components["nhi_question"] = 0.5
        else:
            components["nhi_question"] = 0.0

        named = sum(1 for n in ["drake", "kirkpatrick", "spergel", "fox", "freie",
                                "gold", "walter", "bianco", "bontempi", "wright",
                                "grinspoon", "berea"] if n in lower)
        if named >= 6:
            components["attribution"] = 1.0
        elif named >= 3:
            components["attribution"] = 0.5
        else:
            components["attribution"] = 0.0

        numbered = len(re.findall(r"(?:^|\n)\s*\d+[\.\):]", content)) >= 5
        headed = len(re.findall(r"(?:^|\n)#{2,4}\s", content)) >= 5
        separated = len(re.findall(r"(?:^|\n)---", content)) >= 3
        components["numbering"] = 1.0 if numbered or headed else (0.5 if separated else 0.0)

        weights = {
            "non_empty": 0.05,
            "exchange_count": 0.15,
            "section_separation": 0.10,
            "drake_kirkpatrick": 0.10,
            "case_numbers": 0.10,
            "faa_qa": 0.15,
            "nhi_question": 0.10,
            "attribution": 0.15,
            "numbering": 0.10,
        }
        overall = sum(weights[k] * components[k] for k in weights)
        return round(overall, 4), components

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
        latest = self._latest_update_content(audit_data, TARGET_ARTICLE_ID)
        content_score, components = self._score_content(latest)

        fetched = self._fetched_articles(audit_data)
        tool_bonus = 0.0
        if TARGET_ARTICLE_ID in fetched:
            tool_bonus += 0.5
        if TEMPLATE_ARTICLE_ID in fetched:
            tool_bonus += 0.5
        tool_factor = 0.85 + 0.15 * tool_bonus

        scores.completion = round(min(1.0, content_score * tool_factor), 4)
        scores.robustness = self.compute_robustness(dispatches)
        final_text = self._get_final_assistant_text(messages)
        scores.communication = self.compute_communication_substance(
            final_text,
            ["NASA", "UAP", "Q&A", "kb_update"],
            min(sum(1 for x in ["- ", "1.", "2.", "3."] if x in final_text) / 2.0, 1.0),
        )
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        print(f"[grader] CP68 content={content_score:.3f} tool_factor={tool_factor:.3f} comp={components}")
        return scores
