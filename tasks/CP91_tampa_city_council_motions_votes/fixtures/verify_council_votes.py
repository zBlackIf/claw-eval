"""Hidden verifier for CP91 — Tampa City Council motions + vote outcomes."""
from __future__ import annotations

import json
import re
from pathlib import Path


REPORT_NAMES = ["votes_report.md", "votes.md", "motions.md", "vote_report.md"]


def _find(ws: Path) -> Path | None:
    for n in REPORT_NAMES:
        p = ws / n
        if p.exists():
            return p
    return None


def grade_workspace(ws: Path) -> dict:
    report = _find(ws)
    components = {k: 0.0 for k in [
        "report_created", "minutes_vote", "item12_abstain",
        "item14_15_rollcall", "item19_unanimous", "item22_continued",
        "item23_first_reading", "item25_carlson_no",
        "item26_28_reconsider", "summary_count",
    ]}
    if not report:
        return {"overall_score": 0.0, "components": components}

    content = report.read_text(encoding="utf-8", errors="ignore")
    cl = content.lower()
    components["report_created"] = 1.0

    if re.search(r"miranda", cl) and re.search(r"minut", cl):
        components["minutes_vote"] = 1.0
    if re.search(r"(?:item\s*(?:#?\s*)?12|twelve)", cl) and re.search(r"carlson.*(?:abstain|recus)", cl):
        components["item12_abstain"] = 1.0
    if re.search(r"(?:14|15|rome\s*yard)", cl) and re.search(r"5[\s-]*2", cl):
        components["item14_15_rollcall"] = 1.0
    if re.search(r"(?:item\s*(?:#?\s*)?19|rez[\s-]*25[\s-]*126|4102)", cl) and re.search(r"unanimou", cl):
        components["item19_unanimous"] = 1.0
    if re.search(r"(?:item\s*(?:#?\s*)?22|veteran)", cl) and re.search(r"(?:continu|defer|april\s*16|first\s*reading)", cl):
        components["item22_continued"] = 1.0
    if re.search(r"(?:item\s*(?:#?\s*)?23|capacity\s*fee|water.*wastewater)", cl) and re.search(r"(?:first\s*read|pass|approv)", cl):
        components["item23_first_reading"] = 1.0
    if re.search(r"(?:item\s*(?:#?\s*)?25)", cl) and re.search(r"(?:carlson.*(?:no|nay|dissent)|6[\s-]*1)", cl):
        components["item25_carlson_no"] = 1.0
    if re.search(r"(?:26|27|28|howard|annex|forensic)", cl) and re.search(r"(?:reconsider|rescind|second\s*read|april\s*16)", cl):
        components["item26_28_reconsider"] = 1.0
    if re.search(r"(?:total|summary|count).*(?:\d+\s*vote|\d+\s*motion)", cl):
        components["summary_count"] = 1.0

    weights = {
        "report_created": 0.05,
        "minutes_vote": 0.10,
        "item12_abstain": 0.10,
        "item14_15_rollcall": 0.15,
        "item19_unanimous": 0.10,
        "item22_continued": 0.10,
        "item23_first_reading": 0.10,
        "item25_carlson_no": 0.15,
        "item26_28_reconsider": 0.10,
        "summary_count": 0.05,
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
