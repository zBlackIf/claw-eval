#!/usr/bin/env python3
"""In-container verifier for CP39_stock_volume_price_analysis.

Ports the original automated_score() to a script that runs under
env_snapshot_commands. Emits one JSON line with per-component scores plus
overall_score = mean(components).
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
from pathlib import Path

WORKSPACE = Path("/workspace")
EXPECTED_CODES = {"sh.600519", "sz.000858", "sz.002304"}
EXPECTED_COLUMNS = [
    "code",
    "correlation",
    "avg_volume",
    "avg_price_change",
    "data_quality_notes",
]


def _numeric(value: str) -> bool:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return False
    return number == number and number not in (float("inf"), float("-inf"))


def automated_score(workspace: Path) -> dict[str, float]:
    scores = {}

    results_csv = workspace / "volume_price_results.csv"
    if not results_csv.exists():
        for f in workspace.glob("*.csv"):
            if "stock_data" not in str(f) and "result" in f.name.lower():
                results_csv = f
                break

    if results_csv.exists():
        scores["results_created"] = 1.0
        try:
            content = results_csv.read_text(encoding="utf-8")
            reader = csv.DictReader(io.StringIO(content))
            rows = [r for r in reader if r.get("code")]
            header = [h.strip() for h in (reader.fieldnames or [])]
            scores["schema_exact"] = 1.0 if header == EXPECTED_COLUMNS else 0.0

            codes = {str(r.get("code", "")).strip() for r in rows}
            scores["has_all_stocks"] = len(EXPECTED_CODES.intersection(codes)) / len(EXPECTED_CODES)

            corr_ok = sum(
                1
                for r in rows
                if str(r.get("code", "")).strip() in EXPECTED_CODES
                and _numeric(str(r.get("correlation", "")))
            )
            avg_ok = sum(
                1
                for r in rows
                if str(r.get("code", "")).strip() in EXPECTED_CODES
                and _numeric(str(r.get("avg_volume", "")))
                and _numeric(str(r.get("avg_price_change", "")))
            )
            scores["has_correlation_values"] = corr_ok / len(EXPECTED_CODES)
            scores["has_average_metrics"] = avg_ok / len(EXPECTED_CODES)

            notes_text = " ".join(str(r.get("data_quality_notes", "")) for r in rows).lower()
            scores["notes_missing_value"] = (
                1.0
                if any(k in notes_text for k in ["missing", "nan", "缺失", "空值", "dropped", "filled"])
                else 0.0
            )
        except Exception:
            scores["schema_exact"] = 0.0
            scores["has_all_stocks"] = 0.0
            scores["has_correlation_values"] = 0.0
            scores["has_average_metrics"] = 0.0
            scores["notes_missing_value"] = 0.0
    else:
        scores["results_created"] = 0.0
        scores["schema_exact"] = 0.0
        scores["has_all_stocks"] = 0.0
        scores["has_correlation_values"] = 0.0
        scores["has_average_metrics"] = 0.0
        scores["notes_missing_value"] = 0.0

    summary = workspace / "analysis_summary.txt"
    if not summary.exists():
        for f in workspace.glob("analysis*"):
            summary = f
            break
    scores["summary_created"] = 1.0 if summary.exists() else 0.0

    if summary.exists():
        sc = summary.read_text(encoding="utf-8")
        has_stock_mention = any(
            s in sc for s in ["600519", "002304", "000858", "茅台", "贵州"]
        )
        scores["summary_has_stock_info"] = 1.0 if has_stock_mention else 0.0
        scores["summary_mentions_missing"] = (
            1.0
            if re.search(r"missing|nan|缺失|空值|质量|quality", sc, re.IGNORECASE)
            else 0.0
        )
    else:
        scores["summary_has_stock_info"] = 0.0
        scores["summary_mentions_missing"] = 0.0

    all_text = ""
    for path in [results_csv, summary]:
        if path.exists():
            all_text += path.read_text(encoding="utf-8", errors="ignore").lower() + "\n"
    hallucinated = any(code in all_text for code in ["000001", "300750", "601318", "aapl", "tsla"])
    scores["no_ticker_hallucination"] = 0.0 if hallucinated else 1.0

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
