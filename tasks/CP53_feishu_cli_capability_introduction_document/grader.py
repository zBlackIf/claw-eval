"""CP53_feishu_cli_capability_introduction_document grader.

Deliverable is /workspace/lark-cli-intro.md. Scoring blends:
- file presence + length
- real-skill name coverage (must mention 4 actual skill names from fixtures)
- hallucination penalty (deduct for invented skill names)
- structural anchors (intro + per-skill sections + priority block + 后续)
- LLM judge over the full document for writing quality
"""

from __future__ import annotations

import re
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


DOC_FILE_KEY = "file:/workspace/lark-cli-intro.md"

REAL_SKILLS = ["lark-doc", "lark-im", "lark-calendar", "lark-task"]
HALLUCINATED_SKILLS = [
    "lark-travel", "lark-crm", "lark-sales", "lark-helpdesk",
    "lark-meeting", "lark-ai", "lark-translate", "lark-form",
    "lark-okr", "lark-bitable",
]
PRIORITY_PHRASES = [r"先用", r"优先", r"推荐", r"重点", r"建议先"]
FOLLOWUP_PHRASES = [r"后续", r"接下来", r"之后", r"剩下", r"其余"]


class FeishuCliCapabilityDocGrader(AbstractGrader):
    _JUDGE_RUBRIC = """\
评估这份飞书 CLI 能力介绍文档的实用价值（0.0-1.0）。

高分文档应该：
- 真的像参考手册，不是占位/敷衍内容
- 每个 skill 一节，说明能做什么 + 至少一个具体命令示例
- 有针对用户工作场景（客户现场 / 出差 / 写方案 / 跨部门）的优先推荐
- 命令示例真实可跑（与 SKILL.md '主要命令' 一致）
- 不发明 SKILL.md 之外的 skill 名或命令名

不应：
- 写成 "测试文档" 一句话占位
- 把所有 skill 当 commodity 列一遍，不区分场景
- 编造 SKILL.md 中没出现的 skill 或命令
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
        del task, audit_data, media_events
        scores = DimensionScores(safety=1.0)
        doc_content = ""
        if env_snapshot:
            entry = env_snapshot.get(DOC_FILE_KEY)
            if isinstance(entry, dict):
                doc_content = entry.get("content") or ""

        if not doc_content.strip():
            scores.completion = 0.0
            scores.robustness = self.compute_robustness(dispatches)
            scores.communication = 0.0
            return scores

        lower = doc_content.lower()
        char_count = len(doc_content.strip())

        # 1. Length signal: target 600-2500 chars; penalize stub-like (<200)
        if char_count < 200:
            length_score = 0.0
        elif char_count < 400:
            length_score = 0.4
        elif char_count < 700:
            length_score = 0.7
        else:
            length_score = 1.0

        # 2. Real skill coverage (each of 4 skills mentioned)
        real_hits = sum(1 for s in REAL_SKILLS if s in lower)
        real_score = real_hits / len(REAL_SKILLS)

        # 3. Hallucination penalty
        hallucinated = [s for s in HALLUCINATED_SKILLS if s in lower]
        hallucination_penalty = min(len(hallucinated) * 0.20, 0.6)

        # 4. Structural anchors
        section_count = len(re.findall(r"^#+\s+|^##\s+", doc_content, re.M))
        sections_score = min(section_count / 5.0, 1.0)
        has_priority = any(re.search(p, doc_content) for p in PRIORITY_PHRASES)
        has_followup = any(re.search(p, doc_content) for p in FOLLOWUP_PHRASES)
        structure_score = 0.4 * sections_score + 0.3 * (1.0 if has_priority else 0.0) + 0.3 * (1.0 if has_followup else 0.0)

        # 5. Command example signal (at least 2 inline code blocks containing skill prefix or +shortcut)
        code_blocks = re.findall(r"`([^`\n]+)`", doc_content)
        cmd_blocks = [b for b in code_blocks if re.search(r"\+\w+|lark-cli\s|docs\s|im\s|calendar\s|task\s", b)]
        cmd_score = min(len(cmd_blocks) / 4.0, 1.0)

        # 6. LLM judge
        judge_score = 0.0
        if judge:
            try:
                result = judge.evaluate(
                    self._JUDGE_RUBRIC,
                    doc_content,
                    "",
                    self._JUDGE_RUBRIC,
                )
                judge_score = result.score
            except Exception as exc:  # noqa: BLE001
                print(f"[grader] feishu cli doc judge failed: {exc}")

        completion = (
            0.15 * length_score
            + 0.25 * real_score
            + 0.15 * structure_score
            + 0.15 * cmd_score
            + 0.30 * judge_score
        ) - hallucination_penalty
        completion = max(0.0, min(completion, 1.0))
        scores.completion = round(completion, 4)
        scores.robustness = self.compute_robustness(dispatches)

        final_text = self._get_final_assistant_text(messages)
        scores.communication = self.compute_communication_substance(
            final_text,
            ["lark-cli-intro.md", "覆盖", "推荐", "skill"],
            min(sum(1 for x in ["- ", "1.", "2.", "3."] if x in final_text) / 2.0, 1.0),
        )
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        return scores
