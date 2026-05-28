"""Hidden verifier for CP79 — NTIA CSMAC stakeholder analysis."""
from __future__ import annotations

import json
import re
from pathlib import Path


REPORT_NAMES = ["stakeholder_analysis.md", "stakeholders.md",
                "stakeholder_report.md", "analysis.md"]


def _find(ws: Path) -> Path | None:
    for n in REPORT_NAMES:
        p = ws / n
        if p.exists():
            return p
    return None


def grade_workspace(ws: Path) -> dict:
    report = _find(ws)
    components = {k: 0.0 for k in [
        "report_created", "gov_stakeholders", "commercial_stakeholders",
        "sharing_preference", "relocation_cost", "sharing_vs_relocation",
        "common_parameters", "conflicts_identified", "member_positions",
    ]}
    if not report:
        return {"overall_score": 0.0, "components": components}

    content = report.read_text(encoding="utf-8", errors="ignore")
    lower = content.lower()
    components["report_created"] = 1.0

    gov = ["ntia", "dod", "department of defense", "defense", "dhs",
           "homeland security", "justice", "white house", "ostp",
           "science and technology policy"]
    gov_found = sum(1 for g in gov if g in lower)
    components["gov_stakeholders"] = 1.0 if gov_found >= 4 else (0.5 if gov_found >= 2 else 0.0)

    comm = ["carrier", "wireless", "commercial", "industry", "at&t", "att",
            "verizon", "intel", "t-mobile", "equipment manufacturer",
            "service provider", "ctia", "broadband"]
    cf = sum(1 for c in comm if c in lower)
    components["commercial_stakeholders"] = 1.0 if cf >= 4 else (0.5 if cf >= 2 else 0.0)

    share_pats = [
        r"ntia.*(?:prefer|favor|advocate|support).*shar",
        r"shar.*(?:prefer|favor|better|alternative).*(?:relocat|vacat)",
        r"(?:better way|minimize.*movement|keep.*cost)",
        r"days of vacating.*coming to a close",
    ]
    components["sharing_preference"] = 1.0 if any(re.search(p, lower) for p in share_pats) else 0.0

    cost_pats = [r"\$?18\s*billion", r"18b", r"\$18b", r"18,000", r"eighteen billion"]
    components["relocation_cost"] = 1.0 if any(re.search(p, lower) for p in cost_pats) else 0.0

    tension_pats = [
        r"shar.*(?:vs|versus|or|instead of|rather than).*relocat",
        r"relocat.*(?:vs|versus|or|instead of|rather than).*shar",
        r"(?:sharing|relocation).*(?:tension|debate|disagreement|question|trade-?off)",
        r"(?:why.*spend.*money.*move|if.*sharing.*works)",
    ]
    components["sharing_vs_relocation"] = 1.0 if any(re.search(p, lower) for p in tension_pats) else 0.0

    param_pats = [
        r"(?:common|uniform|consistent).*(?:parameter|characteristic|assumption|input)",
        r"(?:parameter|characteristic|assumption).*(?:common|uniform|consistent|agree)",
        r"rush.*(?:parameter|standard|commercial)",
        r"warren.*(?:common|input|working group)",
        r"kahn.*(?:standard|lte)",
    ]
    components["common_parameters"] = 1.0 if any(re.search(p, lower) for p in param_pats) else 0.0

    conflict_terms = [
        r"(?:tension|conflict|disagree|debate|challenge|concern|oppose)",
        r"(?:agree|consensus|common ground|alignment|shared interest)",
        r"(?:unresolved|open question|outstanding|remain)",
    ]
    ci = sum(1 for t in conflict_terms if re.search(t, lower))
    components["conflicts_identified"] = 1.0 if ci >= 2 else (0.5 if ci >= 1 else 0.0)

    pairs = [
        (r"rush", r"(?:consult|cmr|fcc|parameter)"),
        (r"warren", r"(?:lockheed|defense|military|engineer)"),
        (r"kahn", r"(?:intel|standard|lte)"),
        (r"calabrese", r"(?:new america|small cell|unlicensed|public interest)"),
        (r"povelites", r"(?:at.t|carrier|cost|relocation)"),
    ]
    pf = sum(1 for n, o in pairs if re.search(n, lower) and re.search(o, lower))
    components["member_positions"] = 1.0 if pf >= 3 else (0.5 if pf >= 2 else 0.0)

    weights = {
        "report_created": 0.05,
        "gov_stakeholders": 0.10,
        "commercial_stakeholders": 0.10,
        "sharing_preference": 0.10,
        "relocation_cost": 0.10,
        "sharing_vs_relocation": 0.15,
        "common_parameters": 0.15,
        "conflicts_identified": 0.10,
        "member_positions": 0.15,
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
