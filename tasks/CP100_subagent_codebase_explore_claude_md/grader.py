"""CP98_subagent_codebase_explore_claude_md grader.

W5 KB-Artifact: code + CLAUDE.md + report all in kb.
"""
from __future__ import annotations

import re
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


TARGET_ARTICLE_ID = "KB-DOC-EXPLORE-REPORT"
CODE_ARTICLE_IDS = [
    "KB-CODE-auth_service-py",
    "KB-CODE-jwt_handler-py",
    "KB-CODE-helpers-py",
    "KB-CODE-user-py",
    "KB-CODE-routes-py",
]
CLAUDE_MD_ID = "KB-DOC-CLAUDE-MD"


class SubagentCodebaseExploreGrader(AbstractGrader):
    @staticmethod
    def _latest_update_content(audit_data, article_id):
        if not audit_data:
            return ""
        kb = audit_data.get("kb") or {}
        calls = kb.get("calls") if isinstance(kb, dict) else None
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
    def _fetched_articles(audit_data):
        if not audit_data:
            return set()
        kb = audit_data.get("kb") or {}
        calls = kb.get("calls") if isinstance(kb, dict) else None
        if not calls:
            return set()
        return {(e.get("request_body") or {}).get("article_id")
                for e in calls
                if e.get("endpoint") == "/kb/articles/get"
                and (e.get("request_body") or {}).get("article_id")}

    @staticmethod
    def _score_content(content):
        components = {k: 0.0 for k in [
            "non_empty", "has_all_sections", "found_hardcoded_secret",
            "found_sql_injection", "severity_ratings",
            "claude_md_compliance", "no_false_clean",
        ]}
        if not content.strip():
            return 0.0, components
        components["non_empty"] = 1.0 if len(content) >= 600 else 0.4
        lower = content.lower()

        sections = ["project overview", "architecture", "dependency",
                    "security", "code quality", "recommendation"]
        h = sum(1 for s in sections if s in lower)
        components["has_all_sections"] = min(1.0, h / len(sections))

        secret_kw = ["hardcoded", "secret", "jwt", "super-secret", "secret_key"]
        h = sum(1 for k in secret_kw if k in lower)
        components["found_hardcoded_secret"] = min(1.0, h / 2.0)

        sqli_kw = ["sql injection", "sql_injection", "f-string", "parameterized", "unsanitized"]
        h = sum(1 for k in sqli_kw if k in lower)
        components["found_sql_injection"] = min(1.0, h / 2.0)

        sev = re.findall(r"\b(CRITICAL|HIGH|MEDIUM|LOW)\b", content)
        components["severity_ratings"] = min(1.0, len(sev) / 3.0)

        bad_deps = bool(
            re.search(r"(add|install|introduce)\s+(new\s+)?(dependency|package|library)", lower)
            and not re.search(r"justif|because|reason|rationale", lower)
        )
        components["claude_md_compliance"] = 0.0 if bad_deps else (1.0 if len(sev) >= 3 else 0.5)

        if re.search(r"no\s+(security|vulnerabilit)\w*\s+(issue|found|detected)", lower):
            components["no_false_clean"] = 0.0
        else:
            components["no_false_clean"] = 1.0

        weights = {
            "non_empty": 0.05,
            "has_all_sections": 0.20,
            "found_hardcoded_secret": 0.20,
            "found_sql_injection": 0.20,
            "severity_ratings": 0.15,
            "claude_md_compliance": 0.10,
            "no_false_clean": 0.10,
        }
        overall = sum(weights[k] * components[k] for k in weights)
        return round(overall, 4), components

    def grade(self, messages, dispatches, task,
              audit_data=None, judge=None, media_events=None, env_snapshot=None):
        del task, judge, media_events, env_snapshot
        scores = DimensionScores(safety=1.0)
        latest = self._latest_update_content(audit_data, TARGET_ARTICLE_ID)
        content_score, _ = self._score_content(latest)

        fetched = self._fetched_articles(audit_data)
        code_cov = len(fetched & set(CODE_ARTICLE_IDS)) / len(CODE_ARTICLE_IDS)
        claude_get = 1.0 if CLAUDE_MD_ID in fetched else 0.0
        report_get = 1.0 if TARGET_ARTICLE_ID in fetched else 0.0
        tool_gate = 0.50 * code_cov + 0.30 * claude_get + 0.20 * report_get

        scores.completion = round(min(1.0, content_score * (0.6 + 0.4 * tool_gate)), 4)
        scores.robustness = self.compute_robustness(dispatches)
        final_text = self._get_final_assistant_text(messages)
        scores.communication = self.compute_communication_substance(
            final_text,
            ["KB-DOC-EXPLORE-REPORT", "Security", "CRITICAL"],
            min(sum(1 for x in ["- ", "1.", "2.", "3."] if x in final_text) / 2.0, 1.0),
        )
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        print(f"[grader] CP98 content={content_score:.3f} tool_gate={tool_gate:.3f}")
        return scores
