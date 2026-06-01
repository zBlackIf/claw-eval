"""Hidden verifier for CP116 — HEARTBEAT Protocol Task Dispatch."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_heartbeat(ws: Path) -> Path | None:
    """Find HEARTBEAT.md in the workspace tree."""
    candidates = [
        ws / "HEARTBEAT.md",
        ws / "workspace" / "HEARTBEAT.md",
        ws / "fixtures" / "workspace" / "HEARTBEAT.md",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _find_output_dir(ws: Path) -> Path | None:
    """Find the output/ directory where agent wrote results."""
    candidates = [
        ws / "output",
        ws / "workspace" / "output",
        ws / "fixtures" / "workspace" / "output",
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    return None


def _check_heartbeat_status(ws: Path) -> float:
    """Check that HEARTBEAT.md was updated to DONE status with results."""
    hb_path = _find_heartbeat(ws)
    if not hb_path:
        return 0.0

    content = _read(hb_path)
    score = 0.0

    # Must have Status: DONE
    if re.search(r"Status:\s*DONE", content, re.IGNORECASE):
        score += 0.5
    elif re.search(r"Status:\s*(COMPLETED|FINISHED|COMPLETE)", content, re.IGNORECASE):
        score += 0.4

    # Must have a Results section
    if re.search(r"##\s*Results?", content, re.IGNORECASE):
        score += 0.3
        # Should mention at least 3 book titles or ratings
        rating_mentions = len(re.findall(r"[123]级|Level\s*[123]|过时|部分有效|经典|Outdated|Partially|Classic", content, re.IGNORECASE))
        if rating_mentions >= 4:
            score += 0.2
        elif rating_mentions >= 2:
            score += 0.1

    return min(score, 1.0)


def _check_output_files(ws: Path) -> tuple[float, dict]:
    """Check that output files were created with correct names and content."""
    output_dir = _find_output_dir(ws)
    if not output_dir:
        return 0.0, {}

    expected_files = {
        "book-erta-kuang-jia-shi-zhan-zhi-nan.md": {"level": 1, "title": "ERTA 框架实战指南"},
        "book-suan-fa-she-ji-yu-fen-xi-ji-chu.md": {"level": 3, "title": "算法设计与分析基础"},
        "book-deep-learning-with-tensorflow-1-x.md": {"level": 1, "title": "Deep Learning with TensorFlow 1.x"},
        "book-ji-suan-ji-cheng-xu-de-gou-zao-he-jie-shi.md": {"level": 3, "title": "计算机程序的构造和解释"},
        "book-python-shu-ju-ke-xue-shi-zhan.md": {"level": 2, "title": "Python数据科学实战"},
    }

    file_scores = {}
    total_score = 0.0

    for filename, meta in expected_files.items():
        file_path = output_dir / filename
        if not file_path.exists():
            # Try alternative filename patterns
            alt_found = False
            for f in output_dir.iterdir():
                fname_lower = f.name.lower()
                title_slug = filename.replace("book-", "").replace(".md", "")
                if title_slug[:8] in fname_lower and f.suffix == ".md":
                    file_path = f
                    alt_found = True
                    break
            if not alt_found:
                file_scores[filename] = 0.0
                continue

        content = _read(file_path)
        fscore = 0.0

        # Has frontmatter
        if content.startswith("---") and content.count("---") >= 2:
            fscore += 0.2

            # Check frontmatter fields
            fm_section = content.split("---")[1]
            if "title:" in fm_section:
                fscore += 0.1
            if "tags:" in fm_section or "tag:" in fm_section:
                fscore += 0.05
            if "categories:" in fm_section or "category:" in fm_section:
                fscore += 0.05
            if "rating_level:" in fm_section or "rating:" in fm_section:
                fscore += 0.1

        # Check correct rating level
        level = meta["level"]
        level_patterns = {
            1: [r"rating_level:\s*1", r"1级", r"过时", r"[Oo]utdated", r"Level\s*1"],
            2: [r"rating_level:\s*2", r"2级", r"部分有效", r"[Pp]artially", r"Level\s*2"],
            3: [r"rating_level:\s*3", r"3级", r"经典", r"[Cc]lassic", r"Level\s*3"],
        }
        for pat in level_patterns[level]:
            if re.search(pat, content):
                fscore += 0.3
                break

        # Has chapter/content section
        if re.search(r"(章|chapter|有价值|valuable)", content, re.IGNORECASE):
            fscore += 0.1

        # Has cleanup suggestion
        if re.search(r"(清理|建议|cleanup|suggest)", content, re.IGNORECASE):
            fscore += 0.1

        file_scores[filename] = min(fscore, 1.0)
        total_score += file_scores[filename]

    # Normalize: all 5 files expected
    return total_score / 5.0, file_scores


def _check_rating_accuracy(ws: Path) -> float:
    """Check that the rating logic was applied correctly (hidden discrimination check)."""
    output_dir = _find_output_dir(ws)
    if not output_dir:
        return 0.0

    # Key discrimination checks:
    # 1. ERTA framework book MUST be Level 1 (specific framework, >8 years, dead)
    # 2. Algorithm book MUST be Level 3 (algo/DS topic, rating 8.9 >= 8.0)
    # 3. TensorFlow 1.x MUST be Level 1 (specific version, >8 years, deprecated)
    # 4. SICP MUST be Level 3 (fundamental CS, rating 9.5 >= 9.0)
    # 5. Python DS book MUST be Level 2 (within 5 years, default)

    expected_ratings = [
        ("erta", 1),
        ("suan-fa", 3),
        ("tensorflow", 1),
        ("gou-zao-he-jie-shi", 3),
        ("python", 2),
    ]

    correct = 0
    total = len(expected_ratings)

    for slug_part, expected_level in expected_ratings:
        found = False
        for f in output_dir.iterdir():
            if slug_part in f.name.lower() and f.suffix == ".md":
                content = _read(f)
                level_patterns = {
                    1: [r"rating_level:\s*1", r"1级", r"过时", r"[Oo]utdated", r"Level\s*1"],
                    2: [r"rating_level:\s*2", r"2级", r"部分有效", r"[Pp]artially", r"Level\s*2"],
                    3: [r"rating_level:\s*3", r"3级", r"经典", r"[Cc]lassic", r"Level\s*3"],
                }
                for pat in level_patterns[expected_level]:
                    if re.search(pat, content):
                        correct += 1
                        found = True
                        break
                if found:
                    break
                break

    return correct / total


def _check_filename_convention(ws: Path) -> float:
    """Check filename convention (pinyin with hyphens for Chinese, lowercase for English)."""
    output_dir = _find_output_dir(ws)
    if not output_dir:
        return 0.0

    md_files = [f for f in output_dir.iterdir() if f.suffix == ".md"]
    if not md_files:
        return 0.0

    score = 0.0
    expected_count = 5

    # Check that filenames follow the convention
    good_patterns = [
        r"^book-[a-z0-9]([a-z0-9-]*[a-z0-9])?\.md$",
    ]

    for f in md_files:
        if any(re.match(pat, f.name) for pat in good_patterns):
            if f.name.startswith("book-"):
                score += 0.8 / expected_count
                # Bonus: no consecutive hyphens, no trailing hyphen before .md
                if "--" not in f.name and not f.name.endswith("-.md"):
                    score += 0.2 / expected_count

    return min(score, 1.0)


def grade_workspace(ws: Path) -> dict:
    components = {}

    # Dimension 1: HEARTBEAT.md protocol compliance (0.20)
    components["heartbeat_updated"] = _check_heartbeat_status(ws)

    # Dimension 2: Output file generation (0.30)
    output_score, file_details = _check_output_files(ws)
    components["output_files_generated"] = output_score

    # Dimension 3: Rating accuracy (0.25) - KEY DISCRIMINATION
    components["rating_accuracy"] = _check_rating_accuracy(ws)

    # Dimension 4: Filename convention (0.15)
    components["filename_convention"] = _check_filename_convention(ws)

    # Dimension 5: Queue completeness (0.10)
    output_dir = _find_output_dir(ws)
    md_count = len([f for f in output_dir.iterdir() if f.suffix == ".md"]) if output_dir else 0
    components["queue_completeness"] = min(md_count / 5.0, 1.0)

    weights = {
        "heartbeat_updated": 0.20,
        "output_files_generated": 0.30,
        "rating_accuracy": 0.25,
        "filename_convention": 0.15,
        "queue_completeness": 0.10,
    }

    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "file_details": {k: round(v, 4) for k, v in file_details.items()} if file_details else {},
    }


def main():
    # The sandbox_files land at /workspace/fixtures/workspace/
    # The agent will see them there and create output/ relative to that location
    # But the agent might also create output at /workspace/output/ or /workspace/fixtures/workspace/output/
    # We search multiple locations via _find_output_dir / _find_heartbeat
    ws = Path("/workspace/fixtures/workspace")
    if not ws.exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
