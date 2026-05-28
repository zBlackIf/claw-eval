"""Hidden verifier for CP95 — GitHub repo viral analysis report."""
from __future__ import annotations

import json
import re
from pathlib import Path


def grade_workspace(ws: Path) -> dict:
    report = ws / "analysis_report.md"
    if not report.exists():
        for p in ws.rglob("*.md"):
            n = p.name.lower()
            if "analysis" in n or "report" in n:
                report = p
                break
    components = {k: 0.0 for k in [
        "report_exists", "covers_repo_basics", "covers_viral_analysis",
        "covers_evaluation", "report_in_chinese",
    ]}
    if not report.exists():
        return {"overall_score": 0.0, "components": components}

    content = report.read_text(encoding="utf-8", errors="ignore")
    if len(content) >= 1500:
        components["report_exists"] = 1.0
    elif len(content) >= 500:
        components["report_exists"] = 0.5

    repo_kw = ["star", "fork", "karpathy", "claude", "skill"]
    rh = sum(1 for kw in repo_kw if kw.lower() in content.lower())
    components["covers_repo_basics"] = min(rh / 3.0, 1.0)

    viral_kw = ["twitter", "hacker news", "reddit", "social", "viral", "spread",
                "trending", "influencer", "retweet", "share"]
    vh = sum(1 for kw in viral_kw if kw.lower() in content.lower())
    components["covers_viral_analysis"] = min(vh / 3.0, 1.0)

    eval_en = ["limitation", "weakness", "strength", "value", "borrow",
               "suggest", "recommend", "takeaway", "insight"]
    eval_zh = ["局限", "不足", "优势", "价值", "借鉴", "建议", "启示"]
    eh = sum(1 for kw in eval_en if kw.lower() in content.lower())
    eh += sum(1 for kw in eval_zh if kw in content)
    components["covers_evaluation"] = min(eh / 3.0, 1.0)

    cn = len(re.findall(r"[一-鿿]", content))
    ratio = cn / max(len(content), 1)
    if ratio > 0.3:
        components["report_in_chinese"] = 1.0
    elif ratio > 0.1:
        components["report_in_chinese"] = 0.5

    weights = {
        "report_exists": 0.20,
        "covers_repo_basics": 0.20,
        "covers_viral_analysis": 0.25,
        "covers_evaluation": 0.20,
        "report_in_chinese": 0.15,
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
