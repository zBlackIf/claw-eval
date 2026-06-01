"""Hidden verifier for CP104_game_buyout_competitive_analysis.

Checks the generated report.md for:
1. Statistical completeness (min/median/max/mean/count present per region)
2. Region mapping correctness (中国台湾 mapped to 港台)
3. Theme segmentation analysis
4. 策定九州 prediction with data-backed reasoning
5. First-month ratio analysis
6. HIDDEN: Cross-source data integration (combined product + competitor stats)
7. HIDDEN: Channel-level breakdown (Google Play vs iOS separate stats)
"""

import json
import os
import re
import sys


def check_report():
    report_path = "/workspace/report.md"
    results = {
        "checks": {},
        "overall_score": 0.0,
    }

    if not os.path.exists(report_path):
        results["checks"]["file_exists"] = False
        print(json.dumps(results))
        return

    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    results["checks"]["file_exists"] = True

    # --- Check 1: Report has meaningful length (not stub) ---
    word_count = len(content)
    results["checks"]["meaningful_length"] = word_count > 1500

    # --- Check 2: Statistical values present (min/median/max/mean/count) ---
    stat_keywords = ["最小值", "中位数", "最大值", "平均", "样本"]
    alt_stat_keywords = ["min", "median", "max", "mean", "count"]
    stat_found = sum(1 for kw in stat_keywords if kw in content)
    alt_stat_found = sum(1 for kw in alt_stat_keywords if kw.lower() in content.lower())
    stats_score = min((stat_found + alt_stat_found) / 5.0, 1.0)
    results["checks"]["stats_present"] = stats_score >= 0.8
    results["checks"]["stats_score"] = round(stats_score, 3)

    # --- Check 3: All regions covered ---
    regions = ["日韩", "东南亚", "港台"]
    # Also check if they used the source naming
    alt_regions = ["日本", "韩国", "中国台湾"]
    region_score = 0
    for r in regions:
        if r in content:
            region_score += 1
    # If they mapped properly, 日韩/东南亚/港台 should all appear
    results["checks"]["regions_covered"] = region_score >= 3
    results["checks"]["region_score"] = region_score / 3.0

    # --- Check 4: Channel breakdown (Google Play + iOS separately) ---
    has_google = "Google Play" in content or "Google" in content or "GP" in content or "google" in content.lower()
    has_ios = "iOS" in content or "ios" in content.lower() or "Apple" in content
    channel_breakdown = has_google and has_ios
    results["checks"]["channel_breakdown"] = channel_breakdown

    # --- Check 5: Theme/genre segmentation ---
    themes = ["三国", "军事", "科幻", "文明", "末日", "欧美历史"]
    theme_count = sum(1 for t in themes if t in content)
    # At minimum should distinguish 三国 from others
    results["checks"]["theme_segmentation"] = theme_count >= 3
    results["checks"]["theme_count"] = theme_count

    # --- Check 6: 策定九州 prediction section ---
    has_cedingjiuzhou = "策定九州" in content
    # Check for prediction methodology - should reference comparable data
    prediction_keywords = ["预估", "预测", "范围", "区间", "参考", "依据", "对标", "comparable", "类比"]
    prediction_method_score = sum(1 for kw in prediction_keywords if kw in content)
    has_prediction_reasoning = prediction_method_score >= 2
    results["checks"]["cedingjz_prediction"] = has_cedingjiuzhou and has_prediction_reasoning
    results["checks"]["prediction_method_score"] = min(prediction_method_score / 3.0, 1.0)

    # --- Check 7: First-month ratio analysis (首月占比) ---
    ratio_keywords = ["首月", "占比", "比例", "ratio"]
    ratio_score = sum(1 for kw in ratio_keywords if kw in content.lower())
    has_ratio_analysis = ratio_score >= 2
    results["checks"]["first_month_ratio"] = has_ratio_analysis

    # --- Check 8 (HIDDEN): Actual numeric values that can only come from correct computation ---
    # The product data for 日韩 Google Play has: 185000, 120000, 95000, 160000 (新增)
    # Min should be 95000, Max should be 185000
    # Check if the report contains computed values (not raw data dumps)
    has_computed_numbers = False
    # Look for numbers in table format (suggesting actual computation)
    table_pattern = r'\|[^|]*\d[\d,.]+[^|]*\|'
    tables_found = len(re.findall(table_pattern, content))
    has_computed_numbers = tables_found >= 5
    results["checks"]["has_tables_with_numbers"] = has_computed_numbers
    results["checks"]["table_count"] = tables_found

    # --- Check 9 (HIDDEN): Cross-source integration ---
    # Report should mention both own products AND competitors in same analysis
    has_own = any(name in content for name in ["战地无疆", "荣耀新三国", "铁甲雄兵", "星际远征"])
    has_competitor = any(name in content for name in ["三国志战略版", "率土之滨", "Rise of Kingdoms", "Last War", "Whiteout Survival", "Evony"])
    cross_source = has_own and has_competitor
    results["checks"]["cross_source_integration"] = cross_source

    # --- Check 10 (HIDDEN): Region mapping awareness ---
    # Agent should explicitly acknowledge 中国台湾=港台 mapping or show merged data
    region_mapping_aware = (
        ("中国台湾" in content and "港台" in content)
        or "对应" in content
        or "映射" in content
        or "合并" in content
        or "等同" in content
    )
    results["checks"]["region_mapping_aware"] = region_mapping_aware

    # --- Check 11 (HIDDEN): Buying strategy insight ---
    # Should produce actual strategic insight, not just raw numbers
    strategy_keywords = ["策略", "节奏", "差异", "前置", "后置", "集中", "分散", "激进", "保守", "买量"]
    strategy_score = sum(1 for kw in strategy_keywords if kw in content)
    has_strategy_insight = strategy_score >= 3
    results["checks"]["strategy_insight"] = has_strategy_insight
    results["checks"]["strategy_keyword_count"] = strategy_score

    # --- Compute overall score ---
    weights = {
        "meaningful_length": 0.05,
        "stats_present": 0.15,
        "regions_covered": 0.10,
        "channel_breakdown": 0.12,
        "theme_segmentation": 0.10,
        "cedingjz_prediction": 0.15,
        "first_month_ratio": 0.08,
        "has_tables_with_numbers": 0.08,  # HIDDEN
        "cross_source_integration": 0.07,  # HIDDEN
        "region_mapping_aware": 0.05,  # HIDDEN
        "strategy_insight": 0.05,  # HIDDEN
    }

    total = 0.0
    for key, weight in weights.items():
        val = results["checks"].get(key, False)
        if isinstance(val, bool):
            total += weight * (1.0 if val else 0.0)
        elif isinstance(val, (int, float)):
            total += weight * min(float(val), 1.0)

    results["overall_score"] = round(total, 4)
    print(json.dumps(results))


if __name__ == "__main__":
    check_report()
