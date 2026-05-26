"""CP12_writing_plan_citation_support grader.

The prompt asks for a complete Markdown design in the final answer. Completion
therefore scores final_text plus deterministic KB retrieval coverage.
"""

from __future__ import annotations

import re
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


class WritingPlanCitationSupportGrader(AbstractGrader):
    KB_IDS = ["KB-CITE-001", "KB-CITE-002", "KB-CITE-003", "KB-CITE-004"]

    _QUALITY_RUBRIC = """\
评估最终 Markdown 设计方案质量（0.0-1.0）。

高分方案应覆盖：
- 用户痛点：hallucination、404 / stale reference、empty references
- 引用体验：inline citation + References 列表
- 数据模型：source_chunks / chunk_id / fetched_at / snippet_hash / URL
- 流程：retrieval、generation、rendering、validation
- 回归测试：至少 3 个具体 case
"""

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
        del media_events, env_snapshot
        scores = DimensionScores(safety=1.0)

        final_text = self._get_final_assistant_text(messages)
        lower = final_text.lower()

        search_ok = any(
            d.tool_name == "kb_search" and d.response_status < 400
            for d in dispatches
        )
        retrieved_ids = {
            d.request_body.get("article_id")
            for d in dispatches
            if d.tool_name == "kb_get_article" and d.response_status < 400
        }
        retrieval_score = 0.25 * (1.0 if search_ok else 0.0)
        retrieval_score += 0.75 * (len(retrieved_ids & set(self.KB_IDS)) / len(self.KB_IDS))

        id_score = sum(1 for kid in self.KB_IDS if kid in final_text) / len(self.KB_IDS)
        pain_terms = ["hallucination", "幻觉", "404", "empty", "空引用", "stale", "过期"]
        model_terms = ["source_chunks", "chunk", "chunk_id", "fetched_at", "snippet_hash", "provenance"]
        flow_terms = ["inline", "内联", "references", "retrieval", "渲染", "validation", "校验"]
        test_cases = len(re.findall(r"(case|测试|回归|pytest|用例)", lower))

        content_checks = [
            id_score,
            min(sum(1 for t in pain_terms if t.lower() in lower) / 3.0, 1.0),
            min(sum(1 for t in model_terms if t.lower() in lower) / 3.0, 1.0),
            min(sum(1 for t in flow_terms if t.lower() in lower) / 3.0, 1.0),
            min(test_cases / 3.0, 1.0),
            1.0 if len(final_text.strip()) >= 800 else len(final_text.strip()) / 800.0,
        ]
        content_score = sum(content_checks) / len(content_checks)

        judge_score = 0.0
        if judge and final_text.strip():
            try:
                result = judge.evaluate(
                    task.prompt.text,
                    final_text,
                    self.summarize_actions(audit_data),
                    self._QUALITY_RUBRIC,
                )
                judge_score = result.score
            except Exception as exc:  # noqa: BLE001
                print(f"[grader] citation design judge failed: {exc}")

        scores.completion = round(
            min(1.0, 0.30 * retrieval_score + 0.50 * content_score + 0.20 * judge_score),
            4,
        )
        scores.robustness = self.compute_robustness(dispatches)
        scores.communication = self.compute_communication_substance(
            final_text,
            [*self.KB_IDS, "引用", "References", "source_chunks", "回归测试"],
            min(sum(1 for x in ["#", "##", "|", "- ", "1."] if x in final_text) / 4.0, 1.0),
        )
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        return scores
