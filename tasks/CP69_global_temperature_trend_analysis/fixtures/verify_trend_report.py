"""Hidden verifier for CP69 — Global Temperature Trend Analysis."""
from __future__ import annotations

import json
import re
from pathlib import Path


REPORT_NAMES = ["trend_report.md", "trend_analysis.md", "report.md",
                "temperature_trend.md", "analysis.md"]


def _find(ws: Path) -> Path | None:
    for n in REPORT_NAMES:
        p = ws / n
        if p.exists():
            return p
    return None


def grade_workspace(ws: Path) -> dict:
    report = _find(ws)
    components = {k: 0.0 for k in [
        "report_created", "overall_rate", "pre1950_rate", "post1950_rate",
        "acceleration", "first_05", "first_10", "decade_comparison", "summary",
    ]}
    if not report:
        return {"overall_score": 0.0, "components": components}

    content = report.read_text(encoding="utf-8", errors="ignore")
    lower = content.lower()
    components["report_created"] = 1.0

    rate_pats = [
        r"0\.0[78]\d*\s*°?c?\s*/?\s*(?:per\s*)?decade",
        r"0\.0[78]\d*\s*°?c?\s*(?:per|every)\s*(?:10|ten)\s*year",
        r"0\.00[78]\d*\s*°?c?\s*/?\s*(?:per\s*)?year",
    ]
    components["overall_rate"] = 1.0 if any(re.search(p, lower) for p in rate_pats) else 0.0

    pre_pats = [
        r"(?:pre|before|prior)[\s\-]*1950.*0\.0[345]",
        r"0\.0[345].*(?:pre|before|prior)[\s\-]*1950",
        r"1880.*1949.*0\.0[345]",
    ]
    components["pre1950_rate"] = 1.0 if any(re.search(p, lower) for p in pre_pats) else 0.0

    post_pats = [
        r"(?:post|after|since)[\s\-]*1950.*0\.1[45678]",
        r"0\.1[45678].*(?:post|after|since)[\s\-]*1950",
        r"1950.*2023.*0\.1[45678]",
    ]
    components["post1950_rate"] = 1.0 if any(re.search(p, lower) for p in post_pats) else 0.0

    accel_pats = [
        r"accelerat",
        r"(?:3|4|three|four)\s*(?:times|×|x)\s*(?:fast|great)",
        r"(?:rapid|steep).*(?:recent|post|after|since)",
    ]
    components["acceleration"] = 1.0 if any(re.search(p, lower) for p in accel_pats) else 0.0

    p05 = [
        r"199[78].*(?:first|exceed|cross|breach|surpass).*0\.5",
        r"(?:first|exceed|cross|breach|surpass).*0\.5.*199[78]",
        r"0\.5\s*°?c.*(?:first|exceed|cross).*199[78]",
    ]
    components["first_05"] = 1.0 if any(re.search(p, lower) for p in p05) else 0.0

    p10 = [
        r"201[56].*(?:first|exceed|cross|breach|surpass).*1\.0",
        r"(?:first|exceed|cross|breach|surpass).*1\.0.*201[56]",
        r"1\.0\s*°?c.*(?:first|exceed|cross).*201[56]",
    ]
    components["first_10"] = 1.0 if any(re.search(p, lower) for p in p10) else 0.0

    dec_pats = [
        r"(?:2010|2014|2020|recent).*(?:1880|earliest|first)",
        r"(?:1880|earliest|first).*(?:2010|2014|2020|recent)",
        r"~?1\.\d*\s*°?c.*(?:warmer|higher|difference|increase)",
    ]
    components["decade_comparison"] = 1.0 if any(re.search(p, lower) for p in dec_pats) else 0.0

    sum_pats = [
        r"summar", r"conclusion", r"in\s+(?:summary|conclusion)",
        r"overall.*(?:trend|warming)",
        r"(?:clear|unmistakable|evident|undeniable).*(?:warm|trend)",
    ]
    components["summary"] = 1.0 if any(re.search(p, lower) for p in sum_pats) else 0.0

    weights = {
        "report_created": 0.05,
        "overall_rate": 0.15,
        "pre1950_rate": 0.10,
        "post1950_rate": 0.10,
        "acceleration": 0.10,
        "first_05": 0.15,
        "first_10": 0.15,
        "decade_comparison": 0.10,
        "summary": 0.10,
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
