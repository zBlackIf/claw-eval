"""Hidden verifier for CP196 — API Response Classify & Report Generation."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def grade_workspace(ws: Path) -> dict:
    # Try primary path first, then fallback
    data_dir = ws / "fixtures" / "intelligence_data"
    if not data_dir.exists():
        data_dir = ws / "intelligence_data"

    components = {k: 0.0 for k in [
        "script_exists",
        "script_runs",
        "report_generated",
        "date_grouping",
        "category_classification",
        "statistics_section",
        "highlights_section",
        "content_truncation",
        "nested_date_category_structure",
        "truncation_precision",
        "statistics_completeness",
        "semantic_reclassification",
        "date_order_correctness",
        "top5_accuracy",
    ]}

    # 1. Check script exists
    script_file = None
    for candidate in [
        data_dir / "generate_report.py",
        ws / "generate_report.py",
        ws / "fixtures" / "generate_report.py",
    ]:
        if candidate.exists():
            script_file = candidate
            break

    if not script_file:
        # Search recursively
        for p in ws.rglob("generate_report.py"):
            script_file = p
            break

    if script_file and script_file.exists():
        components["script_exists"] = 1.0
    else:
        return {
            "overall_score": 0.0,
            "components": components,
            "weights": _weights(),
            "error": "generate_report.py not found",
        }

    # 2. Try to run the script
    script_content = _read(script_file)
    has_json_import = "import json" in script_content or "from json" in script_content
    has_file_read = "open(" in script_content and "json" in script_content.lower()
    has_classify = any(kw in script_content for kw in ["classify", "categorize", "category", "labelName"])
    has_groupby = any(kw in script_content for kw in ["group", "defaultdict", "date", "createTime"])
    has_write = any(kw in script_content for kw in ["write(", "report", ".md"])

    if has_json_import and has_file_read:
        components["script_runs"] = 0.5
        if has_classify and has_groupby and has_write:
            components["script_runs"] = 1.0
        elif has_write:
            components["script_runs"] = 0.7

    # 3. Check if report was generated (try running the script)
    report_file = None
    import subprocess
    try:
        cwd = script_file.parent.resolve()
        script_abs = script_file.resolve()
        result = subprocess.run(
            [sys.executable, str(script_abs)],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            components["script_runs"] = 1.0
    except Exception:
        pass

    # Look for report.md
    for candidate in [
        script_file.parent / "report.md",
        data_dir / "report.md",
        ws / "report.md",
        ws / "fixtures" / "report.md",
    ]:
        if candidate.exists():
            report_file = candidate
            break

    if not report_file:
        for p in ws.rglob("report.md"):
            report_file = p
            break

    if report_file and report_file.exists():
        report_content = _read(report_file)
        if len(report_content) > 100:
            components["report_generated"] = 1.0
        elif len(report_content) > 0:
            components["report_generated"] = 0.5
    else:
        # If script didn't produce report.md, score is partial
        components["report_generated"] = 0.0
        return {
            "overall_score": _compute_overall(components),
            "components": {k: round(v, 4) for k, v in components.items()},
            "weights": _weights(),
            "error": "report.md not generated",
        }

    report_content = _read(report_file)

    # 4. Check date grouping (dates should appear as structural headers, not just in content)
    dates_found = []
    dates_as_headers = 0
    for date_str in ["2026-05-18", "2026-05-17", "2026-05-16", "2026-05-15", "2026-05-14", "2026-05-13"]:
        if date_str in report_content:
            dates_found.append(date_str)
            # Check if date appears as a header (## date or # date or **date**)
            for line in report_content.split("\n"):
                if date_str in line and (line.strip().startswith("#") or line.strip().startswith("**")):
                    dates_as_headers += 1
                    break

    if dates_as_headers >= 5:
        components["date_grouping"] = 1.0
    elif dates_as_headers >= 3:
        components["date_grouping"] = 0.7
    elif len(dates_found) >= 5 and dates_as_headers >= 1:
        components["date_grouping"] = 0.5
    elif len(dates_found) >= 3:
        components["date_grouping"] = 0.3
    else:
        components["date_grouping"] = 0.0

    # 5. Check category classification
    macro_keywords = ["大盘/宏观", "大盘", "宏观"]
    industry_keywords = ["行业/产业"]
    stock_keywords = ["个股/公司", "个股"]

    def has_structural_category(keywords, text):
        for line in text.split("\n"):
            stripped = line.strip()
            if any(kw in stripped for kw in keywords):
                if stripped.startswith("#") or stripped.startswith("**") or stripped.startswith("-"):
                    return True
        return False

    has_macro = has_structural_category(macro_keywords, report_content)
    has_industry = has_structural_category(industry_keywords, report_content)
    has_stock = has_structural_category(stock_keywords, report_content)

    cat_score = sum([has_macro, has_industry, has_stock]) / 3.0

    if cat_score < 0.5:
        label_names = ["即时情报", "公司动态", "行业产业", "宏观数据"]
        structural_label_count = sum(1 for ln in label_names if has_structural_category([ln], report_content))
        cat_score = max(cat_score, structural_label_count / 4.0 * 0.7)

    components["category_classification"] = round(cat_score, 4)

    # 6. Statistics section
    has_stats = False
    stats_section_kw = ["统计", "summary", "overview", "汇总", "概览", "总览"]

    for line in report_content.split("\n"):
        stripped = line.strip().lower()
        if stripped.startswith("#") and any(s in stripped for s in stats_section_kw):
            has_stats = True
            break

    if not has_stats:
        has_total = bool(re.search(r"(38|三十八)\s*条", report_content))
        has_date_counts = sum(1 for d in ["2026-05-18", "2026-05-17", "2026-05-16"]
                             if re.search(rf"{d}[^#\n]*\d+\s*条", report_content))
        if has_total or has_date_counts >= 2:
            has_stats = True

    components["statistics_section"] = 1.0 if has_stats else 0.0

    # 7. Key highlights section
    has_highlight_header = False
    highlight_header_kw = ["highlight", "重点", "热门", "top", "Top", "TOP", "最热", "高关注", "key", "Key"]
    for line in report_content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#") and any(kw in stripped for kw in highlight_header_kw):
            has_highlight_header = True
            break

    top_items = ["寒武纪", "宁德时代", "美联储", "华为昇腾", "苹果WWDC"]
    top_mentioned = sum(1 for item in top_items if item in report_content)

    if has_highlight_header and top_mentioned >= 3:
        components["highlights_section"] = 1.0
    elif has_highlight_header and top_mentioned >= 1:
        components["highlights_section"] = 0.7
    elif has_highlight_header:
        components["highlights_section"] = 0.5
    elif top_mentioned >= 4:
        components["highlights_section"] = 0.3
    else:
        components["highlights_section"] = 0.0

    # 8. Content truncation — basic check (are lines reasonably short?)
    lines = report_content.split("\n")
    content_lines = [l for l in lines if not l.startswith("#") and not l.startswith("|")
                     and not l.startswith("---") and l.strip()]
    long_content_lines = [l for l in content_lines if len(l) > 180]
    has_paragraph_breaks = report_content.count("\n\n") > 60

    if len(long_content_lines) == 0 and not has_paragraph_breaks:
        components["content_truncation"] = 1.0
    elif len(long_content_lines) <= 3:
        components["content_truncation"] = 0.7
    elif len(long_content_lines) <= 8:
        components["content_truncation"] = 0.4
    else:
        components["content_truncation"] = 0.0

    # =========================================================================
    # HIDDEN CHECK 8b: Nested date→category structure
    # The prompt says "正文按日期分节，每个日期内再按分类分组". This requires a NESTED
    # hierarchy: date headers at one level, category sub-headers inside each date.
    # Many models flatten the structure (all dates then all categories, or vice versa).
    # We verify the report has category sub-headers BETWEEN consecutive date headers.
    # =========================================================================
    expected_dates_desc = ["2026-05-18", "2026-05-17", "2026-05-16", "2026-05-15", "2026-05-14", "2026-05-13"]
    date_header_lines = []
    category_sub_lines = []
    all_lines = report_content.split("\n")

    for i, line in enumerate(all_lines):
        stripped = line.strip()
        # Identify date headers (## 2026-05-18 or similar)
        if any(d in stripped for d in expected_dates_desc):
            if stripped.startswith("#") or stripped.startswith("**"):
                date_header_lines.append(i)
        # Identify category sub-headers within report body
        cat_kws = ["大盘", "宏观", "行业", "产业", "个股", "公司"]
        if any(ck in stripped for ck in cat_kws):
            if stripped.startswith("#") or stripped.startswith("**") or stripped.startswith("###"):
                category_sub_lines.append(i)

    # For proper nesting: between consecutive date headers, there should be
    # at least 1 category sub-header (ideally 2-3 for the 3 categories)
    nested_count = 0
    if len(date_header_lines) >= 4:
        for idx in range(len(date_header_lines) - 1):
            start = date_header_lines[idx]
            end = date_header_lines[idx + 1]
            cats_between = [c for c in category_sub_lines if start < c < end]
            if len(cats_between) >= 2:
                nested_count += 1

        if nested_count >= 4:
            components["nested_date_category_structure"] = 1.0
        elif nested_count >= 3:
            components["nested_date_category_structure"] = 0.7
        elif nested_count >= 2:
            components["nested_date_category_structure"] = 0.4
        elif nested_count >= 1:
            components["nested_date_category_structure"] = 0.2
        else:
            components["nested_date_category_structure"] = 0.0
    elif len(date_header_lines) >= 2 and len(category_sub_lines) >= 2:
        # Partial structure
        components["nested_date_category_structure"] = 0.2
    else:
        components["nested_date_category_structure"] = 0.0

    # =========================================================================
    # HIDDEN CHECK 8c: Truncation precision (exactly 150 chars, not approximate)
    # The prompt specifies "截断到 150 字符以内". We verify that specific LONG items
    # from the data (whose content exceeds 150 chars) are actually truncated in the
    # report, and that the truncation boundary is close to 150 (not 100 or 200).
    # =========================================================================
    # Known long items (content > 150 chars in original data):
    # post_005: "产业还在爆发..." (168 chars)
    # post_006: "半导体设备国产化率跟踪更新..." (154 chars)
    # post_016: "4月社融数据点评..." (116 chars — actually fits)
    # post_027: "美联储5月议息会议纪要要点..." (133 chars — borderline)
    # post_004: "CPO板块多个细分环节..." (138 chars)
    # post_001: "网传：传内蒙新疆限电..." (115 chars)
    # post_024: "存储芯片行业跟踪：DRAM..." (128 chars)
    # Check a few items that are clearly > 150 chars in original

    # Actual long contents from the JSON:
    long_items_content_prefix = {
        "产业还在爆发": "产业还在爆发——把握5-7月中美超强β",  # post_005, 168+ chars
        "半导体设备国产化率": "半导体设备国产化率跟踪更新",  # post_006, 154+ chars
        "央行今日开展1000亿元MLF": "央行今日开展1000亿元MLF操作",  # post_007, 115 chars — might not need truncation
        "CPO板块多个细分环节": "CPO板块多个细分环节订单口径同步上修",  # post_004, 138+ chars
    }

    # For items with content > 150 chars, verify they appear truncated in report
    # post_005 full content has 168 chars; post_006 has 154 chars
    # If they appear in the report at full length, truncation was not applied
    truncation_score = 0.0
    truncation_checks = 0
    truncation_passes = 0

    # post_005: last part "在最确定的方向上加大仓位" should be cut or "核心方向：算力基建、光模块、PCB载板" should be cut
    post005_full_tail = "核心方向：算力基建、光模块、PCB载板"
    post005_mid = "在最确定的方向上加大仓位"
    # If both tail phrases appear, content was NOT truncated
    if "产业还在爆发" in report_content:
        truncation_checks += 1
        if post005_full_tail not in report_content:
            truncation_passes += 1
        elif post005_mid in report_content and post005_full_tail in report_content:
            # Full content present — no truncation
            pass
        else:
            truncation_passes += 0.5

    # post_006: full content ends with "整体半导体设备国产化率已突破30%"
    post006_full_tail = "整体半导体设备国产化率已突破30%"
    if "半导体设备国产化率" in report_content:
        truncation_checks += 1
        if post006_full_tail not in report_content:
            truncation_passes += 1

    # post_004: full content ends with "重点关注：中际旭创、天孚通信、新易盛"
    post004_full_tail = "重点关注：中际旭创、天孚通信、新易盛"
    if "CPO板块" in report_content:
        truncation_checks += 1
        if post004_full_tail not in report_content:
            truncation_passes += 1

    # Also check that a truncation indicator exists (ellipsis ... or …)
    has_ellipsis = "..." in report_content or "…" in report_content

    if truncation_checks >= 2:
        ratio = truncation_passes / truncation_checks
        if ratio >= 0.9 and has_ellipsis:
            truncation_score = 1.0
        elif ratio >= 0.7 and has_ellipsis:
            truncation_score = 0.8
        elif ratio >= 0.7:
            truncation_score = 0.6
        elif ratio >= 0.5:
            truncation_score = 0.4
        else:
            truncation_score = 0.1
    elif truncation_checks == 1 and truncation_passes >= 1:
        truncation_score = 0.5
    else:
        truncation_score = 0.0

    components["truncation_precision"] = round(truncation_score, 4)

    # =========================================================================
    # HIDDEN CHECK 8d: Statistics completeness
    # The prompt requires "统计汇总（总条数、各日期条数、各分类条数）".
    # Many models only include SOME of these. We verify ALL THREE are present:
    # 1) Total count (38 items)
    # 2) Per-date breakdown (6 dates with counts)
    # 3) Per-category breakdown (3 categories with counts)
    # =========================================================================
    stats_completeness_score = 0.0

    # 1) Total count: must mention 38
    has_total_38 = bool(re.search(r"(38|三十八)", report_content))

    # 2) Per-date counts: at least 4 dates should have associated counts
    per_date_count = 0
    for date_str in expected_dates_desc:
        # Look for patterns like "2026-05-18: 10条" or "2026-05-18（10）" etc.
        if re.search(rf"{date_str}[^\n]{{0,30}}\d+\s*(条|篇|项)", report_content):
            per_date_count += 1
        elif re.search(rf"\d+\s*(条|篇|项)[^\n]{{0,20}}{date_str}", report_content):
            per_date_count += 1

    has_per_date = per_date_count >= 4

    # 3) Per-category counts: the 3 categories should each have a count
    cat_count_patterns = [
        (["大盘", "宏观"], r"(大盘|宏观)[^\n]{0,30}\d+\s*(条|篇|项)"),
        (["行业", "产业"], r"(行业|产业)[^\n]{0,30}\d+\s*(条|篇|项)"),
        (["个股", "公司"], r"(个股|公司)[^\n]{0,30}\d+\s*(条|篇|项)"),
    ]
    per_category_count = 0
    for keywords, pattern in cat_count_patterns:
        if re.search(pattern, report_content):
            per_category_count += 1
        else:
            # Try reverse pattern: "12条 宏观"
            for kw in keywords:
                if re.search(rf"\d+\s*(条|篇|项)[^\n]{{0,20}}{kw}", report_content):
                    per_category_count += 1
                    break

    has_per_category = per_category_count >= 2

    # Score based on how many of the 3 requirements are met
    met_count = sum([has_total_38, has_per_date, has_per_category])
    if met_count == 3:
        stats_completeness_score = 1.0
    elif met_count == 2:
        stats_completeness_score = 0.5
    elif met_count == 1:
        stats_completeness_score = 0.2
    else:
        stats_completeness_score = 0.0

    components["statistics_completeness"] = round(stats_completeness_score, 4)

    # =========================================================================
    # HIDDEN CHECK 9: Semantic reclassification quality
    # The task explicitly says "原始数据的 labelName 只是粗分类，你需要根据内容关键词做更精准的归类"
    # We check that the script performs ACTUAL content-based reclassification,
    # not just a passthrough of the original labelName field.
    # =========================================================================

    # Check 9a: The script must contain keyword-based classification logic
    # (not just mapping labelName directly to the 3 categories)
    has_content_keywords = False
    # Must reference actual content keywords for semantic classification
    macro_content_kw = ["央行", "MLF", "LPR", "CPI", "PPI", "降息", "社融", "美联储", "资金面", "货币"]
    industry_content_kw = ["国产化率", "出货量", "产业链", "市占率", "行业跟踪", "渗透率"]
    stock_content_kw = ["公司", "订单", "量产", "出货", "营收", "业绩"]

    # Count how many semantic keywords appear in the script (indicating real classification logic)
    macro_in_script = sum(1 for kw in macro_content_kw if kw in script_content)
    industry_in_script = sum(1 for kw in industry_content_kw if kw in script_content)
    stock_in_script = sum(1 for kw in stock_content_kw if kw in script_content)

    # Strong signal: script has keywords from all 3 categories
    if macro_in_script >= 3 and industry_in_script >= 2 and stock_in_script >= 2:
        has_content_keywords = True

    # Check 9b: In the report, verify specific items are correctly reclassified
    # post_007 "央行今日开展1000亿元MLF操作" -> should be 大盘/宏观
    # post_011 "今日A股资金面" -> should be 大盘/宏观
    # post_021 "宁德时代：麒麟电池2.0" -> should be 个股/公司
    # post_006 "半导体设备国产化率跟踪" -> should be 行业/产业

    # We look at how items are placed relative to category headers in the report
    # Extract sections between category headers and check item placement
    reclass_score = 0.0

    # Check if MLF/央行 item appears under 宏观 category (not under 即时情报)
    mlf_under_macro = _item_under_category(report_content, "MLF", ["宏观", "大盘"])
    catl_under_stock = _item_under_category(report_content, "宁德时代", ["个股", "公司"])
    semi_under_industry = _item_under_category(report_content, "国产化率", ["行业", "产业"])
    funds_under_macro = _item_under_category(report_content, "资金面", ["宏观", "大盘"])

    placement_hits = sum([mlf_under_macro, catl_under_stock, semi_under_industry, funds_under_macro])

    if has_content_keywords and placement_hits >= 3:
        reclass_score = 1.0
    elif has_content_keywords and placement_hits >= 2:
        reclass_score = 0.7
    elif has_content_keywords or placement_hits >= 3:
        reclass_score = 0.5
    elif placement_hits >= 2:
        reclass_score = 0.3
    else:
        reclass_score = 0.0

    components["semantic_reclassification"] = round(reclass_score, 4)

    # =========================================================================
    # HIDDEN CHECK 10: Date ordering correctness (new -> old)
    # The task specifies "按日期（新→旧）分组". We verify structural date headers
    # appear in descending order.
    # =========================================================================
    date_header_positions = []
    expected_dates_desc = ["2026-05-18", "2026-05-17", "2026-05-16", "2026-05-15", "2026-05-14", "2026-05-13"]

    for i, line in enumerate(report_content.split("\n")):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("**"):
            for d in expected_dates_desc:
                if d in stripped:
                    date_header_positions.append((i, d))
                    break

    if len(date_header_positions) >= 4:
        # Check ordering: positions should correspond to descending dates
        dates_in_order = [d for _, d in date_header_positions]
        # Remove duplicates while preserving order
        seen = set()
        unique_dates = []
        for d in dates_in_order:
            if d not in seen:
                seen.add(d)
                unique_dates.append(d)

        # Check if unique_dates is in descending order
        is_descending = all(unique_dates[i] >= unique_dates[i+1] for i in range(len(unique_dates)-1))
        # Also check it's NOT ascending (some might just list them alphabetically which happens to be descending)
        is_ascending = all(unique_dates[i] <= unique_dates[i+1] for i in range(len(unique_dates)-1))

        if is_descending and not is_ascending and len(unique_dates) >= 5:
            components["date_order_correctness"] = 1.0
        elif is_descending and len(unique_dates) >= 4:
            components["date_order_correctness"] = 0.7
        elif is_descending:
            components["date_order_correctness"] = 0.5
        else:
            components["date_order_correctness"] = 0.0
    elif len(date_header_positions) >= 2:
        dates_in_order = [d for _, d in date_header_positions]
        seen = set()
        unique_dates = []
        for d in dates_in_order:
            if d not in seen:
                seen.add(d)
                unique_dates.append(d)
        is_descending = all(unique_dates[i] >= unique_dates[i+1] for i in range(len(unique_dates)-1))
        components["date_order_correctness"] = 0.3 if is_descending else 0.0
    else:
        components["date_order_correctness"] = 0.0

    # =========================================================================
    # HIDDEN CHECK 11: Top 5 accuracy
    # The correct top 5 by views (from fixture data):
    #   1. 宁德时代 (15678) / 寒武纪 (15678) — tied
    #   2. 美联储 (14567)
    #   3. 华为昇腾 (12345) / 苹果WWDC (12345) — tied
    # We check that the highlight section contains exactly these 5 and includes
    # view counts, and that items outside top5 don't appear in the section.
    # =========================================================================
    top5_score = 0.0

    # Find the highlights section content (between its header and next section header)
    highlight_section_text = _extract_section(report_content, highlight_header_kw)

    if highlight_section_text:
        # All 5 must be present
        correct_top5 = ["寒武纪", "宁德时代", "美联储", "华为昇腾", "苹果WWDC"]
        # Items that should NOT be in top5 (next highest is 美国商务部/出口管制 at 9876, CPI at 9876)
        not_top5 = ["蔚蓝锂芯", "长川科技", "瑞可达"]

        present_correct = sum(1 for item in correct_top5 if item in highlight_section_text)
        present_wrong = sum(1 for item in not_top5 if item in highlight_section_text)

        # Check if view counts are shown
        has_view_counts = bool(re.search(r"(15678|14567|12345)", highlight_section_text))

        # Check count is exactly 5 (not top 3 or top 10)
        # Count numbered items or bullet items in the section
        bullet_lines = [l for l in highlight_section_text.split("\n")
                       if l.strip() and (l.strip().startswith("-") or l.strip().startswith("*")
                                         or re.match(r"\d+[\.\)、]", l.strip()))]
        count_is_five = 4 <= len(bullet_lines) <= 6

        if present_correct == 5 and present_wrong == 0 and has_view_counts and count_is_five:
            top5_score = 1.0
        elif present_correct == 5 and present_wrong == 0 and has_view_counts:
            top5_score = 0.8
        elif present_correct == 5 and present_wrong == 0:
            top5_score = 0.6
        elif present_correct >= 4:
            top5_score = 0.4
        elif present_correct >= 3:
            top5_score = 0.2
        else:
            top5_score = 0.0
    else:
        top5_score = 0.0

    components["top5_accuracy"] = round(top5_score, 4)

    return {
        "overall_score": round(_compute_overall(components), 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": _weights(),
    }


def _item_under_category(report_content: str, item_keyword: str, category_keywords: list) -> bool:
    """Check if an item appears under the correct category header in the report.

    Looks backward from the item's position to find the nearest category header.
    Returns True if the nearest category header contains one of the expected category keywords.
    """
    lines = report_content.split("\n")
    item_line_idx = None

    for i, line in enumerate(lines):
        if item_keyword in line:
            item_line_idx = i
            break

    if item_line_idx is None:
        return False

    # Look backward for the nearest category-level header (### or bold marker)
    for j in range(item_line_idx - 1, -1, -1):
        stripped = lines[j].strip()
        # Category headers are typically ### or #### level, or bold text
        if stripped.startswith("#") or stripped.startswith("**"):
            # Check if this header contains any of the expected category keywords
            if any(ck in stripped for ck in category_keywords):
                return True
            # If we hit a header that is a date header or different category, stop
            if re.search(r"2026-05-\d{2}", stripped):
                # It's a date header, keep looking up
                continue
            # It's a different category header — wrong placement
            return False

    return False


def _extract_section(report_content: str, header_keywords: list) -> str:
    """Extract text content of the section that matches one of the header keywords."""
    lines = report_content.split("\n")
    start_idx = None
    header_level = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") and any(kw in stripped for kw in header_keywords):
            start_idx = i
            header_level = len(stripped) - len(stripped.lstrip("#"))
            break

    if start_idx is None:
        return ""

    # Find the end of this section (next header at same or higher level)
    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("#"):
            current_level = len(stripped) - len(stripped.lstrip("#"))
            if current_level <= header_level:
                end_idx = i
                break

    return "\n".join(lines[start_idx:end_idx])


def _weights() -> dict:
    return {
        "script_exists": 0.03,
        "script_runs": 0.05,
        "report_generated": 0.05,
        "date_grouping": 0.05,
        "category_classification": 0.05,
        "statistics_section": 0.04,
        "highlights_section": 0.04,
        "content_truncation": 0.04,
        "nested_date_category_structure": 0.15,
        "truncation_precision": 0.12,
        "statistics_completeness": 0.10,
        "semantic_reclassification": 0.15,
        "date_order_correctness": 0.05,
        "top5_accuracy": 0.08,
    }


def _compute_overall(components: dict) -> float:
    w = _weights()
    return sum(w.get(k, 0) * components.get(k, 0) for k in w)


def main():
    # Try the standard workspace path first
    ws = Path("/workspace")
    if not ws.exists():
        ws = Path(".")

    # Check both possible locations
    fixture_dir = ws / "fixtures" / "intelligence_data"
    if not fixture_dir.exists():
        fixture_dir = ws / "intelligence_data"
    if not fixture_dir.exists():
        # Last resort
        fixture_dir = ws

    result = grade_workspace(ws)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
