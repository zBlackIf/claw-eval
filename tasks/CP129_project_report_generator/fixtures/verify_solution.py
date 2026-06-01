"""Hidden verifier for CP129 - Project Report Generator."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path


def _ensure_openpyxl():
    """Ensure openpyxl is available for running the agent's script."""
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "openpyxl", "-q"],
            capture_output=True, timeout=60,
        )


def _find_workspace() -> Path:
    """Find workspace root with fallback."""
    candidates = [
        Path("/workspace/fixtures/project-reporter"),
        Path("/workspace/project-reporter"),
        Path("/workspace/fixtures"),
        Path("/workspace"),
    ]
    for candidate in candidates:
        if candidate.exists() and (candidate / "projects_data.json").exists():
            return candidate
    # Fallback: check if data files are directly in /workspace/fixtures/project-reporter
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path("/workspace/fixtures/project-reporter")


def grade_workspace() -> dict:
    _ensure_openpyxl()
    ws = _find_workspace()
    components = {k: 0.0 for k in [
        "script_exists",
        "script_runs",
        "output_exists",
        "overdue_calculation",
        "risk_classification",
        "schedule_merged",
        "summary_stats",
        "markdown_structure",
    ]}

    script_path = ws / "generate_report.py"
    if not script_path.exists():
        # Check alternative locations where the agent might place the script
        search_paths = [
            ws.parent / "generate_report.py",
            Path("/workspace/generate_report.py"),
            Path("/workspace/fixtures/generate_report.py"),
            Path("/workspace/fixtures/project-reporter/generate_report.py"),
            Path("/workspace/project-reporter/generate_report.py"),
        ]
        for alt in search_paths:
            if alt.exists():
                script_path = alt
                break

    # 1. Script exists
    if script_path.exists():
        components["script_exists"] = 1.0
    else:
        return {
            "overall_score": 0.0,
            "components": components,
            "weights": _weights(),
        }

    # 2. Script runs without error
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(ws),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            components["script_runs"] = 1.0
        else:
            components["script_runs"] = 0.3  # partial if it at least tried
    except Exception:
        components["script_runs"] = 0.0

    # 3. Output file exists
    output_path = ws / "output_report.md"
    if not output_path.exists():
        # Try alternative locations and file names
        search_outputs = [
            Path("/workspace/output_report.md"),
            ws.parent / "output_report.md",
            Path("/workspace/fixtures/project-reporter/output_report.md"),
            Path("/workspace/fixtures/output_report.md"),
            ws / "report.md",
            Path("/workspace/report.md"),
            Path("/workspace/fixtures/project-reporter/report.md"),
        ]
        for alt in search_outputs:
            if alt.exists():
                output_path = alt
                break
        # If still not found, search for any .md file in workspace that looks like a report
        if not output_path.exists():
            for search_dir in [ws, Path("/workspace"), Path("/workspace/fixtures")]:
                if search_dir.exists():
                    for md_file in search_dir.glob("*.md"):
                        content_peek = md_file.read_text(encoding="utf-8", errors="ignore")[:200]
                        if "项目" in content_peek or "report" in content_peek.lower() or "周报" in content_peek:
                            output_path = md_file
                            break
                if output_path.exists():
                    break

    if output_path.exists():
        components["output_exists"] = 1.0
        report_content = output_path.read_text(encoding="utf-8", errors="ignore")
    else:
        # Give partial credit if script ran but output is elsewhere
        if components["script_runs"] == 1.0:
            components["output_exists"] = 0.2
        return {
            "overall_score": _calc_score(components),
            "components": components,
            "weights": _weights(),
        }

    # 4. Overdue calculation correctness
    # Based on report_date=2026-04-22, the overdue tasks should be:
    # Project 301: tasks 5003(4/20), 5004(4/17), 5005(4/19), 5006(4/16) = 4 overdue
    # Project 302: tasks 6004(4/18), 6005(4/15), 6006(4/13), 6007(4/20) = 4 overdue
    # Project 303: task 7004(4/19) = 1 overdue
    # Project 304: tasks 8001-8009 (all deadline < 4/22 and not completed) = 9 overdue
    # Total overdue: 4+4+1+9 = 18

    import re
    overdue_score = 0.0

    # Check if report mentions overdue/逾期 concept at all
    has_overdue_concept = bool(re.search(r'逾期|overdue|延期|超期|过期|未完成', report_content, re.IGNORECASE))
    if has_overdue_concept:
        overdue_score += 0.3

    # Project 304 should have the most overdue tasks (8-9)
    if "商城小程序" in report_content:
        p304_section = ""
        parts = report_content.split("商城小程序")
        if len(parts) > 1:
            p304_section = parts[1][:3000]

        # Look for numbers 8 or 9 near overdue context (flexible patterns)
        p304_patterns = [
            r'[89]\s*[个项条任]',
            r'逾期[^。\n]{0,50}[89]',
            r'[89][^。\n]{0,50}逾期',
            r'overdue[^.\n]{0,50}[89]',
            r'[89][^.\n]{0,50}overdue',
            r'逾期[^。\n]{0,50}任务[^。\n]{0,30}[89]',
            r'[89][^。\n]{0,50}(未完成|待开始|进行中)',
        ]
        if any(re.search(p, p304_section, re.IGNORECASE) for p in p304_patterns):
            overdue_score += 0.3
        elif re.search(r'逾期|overdue|延期|未完成', p304_section, re.IGNORECASE):
            overdue_score += 0.15

    # Check if total overdue is mentioned (should be 14-20 range)
    # Multiple patterns: "总逾期任务数: 18", "18个逾期", "逾期 18", etc.
    all_numbers = re.findall(r'(\d+)\s*[个项条]?\s*(?:逾期|overdue|延期)|(?:逾期|overdue|延期)[^。\n]{0,40}?(\d+)', report_content, re.IGNORECASE)
    for m in all_numbers:
        val = int(m[0] or m[1])
        if 14 <= val <= 20:
            overdue_score += 0.2
            break
        elif 10 <= val <= 25:
            overdue_score += 0.1
            break

    # Check if overdue task detail tables/lists exist (flexible)
    # Look for task IDs (4-digit numbers like 5003, 8001) in table-like structures or lists
    if re.search(r'\|\s*\d{4}\s*\||\|\s*[5-8]0\d{2}\s*\|', report_content):
        overdue_score += 0.1
    elif re.search(r'[5-8]0\d{2}', report_content):
        # Task IDs present even without table format
        overdue_score += 0.05

    # Check if deadline/截止 info appears in the report
    if re.search(r'截止|deadline|到期|逾期天数|超期天数', report_content, re.IGNORECASE):
        overdue_score += 0.1

    components["overdue_calculation"] = min(1.0, overdue_score)

    # 5. Risk classification
    # Project 301: actual=18/28=64%, expected~90%, lag=26% -> 中风险
    # Project 302: actual=30/35=86%, expected~90%, lag=4% -> 低风险
    # Project 303: actual=14/15=93%, expected~90%, lag=0% -> 低风险
    # Project 304: actual=20/52=38%, expected~90%, lag=52% -> 高风险
    risk_score = 0.0
    # Check if risk concept is present
    has_risk_concept = bool(re.search(r'风险|risk', report_content, re.IGNORECASE))
    if has_risk_concept:
        risk_score += 0.2

    # Project 304 (商城小程序) should be high risk
    if re.search(r'商城小程序[^#]*高风险|高风险[^#]*商城小程序|商城小程序[^#]*high\s*risk', report_content, re.DOTALL | re.IGNORECASE):
        risk_score += 0.3
    elif "高风险" in report_content or re.search(r'high[\s_-]*risk', report_content, re.IGNORECASE):
        risk_score += 0.2

    # Project 302 (支付网关) should be low risk
    if re.search(r'支付网关[^#]*低风险|低风险[^#]*支付网关', report_content, re.DOTALL):
        risk_score += 0.2
    elif "低风险" in report_content or re.search(r'low[\s_-]*risk', report_content, re.IGNORECASE):
        risk_score += 0.1

    # Project 303 (数据大屏) should be low risk
    if re.search(r'数据大屏[^#]*低风险|低风险[^#]*数据大屏', report_content, re.DOTALL):
        risk_score += 0.15
    elif re.search(r'数据大屏', report_content):
        risk_score += 0.05

    # 中风险 for Project 301 (用户中心)
    if "中风险" in report_content or re.search(r'medium[\s_-]*risk|moderate[\s_-]*risk|mid[\s_-]*risk', report_content, re.IGNORECASE):
        risk_score += 0.15

    components["risk_classification"] = min(1.0, risk_score)

    # 6. Schedule data merged from Excel
    schedule_score = 0.0
    schedule_keywords = [
        "4/18完成开发",
        "4/17-4/20测试",
        "4/14验收",
        "4/20完成一期开发",
    ]
    matches = sum(1 for kw in schedule_keywords if kw in report_content)
    schedule_score = min(1.0, matches * 0.3)
    # Partial credit for variations (date formats may differ)
    if matches == 0:
        # Check for date-based schedule info in any format
        schedule_date_patterns = [
            r'4[\-/月.]18[^0-9].*(?:开发|dev)|(?:开发|dev).*4[\-/月.]18',
            r'4[\-/月.]17[^0-9].*4[\-/月.]20[^0-9].*(?:测试|test)|(?:测试|test).*4[\-/月.]17',
            r'4[\-/月.]14[^0-9].*(?:验收|accept)|(?:验收|accept).*4[\-/月.]14',
            r'4[\-/月.]20[^0-9].*(?:一期|phase)|(?:一期|phase).*4[\-/月.]20',
        ]
        alt_matches = sum(1 for p in schedule_date_patterns if re.search(p, report_content, re.IGNORECASE))
        schedule_score = min(1.0, alt_matches * 0.25)
    # Partial credit if any schedule/milestone info appears
    if schedule_score == 0.0 and re.search(r'排期|schedule|计划|里程碑|milestone|节点|阶段', report_content, re.IGNORECASE):
        schedule_score = 0.4
    # Partial credit if schedule.xlsx was clearly read (dates from it appear)
    if schedule_score < 0.4 and re.search(r'2026[\-/]0?4[\-/](1[3-9]|2[0-2])', report_content):
        schedule_score = max(schedule_score, 0.3)
    components["schedule_merged"] = schedule_score

    # 7. Summary statistics
    summary_score = 0.0
    # Check for summary table with totals
    if re.search(r'总项目.*4|4\s*[个项].*项目|项目.*总数.*4|4.*个项目|项目数[^。\n]{0,20}4', report_content):
        summary_score += 0.25
    elif re.search(r'汇总|总[计览]|summary|overview|概览', report_content, re.IGNORECASE):
        summary_score += 0.15
    # Total tasks should be 28+35+15+52=130
    if re.search(r'130|总任务.*1[23]\d|1[23]\d.*总任务|任务总数[^。\n]{0,20}1[23]\d', report_content):
        summary_score += 0.25
    elif re.search(r'总任务|总.*任务数|total.*task|任务总数', report_content, re.IGNORECASE):
        summary_score += 0.15
    # Should have risk distribution
    if re.search(r'高风险.*\d|低风险.*\d|\d.*高风险|\d.*低风险|风险.*[高中低]', report_content):
        summary_score += 0.25
    elif re.search(r'风险.*分布|risk.*distribution|风险.*等级|风险.*统计', report_content, re.IGNORECASE):
        summary_score += 0.15
    # Should have a table format
    if report_content.count("|") >= 10:
        summary_score += 0.25
    elif report_content.count("|") >= 4:
        summary_score += 0.15
    components["summary_stats"] = min(1.0, summary_score)

    # 8. Markdown structure
    structure_score = 0.0
    # Has headers
    if re.search(r'^#{1,3}\s', report_content, re.MULTILINE):
        header_count = len(re.findall(r'^#{1,3}\s', report_content, re.MULTILINE))
        if header_count >= 4:
            structure_score += 0.25
        elif header_count >= 2:
            structure_score += 0.15
    # Has tables
    if "|" in report_content and ("---" in report_content or "—" in report_content):
        structure_score += 0.25
    elif "|" in report_content:
        structure_score += 0.15
    # Has all 4 projects mentioned
    project_names = ["用户中心", "支付网关", "数据大屏", "商城小程序"]
    mentioned = sum(1 for name in project_names if name in report_content)
    structure_score += mentioned * 0.1
    # Has date
    if "2026" in report_content or "04-22" in report_content or "4月22" in report_content:
        structure_score += 0.1
    components["markdown_structure"] = min(1.0, structure_score)

    return {
        "overall_score": _calc_score(components),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": _weights(),
    }


def _weights() -> dict:
    return {
        "script_exists": 0.10,
        "script_runs": 0.20,
        "output_exists": 0.10,
        "overdue_calculation": 0.20,
        "risk_classification": 0.15,
        "schedule_merged": 0.10,
        "summary_stats": 0.08,
        "markdown_structure": 0.07,
    }


def _calc_score(components: dict) -> float:
    w = _weights()
    return round(sum(w[k] * components[k] for k in w), 4)


def main():
    result = grade_workspace()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
