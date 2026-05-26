"""CP18_fund_trading_logic_audit grader — Pattern D + local_grader_files.

Source: Themis taskset-260421-225115-strict-v2:task_36_superpowers_skill_verify.

Agent audits fund_trader.py (with 5 intentional bugs) and produces markdown
report. local_grader_files contains the bug reference (not visible to agent).
"""

from __future__ import annotations

from claw_eval.graders.pinbench_common import PinbenchAdaptedGrader


class FundTradingLogicAuditGrader(PinbenchAdaptedGrader):

    REQUIRED_TOOLS = {}

    REQUIRED_KEYWORDS = [
        # Core bug anchor phrases (any reasonable rendering counts)
        "subscribe",      # cash check bug location
        "redeem",         # T+1 + fee-tier bug location
        "avg_cost",       # weighted average bug
        "T+1",            # T+1 violation
        # Severity tagging
        "CRITICAL",
    ]

    OPTIONAL_KEYWORDS = [
        # Bug specifics (rewarded if mentioned)
        "现金不足", "insufficient", "InsufficientFunds",
        "加权平均", "weighted average",
        "套利", "日内套利", "T+1 violation",
        "手续费", "fee_rate", "费率",
        "阶梯写反", "tier reversed", "反向", "颠倒",
        "last_buy_date",
        "KeyError", "cash 字典",
        # Severity tags
        "HIGH", "MEDIUM", "LOW",
        # Test recommendation
        "pytest",
        "测试用例",
    ]

    REQUIRED_PATTERNS = [
        r"^#+\s+",                # markdown headings
        r"^\d+\.\s|^[-*]\s",      # numbered or bullet lists
    ]

    MIN_FINAL_LENGTH = 800
