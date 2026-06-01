"""Hidden verifier for CP84 — Trading system design doc v2.4→v2.5 upgrade."""
from __future__ import annotations

import json
import re
from pathlib import Path


def grade_workspace(ws: Path) -> dict:
    doc = ws / "TRADING_SYSTEM_PLAN_V2.md"
    if not doc.exists():
        for alt in ws.glob("*TRADING*PLAN*.md"):
            doc = alt
            break
    components = {k: 0.0 for k in [
        "version_log_updated", "fok_no_insert",
        "lastprice_single_writer", "orderbook_simulation",
        "quote_algorithm_defined",
    ]}
    if not doc.exists():
        return {"overall_score": 0.0, "components": components}

    content = doc.read_text(encoding="utf-8", errors="ignore")

    has_v25_title = bool(re.search(r"v2\.5", content[:200], re.I))
    has_v25_in_log = bool(re.search(
        r"v2\.5.*?(FOK|lastPrice|order.?book|quote|行情)",
        content, re.I | re.DOTALL))
    if has_v25_title and has_v25_in_log:
        components["version_log_updated"] = 1.0
    elif has_v25_in_log:
        components["version_log_updated"] = 0.75
    elif has_v25_title:
        components["version_log_updated"] = 0.5

    fok_lower = content.lower()
    has_no_insert = bool(re.search(
        r"fok.{0,100}(not?.{0,20}(create|insert|record)|no.{0,20}(order.?record|insert)|不.{0,10}(创建|插入|记录|产生)|完全不创建)",
        fok_lower, re.I))
    original_row = bool(re.search(r"FOK\s*\|\s*REJECTED\s*\|", content))
    fok_score = 0.0
    if has_no_insert:
        fok_score += 0.5
    if not original_row:
        fok_score += 0.5
    components["fok_no_insert"] = min(1.0, fok_score)

    sec24 = re.search(r"2\.4.*?(?=##\s*2\.[56]|\Z)", content, re.DOTALL)
    if sec24:
        s24 = sec24.group()
        has_single = bool(re.search(
            r"(only|sole|single|唯一).{0,30}(MatchingEngine|match\(\))|"
            r"MatchingEngine.{0,30}(only|sole|唯一)|"
            r"QuoteService.{0,30}(read.?only|只读|不写入|not.{0,10}(write|update))",
            s24, re.I))
        components["lastprice_single_writer"] = 1.0 if has_single else 0.25
    else:
        components["lastprice_single_writer"] = 0.5 if re.search(r"lastPrice.*single|lastPrice.*唯一", content, re.I) else 0.0

    sec25 = re.search(r"2\.5.*?(?=##\s*[23]\.[0-9]|\Z)", content, re.DOTALL)
    if sec25:
        s25 = sec25.group()
        has_sim = bool(re.search(
            r"simulat|模拟|generate.*quote|生成.*报价|lastPrice.*float|placeholder.*price|虚拟.*报价",
            s25, re.I))
        has_pct = bool(re.search(r"0\.5%|2\.5%|\d+\.?\d*%.*float|浮动", s25, re.I))
        if has_sim and has_pct:
            components["orderbook_simulation"] = 1.0
        elif has_sim:
            components["orderbook_simulation"] = 0.75

    sec5 = re.search(r"5\.1.*?(?=##\s*[56]\.[0-9]|##\s*6\.|\Z)", content, re.DOTALL)
    if sec5:
        s5 = sec5.group()
        rw = bool(re.search(r"random.?walk|随机游走|布朗运动|Brownian", s5, re.I))
        mr = bool(re.search(r"mean.?reversion|均值回归|回归均值", s5, re.I))
        formula = bool(re.search(r"[Pp]\(t\)|price.*=|P_t|delta|sigma|μ|σ|volatil", s5))
        empty = len(s5.strip()) < 80 or "to be defined" in s5.lower() or "待定义" in s5
        if empty:
            components["quote_algorithm_defined"] = 0.0
        elif rw and mr and formula:
            components["quote_algorithm_defined"] = 1.0
        elif rw and mr:
            components["quote_algorithm_defined"] = 0.75
        elif rw or mr:
            components["quote_algorithm_defined"] = 0.5
        else:
            components["quote_algorithm_defined"] = 0.25

    weights = {
        "version_log_updated": 0.15,
        "fok_no_insert": 0.25,
        "lastprice_single_writer": 0.20,
        "orderbook_simulation": 0.20,
        "quote_algorithm_defined": 0.20,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    print(json.dumps(grade_workspace(Path("/workspace")), ensure_ascii=False))


if __name__ == "__main__":
    main()
