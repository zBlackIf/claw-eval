"""Hidden verifier for CP202 — Novel Manuscript Review quality check."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path


def _find_review_file(ws: Path) -> Path | None:
    """Find the review report file in the workspace."""
    # Check common output locations
    candidates = []
    for pattern in ["**/*审查*", "**/*review*", "**/*报告*", "**/*report*"]:
        for p in ws.rglob(pattern.replace("**/*", "")):
            if p.is_file() and p.suffix in (".md", ".txt", ".markdown"):
                # Skip the input criteria file
                if "标准" in p.name or "v2.1" in p.name:
                    continue
                candidates.append(p)

    # Also check top-level .md files that are not the input
    for p in ws.iterdir():
        if p.is_file() and p.suffix == ".md" and p not in candidates:
            if "标准" not in p.name and "v2.1" not in p.name:
                name_lower = p.name.lower()
                if any(k in p.name for k in ["审查", "review", "报告", "report", "重生"]):
                    candidates.append(p)

    # Check fixtures subdir output too
    fixtures_dir = ws / "fixtures" / "manuscript"
    if fixtures_dir.exists():
        for p in fixtures_dir.iterdir():
            if p.is_file() and p.suffix in (".md", ".txt"):
                if "标准" not in p.name and "v2.1" not in p.name and "第三稿" not in p.name:
                    if p not in candidates:
                        candidates.append(p)

    # Sort by modification time (newest first) then size (largest first)
    candidates.sort(key=lambda p: (-p.stat().st_mtime if p.exists() else 0, -p.stat().st_size if p.exists() else 0))
    return candidates[0] if candidates else None


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def grade_workspace(ws: Path) -> dict:
    """Grade the novel review output."""
    components = {k: 0.0 for k in [
        "report_exists",
        "plot_logic_analysis",
        "writing_quality_analysis",
        "ai_traces_detected",
        "placeholder_issue_found",
        "actionable_suggestions",
        "overall_rating_given",
        "compliance_section",
    ]}

    # Find the review file
    review_file = _find_review_file(ws)
    if not review_file:
        # Also check if review was written alongside the manuscript
        for d in [ws, ws / "output", ws / "review", ws / "审查"]:
            if d.exists() and d.is_dir():
                for f in d.iterdir():
                    if f.is_file() and f.suffix in (".md", ".txt") and f.stat().st_size > 500:
                        if "标准" not in f.name and "v2.1" not in f.name and "第三稿" not in f.name:
                            review_file = f
                            break
            if review_file:
                break

    if not review_file or not review_file.exists():
        return {
            "overall_score": 0.0,
            "components": components,
            "reason": "No review report file found in workspace",
        }

    content = _read(review_file)
    if len(content) < 100:
        return {
            "overall_score": 0.0,
            "components": components,
            "reason": f"Review file too short ({len(content)} chars)",
        }

    components["report_exists"] = 1.0

    # Dimension 1: Plot logic analysis (hidden anchor: the novel has specific logic issues)
    # - The timeline is implausibly fast (stock recovery in weeks)
    # - Anonymous forum post with P'd evidence is illegal
    # - Contact with lawyer is suspiciously convenient
    plot_keywords = [
        # Must identify coincidence/convenience issues
        (r"巧合|太巧|不合理|逻辑.*问题|逻辑.*硬伤", 0.3),
        # Must discuss pacing or plot structure
        (r"节奏|铺垫|高潮|转折|爽点", 0.35),
        # Must discuss antagonist weakness or lack of opposition
        (r"反派.*弱|对手.*弱|林正邦.*被动|太容易|阻力.*不足|缺少.*阻力|没有.*反扑", 0.35),
    ]
    plot_score = 0.0
    for pattern, weight in plot_keywords:
        if re.search(pattern, content):
            plot_score += weight
    components["plot_logic_analysis"] = min(1.0, plot_score)

    # Dimension 2: Writing quality analysis
    writing_keywords = [
        # Must identify repetitive phrases
        (r"重复|反复.*出现|多次.*出现|句式.*单调", 0.4),
        # Must discuss dialogue quality
        (r"对话|人物.*语言|台词|口吻|语气", 0.3),
        # Must discuss scene description
        (r"场景|描写|具象|画面感|感官", 0.3),
    ]
    writing_score = 0.0
    for pattern, weight in writing_keywords:
        if re.search(pattern, content):
            writing_score += weight
    components["writing_quality_analysis"] = min(1.0, writing_score)

    # Dimension 3: AI traces detected (KEY HIDDEN ANCHOR)
    # The novel has clear AI writing patterns:
    # - "嘴角弯起一个温和的弧度" appears 4 times (typical AI repetition)
    # - Three-sentence progressive ending ("时间从这里开始...终于轮到...属于...")
    # - "那种颜色" used as placeholder ~8 times
    ai_trace_keywords = [
        # Must catch the "嘴角弯起一个温和的弧度" repetition
        (r"嘴角.*弧度.*重复|温和.*弧度.*多次|弧度.*反复", 0.35),
        # Must catch the three-sentence ending pattern
        (r"三句.*递进|递进.*升华|结尾.*AI|AI.*结尾|排比.*结尾|点题.*刻意", 0.35),
        # General AI trace identification
        (r"AI.*痕迹|AI.*味|机器.*痕迹|套路化|模板化|公式化", 0.3),
    ]
    ai_score = 0.0
    for pattern, weight in ai_trace_keywords:
        if re.search(pattern, content):
            ai_score += weight
    components["ai_traces_detected"] = min(1.0, ai_score)

    # Dimension 4: Placeholder issue identified (CRITICAL HIDDEN ANCHOR)
    # "那种颜色" appears 8 times as an unresolved placeholder
    placeholder_patterns = [
        (r"那种颜色.*占位|占位.*那种颜色|那种颜色.*未替换|那种颜色.*未完成", 0.6),
        (r"那种颜色.*问题|那种颜色.*硬伤|占位符", 0.4),
    ]
    placeholder_score = 0.0
    for pattern, weight in placeholder_patterns:
        if re.search(pattern, content):
            placeholder_score += weight
    components["placeholder_issue_found"] = min(1.0, placeholder_score)

    # Dimension 5: Actionable suggestions provided
    suggestion_indicators = [
        (r"建议|修改|改为|可以改|应该改|推荐", 0.4),
        (r"示范|修改.*示例|改写.*版|参考.*写法", 0.3),
        (r"优先.*修改|高优|必须.*修", 0.3),
    ]
    suggestion_score = 0.0
    for pattern, weight in suggestion_indicators:
        if re.search(pattern, content):
            suggestion_score += weight
    components["actionable_suggestions"] = min(1.0, suggestion_score)

    # Dimension 6: Overall rating given
    rating_patterns = [
        (r"[SABCD][+-]?\s*$|评[级分][:：]\s*[SABCD]|综合.*[SABCD]|等级.*[SABCD]", 0.5),
        (r"\d+\.?\d*/\s*(?:5|10|100)|[★☆⭐]|评分", 0.5),
    ]
    rating_score = 0.0
    for pattern, weight in rating_patterns:
        if re.search(pattern, content, re.MULTILINE):
            rating_score += weight
    components["overall_rating_given"] = min(1.0, rating_score)

    # Dimension 7: Compliance/risk section
    compliance_keywords = [
        # Must address the forged evidence / anonymous defamation issue
        (r"合规|风[控险]|违法|法律|伪造.*证据|P图|匿名.*发帖|诽谤|侵权", 0.5),
        # Must address financial/legal accuracy
        (r"金融.*常识|法律.*常识|股权.*转移.*合理|证监会|公证", 0.5),
    ]
    compliance_score = 0.0
    for pattern, weight in compliance_keywords:
        if re.search(pattern, content):
            compliance_score += weight
    components["compliance_section"] = min(1.0, compliance_score)

    # Overall score with weights
    weights = {
        "report_exists": 0.05,
        "plot_logic_analysis": 0.20,
        "writing_quality_analysis": 0.15,
        "ai_traces_detected": 0.20,
        "placeholder_issue_found": 0.15,
        "actionable_suggestions": 0.10,
        "overall_rating_given": 0.05,
        "compliance_section": 0.10,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "review_file": str(review_file),
        "review_length": len(content),
    }


def main():
    # Try /workspace/fixtures/manuscript/ first, fallback to /workspace/
    ws = Path("/workspace/fixtures/manuscript")
    if not ws.exists():
        ws = Path("/workspace")

    # Actually search the whole workspace for the review output
    result = grade_workspace(Path("/workspace"))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
