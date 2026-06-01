"""CP96_mobile_video_operation_page grader.

Hybrid: verify.py for structure checks + LLM Judge for code quality.
"""
from __future__ import annotations

import json
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


VERIFY_CMD_KEY = "cmd:python /workspace/fixtures/verify_video_page.py"

_CODE_QUALITY_RUBRIC = """\
评估 Vue 移动端视频页面代码的实现质量（0.0-1.0）。逐项检查：

1. [+0.30] 自动全屏逻辑：是否正确绑定了 video 的 play 事件并调用 requestFullscreen API？\
事件监听是否在组件生命周期中正确管理（mounted/unmounted）？全屏退出时是否有恢复逻辑？
2. [+0.25] 视频列表渲染：v-for 是否有唯一 key 绑定？是否处理了空列表/加载中/错误状态？\
是否调用了 API 获取数据（不是写死的 mock 数据）？
3. [+0.25] TypeScript 类型安全：是否定义了 VideoItem 接口覆盖视频数据字段？\
是否正确使用了 ref/reactive 的泛型参数？是否有 lang="ts"？
4. [+0.20] 移动端响应式：是否使用了 viewport 相关单位（vw/vh/100%）？\
是否有合理的 flex/grid 布局？是否考虑了触摸交互（touch events）？

严格评分：
- 0.9-1.0: 4项全部高质量实现
- 0.6-0.8: 核心功能正确但有细节缺失
- 0.3-0.5: 基本结构存在但实现有明显错误
- 0.0-0.2: 代码不完整或完全不能工作
"""


class MobileVideoOperationPageGrader(AbstractGrader):
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
            conversation = self.format_conversation_detailed(
                messages,
                include_user_text=True,
                include_assistant_text=True,
                include_tool_use=True,
                include_tool_result=True,
            )
            try:
                result = judge.evaluate(task.prompt.text, conversation, "", _CODE_QUALITY_RUBRIC)
                judge_score = result.score
                print(f"[grader] code_quality judge: {result.score:.2f}")
            except Exception as e:
                print(f"[grader] judge failed: {e}")

        scores.completion = round(min(0.5 * base_score + 0.5 * judge_score, 1.0), 4)
        scores.robustness = self.compute_robustness(dispatches)

        final_text = self._get_final_assistant_text(messages)
        scores.communication = self.compute_communication_substance(
            final_text,
            ["video", "[id].vue", "fullscreen"],
            min(sum(1 for x in ["- ", "1.", "2.", "3."] if x in final_text) / 2.0, 1.0),
        )
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        return scores
