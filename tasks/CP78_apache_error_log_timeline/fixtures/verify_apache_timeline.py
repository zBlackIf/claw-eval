"""Hidden verifier for CP78 — Apache error log timeline."""
from __future__ import annotations

import json
from pathlib import Path


def grade_workspace(ws: Path) -> dict:
    report = ws / "error_timeline.json"
    components = {k: 0.0 for k in [
        "output_created", "valid_json", "daily_breakdown",
        "peak_day_identified", "peak_burst_identified", "server_restarts_noted",
    ]}
    if not report.exists():
        return {"overall_score": 0.0, "components": components}

    components["output_created"] = 1.0

    try:
        data = json.loads(report.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"overall_score": 0.05, "components": components}

    components["valid_json"] = 1.0
    full_text = json.dumps(data).lower()

    # Daily breakdown
    daily = data.get("daily_summary", [])
    if not isinstance(daily, list):
        daily = []
    days_with_counts = sum(
        1 for d in daily
        if isinstance(d, dict) and isinstance(d.get("error_count"), (int, float))
        and d.get("error_count", 0) > 0
    )
    components["daily_breakdown"] = (
        1.0 if days_with_counts >= 5 else
        0.5 if days_with_counts >= 3 else 0.0
    )

    # Peak day = June 11
    jun11_found = False
    max_count = 0
    max_date = ""
    for d in daily:
        if not isinstance(d, dict):
            continue
        date_str = str(d.get("date", ""))
        count = d.get("error_count", 0)
        if isinstance(count, (int, float)) and count > max_count:
            max_count = count
            max_date = date_str
        if "06-11" in date_str or "jun 11" in date_str.lower():
            jun11_found = True
    components["peak_day_identified"] = (
        1.0 if ("06-11" in max_date or "jun 11" in max_date.lower()) else
        0.5 if jun11_found else 0.0
    )

    # Peak burst (202.133.98.6 / awstats / 03:03)
    burst = data.get("peak_burst", {})
    btext = json.dumps(burst).lower() if isinstance(burst, dict) else full_text
    has_ip = "202.133.98.6" in btext
    has_awstats = "awstats" in btext
    has_time = any(t in btext for t in ["03:03", "jun 11", "06-11", "saturday"])
    if (has_ip or has_awstats) and has_time:
        components["peak_burst_identified"] = 1.0
    elif has_ip or has_awstats:
        components["peak_burst_identified"] = 0.5

    # Server restarts
    restart_kw = ["restart", "startup", "configured -- resuming", "graceful",
                  "resuming normal operations"]
    components["server_restarts_noted"] = 1.0 if any(kw in full_text for kw in restart_kw) else 0.0

    weights = {
        "output_created": 0.05,
        "valid_json": 0.10,
        "daily_breakdown": 0.20,
        "peak_day_identified": 0.20,
        "peak_burst_identified": 0.30,
        "server_restarts_noted": 0.15,
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
