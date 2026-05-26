"""T166_zh_butterfly_curve_animejs_v4_realtime_data grader — A股行情播报 H5 page."""

from __future__ import annotations

import re
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


class MarketBroadcastH5Grader(AbstractGrader):
    """Grade A-share market broadcast H5 page task."""

    # Ground truth: 2026-05-20 SSE Composite Index full intraday data
    # Source: xueqiu.com/S/SH000001, 已收盘 05-20 15:00:00 北京时间
    MARKET_DATA = {
        "close": 4162.18,
        "change": -7.36,
        "change_pct": -0.18,
        "open": 4152.70,
        "high": 4169.85,
        "low": 4139.97,
        "prev_close": 4169.54,
    }
    IS_DOWN = True  # close < prev_close

    ANIMEJS_V4_ANCHORS = [
        [r"animejs@4|anime\.js.*v4|animejs.*4\.\d"],
        [r"createtimeline|createanimation|animate\s*\("],
        [r"stagger|innerHTML.*\d|counter|count"],
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

        data_searched = any(
            re.search(r"上证|sse|shanghai|2026.*5.*20|行情|收盘", q, re.IGNORECASE)
            for q in unique_queries
        )
        animejs_searched = any(
            re.search(r"anime\.?js.*v?4|animejs.*doc|animejs.*api", q, re.IGNORECASE)
            for q in unique_queries
        )
        search_coverage = sum([data_searched, animejs_searched]) / 2.0

        data_score = self._check_market_data(all_text)
        animejs_score = self._check_animejs_v4(all_text)
        mobile_score = self._check_mobile_responsive(all_text)
        page_score = self._check_page_completeness(all_text)

        judged = judge.evaluate(
            task.prompt.text,
            self.format_conversation(messages),
            self.summarize_actions(audit_data),
            task.judge_rubric,
        ).score

        anchor_composite = (
            0.35 * data_score
            + 0.25 * animejs_score
            + 0.20 * mobile_score
            + 0.20 * page_score
        )

        scores.completion = round(
            min(1.0, 0.45 * judged + 0.35 * anchor_composite + 0.20 * search_coverage),
            2,
        )
        scores.robustness = self.compute_robustness(dispatches)
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        return scores

    def _check_market_data(self, text: str) -> float:
        """Check how many of the 7 market data fields are correct."""
        checks = [
            (r"4162\.?18|4,?162\.?18", "close"),
            (r"[-−]?\s*7\.?36|涨跌.*[-−]7", "change"),
            (r"[-−]?\s*0\.?18\s*%|涨跌幅.*[-−]0\.18", "change_pct"),
            (r"4152\.?70|4,?152\.?7", "open"),
            (r"4169\.?85|4,?169\.?85", "high"),
            (r"4139\.?97|4,?139\.?97", "low"),
            (r"1\.?36\s*万亿|13[56]\d{2}\s*亿|成交额.*1[.,]3", "volume"),
        ]

        found = sum(1 for pattern, _ in checks if re.search(pattern, text))
        return found / len(checks)

    def _check_animejs_v4(self, text: str) -> float:
        """Check anime.js v4 usage correctness."""
        score = self._coverage(all_text=text, anchor_groups=self.ANIMEJS_V4_ANCHORS)

        v3_antipattern = bool(re.search(r"anime\s*\(\s*\{[^}]*targets\s*:", text))
        if v3_antipattern:
            score = max(0, score - 0.5)

        return score

    def _check_mobile_responsive(self, text: str) -> float:
        """Check mobile responsiveness."""
        score = 0.0
        if re.search(r"viewport.*width.*device-width|meta.*viewport", text):
            score += 0.4
        if re.search(r"max-width|@media|rem|vw|flex|grid", text):
            score += 0.3
        if re.search(r"#1a1a2e|dark|背景.*#[12]", text):
            score += 0.3
        return min(1.0, score)

    def _check_page_completeness(self, text: str) -> float:
        """Check page completeness and usability."""
        score = 0.0
        if re.search(r"<!doctype|<html", text):
            score += 0.2
        if re.search(r"免责|disclaimer|仅供参考|不构成.*建议", text):
            score += 0.3
        if re.search(r"数据来源|source|来源", text):
            score += 0.2
        if re.search(r"2026.*05.*20|2026\.5\.20|5月20", text):
            score += 0.15
        if re.search(r"收盘播报|行情|a股", text):
            score += 0.15
        return min(1.0, score)

    def _coverage(self, all_text: str, anchor_groups: list[list[str]]) -> float:
        covered = sum(
            1 for group in anchor_groups
            if any(re.search(pat, all_text) for pat in group)
        )
        return covered / len(anchor_groups) if anchor_groups else 0.0
