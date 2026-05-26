"""CP18_fund_trading_logic_audit grader.

Scores the final audit report against hidden bug anchors. The hidden
bugs_reference.md remains unavailable to the agent and is used only by grader.
"""

from __future__ import annotations

from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


class FundTradingLogicAuditGrader(AbstractGrader):
    CORE_BUGS = [
        ("cash_check", ["现金不足", "insufficient", "cash", "subscribe"]),
        ("avg_cost", ["avg_cost", "加权平均", "weighted average"]),
        ("t_plus_one", ["t+1", "日内", "套利", "last_buy_date"]),
        ("fee_tier", ["手续费", "fee_rate", "阶梯", "tier", "反"]),
    ]
    BONUS_BUG = ["keyerror", "cash 字典", "self.cash[user_id]", "get(user_id"]

    _AUDIT_RUBRIC = """\
评估最终基金交易逻辑审计报告质量（0.0-1.0）。

高分报告应：
- 准确识别 4 个核心 bug：申购现金校验、加权平均成本、T+1、赎回费率阶梯
- 每个问题有位置、当前行为、期望行为、业务/监管影响、修复思路
- 给出测试建议，不编造代码里不存在的问题
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
        del audit_data, media_events, env_snapshot
        scores = DimensionScores(safety=1.0)
        final_text = self._get_final_assistant_text(messages)
        lower = final_text.lower()

        core_score = 0.0
        for _, terms in self.CORE_BUGS:
            if any(t.lower() in lower for t in terms):
                core_score += 1.0
        core_score /= len(self.CORE_BUGS)

        bonus_score = 1.0 if any(t.lower() in lower for t in self.BONUS_BUG) else 0.0
        detail_terms = ["位置", "line", "影响", "修复", "raise", "pytest", "测试"]
        detail_score = min(sum(1 for t in detail_terms if t.lower() in lower) / 5.0, 1.0)
        severity_score = min(sum(1 for t in ["critical", "high", "严重", "高危"] if t in lower) / 2.0, 1.0)

        judge_score = 0.0
        if judge and final_text.strip():
            try:
                result = judge.evaluate(task.prompt.text, final_text, "", self._AUDIT_RUBRIC)
                judge_score = result.score
            except Exception as exc:  # noqa: BLE001
                print(f"[grader] fund audit judge failed: {exc}")

        completion = (
            0.55 * core_score
            + 0.10 * bonus_score
            + 0.15 * detail_score
            + 0.05 * severity_score
            + 0.15 * judge_score
        )
        if len(final_text.strip()) < 500:
            completion = min(completion, 0.50)
        scores.completion = round(min(completion, 1.0), 4)
        scores.robustness = self.compute_robustness(dispatches)
        scores.communication = self.compute_communication_substance(
            final_text,
            ["subscribe", "redeem", "avg_cost", "T+1", "fee_rate", "修复"],
            min(sum(1 for x in ["#", "|", "- ", "1.", "2."] if x in final_text) / 4.0, 1.0),
        )
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        return scores
