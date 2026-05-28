"""Hidden verifier for CP56 — Global Temperature Decade Comparison.

Reads /workspace/decade_report.md (with fallback filenames) and scores:
- report presence + non-empty
- decade label coverage (≥12 of 14 decades)
- markdown table presence
- correct identification of coldest decade (1910s ~-0.33 or 1900s ~-0.32)
- correct identification of warmest full decade (2010s ~0.80)
- decade-to-decade transition language
- largest warming transition (1970s→1980s or 2000s→2010s, ~+0.20-0.22)
- intra-decade variability / std deviation mention
- per-decade extreme years (≥20 distinct year mentions + warmest/coldest year language)
- source comparison (GISTEMP vs gcag)

Emits single-line JSON to stdout.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


REPORT_NAMES = [
    "decade_report.md", "decades.md", "report.md",
    "decade_analysis.md", "decade_comparison.md", "analysis.md",
]


def _read_report(ws: Path) -> tuple[str, str]:
    for name in REPORT_NAMES:
        p = ws / name
        if p.exists():
            try:
                return p.read_text(encoding="utf-8"), name
            except Exception:
                continue
    return "", ""


def grade_workspace(ws: Path) -> dict:
    content, fname = _read_report(ws)
    if not content.strip():
        return {
            "overall_score": 0.0,
            "components": {k: 0.0 for k in [
                "report", "decades", "table", "coldest", "warmest",
                "transitions", "largest_transition", "variability",
                "per_decade_extremes", "source_comparison",
            ]},
            "report_file": fname,
        }

    content_lower = content.lower()

    # Report presence
    c_report = 1.0

    # Decade label coverage
    decade_labels = ["1880", "1890", "1900", "1910", "1920", "1930", "1940",
                     "1950", "1960", "1970", "1980", "1990", "2000", "2010"]
    decades_found = sum(1 for d in decade_labels if d in content)
    if decades_found >= 12:
        c_decades = 1.0
    elif decades_found >= 8:
        c_decades = 0.7
    elif decades_found >= 5:
        c_decades = 0.4
    else:
        c_decades = 0.0

    # Markdown table presence
    c_table = 1.0 if re.search(r"\|.*\|.*\|", content) else 0.0

    # Coldest decade
    cold_patterns = [
        r"191\d.*(?:cold|cool|low|minimum)",
        r"(?:cold|cool|low|minimum).*191\d",
        r"190\d.*(?:cold|cool|low|minimum)",
        r"(?:cold|cool|low|minimum).*190\d",
        r"1910s.*-0\.3[23]",
        r"1900s.*-0\.3[12]",
    ]
    c_coldest = 1.0 if any(re.search(p, content_lower) for p in cold_patterns) else 0.0

    # Warmest decade
    warm_patterns = [
        r"2010.*(?:warm|hot|high|peak|maximum)",
        r"(?:warm|hot|high|peak|maximum).*2010",
        r"2010s.*0\.8[0-9]",
        r"2010s.*warmest",
    ]
    c_warmest = 1.0 if any(re.search(p, content_lower) for p in warm_patterns) else 0.0

    # Decade-to-decade changes language
    transition_patterns = [
        r"decade[\-\s]?to[\-\s]?decade",
        r"(?:transition|change|shift|difference|increase|warming).*decade",
        r"decade.*(?:transition|change|shift|difference|increase|warming)",
        r"→|->",
        r"\+0\.[012]\d",
    ]
    transition_count = sum(1 for p in transition_patterns if re.search(p, content_lower) or re.search(p, content))
    c_transitions = 1.0 if transition_count >= 2 else (0.5 if transition_count >= 1 else 0.0)

    # Largest warming transition
    largest_patterns = [
        r"(?:197|198).*(?:larg|great|big|most|maximum)",
        r"(?:larg|great|big|most|maximum).*(?:197|198)",
        r"(?:200|201).*(?:larg|great|big|most|maximum)",
        r"(?:larg|great|big|most|maximum).*(?:200|201)",
        r"(?:\+\s*)?0\.2[012]\d*.*(?:larg|great|big|most)",
        r"(?:larg|great|big|most).*(?:\+\s*)?0\.2[012]",
    ]
    c_largest = 1.0 if any(re.search(p, content_lower) or re.search(p, content) for p in largest_patterns) else 0.0

    # Variability / std
    var_patterns = [
        r"(?:variab|std|standard\s*dev|stddev)",
        r"(?:most|least|high|low).*(?:variab|spread|range)",
    ]
    c_variability = 1.0 if any(re.search(p, content_lower) for p in var_patterns) else 0.0

    # Per-decade extremes
    year_mentions = re.findall(r"(?:19|20)\d{2}", content)
    unique_years = len(set(year_mentions))
    extreme_lang = bool(re.search(r"(?:warm|cold|hot|cool)est.*(?:year|annual)|(?:year|annual).*(?:warm|cold|hot|cool)est", content_lower))
    if unique_years >= 20 and extreme_lang:
        c_extremes = 1.0
    elif unique_years >= 15:
        c_extremes = 0.6
    elif unique_years >= 10:
        c_extremes = 0.3
    else:
        c_extremes = 0.0

    # Source comparison
    comparison_patterns = [
        r"gistemp.*gcag|gcag.*gistemp",
        r"(?:both|two)\s+(?:source|dataset|series)",
        r"(?:compar|agree|differ|consistent).*(?:source|gistemp|gcag)",
        r"(?:source|gistemp|gcag).*(?:compar|agree|differ|consistent)",
    ]
    c_source = 1.0 if any(re.search(p, content_lower) for p in comparison_patterns) else 0.0

    weights = {
        "report": 0.05,
        "decades": 0.15,
        "table": 0.10,
        "coldest": 0.10,
        "warmest": 0.10,
        "transitions": 0.10,
        "largest_transition": 0.10,
        "variability": 0.10,
        "per_decade_extremes": 0.10,
        "source_comparison": 0.10,
    }
    components = {
        "report": c_report,
        "decades": round(c_decades, 4),
        "table": c_table,
        "coldest": c_coldest,
        "warmest": c_warmest,
        "transitions": c_transitions,
        "largest_transition": c_largest,
        "variability": c_variability,
        "per_decade_extremes": round(c_extremes, 4),
        "source_comparison": c_source,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": components,
        "weights": weights,
        "report_file": fname,
        "unique_years": unique_years,
        "decades_found": decades_found,
    }


def main():
    print(json.dumps(grade_workspace(Path("/workspace")), ensure_ascii=False))


if __name__ == "__main__":
    main()
