"""Hidden verifier for CP174 — Epub Extract Knowledge Base."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_output_file(ws: Path) -> Path | None:
    """Find the generated knowledge base markdown file."""
    # Check common output locations
    candidates = []
    for pattern in ["**/*.md", "**/*.markdown"]:
        for p in ws.rglob(pattern[3:]) if pattern.startswith("**/") else [ws / pattern]:
            pass
        for p in ws.rglob("*.md"):
            if p.name == "portfolio_context.md":
                continue
            if p.name == "README.md":
                continue
            candidates.append(p)
        break

    # Also check output/ or knowledge_base/ directories
    for d in ["output", "knowledge_base", "kb", "memory", "notes"]:
        dirpath = ws / d
        if dirpath.exists():
            for p in dirpath.rglob("*.md"):
                if p not in candidates:
                    candidates.append(p)

    # Return the largest markdown file (most likely the main output)
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_size if p.exists() else 0)


def grade_workspace(ws: Path) -> dict:
    components = {k: 0.0 for k in [
        "epub_parsed",
        "chapters_extracted",
        "ten_criteria_covered",
        "risk_framework_covered",
        "buy_sell_framework_covered",
        "portfolio_integration",
        "structure_quality",
    ]}

    # Find the output file
    output_file = _find_output_file(ws)
    if not output_file or not output_file.exists():
        # Also check directly in workspace root or project/
        for p in (ws / "project").rglob("*.md") if (ws / "project").exists() else []:
            if p.name != "portfolio_context.md" and p.stat().st_size > 500:
                output_file = p
                break
        if not output_file:
            return {
                "overall_score": 0.0,
                "components": components,
                "weights": _weights(),
                "error": "No output markdown file found",
            }

    content = _read(output_file)
    content_lower = content.lower()

    # 1. epub_parsed: Did the agent successfully extract content from the epub?
    # Evidence: output contains book-specific terms that only exist in the epub
    epub_markers = [
        "系统化投资原则",
        "张明远",
        "sip",
        "第一性原则",
        "护城河原则",
        "安全边际原则",
    ]
    found_markers = sum(1 for m in epub_markers if m.lower() in content_lower)
    components["epub_parsed"] = min(1.0, found_markers / 3.0)

    # 2. chapters_extracted: Were all 5 chapters covered?
    chapter_keywords = [
        ["投资哲学", "价值投资", "成长投资", "复利", "市场先生"],
        ["选股", "准则", "十大", "核心准则", "营收增长"],
        ["风险控制", "五层", "风控", "止损", "止盈"],
        ["买入时机", "仓位管理", "金字塔", "加仓"],
        ["卖出", "决策框架", "证伪", "估值透支"],
    ]
    chapters_found = 0
    for ch_keywords in chapter_keywords:
        if any(kw in content for kw in ch_keywords):
            chapters_found += 1
    components["chapters_extracted"] = chapters_found / 5.0

    # 3. ten_criteria_covered: Were the 10 stock selection criteria included?
    criteria_keywords = [
        "营收增长",
        "利润率",
        "管理层",
        "护城河",
        "自由现金流",
        "行业地位",
        "研发",
        "财务健康",
        "估值",
        "催化剂",
    ]
    criteria_found = sum(1 for kw in criteria_keywords if kw in content)
    components["ten_criteria_covered"] = min(1.0, criteria_found / 7.0)

    # 4. risk_framework_covered: Was the 5-layer risk control model included?
    risk_keywords = [
        "选股质量",
        "仓位管理",
        "估值纪律",
        "动态监控",
        "极端情景",
        "七大错误",
        "过度交易",
        "追涨杀跌",
    ]
    risk_found = sum(1 for kw in risk_keywords if kw in content)
    components["risk_framework_covered"] = min(1.0, risk_found / 4.0)

    # 5. buy_sell_framework_covered: Buy/sell timing frameworks
    buysell_keywords = [
        "估值回归",
        "业绩拐点",
        "金字塔",
        "买入逻辑被证伪",
        "估值严重透支",
        "绝对不卖",
        "卖出纪律",
    ]
    buysell_found = sum(1 for kw in buysell_keywords if kw in content)
    components["buy_sell_framework_covered"] = min(1.0, buysell_found / 4.0)

    # 6. portfolio_integration: Did the agent integrate with portfolio context?
    portfolio_markers = [
        "华测检测",
        "300012",
        "迈瑞医疗",
        "东方财富",
        "检测",
        "持仓",
    ]
    portfolio_found = sum(1 for m in portfolio_markers if m in content)
    components["portfolio_integration"] = min(1.0, portfolio_found / 3.0)

    # 7. structure_quality: Is the document well-structured?
    structure_score = 0.0
    # Has headings
    h1_count = len(re.findall(r'^#\s+', content, re.MULTILINE))
    h2_count = len(re.findall(r'^##\s+', content, re.MULTILINE))
    h3_count = len(re.findall(r'^###\s+', content, re.MULTILINE))
    if h2_count >= 3:
        structure_score += 0.3
    if h3_count >= 5:
        structure_score += 0.2
    # Has lists
    list_items = len(re.findall(r'^[-*]\s+', content, re.MULTILINE))
    if list_items >= 10:
        structure_score += 0.2
    # Reasonable length (at least 2000 chars for a knowledge base)
    if len(content) >= 2000:
        structure_score += 0.15
    if len(content) >= 4000:
        structure_score += 0.15
    components["structure_quality"] = min(1.0, structure_score)

    weights = _weights()
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "output_file": str(output_file),
    }


def _weights() -> dict:
    return {
        "epub_parsed": 0.20,
        "chapters_extracted": 0.20,
        "ten_criteria_covered": 0.15,
        "risk_framework_covered": 0.10,
        "buy_sell_framework_covered": 0.10,
        "portfolio_integration": 0.10,
        "structure_quality": 0.15,
    }


def main():
    # Try /workspace/fixtures/project/ first, then /workspace/project/, then /workspace/
    ws = Path("/workspace/fixtures/project")
    if not ws.exists():
        ws = Path("/workspace/project")
    if not ws.exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
