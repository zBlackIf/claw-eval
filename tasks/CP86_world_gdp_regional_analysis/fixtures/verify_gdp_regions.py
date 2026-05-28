"""Hidden verifier for CP86 — World GDP regional analysis."""
from __future__ import annotations

import json
import re
from pathlib import Path


REPORT_NAMES = ["gdp_regions_report.md", "regions_report.md", "report.md",
                "gdp_regions.md", "regional_report.md", "regional_analysis.md", "analysis.md"]


def _find(ws: Path) -> Path | None:
    for n in REPORT_NAMES:
        p = ws / n
        if p.exists():
            return p
    return None


def grade_workspace(ws: Path) -> dict:
    report = _find(ws)
    components = {k: 0.0 for k in [
        "report_created", "regional_totals", "top_per_region",
        "dominant_regions", "avg_per_country", "disparity",
        "borderline_cases", "summary_paragraph",
    ]}
    if not report:
        return {"overall_score": 0.0, "components": components}

    content = report.read_text(encoding="utf-8", errors="ignore")
    lower = content.lower()
    components["report_created"] = 1.0

    region_pats = [r"north\s*america", r"europe", r"east\s*asia", r"south\s*asia",
                   r"latin\s*america", r"middle\s*east", r"sub[- ]saharan", r"central\s*asia"]
    regions_found = sum(1 for r in region_pats if re.search(r, lower))
    has_pct = bool(re.search(r"\d+\.?\d*\s*%", content))
    components["regional_totals"] = 1.0 if (regions_found >= 7 and has_pct) else (0.5 if regions_found >= 4 else 0.0)

    top_pats = [r"united\s*states", r"germany", r"china", r"india", r"brazil",
                r"saudi\s*arabia", r"nigeria", r"kazakhstan"]
    top_found = sum(1 for p in top_pats if re.search(p, lower))
    components["top_per_region"] = 1.0 if top_found >= 7 else (0.5 if top_found >= 4 else 0.0)

    dom_pats = [
        r"(?:dominat|largest|top\s*(?:3|three)).*(?:region|area)",
        r"(?:north\s*america|europe|east\s*asia).*(?:combin|together|account)",
        r"(?:7[5-9]|80)\s*[\.\d]*%.*(?:combin|together|three|3)",
    ]
    components["dominant_regions"] = 1.0 if any(re.search(p, lower) for p in dom_pats) else 0.0

    avg_pats = [
        r"(?:average|mean)\s*(?:gdp)?\s*(?:per\s*country|per\s*economy)",
        r"north\s*america.*(?:highest|largest).*(?:average|mean)",
        r"(?:africa|sub[- ]saharan).*(?:lowest|smallest).*(?:average|mean)",
    ]
    af = sum(1 for p in avg_pats if re.search(p, lower))
    components["avg_per_country"] = 1.0 if af >= 2 else (0.5 if af >= 1 else 0.0)

    disp_pats = [r"(?:dispar|ratio|inequal|gap|range)",
                 r"(?:largest|biggest).*(?:smallest|lowest)",
                 r"(?:ratio|factor|times)"]
    df = sum(1 for p in disp_pats if re.search(p, lower))
    components["disparity"] = 1.0 if df >= 2 else (0.5 if df >= 1 else 0.0)

    border_pats = [
        r"(?:russia|turkey).*(?:border|ambiguous|classify|assign|debat|could)",
        r"(?:border|ambiguous|transcontinental).*(?:russia|turkey)",
        r"(?:classif|assign|categori).*(?:challeng|difficult|judgment|borderline)",
    ]
    components["borderline_cases"] = 1.0 if any(re.search(p, lower) for p in border_pats) else 0.0

    sum_pats = [
        r"(?:concentrat|cluster|dominat).*(?:global|world)",
        r"(?:global|world).*(?:output|gdp).*(?:concentrat|dominat|cluster)",
        r"(?:africa|developing|south).*(?:small|fraction|marginal)",
    ]
    components["summary_paragraph"] = 1.0 if any(re.search(p, lower) for p in sum_pats) else 0.0

    weights = {
        "report_created": 0.05,
        "regional_totals": 0.20,
        "top_per_region": 0.20,
        "dominant_regions": 0.10,
        "avg_per_country": 0.15,
        "disparity": 0.15,
        "borderline_cases": 0.05,
        "summary_paragraph": 0.10,
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
