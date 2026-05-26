#!/usr/bin/env python3
"""In-container verifier for CP27_metro_station_population_profile.

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

REQUIRED_STATIONS = [
        "纪念堂", "西场", "松溪", "南漖", "广州东站", "白云城市中心",
        "秀全公园", "江高", "梓元岗", "凤浦公园", "远景", "槎头",
        "梅东路", "仓边路", "烈士陵园", "京溪路", "棠景"
    ]
EXISTING_STATIONS = ["岭南广场", "赤岗", "南浦西", "石牌南"]
DATA_CHECKS = [
        ("纪念堂", "1.59"),
        ("西场", "2.55"),
        ("江高", "69.08"),
        ("棠景", "4.56"),
        ("远景", "3.52"),
        ("凤浦公园", "0.54"),
        ("白云城市中心", "0.66"),
        ("广州东站", "49.10"),
    ]


def automated_score(workspace: Path) -> dict[str, float]:
    scores = {}

    output_file = workspace / "existing_stations_v4.txt"
    if not output_file.exists():
        return {
            "station_count": 0.0,
            "format_consistency": 0.0,
            "data_accuracy": 0.0,
            "existing_preserved": 0.0,
            "comparative_context": 0.0,
        }

    content = output_file.read_text(encoding="utf-8", errors="ignore")

    # Station count
    found_stations = sum(1 for s in REQUIRED_STATIONS if s in content)
    scores["station_count"] = min(1.0, found_stations / 17)

    # Format consistency
    section_markers = ["精炼描述", "人群构成", "出行特征", "设施需求", "建议"]
    marker_counts = [content.count(m) for m in section_markers]
    min_markers = min(marker_counts)
    if min_markers >= 17:
        scores["format_consistency"] = 1.0
    elif min_markers >= 12:
        scores["format_consistency"] = 0.75
    elif min_markers >= 8:
        scores["format_consistency"] = 0.5
    elif min_markers >= 4:
        scores["format_consistency"] = 0.25
    else:
        scores["format_consistency"] = 0.0

    # Data accuracy
    hits = 0
    for station, val in DATA_CHECKS:
        idx = content.find(station)
        if idx >= 0:
            section = content[idx:idx + 1000]
            if val in section:
                hits += 1
    scores["data_accuracy"] = hits / len(DATA_CHECKS)

    # Existing preserved
    preserved = sum(1 for s in EXISTING_STATIONS if s in content)
    scores["existing_preserved"] = preserved / len(EXISTING_STATIONS)

    # Comparative context
    comparison_terms = ["最高", "最低", "第二高", "前列", "居首", "偏低", "偏高",
                       "高于", "低于", "超过", "不及"]
    comp_hits = sum(1 for t in comparison_terms if t in content)
    scores["comparative_context"] = min(1.0, comp_hits / 5)

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
