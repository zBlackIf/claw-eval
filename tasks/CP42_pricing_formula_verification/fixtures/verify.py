#!/usr/bin/env python3
"""In-container verifier for CP42_pricing_formula_verification.

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

TIER_PRICES = ["199", "2999", "6999", "14999", "49999", "99999"]
SCENARIOS = ["no_bonus", "kol_5pct", "producer_10pct"]


def automated_score(workspace: Path) -> dict[str, float]:
    scores = {}

    all_text = ""
    for f in workspace.rglob("*"):
        if f.is_file() and f.suffix in (".md", ".json", ".txt", ".py"):
            try:
                all_text += f.read_text(errors="replace") + "\n"
            except Exception:
                pass

    has_decimal = bool(re.search(r"0\.\s*4[0]?\b", all_text)) or bool(
        re.search(r"0\.\s*3[74]\b", all_text)
    )
    has_pct_error = bool(re.search(r"margin\s*[=:]\s*4[0]\b", all_text, re.IGNORECASE))
    scores["formula_decimal_conversion"] = 1.0 if has_decimal and not has_pct_error else 0.0

    tiers_found = sum(1 for t in TIER_PRICES if t in all_text)
    scores["calculation_completeness"] = min(tiers_found / 6.0, 1.0)

    has_mono = bool(re.search(
        r"(monoton|单调|递增|越高.*越多|violation|non-?increasing)", all_text, re.IGNORECASE
    ))
    scores["monotonicity_check"] = 1.0 if has_mono else 0.0

    result_file = workspace / "pricing_result.json"
    if result_file.exists():
        try:
            data = json.loads(result_file.read_text())
            scenarios_present = sum(
                1 for s in SCENARIOS if s in json.dumps(data)
            )
            scores["three_scenario_output"] = scenarios_present / 3.0
        except (json.JSONDecodeError, UnicodeDecodeError):
            scores["three_scenario_output"] = 0.2
    else:
        scores["three_scenario_output"] = 0.0

    report_file = workspace / "compliance_report.md"
    if report_file.exists():
        report_text = report_file.read_text(errors="replace")
        has_pass_fail = bool(re.search(r"(PASS|FAIL)", report_text))
        constraints_found = sum(
            1 for kw in ["margin", "cost.?ratio", "monoton"]
            if re.search(kw, report_text, re.IGNORECASE)
        )
        scores["compliance_report"] = 0.3 * has_pass_fail + 0.7 * min(constraints_found / 3.0, 1.0)
    else:
        scores["compliance_report"] = 0.0

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
