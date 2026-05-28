"""CP52_enterprise_bulk_info_query_csv_export grader.

Deliverable is /workspace/enterprise_info.csv. Scoring blends structural CSV
quality (header, row count, credit-code format, non-placeholder ratio) with
search-behavior evidence (the agent must actually use web_search/web_fetch
rather than fabricate from memory).
"""

from __future__ import annotations

import csv
import io
import re
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


REQUIRED_HEADER = ["企业名称", "统一社会信用代码", "法定代表人", "注册资本", "成立日期", "经营状态"]
CSV_FILE_KEY = "file:/workspace/enterprise_info.csv"

# Chinese unified social credit code: 18 chars, [0-9A-HJ-NPQRTUWXY], first char usually 9 (enterprise)
CREDIT_CODE_RE = re.compile(r"^[0-9A-HJ-NPQRTUWXY]{18}$")
PLACEHOLDER_TOKENS = {"未查到", "未知", "待查", "待补充", "-", "—", "n/a", "null", "无", "查询失败"}


class EnterpriseBulkInfoQueryGrader(AbstractGrader):
    @staticmethod
    def _read_csv(env_snapshot: dict | None) -> tuple[list[str], list[list[str]], str]:
        """Return (header, rows, raw_text). Empty tuple on failure."""
        if not env_snapshot:
            return [], [], ""
        entry = env_snapshot.get(CSV_FILE_KEY)
        if not isinstance(entry, dict):
            return [], [], ""
        content = entry.get("content") or ""
        if not content.strip():
            return [], [], ""
        try:
            reader = csv.reader(io.StringIO(content))
            rows = list(reader)
            if not rows:
                return [], [], content
            return rows[0], rows[1:], content
        except csv.Error:
            return [], [], content

    @staticmethod
    def _placeholder_ratio(rows: list[list[str]]) -> float:
        if not rows:
            return 1.0
        total_cells = 0
        placeholder_cells = 0
        for row in rows:
            for cell in row:
                cell_stripped = cell.strip().lower()
                if not cell_stripped:
                    continue
                total_cells += 1
                if cell_stripped in PLACEHOLDER_TOKENS:
                    placeholder_cells += 1
        if total_cells == 0:
            return 1.0
        return placeholder_cells / total_cells

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
        del task, audit_data, judge, media_events
        scores = DimensionScores(safety=1.0)

        header, rows, _ = self._read_csv(env_snapshot)
        if not header and not rows:
            scores.completion = 0.0
            scores.robustness = self.compute_robustness(dispatches)
            scores.communication = 0.0
            return scores

        # 1. Header coverage (six required columns)
        header_hits = sum(1 for col in REQUIRED_HEADER if any(col in h for h in header))
        header_score = header_hits / len(REQUIRED_HEADER)

        # 2. Row count
        n = len(rows)
        if n >= 10:
            row_score = 1.0
        elif n >= 6:
            row_score = 0.6
        elif n >= 3:
            row_score = 0.3
        else:
            row_score = max(0.0, n / 10.0)

        # 3. Credit code format validity (column 1, 0-indexed)
        code_valid = 0
        code_total = 0
        if header_hits >= 2:
            code_col = None
            for idx, h in enumerate(header):
                if "统一社会信用代码" in h or "信用代码" in h:
                    code_col = idx
                    break
            if code_col is not None:
                for row in rows:
                    if code_col >= len(row):
                        continue
                    val = row[code_col].strip()
                    if not val or val.lower() in PLACEHOLDER_TOKENS:
                        continue
                    code_total += 1
                    if CREDIT_CODE_RE.match(val):
                        code_valid += 1
        code_score = (code_valid / max(code_total, 1)) if code_total else 0.0
        # Need enough codes attempted, otherwise penalize
        if code_total < 5:
            code_score *= code_total / 5.0

        # 4. Non-placeholder ratio across all cells
        placeholder_ratio = self._placeholder_ratio(rows)
        non_placeholder_score = max(0.0, 1.0 - placeholder_ratio * 1.5)

        # 5. Search behavior: agent must have actually called web_search / web_fetch
        search_calls = [d for d in dispatches if d.tool_name == "web_search"]
        fetch_calls = [d for d in dispatches if d.tool_name == "web_fetch"]
        unique_search = {(d.request_body or {}).get("query", "") for d in search_calls if d.response_status < 400}
        unique_fetch = {(d.request_body or {}).get("url", "") for d in fetch_calls if d.response_status < 400}
        # ≥6 unique queries OR ≥6 unique fetches → full credit; scale linearly otherwise
        search_breadth = min((len(unique_search) + len(unique_fetch)) / 12.0, 1.0)

        completion = (
            0.20 * header_score
            + 0.15 * row_score
            + 0.25 * code_score
            + 0.20 * non_placeholder_score
            + 0.20 * search_breadth
        )
        scores.completion = round(min(completion, 1.0), 4)
        scores.robustness = self.compute_robustness(dispatches)

        final_text = self._get_final_assistant_text(messages)
        scores.communication = self.compute_communication_substance(
            final_text,
            ["enterprise_info.csv", "覆盖", "异常", "查不到"],
            min(sum(1 for x in ["- ", "1.", "2.", "3."] if x in final_text) / 2.0, 1.0),
        )
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        return scores
