#!/usr/bin/env python3
"""In-container verifier for CP23_cpp_firmware_starttime_bug_analysis.

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

    # Check BUGFIX_REPORT.md exists and has content
    report = workspace / "BUGFIX_REPORT.md"
    if report.exists():
        content = report.read_text()
        scores["bugfix_report_present"] = 1.0
        scores["report_has_root_cause"] = 1.0 if any(
            k in content.lower() for k in ["根因", "root cause", "原因", "问题分析"]
        ) else 0.0
        scores["report_has_fix"] = 1.0 if any(
            k in content.lower() for k in ["修复", "fix", "解决方案", "修改"]
        ) else 0.0
        scores["report_has_impact"] = 1.0 if any(
            k in content.lower() for k in ["影响", "impact", "副作用", "风险"]
        ) else 0.0
    else:
        scores["bugfix_report_present"] = 0.0
        scores["report_has_root_cause"] = 0.0
        scores["report_has_fix"] = 0.0
        scores["report_has_impact"] = 0.0

    # Check firmware_item.cpp was modified
    cpp_file = workspace / "src" / "item" / "firmware_item.cpp"
    if cpp_file.exists():
        content = cpp_file.read_text()
        scores["firmware_cpp_present"] = 1.0
        # Check if base class call was added (the fix)
        has_base_call = bool(re.search(
            r'(ICloneItem::preExecuteItem|base::preExecuteItem|'
            r'__super::preExecuteItem|Parent::preExecuteItem)',
            content
        ))
        scores["base_class_call_added"] = 1.0 if has_base_call else 0.0
        # Alternative fix: explicit startTime setting in subclass
        has_explicit_starttime = "m_startTime" in content and "getDateTimeString" in content
        if not has_base_call and has_explicit_starttime:
            scores["base_class_call_added"] = 0.7
    else:
        scores["firmware_cpp_present"] = 0.0
        scores["base_class_call_added"] = 0.0

    # Check that iclone_item.h was NOT modified (constraint)
    iclone_h = workspace / "src" / "item" / "iclone_item.h"
    if iclone_h.exists():
        original_size = 2048  # approximate
        current_size = iclone_h.stat().st_size
        # Allow small size changes (formatting) but flag major changes
        scores["base_class_not_modified"] = 1.0 if abs(current_size - original_size) < 500 else 0.5
    else:
        scores["base_class_not_modified"] = 1.0

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
