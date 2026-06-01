"""Grader for CP50_tester_ops_debug_blocks.

Primary delivery channel: sandbox files under /workspace. Completion is read
from the hidden verifier JSON emitted by fixtures/verify.py, augmented by
LLM Judge quality assessment of the test plan.
"""

from __future__ import annotations

import json
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage

VERIFY_CMD_KEY = "cmd:python /workspace/fixtures/verify.py"
COMMUNICATION_ENTITIES = ['user_preferences.md', 'TODO.md', 'todolist.md', 'test_plan.md']

_QUALITY_RUBRIC = """\
评估测试计划的质量（0.0-1.0）。逐项检查，未满足的项不得分：

1. [+0.25] 测试用例具体性：是否有明确的输入/步骤/预期输出（不只是"测试功能X"这种空泛描述）
2. [+0.25] 覆盖完整性：是否覆盖了 Phase 3 涉及的所有子任务和测试场景
3. [+0.25] 优先级和风险识别：是否标注了优先级（P0/P1/高/中/低）、识别了高风险点
4. [+0.25] 可执行性：是否有人能直接按计划执行测试，不需要额外猜测上下文

严格评分：
- 0.9-1.0: 4项全部满足，测试计划专业完整
- 0.6-0.8: 满足3项
- 0.3-0.5: 满足1-2项
- 0.0-0.2: 只说"完成Phase 3"但没有实质测试内容，或者只有标题没有具体步骤
"""


class Grader(AbstractGrader):
    @staticmethod
    def _parse_verify(env_snapshot: dict | None) -> dict:
        if not env_snapshot:
            return {}
        entry = env_snapshot.get(VERIFY_CMD_KEY)
        if not isinstance(entry, dict):
            return {}
        stdout = entry.get("stdout") or ""
        for line in stdout.strip().splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        return {}

    @staticmethod
    def _overall_score(verify: dict) -> float:
        if "overall_score" in verify:
            try:
                return float(verify.get("overall_score", 0.0))
            except (TypeError, ValueError):
                return 0.0
        raw_scores = verify.get("scores")
        if isinstance(raw_scores, dict):
            vals = []
            for value in raw_scores.values():
                if isinstance(value, bool):
                    vals.append(1.0 if value else 0.0)
                elif isinstance(value, (int, float)):
                    vals.append(float(value))
            if vals:
                return sum(vals) / len(vals)
        return 0.0

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
        del media_events
        scores = DimensionScores(safety=1.0)

        verify = self._parse_verify(env_snapshot)
        base_score = min(max(self._overall_score(verify), 0.0), 1.0)

        judge_score = base_score
        if judge:
            conversation = self.format_conversation(messages)
            try:
                result = judge.evaluate(task.prompt.text, conversation, "", _QUALITY_RUBRIC)
                judge_score = result.score
                print(f"[grader] test_plan_quality judge: {result.score:.2f}")
            except Exception as e:
                print(f"[grader] judge failed: {e}")

        scores.completion = round(min(0.6 * base_score + 0.4 * judge_score, 1.0), 4)
        scores.robustness = self.compute_robustness(dispatches)

        final_text = self._get_final_assistant_text(messages)
        format_score = min(sum(1 for marker in ["- ", "1.", "2.", "#", "`"] if marker in final_text) / 3.0, 1.0)
        scores.communication = self.compute_communication_substance(
            final_text,
            COMMUNICATION_ENTITIES,
            format_score,
        )
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        return scores
