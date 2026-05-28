"""Hidden verifier for CP75 — GitLab Q3 margin guidance beat/miss analysis."""
from __future__ import annotations

import json
import re
from pathlib import Path


def grade_workspace(ws: Path) -> dict:
    answer = ws / "gitlab_margin_guidance.txt"
    components = {k: 0.0 for k in [
        "file_created", "mentions_metric", "has_actual",
        "has_guidance", "bp_conclusion", "readable",
    ]}
    if not answer.exists():
        return {"overall_score": 0.0, "components": components}

    content = answer.read_text(encoding="utf-8", errors="ignore")
    lower = content.lower()
    components["file_created"] = 1.0

    if "gitlab" in lower and "margin" in lower and ("operating" in lower or "non-gaap" in lower):
        components["mentions_metric"] = 1.0

    if re.search(r"17\.9\s*%|18\s*%|17\.[89]", lower):
        components["has_actual"] = 1.0
    if re.search(r"13\.2\s*%|13\s*%|guidance\s*of\s*1[23]|guided\s*1[23]|five\s*points\s*above", lower):
        components["has_guidance"] = 1.0

    bp_score = 0.0
    if re.search(r"500\s*basis\s*points|500\s*bps|beat\s+by\s+500", lower):
        bp_score = 1.0
    elif re.search(r"4[67]\d\s*basis\s*points|4[67]\d\s*bps|5\s*points?\s*above\s*guidance|beat\s+by\s+5\s*points?", lower):
        bp_score = 0.75
    elif re.search(r"beat", lower) and re.search(r"basis\s*points|bps", lower):
        bp_score = 0.5
    components["bp_conclusion"] = bp_score

    components["readable"] = 1.0 if len(content.strip()) >= 35 else 0.0

    weights = {
        "file_created": 0.05,
        "mentions_metric": 0.15,
        "has_actual": 0.20,
        "has_guidance": 0.20,
        "bp_conclusion": 0.30,
        "readable": 0.10,
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
