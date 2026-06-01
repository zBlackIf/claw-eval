"""Hidden verifier for CP161 — Forum Scraper Pagination Fix.

Checks that the forum scraper correctly:
1. Detects total page count from Discuz pagination HTML (not hardcoded 1)
2. Constructs correct page URLs (forum-{id}-{page}.html pattern, not ?page=N)
3. Handles GBK encoding for response parsing
4. Extracts forum ID from the base URL for URL construction
5. Integration test: actually scrapes multiple pages from mock server
6. HIDDEN-HARD: encoding ordering, URL generality, edge-case resilience

Runs the scraper against a mock server to verify multi-page scraping works.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import socket
import os
import re
import ast
import textwrap
from pathlib import Path


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _strip_comments_and_strings(code: str) -> str:
    """Remove comments and string literals to focus on actual code logic."""
    code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'"""[\s\S]*?"""', '', code)
    code = re.sub(r"'''[\s\S]*?'''", '', code)
    return code


def check_source_code(scraper_path: Path) -> dict:
    """Static analysis of the fixed scraper source code."""
    results = {}
    code = _read(scraper_path)
    if not code:
        return {"error": "scraper file not found or empty"}

    code_logic = _strip_comments_and_strings(code)

    # ===================================================================
    # EASY TIER (visible checks — all competent models pass these)
    # ===================================================================

    # Check 1: GBK encoding handling in actual code
    has_gbk = bool(re.search(r"encoding\s*=\s*['\"]gbk['\"]", code_logic, re.IGNORECASE) or
                   re.search(r"\.encoding\s*=\s*['\"]gbk['\"]", code_logic, re.IGNORECASE) or
                   re.search(r"encoding\s*=\s*['\"]gb2312['\"]", code_logic, re.IGNORECASE) or
                   re.search(r"encoding\s*=\s*['\"]gb18030['\"]", code_logic, re.IGNORECASE))
    results["handles_gbk_encoding"] = 1.0 if has_gbk else 0.0

    # Check 2: URL construction uses forum-ID-PAGE.html format
    has_correct_url_construction = bool(
        re.search(r'f["\'].*forum-.*\{.*\}.*\.html', code_logic) or
        re.search(r'format\(.*forum-.*\.html', code_logic) or
        re.search(r'forum-.*%[sd].*\.html', code_logic) or
        re.search(r'["\']forum-["\'].*\+.*["\']\.html["\']', code_logic) or
        re.search(r'forum-\{.*\}-\{.*\}\.html', code_logic)
    )
    has_query_page = "?page=" in code_logic
    results["correct_url_construction"] = 1.0 if (has_correct_url_construction and not has_query_page) else (0.3 if has_correct_url_construction else 0.0)

    # Check 3: Extracts forum ID from URL
    has_forum_id_extraction = bool(
        re.search(r"re\.\w+\(\s*r?['\"].*forum-\(?\??\\?d", code_logic) or
        re.search(r"forum_id\s*=", code_logic) or
        re.search(r"self\.forum_id", code_logic)
    )
    results["extracts_forum_id"] = 1.0 if has_forum_id_extraction else 0.0

    # Check 4: Pagination detection parses page numbers from HTML
    has_proper_pagination = bool(
        (re.search(r"findall.*forum.*\\d", code_logic) or
         re.search(r"find_all.*href.*forum", code_logic) or
         re.search(r"find_all.*['\"]a['\"]", code_logic) or
         re.search(r"select\(.*a\[href", code_logic) or
         re.search(r"page_nums|page_numbers|all_pages", code_logic) or
         (re.search(r"max\s*\(", code_logic) and re.search(r"forum-.*\\d", code_logic)))
        and
        not (not re.search(r"findall|find_all|select\(", code_logic) and
             re.search(r"return\s+1", code_logic))
    )
    results["pagination_detection"] = 1.0 if has_proper_pagination else 0.0

    # Check 5: No ?page=N in URL construction
    results["no_query_string_pagination"] = 1.0 if not has_query_page else 0.0

    # ===================================================================
    # HARD TIER (hidden checks — only strong models pass these)
    # These test deeper understanding of Discuz scraping patterns.
    # ===================================================================

    # Hidden Check H1: Encoding set on response OBJECT BEFORE accessing .text
    # The correct Discuz pattern is: response.encoding = 'gbk' (set attribute)
    # This ensures response.text uses GBK. Simply calling .decode('gbk') on
    # response.content works but is less idiomatic and may break with streaming.
    has_response_encoding_attr = bool(
        re.search(r"response\.encoding\s*=\s*['\"]gb", code_logic, re.IGNORECASE) or
        re.search(r"resp\.encoding\s*=\s*['\"]gb", code_logic, re.IGNORECASE) or
        re.search(r"r\.encoding\s*=\s*['\"]gb", code_logic, re.IGNORECASE)
    )
    has_content_decode = bool(
        re.search(r"\.content\.decode\(\s*['\"]gb", code_logic, re.IGNORECASE)
    )
    if has_response_encoding_attr:
        results["encoding_on_response_object"] = 1.0
    elif has_content_decode:
        results["encoding_on_response_object"] = 0.5
    else:
        results["encoding_on_response_object"] = 0.0

    # Hidden Check H2: Pagination extraction uses max() or sorted() to find highest page
    # Weak solutions just find the last <a> link; strong solutions extract ALL page numbers
    # and take the max, handling non-contiguous pagination links
    has_robust_max_page = bool(
        re.search(r"max\s*\(", code_logic) and
        (re.search(r"int\(", code_logic) or re.search(r"page_num", code_logic))
    )
    results["robust_max_page_extraction"] = 1.0 if has_robust_max_page else 0.0

    # Hidden Check H3: Handles base_url path construction (not just hardcoded /forum/)
    # Strong solutions extract the base path so it works regardless of forum path depth.
    has_base_path_handling = bool(
        re.search(r"(rsplit|replace|sub)\(.*forum-\d+-\d+", code_logic) or
        (re.search(r"urljoin\(", code_logic) and re.search(r"forum-.*\.html", code_logic)) or
        (re.search(r"(url_base|base_path)\s*=", code_logic) and re.search(r"forum-", code_logic)) or
        re.search(r"\.rsplit\(['\"]forum-", code_logic) or
        re.search(r"re\.sub\(['\"].*forum-\d+-\d+", code_logic) or
        re.search(r"base_url.*\.replace\(['\"].*-1\.html", code_logic) or
        re.search(r"\.replace\(['\"]forum-\d+-1", code_logic) or
        re.search(r"re\.sub\(['\"].*-\\d\+.*\.html", code_logic)
    )
    results["handles_base_path"] = 1.0 if has_base_path_handling else 0.0

    # Hidden Check H4: First page URL also uses the corrected format when start_page != 1
    has_start_page_url_fix = bool(
        re.search(r"start_page.*forum-", code_logic) or
        re.search(r"forum-.*start_page", code_logic) or
        (re.search(r"def\s+\w*url|def\s+\w*page_url|get_page_url|build_url|_build_page_url", code_logic) and
         re.search(r"forum-.*\{.*\}.*\.html", code_logic)) or
        re.search(r"base_url.*replace.*start_page|format.*start_page", code_logic)
    )
    results["start_page_url_construction"] = 1.0 if has_start_page_url_fix else 0.0

    # Hidden Check H5: Error handling for forum_id extraction
    has_forum_id_error_handling = bool(
        (re.search(r"if.*match|if.*forum_id|if not.*forum_id", code_logic) or
         re.search(r"try:.*forum_id|except.*forum_id", code_logic) or
         re.search(r"forum_id.*or\s", code_logic) or
         re.search(r"raise.*forum_id|raise.*URL|ValueError", code_logic))
        and has_forum_id_extraction
    )
    results["forum_id_error_handling"] = 1.0 if has_forum_id_error_handling else 0.0

    # Hidden Check H6: Encoding is set BEFORE accessing response.text (ordering matters)
    # The encoding assignment must appear in the same function/method that fetches,
    # and it must be BEFORE the return of .text. Check that encoding= line precedes
    # the usage of response.text or return response.text.
    # This catches models that add encoding but in wrong location (e.g., after .text).
    encoding_before_text = False
    lines = code.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if re.search(r'\.encoding\s*=\s*[\'"]gb', stripped, re.IGNORECASE):
            # Found encoding assignment; check that .text usage comes AFTER
            for j in range(i + 1, min(i + 15, len(lines))):
                if 'response.text' in lines[j] or 'resp.text' in lines[j] or 'return' in lines[j]:
                    encoding_before_text = True
                    break
            if encoding_before_text:
                break
    # Also accept .content.decode() which inherently has correct ordering
    if has_content_decode:
        encoding_before_text = True
    results["encoding_order_correct"] = 1.0 if encoding_before_text else 0.0

    # Hidden Check H7: Scrape loop uses unified URL builder for ALL pages (including first)
    # Weak solutions fix only the loop body but still use self.base_url for page 1.
    # Strong solutions use a single URL builder function/pattern for ALL pages.
    # Detect: either a helper function that builds page URLs (used in both first fetch and loop),
    # or the loop starts from start_page (not start_page+1) meaning first page goes through
    # the same URL construction.
    has_unified_url_building = bool(
        # Loop starts from start_page (not start_page + 1), meaning ALL pages use constructed URL
        re.search(r"range\s*\(\s*start_page\s*,", code_logic) or
        # Or a dedicated URL builder function exists
        re.search(r"def\s+(get_page_url|build_url|_build_page_url|make_url|page_url)\s*\(", code_logic) or
        # Or uses a list comprehension/generator for all page URLs
        re.search(r"\[.*forum-.*for\s+\w+\s+in\s+range\(start_page", code_logic)
    )
    results["unified_url_building"] = 1.0 if has_unified_url_building else 0.0

    # Hidden Check H8: Does not remove the existing retry/error handling
    # The original code has a try/except in get_page(). A strong fix preserves or
    # improves it rather than replacing it with bare requests.get().
    has_error_handling_in_fetch = bool(
        re.search(r"try:.*get\(|try:.*session\.get\(", code_logic, re.DOTALL) or
        re.search(r"except.*Exception|except.*RequestException|except.*Timeout", code_logic)
    )
    results["preserves_error_handling"] = 1.0 if has_error_handling_in_fetch else 0.0

    return results


def run_integration_test(scraper_dir: Path, port: int) -> dict:
    """Run the scraper against a mock server to verify multi-page scraping."""
    results = {}
    mock_server_path = Path("/workspace/fixtures/scraper_project/mock_forum_server.py")

    # Fallback paths
    if not mock_server_path.exists():
        mock_server_path = scraper_dir / "mock_forum_server.py"
    if not mock_server_path.exists():
        mock_server_path = Path(__file__).parent / "scraper_project" / "mock_forum_server.py"
    if not mock_server_path.exists():
        results["multi_page_works"] = 0.0
        results["integration_error"] = "mock server not found"
        return results

    # Patch mock server to use our port
    mock_code = _read(mock_server_path)
    patched_mock = mock_code.replace("port=18923", f"port={port}")
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
        tmp.write(patched_mock)
        tmp_mock_path = tmp.name

    # Start mock server
    server_proc = subprocess.Popen(
        [sys.executable, tmp_mock_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to start
    time.sleep(2.0)

    try:
        # Find scraper file
        scraper_file = None
        for candidate in [
            scraper_dir / "forum_scraper.py",
            scraper_dir / "forum_scraper_fixed.py",
            scraper_dir / "forum_scraper_fixed2.py",
            scraper_dir / "scraper.py",
        ]:
            if candidate.exists():
                scraper_file = candidate
                break

        if not scraper_file:
            for f in scraper_dir.rglob("*scraper*.py"):
                if "mock" not in f.name and "verify" not in f.name and "test" not in f.name:
                    scraper_file = f
                    break

        if not scraper_file:
            results["multi_page_works"] = 0.0
            results["integration_error"] = "scraper file not found"
            return results

        # --- Integration Test 1: Basic multi-page scraping (EASY) ---
        test_script = f'''
import sys, json
sys.path.insert(0, "{scraper_dir}")
import importlib.util
spec = importlib.util.spec_from_file_location("forum_scraper", "{scraper_file}")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

scraper = mod.ForumScraper("http://127.0.0.1:{port}/forum/forum-25-1.html", delay_range=(0.01, 0.02))
scraper.scrape(start_page=1, max_pages=5)
print("RESULT_JSON:" + json.dumps({{"total_posts": len(scraper.posts), "posts_sample": [p.get("title","") for p in scraper.posts[:3]]}}))
'''
        test_result = subprocess.run(
            [sys.executable, "-c", test_script],
            capture_output=True,
            text=True,
            timeout=45,
        )

        output = test_result.stdout + test_result.stderr
        for line in output.split('\n'):
            if 'RESULT_JSON:' in line:
                data = json.loads(line.split('RESULT_JSON:')[1])
                total_posts = data.get("total_posts", 0)
                if total_posts >= 20:
                    results["multi_page_works"] = 1.0
                elif total_posts > 5:
                    results["multi_page_works"] = 0.6
                else:
                    results["multi_page_works"] = 0.0
                results["posts_scraped"] = total_posts
                break
        else:
            results["multi_page_works"] = 0.0
            results["integration_output"] = output[:300]

        # --- Integration Test 2 (HARD): start_page != 1 ---
        # Tests that URL construction is generalized, not just patching the loop.
        test_script_2 = f'''
import sys, json
sys.path.insert(0, "{scraper_dir}")
import importlib.util
spec = importlib.util.spec_from_file_location("forum_scraper", "{scraper_file}")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

scraper = mod.ForumScraper("http://127.0.0.1:{port}/forum/forum-25-1.html", delay_range=(0.01, 0.02))
scraper.scrape(start_page=3, max_pages=3)
# If start_page=3, should get pages 3,4,5 = 15 posts
# The first fetched page should have titles containing "Page 3"
first_title = scraper.posts[0].get("title", "") if scraper.posts else ""
has_page3 = "Page 3" in first_title or "page 3" in first_title.lower()
print("RESULT2_JSON:" + json.dumps({{"total_posts": len(scraper.posts), "first_title": first_title, "has_page3": has_page3}}))
'''
        test_result_2 = subprocess.run(
            [sys.executable, "-c", test_script_2],
            capture_output=True,
            text=True,
            timeout=45,
        )

        output2 = test_result_2.stdout + test_result_2.stderr
        for line in output2.split('\n'):
            if 'RESULT2_JSON:' in line:
                data2 = json.loads(line.split('RESULT2_JSON:')[1])
                posts2 = data2.get("total_posts", 0)
                has_page3 = data2.get("has_page3", False)
                if posts2 >= 10 and has_page3:
                    results["start_page_offset_works"] = 1.0
                elif posts2 >= 10:
                    results["start_page_offset_works"] = 0.5
                elif posts2 > 0:
                    results["start_page_offset_works"] = 0.3
                else:
                    results["start_page_offset_works"] = 0.0
                break
        else:
            results["start_page_offset_works"] = 0.0

        # --- Integration Test 3 (HARD): Total pages detection accuracy ---
        test_script_3 = f'''
import sys, json
sys.path.insert(0, "{scraper_dir}")
import importlib.util
spec = importlib.util.spec_from_file_location("forum_scraper", "{scraper_file}")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

import requests
scraper = mod.ForumScraper("http://127.0.0.1:{port}/forum/forum-25-1.html", delay_range=(0.01, 0.02))
# Fetch page and test pagination detection
resp = requests.get("http://127.0.0.1:{port}/forum/forum-25-1.html")
resp.encoding = 'gbk'
total = scraper.get_total_pages(resp.text)
print("RESULT3_JSON:" + json.dumps({{"detected_total_pages": total}}))
'''
        test_result_3 = subprocess.run(
            [sys.executable, "-c", test_script_3],
            capture_output=True,
            text=True,
            timeout=30,
        )

        output3 = test_result_3.stdout + test_result_3.stderr
        for line in output3.split('\n'):
            if 'RESULT3_JSON:' in line:
                data3 = json.loads(line.split('RESULT3_JSON:')[1])
                detected = data3.get("detected_total_pages", 0)
                # Mock server has 50 pages. Detection should find 50 (from last link).
                if detected == 50:
                    results["correct_total_pages"] = 1.0
                elif detected >= 40:
                    results["correct_total_pages"] = 0.7
                elif detected > 1:
                    results["correct_total_pages"] = 0.3
                else:
                    results["correct_total_pages"] = 0.0
                results["detected_pages_value"] = detected
                break
        else:
            results["correct_total_pages"] = 0.0

        # --- Integration Test 4 (HARD): max_pages=None scrapes beyond page 1 ---
        # Tests that when max_pages is None (scrape all), the scraper respects
        # detected total_pages and scrapes more than 1 page.
        test_script_4 = f'''
import sys, json
sys.path.insert(0, "{scraper_dir}")
import importlib.util
spec = importlib.util.spec_from_file_location("forum_scraper", "{scraper_file}")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

scraper = mod.ForumScraper("http://127.0.0.1:{port}/forum/forum-25-1.html", delay_range=(0.01, 0.02))
# Scrape with max_pages=None but we will time-limit it.
# A correct scraper should detect 50 pages and start scraping them.
# We just check it gets at least pages 1-3 (15 posts).
import threading, time
done = threading.Event()
def run_scrape():
    try:
        scraper.scrape(start_page=1, max_pages=10)
    except:
        pass
    done.set()
t = threading.Thread(target=run_scrape)
t.start()
t.join(timeout=30)
total = len(scraper.posts)
print("RESULT4_JSON:" + json.dumps({{"total_posts_unlimited": total}}))
'''
        test_result_4 = subprocess.run(
            [sys.executable, "-c", test_script_4],
            capture_output=True,
            text=True,
            timeout=40,
        )

        output4 = test_result_4.stdout + test_result_4.stderr
        for line in output4.split('\n'):
            if 'RESULT4_JSON:' in line:
                data4 = json.loads(line.split('RESULT4_JSON:')[1])
                total4 = data4.get("total_posts_unlimited", 0)
                # With 10 pages and 5 posts/page, expect 50 posts
                if total4 >= 45:
                    results["unlimited_pages_works"] = 1.0
                elif total4 >= 25:
                    results["unlimited_pages_works"] = 0.7
                elif total4 > 5:
                    results["unlimited_pages_works"] = 0.4
                else:
                    results["unlimited_pages_works"] = 0.0
                break
        else:
            results["unlimited_pages_works"] = 0.0

        # --- Integration Test 5 (HARD): Scraped content is actually GBK-decoded ---
        # Tests that the posts have correct Chinese text (not garbled).
        # The mock server returns GBK-encoded HTML. If encoding is wrong,
        # titles will be garbled.
        test_script_5 = f'''
import sys, json
sys.path.insert(0, "{scraper_dir}")
import importlib.util
spec = importlib.util.spec_from_file_location("forum_scraper", "{scraper_file}")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

scraper = mod.ForumScraper("http://127.0.0.1:{port}/forum/forum-25-1.html", delay_range=(0.01, 0.02))
scraper.scrape(start_page=1, max_pages=2)
# Titles should contain "Test Thread Title" - if encoding is wrong they'll be garbled
titles = [p.get("title","") for p in scraper.posts]
has_readable_titles = any("Test Thread Title" in t for t in titles)
# Also check no mojibake patterns (common when GBK read as UTF-8)
has_garbled = any("\\ufffd" in t or "\\xe" in repr(t) for t in titles)
print("RESULT5_JSON:" + json.dumps({{"has_readable": has_readable_titles, "has_garbled": has_garbled, "sample": titles[:2]}}))
'''
        test_result_5 = subprocess.run(
            [sys.executable, "-c", test_script_5],
            capture_output=True,
            text=True,
            timeout=30,
        )

        output5 = test_result_5.stdout + test_result_5.stderr
        for line in output5.split('\n'):
            if 'RESULT5_JSON:' in line:
                data5 = json.loads(line.split('RESULT5_JSON:')[1])
                readable = data5.get("has_readable", False)
                garbled = data5.get("has_garbled", False)
                if readable and not garbled:
                    results["content_correctly_decoded"] = 1.0
                elif readable:
                    results["content_correctly_decoded"] = 0.6
                else:
                    results["content_correctly_decoded"] = 0.0
                break
        else:
            results["content_correctly_decoded"] = 0.0

    except subprocess.TimeoutExpired:
        results["multi_page_works"] = results.get("multi_page_works", 0.0)
        results["integration_error"] = "timeout"
    except Exception as e:
        results["multi_page_works"] = results.get("multi_page_works", 0.0)
        results["integration_error"] = str(e)[:200]
    finally:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
        except:
            server_proc.kill()
        try:
            os.unlink(tmp_mock_path)
        except:
            pass

    return results


def grade_workspace(ws: Path) -> dict:
    """Grade the workspace."""
    components = {}

    # Find the scraper project directory
    scraper_dir = ws / "fixtures" / "scraper_project"
    if not scraper_dir.exists():
        scraper_dir = ws / "scraper_project"
    if not scraper_dir.exists():
        for candidate in ws.rglob("forum_scraper*.py"):
            if "verify" not in candidate.name and "mock" not in candidate.name:
                scraper_dir = candidate.parent
                break
        else:
            scraper_dir = ws

    # Find scraper file
    scraper_file = None
    for candidate in [
        scraper_dir / "forum_scraper.py",
        scraper_dir / "forum_scraper_fixed.py",
        scraper_dir / "forum_scraper_fixed2.py",
        scraper_dir / "scraper.py",
    ]:
        if candidate.exists():
            scraper_file = candidate
            break

    if not scraper_file:
        for f in scraper_dir.rglob("*scraper*.py"):
            if "mock" not in f.name and "verify" not in f.name and "test" not in f.name:
                scraper_file = f
                break

    if not scraper_file:
        return {
            "overall_score": 0.0,
            "components": {"error": "no scraper file found"},
            "weights": {},
        }

    # Static code analysis
    source_checks = check_source_code(scraper_file)
    components.update(source_checks)

    # Integration test
    port = find_free_port()
    integration_results = run_integration_test(scraper_dir, port)
    components.update(integration_results)

    # ===================================================================
    # WEIGHT STRUCTURE:
    #   Easy tier (visible, all pass):  30% total
    #   Hard tier (hidden, discriminating): 70% total  (hidden >= 30%)
    #
    # The easy tier covers the 4 core bugs anyone would fix.
    # The hard tier tests deeper understanding: encoding ordering, URL
    # generality, edge cases, robust pagination, unified code structure.
    # ===================================================================
    weights = {
        # --- EASY TIER (visible): 30% total ---
        # Any competent model fixes these 4 bugs with basic static checks
        "handles_gbk_encoding": 0.06,         # Basic: adds GBK somewhere
        "correct_url_construction": 0.07,      # Basic: uses forum-ID-PAGE pattern
        "extracts_forum_id": 0.05,             # Basic: extracts forum ID
        "pagination_detection": 0.07,          # Basic: parses pagination links
        "no_query_string_pagination": 0.05,    # Basic: removes ?page=N

        # --- HARD TIER (hidden): 70% total ---
        # Static checks (hidden) — code quality & deeper understanding
        "encoding_on_response_object": 0.06,   # H1: sets .encoding attr (not just decode)
        "robust_max_page_extraction": 0.06,    # H2: uses max() for page numbers
        "handles_base_path": 0.05,             # H3: handles URL path prefix
        "start_page_url_construction": 0.05,   # H4: start_page URL not hardcoded
        "forum_id_error_handling": 0.04,       # H5: graceful error on bad URL
        "encoding_order_correct": 0.06,        # H6: encoding BEFORE .text access
        "unified_url_building": 0.06,          # H7: same URL builder for all pages
        "preserves_error_handling": 0.04,      # H8: keeps try/except in fetch

        # Integration tests (hidden) — behavioral verification
        "multi_page_works": 0.08,              # Integration: basic multi-page
        "start_page_offset_works": 0.07,       # Integration: start_page=3 works
        "correct_total_pages": 0.05,           # Integration: detects 50 pages
        "unlimited_pages_works": 0.05,         # Integration: max_pages=10 full
        "content_correctly_decoded": 0.03,     # Integration: no garbled text
    }

    overall = 0.0
    for k, w in weights.items():
        val = components.get(k, 0.0)
        if isinstance(val, (int, float)):
            overall += w * val

    return {
        "overall_score": round(overall, 4),
        "components": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in components.items()},
        "weights": weights,
    }


def main():
    ws = Path("/workspace/fixtures/scraper_project")
    if not ws.exists():
        ws = Path("/workspace/scraper_project")
    if not ws.exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
