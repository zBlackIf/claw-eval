"""Hidden verifier for CP58 — AI Coding Evolution HTML slide deck.

Scores /workspace/presentation.html (fallback: slides.html / index.html / *.html)
on 9 anchors: file presence + self-contained + ≥16 slides + cover has AI Coding
+ SDD 4 pillars + keyboard nav + progress indicator + Q&A page + animations.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


HTML_NAMES = ["presentation.html", "slides.html", "index.html"]


def _find_html(ws: Path) -> Path | None:
    for name in HTML_NAMES:
        p = ws / name
        if p.exists():
            return p
    for p in ws.glob("*.html"):
        return p
    return None


def grade_workspace(ws: Path) -> dict:
    html = _find_html(ws)
    components = {k: 0.0 for k in [
        "html_file", "self_contained", "slide_count", "cover_ai_coding",
        "sdd_pillars", "keyboard_nav", "progress_indicator", "thanks_page", "animations",
    ]}
    if not html:
        return {"overall_score": 0.0, "components": components}

    try:
        text = html.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {"overall_score": 0.0, "components": components}

    if len(text) >= 5000:
        components["html_file"] = 1.0
    elif len(text) >= 1500:
        components["html_file"] = 0.5

    external_refs = re.findall(
        r'<(?:link|script)[^>]*(?:href|src)\s*=\s*["\'][^"\']*\.(?:css|js)["\']',
        text, re.I,
    )
    non_font_refs = [r for r in external_refs
                     if not re.search(r"font|icon|cdnjs|googleapis|jsdelivr|highlight", r, re.I)]
    components["self_contained"] = 1.0 if len(non_font_refs) == 0 else (0.5 if len(non_font_refs) <= 2 else 0.0)

    slide_patterns = [
        r'class="[^"]*slide[^"]*"', r"<section[^>]*>", r"data-slide", r'id="slide',
    ]
    slide_count = max(len(re.findall(p, text, re.I)) for p in slide_patterns)
    if slide_count >= 16:
        components["slide_count"] = 1.0
    elif slide_count >= 12:
        components["slide_count"] = 0.6
    elif slide_count >= 8:
        components["slide_count"] = 0.3
    else:
        components["slide_count"] = 0.0

    components["cover_ai_coding"] = 1.0 if ("AI Coding" in text[:6000] or "AI coding" in text[:6000]) else 0.0

    pillars = ["Spec", "Skill", "Rule", "TDD"]
    pillar_hits = sum(1 for p in pillars if p in text)
    components["sdd_pillars"] = pillar_hits / 4.0

    components["keyboard_nav"] = 1.0 if re.search(r"(keydown|keyup|addEventListener.*key|onkeydown|ArrowLeft|ArrowRight)", text, re.I) else 0.0

    components["progress_indicator"] = 1.0 if re.search(r"(progress|page.*count|slide.*number|页码|进度|indicator|pagination)", text, re.I) else 0.0

    components["thanks_page"] = 1.0 if re.search(r"(谢谢|Thank|Q\s*&\s*A|Q&A)", text, re.I) else 0.0

    components["animations"] = 1.0 if re.search(r"(transition|animation|transform|@keyframes|animate)", text, re.I) else 0.0

    weights = {
        "html_file": 0.10,
        "self_contained": 0.10,
        "slide_count": 0.20,
        "cover_ai_coding": 0.10,
        "sdd_pillars": 0.20,
        "keyboard_nav": 0.10,
        "progress_indicator": 0.05,
        "thanks_page": 0.05,
        "animations": 0.10,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "slide_count": slide_count,
        "html_size": len(text),
    }


def main():
    print(json.dumps(grade_workspace(Path("/workspace")), ensure_ascii=False))


if __name__ == "__main__":
    main()
