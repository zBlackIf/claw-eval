"""Hidden verifier for CP198 — Book Catalog Scraper + Markdown Generator."""
from __future__ import annotations

import ast
import json
import os
import re
import sys
from pathlib import Path


def _find_output_dir() -> Path:
    """Find the output directory - check multiple possible locations."""
    candidates = [
        Path("/workspace/fixtures/book_catalog/output"),
        Path("/workspace/book_catalog/output"),
        Path("/workspace/output"),
        Path("/workspace/fixtures/output"),
    ]
    for c in candidates:
        if c.exists() and any(c.iterdir()):
            return c
    return candidates[0]


def _find_script() -> Path | None:
    """Find the scraper/crawler script."""
    search_dirs = [
        Path("/workspace/fixtures/book_catalog"),
        Path("/workspace/book_catalog"),
        Path("/workspace/fixtures"),
        Path("/workspace"),
    ]
    for d in search_dirs:
        if not d.exists():
            continue
        for f in d.rglob("*.py"):
            if f.name.startswith("verify"):
                continue
            content = f.read_text(encoding="utf-8", errors="ignore")
            if "book-item" in content or "book_item" in content or "book-list" in content or "BeautifulSoup" in content or "html.parser" in content or "lxml" in content:
                return f
    return None


def _find_markdown_files() -> list[Path]:
    """Find generated markdown output files."""
    md_files = []
    search_dirs = [
        Path("/workspace/fixtures/book_catalog"),
        Path("/workspace/book_catalog"),
        Path("/workspace/fixtures"),
        Path("/workspace"),
    ]
    for d in search_dirs:
        if not d.exists():
            continue
        for f in d.rglob("*.md"):
            content = f.read_text(encoding="utf-8", errors="ignore")
            if any(title in content for title in ["三体", "刘慈欣", "球状闪电", "流浪地球"]):
                md_files.append(f)
    return md_files


def _find_json_data() -> list[Path]:
    """Find intermediate JSON data files."""
    json_files = []
    search_dirs = [
        Path("/workspace/fixtures/book_catalog"),
        Path("/workspace/book_catalog"),
        Path("/workspace/fixtures"),
        Path("/workspace"),
    ]
    for d in search_dirs:
        if not d.exists():
            continue
        for f in d.rglob("*.json"):
            if f.name.startswith("verify") or "package" in f.name:
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8", errors="ignore"))
                if isinstance(data, list) and len(data) > 0:
                    if isinstance(data[0], dict) and any(k in data[0] for k in ["title", "isbn", "book_id", "name"]):
                        json_files.append(f)
            except (json.JSONDecodeError, Exception):
                continue
    return json_files


# Expected book metadata for strict validation
EXPECTED_BOOKS_FULL = [
    {"title": "三体", "isbn": "978-7-5366-9293-0", "date": "2008-01-01", "genre": "硬科幻", "pages": 302},
    {"title": "黑暗森林", "isbn": "978-7-5366-9923-6", "date": "2008-05-01", "genre": "硬科幻", "pages": 400},
    {"title": "死神永生", "isbn": "978-7-5366-9880-2", "date": "2010-11-01", "genre": "硬科幻", "pages": 513},
    {"title": "球状闪电", "isbn": "978-7-5366-7059-4", "date": "2005-06-01", "genre": "硬科幻", "pages": 291},
    {"title": "超新星纪元", "isbn": "978-7-5366-5645-1", "date": "2003-01-01", "genre": "软科幻", "pages": 293},
    {"title": "流浪地球", "isbn": "978-7-5357-3226-8", "date": "2000-07-01", "genre": "硬科幻", "pages": 36},
    {"title": "乡村教师", "isbn": "978-7-5357-3226-8", "date": "2001-01-01", "genre": "软科幻", "pages": 28},
    {"title": "带上她的眼睛", "isbn": "978-7-5357-4110-9", "date": "1999-03-01", "genre": "软科幻", "pages": 18},
    {"title": "全频带阻塞干扰", "isbn": "978-7-5366-6012-0", "date": "2001-12-01", "genre": "军事科幻", "pages": 42},
    {"title": "朝闻道", "isbn": "978-7-5366-6200-1", "date": "2002-06-01", "genre": "硬科幻", "pages": 22},
    {"title": "镜子", "isbn": "978-7-5366-7100-3", "date": "2004-12-01", "genre": "软科幻", "pages": 32},
    {"title": "赡养人类", "isbn": "978-7-5366-7500-1", "date": "2005-11-01", "genre": "硬科幻", "pages": 38},
]

# Correct descending date order
CORRECT_ORDER = [
    "死神永生",       # 2010-11-01
    "黑暗森林",       # 2008-05-01
    "三体",           # 2008-01-01
    "赡养人类",       # 2005-11-01
    "球状闪电",       # 2005-06-01
    "镜子",           # 2004-12-01
    "超新星纪元",     # 2003-01-01
    "朝闻道",         # 2002-06-01
    "全频带阻塞干扰", # 2001-12-01
    "乡村教师",       # 2001-01-01
    "流浪地球",       # 2000-07-01
    "带上她的眼睛",   # 1999-03-01
]

EXPECTED_TITLES = [b["title"] for b in EXPECTED_BOOKS_FULL]


def grade_workspace() -> dict:
    components = {
        "scraper_exists": 0.0,
        "pagination_handled": 0.0,
        "all_books_extracted": 0.0,
        "markdown_generated": 0.0,
        "markdown_structure": 0.0,
        "date_sorting": 0.0,
        "metadata_completeness": 0.0,
        "script_quality": 0.0,
        "author_bio_in_md": 0.0,
        "tags_structured": 0.0,
        "synopsis_fidelity": 0.0,
        "data_id_captured": 0.0,
    }

    # 1. Check scraper script exists and has proper parsing logic
    script = _find_script()
    script_content = ""
    if script:
        script_content = script.read_text(encoding="utf-8", errors="ignore")
        has_html_parsing = any(lib in script_content for lib in [
            "BeautifulSoup", "html.parser", "lxml", "selectolax",
            "parsel", "HTMLParser", "etree"
        ])
        has_file_reading = "open(" in script_content or "read_text" in script_content or "Path(" in script_content
        has_css_or_xpath = any(sel in script_content for sel in [
            "find_all", "select", "find(", "css(", "xpath(",
            "book-item", "book_item", "book-list", "book_list"
        ])
        score = 0.0
        if has_html_parsing:
            score += 0.4
        if has_file_reading:
            score += 0.3
        if has_css_or_xpath:
            score += 0.3
        components["scraper_exists"] = min(1.0, score)

        # 2. Check pagination handling
        pagination_indicators = [
            "page" in script_content.lower() and ("1" in script_content or "range" in script_content),
            "page2" in script_content or "page3" in script_content,
            "pagination" in script_content.lower(),
            "next" in script_content.lower() and "page" in script_content.lower(),
            "for" in script_content and "page" in script_content,
            "glob" in script_content and "page" in script_content,
        ]
        if sum(pagination_indicators) >= 2:
            components["pagination_handled"] = 1.0
        elif sum(pagination_indicators) >= 1:
            components["pagination_handled"] = 0.5

    # 3. Check all 12 books extracted (via JSON or MD)
    json_files = _find_json_data()
    md_files = _find_markdown_files()

    found_books = set()

    # Check JSON
    json_data_all: list[dict] = []
    for jf in json_files:
        try:
            data = json.loads(jf.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        title = item.get("title", "") or item.get("name", "") or ""
                        for eb in EXPECTED_TITLES:
                            if eb in title:
                                found_books.add(eb)
                                json_data_all.append(item)
        except Exception:
            pass

    # Check MD
    for mf in md_files:
        content = mf.read_text(encoding="utf-8", errors="ignore")
        for eb in EXPECTED_TITLES:
            if eb in content:
                found_books.add(eb)

    if len(found_books) >= 12:
        components["all_books_extracted"] = 1.0
    elif len(found_books) >= 9:
        components["all_books_extracted"] = 0.75
    elif len(found_books) >= 5:
        components["all_books_extracted"] = 0.5
    elif len(found_books) >= 1:
        components["all_books_extracted"] = 0.25
    else:
        components["all_books_extracted"] = 0.0

    # 4. Check markdown generation
    if md_files:
        components["markdown_generated"] = 1.0

        # 5. Check markdown structure quality
        best_score = 0.0
        for mf in md_files:
            content = mf.read_text(encoding="utf-8", errors="ignore")
            score = 0.0
            if "#" in content:
                score += 0.15
            if content.count("##") >= 3 or content.count("**") >= 6:
                score += 0.15
            isbn_count = content.lower().count("isbn") + content.count("978-")
            if isbn_count >= 10:
                score += 0.2
            elif isbn_count >= 5:
                score += 0.15
            elif isbn_count >= 1:
                score += 0.05
            genre_count = sum(1 for g in ["硬科幻", "软科幻", "军事科幻"] if g in content)
            if genre_count >= 3:
                score += 0.2
            elif genre_count >= 2:
                score += 0.15
            elif genre_count >= 1:
                score += 0.05
            # Check pages info present
            pages_count = len(re.findall(r'\d+\s*页', content))
            if pages_count >= 10:
                score += 0.15
            elif pages_count >= 5:
                score += 0.1
            # Check synopsis/description presence (substantial content)
            if len(content) > 4000:
                score += 0.15
            elif len(content) > 2000:
                score += 0.1
            elif len(content) > 500:
                score += 0.05
            best_score = max(best_score, score)
        components["markdown_structure"] = min(1.0, best_score)

        # 6. Check date sorting - STRICT version
        for mf in md_files:
            content = mf.read_text(encoding="utf-8", errors="ignore")
            # Find the order of book titles as they appear in the markdown
            title_positions = []
            for title in CORRECT_ORDER:
                pos = content.find(title)
                if pos >= 0:
                    title_positions.append((pos, title))
            title_positions.sort(key=lambda x: x[0])
            actual_order = [t[1] for t in title_positions]

            if len(actual_order) >= 10:
                # Check strict descending order
                correct_subset = [t for t in CORRECT_ORDER if t in actual_order]
                # Count inversions (pairs out of order)
                inversions = 0
                total_pairs = 0
                for i in range(len(actual_order)):
                    for j in range(i + 1, len(actual_order)):
                        total_pairs += 1
                        idx_i = CORRECT_ORDER.index(actual_order[i]) if actual_order[i] in CORRECT_ORDER else -1
                        idx_j = CORRECT_ORDER.index(actual_order[j]) if actual_order[j] in CORRECT_ORDER else -1
                        if idx_i >= 0 and idx_j >= 0 and idx_i > idx_j:
                            inversions += 1
                if total_pairs > 0:
                    correctness = 1.0 - (inversions / total_pairs)
                    if correctness >= 0.95:
                        components["date_sorting"] = 1.0
                    elif correctness >= 0.8:
                        components["date_sorting"] = 0.6
                    elif correctness >= 0.5:
                        components["date_sorting"] = 0.3
                    else:
                        components["date_sorting"] = 0.1
                break
            elif len(actual_order) >= 5:
                # Partial ordering check
                components["date_sorting"] = 0.3
                break

    # --- HIDDEN CHECKS (harder to max out) ---

    # 7. Metadata completeness in JSON — checks that ALL fields are properly extracted per book
    if json_data_all:
        required_fields = {"title", "isbn", "date", "genre", "pages", "synopsis", "tags"}
        # Accept common aliases
        field_aliases = {
            "title": ["title", "name", "book_title", "书名"],
            "isbn": ["isbn", "ISBN", "book_id"],
            "date": ["date", "pub_date", "publication_date", "publish_date", "出版日期"],
            "genre": ["genre", "type", "category", "类型"],
            "pages": ["pages", "page_count", "页数"],
            "synopsis": ["synopsis", "description", "summary", "intro", "简介", "content"],
            "tags": ["tags", "tag", "labels", "标签"],
        }

        total_field_score = 0.0
        books_checked = 0
        for item in json_data_all:
            if not isinstance(item, dict):
                continue
            books_checked += 1
            item_keys_lower = {k.lower() for k in item.keys()}
            fields_present = 0
            for field, aliases in field_aliases.items():
                for alias in aliases:
                    if alias.lower() in item_keys_lower:
                        # Check the value is non-empty
                        val = item.get(alias) or item.get(alias.lower()) or ""
                        # Try case-insensitive key match
                        for k, v in item.items():
                            if k.lower() == alias.lower() and v:
                                val = v
                                break
                        if val:
                            fields_present += 1
                            break
            total_field_score += fields_present / len(required_fields)

        if books_checked > 0:
            avg_completeness = total_field_score / min(books_checked, 12)
            # Only give full score if nearly all fields present across all books
            if avg_completeness >= 0.95:
                components["metadata_completeness"] = 1.0
            elif avg_completeness >= 0.8:
                components["metadata_completeness"] = 0.7
            elif avg_completeness >= 0.6:
                components["metadata_completeness"] = 0.4
            else:
                components["metadata_completeness"] = 0.2
    else:
        # No JSON intermediate — partial credit if markdown has the info
        # but penalize for not following the instruction about JSON intermediate
        components["metadata_completeness"] = 0.0

    # 8. Script quality — compilable, proper error handling, no hardcoded absolute paths to wrong dirs
    if script_content:
        quality_score = 0.0

        # Check if script compiles without syntax errors
        try:
            ast.parse(script_content)
            quality_score += 0.3
        except SyntaxError:
            quality_score += 0.0

        # Check for proper error handling (try/except around file ops or parsing)
        if "try:" in script_content and "except" in script_content:
            quality_score += 0.2

        # Check for encoding handling (utf-8 specified in open calls)
        if "utf-8" in script_content or "encoding" in script_content:
            quality_score += 0.2

        # Check that tags are extracted as list/array (not dumped as raw string)
        # Look for list comprehension or split or proper tag extraction
        tag_handling = any(pattern in script_content for pattern in [
            "find_all", ".text", "get_text", "strip()", "[tag",
            "tags.append", "tag_list", "tag_names",
            "for tag in", "for t in", ".tags", "find('span')",
        ])
        if tag_handling:
            quality_score += 0.15

        # Check for proper main guard or function structure
        if "def " in script_content and ("if __name__" in script_content or "main()" in script_content):
            quality_score += 0.15
        elif "def " in script_content:
            quality_score += 0.1

        components["script_quality"] = min(1.0, quality_score)

    # 9. Author bio inclusion in markdown (task explicitly asks for 作者简介)
    if md_files:
        bio_score = 0.0
        for mf in md_files:
            content = mf.read_text(encoding="utf-8", errors="ignore")
            # Check for actual bio content from the HTML
            has_bio_section = any(marker in content for marker in [
                "作者简介", "作者介绍", "关于作者", "Author", "作者信息"
            ])
            has_bio_content = "雨果奖" in content and ("1963" in content or "北京" in content or "华北水利" in content)
            has_works_count = "12" in content and ("部" in content or "作品" in content)

            if has_bio_section and has_bio_content:
                bio_score = 1.0
            elif has_bio_section:
                bio_score = max(bio_score, 0.5)
            elif has_bio_content:
                bio_score = max(bio_score, 0.4)

            # Extra: check if bio mentions total works
            if has_works_count and bio_score > 0:
                bio_score = min(1.0, bio_score + 0.2)

        components["author_bio_in_md"] = bio_score

    # 10. HIDDEN: Tags stored as proper arrays in JSON (not comma-joined strings)
    #     AND exact tag text preserved from HTML source
    components["tags_structured"] = 0.0
    EXPECTED_TAGS = {
        "三体": ["雨果奖", "三体系列", "第一部"],
        "球状闪电": ["量子物理", "武器开发"],
        "超新星纪元": ["儿童", "末日", "社会实验"],
        "流浪地球": ["电影改编", "太阳危机"],
        "乡村教师": ["短篇", "教育", "星际文明"],
        "带上她的眼睛": ["短篇", "地心探险", "感人"],
        "全频带阻塞干扰": ["中篇", "军事", "俄罗斯"],
        "朝闻道": ["短篇", "宇宙真理", "哲学"],
        "镜子": ["中篇", "模拟宇宙", "社会"],
        "赡养人类": ["中篇", "贫富分化", "外星来客"],
    }
    if json_data_all:
        tags_correct = 0
        tags_checked = 0
        for item in json_data_all:
            if not isinstance(item, dict):
                continue
            title = item.get("title", "") or item.get("name", "") or ""
            # Find which expected book this is
            matched_book = None
            for eb in EXPECTED_TAGS:
                if eb in title:
                    matched_book = eb
                    break
            if not matched_book:
                continue
            tags_checked += 1
            # Get tags value
            tags_val = None
            for k in ["tags", "tag", "labels", "标签"]:
                if k in item:
                    tags_val = item[k]
                    break
                # case-insensitive
                for ik, iv in item.items():
                    if ik.lower() == k.lower():
                        tags_val = iv
                        break
                if tags_val is not None:
                    break
            if tags_val is None:
                continue
            # Must be a list/array, not a string
            if isinstance(tags_val, str):
                # Penalty: stored as string instead of array
                tags_correct += 0.2
                continue
            if isinstance(tags_val, list):
                expected = set(EXPECTED_TAGS[matched_book])
                actual = set(str(t).strip() for t in tags_val if str(t).strip())
                if expected == actual:
                    tags_correct += 1.0
                elif expected.issubset(actual) or actual.issubset(expected):
                    tags_correct += 0.6
                elif len(expected & actual) > 0:
                    tags_correct += 0.3
        if tags_checked > 0:
            ratio = tags_correct / tags_checked
            if ratio >= 0.9:
                components["tags_structured"] = 1.0
            elif ratio >= 0.7:
                components["tags_structured"] = 0.7
            elif ratio >= 0.4:
                components["tags_structured"] = 0.4
            else:
                components["tags_structured"] = 0.15

    # 11. HIDDEN: Synopsis fidelity — synopses must be faithfully extracted, not truncated or paraphrased
    components["synopsis_fidelity"] = 0.0
    # Key unique phrases from each book's synopsis that prove faithful extraction
    SYNOPSIS_FINGERPRINTS = {
        "三体": ["红岸工程", "叶文洁", "以太阳为中心"],
        "球状闪电": ["离奇的雨夜", "蜂窝里激怒的蜂群", "毕生心血"],
        "超新星纪元": ["超新星爆发", "训练孩子们接管这个世界", "由孩子统治的新纪元"],
        "流浪地球": ["巨大的推进器", "比邻星", "引力危机"],
        "乡村教师": ["牛顿三定律", "星际文明等级测试", "地球的最后希望"],
        "带上她的眼睛": ["传感眼镜", "地心深处", "狭小的空间"],
        "全频带阻塞干扰": ["人造太阳推向地球", "电磁辐射", "信息化优势"],
        "朝闻道": ["粒子加速器", "宇宙大统一模型", "真理祭坛"],
        "镜子": ["精确模拟宇宙演化", "全知全能的镜子", "反腐"],
        "赡养人类": ["极端的贫富分化", "整个星球的财富", "流亡太空"],
    }
    if md_files or json_data_all:
        # Check both MD and JSON for synopsis content
        all_text = ""
        for mf in md_files:
            all_text += mf.read_text(encoding="utf-8", errors="ignore")
        for item in json_data_all:
            if isinstance(item, dict):
                for k in ["synopsis", "description", "summary", "intro", "简介", "content"]:
                    v = item.get(k, "")
                    if isinstance(v, str):
                        all_text += " " + v

        books_with_full_synopsis = 0
        books_with_partial_synopsis = 0
        for book_title, fingerprints in SYNOPSIS_FINGERPRINTS.items():
            matches = sum(1 for fp in fingerprints if fp in all_text)
            if matches == len(fingerprints):
                books_with_full_synopsis += 1
            elif matches >= 1:
                books_with_partial_synopsis += 1

        total_books = len(SYNOPSIS_FINGERPRINTS)
        full_ratio = books_with_full_synopsis / total_books
        partial_ratio = books_with_partial_synopsis / total_books

        if full_ratio >= 0.9:
            components["synopsis_fidelity"] = 1.0
        elif full_ratio >= 0.7:
            components["synopsis_fidelity"] = 0.8
        elif full_ratio >= 0.5:
            components["synopsis_fidelity"] = 0.6
        elif full_ratio + partial_ratio * 0.3 >= 0.4:
            components["synopsis_fidelity"] = 0.35
        else:
            components["synopsis_fidelity"] = 0.1

    # 12. HIDDEN: data-id attribute preservation — checks if the HTML data-id is captured
    #     This is subtle metadata that weak models skip (not explicitly asked for but good practice)
    components["data_id_captured"] = 0.0
    EXPECTED_DATA_IDS = [
        "book-001", "book-002", "book-003", "book-004", "book-005", "book-006",
        "book-007", "book-008", "book-009", "book-010", "book-011", "book-012",
    ]
    if json_data_all:
        ids_found = 0
        for item in json_data_all:
            if not isinstance(item, dict):
                continue
            # Look for data-id or id or book_id field that contains "book-0XX"
            for k in ["data_id", "data-id", "id", "book_id", "bookId", "data_book_id"]:
                val = str(item.get(k, ""))
                if any(did in val for did in EXPECTED_DATA_IDS):
                    ids_found += 1
                    break
            else:
                # Also check if any value in the dict contains the data-id pattern
                for v in item.values():
                    if isinstance(v, str) and any(did in v for did in EXPECTED_DATA_IDS):
                        ids_found += 1
                        break
        if ids_found >= 10:
            components["data_id_captured"] = 1.0
        elif ids_found >= 6:
            components["data_id_captured"] = 0.5
        elif ids_found >= 3:
            components["data_id_captured"] = 0.25
    # Also check in markdown (some solutions embed data-id)
    if components["data_id_captured"] == 0.0 and md_files:
        for mf in md_files:
            content = mf.read_text(encoding="utf-8", errors="ignore")
            ids_in_md = sum(1 for did in EXPECTED_DATA_IDS if did in content)
            if ids_in_md >= 10:
                components["data_id_captured"] = 0.7  # partial: in MD but not structured
            elif ids_in_md >= 6:
                components["data_id_captured"] = 0.35

    # --- SCORING ---
    # Rebalanced weights: basic checks reduced, hidden hard checks increased
    weights = {
        "scraper_exists": 0.07,          # basic - easy
        "pagination_handled": 0.06,       # basic - easy
        "all_books_extracted": 0.12,      # moderate
        "markdown_generated": 0.03,       # trivial
        "markdown_structure": 0.10,       # moderate
        "date_sorting": 0.12,            # harder with strict check
        "metadata_completeness": 0.12,   # hidden - hard
        "script_quality": 0.08,          # hidden - moderate
        "author_bio_in_md": 0.06,        # hidden - easy-moderate
        "tags_structured": 0.10,         # NEW hidden - hard (exact array + content match)
        "synopsis_fidelity": 0.08,       # NEW hidden - moderate (faithful extraction)
        "data_id_captured": 0.06,        # NEW hidden - hard (non-obvious metadata)
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "found_books": len(found_books),
    }


def main():
    result = grade_workspace()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
