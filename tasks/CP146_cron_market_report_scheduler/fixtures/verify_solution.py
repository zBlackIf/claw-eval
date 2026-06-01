"""Hidden verifier for CP146 — Cron Market Report Scheduler."""
from __future__ import annotations

import json
import subprocess
import sys
import re
from pathlib import Path
from datetime import date as dt_date, timedelta


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _run_cmd(cmd: list[str], cwd: Path, timeout: int = 10) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return -1, "", str(e)


def _load_holidays_from_file(base: Path) -> list[str]:
    """Load holidays directly for verification purposes."""
    try:
        hf = base / "holidays_sse.json"
        with open(hf, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def grade_workspace(ws: Path) -> dict:
    # Try both locations
    base = ws / "fixtures" / "market-scheduler"
    if not base.exists():
        base = ws / "market-scheduler"
    if not base.exists():
        # Also check direct workspace
        base = ws
        if not (base / "scheduler.py").exists():
            return {"overall_score": 0.0, "components": {}, "error": "scheduler.py not found"}

    base = base.resolve()
    scheduler = base / "scheduler.py"
    src = _read(scheduler)

    components = {k: 0.0 for k in [
        "is_trading_day_fixed",
        "is_trading_day_holidays_check",
        "generate_cron_entry_impl",
        "run_if_trading_impl",
        "get_next_jobs_impl",
        "cron_weekday_filter",
        "trading_day_guard_in_cron",
        # Hidden harder checks
        "next_jobs_skips_holidays",
        "next_jobs_all_schedules_per_day",
        "cron_absolute_path_or_cd",
        "run_if_trading_error_handling",
        # Hidden harder checks (added)
        "cron_output_redirection",
        "next_jobs_chronological_order",
        "next_jobs_accepts_from_date_cli",
    ]}

    # ----------------------------------------------------------------
    # Dimension 1: is_trading_day weekend detection fixed
    # The bug was isoweekday() > 6 should be >= 6 (Saturday=6, Sunday=7)
    # ----------------------------------------------------------------
    rc, out, err = _run_cmd(
        [sys.executable, str(scheduler), "check", "2026-05-16"],  # Saturday
        cwd=base
    )
    if rc == 0 and out.strip():
        try:
            result = json.loads(out.strip())
            if result.get("is_trading_day") is False:
                components["is_trading_day_fixed"] = 0.5
        except json.JSONDecodeError:
            pass

    # Also check Sunday
    rc, out, err = _run_cmd(
        [sys.executable, str(scheduler), "check", "2026-05-17"],  # Sunday
        cwd=base
    )
    if rc == 0 and out.strip():
        try:
            result = json.loads(out.strip())
            if result.get("is_trading_day") is False and components["is_trading_day_fixed"] == 0.5:
                components["is_trading_day_fixed"] = 1.0
        except json.JSONDecodeError:
            pass

    # ----------------------------------------------------------------
    # Dimension 2: Holiday check works correctly
    # ----------------------------------------------------------------
    rc, out, err = _run_cmd(
        [sys.executable, str(scheduler), "check", "2026-05-01"],  # Holiday (Thursday)
        cwd=base
    )
    holiday_detected = False
    if rc == 0 and out.strip():
        try:
            result = json.loads(out.strip())
            if result.get("is_trading_day") is False:
                holiday_detected = True
                components["is_trading_day_holidays_check"] = 0.5
        except json.JSONDecodeError:
            pass

    # 2026-05-19 is a normal Monday, should be trading day
    rc, out, err = _run_cmd(
        [sys.executable, str(scheduler), "check", "2026-05-19"],  # Monday, not holiday
        cwd=base
    )
    if rc == 0 and out.strip() and holiday_detected:
        try:
            result = json.loads(out.strip())
            if result.get("is_trading_day") is True:
                components["is_trading_day_holidays_check"] = 1.0
        except json.JSONDecodeError:
            pass

    # ----------------------------------------------------------------
    # Dimension 3: generate_cron_entry implementation
    # ----------------------------------------------------------------
    rc, out, err = _run_cmd(
        [sys.executable, str(scheduler), "generate-cron"],
        cwd=base
    )
    cron_output = out if rc == 0 else ""
    if rc == 0 and out.strip():
        lines = out.strip().splitlines()
        cron_lines = [l for l in lines if l.strip() and not l.strip().startswith("#")]
        if len(cron_lines) >= 1:
            components["generate_cron_entry_impl"] = 0.5
            first_cron = cron_lines[0].strip()
            parts = first_cron.split()
            if len(parts) >= 6:
                try:
                    int(parts[0])
                    int(parts[1])
                    components["generate_cron_entry_impl"] = 1.0
                except ValueError:
                    pass

    # ----------------------------------------------------------------
    # Dimension 4: run_if_trading implementation (basic)
    # ----------------------------------------------------------------
    if "run_if_trading" in src:
        func_start = src.find("def run_if_trading")
        if func_start >= 0:
            func_body = src[func_start:]
            next_def = func_body.find("\ndef ", 1)
            if next_def > 0:
                func_body = func_body[:next_def]
            body_lines = [l.strip() for l in func_body.splitlines()[1:] if l.strip() and not l.strip().startswith("#") and not l.strip().startswith('"""') and not l.strip().startswith("'''")]
            non_docstring_lines = []
            in_docstring = False
            for line in body_lines:
                if '"""' in line or "'''" in line:
                    in_docstring = not in_docstring
                    continue
                if not in_docstring:
                    non_docstring_lines.append(line)
            if len(non_docstring_lines) > 1 and "pass" not in non_docstring_lines:
                components["run_if_trading_impl"] = 0.5
                if "is_trading_day" in func_body:
                    components["run_if_trading_impl"] = 1.0

    # ----------------------------------------------------------------
    # Dimension 5: get_next_jobs implementation (basic)
    # ----------------------------------------------------------------
    rc, out, err = _run_cmd(
        [sys.executable, str(scheduler), "next", "3"],
        cwd=base
    )
    if rc == 0 and out.strip() and out.strip() != "No upcoming jobs found.":
        try:
            jobs = json.loads(out.strip())
            if isinstance(jobs, list) and len(jobs) > 0:
                first = jobs[0]
                if "date" in first and ("job_id" in first or "id" in first or "name" in first):
                    components["get_next_jobs_impl"] = 0.5
                    all_valid = True
                    for job in jobs:
                        d = job.get("date", "")
                        if d:
                            try:
                                jd = dt_date.fromisoformat(d)
                                if jd.isoweekday() >= 6:
                                    all_valid = False
                            except ValueError:
                                all_valid = False
                    if all_valid:
                        components["get_next_jobs_impl"] = 1.0
        except (json.JSONDecodeError, TypeError):
            pass

    # ----------------------------------------------------------------
    # Dimension 6: Cron entries have weekday filter
    # ----------------------------------------------------------------
    if cron_output.strip():
        cron_lines = [l for l in cron_output.strip().splitlines() if l.strip() and not l.strip().startswith("#")]
        if cron_lines:
            has_weekday = False
            for cl in cron_lines:
                parts = cl.split()
                if len(parts) >= 5:
                    dow = parts[4]
                    if dow in ("1-5", "Mon-Fri", "1,2,3,4,5"):
                        has_weekday = True
                        break
            components["cron_weekday_filter"] = 1.0 if has_weekday else 0.0

    # ----------------------------------------------------------------
    # Dimension 7: Cron entries include trading-day guard
    # ----------------------------------------------------------------
    if cron_output.strip():
        cron_lines = [l for l in cron_output.strip().splitlines() if l.strip() and not l.strip().startswith("#")]
        has_guard = False
        for cl in cron_lines:
            if "run-if-trading" in cl or "run_if_trading" in cl:
                has_guard = True
                break
        components["trading_day_guard_in_cron"] = 1.0 if has_guard else 0.0

    # ================================================================
    # HIDDEN HARDER CHECKS (these discriminate strong vs weak models)
    # ================================================================

    # ----------------------------------------------------------------
    # Hidden 1: get_next_jobs must correctly skip holidays (not just weekends)
    # We ask for next jobs starting from 2026-04-30 (Wed before Labour Day week)
    # The May holiday block is 2026-05-01 through 2026-05-05.
    # So the next trading day after 2026-04-30 should be 2026-05-06 (Wed).
    # Strong models handle this; weak ones just skip weekends or ignore from_date.
    # Key: the CLI must accept a from_date argument for this to work.
    # ----------------------------------------------------------------
    rc, out, err = _run_cmd(
        [sys.executable, str(scheduler), "next", "8", "2026-04-30"],
        cwd=base
    )
    # The command might accept from_date as 3rd arg or not — try alternative
    if rc != 0 or not out.strip() or out.strip() == "No upcoming jobs found.":
        # Try passing as named arg style or different position
        rc, out, err = _run_cmd(
            [sys.executable, str(scheduler), "next", "8", "--from", "2026-04-30"],
            cwd=base
        )

    holidays = _load_holidays_from_file(base)
    if rc == 0 and out.strip() and out.strip() != "No upcoming jobs found.":
        try:
            jobs = json.loads(out.strip())
            if isinstance(jobs, list) and len(jobs) > 0:
                # Check that NO job date falls on a holiday
                has_holiday_job = False
                for job in jobs:
                    d = job.get("date", "")
                    if d in holidays:
                        has_holiday_job = True
                        break
                if not has_holiday_job:
                    # The critical check: the first date MUST be 2026-05-06
                    # (proving the model actually used from_date=2026-04-30 and
                    # correctly skipped the 5-day holiday block).
                    # If dates start from today instead, the model ignored from_date.
                    dates_in_jobs = sorted(set(job.get("date", "") for job in jobs))
                    first_date = dates_in_jobs[0] if dates_in_jobs else ""
                    if first_date == "2026-05-06":
                        components["next_jobs_skips_holidays"] = 1.0
                    elif first_date > "2026-04-30" and first_date <= "2026-05-09":
                        # Close but not exact — maybe off-by-one or partial
                        components["next_jobs_skips_holidays"] = 0.5
                    # else: model ignored from_date entirely, score stays 0
        except (json.JSONDecodeError, TypeError):
            pass

    # ----------------------------------------------------------------
    # Hidden 2: get_next_jobs should produce ALL enabled schedules per trading day
    # With 4 enabled schedules, asking for "next 8" should cover exactly 2 trading days
    # (4 jobs per day x 2 days = 8 jobs). Each day should have 4 distinct time entries.
    # ----------------------------------------------------------------
    rc, out, err = _run_cmd(
        [sys.executable, str(scheduler), "next", "8"],
        cwd=base
    )
    if rc == 0 and out.strip() and out.strip() != "No upcoming jobs found.":
        try:
            jobs = json.loads(out.strip())
            if isinstance(jobs, list) and len(jobs) >= 8:
                # Group by date
                by_date: dict[str, list] = {}
                for job in jobs:
                    d = job.get("date", "")
                    by_date.setdefault(d, []).append(job)
                # Check that at least one date has 4 jobs (all schedules)
                max_per_day = max(len(v) for v in by_date.values()) if by_date else 0
                if max_per_day >= 4:
                    components["next_jobs_all_schedules_per_day"] = 1.0
                elif max_per_day >= 3:
                    components["next_jobs_all_schedules_per_day"] = 0.5
            elif isinstance(jobs, list) and len(jobs) >= 4:
                # At least got some multi-schedule output
                by_date = {}
                for job in jobs:
                    d = job.get("date", "")
                    by_date.setdefault(d, []).append(job)
                max_per_day = max(len(v) for v in by_date.values()) if by_date else 0
                if max_per_day >= 4:
                    components["next_jobs_all_schedules_per_day"] = 0.8
                elif max_per_day >= 2:
                    components["next_jobs_all_schedules_per_day"] = 0.3
        except (json.JSONDecodeError, TypeError):
            pass

    # ----------------------------------------------------------------
    # Hidden 3: Cron entries should use absolute paths or cd to the scheduler dir
    # A proper cron entry needs: cd /path/to/dir && python scheduler.py ...
    # or use absolute path to python and scheduler.py
    # Without this, cron jobs fail silently in production.
    # ----------------------------------------------------------------
    if cron_output.strip():
        cron_lines = [l for l in cron_output.strip().splitlines() if l.strip() and not l.strip().startswith("#")]
        has_path_handling = False
        for cl in cron_lines:
            # Check for cd /... && or absolute python path or absolute scheduler path
            if re.search(r'\bcd\s+/', cl):
                has_path_handling = True
                break
            if re.search(r'/\S+/scheduler\.py', cl) or re.search(r'/\S+/python', cl):
                has_path_handling = True
                break
        components["cron_absolute_path_or_cd"] = 1.0 if has_path_handling else 0.0

    # ----------------------------------------------------------------
    # Hidden 4: run_if_trading has proper error handling
    # Should handle: subprocess errors, missing script file, return codes.
    # Strong models add try/except around subprocess call and handle
    # FileNotFoundError or CalledProcessError gracefully.
    # Require ALL THREE: try/except + subprocess + return code handling.
    # ----------------------------------------------------------------
    if "run_if_trading" in src:
        func_start = src.find("def run_if_trading")
        if func_start >= 0:
            func_body = src[func_start:]
            next_def = func_body.find("\ndef ", 1)
            if next_def > 0:
                func_body = func_body[:next_def]

            has_try_except = ("try:" in func_body and "except" in func_body)
            has_subprocess = ("subprocess" in func_body or "Popen" in func_body)
            has_return_code = ("returncode" in func_body or ("return 0" in func_body and "return 1" in func_body))

            if has_try_except and has_subprocess and has_return_code:
                components["run_if_trading_error_handling"] = 1.0
            elif has_try_except and has_subprocess:
                components["run_if_trading_error_handling"] = 0.7
            elif has_subprocess and has_return_code:
                components["run_if_trading_error_handling"] = 0.4
            elif has_subprocess:
                components["run_if_trading_error_handling"] = 0.2

    # ----------------------------------------------------------------
    # Hidden 5: Cron entries redirect stdout/stderr for logging
    # Production cron jobs MUST capture output; without redirection cron
    # swallows output silently, making debugging impossible.
    # Look for: >> /path 2>&1, or > /path 2>&1, or | logger, or &> /path
    # Strong models add logging; weak models only generate bare commands.
    # ----------------------------------------------------------------
    if cron_output.strip():
        cron_lines = [l for l in cron_output.strip().splitlines() if l.strip() and not l.strip().startswith("#")]
        has_redirection = False
        for cl in cron_lines:
            # Standard output redirection patterns for cron
            if re.search(r'>>?\s*\S+', cl) and ('2>&1' in cl or '&>' in cl or '2>' in cl):
                has_redirection = True
                break
            if '| logger' in cl or '| tee' in cl:
                has_redirection = True
                break
            # Simple append redirection (less strict)
            if re.search(r'>>\s*\S+', cl):
                has_redirection = True
                break
        components["cron_output_redirection"] = 1.0 if has_redirection else 0.0

    # ----------------------------------------------------------------
    # Hidden 6: get_next_jobs output is chronologically sorted
    # Each job must have a "time" field (HH:MM), and the list must be
    # sorted by (date, time). Strong models produce clean structured
    # output; weak models return unsorted or missing time fields.
    # ----------------------------------------------------------------
    rc, out, err = _run_cmd(
        [sys.executable, str(scheduler), "next", "8"],
        cwd=base
    )
    if rc == 0 and out.strip() and out.strip() != "No upcoming jobs found.":
        try:
            jobs = json.loads(out.strip())
            if isinstance(jobs, list) and len(jobs) >= 2:
                # Check all jobs have a time field in HH:MM format
                all_have_time = True
                sort_keys = []
                for job in jobs:
                    t = job.get("time", "")
                    if not re.match(r'^\d{2}:\d{2}$', t):
                        all_have_time = False
                        break
                    sort_keys.append((job.get("date", ""), t))

                if all_have_time and sort_keys:
                    # Check that the list is sorted
                    is_sorted = all(sort_keys[i] <= sort_keys[i+1] for i in range(len(sort_keys)-1))
                    if is_sorted:
                        components["next_jobs_chronological_order"] = 1.0
                    else:
                        # Has time field but not sorted — partial credit
                        components["next_jobs_chronological_order"] = 0.3
                elif all_have_time:
                    components["next_jobs_chronological_order"] = 0.5
        except (json.JSONDecodeError, TypeError):
            pass

    # ----------------------------------------------------------------
    # Hidden 7: CLI properly accepts from_date argument for "next" command
    # The original main() only parses count; a strong model must also
    # wire the from_date parameter through the CLI (positional or --from).
    # We test: scheduler.py next 3 2026-06-22 (Monday after Dragon Boat)
    # should return jobs starting from 2026-06-22, NOT from today.
    # 2026-06-19 and 2026-06-20 are holidays (Dragon Boat).
    # So "next 3 2026-06-18" should skip 06-19 and 06-20 and start at 06-22.
    # ----------------------------------------------------------------
    rc, out, err = _run_cmd(
        [sys.executable, str(scheduler), "next", "3", "2026-06-18"],
        cwd=base
    )
    # Try alternative arg style if first fails
    if rc != 0 or not out.strip() or out.strip() == "No upcoming jobs found.":
        rc, out, err = _run_cmd(
            [sys.executable, str(scheduler), "next", "3", "--from", "2026-06-18"],
            cwd=base
        )

    if rc == 0 and out.strip() and out.strip() != "No upcoming jobs found.":
        try:
            jobs = json.loads(out.strip())
            if isinstance(jobs, list) and len(jobs) > 0:
                dates_in_jobs = sorted(set(job.get("date", "") for job in jobs))
                # No job should fall on 2026-06-19 or 2026-06-20 (holidays)
                has_holiday = any(d in ("2026-06-19", "2026-06-20") for d in dates_in_jobs)
                # First date should be 2026-06-18 (Thu, trading day) or 2026-06-22 (Mon)
                first_date = dates_in_jobs[0] if dates_in_jobs else ""
                if not has_holiday and first_date in ("2026-06-18", "2026-06-22"):
                    components["next_jobs_accepts_from_date_cli"] = 1.0
                elif not has_holiday and first_date > "2026-06-17" and first_date <= "2026-06-25":
                    components["next_jobs_accepts_from_date_cli"] = 0.5
                # else: from_date not wired correctly, stays 0
        except (json.JSONDecodeError, TypeError):
            pass

    # ----------------------------------------------------------------
    # Weights: reduce easy checks, add weight to hidden harder checks
    # ----------------------------------------------------------------
    weights = {
        # Basic checks (total 0.40)
        "is_trading_day_fixed": 0.08,
        "is_trading_day_holidays_check": 0.07,
        "generate_cron_entry_impl": 0.08,
        "run_if_trading_impl": 0.05,
        "get_next_jobs_impl": 0.05,
        "cron_weekday_filter": 0.04,
        "trading_day_guard_in_cron": 0.03,
        # Hidden harder checks (total 0.60)
        "next_jobs_skips_holidays": 0.10,
        "next_jobs_all_schedules_per_day": 0.09,
        "cron_absolute_path_or_cd": 0.08,
        "run_if_trading_error_handling": 0.08,
        "cron_output_redirection": 0.09,
        "next_jobs_chronological_order": 0.08,
        "next_jobs_accepts_from_date_cli": 0.08,
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
