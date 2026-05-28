"""CP65_java_codebase_reverse_engineer_requirements grader.

W5 KB-Artifact: code + requirements doc all in kb.
"""
from __future__ import annotations

import re
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


TARGET_ARTICLE_ID = "KB-CODE-REQUIREMENTS-DOC"
CODE_ARTICLE_IDS = [
    "KB-CODE-Contract-java",
    "KB-CODE-ContractController-java",
    "KB-CODE-ContractService-java",
    "KB-CODE-ContractServiceImpl-java",
]
HALLUCINATIONS = [
    "email notification", "pdf generation", "pdf export",
    "user authentication", "login page", "oauth",
    "role-based access", "send email", "generate report",
    "ldap", "sso integration",
]


class JavaReverseRequirementsGrader(AbstractGrader):
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
    def _score_content(text):
        components = {k: 0.0 for k in [
            "non_empty", "overview", "modules", "data_model",
            "business_rules", "deposit_rule", "status_transitions",
            "settlement_periods", "api_section", "no_hallucination",
        ]}
        if not text.strip() or len(text) < 400:
            return 0.0, components
        components["non_empty"] = 1.0
        lower = text.lower()

        if re.search(r"(overview|introduction|system\s+description|summary|系统概述|系统概览)", lower):
            components["overview"] = 1.0

        mod_kw = ["creat", "modif", "terminat", "search", "settlement", "创建", "修改", "终止", "搜索", "结算"]
        h = sum(1 for kw in mod_kw if kw in lower)
        components["modules"] = 1.0 if h >= 4 else (0.5 if h >= 3 else 0.0)

        ent_kw = ["tenant", "monthlyrent", "monthly_rent", "monthly rent",
                  "deposit", "propertytype", "property_type", "property type",
                  "billing", "area", "租户", "月租"]
        h = sum(1 for kw in ent_kw if kw in lower)
        components["data_model"] = 1.0 if h >= 4 else (0.5 if h >= 2 else 0.0)

        rules_pats = [
            r"3\s*(months?|x|\*|times|个月)",
            r"100[,.]?000",
            r"(pro.?rat|partial\s+period|按比例)",
            r"(penalty|termination\s+fee|违约金)",
            r"(status.*active|active.*status)",
            r"billing\s+cycle|计费周期",
        ]
        h = sum(1 for p in rules_pats if re.search(p, lower))
        components["business_rules"] = 1.0 if h >= 3 else (0.5 if h >= 2 else 0.0)

        if re.search(r"(deposit|security|押金).{0,50}(3|three|三).{0,30}(month|rent|月)", lower):
            components["deposit_rule"] = 1.0

        statuses = ["draft", "active", "archived", "terminated"]
        h = sum(1 for s in statuses if s in lower)
        components["status_transitions"] = 1.0 if h >= 3 else (0.5 if h >= 2 else 0.0)

        if re.search(r"settlement\s+period|结算周期", lower):
            components["settlement_periods"] = 1.0

        api_kw = ["/api/contracts", "post", "get", "endpoint", "rest", "put", "delete"]
        h = sum(1 for kw in api_kw if kw in lower)
        components["api_section"] = 1.0 if h >= 4 else (0.5 if h >= 2 else 0.0)

        if any(h in lower for h in HALLUCINATIONS):
            components["no_hallucination"] = 0.0
        else:
            components["no_hallucination"] = 1.0

        weights = {
            "non_empty": 0.05,
            "overview": 0.05,
            "modules": 0.10,
            "data_model": 0.15,
            "business_rules": 0.15,
            "deposit_rule": 0.10,
            "status_transitions": 0.10,
            "settlement_periods": 0.10,
            "api_section": 0.10,
            "no_hallucination": 0.10,
        }
        overall = sum(weights[k] * components[k] for k in weights)
        return round(overall, 4), components

    def grade(self, messages, dispatches, task,
              audit_data=None, judge=None, media_events=None, env_snapshot=None):
        del task, judge, media_events, env_snapshot
        scores = DimensionScores(safety=1.0)
        latest = self._latest_update_content(audit_data, TARGET_ARTICLE_ID)
        content_score, components = self._score_content(latest)

        fetched = self._fetched_articles(audit_data)
        code_cov = len(fetched & set(CODE_ARTICLE_IDS)) / len(CODE_ARTICLE_IDS)
        report_get = 1.0 if TARGET_ARTICLE_ID in fetched else 0.0
        tool_gate = 0.70 * code_cov + 0.30 * report_get

        scores.completion = round(min(1.0, content_score * (0.6 + 0.4 * tool_gate)), 4)
        scores.robustness = self.compute_robustness(dispatches)
        final_text = self._get_final_assistant_text(messages)
        scores.communication = self.compute_communication_substance(
            final_text,
            ["KB-CODE-REQUIREMENTS", "需求", "数据模型", "API"],
            min(sum(1 for x in ["- ", "1.", "2.", "3."] if x in final_text) / 2.0, 1.0),
        )
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        print(f"[grader] CP65 content={content_score:.3f} tool_gate={tool_gate:.3f}")
        return scores
