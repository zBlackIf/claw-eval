"""Hidden verifier for CP147 — Cron News Aggregator Script.

Checks:
1. cron_schedule_valid: crontab file exists with correct 8am/8pm expressions
2. config_loader: sync_news.py loads and parses config.yaml properly
3. source_fetchers: at least arXiv + one other source has a fetch implementation
4. dedup_filter: deduplication logic exists (not just a stub)
5. report_formatter: structured markdown output with required sections
6. api_sync: HTTP POST to configured endpoint with auth header
7. dry_run_mode: --dry-run flag skips API call and prints report
8. error_handling: graceful handling of source failures (partial results OK)

Hidden advanced checks (undisclosed in prompt):
H1. config_driven_sources: fetcher respects enabled/disabled flag from config
H2. robust_retry_impl: retry has backoff or delay, not just a loop counter
H3. env_token_security: API token loaded from env var, not hardcoded
H4. cron_working_dir: crontab uses absolute path and proper cd/working dir
H5. modular_structure: code uses functions/classes per source, not monolithic
H6. concurrent_fetching: sources fetched concurrently (asyncio/threading/futures)
H7. structured_error_reporting: failed sources produce metadata/stats in report
H8. date_aware_filtering: implementation filters articles by date/recency
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_file(base: Path, pattern: str) -> Path | None:
    """Find a file matching glob pattern under base."""
    matches = list(base.rglob(pattern))
    return matches[0] if matches else None


def _check_python_syntax(content: str) -> bool:
    """Check if Python code is syntactically valid."""
    try:
        ast.parse(content)
        return True
    except SyntaxError:
        return False


def _count_function_defs(content: str) -> int:
    """Count top-level and nested function/method definitions."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return 0
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            count += 1
    return count


def _count_class_defs(content: str) -> int:
    """Count class definitions."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return 0
    return sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))


def grade_workspace(ws: Path) -> dict:
    # Try /workspace/fixtures/news_sync_project first, fallback to /workspace/news_sync_project
    project = ws / "fixtures" / "news_sync_project"
    if not project.exists():
        project = ws / "news_sync_project"
    if not project.exists():
        # Try finding sync_news.py anywhere
        found = _find_file(ws, "sync_news.py")
        if found:
            project = found.parent
        else:
            return {"overall_score": 0.0, "components": {}, "error": "project directory not found"}

    components = {k: 0.0 for k in [
        "cron_schedule_valid",
        "config_loader",
        "source_fetchers",
        "dedup_filter",
        "report_formatter",
        "api_sync",
        "dry_run_mode",
        "error_handling",
        "config_driven_sources",
        "robust_retry_impl",
        "env_token_security",
        "cron_working_dir",
        "modular_structure",
        "concurrent_fetching",
        "structured_error_reporting",
        "date_aware_filtering",
    ]}

    # ---- 1. Cron Schedule ----
    crontab_file = _find_file(project, "crontab*")
    if not crontab_file:
        crontab_file = _find_file(project, "*.cron")
    if not crontab_file:
        crontab_file = _find_file(project, "cron*")

    cron_content = ""
    if crontab_file:
        cron_content = _read(crontab_file)
        # Check for 8:00 AM expression (0 8 * * *)
        has_morning = bool(re.search(r'0\s+8\s+\*\s+\*\s+\*', cron_content))
        # Check for 8:00 PM expression (0 20 * * *)
        has_evening = bool(re.search(r'0\s+20\s+\*\s+\*\s+\*', cron_content))
        # Check it references the sync script
        has_script_ref = "sync_news" in cron_content or "sync-news" in cron_content or "python" in cron_content
        components["cron_schedule_valid"] = (
            0.4 * float(has_morning) +
            0.4 * float(has_evening) +
            0.2 * float(has_script_ref)
        )
    else:
        # Check if cron is configured in config.yaml
        config_file = _find_file(project, "config.yaml") or _find_file(project, "config.yml")
        if config_file:
            cfg = _read(config_file)
            has_morning = bool(re.search(r'(0\s+8\s+\*\s+\*\s+\*|8:00|08:00)', cfg))
            has_evening = bool(re.search(r'(0\s+20\s+\*\s+\*\s+\*|20:00)', cfg))
            if has_morning and has_evening:
                components["cron_schedule_valid"] = 0.5  # partial: in config but no crontab file

    # ---- 2. Config Loader ----
    sync_file = _find_file(project, "sync_news.py")
    if not sync_file:
        sync_file = _find_file(project, "sync*.py")
    if not sync_file:
        sync_file = _find_file(project, "main.py")

    sync_content = _read(sync_file) if sync_file else ""

    if sync_content and _check_python_syntax(sync_content):
        has_yaml_import = "yaml" in sync_content or "pyyaml" in sync_content.lower()
        has_config_load = "config" in sync_content.lower() and ("open(" in sync_content or "load" in sync_content)
        has_config_path = "config.yaml" in sync_content or "config.yml" in sync_content or "config" in sync_content
        components["config_loader"] = min(1.0,
            0.4 * float(has_yaml_import) +
            0.4 * float(has_config_load) +
            0.2 * float(has_config_path)
        )

    # ---- 3. Source Fetchers ----
    all_py_files = list(project.rglob("*.py"))
    all_content = "\n".join(_read(f) for f in all_py_files) if all_py_files else ""

    if sync_content:
        has_arxiv = bool(re.search(r'arxiv|arXiv|export\.arxiv', all_content))
        has_huggingface = bool(re.search(r'huggingface|hugging_face|hf\.co|HuggingFace', all_content, re.I))
        has_techcrunch = bool(re.search(r'techcrunch|TechCrunch', all_content, re.I))
        has_openai_blog = bool(re.search(r'openai\.com|OpenAI', all_content, re.I))
        has_http_fetch = bool(re.search(r'requests\.(get|post)|urllib\.request|httpx\.(get|AsyncClient)|aiohttp\.ClientSession', all_content))
        has_xml_parse = bool(re.search(r'xml\.etree|feedparser|ElementTree|BeautifulSoup|lxml', all_content))

        source_count = sum([has_arxiv, has_huggingface, has_techcrunch, has_openai_blog])
        # Require actual HTTP call + parsing, not just mention of source name
        fetch_infra = float(has_http_fetch) * 0.5 + float(has_xml_parse) * 0.5

        components["source_fetchers"] = min(1.0,
            (source_count / 4.0) * 0.5 +
            fetch_infra * 0.5
        )

    # ---- 4. Dedup / Filter ----
    if sync_content:
        has_dedup_logic = bool(re.search(
            r'dedup|deduplicate|seen|duplicat|unique|already_added|existing',
            all_content, re.I
        ))
        has_filter_logic = bool(re.search(
            r'denoise|noise|uncertain|即将|可能|upcoming|might\b|may\b',
            all_content, re.I
        ))
        has_set_or_dict = bool(re.search(r'set\(|seen_urls|seen_titles|processed_ids', all_content))
        # Must have actual conditional logic tied to dedup (not just mentioning it in docs)
        has_dedup_conditional = bool(re.search(
            r'if\s+.*?(url|title|id|link)\s+.*?in\s+.*?(seen|processed|existing|urls|titles)',
            all_content, re.I
        )) or bool(re.search(
            r'if\s+.*?(seen|processed|existing).*?:.*?(continue|skip|pass)',
            all_content, re.I | re.DOTALL
        ))

        components["dedup_filter"] = min(1.0,
            0.3 * float(has_dedup_logic) +
            0.2 * float(has_filter_logic) +
            0.25 * float(has_set_or_dict) +
            0.25 * float(has_dedup_conditional)
        )

    # ---- 5. Report Formatter ----
    if sync_content:
        has_headline_section = bool(re.search(r'头条|headline|top.?news|impact', all_content, re.I))
        has_breakthrough_section = bool(re.search(r'技术突破|breakthrough|paper|论文', all_content, re.I))
        has_business_section = bool(re.search(r'商业动态|business|commercial|产品', all_content, re.I))
        has_quicklook_section = bool(re.search(r'速览|quicklook|quick.?look|summary|brief', all_content, re.I))
        has_markdown_format = bool(re.search(r'#{1,3}\s|^\s*[-*]\s|\|.*\|', all_content, re.M))

        section_count = sum([has_headline_section, has_breakthrough_section, has_business_section, has_quicklook_section])
        components["report_formatter"] = min(1.0,
            (section_count / 4.0) * 0.7 +
            float(has_markdown_format) * 0.3
        )

    # ---- 6. API Sync ----
    if sync_content:
        has_post = bool(re.search(r'\.post\(|POST|post\(', all_content))
        has_auth_header = bool(re.search(r'[Aa]uthorization|[Bb]earer|auth', all_content))
        has_json_payload = bool(re.search(r'json[=:]|json\.dumps|Content-Type.*json', all_content))
        has_endpoint_config = bool(re.search(r'endpoint|sync.?articles|api.*url', all_content, re.I))
        has_retry = bool(re.search(r'retry|retries|attempt|max_retries', all_content, re.I))

        components["api_sync"] = min(1.0,
            0.25 * float(has_post) +
            0.25 * float(has_auth_header) +
            0.2 * float(has_json_payload) +
            0.15 * float(has_endpoint_config) +
            0.15 * float(has_retry)
        )

    # ---- 7. Dry Run Mode ----
    if sync_content:
        has_dry_run_flag = bool(re.search(r'dry.?run|--dry-run|dry_run', all_content))
        # Must actually have conditional logic that uses the dry_run flag
        has_conditional_skip = bool(re.search(
            r'if\s+(not\s+)?.*?dry.?run.*?:',
            all_content, re.I
        ))
        has_argparse = bool(re.search(r'argparse|ArgumentParser|add_argument', all_content))
        # Must have both: print report AND skip API — not just define the flag
        has_print_on_dry = bool(re.search(
            r'(dry.?run|args\.dry).*(print|stdout|write|output)',
            all_content, re.I | re.DOTALL
        ))

        components["dry_run_mode"] = min(1.0,
            0.25 * float(has_dry_run_flag) +
            0.35 * float(has_conditional_skip) +
            0.15 * float(has_argparse) +
            0.25 * float(has_print_on_dry)
        )

    # ---- 8. Error Handling ----
    if sync_content:
        has_try_except = all_content.count("except") >= 2
        has_timeout = bool(re.search(r'timeout|Timeout', all_content))
        has_partial_results = bool(re.search(
            r'partial|continue|skip.*source|failed.*source|warning|warn',
            all_content, re.I
        ))
        has_logging = bool(re.search(r'logging|logger|log\.|print\(.*err|stderr', all_content))

        components["error_handling"] = min(1.0,
            0.3 * float(has_try_except) +
            0.25 * float(has_timeout) +
            0.25 * float(has_partial_results) +
            0.2 * float(has_logging)
        )

    # ==== HIDDEN ADVANCED CHECKS ====

    # ---- H1. Config-Driven Source Enabling/Disabling ----
    # The config.yaml has 'enabled: true' per source. A strong implementation
    # should check this flag and skip disabled sources.
    if sync_content:
        # Must reference 'enabled' field from config and use it conditionally
        has_enabled_check = bool(re.search(
            r'(source|src|s)\[?[\'"]?enabled[\'"]?\]?|\.get\([\'"]enabled[\'"]|config.*enabled|if.*enabled',
            all_content, re.I
        ))
        # Must iterate over sources from config, not hardcoded source list
        has_config_iteration = bool(re.search(
            r'for\s+\w+\s+in\s+.*sources|config\[.sources.\]|config\.get\(.sources',
            all_content, re.I
        ))
        # Should not have 4 completely separate hardcoded functions without dispatch
        has_dispatch_pattern = bool(re.search(
            r'(fetch_map|fetcher_map|source_map|handler|dispatch|getattr|registry|\[source_type\]|type.*rss|type.*api)',
            all_content, re.I
        ))

        components["config_driven_sources"] = min(1.0,
            0.4 * float(has_enabled_check) +
            0.35 * float(has_config_iteration) +
            0.25 * float(has_dispatch_pattern)
        )

    # ---- H2. Robust Retry Implementation ----
    # A simple retry is just a for loop. Robust retry includes:
    # - exponential backoff or at least a sleep/delay between retries
    # - respect of retry_delay_seconds from config
    # - proper exception types caught (not bare except)
    if sync_content:
        has_sleep_in_retry = bool(re.search(
            r'(time\.sleep|asyncio\.sleep|sleep)\s*\(\s*.*?(retry|delay|backoff|wait)',
            all_content, re.I
        )) or bool(re.search(
            r'(retry|backoff|attempt).*?(time\.sleep|sleep)',
            all_content, re.I
        ))
        has_exponential_backoff = bool(re.search(
            r'(\*\*\s*\d|\*\s*2|exponential|backoff|2\s*\*\*|pow\(2)',
            all_content, re.I
        ))
        has_retry_config_usage = bool(re.search(
            r'retry_count|retry_delay|max_retries.*config|config.*retry',
            all_content, re.I
        ))
        has_specific_exception = bool(re.search(
            r'except\s+(requests\.|urllib|HTTPError|ConnectionError|Timeout|RequestException|IOError)',
            all_content
        ))

        components["robust_retry_impl"] = min(1.0,
            0.3 * float(has_sleep_in_retry) +
            0.25 * float(has_exponential_backoff) +
            0.25 * float(has_retry_config_usage) +
            0.2 * float(has_specific_exception)
        )

    # ---- H3. Environment Variable Token Security ----
    # The config.yaml says "token loaded from environment variable NEWS_SYNC_API_TOKEN"
    # Strong implementations should use os.environ/os.getenv, not hardcode a token.
    if sync_content:
        has_env_var_load = bool(re.search(
            r'os\.(environ|getenv)\s*\(\s*[\'"].*?(TOKEN|KEY|SECRET|API)',
            all_content, re.I
        ))
        has_no_hardcoded_token = not bool(re.search(
            r'(bearer|token)\s*[=:]\s*["\'][a-zA-Z0-9_-]{20,}["\']',
            all_content, re.I
        ))
        has_env_var_name = bool(re.search(
            r'NEWS_SYNC_API_TOKEN|API_TOKEN|AUTH_TOKEN',
            all_content
        ))
        # Should handle missing token gracefully
        has_token_missing_check = bool(re.search(
            r'(not\s+.*token|token\s*(is\s+None|==\s*None|==\s*["\']{2})|raise.*token|if.*token)',
            all_content, re.I
        ))

        components["env_token_security"] = min(1.0,
            0.35 * float(has_env_var_load) +
            0.2 * float(has_no_hardcoded_token) +
            0.25 * float(has_env_var_name) +
            0.2 * float(has_token_missing_check)
        )

    # ---- H4. Cron Working Directory Handling ----
    # A proper crontab should: use absolute paths, set working dir (cd),
    # handle PATH, log output, avoid env issues.
    if cron_content:
        # Should cd to project dir before running
        has_cd_or_workdir = bool(re.search(
            r'cd\s+/|WORKDIR|--config\s+/',
            cron_content
        ))
        # Should use absolute path to python
        has_abs_python = bool(re.search(
            r'(/usr/bin/python|/usr/local/bin/python|/home/.*python|/opt/.*python|venv.*python|\$\(which python\)|PATH=)',
            cron_content
        ))
        # Should redirect output/errors to log
        has_output_redirect = bool(re.search(
            r'>>?\s*.*\.(log|txt)|2>&1|/dev/null|tee\s',
            cron_content
        ))
        # Should set env vars (PATH, LANG, etc.) or source a profile
        has_env_setup = bool(re.search(
            r'(PATH=|LANG=|source\s|\..*profile|\..*env|export\s)',
            cron_content
        ))

        components["cron_working_dir"] = min(1.0,
            0.35 * float(has_cd_or_workdir) +
            0.25 * float(has_abs_python) +
            0.2 * float(has_output_redirect) +
            0.2 * float(has_env_setup)
        )

    # ---- H5. Modular Code Structure ----
    # Strong implementations decompose into clear functions/classes,
    # not a single monolithic main(). Expect: separate fetcher funcs,
    # a formatting func, an API sync func, etc.
    if sync_content:
        func_count = _count_function_defs(sync_content)
        class_count = _count_class_defs(sync_content)

        # Check if code is split across multiple modules
        py_file_count = len(all_py_files)
        multi_module = py_file_count >= 3  # e.g., sync_news.py, fetchers.py, formatter.py

        # Check for separation of concerns: separate functions for fetch, format, sync
        has_fetch_func = bool(re.search(
            r'def\s+(fetch_|get_|pull_|download_)\w+',
            all_content
        ))
        has_format_func = bool(re.search(
            r'def\s+(format_|generate_|render_|build_)\w+.*(report|markdown|output)',
            all_content, re.I
        ))
        has_sync_func = bool(re.search(
            r'def\s+(sync_|post_|upload_|push_|send_)\w+',
            all_content
        ))

        # Minimum function count for non-trivial implementation
        # 6+ functions indicates proper decomposition
        func_score = min(1.0, max(0.0, (func_count - 3) / 5.0))  # 3 funcs = 0, 8+ = 1.0

        components["modular_structure"] = min(1.0,
            0.3 * func_score +
            0.15 * float(multi_module) +
            0.2 * float(has_fetch_func) +
            0.2 * float(has_format_func) +
            0.15 * float(has_sync_func)
        )

    # ---- H6. Concurrent Fetching ----
    # Professional implementations don't fetch 4 sources sequentially — they use
    # concurrent.futures, asyncio, or threading to parallelize network I/O.
    # This is a strong quality signal: weak models write simple sequential loops.
    if sync_content:
        has_concurrent_futures = bool(re.search(
            r'concurrent\.futures|ThreadPoolExecutor|ProcessPoolExecutor|as_completed',
            all_content
        ))
        has_asyncio_gather = bool(re.search(
            r'asyncio\.(gather|create_task|wait)|async\s+def\s+fetch|await.*fetch',
            all_content
        ))
        has_threading = bool(re.search(
            r'threading\.(Thread|Pool)|multiprocessing|thread_map',
            all_content
        ))
        # Must actually map over sources, not just import the module
        has_parallel_dispatch = bool(re.search(
            r'(executor\.map|executor\.submit|gather\(\*|await\s+asyncio|pool\.map|\.start\(\))',
            all_content
        ))

        any_concurrency = float(has_concurrent_futures or has_asyncio_gather or has_threading)
        components["concurrent_fetching"] = min(1.0,
            0.5 * any_concurrency +
            0.5 * float(has_parallel_dispatch)
        )

    # ---- H7. Structured Error Reporting ----
    # A strong implementation doesn't just skip failed sources — it tracks which
    # sources succeeded/failed and reports statistics (e.g., "3/4 sources fetched,
    # techcrunch timed out"). Weak models just use bare try/except with pass.
    if sync_content:
        has_failure_tracking = bool(re.search(
            r'(failed_sources|errors|failures|source_status|fetch_results)\s*[=\[]',
            all_content, re.I
        ))
        has_stats_in_output = bool(re.search(
            r'(成功|失败|fetched|succeeded|skipped|timed.?out|sources?\s*:?\s*\d)',
            all_content, re.I
        ))
        has_per_source_status = bool(re.search(
            r'(status|result|outcome)\s*[=\[{].*?(success|fail|error|ok)',
            all_content, re.I
        )) or bool(re.search(
            r'(append|add).*?(error|failure|exception).*?(source|name)',
            all_content, re.I
        ))
        # Penalize bare except with pass/continue (lazy error handling)
        bare_except_count = len(re.findall(r'except.*?:\s*\n\s*(pass|continue)\s*\n', all_content))
        no_lazy_except = bare_except_count == 0

        components["structured_error_reporting"] = min(1.0,
            0.3 * float(has_failure_tracking) +
            0.25 * float(has_stats_in_output) +
            0.25 * float(has_per_source_status) +
            0.2 * float(no_lazy_except)
        )

    # ---- H8. Date-Aware Filtering ----
    # The config says "daily" aggregation. A strong implementation filters by
    # publication date (only today's or last 24h articles), not just fetching
    # whatever the RSS returns. This requires datetime parsing of feed entries.
    if sync_content:
        has_date_parsing = bool(re.search(
            r'(dateutil|datetime\.strptime|parse_date|published_parsed|updated_parsed|isoformat|fromisoformat)',
            all_content
        ))
        has_recency_filter = bool(re.search(
            r'(timedelta|hours?\s*=\s*24|days?\s*=\s*1|today|now\(\)|utcnow|recent|within)',
            all_content, re.I
        ))
        has_date_comparison = bool(re.search(
            r'(>\s*(cutoff|threshold|since|start_time|min_date)|<\s*(now|end)|published.*>|date.*>=)',
            all_content, re.I
        )) or bool(re.search(
            r'if.*(date|time|published|updated).*(>|<|>=|<=|after|before)',
            all_content, re.I
        ))

        components["date_aware_filtering"] = min(1.0,
            0.35 * float(has_date_parsing) +
            0.35 * float(has_recency_filter) +
            0.30 * float(has_date_comparison)
        )

    # ---- Requirements file (bonus to config_loader) ----
    req_file = _find_file(project, "requirements.txt")
    if req_file:
        req_content = _read(req_file)
        # Bonus: if requirements.txt actually has proper deps
        has_real_deps = len([l for l in req_content.strip().splitlines()
                           if l.strip() and not l.startswith("#")]) >= 2
        if has_real_deps and components["config_loader"] > 0:
            components["config_loader"] = min(1.0, components["config_loader"] + 0.1)

    # ---- Weights and final score ----
    # Basic checks are easy — most agents pass them. Hidden checks discriminate.
    weights = {
        # Basic checks — 45% total (reduced)
        "cron_schedule_valid": 0.07,
        "config_loader": 0.05,
        "source_fetchers": 0.09,
        "dedup_filter": 0.06,
        "report_formatter": 0.06,
        "api_sync": 0.05,
        "dry_run_mode": 0.04,
        "error_handling": 0.03,
        # Hidden advanced checks — 55% total (increased)
        "config_driven_sources": 0.09,
        "robust_retry_impl": 0.09,
        "env_token_security": 0.07,
        "cron_working_dir": 0.06,
        "modular_structure": 0.05,
        "concurrent_fetching": 0.09,
        "structured_error_reporting": 0.05,
        "date_aware_filtering": 0.05,
    }

    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    ws = Path("/workspace")
    result = grade_workspace(ws)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
