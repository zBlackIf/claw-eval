"""Hidden verifier for CP80 — Embodied AI 15-page HTML slide deck."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _ignored(path: Path) -> bool:
    return any(part in {"fixtures", "__pycache__", ".git"} for part in path.parts)


def _natural_key(path: Path):
    return [int(s) if s.isdigit() else s.lower() for s in re.split(r"(\d+)", path.name)]


def _find_pages_dir(ws: Path) -> Path:
    pages_dir = ws / "pages"
    if pages_dir.exists():
        return pages_dir
    for d in ws.rglob("pages"):
        if d.is_dir():
            try:
                rel = d.relative_to(ws)
            except ValueError:
                rel = d
            if not _ignored(rel):
                return d
    return pages_dir


def grade_workspace(ws: Path) -> dict:
    pages_dir = _find_pages_dir(ws)

    html_files = []
    if pages_dir.exists():
        html_files = sorted(
            [p for p in pages_dir.glob("*.html") if p.is_file()],
            key=_natural_key,
        )
    count = len(html_files)
    components = {k: 0.0 for k in [
        "page_count", "valid_html", "tailwind", "echarts",
        "huawei_color", "fixed_dimensions", "data_tables", "company_coverage",
    ]}
    if count == 0:
        return {"overall_score": 0.0, "components": components}

    if count >= 15:
        components["page_count"] = 1.0
    elif count >= 12:
        components["page_count"] = 0.75
    elif count >= 8:
        components["page_count"] = 0.5
    elif count >= 3:
        components["page_count"] = 0.25

    companies = ["tesla", "figure", "agility", "boston dynamics",
                 "优必选", "宇树", "智元", "傅利叶", "达闼", "小鹏", "小米", "追觅"]

    valid_html = tailwind = echarts = huawei = fixed_dim = tables = comp_pages = 0
    for f in html_files:
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        lower = content.lower()
        if "<html" in lower and "</html>" in lower:
            valid_html += 1
        if "tailwind" in lower:
            tailwind += 1
        if "echarts" in lower and ("init" in lower or "setoption" in lower):
            echarts += 1
        if "c7020e" in lower:
            huawei += 1
        if "1280" in content and "720" in content:
            fixed_dim += 1
        if "<table" in lower and "<td" in lower:
            tables += 1
        if any(c in lower for c in companies):
            comp_pages += 1

    n = max(count, 1)
    components["valid_html"] = valid_html / n
    components["tailwind"] = min(1.0, tailwind / n)
    components["echarts"] = min(1.0, echarts / 2.0)
    components["huawei_color"] = min(1.0, huawei / max(n * 0.5, 1))
    components["fixed_dimensions"] = min(1.0, fixed_dim / max(n * 0.5, 1))
    components["data_tables"] = min(1.0, tables / 2.0)
    components["company_coverage"] = min(1.0, comp_pages / 5.0)

    weights = {
        "page_count": 0.20,
        "valid_html": 0.10,
        "tailwind": 0.10,
        "echarts": 0.10,
        "huawei_color": 0.15,
        "fixed_dimensions": 0.10,
        "data_tables": 0.10,
        "company_coverage": 0.15,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "page_count": count,
    }


def main():
    print(json.dumps(grade_workspace(Path("/workspace")), ensure_ascii=False))


if __name__ == "__main__":
    main()
