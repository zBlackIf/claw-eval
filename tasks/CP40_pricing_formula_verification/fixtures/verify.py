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


def _expected_values() -> dict[tuple[str, str], float]:
    input_path = WORKSPACE / "fixtures" / "pricing_input.json"
    if not input_path.exists():
        input_path = WORKSPACE / "pricing_input.json"
    data = json.loads(input_path.read_text(encoding="utf-8"))
    params = data["parameters"]
    expected = {}
    for scenario in data["scenarios"]:
        scenario_name = scenario["name"]
        for tier in data["tiers"]:
            price = tier["price"]
            margin = params["gross_margin_targets"][str(price)]
            bonus_cost = params["bonus_feature_costs"][str(price)]
            sharing_ratio = scenario["bonus_sharing_ratio"]
            premium_ratio = params["model_premium_ratio"]
            ratio = (
                1 / (margin + 1)
                - 1 / (margin + 1) * (bonus_cost / price * (margin + 1))
                - sharing_ratio
            ) * (1 + premium_ratio) - 1
            expected[(scenario_name, str(price))] = ratio
    return expected


def _walk_numbers(obj, path=()):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from _walk_numbers(value, path + (str(key),))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from _walk_numbers(value, path + (str(index),))
    elif isinstance(obj, (int, float)):
        yield path, float(obj)
    elif isinstance(obj, str):
        for match in re.finditer(r"-?\d+(?:\.\d+)?", obj):
            yield path, float(match.group(0))


def _json_contains_ratio(data, scenario: str, tier: str, expected: float) -> bool:
    blob = json.dumps(data, ensure_ascii=False)
    if scenario not in blob or tier not in blob:
        return False
    for path, number in _walk_numbers(data):
        context = " ".join(path)
        if scenario not in context and tier not in context:
            node = data
            for part in path[:-1]:
                try:
                    node = node[int(part)] if isinstance(node, list) else node[part]
                except (KeyError, IndexError, ValueError, TypeError):
                    node = None
                    break
            context = json.dumps(node, ensure_ascii=False) if node is not None else context
        if scenario in context and tier in context and abs(number - expected) <= 0.01:
            return True
    return False


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
            expected = _expected_values()
            exact_hits = sum(
                1 for (scenario, tier), value in expected.items()
                if _json_contains_ratio(data, scenario, tier, value)
            )
            scores["golden_calculation_accuracy"] = exact_hits / len(expected)

            structure_blob = json.dumps(data, ensure_ascii=False)
            tiers_present = sum(1 for tier in TIER_PRICES if tier in structure_blob)
            scores["result_structure_complete"] = 0.5 * (scenarios_present / 3.0) + 0.5 * (tiers_present / 6.0)
        except (json.JSONDecodeError, UnicodeDecodeError):
            scores["three_scenario_output"] = 0.2
            scores["golden_calculation_accuracy"] = 0.0
            scores["result_structure_complete"] = 0.0
    else:
        scores["three_scenario_output"] = 0.0
        scores["golden_calculation_accuracy"] = 0.0
        scores["result_structure_complete"] = 0.0

    report_file = workspace / "compliance_report.md"
    if report_file.exists():
        report_text = report_file.read_text(errors="replace")
        has_pass_fail = bool(re.search(r"(PASS|FAIL)", report_text))
        constraints_found = sum(
            1 for kw in ["margin", "cost.?ratio", "monoton"]
            if re.search(kw, report_text, re.IGNORECASE)
        )
        scores["compliance_report"] = 0.3 * has_pass_fail + 0.7 * min(constraints_found / 3.0, 1.0)
        has_specific_violation = bool(re.search(r"(199|2999|6999|14999|49999|99999).*(FAIL|违规|violation)|"
                                                r"(FAIL|违规|violation).*(199|2999|6999|14999|49999|99999)",
                                                report_text, re.IGNORECASE | re.DOTALL))
        scores["violation_localized"] = 1.0 if has_specific_violation else 0.0
    else:
        scores["compliance_report"] = 0.0
        scores["violation_localized"] = 0.0

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
