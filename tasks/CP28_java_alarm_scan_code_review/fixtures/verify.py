#!/usr/bin/env python3
"""In-container verifier for CP28_java_alarm_scan_code_review.

Ports the original automated_score() to a script that runs under
env_snapshot_commands. Emits one JSON line with per-component scores plus
overall_score = mean(components).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

WORKSPACE = Path("/workspace")


def automated_score(workspace: Path) -> dict[str, float]:
    scores = {}

    # Find review report
    report = workspace / "review_report.md"
    if not report.exists():
        for f in workspace.glob("*.md"):
            if f.name != "design_spec.md":
                report = f
                break

    if not report.exists():
        for f in workspace.rglob("*review*"):
            report = f
            break

    if report and report.exists():
        scores["report_created"] = 1.0
        content = report.read_text(encoding="utf-8", errors="ignore").lower()

        # Check for key issues identified
        issues_found = 0
        if "interface" in content:
            issues_found += 1
        if "public" in content and ("field" in content or "rules" in content):
            issues_found += 1
        if "exception" in content or "swallow" in content or "catch" in content:
            issues_found += 1
        if "hardcod" in content or "hard-cod" in content or "smtp" in content:
            issues_found += 1
        if "repository" in content or "missing" in content:
            issues_found += 1
        if "strategy" in content or "pattern" in content:
            issues_found += 1

        scores["issues_identified"] = min(issues_found / 6.0, 1.0)
        expected_findings = {
            "scanner_interface": ["alarmscanner", "interface"],
            "public_rules": ["public", "rules"],
            "swallowed_exception": ["catch", "exception"],
            "hardcoded_smtp": ["smtp", "hardcod"],
            "missing_repository": ["repository", "missing"],
            "missing_dispatcher": ["notificationdispatcher", "dispatcher"],
        }
        finding_hits = 0
        for terms in expected_findings.values():
            if all(t in content for t in terms):
                finding_hits += 1
        scores["expected_finding_ids"] = finding_hits / len(expected_findings)
        path_refs = sum(
            1
            for p in ["AlarmScanner.java", "RuleEngine.java", "EmailNotifier.java", "design_spec.md"]
            if p.lower() in content
        )
        scores["source_references"] = min(path_refs / 3.0, 1.0)
        scores["line_or_method_refs"] = 1.0 if re.search(r"line\s*\d+|:\d+|method|class|字段|方法", content, re.I) else 0.0

        # Has severity classification
        has_severity = bool(re.search(r"(critical|high|medium|low)", content))
        scores["has_severity"] = 1.0 if has_severity else 0.0

        # Has actionable suggestions
        has_suggestions = bool(re.search(
            r"(suggest|recommend|should|consider|improv)", content
        ))
        scores["has_suggestions"] = 1.0 if has_suggestions else 0.0

        # Report length (minimum substance)
        word_count = len(content.split())
        scores["report_substance"] = min(1.0, word_count / 300.0)
    else:
        scores["report_created"] = 0.0
        scores["issues_identified"] = 0.0
        scores["expected_finding_ids"] = 0.0
        scores["source_references"] = 0.0
        scores["line_or_method_refs"] = 0.0
        scores["has_severity"] = 0.0
        scores["has_suggestions"] = 0.0
        scores["report_substance"] = 0.0

    return scores


def main() -> dict:
    try:
        scores = automated_score(WORKSPACE)
    except Exception as exc:  # noqa: BLE001
        return {"scores": {}, "overall_score": 0.0, "error": f"{type(exc).__name__}: {exc}"}
    numeric = [float(v) for v in scores.values() if isinstance(v, (int, float))]
    overall = sum(numeric) / len(numeric) if numeric else 0.0
    return {"scores": scores, "overall_score": round(overall, 4)}


if __name__ == "__main__":
    sys.stdout.write(json.dumps(main(), ensure_ascii=False) + "\n")
