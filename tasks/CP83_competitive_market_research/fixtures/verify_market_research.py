"""Hidden verifier for CP83 — APM/observability competitive market research."""
from __future__ import annotations

import json
import re
from pathlib import Path


KNOWN_COMPETITORS = [
    "datadog", "new relic", "dynatrace", "splunk", "grafana",
    "elastic", "appdynamics", "honeycomb", "lightstep", "sumo logic",
    "instana", "sentry", "chronosphere", "logz.io", "coralogix",
    "signoz", "observe inc", "mezmo",
]


def grade_workspace(ws: Path) -> dict:
    report = ws / "market_research.md"
    components = {k: 0.0 for k in [
        "file_created", "competitors_identified", "comparison_table",
        "pricing_info", "trends_section", "structure",
        "executive_summary",
    ]}
    if not report.exists():
        return {"overall_score": 0.0, "components": components}

    content = report.read_text(encoding="utf-8", errors="ignore")
    lower = content.lower()
    components["file_created"] = 1.0

    found = [c for c in KNOWN_COMPETITORS if c in lower]
    if len(found) >= 5:
        components["competitors_identified"] = 1.0
    elif len(found) >= 3:
        components["competitors_identified"] = 0.5
    elif len(found) >= 1:
        components["competitors_identified"] = 0.25

    has_table = bool(re.search(r"\|.*\|.*\|", content)) and bool(re.search(r"\|[\s-]+\|", content))
    components["comparison_table"] = 1.0 if has_table else 0.0

    pricing_pats = [r"pric(e|ing|ed)", r"per[\s-]?(host|gb|user|seat|node|core)",
                    r"free\s+tier", r"subscription", r"\$\d+", r"cost"]
    pm = sum(1 for p in pricing_pats if re.search(p, lower))
    components["pricing_info"] = 1.0 if pm >= 3 else (0.5 if pm >= 1 else 0.0)

    trends_pats = [r"trend", r"market\s+(direction|shift|movement|growth)",
                   r"opentelemetry", r"otel", r"ai[\s/]ml", r"artificial intelligence",
                   r"machine learning", r"consolidat", r"cloud[\s-]native"]
    tm = sum(1 for p in trends_pats if re.search(p, lower))
    components["trends_section"] = 1.0 if tm >= 3 else (0.5 if tm >= 1 else 0.0)

    headings = re.findall(r"^#{1,3}\s+.+", content, re.M)
    components["structure"] = 1.0 if len(headings) >= 6 else (0.5 if len(headings) >= 3 else 0.0)

    if re.search(r"(executive\s+summary|overview|introduction)", lower):
        components["executive_summary"] = 1.0

    weights = {
        "file_created": 0.05,
        "competitors_identified": 0.25,
        "comparison_table": 0.15,
        "pricing_info": 0.15,
        "trends_section": 0.15,
        "structure": 0.15,
        "executive_summary": 0.10,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "competitors_found": found,
    }


def main():
    print(json.dumps(grade_workspace(Path("/workspace")), ensure_ascii=False))


if __name__ == "__main__":
    main()
