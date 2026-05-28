"""CP72_gatk_assembly_region_traversal_pipeline grader.

W5 KB-Artifact: code + log + analysis doc all in kb.
"""
from __future__ import annotations

import re
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


TARGET_ARTICLE_ID = "KB-CODE-PIPELINE-ANALYSIS"
CODE_ARTICLE_IDS = [
    "KB-CODE-AssemblyRegionWalker-java",
    "KB-CODE-AssemblyRegionIterator-java",
    "KB-CODE-MultiIntervalLocalReadShard-java",
    "KB-CODE-GATKTool-java",
    "KB-CODE-HaplotypeCallerEngine-java",
]
LOG_ARTICLE_ID = "KB-LOG-GATK-DEBUG"


class GatkAssemblyRegionPipelineGrader(AbstractGrader):
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
            "non_empty", "call_chain", "data_structures",
            "code_references", "padding_question", "downsampling_question",
            "isactive_question", "debug_log_anomalies",
        ]}
        if not content.strip() or len(content) < 500:
            return 0.0, components
        components["non_empty"] = 1.0 if len(content) >= 800 else 0.5
        lower = content.lower()

        chain = ["traverse", "processreadshard", "assemblyregioniterator", "loadnextassemblyregion"]
        h = sum(1 for t in chain if t in lower)
        components["call_chain"] = min(h / 3.0, 1.0)

        structures = ["MultiIntervalLocalReadShard", "AssemblyRegion", "AlignmentContext",
                      "ReadPileup", "PileupElement"]
        h = sum(1 for s in structures if s.lower() in lower)
        components["data_structures"] = min(h / 4.0, 1.0)

        refs = re.findall(r"\w+\.java[:\s]+(?:line\s+)?\d+", content, re.I)
        if len(refs) >= 5:
            components["code_references"] = 1.0
        elif len(refs) >= 3:
            components["code_references"] = 0.7
        elif len(refs) >= 1:
            components["code_references"] = 0.4

        if re.search(r"padding.*(?:contig|boundary)|contig.*padding|(?:min|max)\s*\(.*contig\)", lower):
            components["padding_question"] = 1.0
        elif "padding" in lower and "contig" in lower:
            components["padding_question"] = 0.5

        if re.search(r"downsampl|down-sampl|read\s*downsampl", lower):
            components["downsampling_question"] = 1.0

        h = sum([
            bool(re.search(r"isactive", lower)),
            bool(re.search(r"pileup|read\s*pile\s*up", lower)),
            bool(re.search(r"locus", lower)),
        ])
        components["isactive_question"] = min(h / 2.0, 1.0)

        ah = sum(1 for p in ["anomal", r"310", r"depth.{0,5}0", r"0\s*reads", "bug", "warn", "issue"]
                  if re.search(p, lower))
        if ah >= 3:
            components["debug_log_anomalies"] = 1.0
        elif ah >= 2:
            components["debug_log_anomalies"] = 0.7
        elif ah >= 1:
            components["debug_log_anomalies"] = 0.4

        weights = {
            "non_empty": 0.10,
            "call_chain": 0.15,
            "data_structures": 0.20,
            "code_references": 0.15,
            "padding_question": 0.10,
            "downsampling_question": 0.10,
            "isactive_question": 0.10,
            "debug_log_anomalies": 0.10,
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
        log_get = 1.0 if LOG_ARTICLE_ID in fetched else 0.0
        target_get = 1.0 if TARGET_ARTICLE_ID in fetched else 0.0
        tool_gate = 0.50 * code_cov + 0.25 * log_get + 0.25 * target_get

        scores.completion = round(min(1.0, content_score * (0.6 + 0.4 * tool_gate)), 4)
        scores.robustness = self.compute_robustness(dispatches)
        final_text = self._get_final_assistant_text(messages)
        scores.communication = self.compute_communication_substance(
            final_text,
            ["KB-CODE-PIPELINE", "traverse", "AssemblyRegion"],
            min(sum(1 for x in ["- ", "1.", "2.", "3."] if x in final_text) / 2.0, 1.0),
        )
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        print(f"[grader] CP72 content={content_score:.3f} tool_gate={tool_gate:.3f}")
        return scores
