#!/usr/bin/env python3
"""In-container verifier for CP49_quant_atr_ma_strategy_optimization.

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

    # Find the output file
    output_file = workspace / "strategy_optimized.py"
    if not output_file.exists():
        # Try alternative names
        for alt in ["strategy_fixed.py", "strategy.py"]:
            alt_path = workspace / alt
            if alt_path.exists():
                output_file = alt_path
                break

    if not output_file.exists():
        return {
            "output_created": 0.0,
            "rolling_fixed": 0.0,
            "no_bitwise_ops": 0.0,
            "signals_defined": 0.0,
            "no_custom_func": 0.0,
            "indicators_present": 0.0,
        }

    content = output_file.read_text()
    scores["output_created"] = 1.0
    try:
        compile(content, str(output_file), "exec")
        scores["syntax_valid"] = 1.0
    except SyntaxError:
        scores["syntax_valid"] = 0.0

    # Check rolling window is complete (not truncated)
    has_complete_rolling = bool(re.search(
        r'rolling\s*\(\s*window\s*=\s*\d+\s*\)', content
    ))
    has_truncated = "rolling(windo" in content and "window=" not in content
    scores["rolling_fixed"] = 1.0 if has_complete_rolling and not has_truncated else 0.0

    # Check no bitwise operators in entries/exits logic
    # Look for & or | used as logical operators (not in comments or strings)
    lines = content.split('\n')
    code_lines = [l for l in lines if not l.strip().startswith('#')]
    code_text = '\n'.join(code_lines)

    # Check for entries/exits definitions using bitwise
    entry_exit_section = re.findall(
        r'(entries|exits)\s*=\s*(.+?)(?:\n(?![ \t])|$)',
        code_text, re.DOTALL
    )
    has_bitwise = False
    for _, expr in entry_exit_section:
        if '&' in expr or '|' in expr or '~' in expr:
            has_bitwise = True
            break

    scores["no_bitwise_ops"] = 0.0 if has_bitwise else 1.0

    # Check entries and exits are defined
    has_entries = bool(re.search(r'^entries\s*=', content, re.MULTILINE))
    has_exits = bool(re.search(r'^exits\s*=', content, re.MULTILINE))
    scores["signals_defined"] = (
        0.5 * (1.0 if has_entries else 0.0)
        + 0.5 * (1.0 if has_exits else 0.0)
    )

    # Check no custom function definitions
    has_def = bool(re.search(r'^def\s+\w+\s*\(', content, re.MULTILINE))
    scores["no_custom_func"] = 0.0 if has_def else 1.0

    # Check technical indicators are present
    indicators = [
        r'atr|ATR',
        r'ma_short|ma_long|rolling.*mean',
        r'volume|成交量',
    ]
    found_indicators = sum(
        1 for p in indicators if re.search(p, content, re.IGNORECASE)
    )
    scores["indicators_present"] = min(found_indicators / 2.0, 1.0)

    negative_shift = bool(re.search(r"\.shift\s*\(\s*-\d+", content))
    future_terms = bool(re.search(r"future|未来|lookahead", content, re.IGNORECASE))
    scores["no_future_function"] = 0.0 if negative_shift or future_terms else 1.0

    try:
        import numpy as np
        import pandas as pd

        dates = pd.date_range("2026-01-01", periods=80, freq="D")
        base = np.linspace(100, 126, len(dates)) + np.sin(np.arange(len(dates)) / 2.5) * 2
        price_df = pd.DataFrame(
            {
                "open": base - 0.5,
                "high": base + 1.8,
                "low": base - 1.7,
                "close": base,
                "volume": 1000 + (np.arange(len(dates)) % 11) * 80,
            },
            index=dates,
        )
        namespace = {"price_df": price_df.copy(), "pd": pd, "np": np, "__name__": "__strategy_verify__"}
        exec(compile(content, str(output_file), "exec"), namespace)
        entries = namespace.get("entries")
        exits = namespace.get("exits")
        entries_ok = isinstance(entries, pd.Series) and entries.dtype == bool and len(entries) == len(price_df)
        exits_ok = isinstance(exits, pd.Series) and exits.dtype == bool and len(exits) == len(price_df)
        scores["strategy_executes_on_sample"] = 1.0
        scores["signals_are_bool_series"] = (float(entries_ok) + float(exits_ok)) / 2.0
        if entries_ok and exits_ok:
            nontrivial_entries = 0 < int(entries.fillna(False).sum()) < len(entries) * 0.8
            nontrivial_exits = 0 < int(exits.fillna(False).sum()) < len(exits) * 0.8
            scores["signals_nontrivial"] = (float(nontrivial_entries) + float(nontrivial_exits)) / 2.0
        else:
            scores["signals_nontrivial"] = 0.0
    except Exception:
        scores["strategy_executes_on_sample"] = 0.0
        scores["signals_are_bool_series"] = 0.0
        scores["signals_nontrivial"] = 0.0

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
