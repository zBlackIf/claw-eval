"""T_CP12_writing_plan_citation_support grader — Pattern D.

Source: Themis taskset-260427-121234:task_75_writing_plan_citation.

Agent reads KB articles about citation and produces a markdown design plan.
"""

from __future__ import annotations

from claw_eval.graders.pinbench_common import PinbenchAdaptedGrader


class WritingPlanCitationSupportGrader(PinbenchAdaptedGrader):

    REQUIRED_TOOLS = {
        "kb_search": 1,
        "kb_get_article": 2,
    }

    REQUIRED_KEYWORDS = [
        # Must reference all 4 KB anchor IDs to prove genuine reading
        "KB-CITE-001",
        "KB-CITE-002",
        "KB-CITE-003",
        "KB-CITE-004",
        # Concept anchors
        "引用",
        "References",
    ]

    OPTIONAL_KEYWORDS = [
        "内联", "inline",
        "超链接",
        "provenance",
        "source_chunks",
        "hallucination",
        "404",
        "fetched_at",
        "snippet_hash",
        "回归", "测试",
        "retrieval",
        "渲染",
    ]

    REQUIRED_PATTERNS = [
        r"^#+\s+|^\d+\.\s|^[-*]\s",
    ]

    MIN_FINAL_LENGTH = 600
