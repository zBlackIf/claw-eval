"""Hidden verifier for CP77 — Idaho weather stations coverage gap."""
from __future__ import annotations

import json
import re
from pathlib import Path


REPORT_NAMES = ["coverage_report.md", "coverage.md", "report.md",
                "gap_analysis.md", "analysis.md", "coverage_analysis.md"]


def _find(ws: Path) -> Path | None:
    for n in REPORT_NAMES:
        p = ws / n
        if p.exists():
            return p
    return None


def grade_workspace(ws: Path) -> dict:
    report = _find(ws)
    components = {k: 0.0 for k in [
        "report_created", "payette_identified", "county_counts",
        "elevation_bands", "agency_comparison", "missing_data", "recommendations",
    ]}
    if not report:
        return {"overall_score": 0.0, "components": components}

    content = report.read_text(encoding="utf-8", errors="ignore")
    lower = content.lower()
    components["report_created"] = 1.0

    components["payette_identified"] = 1.0 if "payette" in lower else 0.0

    top_counties = ["idaho", "blaine", "shoshone", "custer", "clearwater"]
    mentions = sum(
        1 for c in top_counties
        if re.search(rf"\b{c}\b.*\b1[0-3]\b|\b1[0-3]\b.*\b{c}\b", lower)
    )
    components["county_counts"] = 1.0 if mentions >= 3 else (0.5 if mentions >= 1 else 0.0)

    ev = 0
    if re.search(r"elevation.*band|band.*elevation|elevation.*range|elevation.*distribution", lower):
        ev += 1
    if re.search(r"(?:4[,.]?000|5[,.]?000|6[,.]?000)", content):
        ev += 1
    if re.search(r"(?:37|42)\s*station", lower) or re.search(r"(?:over|under).*represent", lower):
        ev += 1
    components["elevation_bands"] = 1.0 if ev >= 2 else (0.5 if ev >= 1 else 0.0)

    has_nws = bool(re.search(r"\bnws\b", lower))
    has_nrcs = bool(re.search(r"\bnrcs\b", lower))
    has_143 = bool(re.search(r"\b143\b", content))
    has_70 = bool(re.search(r"\b70\b", content))
    if has_nws and has_nrcs and (has_143 or has_70):
        components["agency_comparison"] = 1.0
    elif has_nws and has_nrcs:
        components["agency_comparison"] = 0.5

    miss_pats = [
        r"(?:5|five)\s*station.*(?:missing|blank|empty)",
        r"(?:missing|blank|empty).*(?:5|five)\s*station",
        r"(?:missing|blank|empty).*county",
        r"county.*(?:missing|blank|empty)",
    ]
    components["missing_data"] = 1.0 if any(re.search(p, lower) for p in miss_pats) else 0.0

    rec_pats = [r"recommend", r"suggest", r"additional\s*station",
                r"improv.*coverage", r"gap.*(?:fill|address|close)"]
    components["recommendations"] = 1.0 if any(re.search(p, lower) for p in rec_pats) else 0.0

    weights = {
        "report_created": 0.05,
        "payette_identified": 0.15,
        "county_counts": 0.20,
        "elevation_bands": 0.20,
        "agency_comparison": 0.15,
        "missing_data": 0.10,
        "recommendations": 0.15,
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
