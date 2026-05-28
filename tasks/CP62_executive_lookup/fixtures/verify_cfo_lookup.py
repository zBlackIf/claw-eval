"""Hidden verifier for CP62 — GitLab CFO Executive Lookup.

Truth anchor: Jessica Ross (announced early 2026).
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def grade_workspace(ws: Path) -> dict:
    answer = ws / "gitlab_cfo.txt"
    content = _read(answer)
    lower = content.lower()

    components = {k: 0.0 for k in [
        "file_created", "correct_name", "mentions_role",
        "has_date_or_source", "readable",
    ]}

    if not content.strip():
        return {"overall_score": 0.0, "components": components}

    components["file_created"] = 1.0
    components["correct_name"] = 1.0 if "jessica ross" in lower else 0.0
    components["mentions_role"] = 1.0 if ("gitlab" in lower and ("cfo" in lower or "chief financial" in lower)) else 0.0
    if re.search(r"2026|march\s*3,\s*2026|april\s*7,\s*2026|source|press release|investor|reuters|bloomberg", lower):
        components["has_date_or_source"] = 1.0
    if len(content.strip()) >= 20 and len(content.splitlines()) >= 1:
        components["readable"] = 1.0

    weights = {
        "file_created": 0.10,
        "correct_name": 0.40,
        "mentions_role": 0.15,
        "has_date_or_source": 0.25,
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
