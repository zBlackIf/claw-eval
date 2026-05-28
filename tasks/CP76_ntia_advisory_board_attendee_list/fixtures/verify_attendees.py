"""Hidden verifier for CP76 — NTIA CSMAC attendee list."""
from __future__ import annotations

import json
import re
from pathlib import Path


REPORT_NAMES = ["attendees.md", "attendee_list.md", "attendees_list.md", "meeting_attendees.md"]


def _find(ws: Path) -> Path | None:
    for n in REPORT_NAMES:
        p = ws / n
        if p.exists():
            return p
    return None


def grade_workspace(ws: Path) -> dict:
    report = _find(ws)
    components = {k: 0.0 for k in [
        "report_created", "chair_identified", "member_count",
        "remote_attendees", "officials_listed", "organizations_included",
        "attendance_mode", "public_participant", "summary_count",
    ]}
    if not report:
        return {"overall_score": 0.0, "components": components}

    content = report.read_text(encoding="utf-8", errors="ignore")
    lower = content.lower()
    components["report_created"] = 1.0

    # Chair
    if "fontes" in lower and "chair" in lower and re.search(r"nena|national emergency", lower):
        components["chair_identified"] = 1.0

    # Members (≥15 of 19)
    members = ["fontes", "borth", "calabrese", "dombrowsky", "donovan", "feldman",
               "furchtgott", "gibson", "hatfield", "kahn", "mcginnis", "mchenry",
               "obuchowski", "povelites", "reaser", "rush", "stancil", "tramont", "warren"]
    found = sum(1 for m in members if m in lower)
    components["member_count"] = 1.0 if found >= 15 else (0.5 if found >= 10 else 0.0)

    # Remote attendees (named + near phone/remote/virtual)
    remote = ["hatfield", "feldman", "mcginnis", "stancil", "reaser", "donovan"]
    remote_found = 0
    for rm in remote:
        if rm in lower:
            patterns = [rf"{rm}.*(?:phone|remote|virtual|telephone|dial)",
                        rf"(?:phone|remote|virtual|telephone|dial).*{rm}"]
            if any(re.search(p, lower) for p in patterns):
                remote_found += 1
            elif "*" in content:
                remote_found += 0.5
    components["remote_attendees"] = 1.0 if remote_found >= 4 else (0.5 if remote_found >= 2 else 0.0)

    # Officials
    officials = ["strickling", "nebbia", "power", "washington"]
    of_found = sum(1 for o in officials if o in lower)
    components["officials_listed"] = 1.0 if of_found >= 3 else (0.5 if of_found >= 2 else 0.0)

    # Organizations
    orgs = ["nena", "national emergency number", "verizon", "at&t", "att", "intel",
            "lockheed", "raytheon", "comsearch", "new america", "wiley rein",
            "wilkinson barker", "shared spectrum", "exelon", "ntia",
            "furchtgott-roth", "nc state", "north carolina", "colorado",
            "freedom technologies"]
    org_found = sum(1 for o in orgs if o in lower)
    components["organizations_included"] = 1.0 if org_found >= 10 else (0.5 if org_found >= 5 else 0.0)

    # Attendance mode
    mode_pats = [r"in[- ]person", r"on[- ]?site", r"physical", r"phone", r"remote", r"virtual"]
    mode_count = sum(1 for p in mode_pats if re.search(p, lower))
    components["attendance_mode"] = 1.0 if mode_count >= 2 else (0.5 if mode_count >= 1 else 0.0)

    # Public participant
    components["public_participant"] = 1.0 if "snider" in lower else 0.0

    # Summary count
    count_pats = [r"total.*\d+", r"\d+.*total", r"(?:attendee|participant|member)s?.*\d+",
                  r"\d+.*(?:attendee|participant|member)", r"count.*\d+"]
    components["summary_count"] = 1.0 if any(re.search(p, lower) for p in count_pats) else 0.0

    weights = {
        "report_created": 0.05,
        "chair_identified": 0.10,
        "member_count": 0.20,
        "remote_attendees": 0.15,
        "officials_listed": 0.10,
        "organizations_included": 0.15,
        "attendance_mode": 0.10,
        "public_participant": 0.05,
        "summary_count": 0.10,
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
