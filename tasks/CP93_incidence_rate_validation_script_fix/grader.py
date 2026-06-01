"""CP90_incidence_rate_validation_script_fix grader.

Hybrid: verify.py for correctness + LLM Judge for analysis depth.
"""
from __future__ import annotations

import json
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


VERIFY_CMD_KEY = "cmd:python /workspace/fixtures/verify_incidence_fix.py"

_ANALYSIS_RUBRIC = """\
评估修复分析的准确性和深度（0.0-1.0）。逐项检查：

1. [+0.30] 根因解释：是否正确解释了 PAD 发病率偏低是因为 ICD-10 编码 I73（其他周围血管疾病）\
缺失导致漏计，只有 I70（动脉粥样硬化）被纳入计算
2. [+0.25] 修复验证：是否说明了添加 I73 后 PAD 发病率应该如何变化（上升），\
以及修复后的数值是否接近参考论文的报告值
3. [+0.25] CVDeath 处理：是否分析了 cardiovascular death 端点的计算逻辑，\
说明了其与 PAD 的关系或独立性
4. [+0.20] 数据对比：是否引用了具体数值（如修复前后的 incidence rate）进行前后对比

严格评分：
- 0.9-1.0: 4项全部满足，分析专业有深度
- 0.6-0.8: 满足3项，核心解释正确
- 0.3-0.5: 只满足1-2项，解释表面
- 0.0-0.2: 只修改了代码但没有任何分析说明
"""


class IncidenceRateValidationFixGrader(AbstractGrader):
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
        base_score = min(max(float(verify.get("overall_score", 0.0)), 0.0), 1.0)

        judge_score = base_score
        if judge:
            conversation = self.format_conversation(messages)
            try:
                result = judge.evaluate(task.prompt.text, conversation, "", _ANALYSIS_RUBRIC)
                judge_score = result.score
                print(f"[grader] analysis_depth judge: {result.score:.2f}")
            except Exception as e:
                print(f"[grader] judge failed: {e}")

        scores.completion = round(min(0.5 * base_score + 0.5 * judge_score, 1.0), 4)
        scores.robustness = self.compute_robustness(dispatches)

        final_text = self._get_final_assistant_text(messages)
        scores.communication = self.compute_communication_substance(
            final_text,
            ["validate_incidence_rate.py", "PAD", "I73", "incidence_rate_comparison.csv"],
            min(sum(1 for x in ["- ", "1.", "2.", "3."] if x in final_text) / 2.0, 1.0),
        )
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        return scores
