"""Hidden verifier for CP120 — SLG Game UA Data Analysis."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd


def find_report(ws: Path) -> Path | None:
    """Find the generated markdown report."""
    candidates = []
    for pattern in ["**/*.md", "**/*.markdown"]:
        for p in ws.rglob(pattern[3:]) if "**/" in pattern else [ws / pattern]:
            pass
        candidates.extend(ws.rglob(pattern.replace("**/", "")))

    # Search in multiple locations
    search_dirs = [ws / "fixtures" / "data", ws / "data", ws]
    for d in search_dirs:
        if d.exists():
            for f in d.rglob("*.md"):
                if f.name.lower() not in ("readme.md",):
                    candidates.append(f)

    # Also check for any .md files in workspace root
    for f in ws.iterdir():
        if f.suffix == ".md" and f.name.lower() != "readme.md":
            candidates.append(f)

    if not candidates:
        return None
    # Prefer the largest .md file (most likely the report)
    candidates = list(set(candidates))
    candidates.sort(key=lambda p: p.stat().st_size if p.exists() else 0, reverse=True)
    return candidates[0] if candidates else None


def load_product_data(ws: Path) -> pd.DataFrame | None:
    """Load product CSV data."""
    for path in [
        ws / "fixtures" / "data" / "product_data.csv",
        ws / "data" / "product_data.csv",
    ]:
        if path.exists():
            return pd.read_csv(path)
    return None


def load_competitor_data(ws: Path) -> pd.DataFrame | None:
    """Load competitor CSV data."""
    for path in [
        ws / "fixtures" / "data" / "competitor_data.csv",
        ws / "data" / "competitor_data.csv",
    ]:
        if path.exists():
            return pd.read_csv(path)
    return None


def check_statistics_by_region(report: str, product_df: pd.DataFrame, competitor_df: pd.DataFrame) -> float:
    """Check if statistics by region are present and roughly correct."""
    score = 0.0

    # Check that key regions are mentioned
    regions = ["日本", "韩国", "东南亚", "港台", "台湾"]
    region_count = sum(1 for r in regions if r in report)
    score += min(region_count / 4.0, 1.0) * 0.3

    # Check for statistical terms
    stat_terms = ["最小值", "中位数", "最大值", "平均", "样本量"]
    stat_count = sum(1 for t in stat_terms if t in report)
    score += min(stat_count / 5.0, 1.0) * 0.3

    # Check for channel breakdown (分渠道)
    channels = ["android", "ios", "合计"]
    channel_count = sum(1 for c in channels if c.lower() in report.lower())
    score += min(channel_count / 3.0, 1.0) * 0.2

    # Check that actual numbers are present (not fabricated)
    # Verify a known data point: 战地无疆日本 android 新增=61959
    if "61959" in report or "61,959" in report or "6.2万" in report or "62.0k" in report.lower():
        score += 0.1
    # Another known point: 枫之谷港台 ios 充值流水=25226367
    if "25226367" in report or "25,226,367" in report or "2522.6" in report or "2523" in report:
        score += 0.1

    return min(score, 1.0)


def check_theme_analysis(report: str, competitor_df: pd.DataFrame) -> float:
    """Check if theme/type analysis is present."""
    score = 0.0

    # Check for theme categories
    themes = ["三国", "日本战国", "多文明"]
    theme_count = sum(1 for t in themes if t in report)
    score += min(theme_count / 3.0, 1.0) * 0.4

    # Check for type categories
    types = ["率土", "ROK", "COK", "国战"]
    type_count = sum(1 for t in types if t.lower() in report.lower())
    score += min(type_count / 3.0, 1.0) * 0.3

    # Check that there's a comparison/differential analysis
    comparison_terms = ["差异", "对比", "高于", "低于", "优于", "表现"]
    comp_count = sum(1 for t in comparison_terms if t in report)
    score += min(comp_count / 3.0, 1.0) * 0.3

    return min(score, 1.0)


def check_prediction(report: str) -> float:
    """Check if prediction for 策定九州 entering new markets is present with reasoning."""
    score = 0.0

    # Must mention 策定九州
    if "策定九州" not in report:
        return 0.0
    score += 0.2

    # Must mention target regions
    target_regions = ["日韩", "日本", "韩国", "东南亚", "港台"]
    region_count = sum(1 for r in target_regions if r in report)
    score += min(region_count / 3.0, 1.0) * 0.2

    # Must have numerical range/interval
    range_patterns = [
        r'\d+\s*[-~～至到]\s*\d+',  # number range
        r'区间',
        r'范围',
        r'预估',
        r'预测',
    ]
    range_found = sum(1 for p in range_patterns if re.search(p, report))
    score += min(range_found / 2.0, 1.0) * 0.3

    # Must have reasoning/basis
    reasoning_terms = ["依据", "基于", "参考", "根据", "因为", "由于", "考虑"]
    reason_count = sum(1 for t in reasoning_terms if t in report)
    score += min(reason_count / 2.0, 1.0) * 0.3

    return min(score, 1.0)


def check_first_month_ratio(report: str, product_df: pd.DataFrame) -> float:
    """Check if first-month ratio analysis and UA strategy comparison is present."""
    score = 0.0

    # Check for ratio/proportion terms
    ratio_terms = ["占比", "比例", "百分比", "%"]
    ratio_count = sum(1 for t in ratio_terms if t in report)
    score += min(ratio_count / 2.0, 1.0) * 0.3

    # Check for first-month mention
    if "首月" in report:
        score += 0.2

    # Check for UA strategy analysis
    strategy_terms = ["买量", "策略", "投放", "获客", "用户获取"]
    strategy_count = sum(1 for t in strategy_terms if t in report)
    score += min(strategy_count / 2.0, 1.0) * 0.3

    # Check for comparison between product and competitor
    if ("产品" in report or "自研" in report) and ("竞品" in report or "竞争" in report):
        score += 0.2

    return min(score, 1.0)


def check_report_structure(report: str) -> float:
    """Check overall report quality and structure."""
    score = 0.0

    # Has markdown headers
    header_count = len(re.findall(r'^#{1,4}\s+', report, re.MULTILINE))
    score += min(header_count / 4.0, 1.0) * 0.25

    # Has tables (markdown tables)
    table_rows = len(re.findall(r'\|.*\|.*\|', report))
    score += min(table_rows / 5.0, 1.0) * 0.35

    # Reasonable length (at least 2000 chars for a proper report)
    length_score = min(len(report) / 3000.0, 1.0)
    score += length_score * 0.2

    # Has multiple sections covering 4 questions
    section_markers = ["问题1", "问题2", "问题3", "问题4", "一、", "二、", "三、", "四、",
                       "1.", "2.", "3.", "4.", "1、", "2、", "3、", "4、"]
    section_count = sum(1 for m in section_markers if m in report)
    score += min(section_count / 4.0, 1.0) * 0.2

    return min(score, 1.0)


def grade_workspace(ws: Path) -> dict:
    """Grade the analysis workspace."""
    components = {
        "region_statistics": 0.0,
        "theme_analysis": 0.0,
        "prediction_reasoning": 0.0,
        "first_month_ratio": 0.0,
        "report_structure": 0.0,
    }

    # Find and read the report
    report_path = find_report(ws)
    if not report_path:
        return {
            "overall_score": 0.0,
            "components": components,
            "error": "No markdown report file found in workspace",
        }

    try:
        report = report_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return {
            "overall_score": 0.0,
            "components": components,
            "error": f"Failed to read report: {e}",
        }

    if len(report.strip()) < 100:
        return {
            "overall_score": 0.0,
            "components": components,
            "error": "Report is too short (< 100 chars)",
        }

    # Load source data for validation
    product_df = load_product_data(ws)
    competitor_df = load_competitor_data(ws)

    if product_df is None or competitor_df is None:
        # Data files might have been moved, still grade based on report content
        product_df = pd.DataFrame()
        competitor_df = pd.DataFrame()

    # Grade each dimension
    components["region_statistics"] = check_statistics_by_region(report, product_df, competitor_df)
    components["theme_analysis"] = check_theme_analysis(report, competitor_df)
    components["prediction_reasoning"] = check_prediction(report)
    components["first_month_ratio"] = check_first_month_ratio(report, product_df)
    components["report_structure"] = check_report_structure(report)

    # Weighted overall score
    weights = {
        "region_statistics": 0.25,
        "theme_analysis": 0.20,
        "prediction_reasoning": 0.25,
        "first_month_ratio": 0.15,
        "report_structure": 0.15,
    }

    overall = sum(weights[k] * components[k] for k in weights)

    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "report_path": str(report_path),
        "report_length": len(report),
    }


def main():
    # Try multiple workspace paths
    ws = Path("/workspace/fixtures/data")
    if not ws.exists():
        ws = Path("/workspace/data")
    if not ws.exists():
        ws = Path("/workspace")

    result = grade_workspace(Path("/workspace"))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
