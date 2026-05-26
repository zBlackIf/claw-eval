#!/usr/bin/env python3
"""In-container verifier for CP32_java_dao_sql_fragment_extraction.

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

    sql_file = workspace / "sql" / "total_score_query.sql"
    java_file = workspace / "dao" / "TotalScoreDao.java"

    sql_content = sql_file.read_text(errors="ignore") if sql_file.exists() else ""
    java_content = java_file.read_text(errors="ignore") if java_file.exists() else ""

    # SQL has startedcourse JOIN
    sql_no_comments = re.sub(r"--.*$", "", sql_content, flags=re.MULTILINE)
    has_started = bool(re.search(r"startedcourse", sql_no_comments, re.IGNORECASE))
    has_uptostandard = bool(re.search(r"UpToStandard", sql_no_comments, re.IGNORECASE))
    if has_started and has_uptostandard:
        scores["sql_has_started_course_join"] = 1.0
    elif has_started:
        scores["sql_has_started_course_join"] = 0.5
    else:
        scores["sql_has_started_course_join"] = 0.0

    # SQL has canTakeTest JOIN
    has_qualification = bool(re.search(r"examstudenttestqualification", sql_no_comments, re.IGNORECASE))
    has_cantaketest = bool(re.search(r"CanTakeTest", sql_no_comments, re.IGNORECASE))
    if has_qualification and has_cantaketest:
        scores["sql_has_can_taketest_join"] = 1.0
    elif has_qualification:
        scores["sql_has_can_taketest_join"] = 0.5
    else:
        scores["sql_has_can_taketest_join"] = 0.0

    # SQL uses conditional syntax
    conditional_patterns = [
        r"<if\b", r"<when\b", r"<choose\b", r"--\s*\[if\b",
        r"CASE\s+WHEN", r"#if\b", r"\$\{", r"test=",
    ]
    is_conditional = any(re.search(p, sql_content, re.IGNORECASE) for p in conditional_patterns)
    scores["sql_is_conditional"] = 1.0 if is_conditional else 0.0

    # Java simplified (no more inline SQL concatenation)
    has_inline_started = bool(re.search(
        r'startedCourseSql\s*=\s*".*INNER JOIN', java_content, re.DOTALL
    ))
    has_inline_cantake = bool(re.search(
        r'canTaketestSql\s*=\s*".*INNER JOIN', java_content, re.DOTALL
    ))
    if not has_inline_started and not has_inline_cantake and java_file.exists():
        scores["java_simplified"] = 1.0
    elif not has_inline_started or not has_inline_cantake:
        scores["java_simplified"] = 0.5
    else:
        scores["java_simplified"] = 0.0

    # Risk assessment exists
    risk_files = list(workspace.rglob("*risk*")) + list(workspace.rglob("*风险*"))
    md_risk = [f for f in risk_files if f.suffix in (".md", ".txt")]
    if md_risk:
        content = md_risk[0].read_text(errors="ignore")
        scores["risk_assessment_exists"] = 1.0 if len(content) > 100 else 0.5
    else:
        scores["risk_assessment_exists"] = 0.0

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
