"""Hidden verifier for CP128 — Project Report Generator.

Checks:
1. Script exists and is executable (generate_report.py)
2. Single-project report generation works (--id flag)
3. Batch report generation works (--all flag)
4. Risk calculation correctness (high/medium/low thresholds)
5. Excel data integration (schedule and phase from xlsx)
6. Report structure completeness (summary table, per-project sections)
7. Phase override logic (Excel phase takes priority over auto-detection)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _run_cmd(cmd: list[str], cwd: str, timeout: int = 30) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:
        return -1, "", str(e)


def grade_workspace(ws: Path) -> dict:
    # Try both possible locations
    base = ws / "fixtures" / "project-report-gen"
    if not base.exists():
        base = ws / "project-report-gen"
    if not base.exists():
        base = ws

    # Find the generate_report.py script
    script = None
    for candidate in [
        base / "generate_report.py",
        ws / "generate_report.py",
        ws / "fixtures" / "project-report-gen" / "generate_report.py",
        ws / "project-report-gen" / "generate_report.py",
    ]:
        if candidate.exists():
            script = candidate
            break

    # Also search recursively
    if not script:
        for p in ws.rglob("generate_report.py"):
            script = p
            break

    components = {k: 0.0 for k in [
        "script_exists",
        "single_report_works",
        "batch_report_works",
        "risk_calculation",
        "excel_integration",
        "report_structure",
        "phase_override",
    ]}

    if not script:
        return {
            "overall_score": 0.0,
            "components": components,
            "weights": _weights(),
            "error": "generate_report.py not found anywhere in workspace",
        }

    components["script_exists"] = 1.0
    script_dir = script.parent

    # Ensure openpyxl is available
    subprocess.run([sys.executable, "-m", "pip", "install", "openpyxl", "-q"],
                   capture_output=True, timeout=30)

    # Check 2: Single report generation (--id 910)
    rc, stdout, stderr = _run_cmd(
        [sys.executable, str(script), "--id", "910"],
        cwd=str(script_dir),
    )
    if rc == 0 and stdout.strip():
        single_output = stdout.strip()
        # Check for key elements in single report
        has_project_name = "910" in single_output
        has_progress = any(w in single_output for w in ["43", "87", "进度"])
        has_risk = any(w in single_output.lower() for w in ["高风险", "high", "risk", "⚠"])
        has_overdue = any(w in single_output for w in ["逾期", "overdue", "8"])
        score = sum([has_project_name, has_progress, has_risk, has_overdue]) / 4.0
        components["single_report_works"] = round(score, 4)
    elif rc == 0:
        # Maybe it writes to a file by default
        components["single_report_works"] = 0.3

    # Check 3: Batch report generation (--all)
    rc, stdout, stderr = _run_cmd(
        [sys.executable, str(script), "--all"],
        cwd=str(script_dir),
    )
    if rc == 0 and stdout.strip():
        batch_output = stdout.strip()
        # Should mention multiple projects
        project_ids = ["891", "898", "910", "897", "952", "972", "974"]
        found_ids = sum(1 for pid in project_ids if pid in batch_output)
        components["batch_report_works"] = round(min(found_ids / 5.0, 1.0), 4)
    elif rc == 0:
        # Check if output file was created
        for out_candidate in [script_dir / "report.md", script_dir / "output.md"]:
            if out_candidate.exists():
                batch_output = out_candidate.read_text(encoding="utf-8", errors="ignore")
                project_ids = ["891", "898", "910", "897", "952", "972", "974"]
                found_ids = sum(1 for pid in project_ids if pid in batch_output)
                components["batch_report_works"] = round(min(found_ids / 5.0, 1.0), 4)
                break

    # Check 4: Risk calculation correctness
    # Expected: 891=low(7%), 898=medium(11%), 910=high(44%), 897=high(32%),
    #           952=medium(16%), 972=high(32%), 974=high(50%)
    rc, stdout, stderr = _run_cmd(
        [sys.executable, str(script), "--all"],
        cwd=str(script_dir),
    )
    if rc == 0:
        output = stdout.strip()
        if not output:
            # Try reading output file
            for out_candidate in [script_dir / "report.md", script_dir / "output.md"]:
                if out_candidate.exists():
                    output = out_candidate.read_text(encoding="utf-8", errors="ignore")
                    break

        if output:
            # Check risk levels are correctly assigned
            risk_checks = 0
            total_risk_checks = 4

            # ID 891 should be low risk (7% lag)
            idx_891 = output.find("891")
            if idx_891 >= 0:
                section_891 = output[idx_891:idx_891+300]
                if any(w in section_891 for w in ["低风险", "低", "low"]):
                    risk_checks += 1

            # ID 910 should be high risk (44% lag)
            idx_910 = output.find("910")
            if idx_910 >= 0:
                section_910 = output[idx_910:idx_910+300]
                if any(w in section_910 for w in ["高风险", "高", "high", "⚠"]):
                    risk_checks += 1

            # ID 898 should be medium risk (11% lag)
            idx_898 = output.find("898")
            if idx_898 >= 0:
                section_898 = output[idx_898:idx_898+300]
                if any(w in section_898 for w in ["中风险", "中", "medium"]):
                    risk_checks += 1

            # ID 974 should be high risk (50% lag)
            idx_974 = output.find("974")
            if idx_974 >= 0:
                section_974 = output[idx_974:idx_974+300]
                if any(w in section_974 for w in ["高风险", "高", "high", "⚠"]):
                    risk_checks += 1

            components["risk_calculation"] = round(risk_checks / total_risk_checks, 4)

    # Check 5: Excel integration (schedule text appears in output)
    rc, stdout, stderr = _run_cmd(
        [sys.executable, str(script), "--id", "891"],
        cwd=str(script_dir),
    )
    if rc == 0:
        output = stdout.strip()
        if not output:
            for out_candidate in [script_dir / "report.md", script_dir / "output.md"]:
                if out_candidate.exists():
                    output = out_candidate.read_text(encoding="utf-8", errors="ignore")
                    break
        if output:
            excel_checks = 0
            # Should include schedule from Excel
            if any(w in output for w in ["一期已上线", "4/23", "4/24测试", "4/27定版", "4/28上线"]):
                excel_checks += 1
            # Should include project phase from Excel
            if "测试中" in output:
                excel_checks += 1
            components["excel_integration"] = round(excel_checks / 2.0, 4)

    # Check 6: Report structure (summary table in batch mode)
    rc, stdout, stderr = _run_cmd(
        [sys.executable, str(script), "--all"],
        cwd=str(script_dir),
    )
    if rc == 0:
        output = stdout.strip()
        if not output:
            for out_candidate in [script_dir / "report.md", script_dir / "output.md"]:
                if out_candidate.exists():
                    output = out_candidate.read_text(encoding="utf-8", errors="ignore")
                    break
        if output:
            struct_checks = 0
            total_struct = 5
            # Should have summary statistics
            if any(w in output for w in ["总项目数", "项目数", "总计", "汇总", "统计"]):
                struct_checks += 1
            # Total tasks count (sum = 30+45+52+62+40+25+48 = 302)
            if any(w in output for w in ["302", "267", "总任务"]):
                struct_checks += 1
            # Total overdue (1+6+8+10+7+7+6 = 45)
            if any(w in output for w in ["45", "44", "逾期"]):
                struct_checks += 1
            # Has table formatting (| or structured sections)
            if "|" in output or "---" in output:
                struct_checks += 1
            # Has per-project sections
            if output.count("#") >= 7 or output.count("项目") >= 7:
                struct_checks += 1
            components["report_structure"] = round(struct_checks / total_struct, 4)

    # Check 7: Phase override logic (Excel phase takes priority)
    # ID 974: Excel says "待排期", API progress is 4% (would auto-detect as "开发中" or similar)
    rc, stdout, stderr = _run_cmd(
        [sys.executable, str(script), "--id", "974"],
        cwd=str(script_dir),
    )
    if rc == 0:
        output = stdout.strip()
        if not output:
            for out_candidate in [script_dir / "report.md", script_dir / "output.md"]:
                if out_candidate.exists():
                    output = out_candidate.read_text(encoding="utf-8", errors="ignore")
                    break
        if output:
            # Should use Excel phase "待排期" not auto-detect
            if "待排期" in output:
                components["phase_override"] = 1.0
            elif any(w in output for w in ["阶段", "phase"]):
                components["phase_override"] = 0.3

    weights = _weights()
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def _weights() -> dict:
    return {
        "script_exists": 0.05,
        "single_report_works": 0.20,
        "batch_report_works": 0.20,
        "risk_calculation": 0.20,
        "excel_integration": 0.15,
        "report_structure": 0.10,
        "phase_override": 0.10,
    }


def main():
    ws = Path("/workspace")
    # Fallback: check if fixtures are directly available
    if not (ws / "fixtures" / "project-report-gen").exists() and not (ws / "project-report-gen").exists():
        # Maybe we're in a different layout
        pass
    result = grade_workspace(ws)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
