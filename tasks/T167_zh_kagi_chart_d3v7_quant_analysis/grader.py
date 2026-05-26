"""T167_zh_kagi_chart_d3v7_quant_analysis grader — Kagi chart with D3.js v7 + multi-day data."""

from __future__ import annotations

import re
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


class KagiChartD3Grader(AbstractGrader):
    """Grade Kagi chart technical analysis tool with trend judgment."""

    # Ground truth: SSE Composite 5-day closing prices (2026-05-14 to 2026-05-20)
    # Sources: Yahoo Finance HK (000001.SS), Sohu Finance, Xueqiu
    CLOSE_PRICES = {
        "2026-05-14": 4177.92,
        "2026-05-15": 4135.39,
        "2026-05-18": 4131.53,
        "2026-05-19": 4169.54,
        "2026-05-20": 4162.18,
    }
    PRICE_MAX = 4177.92  # 05-14
    PRICE_MIN = 4131.53  # 05-18
    PRICE_RANGE = PRICE_MAX - PRICE_MIN  # 46.39
    EXPECTED_REVERSAL = PRICE_RANGE * 0.5  # 23.20

    # Kagi analysis ground truth:
    # 4177.92→4135.39: drop 42.53 > 23.20 → reversal to 阴线
    # 4135.39→4131.53: drop 3.86 < 23.20 → extend 阴线
    # 4131.53→4169.54: rise 38.01 > 23.20 → reversal to 阳线
    # 4169.54→4162.18: drop 7.36 < 23.20 → no reversal
    # Current state: 阳线 (bullish), last reversal 05-18→05-19
    CURRENT_TREND = "yang"  # bullish / 阳线
    REVERSAL_POINT = 4146.34  # 4169.54 - 23.20

    D3V7_ANCHORS = [
        [r"d3@7|d3\.js.*v7|d3-selection|\"d3\""],
        [r"d3\.select|d3\.scalelinear|d3\.line"],
        [r"<svg|createsvg|appendchild"],
    ]

    KAGI_ALGORITHM_ANCHORS = [
        [r"reversal|反转|threshold|阈值"],
        [r"kagi|カギ"],
        [r"阳线|阴线|yang|yin|上升.*趋势|下降.*趋势|bullish|bearish"],
    ]

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
        scores = DimensionScores()
        scores.safety = 1.0

        all_text = self._get_all_assistant_text(messages).lower()

        search_calls = [
            d for d in dispatches
            if d.tool_name == "web_search" and d.response_status < 400
        ]
        unique_queries = {d.request_body.get("query", "") for d in search_calls}

        kagi_searched = any(
            re.search(r"kagi.*chart|kagi.*algorithm|カギ足|kagi.*rule", q, re.IGNORECASE)
            for q in unique_queries
        )
        data_searched = any(
            re.search(r"上证.*历史|sse.*histor|000001.*history|5月.*收盘", q, re.IGNORECASE)
            for q in unique_queries
        )
        d3_searched = any(
            re.search(r"d3.*v7|d3\.js.*7|d3.*migration|d3.*event", q, re.IGNORECASE)
            for q in unique_queries
        )

        search_coverage = sum([kagi_searched, data_searched, d3_searched]) / 3.0

        kagi_score = self._coverage(all_text, self.KAGI_ALGORITHM_ANCHORS)
        d3_score = self._coverage(all_text, self.D3V7_ANCHORS)
        data_score = self._check_historical_data(all_text)
        reversal_score = self._check_reversal_threshold(all_text)
        trend_score = self._check_trend_analysis(all_text)

        # D3 v7 anti-pattern: using d3.event (removed in v7)
        d3_event_antipattern = bool(re.search(r"d3\.event", all_text))
        d3_penalty = 0.3 if d3_event_antipattern else 0.0

        # Kagi anti-pattern: equal-spaced X axis with all 5 data points
        equal_x = bool(re.search(r"xscale\s*=.*d3\.scalelinear.*domain.*\[0.*4\]", all_text))

        html_present = 1.0 if re.search(r"<!doctype|<html", all_text) else 0.0
        has_svg = 1.0 if re.search(r"<svg|createelement.*svg|d3.*append.*svg", all_text) else 0.0

        judged = judge.evaluate(
            task.prompt.text,
            self.format_conversation(messages),
            self.summarize_actions(audit_data),
            task.judge_rubric,
        ).score

        anchor_composite = (
            0.25 * kagi_score
            + 0.25 * data_score
            + 0.15 * reversal_score
            + 0.20 * trend_score
            + 0.10 * max(0, d3_score - d3_penalty)
            + 0.05 * html_present
        )

        scores.completion = round(
            min(1.0, 0.45 * judged + 0.35 * anchor_composite + 0.20 * search_coverage),
            2,
        )
        scores.robustness = self.compute_robustness(dispatches)
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        return scores

    def _check_historical_data(self, text: str) -> float:
        """Check how many of the 5 correct closing prices appear in output."""
        found = 0
        for date, price in self.CLOSE_PRICES.items():
            price_str = f"{price:.2f}"
            price_patterns = [
                re.escape(price_str),
                re.escape(price_str.replace(".", r"\.?")),
                re.escape(f"{price}"),
            ]
            if any(re.search(pat, text) for pat in price_patterns):
                found += 1
            elif re.search(re.escape(str(int(price))), text):
                found += 0.5

        return min(1.0, found / 5.0)

    def _check_reversal_threshold(self, text: str) -> float:
        """Check reversal threshold calculation (expected ≈ 23.20)."""
        threshold_match = re.findall(
            r"(?:reversal|反转|阈值|threshold)\s*[=:≈]\s*(\d+\.?\d*)", text
        )
        if not threshold_match:
            threshold_match = re.findall(r"23\.?\d{0,2}", text)

        for match in threshold_match:
            try:
                val = float(match)
                if abs(val - self.EXPECTED_REVERSAL) < 2.0:
                    return 1.0
                if abs(val - self.EXPECTED_REVERSAL) < 5.0:
                    return 0.5
            except ValueError:
                continue

        range_mentioned = bool(re.search(r"46\.?3|46\.?4", text))
        if range_mentioned:
            return 0.3

        return 0.0

    def _check_trend_analysis(self, text: str) -> float:
        """Check trend analysis panel output (the core value deliverable)."""
        score = 0.0

        # Current trend direction: should be 阳线/bullish/上升
        if re.search(r"当前.*阳|current.*yang|bullish|上升趋势|看多", text):
            score += 0.35
        elif re.search(r"阳线|yang|上升", text):
            score += 0.2

        # Last reversal identification: 05-18→05-19, 阴→阳
        if re.search(r"05.?1[89].*反转|反转.*05.?1[89]|阴.*转.*阳|bearish.*bullish", text):
            score += 0.25

        # Distance to next reversal: ~15.84 points or reversal at ~4146
        if re.search(r"414[56]|15\.?8|距离.*反转.*\d{1,2}", text):
            score += 0.2

        # Has any actionable conclusion
        if re.search(r"建议|操作|看多|看空|震荡|关注|注意", text):
            score += 0.2

        return min(1.0, score)

    def _coverage(self, text: str, anchor_groups: list[list[str]]) -> float:
        covered = sum(
            1 for group in anchor_groups
            if any(re.search(pat, text) for pat in group)
        )
        return covered / len(anchor_groups) if anchor_groups else 0.0
