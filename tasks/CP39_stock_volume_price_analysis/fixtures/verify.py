#!/usr/bin/env python3
"""In-container verifier for CP39_stock_volume_price_analysis.

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
            reader = csv.reader(io.StringIO(content))
            rows = list(reader)
            data_rows = [r for r in rows[1:] if r and r[0].strip()]
            scores["has_all_stocks"] = min(len(data_rows) / 3.0, 1.0)

            has_numeric = any(
                len(r) >= 2
                and r[1].strip().replace("-", "").replace(".", "").replace("e", "").isdigit()
                for r in data_rows
            ) if data_rows else False
            scores["has_correlation_values"] = 1.0 if has_numeric else 0.0
        except Exception:
            scores["has_all_stocks"] = 0.0
            scores["has_correlation_values"] = 0.0
    else:
        scores["results_created"] = 0.0
        scores["has_all_stocks"] = 0.0
        scores["has_correlation_values"] = 0.0

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
    else:
        scores["summary_has_stock_info"] = 0.0

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
