"""Hidden verifier for CP130 — Zentao Project Report Generator."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path


CURRENT_DATE = date(2026, 4, 23)

# Expected values for each project
EXPECTED = {
    891: {
        "name": "直播需求v2.2.8",
        "phase": "测试中",
        "total_tasks": 8,
        "done_count": 4,
        "actual_progress": 50,  # 4/8 = 50%
        "overdue_count": 0,  # tasks 29004(4/21 doing), 29007(4/20 done) — 29004 deadline 4/21 < 4/23 but doing not done → overdue; actually let's recalculate
        # Overdue = deadline < 2026-04-23 AND status != done
        # 29001: 4/18 done → not overdue
        # 29002: 4/19 done → not overdue
        # 29003: 4/20 done → not overdue
        # 29004: 4/21 doing → OVERDUE (2 days)
        # 29005: 4/22 doing → OVERDUE (1 day)
        # 29006: 4/23 wait → NOT overdue (deadline == current_date, not <)
        # 29007: 4/20 done → not overdue
        # 29008: 4/22 doing → OVERDUE (1 day)
        "overdue_count_correct": 3,
        "risk_level": "high",  # lag_rate=38% > 25% → high
        "schedule": "一期已上线。二期4/23完成开发",
        "estimated_hours": 78.0,
        "consumed_hours": 52.5,
    },
    897: {
        "name": "中台2.2.3",
        "phase": "开发中",
        "total_tasks": 14,
        "done_count": 2,
        "actual_progress": 14,  # 2/14 ≈ 14%
        "overdue_count_correct": 10,  # all wait tasks with deadline < 4/23
        "risk_level": "high",  # >7 overdue → high
        "schedule": "一期已上线。二期排期4/24完成开发",
        "estimated_hours": 148.0,
        "consumed_hours": 28.5,
    },
    910: {
        "name": "智能销售前沿获客v2.2.9",
        "phase": "测试中",
        "total_tasks": 10,
        "done_count": 2,
        "actual_progress": 20,  # 2/10 = 20%
        "overdue_count_correct": 7,  # 29103(4/20 wait), 29104(4/19 wait), 29105(4/18 wait), 29106(4/21 wait), 29107(4/20 wait), 29108(4/19 wait), 29109(4/22 doing)
        "risk_level": "high",  # lag_rate=60% > 25% → high
        "schedule": "4/24提测",
        "estimated_hours": 102.0,
        "consumed_hours": 37.0,
    },
}


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def check_report_exists(output_dir: Path, exec_id: int) -> float:
    """Check if report file exists."""
    report_file = output_dir / f"report_{exec_id}.md"
    if report_file.exists() and len(_read(report_file)) > 100:
        return 1.0
    return 0.0


def check_overdue_calculation(report_content: str, expected: dict) -> float:
    """Check if overdue task count is correctly calculated."""
    correct_count = expected["overdue_count_correct"]
    # Look for the overdue count in the report
    patterns = [
        rf"逾期任务[数量]*[：:|\s]*{correct_count}",
        rf"overdue[_ ]*(count|tasks?)[：:|\s]*{correct_count}",
        rf"{correct_count}\s*(个|项)?\s*逾期",
        rf"\|\s*\d+\s*\|\s*逾期任务数?\s*\|\s*{correct_count}\s*\|",
        rf"逾期任务[^|]*\|\s*{correct_count}\s*\|",
    ]
    for pat in patterns:
        if re.search(pat, report_content):
            return 1.0
    # Check if number appears near "逾期"
    matches = re.findall(r"逾期[^0-9]*(\d+)", report_content)
    if matches:
        if str(correct_count) in matches:
            return 1.0
        # Partial credit if close
        for m in matches:
            if abs(int(m) - correct_count) <= 1:
                return 0.5
    return 0.0


def check_risk_level(report_content: str, expected: dict) -> float:
    """Check if risk level is correctly determined."""
    risk = expected["risk_level"]
    risk_map = {
        "none": ["无风险", "no risk", "none"],
        "low": ["低风险", "low risk", "low"],
        "medium": ["中风险", "medium risk", "medium", "中等"],
        "high": ["高风险", "high risk", "high"],
    }
    for keyword in risk_map.get(risk, []):
        if keyword in report_content.lower() or keyword in report_content:
            return 1.0
    return 0.0


def check_schedule_integration(report_content: str, expected: dict) -> float:
    """Check if schedule info from CSV is correctly integrated."""
    schedule_fragment = expected.get("schedule", "")
    if not schedule_fragment:
        return 0.5
    if schedule_fragment in report_content:
        return 1.0
    # Partial match
    words = schedule_fragment.split("。")
    matched = sum(1 for w in words if w and w in report_content)
    return min(matched / max(len(words), 1), 1.0)


def check_phase_from_csv(report_content: str, expected: dict) -> float:
    """Check if project phase is read from CSV (not just API status)."""
    phase = expected["phase"]
    if phase in report_content:
        return 1.0
    return 0.0


def check_hours_calculation(report_content: str, expected: dict) -> float:
    """Check if hours are correctly summed."""
    est = expected["estimated_hours"]
    con = expected["consumed_hours"]
    score = 0.0
    # Look for estimated hours
    est_patterns = [str(est), f"{est:.0f}", f"{est:.1f}"]
    for p in est_patterns:
        if p in report_content:
            score += 0.5
            break
    # Look for consumed hours
    con_patterns = [str(con), f"{con:.0f}", f"{con:.1f}"]
    for p in con_patterns:
        if p in report_content:
            score += 0.5
            break
    return score


def check_overdue_details_table(report_content: str, exec_id: int) -> float:
    """Check if overdue task detail table is present with correct entries."""
    if exec_id == 891:
        # Should have 3 overdue tasks: 29004, 29005, 29008
        expected_ids = ["29004", "29005", "29008"]
    elif exec_id == 897:
        # Should have 10 overdue tasks
        expected_ids = ["28911", "28861", "28860", "28859", "28858", "28854", "28853", "28852", "28483", "28482"]
    elif exec_id == 910:
        expected_ids = ["29103", "29104", "29105", "29106", "29107", "29108", "29109"]
    else:
        return 0.0

    found = sum(1 for tid in expected_ids if tid in report_content)
    return found / len(expected_ids)


def check_script_runnable(ws: Path) -> float:
    """Check if generate_reports.py runs without errors."""
    script = None
    # Search in various locations
    for candidate in [
        ws / "fixtures" / "project_data" / "generate_reports.py",
        ws / "project_data" / "generate_reports.py",
        ws / "generate_reports.py",
    ]:
        if candidate.exists():
            script = candidate
            break

    if not script:
        # Search recursively
        for p in ws.rglob("generate_reports.py"):
            if "verify" not in p.name and "__pycache__" not in str(p):
                script = p
                break

    if not script:
        return 0.0

    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, timeout=30,
            cwd=str(script.parent),
        )
        if result.returncode == 0:
            return 1.0
        return 0.2  # at least it exists
    except Exception:
        return 0.1


def grade_workspace(ws: Path) -> dict:
    """Grade the workspace."""
    components = {
        "script_runs": 0.0,
        "reports_generated": 0.0,
        "overdue_calculation": 0.0,
        "risk_assessment": 0.0,
        "schedule_integration": 0.0,
        "hours_accuracy": 0.0,
        "overdue_details": 0.0,
    }

    # 1. Check if script runs
    components["script_runs"] = check_script_runnable(ws)

    # Find output directory
    output_dir = None
    for candidate in [
        ws / "fixtures" / "project_data" / "output",
        ws / "project_data" / "output",
        ws / "output",
    ]:
        if candidate.exists():
            output_dir = candidate
            break

    if not output_dir:
        # Search
        for p in ws.rglob("output"):
            if p.is_dir() and any(p.glob("report_*.md")):
                output_dir = p
                break

    if not output_dir:
        return {
            "overall_score": round(components["script_runs"] * 0.25, 4),
            "components": components,
        }

    # 2. Check reports exist
    exist_scores = []
    for exec_id in [891, 897, 910]:
        exist_scores.append(check_report_exists(output_dir, exec_id))
    components["reports_generated"] = sum(exist_scores) / len(exist_scores)

    # Grade each report
    overdue_scores = []
    risk_scores = []
    schedule_scores = []
    hours_scores = []
    detail_scores = []

    for exec_id, expected in EXPECTED.items():
        report_file = output_dir / f"report_{exec_id}.md"
        content = _read(report_file)
        if not content:
            overdue_scores.append(0.0)
            risk_scores.append(0.0)
            schedule_scores.append(0.0)
            hours_scores.append(0.0)
            detail_scores.append(0.0)
            continue

        overdue_scores.append(check_overdue_calculation(content, expected))
        risk_scores.append(check_risk_level(content, expected))
        schedule_scores.append(check_schedule_integration(content, expected))
        hours_scores.append(check_hours_calculation(content, expected))
        detail_scores.append(check_overdue_details_table(content, exec_id))

    components["overdue_calculation"] = sum(overdue_scores) / max(len(overdue_scores), 1)
    components["risk_assessment"] = sum(risk_scores) / max(len(risk_scores), 1)
    components["schedule_integration"] = sum(schedule_scores) / max(len(schedule_scores), 1)
    components["hours_accuracy"] = sum(hours_scores) / max(len(hours_scores), 1)
    components["overdue_details"] = sum(detail_scores) / max(len(detail_scores), 1)

    weights = {
        "script_runs": 0.15,
        "reports_generated": 0.10,
        "overdue_calculation": 0.20,
        "risk_assessment": 0.15,
        "schedule_integration": 0.15,
        "hours_accuracy": 0.10,
        "overdue_details": 0.15,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    # Try /workspace/fixtures/project_data first, then /workspace/project_data, then /workspace
    ws = Path("/workspace")

    # Run the script first if it exists
    script = None
    for candidate in [
        ws / "fixtures" / "project_data" / "generate_reports.py",
        ws / "project_data" / "generate_reports.py",
        ws / "generate_reports.py",
    ]:
        if candidate.exists():
            script = candidate
            break
    if not script:
        for p in ws.rglob("generate_reports.py"):
            if "verify" not in p.name and "__pycache__" not in str(p):
                script = p
                break

    if script:
        try:
            subprocess.run(
                [sys.executable, str(script)],
                capture_output=True, text=True, timeout=30,
                cwd=str(script.parent),
            )
        except Exception:
            pass

    result = grade_workspace(ws)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
