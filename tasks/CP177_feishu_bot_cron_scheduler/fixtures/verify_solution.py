"""Hidden verifier for CP177 - Feishu Bot Cron Scheduler.

Tiered hidden checks:
  - EASY HIDDEN: basic structural correctness (all reasonable agents pass)
  - HARD HIDDEN: subtle implementation depth (only strong agents pass)

Hidden checks total weight >= 30%.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_file(base: Path, pattern: str) -> Path | None:
    """Find a file matching glob pattern."""
    results = list(base.rglob(pattern))
    return results[0] if results else None


def _collect_all_py(ws: Path) -> str:
    """Collect all Python source in workspace (excluding verify)."""
    parts = []
    for f in ws.rglob("*.py"):
        if "verify" not in f.name and "__pycache__" not in str(f):
            parts.append(_read(f))
    return "\n".join(parts)


# ============================================================
# VISIBLE CHECKS (public, not discriminating)
# ============================================================


def _check_yaml_config(ws: Path) -> dict:
    """Check if config.yaml has valid scheduled_tasks with cron expressions."""
    config_path = _find_file(ws, "config.yaml") or _find_file(ws, "config.yml")
    if not config_path:
        return {"score": 0.0, "detail": "config.yaml not found"}

    content = _read(config_path)

    has_scheduled = bool(re.search(r"scheduled_tasks\s*:", content))
    is_populated = has_scheduled and not re.search(r"scheduled_tasks\s*:\s*\[\s*\]", content)
    if not is_populated:
        return {"score": 0.0, "detail": "no populated scheduled_tasks section"}

    cron_patterns = re.findall(r'["\']?(\d+\s+\d+\s+[\d*]+\s+[\d*]+\s+[\d*]+)["\']?', content)
    has_cron = len(cron_patterns) >= 2

    has_weather_job = bool(re.search(r"(?i)(weather|天气)", content))
    has_news_job = bool(re.search(r"(?i)(news|新闻|热点)", content))
    has_timezone = bool(re.search(r"(?i)(timezone|tz|asia/shanghai|utc\+8|GMT\+8)", content))
    has_target = bool(re.search(r"(user_id|target|receive|ou_)", content))

    score = sum([
        0.25 if has_cron else 0.0,
        0.20 if has_weather_job else 0.0,
        0.20 if has_news_job else 0.0,
        0.20 if has_timezone else 0.0,
        0.15 if has_target else 0.0,
    ])
    return {
        "score": round(score, 4),
        "detail": {
            "has_cron_expressions": has_cron,
            "has_weather_job": has_weather_job,
            "has_news_job": has_news_job,
            "has_timezone": has_timezone,
            "has_target_user": has_target,
        },
    }


def _check_scheduler_module(ws: Path) -> dict:
    """Check for a scheduler module with proper cron logic."""
    scheduler_file = None
    for pattern in ["scheduler.py", "cron.py", "jobs.py", "cron_*.py", "*scheduler*.py", "*cron*.py"]:
        f = _find_file(ws, pattern)
        if f and "verify" not in f.name and "__pycache__" not in str(f):
            scheduler_file = f
            break

    if not scheduler_file:
        return {"score": 0.0, "detail": "no scheduler module found"}

    content = _read(scheduler_file)

    has_scheduling_lib = bool(re.search(
        r"(import\s+(schedule|apscheduler|croniter|asyncio)|from\s+(schedule|apscheduler|croniter|asyncio)\s+import)",
        content,
    ))
    has_threading = bool(re.search(r"(import\s+threading|from\s+threading)", content))
    has_cron_parse = bool(re.search(r"(?i)(cron|parse_cron|crontab|next_run)", content))
    scheduling_approach = has_scheduling_lib or (has_threading and has_cron_parse) or has_cron_parse

    has_class = bool(re.search(r"class\s+\w*(Scheduler|CronManager|JobRunner|TaskRunner)\w*", content))
    has_add_job = bool(re.search(r"def\s+(add_job|register|schedule_task|add_task|register_job)", content))
    has_run_loop = bool(re.search(r"def\s+(run|start|run_pending|run_forever|_loop|_run_scheduler)", content))
    has_error_handling = bool(re.search(r"(try:|except\s+\w+|on_error|retry|max_retries)", content))
    has_callback = bool(re.search(r"(callback|handler|on_trigger|execute_job|_execute)", content))

    try:
        ast.parse(content)
        valid_syntax = True
    except SyntaxError:
        valid_syntax = False

    score = sum([
        0.25 if scheduling_approach else 0.0,
        0.20 if (has_class or has_add_job) else 0.0,
        0.20 if has_run_loop else 0.0,
        0.15 if has_error_handling else 0.0,
        0.10 if has_callback else 0.0,
        0.10 if valid_syntax else 0.0,
    ])
    return {
        "score": round(score, 4),
        "detail": {
            "file": str(scheduler_file.relative_to(ws)),
            "has_scheduling_approach": scheduling_approach,
            "has_class_or_add_job": has_class or has_add_job,
            "has_run_loop": has_run_loop,
            "has_error_handling": has_error_handling,
            "has_callback": has_callback,
            "valid_syntax": valid_syntax,
        },
    }


def _check_main_integration(ws: Path) -> dict:
    """Check if main.py properly integrates the scheduler."""
    main_file = _find_file(ws, "main.py")
    if not main_file:
        return {"score": 0.0, "detail": "main.py not found"}

    content = _read(main_file)

    has_config_load = bool(re.search(r"(yaml\.safe_load|load_config|read_config|open.*config)", content))
    has_scheduler_init = bool(re.search(
        r"(Scheduler|CronManager|JobRunner|scheduler|schedule)\s*[=(]",
        content,
    ))
    has_weather_register = bool(re.search(r"(?i)(weather|天气)", content))
    has_news_register = bool(re.search(r"(?i)(news|新闻)", content))
    has_start = bool(re.search(r"\.(start|run|run_forever|run_pending)\s*\(", content))
    has_shutdown = bool(re.search(r"(signal|KeyboardInterrupt|shutdown|stop|atexit|finally)", content))

    score = sum([
        0.20 if has_config_load else 0.0,
        0.25 if has_scheduler_init else 0.0,
        0.15 if has_weather_register else 0.0,
        0.15 if has_news_register else 0.0,
        0.15 if has_start else 0.0,
        0.10 if has_shutdown else 0.0,
    ])
    return {
        "score": round(score, 4),
        "detail": {
            "has_config_load": has_config_load,
            "has_scheduler_init": has_scheduler_init,
            "has_weather_register": has_weather_register,
            "has_news_register": has_news_register,
            "has_start": has_start,
            "has_shutdown": has_shutdown,
        },
    }


def _check_job_handlers(ws: Path) -> dict:
    """Check for job handler functions that call weather/news providers + messenger."""
    bot_dir = ws / "feishu-bot"
    if not bot_dir.exists():
        bot_dir = ws / "fixtures" / "feishu-bot"
    if not bot_dir.exists():
        for candidate in ws.rglob("messenger.py"):
            bot_dir = candidate.parent
            break

    if not bot_dir or not bot_dir.exists():
        return {"score": 0.0, "detail": "bot directory not found"}

    handler_content = ""
    for pattern in ["*handler*.py", "*job*.py", "tasks.py", "scheduler.py", "cron*.py", "main.py"]:
        for f in bot_dir.rglob(pattern):
            if "verify" not in f.name and "__pycache__" not in str(f):
                handler_content += _read(f) + "\n"

    if not handler_content.strip():
        return {"score": 0.0, "detail": "no handler files found"}

    uses_weather = bool(re.search(r"(WeatherProvider|weather.*format|format_daily_report|get_forecast)", handler_content))
    uses_news = bool(re.search(r"(NewsAggregator|news.*format|format_news_bulletin|get_daily_hot)", handler_content))
    uses_messenger = bool(re.search(r"(FeishuMessageSender|send_text|send_rich_text|messenger)", handler_content))
    has_async = bool(re.search(r"(async\s+def|await\s+|asyncio\.|threading\.Thread)", handler_content))

    score = sum([
        0.30 if uses_weather else 0.0,
        0.30 if uses_news else 0.0,
        0.25 if uses_messenger else 0.0,
        0.15 if has_async else 0.0,
    ])
    return {
        "score": round(score, 4),
        "detail": {
            "uses_weather_provider": uses_weather,
            "uses_news_aggregator": uses_news,
            "uses_messenger": uses_messenger,
            "has_async_or_threaded": has_async,
        },
    }


# ============================================================
# HIDDEN EASY CHECKS — baseline correctness, all agents should pass
# These verify basic facts from the task spec are present.
# ============================================================


def _hidden_easy_cron_values_exist(ws: Path) -> dict:
    """
    HIDDEN EASY: Verify that the two required cron expressions exist anywhere.

    Any agent that reads the task spec should produce "0 7 * * *" and
    "0 8 * * *" (or close variants) somewhere in the output. This does NOT
    check that they are correctly associated with the right jobs.
    """
    config_path = _find_file(ws, "config.yaml") or _find_file(ws, "config.yml")
    all_py = _collect_all_py(ws)
    content = (_read(config_path) if config_path else "") + "\n" + all_py

    # Accept variations: "0 7 * * *", "00 7 * * *", "0 07 * * *"
    has_7am = bool(re.search(r'0+\s+0*7\s+\*\s+\*\s+\*', content))
    has_8am = bool(re.search(r'0+\s+0*8\s+\*\s+\*\s+\*', content))

    # Check target user_id appears somewhere (config or code)
    target_user = "ou_6ee310124cd63f71dc8ea30cb12721a0"
    has_user_id = target_user in content

    score = sum([
        0.35 if has_7am else 0.0,
        0.35 if has_8am else 0.0,
        0.30 if has_user_id else 0.0,
    ])
    return {
        "score": round(score, 4),
        "detail": {
            "has_7am_cron_anywhere": has_7am,
            "has_8am_cron_anywhere": has_8am,
            "has_target_user_id": has_user_id,
        },
    }


def _hidden_easy_scheduler_syntax(ws: Path) -> dict:
    """
    HIDDEN EASY: All generated Python files have valid syntax.

    Any competent agent should produce syntactically valid Python.
    """
    total_files = 0
    valid_files = 0
    invalid_list = []

    for f in ws.rglob("*.py"):
        if "verify" not in f.name and "__pycache__" not in str(f):
            total_files += 1
            content = _read(f)
            if not content.strip():
                valid_files += 1
                continue
            try:
                ast.parse(content)
                valid_files += 1
            except SyntaxError:
                invalid_list.append(str(f.relative_to(ws)))

    if total_files == 0:
        return {"score": 0.0, "detail": "no Python files found"}

    score = valid_files / total_files
    return {
        "score": round(score, 4),
        "detail": {
            "total_files": total_files,
            "valid_files": valid_files,
            "invalid": invalid_list[:5],
        },
    }


# ============================================================
# HIDDEN HARD CHECKS — subtle correctness, only strong agents pass
# These require proper implementation depth beyond surface structure.
# ============================================================


def _hidden_hard_cron_job_association(ws: Path) -> dict:
    """
    HIDDEN HARD: Verify cron expressions are correctly ASSOCIATED with jobs.

    The task asks for:
    - Weather at 7:00 Beijing time -> cron "0 7 * * *"
    - News at 8:00 Beijing time -> cron "0 8 * * *"

    Weak models might swap them (news at 7, weather at 8), or use wrong
    minute values (e.g. "7 0 * * *" reversing minute/hour fields).
    This checks proximity-based association between job name and cron.
    """
    config_path = _find_file(ws, "config.yaml") or _find_file(ws, "config.yml")
    all_py = _collect_all_py(ws)

    weather_at_7 = False
    news_at_8 = False

    # Check in config YAML for correct association (proximity)
    if config_path:
        cfg_content = _read(config_path)
        lines = cfg_content.split("\n")
        for i, line in enumerate(lines):
            context = "\n".join(lines[max(0, i - 3):i + 4])
            if re.search(r"(?i)(weather|天气)", line) and re.search(r"0+\s+0*7\s+\*", context):
                weather_at_7 = True
            if re.search(r"(?i)(news|新闻|热点)", line) and re.search(r"0+\s+0*8\s+\*", context):
                news_at_8 = True

    # Also check in Python code for correct association
    content = (_read(config_path) if config_path else "") + "\n" + all_py

    if not weather_at_7:
        weather_at_7 = bool(re.search(
            r'(0+\s+0*7\s+\*\s+\*\s+\*).{0,80}(weather|天气|Weather)',
            content, re.DOTALL,
        )) or bool(re.search(
            r'(weather|天气|Weather).{0,80}(0+\s+0*7\s+\*\s+\*\s+\*)',
            content, re.DOTALL,
        ))

    if not news_at_8:
        news_at_8 = bool(re.search(
            r'(0+\s+0*8\s+\*\s+\*\s+\*).{0,80}(news|新闻|热点|News)',
            content, re.DOTALL,
        )) or bool(re.search(
            r'(news|新闻|热点|News).{0,80}(0+\s+0*8\s+\*\s+\*\s+\*)',
            content, re.DOTALL,
        ))

    # Additional hard check: ensure minute field is NOT reversed (e.g. "7 0 * * *")
    has_reversed_cron = bool(re.search(r'["\']?\s*[78]\s+0\s+\*\s+\*\s+\*', content))

    score = sum([
        0.35 if weather_at_7 else 0.0,
        0.35 if news_at_8 else 0.0,
        0.30 if not has_reversed_cron else 0.0,
    ])
    return {
        "score": round(score, 4),
        "detail": {
            "weather_correctly_at_7": weather_at_7,
            "news_correctly_at_8": news_at_8,
            "no_reversed_minute_hour": not has_reversed_cron,
        },
    }


def _hidden_hard_timezone_in_code(ws: Path) -> dict:
    """
    HIDDEN HARD: Verify timezone is ACTUALLY IMPLEMENTED in Python code.

    Proper timezone handling requires:
    1. Importing a timezone library (pytz, zoneinfo, dateutil)
    2. Creating a timezone object for Asia/Shanghai
    3. Using it in datetime operations (not just config)

    Weak models write timezone: "Asia/Shanghai" in config.yaml but never
    actually use it in scheduling code. Strong models use zoneinfo/pytz
    to make the scheduler timezone-aware.
    """
    all_py = _collect_all_py(ws)

    # Check for timezone library import
    has_tz_import = bool(re.search(
        r"(from\s+zoneinfo\s+import|import\s+pytz|from\s+pytz|from\s+dateutil\.tz|"
        r"import\s+zoneinfo|from\s+datetime.*timezone|ZoneInfo|pytz\.timezone)",
        all_py,
    ))

    # Check for actual timezone object creation with Asia/Shanghai
    has_tz_object = bool(re.search(
        r"(ZoneInfo\s*\(\s*['\"]Asia/Shanghai['\"]\s*\)|"
        r"pytz\.timezone\s*\(\s*['\"]Asia/Shanghai['\"]\s*\)|"
        r"timezone\s*\(\s*timedelta\s*\(\s*hours\s*=\s*8)",
        all_py,
    ))

    # Check for timezone-aware datetime operations (not just defining TZ)
    has_tz_in_operations = bool(re.search(
        r"(\.astimezone\s*\(|"
        r"\.localize\s*\(|"
        r"now\s*\(\s*\w*(tz|timezone|zone)|"
        r"datetime\.now\s*\(\s*\w+|"
        r"tzinfo\s*=\s*\w+|"
        r"tz\s*=\s*\w+)",
        all_py,
    ))

    # APScheduler-specific: timezone param in scheduler config
    has_apscheduler_tz = bool(re.search(
        r"(timezone\s*=\s*['\"]Asia/Shanghai['\"]|"
        r"job_defaults.*timezone|"
        r"executors.*timezone|"
        r"BlockingScheduler\s*\(.*timezone|"
        r"BackgroundScheduler\s*\(.*timezone|"
        r"trigger.*timezone)",
        all_py,
    ))

    # Asia/Shanghai must appear in Python code, not just YAML
    has_shanghai_in_code = bool(re.search(r"Asia/Shanghai", all_py))

    score = sum([
        0.25 if has_tz_import else 0.0,
        0.25 if has_tz_object or has_apscheduler_tz else 0.0,
        0.25 if has_tz_in_operations or has_apscheduler_tz else 0.0,
        0.25 if has_shanghai_in_code else 0.0,
    ])
    return {
        "score": round(score, 4),
        "detail": {
            "has_timezone_library_import": has_tz_import,
            "has_timezone_object_creation": has_tz_object or has_apscheduler_tz,
            "has_timezone_in_operations": has_tz_in_operations or has_apscheduler_tz,
            "has_shanghai_in_python_code": has_shanghai_in_code,
        },
    }


def _hidden_hard_user_wiring_end_to_end(ws: Path) -> dict:
    """
    HIDDEN HARD: Verify the target user_id is wired end-to-end.

    Strong models will:
    1. Put user_id in config.yaml
    2. Load it from config into a variable in Python
    3. Pass it to messenger.send_* calls in job handlers

    Weak models often only hardcode it in config without loading, or put
    it in a comment, or pass a different variable to send calls.
    """
    target_user = "ou_6ee310124cd63f71dc8ea30cb12721a0"
    all_py = _collect_all_py(ws)
    config_path = _find_file(ws, "config.yaml") or _find_file(ws, "config.yml")
    config_content = _read(config_path) if config_path else ""

    # Step 1: user in config
    user_in_config = target_user in config_content

    # Step 2: config loading extracts user_id into a variable
    has_config_user_extract = bool(re.search(
        r"(user_id|target_user|receive_id)\s*=\s*\w*(config|cfg|settings)\w*",
        all_py,
    )) or bool(re.search(
        r"\w*(config|cfg|settings)\w*.*\[\s*['\"]user_id['\"]\s*\]",
        all_py,
    )) or bool(re.search(
        r"\w*(config|cfg|settings)\w*\.get\s*\(\s*['\"]user_id['\"]",
        all_py,
    )) or bool(re.search(
        r"\w*(config|cfg|settings)\w*.*\[\s*['\"]target_user['\"]\s*\]",
        all_py,
    ))

    # Step 3: messenger is called with user_id parameter (not hardcoded)
    has_send_with_user = bool(re.search(
        r"send_(text|rich_text|message)\s*\([^)]*\b(user_id|receive_id|target_user|target)\b",
        all_py,
    ))

    # Bonus: user_id appears in code as a variable (not just in a string literal comment)
    user_used_as_var = bool(re.search(
        r"(user_id|target_user|receive_id)\s*=.*" + re.escape(target_user),
        all_py,
    )) or (target_user in all_py and has_config_user_extract)

    score = sum([
        0.25 if user_in_config else 0.0,
        0.30 if has_config_user_extract else 0.0,
        0.25 if has_send_with_user else 0.0,
        0.20 if user_used_as_var else 0.0,
    ])
    return {
        "score": round(score, 4),
        "detail": {
            "target_user_in_config": user_in_config,
            "config_extracts_user_id": has_config_user_extract,
            "messenger_called_with_user_var": has_send_with_user,
            "user_id_wired_end_to_end": user_used_as_var,
        },
    }


def _hidden_hard_retry_implementation(ws: Path) -> dict:
    """
    HIDDEN HARD: Verify genuine retry/resilience implementation.

    The task mentions delivery failures in the source session. Strong
    models will implement actual retry logic (loop, decorator, backoff).
    Weak models only add try/except with a log statement but no retry.
    """
    all_py = _collect_all_py(ws)

    # Real retry: loop with attempt counter or retry decorator
    has_retry_loop = bool(re.search(
        r"(for\s+\w+\s+in\s+range\s*\(\s*\w*(retries|attempts|max_retry|retry_count)|"
        r"while\s+\w*(retries|attempts|tries|attempt)\w*\s*[<>]|"
        r"@retry|"
        r"tenacity\.|"
        r"backoff\.|"
        r"Retry\s*\()",
        all_py,
    ))

    # Exponential backoff or sleep between retries
    has_backoff = bool(re.search(
        r"(time\.sleep\s*\(\s*\w*(delay|wait|backoff|interval)|"
        r"sleep\s*\(\s*\d+\s*\*\*|"
        r"sleep\s*\(\s*\w*\s*\*\s*\d|"
        r"exponential|"
        r"backoff)",
        all_py,
    ))

    # Exception-specific handling (not just bare except)
    has_specific_except = bool(re.search(
        r"except\s+(requests\.\w+Error|HTTPError|ConnectionError|TimeoutError|"
        r"IOError|OSError|socket\.\w+|urllib)",
        all_py,
    ))

    # Logging on failure (meaningful for production)
    has_failure_log = bool(re.search(
        r"(logger\.(error|warning|exception)|logging\.(error|warning|exception))",
        all_py,
    ))

    score = sum([
        0.40 if has_retry_loop else 0.0,
        0.25 if has_backoff else 0.0,
        0.20 if has_specific_except else 0.0,
        0.15 if has_failure_log else 0.0,
    ])
    return {
        "score": round(score, 4),
        "detail": {
            "has_retry_loop_or_decorator": has_retry_loop,
            "has_backoff_delay": has_backoff,
            "has_specific_exception_handling": has_specific_except,
            "has_structured_failure_logging": has_failure_log,
        },
    }


# ============================================================
# ORCHESTRATOR
# ============================================================


def grade_workspace(ws: Path) -> dict:
    """Grade the complete workspace with tiered hidden checks."""
    # --- Visible checks ---
    config_result = _check_yaml_config(ws)
    scheduler_result = _check_scheduler_module(ws)
    main_result = _check_main_integration(ws)
    handlers_result = _check_job_handlers(ws)

    # --- Hidden EASY checks (all agents should pass) ---
    easy_cron_result = _hidden_easy_cron_values_exist(ws)
    easy_syntax_result = _hidden_easy_scheduler_syntax(ws)

    # --- Hidden HARD checks (only strong agents pass) ---
    hard_assoc_result = _hidden_hard_cron_job_association(ws)
    hard_tz_result = _hidden_hard_timezone_in_code(ws)
    hard_user_result = _hidden_hard_user_wiring_end_to_end(ws)
    hard_retry_result = _hidden_hard_retry_implementation(ws)

    # Weights breakdown:
    #   Visible:     config(0.08) + scheduler(0.15) + main(0.10) + handlers(0.12) = 0.45
    #   Hidden EASY: cron_values(0.08) + syntax(0.05) = 0.13
    #   Hidden HARD: association(0.12) + timezone(0.12) + user_wiring(0.10) + retry(0.08) = 0.42
    #   Total hidden = 0.13 + 0.42 = 0.55 (>= 30%)
    weights = {
        # Visible (0.45)
        "config_yaml": 0.08,
        "scheduler_module": 0.15,
        "main_integration": 0.10,
        "job_handlers": 0.12,
        # Hidden EASY (0.13) -- baseline, all agents pass
        "hidden_easy_cron_values": 0.08,
        "hidden_easy_syntax": 0.05,
        # Hidden HARD (0.42) -- discriminators, only strong pass
        "hidden_hard_cron_association": 0.12,
        "hidden_hard_timezone_code": 0.12,
        "hidden_hard_user_wiring": 0.10,
        "hidden_hard_retry": 0.08,
    }

    scores = {
        "config_yaml": config_result["score"],
        "scheduler_module": scheduler_result["score"],
        "main_integration": main_result["score"],
        "job_handlers": handlers_result["score"],
        "hidden_easy_cron_values": easy_cron_result["score"],
        "hidden_easy_syntax": easy_syntax_result["score"],
        "hidden_hard_cron_association": hard_assoc_result["score"],
        "hidden_hard_timezone_code": hard_tz_result["score"],
        "hidden_hard_user_wiring": hard_user_result["score"],
        "hidden_hard_retry": hard_retry_result["score"],
    }

    overall = sum(weights[k] * scores[k] for k in weights)

    return {
        "overall_score": round(overall, 4),
        "components": scores,
        "weights": weights,
        "details": {
            "config_yaml": config_result.get("detail"),
            "scheduler_module": scheduler_result.get("detail"),
            "main_integration": main_result.get("detail"),
            "job_handlers": handlers_result.get("detail"),
            "hidden_easy_cron_values": easy_cron_result.get("detail"),
            "hidden_easy_syntax": easy_syntax_result.get("detail"),
            "hidden_hard_cron_association": hard_assoc_result.get("detail"),
            "hidden_hard_timezone_code": hard_tz_result.get("detail"),
            "hidden_hard_user_wiring": hard_user_result.get("detail"),
            "hidden_hard_retry": hard_retry_result.get("detail"),
        },
    }


def main():
    # Try primary path first, fallback to alternative
    ws = Path("/workspace/fixtures/feishu-bot")
    if not ws.exists():
        ws = Path("/workspace/feishu-bot")
    if not ws.exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
