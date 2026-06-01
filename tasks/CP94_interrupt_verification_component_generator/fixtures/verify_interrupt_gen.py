"""Hidden verifier for CP92 — interrupt cluster verification generator."""
from __future__ import annotations

import json
import re
from pathlib import Path


def grade_workspace(ws: Path) -> dict:
    main = ws / "interrupt_cluster_check_gen.py"
    if not main.exists():
        for p in ws.rglob("*interrupt*cluster*gen*.py"):
            main = p
            break
    components = {k: 0.0 for k in [
        "main_script_exists", "verdi_integration", "excel_generation",
        "excel_reading", "sv_task_generation", "five_repeat_loop",
        "level_pulse_handling",
    ]}
    if not main.exists():
        return {"overall_score": 0.0, "components": components}

    components["main_script_exists"] = 1.0
    content = main.read_text(encoding="utf-8", errors="ignore")

    has_verdi = bool(re.search(r"verdi", content, re.I))
    has_tcl = bool(re.search(r"\.tcl|tcl_script", content, re.I))
    has_kdb = bool(re.search(r"kdb", content, re.I))
    if has_verdi and has_tcl and has_kdb:
        components["verdi_integration"] = 1.0
    elif has_verdi and has_kdb:
        components["verdi_integration"] = 0.75
    elif has_verdi:
        components["verdi_integration"] = 0.5

    has_excel_w = bool(re.search(r"ExcelWriter|to_excel|xlsxwriter|openpyxl.*save|write_excel", content, re.I))
    has_cols = bool(re.search(r"hierarchy|trigger|info|level.*pulse|ral", content, re.I))
    if has_excel_w and has_cols:
        components["excel_generation"] = 1.0
    elif has_excel_w:
        components["excel_generation"] = 0.5

    has_excel_r = bool(re.search(r"read_excel|pd\.read|ExcelFile|load_workbook", content, re.I))
    has_xlsx = "interrupt_cluster_check" in content
    if has_excel_r and has_xlsx:
        components["excel_reading"] = 1.0
    elif has_excel_r:
        components["excel_reading"] = 0.5

    has_sv = bool(re.search(r"\.sv|systemverilog|task\s+automatic|`include", content, re.I))
    has_ral = bool(re.search(r"\bral\b|register.*access|uvm_status", content, re.I))
    has_force = "force" in content.lower()
    if has_sv and has_ral and has_force:
        components["sv_task_generation"] = 1.0
    elif has_sv and has_ral:
        components["sv_task_generation"] = 0.75
    elif has_sv:
        components["sv_task_generation"] = 0.5

    if re.search(r"repeat.*5|5.*repeat|repeat_count\s*=\s*5|for.*5|range\(5\)|iter.*<\s*5", content, re.I):
        components["five_repeat_loop"] = 1.0

    has_level = bool(re.search(r"level", content, re.I))
    has_pulse = bool(re.search(r"pulse", content, re.I))
    has_dur = bool(re.search(r"clk|cycle|clock|持续|duration", content, re.I))
    if has_level and has_pulse and has_dur:
        components["level_pulse_handling"] = 1.0
    elif has_level and has_pulse:
        components["level_pulse_handling"] = 0.5

    weights = {
        "main_script_exists": 0.05,
        "verdi_integration": 0.20,
        "excel_generation": 0.20,
        "excel_reading": 0.10,
        "sv_task_generation": 0.20,
        "five_repeat_loop": 0.10,
        "level_pulse_handling": 0.15,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    print(json.dumps(grade_workspace(Path("/workspace")), ensure_ascii=False))


if __name__ == "__main__":
    main()
