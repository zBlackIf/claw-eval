"""CP16_web_file_upload_security_audit grader.

The deliverable is the final assistant message, not a workspace markdown file.
"""

from __future__ import annotations

import re
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


class WebFileUploadSecurityAuditGrader(AbstractGrader):
    FINDINGS = [
        ("extension_bypass", ["扩展名", "extension", "double extension", "双扩展"]),
        ("mime_validation", ["mime", "finfo", "content-type", "探嗅"]),
        ("path_traversal", ["path traversal", "路径穿越", "../", "basename"]),
        ("size_limit", ["size", "大小", "oversize", "dos", "client_max_body_size"]),
        ("race_condition", ["race", "toctou", "竞态", "覆盖"]),
        ("executable_upload", [".htaccess", "php", "phtml", "phar", "rce", "代码执行"]),
        ("xss_filename", ["xss", "htmlspecialchars", "转义"]),
        ("privacy_log", ["remote_addr", "gdpr", "隐私", "ip"]),
        ("csrf", ["csrf", "token"]),
    ]

    _REPORT_RUBRIC = """\
评估最终安全审计报告质量（0.0-1.0）。

高分报告应让开发可以直接修复：
- 每个 finding 有文件/位置、严重级别、影响、PoC 思路、修复建议
- 覆盖 PHP upload handler 与 nginx uploads 配置
- 区分 Critical/High/Medium，并给出优先级
- 不泛泛而谈，不凭空编造与代码无关的问题
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

        if not final_text.strip():
            scores.completion = 0.0
            scores.robustness = self.compute_robustness(dispatches)
            return scores

        finding_hits = 0
        for _, terms in self.FINDINGS:
            if any(t.lower() in lower for t in terms):
                finding_hits += 1
        finding_score = finding_hits / len(self.FINDINGS)

        evidence_terms = ["upload_handler.php", "nginx_uploads.conf", "line", "行", "severity", "严重"]
        fix_terms = ["修复", "建议", "finfo", "basename", "htmlspecialchars", "deny", "nosniff"]
        structure_score = sum([
            min(sum(1 for t in evidence_terms if t.lower() in lower) / 4.0, 1.0),
            min(sum(1 for t in fix_terms if t.lower() in lower) / 4.0, 1.0),
            1.0 if re.search(r"critical|high|medium|严重|高危|中危", lower) else 0.0,
            min(len(final_text.strip()) / 900.0, 1.0),
        ]) / 4.0

        judge_score = 0.0
        if judge:
            try:
                result = judge.evaluate(task.prompt.text, final_text, "", self._REPORT_RUBRIC)
                judge_score = result.score
            except Exception as exc:  # noqa: BLE001
                print(f"[grader] security audit judge failed: {exc}")

        completion = 0.55 * finding_score + 0.25 * structure_score + 0.20 * judge_score
        if len(final_text.strip()) < 300:
            completion = min(completion, 0.45)
        scores.completion = round(min(completion, 1.0), 4)
        scores.robustness = self.compute_robustness(dispatches)
        scores.communication = self.compute_communication_substance(
            final_text,
            ["upload_handler.php", "nginx_uploads.conf", "Critical", "High", "修复"],
            min(sum(1 for x in ["#", "|", "- ", "1.", "2."] if x in final_text) / 4.0, 1.0),
        )
        scores.efficiency_turns = len([m for m in messages if m.message.role == "assistant"])
        return scores
