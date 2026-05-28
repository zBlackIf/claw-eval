"""Hidden verifier for CP61 — Stock Price Research."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


def grade_workspace(ws: Path) -> dict:
    report = ws / "stock_report.txt"
    content = _read(report)

    components = {k: 0.0 for k in [
        "file_created", "ticker_present", "price_present",
        "date_present", "summary_present", "well_formatted",
    ]}

    if not content.strip():
        return {"overall_score": 0.0, "components": components}

    components["file_created"] = 1.0

    if re.search(r"\bAAPL\b", content, re.I) or "Apple" in content:
        components["ticker_present"] = 1.0

    price_patterns = [r"\$\s*\d+\.?\d*", r"\d+\.\d{2}", r"price[^\n]{0,15}\d+"]
    if any(re.search(p, content, re.I) for p in price_patterns):
        components["price_present"] = 1.0

    date_patterns = [
        r"\d{4}-\d{2}-\d{2}", r"\d{1,2}/\d{1,2}/\d{2,4}",
        r"(January|February|March|April|May|June|July|August|September|October|November|December)",
        r"\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)",
        r"\d{4}\s*年\s*\d{1,2}\s*月",
    ]
    if any(re.search(p, content, re.I) for p in date_patterns):
        components["date_present"] = 1.0

    # Summary: at least 60 chars beyond the ticker/price/date noise
    if len(content.strip()) >= 200:
        components["summary_present"] = 1.0
    elif len(content.strip()) >= 100:
        components["summary_present"] = 0.6

    # Well-formatted: line breaks, sections, or headers
    line_count = content.count("\n")
    has_structure = bool(re.search(r"^#+\s|^-\s|^\*\s|^\d+\.\s|:\s*$", content, re.M))
    if line_count >= 3 and has_structure:
        components["well_formatted"] = 1.0
    elif line_count >= 2:
        components["well_formatted"] = 0.6

    weights = {
        "file_created": 0.10,
        "ticker_present": 0.20,
        "price_present": 0.25,
        "date_present": 0.15,
        "summary_present": 0.20,
        "well_formatted": 0.10,
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
