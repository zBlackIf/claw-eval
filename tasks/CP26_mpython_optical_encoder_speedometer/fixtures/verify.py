#!/usr/bin/env python3
"""In-container verifier for CP26_mpython_optical_encoder_speedometer.

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

    ds_dir = workspace / "DS_speed_car"

    # Find master program
    master_file = None
    slave_file = None
    for p in ds_dir.rglob("*.py") if ds_dir.exists() else []:
        name = p.name.lower()
        if "reference" in name or "diagnostic" in name:
            continue
        content = p.read_text(encoding="utf-8", errors="ignore")
        if ("P0" in content or "laser" in content.lower() or "photo_pin" in content):
            if "radio" not in content.lower() or "send" in content.lower():
                master_file = p
        if ("radio" in content.lower() or "无线" in content) and "receive" in content.lower():
            slave_file = p

    if not master_file:
        for p in (ds_dir.rglob("*主机*.py") if ds_dir.exists() else []):
            master_file = p
            break
    if not master_file:
        for p in (ds_dir.rglob("*master*.py") if ds_dir.exists() else []):
            master_file = p
            break
    if not slave_file:
        for p in (ds_dir.rglob("*从机*.py") if ds_dir.exists() else []):
            slave_file = p
            break
    if not slave_file:
        for p in (ds_dir.rglob("*slave*.py") if ds_dir.exists() else []):
            slave_file = p
            break

    # Also search workspace root
    if not master_file:
        for p in workspace.rglob("*master*.py"):
            master_file = p
            break
    if not slave_file:
        for p in workspace.rglob("*slave*.py"):
            slave_file = p
            break

    scores["master_program_created"] = 1.0 if master_file and master_file.exists() else 0.0
    scores["slave_program_created"] = 1.0 if slave_file and slave_file.exists() else 0.0

    if not master_file or not master_file.exists():
        scores["calibration_flow"] = 0.0
        scores["dynamic_threshold"] = 0.0
        scores["per_pulse_speed"] = 0.0
        scores["auto_stop"] = 0.0
        scores["correct_mpython_api"] = 0.0
        return scores

    content = master_file.read_text(encoding="utf-8", errors="ignore")

    # Calibration flow
    has_calibration = bool(re.search(r'(校准|calibrat)', content, re.IGNORECASE))
    has_button_a = "button_a" in content
    has_button_b = "button_b" in content
    cal_score = 0.0
    if has_calibration and has_button_a and has_button_b:
        cal_score = 1.0
    elif has_calibration and has_button_a:
        cal_score = 0.5
    elif has_button_a:
        cal_score = 0.25
    scores["calibration_flow"] = cal_score

    # Dynamic threshold
    dynamic_calc = bool(re.search(
        r'(v_min|v_max|cal_min|cal_max|voltage_min|voltage_max|min_v|max_v)',
        content, re.IGNORECASE
    ))
    percentage_calc = bool(re.search(r'(\*\s*0\.\d+|\d+\s*%|range)', content, re.IGNORECASE))
    if dynamic_calc and percentage_calc:
        scores["dynamic_threshold"] = 1.0
    elif dynamic_calc:
        scores["dynamic_threshold"] = 0.75
    else:
        scores["dynamic_threshold"] = 0.0

    # Per pulse speed
    has_speed_calc = "DISTANCE_PER_SLIT" in content or "12.97" in content or "缝间距" in content
    has_per_edge = bool(re.search(r'(edge|边沿|脉冲|pulse).*speed|speed.*per', content, re.IGNORECASE))
    if has_per_edge and has_speed_calc:
        scores["per_pulse_speed"] = 1.0
    elif has_speed_calc:
        scores["per_pulse_speed"] = 0.5
    else:
        scores["per_pulse_speed"] = 0.0

    # Auto stop (2 seconds timeout)
    has_timeout = bool(re.search(r'(2000|2\s*秒|timeout|auto.*stop|自动.*停)', content, re.IGNORECASE))
    scores["auto_stop"] = 1.0 if has_timeout else 0.0

    # Correct mPython API
    api_checks = [
        "MPythonPin" in content,
        "PinMode" in content,
        "read_analog" in content,
        "oled" in content,
        "button_a" in content,
    ]
    scores["correct_mpython_api"] = sum(api_checks) / len(api_checks)

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
