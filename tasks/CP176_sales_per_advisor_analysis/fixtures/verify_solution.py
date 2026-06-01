"""Hidden verifier for CP176 — Sales Per Advisor Analysis.

Tiered grading with strong discrimination:
  EASY tier (15%) — any agent that produces a file passes these fully.
  MEDIUM tier (20%) — requires reading the Excel and referencing real data.
  HARD tier (35%) — requires correct computation, paradox identification,
                     and cross-dimensional analysis.  Only strong agents pass.
  EXPERT tier (30%) — requires precise derived values that need multi-step
                       computation and analytical framing.

Hidden (HARD + EXPERT) >= 65% weight ensures discrimination.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def grade_workspace(ws: Path) -> dict:
    """Grade the workspace for the sales analysis task.

    Dimensions (tiered):
    --- EASY (15%) — all agents should pass ---
    1. report_exists (0.05) - Output file produced
    2. has_structure (0.05) - Report has headings + table
    3. basic_keywords (0.05) - Mentions categories, advisors, sales

    --- MEDIUM (20%) — requires actual data extraction ---
    4. data_referenced (0.10) - Monthly totals from Excel appear in report
    5. category_names (0.05) - All 6 product categories mentioned
    6. executive_summary (0.05) - Report begins with a quantified summary

    --- HARD (35%) — requires correct computation (hidden discriminator) ---
    7. correct_quarterly_totals (0.10) - Correctly summed quarterly aggregates
    8. advisor_reduction_pct (0.08) - Correct % decline in advisor headcount
    9. productivity_paradox (0.12) - Identifies total-down but per-capita-up
    10. monthly_per_capita (0.05) - Correct per-capita values for key months

    --- EXPERT (30%) — multi-step derived analysis (hidden discriminator) ---
    11. per_category_per_advisor (0.10) - Per-category per-advisor values
    12. yoy_precise_comparison (0.10) - Precise Q1 YoY with 3+ correct metrics
    13. paradox_framing_depth (0.10) - Explicit causal framing of the paradox
    """
    components = {k: 0.0 for k in [
        "report_exists",
        "has_structure",
        "basic_keywords",
        "data_referenced",
        "category_names",
        "executive_summary",
        "correct_quarterly_totals",
        "advisor_reduction_pct",
        "productivity_paradox",
        "monthly_per_capita",
        "per_category_per_advisor",
        "yoy_precise_comparison",
        "paradox_framing_depth",
    ]}

    # --- Find the report ---
    report_path = ws / "output" / "sales_analysis_report.md"
    if not report_path.exists():
        for alt in [
            ws / "fixtures" / "output" / "sales_analysis_report.md",
            ws / "sales_analysis_report.md",
            ws / "output" / "report.md",
        ]:
            if alt.exists():
                report_path = alt
                break

    if not report_path.exists():
        if (ws / "output").exists():
            for candidate in (ws / "output").rglob("*.md"):
                report_path = candidate
                break
        if not report_path.exists():
            return {
                "overall_score": 0.0,
                "components": components,
                "weights": _weights(),
                "error": "Report not found.",
            }

    components["report_exists"] = 1.0
    content = _read(report_path)
    content_lower = content.lower()

    # ===================================================================
    # EASY TIER (15%) — trivial, any agent that writes a file gets these
    # ===================================================================

    # 2. Has structure (headings + table)
    structure_score = 0.0
    if content.count("#") >= 2:
        structure_score += 0.5
    if "|" in content and "-" * 3 in content:
        structure_score += 0.5
    components["has_structure"] = min(1.0, structure_score)

    # 3. Basic keywords (very easy — just mention the domain)
    basic_kw = ["理财师", "销量", "产品", "人均"]
    kw_hits = sum(1 for k in basic_kw if k in content)
    components["basic_keywords"] = min(1.0, kw_hits / 3.0)

    # ===================================================================
    # MEDIUM TIER (20%) — requires actual data extraction from Excel
    # ===================================================================

    # 4. Data referenced — specific monthly totals from our fixture Excel
    monthly_totals_2025 = [8520, 7890, 9200, 8750, 9100, 8400, 8900, 9350, 8650, 9500, 8800, 7200]
    monthly_totals_2026 = [5100, 5450, 5800]
    advisor_counts = [156, 158, 155, 160, 162, 159, 157, 161, 152, 82, 85, 87]

    monthly_hits = sum(1 for n in monthly_totals_2025 + monthly_totals_2026 if str(n) in content)
    advisor_hits = sum(1 for n in advisor_counts if str(n) in content)
    # Need a mix of both to show genuine parsing
    data_score = min(0.6, monthly_hits / 10.0) + min(0.4, advisor_hits / 5.0)
    components["data_referenced"] = min(1.0, data_score)

    # 5. Category names — all 6 product categories mentioned
    categories = ["债券投资", "证券投资", "工商企业", "基础设施", "房地产", "政信类"]
    cat_found = sum(1 for c in categories if c in content)
    components["category_names"] = min(1.0, cat_found / 5.0)

    # 6. Executive summary with quantified claims
    first_1000 = content[:1000].lower()
    exec_markers = [
        any(k in first_1000 for k in ["摘要", "summary", "核心", "结论", "概要", "关键发现"]),
        bool(re.search(r"\d+\.?\d*%", content[:1000])),
        any(k in first_1000 for k in ["人均", "理财师"]),
    ]
    components["executive_summary"] = min(1.0, sum(exec_markers) / 2.5)

    # ===================================================================
    # HARD TIER (35%) — requires correct computation; discriminates
    # ===================================================================

    # 7. Correct quarterly totals (agent must sum monthly data)
    # Q1'25: 8520+7890+9200=25610, Q2'25: 8750+9100+8400=26250
    # Q3'25: 8900+9350+8650=26900, Q4'25: 9500+8800+7200=25500
    # Q1'26: 5100+5450+5800=16350
    quarterly_values = ["25610", "26250", "26900", "25500", "16350"]
    qt_hits = sum(1 for qt in quarterly_values if qt in content)
    components["correct_quarterly_totals"] = min(1.0, qt_hits / 3.0)

    # 8. Advisor headcount reduction — correct percentage
    # Pre-reduction avg ~157.5, post-reduction avg ~84.7 => ~46.2% decline
    # Or comparing Q1'25 avg (156.3) vs Q1'26 avg (84.7) => 45.8%
    # Accept 45-47% range as correct
    adv_pct_score = 0.0
    # Strict: exact or near-exact percentage
    if any(x in content for x in ["45.5%", "45.8%", "46%", "46.2%", "45.5", "45.8", "46.2"]):
        adv_pct_score = 1.0
    # Partial: approximate mentions
    elif any(x in content for x in ["45%", "46%", "约45", "约46", "近半", "接近一半"]):
        adv_pct_score = 0.6
    # Weak: just mentions the absolute numbers declining
    elif any(x in content for x in ["减少约70", "减少了70", "从156", "从157", "降至82", "降至85"]):
        adv_pct_score = 0.3
    components["advisor_reduction_pct"] = adv_pct_score

    # 9. Productivity paradox — THE key discriminator
    # Strong agents identify: total sales down ~36% BUT per-advisor up ~17%
    paradox_score = 0.0

    # Part A: mentions total sales decline with roughly correct %
    if any(x in content for x in ["36.1%", "36%", "36.1", "36.2"]):
        paradox_score += 0.2
    elif any(x in content_lower for x in ["总销量下降", "销量减少", "销量下滑", "总量下降"]):
        paradox_score += 0.1

    # Part B: mentions per-capita INCREASE with roughly correct %
    if any(x in content for x in ["17.2%", "17%", "17.1", "17.2"]):
        paradox_score += 0.3
    elif any(x in content_lower for x in ["人均提升", "人均增长", "人均提高", "人均销量增"]):
        paradox_score += 0.15

    # Part C: explicitly contrasts the two (the paradox itself)
    # This is the hardest part — weak agents report decline without the contrast
    contrast_patterns = [
        r"(下降|减少|下滑).{0,30}(人均|产能).{0,20}(提升|增长|提高|上升)",
        r"(人均|产能).{0,20}(提升|增长|提高).{0,30}(总[量销]|整体).{0,20}(下降|减少)",
        r"减员增效",
        r"(虽然|尽管).{0,40}(但|然而|却).{0,40}(人均|产能)",
    ]
    if any(re.search(pat, content) for pat in contrast_patterns):
        paradox_score += 0.5
    elif any(x in content_lower for x in ["反而", "但人均", "但产能", "值得注意"]):
        paradox_score += 0.25

    components["productivity_paradox"] = min(1.0, paradox_score)

    # 10. Monthly per-capita values (computed: monthly_total / advisor_count)
    # Jan'25: 8520/156=54.62, Feb'25: 7890/158=49.94, Mar'25: 9200/155=59.35
    # Jan'26: 5100/82=62.20, Feb'26: 5450/85=64.12, Mar'26: 5800/87=66.67
    monthly_per_capita_values = [
        ("54.6", "54.62"),   # Jan'25
        ("49.9", "49.94"),   # Feb'25
        ("59.4", "59.35"),   # Mar'25
        ("62.2", "62.20"),   # Jan'26
        ("64.1", "64.12"),   # Feb'26
        ("66.7", "66.67"),   # Mar'26
    ]
    mpc_hits = 0
    for short, full in monthly_per_capita_values:
        if short in content or full in content:
            mpc_hits += 1
    components["monthly_per_capita"] = min(1.0, mpc_hits / 3.0)

    # ===================================================================
    # EXPERT TIER (30%) — multi-step derived analysis; only top agents
    # ===================================================================

    # 11. Per-category per-advisor analysis
    # Requires: category_sales[month] / advisor_count[month] for each category
    # Debt bonds: Jan'25 2130/156=13.65, Jan'26 1224/82=14.93
    # Securities: Jan'25 1704/156=10.92, Jan'26 1020/82=12.44
    # Industry: Jan'25 1278/156=8.19, Jan'26 765/82=9.33
    # Infrastructure: Jan'25 1534/156=9.83, Jan'26 918/82=11.20
    per_cat_score = 0.0

    # Conceptual mention (partial credit)
    cat_per_advisor_concept = any(x in content_lower for x in [
        "各产品人均", "分产品人均", "各类别人均", "分类.*人均",
        "各产品.*人均", "per category per advisor",
    ]) or bool(re.search(r"(债券|证券|工商|基础设施).{0,30}人均", content))
    if cat_per_advisor_concept:
        per_cat_score += 0.3

    # Precise computed values (strict)
    precise_cat_per_advisor = [
        "13.65", "13.6",   # Debt Jan'25
        "14.93", "14.9",   # Debt Jan'26
        "10.92", "10.9",   # Securities Jan'25
        "12.44", "12.4",   # Securities Jan'26
        "8.19", "8.2",     # Industry Jan'25
        "9.33", "9.3",     # Industry Jan'26
        "9.83", "9.8",     # Infrastructure Jan'25
        "11.20", "11.2",   # Infrastructure Jan'26
    ]
    pcav_hits = sum(1 for v in precise_cat_per_advisor if v in content)
    per_cat_score += min(0.7, pcav_hits / 4.0 * 0.7)

    components["per_category_per_advisor"] = min(1.0, per_cat_score)

    # 12. Precise YoY Q1 comparison (requires 3+ correct metrics together)
    # Q1'25 total=25610 vs Q1'26 total=16350 => decline 36.1%
    # Q1'25 advisors avg=156.3 vs Q1'26 advisors avg=84.7 => decline 45.8%
    # Q1'25 per-capita=164.2 vs Q1'26 per-capita=192.4 => increase 17.2%
    yoy_score = 0.0
    yoy_metrics_found = 0

    # Metric 1: Q1 totals comparison
    if "25610" in content and "16350" in content:
        yoy_metrics_found += 1
        yoy_score += 0.2

    # Metric 2: Quarterly per-capita values
    q_per_capita = ["164.2", "164.1", "192.4", "192.3"]
    if sum(1 for v in q_per_capita if v in content) >= 2:
        yoy_metrics_found += 1
        yoy_score += 0.3

    # Metric 3: All quarterly per-capita (Q1-Q4'25 + Q1'26)
    all_q_per_capita = ["164.2", "164.1", "169.2", "163.5", "192.4"]
    aqpc_hits = sum(1 for v in all_q_per_capita if v in content)
    if aqpc_hits >= 3:
        yoy_metrics_found += 1
        yoy_score += 0.3

    # Metric 4: Percentage changes are correct
    if any(x in content for x in ["36.1%", "36.1"]):
        yoy_score += 0.1
    if any(x in content for x in ["17.2%", "17.2"]):
        yoy_score += 0.1

    components["yoy_precise_comparison"] = min(1.0, yoy_score)

    # 13. Paradox framing depth — not just noticing, but explaining causality
    # Strong agents explain WHY per-capita went up (fewer advisors, same/similar
    # total workload distributed among remaining staff) and draw management implications
    framing_score = 0.0

    # Mentions the mechanism (fewer people doing similar work)
    mechanism_patterns = [
        r"(减员|裁员|人员减少).{0,40}(工作量|任务|负荷|压力).{0,20}(分[担摊配]|承担|集中)",
        r"(留下|剩余|现有).{0,30}(理财师|人员).{0,30}(承担|负责|覆盖)",
        r"(人均.*负荷|单人.*工作量|个人.*压力).{0,20}(增[加大]|提[高升])",
        r"减员增效",
        r"(优化|精简).{0,20}(人员|团队|编制).{0,30}(效[率能]|产能)",
    ]
    if any(re.search(pat, content) for pat in mechanism_patterns):
        framing_score += 0.4

    # Discusses sustainability or risk of the paradox
    sustainability_patterns = [
        r"(可持续|持续性|长期|风险).{0,40}(人均|产能|工作量|负荷)",
        r"(倦怠|疲劳|burnout|流失|离职).{0,30}(风险|可能|隐患)",
        r"(关注|警惕|注意).{0,30}(人均.*过高|负荷.*过[大重]|压力)",
        r"(建议|需要).{0,40}(平衡|关注|监控).{0,30}(产能|负荷|工作量)",
    ]
    if any(re.search(pat, content) for pat in sustainability_patterns):
        framing_score += 0.3

    # Provides actionable management recommendations tied to the paradox
    action_patterns = [
        r"(建议|措施|行动).{0,60}(招聘|补充|扩[充编]|激励|留[人才住])",
        r"(优化|调整).{0,40}(产品.*配|客户.*分|区域.*划)",
        r"(监控|跟踪|评估).{0,30}(人均|产能|效率).{0,20}(指标|变化|趋势)",
    ]
    if any(re.search(pat, content) for pat in action_patterns):
        framing_score += 0.3

    components["paradox_framing_depth"] = min(1.0, framing_score)

    # --- Compute overall ---
    weights = _weights()
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def _weights() -> dict:
    return {
        # EASY TIER (15%) — any agent passes
        "report_exists": 0.05,
        "has_structure": 0.05,
        "basic_keywords": 0.05,
        # MEDIUM TIER (20%) — requires data extraction
        "data_referenced": 0.10,
        "category_names": 0.05,
        "executive_summary": 0.05,
        # HARD TIER (35%) — requires correct computation (hidden discriminator)
        "correct_quarterly_totals": 0.10,
        "advisor_reduction_pct": 0.08,
        "productivity_paradox": 0.12,
        "monthly_per_capita": 0.05,
        # EXPERT TIER (30%) — multi-step derived (hidden discriminator)
        "per_category_per_advisor": 0.10,
        "yoy_precise_comparison": 0.10,
        "paradox_framing_depth": 0.10,
    }


def main():
    ws = Path("/workspace")
    if not (ws / "output").exists() and not (ws / "fixtures" / "sales_data").exists():
        ws = Path("/workspace/fixtures").parent if Path("/workspace/fixtures").exists() else Path(".")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
