"""Hidden verifier for CP194 — Web Scraper with Markdown + Images for Obsidian.

Scoring philosophy: tiered difficulty.
  - EASY checks: script exists, output files present, basic content present.
    Any agent that writes/runs a script should score here.
  - HARD checks (hidden, >= 30% weight): precise image path structure with
    hash-based naming, exact frontmatter field values, per-article image count
    accuracy, code-block language annotation, table column alignment preservation.
    Only strong agents that carefully read the REQUIREMENTS.md and implement
    all details will score on these.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_python_script(ws: Path) -> Path | None:
    """Find the main scraper script."""
    project = ws / "scraper-project"
    candidates = [
        project / "scrape.py",
        project / "scraper.py",
        project / "main.py",
        project / "html_to_md.py",
        project / "convert.py",
        project / "article_scraper.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    # fallback: any .py that imports beautifulsoup4 or markdownify
    for py in project.rglob("*.py"):
        content = _read(py)
        if "BeautifulSoup" in content or "markdownify" in content:
            return py
    # also check workspace root
    for py in ws.rglob("*.py"):
        if py.name.startswith("verify") or "test" in py.name.lower():
            continue
        content = _read(py)
        if "BeautifulSoup" in content or "markdownify" in content:
            return py
    return None


def _find_output_dir(ws: Path) -> Path | None:
    """Find the output directory."""
    project = ws / "scraper-project"
    candidates = [
        project / "output",
        project / "results",
        project / "markdown_output",
        project / "out",
        ws / "output",
        ws / "results",
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    return None


def _find_md_files(ws: Path) -> list[Path]:
    """Find markdown output files."""
    output_dir = _find_output_dir(ws)
    if output_dir:
        return list(output_dir.rglob("*.md"))
    return []


# --- Expected data from the two sample articles ---
EXPECTED_ARTICLES = {
    "health_tech": {
        "title": "AI驱动的患者健康管理创新模式",
        "source": "健康科技前沿",
        "date": "2026-05-10",
        "date_compact": "20260510",
        "image_count": 4,
        "unique_text": ["三层架构设计", "可穿戴设备", "Transformer架构", "2,847名患者"],
        "has_table": True,
        "table_data": ["34.2%", "92.5%", "再入院率"],
        "has_code": True,
        "code_content": "HealthRiskPredictor",
        "headings": ["引言", "技术架构", "核心算法", "临床验证", "结论与展望"],
    },
    "market_report": {
        "title": "2026年医疗大模型行业分析报告",
        "source": "行业洞察周刊",
        "date": "2026-05-15",
        "date_compact": "20260515",
        "image_count": 3,
        "unique_text": ["458亿美元", "字节跳动", "RAG增强检索"],
        "has_table": False,
        "has_code": False,
        "has_blockquote": True,
        "blockquote_text": "临床数据的质量和合规性",
        "headings": ["市场概览", "主要玩家", "技术趋势", "投资热点"],
        "has_ordered_list": True,
    },
}


def grade_workspace(ws: Path) -> dict:
    components = {k: 0.0 for k in [
        # --- Easy tier (all agents should pass) ---
        "script_quality",
        "output_exists",
        "content_fidelity",
        "structural_elements",
        # --- Hard tier (only strong agents pass) ---
        "image_path_precision",
        "frontmatter_exact_values",
        "naming_hash_convention",
        "per_article_image_accuracy",
    ]}

    # --- 1. Script quality (EASY, low weight) ---
    script = _find_python_script(ws)
    if not script:
        return {
            "overall_score": 0.0,
            "components": components,
            "weights": _weights(),
        }

    code = _read(script)
    has_bs4 = "BeautifulSoup" in code or "bs4" in code
    has_md_convert = "markdownify" in code or "markdown" in code.lower()
    has_io = "open(" in code or "write" in code or "Path" in code
    components["script_quality"] = round(
        (0.4 if has_bs4 else 0.0) + (0.3 if has_md_convert else 0.0) + (0.3 if has_io else 0.0),
        4,
    )

    # --- 2. Output exists (EASY) ---
    md_files = _find_md_files(ws)
    if not md_files:
        components["output_exists"] = 0.0
        weights = _weights()
        overall = sum(weights[k] * components[k] for k in weights)
        return {
            "overall_score": round(overall, 4),
            "components": {k: round(v, 4) for k, v in components.items()},
            "weights": weights,
        }

    file_count_score = min(len(md_files) / 2.0, 1.0)
    components["output_exists"] = round(file_count_score, 4)

    # --- 3. Content fidelity (EASY: basic text + structural presence) ---
    all_md_content = "\n".join(_read(f) for f in md_files)
    fidelity_hits = 0
    fidelity_total = 0

    for article_key, expected in EXPECTED_ARTICLES.items():
        for text_fragment in expected["unique_text"]:
            fidelity_total += 1
            if text_fragment in all_md_content:
                fidelity_hits += 1

    # Table data from health_tech article
    for td in EXPECTED_ARTICLES["health_tech"]["table_data"]:
        fidelity_total += 1
        if td in all_md_content:
            fidelity_hits += 1

    # Code block content
    fidelity_total += 1
    if EXPECTED_ARTICLES["health_tech"]["code_content"] in all_md_content:
        fidelity_hits += 1

    # Blockquote content
    fidelity_total += 1
    if EXPECTED_ARTICLES["market_report"]["blockquote_text"] in all_md_content:
        fidelity_hits += 1

    components["content_fidelity"] = round(fidelity_hits / max(fidelity_total, 1), 4)

    # --- 4. Structural elements (EASY: headings, lists, tables present) ---
    struct_checks = 0
    struct_hits = 0

    for article_key, expected in EXPECTED_ARTICLES.items():
        for heading in expected["headings"][:3]:
            struct_checks += 1
            if re.search(r'^#{2,3}\s+.*' + re.escape(heading), all_md_content, re.MULTILINE):
                struct_hits += 1

    struct_checks += 1
    if re.search(r'\|.*\|.*\|', all_md_content) and "---" in all_md_content:
        struct_hits += 1

    struct_checks += 1
    if "```" in all_md_content and "HealthRiskPredictor" in all_md_content:
        struct_hits += 1

    struct_checks += 1
    if re.search(r'^>\s+', all_md_content, re.MULTILINE):
        struct_hits += 1

    struct_checks += 1
    if re.search(r'^\d+\.\s+', all_md_content, re.MULTILINE):
        struct_hits += 1

    struct_checks += 1
    if re.search(r'^[-*]\s+', all_md_content, re.MULTILINE):
        struct_hits += 1

    components["structural_elements"] = round(struct_hits / max(struct_checks, 1), 4)

    # =========================================================================
    # HARD TIER — hidden checks that discriminate strong from weak agents
    # =========================================================================

    output_dir = _find_output_dir(ws)

    # --- 5. Image path precision (HARD) ---
    # Requirements specify: images/{date}_{source}_{first8chars_of_md5(title)}/img_N.ext
    # Weak agents just dump images/ or use wrong naming.
    img_refs = re.findall(r'!\[.*?\]\(([^)]+)\)', all_md_content)
    img_precision_score = 0.0

    if img_refs:
        # Has image refs at all
        img_precision_score += 0.1

        # All refs use relative paths (not http/absolute)
        relative_refs = [r for r in img_refs if not r.startswith("http") and not r.startswith("/")]
        if len(relative_refs) == len(img_refs):
            img_precision_score += 0.1

        # Refs start with images/ prefix
        images_prefix_refs = [r for r in img_refs if r.startswith("images/")]
        if images_prefix_refs and len(images_prefix_refs) == len(img_refs):
            img_precision_score += 0.1

        # Three-level path: images/subfolder/file.ext
        deep_refs = [r for r in img_refs if len(r.split("/")) >= 3]
        if deep_refs and len(deep_refs) == len(img_refs):
            img_precision_score += 0.15

        # Subfolder contains hash component (8-char hex from md5 of title)
        # Expected hashes:
        expected_hashes = {}
        for ak, av in EXPECTED_ARTICLES.items():
            h = hashlib.md5(av["title"].encode("utf-8")).hexdigest()[:8]
            expected_hashes[ak] = h

        hash_found_count = 0
        for href in img_refs:
            parts = href.split("/")
            if len(parts) >= 2:
                folder_name = parts[1]  # images/{folder}/file
                for h in expected_hashes.values():
                    if h in folder_name:
                        hash_found_count += 1
                        break

        if hash_found_count > 0:
            hash_ratio = hash_found_count / len(img_refs)
            img_precision_score += 0.25 * hash_ratio

        # Subfolder contains date component (YYYYMMDD)
        date_in_folder = 0
        for href in img_refs:
            parts = href.split("/")
            if len(parts) >= 2:
                folder_name = parts[1]
                if re.search(r'\d{8}', folder_name):
                    date_in_folder += 1
        if date_in_folder > 0:
            img_precision_score += 0.1 * min(date_in_folder / len(img_refs), 1.0)

        # Image filenames follow img_N pattern
        img_n_count = 0
        for href in img_refs:
            fname = href.split("/")[-1]
            if re.match(r'img_\d+\.\w+', fname):
                img_n_count += 1
        if img_n_count > 0:
            img_precision_score += 0.1 * min(img_n_count / len(img_refs), 1.0)

    # Also verify images dir structure on disk
    if output_dir:
        img_dir = output_dir / "images"
        if img_dir.exists() and img_dir.is_dir():
            subdirs = [d for d in img_dir.iterdir() if d.is_dir()]
            if len(subdirs) >= 2:
                # Two separate per-article image directories
                img_precision_score = min(img_precision_score + 0.05, 1.0)
                # Check placeholder files exist
                total_placeholders = sum(1 for sd in subdirs for f in sd.iterdir() if f.is_file())
                if total_placeholders >= 5:  # expect 7 total
                    img_precision_score = min(img_precision_score + 0.05, 1.0)

    components["image_path_precision"] = round(min(img_precision_score, 1.0), 4)

    # --- 6. Frontmatter exact values (HARD) ---
    # Not just "has frontmatter" but exact field values matching source data.
    fm_exact_score = 0.0
    fm_exact_checks = 0
    fm_exact_hits = 0

    for md_file in md_files:
        content = _read(md_file)
        if not content.startswith("---"):
            continue

        end = content.find("---", 3)
        if end < 0:
            continue

        fm_block = content[3:end]

        # title field matches an expected title exactly
        fm_exact_checks += 1
        title_match = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', fm_block, re.MULTILINE)
        if title_match:
            title_val = title_match.group(1).strip().strip('"').strip("'")
            for expected in EXPECTED_ARTICLES.values():
                if title_val == expected["title"]:
                    fm_exact_hits += 1
                    break

        # date field matches expected date exactly (YYYY-MM-DD)
        fm_exact_checks += 1
        date_match = re.search(r'^date:\s*["\']?(.+?)["\']?\s*$', fm_block, re.MULTILINE)
        if date_match:
            date_val = date_match.group(1).strip().strip('"').strip("'")
            for expected in EXPECTED_ARTICLES.values():
                if date_val == expected["date"]:
                    fm_exact_hits += 1
                    break

        # source field matches expected source exactly
        fm_exact_checks += 1
        source_match = re.search(r'^source:\s*["\']?(.+?)["\']?\s*$', fm_block, re.MULTILINE)
        if source_match:
            source_val = source_match.group(1).strip().strip('"').strip("'")
            for expected in EXPECTED_ARTICLES.values():
                if source_val == expected["source"]:
                    fm_exact_hits += 1
                    break

        # url field is present (even if empty for local files)
        fm_exact_checks += 1
        url_match = re.search(r'^url:\s*', fm_block, re.MULTILINE)
        if url_match:
            fm_exact_hits += 1

    if fm_exact_checks > 0:
        fm_exact_score = fm_exact_hits / fm_exact_checks
    else:
        # No frontmatter at all — 0
        fm_exact_score = 0.0

    components["frontmatter_exact_values"] = round(min(fm_exact_score, 1.0), 4)

    # --- 7. Naming convention with hash (HARD) ---
    # REQUIREMENTS.md specifies: {date}_{source}_{title}.md for files,
    # and {date}_{source}_{first8chars_of_md5(article_title)}/ for image dirs.
    # This checks filename precision beyond just "starts with 8 digits".
    naming_score = 0.0
    naming_checks = 0
    naming_hits = 0

    for md_file in md_files:
        name = md_file.stem

        # Check YYYYMMDD prefix with correct date
        naming_checks += 1
        date_match_in_name = re.match(r'^(\d{8})', name)
        if date_match_in_name:
            date_part = date_match_in_name.group(1)
            if date_part in ("20260510", "20260515"):
                naming_hits += 1

        # Check source component is present and correct
        naming_checks += 1
        for expected in EXPECTED_ARTICLES.values():
            if expected["source"] in name:
                naming_hits += 1
                break

        # Check title component is present (not empty, > 2 chars after source)
        naming_checks += 1
        parts = name.split('_', 2)
        if len(parts) >= 3 and len(parts[2]) > 2:
            naming_hits += 1

        # Check underscore-separated three-part structure (date_source_title)
        naming_checks += 1
        if re.match(r'^\d{8}_.+_.+', name):
            naming_hits += 1

    # Also check image directory naming follows convention
    if output_dir:
        img_dir = output_dir / "images"
        if img_dir.exists():
            subdirs = [d for d in img_dir.iterdir() if d.is_dir()]
            for sd in subdirs:
                naming_checks += 1
                sd_name = sd.name
                # Should contain date + source + hash
                has_date = bool(re.search(r'\d{8}', sd_name))
                has_hash_like = bool(re.search(r'[0-9a-f]{8}', sd_name))
                if has_date and has_hash_like:
                    naming_hits += 1
                elif has_date:
                    naming_hits += 0.5  # partial: has date but no hash

    components["naming_hash_convention"] = round(naming_hits / max(naming_checks, 1), 4)

    # --- 8. Per-article image accuracy (HARD) ---
    # Each article has a specific number of images (4 and 3).
    # Strong agents get the exact count per article right.
    img_acc_score = 0.0

    # Try to match images to articles by checking which article's content
    # appears near the image refs, or by folder association
    for md_file in md_files:
        content = _read(md_file)
        file_img_refs = re.findall(r'!\[.*?\]\(([^)]+)\)', content)

        if not file_img_refs:
            continue

        # Identify which article this file corresponds to
        matched_article = None
        for ak, av in EXPECTED_ARTICLES.items():
            if av["title"] in content or av["source"] in content:
                matched_article = ak
                break
            # Also check unique text
            for txt in av["unique_text"][:2]:
                if txt in content:
                    matched_article = ak
                    break
            if matched_article:
                break

        if matched_article:
            expected_count = EXPECTED_ARTICLES[matched_article]["image_count"]
            actual_count = len(file_img_refs)
            if actual_count == expected_count:
                img_acc_score += 0.5  # exact match per article
            elif abs(actual_count - expected_count) <= 1:
                img_acc_score += 0.2  # off by one

    components["per_article_image_accuracy"] = round(min(img_acc_score, 1.0), 4)

    weights = _weights()
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def _weights() -> dict:
    """Weights sum to 1.0. Hard tier (hidden) >= 30%."""
    return {
        # --- Easy tier: 65% ---
        "script_quality": 0.05,          # Having a script with right imports
        "output_exists": 0.10,           # Script ran and produced output
        "content_fidelity": 0.25,        # Article text preserved
        "structural_elements": 0.25,     # MD headings/tables/code/lists
        # --- Hard tier: 35% (hidden discrimination) ---
        "image_path_precision": 0.12,    # Exact image path structure
        "frontmatter_exact_values": 0.10,  # Field values match source exactly
        "naming_hash_convention": 0.07,  # Filename + image dir hash naming
        "per_article_image_accuracy": 0.06,  # Correct image count per article
    }


def main():
    # Try /workspace/fixtures/scraper-project first, fallback to /workspace/scraper-project
    ws = Path("/workspace/fixtures")
    if not (ws / "scraper-project").exists():
        ws = Path("/workspace")
    if not (ws / "scraper-project").exists():
        # Also try if output is directly in /workspace
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
