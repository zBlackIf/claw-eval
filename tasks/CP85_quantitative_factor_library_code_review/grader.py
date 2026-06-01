"""CP74_quantitative_factor_library_code_review grader.

Workflow W5 (kb-artifact): grader pulls latest KB-CODE-REVIEW-REPORT content
from audit_data['kb'] and runs 6 hidden anchors + a tool gate factor for
whether agent consulted the review principles article.
"""
from __future__ import annotations

import re
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


TARGET_ARTICLE_ID = "KB-CODE-REVIEW-REPORT"
PRINCIPLES_ARTICLE_ID = "KB-CODE-REVIEW-PRINCIPLES"


class QuantFactorCodeReviewGrader(AbstractGrader):
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
            "non_empty", "look_ahead_bias", "divide_by_zero",
            "performance_issue", "severity_ratings", "no_false_clean",
            "file_path_evidence",
        ]}
        if not content.strip():
            return 0.0, components
        lower = content.lower()

        components["non_empty"] = 1.0 if len(content.strip()) >= 600 else 0.4

        la_terms = ["look-ahead", "lookahead", "look ahead", "future", "leakage",
                    "shift(-", "forward-looking", "未来信息", "泄漏"]
        mom_terms = ["momentum", "reversal", "skip_recent"]
        la_hits = sum(1 for t in la_terms if t in lower)
        mom_hits = sum(1 for t in mom_terms if t in lower)
        if la_hits >= 1 and mom_hits >= 1:
            components["look_ahead_bias"] = 1.0
        elif la_hits >= 1:
            components["look_ahead_bias"] = 0.5

        div_terms = ["division", "zero", "divid", "nan", "inf", "除零"]
        val_terms = ["value", "book_to_market", "earnings_yield", "market_cap", "value.py"]
        dz_hits = sum(1 for t in div_terms if t in lower)
        val_hits = sum(1 for t in val_terms if t in lower)
        if dz_hits >= 1 and val_hits >= 1:
            components["divide_by_zero"] = 1.0
        elif dz_hits >= 1:
            components["divide_by_zero"] = 0.5

        perf_terms = ["iterrows", "loop", "vectori", "slow", "performance", "apply", "性能"]
        eng_terms = ["feature_engine", "build_training", "training_set", "pipeline"]
        p_hits = sum(1 for t in perf_terms if t in lower)
        e_hits = sum(1 for t in eng_terms if t in lower)
        if p_hits >= 1 and e_hits >= 1:
            components["performance_issue"] = 1.0
        elif p_hits >= 1:
            components["performance_issue"] = 0.5

        severity_matches = re.findall(r"\bP[0-3]\b", content)
        components["severity_ratings"] = min(len(severity_matches) / 3.0, 1.0)

        false_clean = ["no issues", "code is clean", "no problems found",
                       "looks good overall", "未发现问题", "代码无问题"]
        if any(p in lower for p in false_clean) and not any(
            k in lower for k in ["bug", "issue", "risk", "problem", "concern",
                                 "warning", "风险", "问题"]
        ):
            components["no_false_clean"] = 0.0
        else:
            components["no_false_clean"] = 1.0

        path_evidence = sum(1 for f in ["momentum.py", "value.py", "volatility.py",
                                         "feature_engine.py", "test_factors.py"] if f in lower)
        components["file_path_evidence"] = min(path_evidence / 3.0, 1.0)

        weights = {
            "non_empty": 0.05,
            "look_ahead_bias": 0.25,
            "divide_by_zero": 0.15,
            "performance_issue": 0.15,
            "severity_ratings": 0.15,
            "no_false_clean": 0.10,
            "file_path_evidence": 0.15,
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
        if PRINCIPLES_ARTICLE_ID in fetched:
            tool_bonus += 0.5
        tool_factor = 0.85 + 0.15 * tool_bonus

        scores.completion = round(min(1.0, content_score * tool_factor), 4)
        scores.robustness = self.compute_robustness(dispatches)
        final_text = self._get_final_assistant_text(messages)
        scores.communication = self.compute_communication_substance(
            final_text,
            ["KB-CODE-REVIEW", "P0", "look-ahead", "factors"],
            min(sum(1 for x in ["- ", "1.", "2.", "3."] if x in final_text) / 2.0, 1.0),
        )
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        print(f"[grader] CP74 content={content_score:.3f} tool_factor={tool_factor:.3f} comp={components}")
        return scores
