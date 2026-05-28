"""CP64_spring_boot_project_management_code_review grader.

W5 KB-Artifact: code + report all in kb. Score from audit_data['kb'].
"""
from __future__ import annotations

import re
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


TARGET_ARTICLE_ID = "KB-CODE-REVIEW-REPORT"
PRINCIPLES_ARTICLE_ID = "KB-CODE-REVIEW-PRINCIPLES"
CODE_ARTICLE_IDS = [
    "KB-CODE-Project-java",
    "KB-CODE-ProjectDao-java",
    "KB-CODE-ProjectController-java",
    "KB-CODE-ProjectService-java",
]


class SpringBootCodeReviewGrader(AbstractGrader):
    @staticmethod
    def _latest_update_content(audit_data, article_id: str) -> str:
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
    def _fetched_articles(audit_data) -> set[str]:
        if not audit_data:
            return set()
        kb = audit_data.get("kb") or {}
        calls = kb.get("calls") if isinstance(kb, dict) else None
        if not calls:
            return set()
        out = set()
        for e in calls:
            if e.get("endpoint") == "/kb/articles/get":
                aid = (e.get("request_body") or {}).get("article_id")
                if aid:
                    out.add(aid)
        return out

    @staticmethod
    def _score_content(content: str) -> tuple[float, dict]:
        components = {k: 0.0 for k in [
            "non_empty", "sql_injection", "n_plus_one", "thread_safety",
            "hardcoded_secret", "missing_validation", "missing_auth",
            "severity_classification", "file_path_evidence",
        ]}
        if not content.strip():
            return 0.0, components
        lower = content.lower()

        components["non_empty"] = 1.0 if len(content.strip()) >= 600 else 0.4

        sql_kw = ["sql injection", "sql注入", "$", "拼接", "注入风险", "parameterized", "参数化", "#{"]
        h = sum(1 for kw in sql_kw if kw in lower)
        components["sql_injection"] = 1.0 if h >= 2 else (0.5 if h >= 1 else 0.0)

        n1_kw = ["n+1", "n plus 1", "循环查询", "loop query", "getstats",
                 "countasks", "countmembers", "批量查询"]
        h = sum(1 for kw in n1_kw if kw in lower)
        components["n_plus_one"] = 1.0 if h >= 2 else (0.5 if h >= 1 else 0.0)

        thread_kw = ["simpledateformat", "线程安全", "thread-safe", "threadsafe",
                     "threadlocal", "线程不安全", "并发"]
        h = sum(1 for kw in thread_kw if kw in lower)
        components["thread_safety"] = 1.0 if h >= 2 else (0.5 if h >= 1 else 0.0)

        secret_kw = ["hardcoded", "硬编码", "密钥", "secret", "aes256",
                     "generateexporttoken", "明文密钥", "明文"]
        h = sum(1 for kw in secret_kw if kw in lower)
        components["hardcoded_secret"] = 1.0 if h >= 2 else (0.5 if h >= 1 else 0.0)

        val_kw = ["validation", "校验", "入参校验", "@valid", "参数验证", "空值检查", "空指针"]
        h = sum(1 for kw in val_kw if kw in lower)
        components["missing_validation"] = 1.0 if h >= 2 else (0.5 if h >= 1 else 0.0)

        auth_kw = ["权限", "鉴权", "authorization", "未鉴权", "delete",
                   "权限控制", "认证", "auth missing"]
        h = sum(1 for kw in auth_kw if kw in lower)
        components["missing_auth"] = 1.0 if h >= 2 else (0.5 if h >= 1 else 0.0)

        sev_terms = ["严重", "高风险", "中等", "建议", "critical", "high", "medium", "low"]
        h = sum(1 for t in sev_terms if t in lower)
        components["severity_classification"] = min(1.0, h / 3)

        evidence = sum(1 for f in ["projectcontroller", "projectservice", "projectdao", "project-java"] if f in lower)
        components["file_path_evidence"] = min(evidence / 3.0, 1.0)

        weights = {
            "non_empty": 0.05,
            "sql_injection": 0.15,
            "n_plus_one": 0.15,
            "thread_safety": 0.10,
            "hardcoded_secret": 0.15,
            "missing_validation": 0.10,
            "missing_auth": 0.15,
            "severity_classification": 0.10,
            "file_path_evidence": 0.05,
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
        code_cov = len(fetched & set(CODE_ARTICLE_IDS)) / len(CODE_ARTICLE_IDS)
        report_get = 1.0 if TARGET_ARTICLE_ID in fetched else 0.0
        prin_get = 1.0 if PRINCIPLES_ARTICLE_ID in fetched else 0.0
        tool_gate = 0.50 * code_cov + 0.25 * report_get + 0.25 * prin_get

        scores.completion = round(min(1.0, content_score * (0.6 + 0.4 * tool_gate)), 4)
        scores.robustness = self.compute_robustness(dispatches)
        final_text = self._get_final_assistant_text(messages)
        scores.communication = self.compute_communication_substance(
            final_text,
            ["KB-CODE-REVIEW", "严重", "高风险", "SQL"],
            min(sum(1 for x in ["- ", "1.", "2.", "3."] if x in final_text) / 2.0, 1.0),
        )
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        print(f"[grader] CP64 content={content_score:.3f} tool_gate={tool_gate:.3f} code_cov={code_cov:.2f}")
        return scores
