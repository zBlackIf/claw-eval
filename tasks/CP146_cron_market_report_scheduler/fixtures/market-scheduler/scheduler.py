"""
Market Report Scheduler - Cron-based scheduler for stock market reports.

Reads schedule_config.json and executes report scripts at configured times,
but ONLY on trading days (weekdays excluding SSE holidays).

Usage:
    python scheduler.py run             # Run the scheduler daemon
    python scheduler.py next            # Show next scheduled jobs
    python scheduler.py check <date>    # Check if a date is a trading day
    python scheduler.py generate-cron   # Generate crontab entries
"""
import sys
import json
import os
import subprocess
from datetime import datetime, date, timedelta
from pathlib import Path


CONFIG_FILE = "schedule_config.json"
WATCHLIST_FILE = "watchlist.json"


def load_config() -> dict:
    """Load the schedule configuration."""
    config_path = Path(__file__).parent / CONFIG_FILE
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_holidays() -> list[str]:
    """Load SSE holiday dates from the holidays file."""
    config = load_config()
    holidays_file = config["trading_calendar"]["holidays_file"]
    holidays_path = Path(__file__).parent / holidays_file
    with open(holidays_path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_trading_day(check_date: date) -> bool:
    """
    Determine if a given date is a trading day.
    Trading day = weekday AND not in SSE holidays list.
    """
    # Weekend check
    if check_date.isoweekday() > 6:
        return False

    holidays = load_holidays()
    if check_date in holidays:
        return False

    return True


def parse_trigger(trigger_str: str) -> dict:
    """
    Parse trigger string like 'trading_day 09:15 Asia/Shanghai'
    Returns dict with keys: type, hour, minute, timezone
    """
    parts = trigger_str.split()
    if len(parts) != 3:
        raise ValueError(f"Invalid trigger format: {trigger_str}")

    trigger_type = parts[0]
    time_parts = parts[1].split(":")
    timezone = parts[2]

    return {
        "type": trigger_type,
        "hour": int(time_parts[0]),
        "minute": int(time_parts[1]),
        "timezone": timezone,
    }


def generate_cron_entry(schedule: dict) -> str:
    """
    Generate a crontab entry for a schedule item.

    The cron entry should:
    1. Run at the specified time
    2. Only on weekdays (Mon-Fri)
    3. Call the scheduler with a wrapper that checks trading_day

    Format: minute hour * * day_of_week command
    """
    trigger = parse_trigger(schedule["trigger"])
    script = schedule["script"]
    args = " ".join(schedule["args"])

    # TODO: implement crontab entry generation
    pass


def run_if_trading(script: str, args: list[str]) -> int:
    """
    Run a script only if today is a trading day.
    Returns 0 if executed (or skipped non-trading-day), 1 on error.
    """
    # TODO: implement
    pass


def get_next_jobs(from_date: date = None, count: int = 5) -> list[dict]:
    """
    Get the next N scheduled jobs from a given date.
    Returns list of dicts with: date, time, job_id, job_name
    """
    # TODO: implement
    pass


def load_watchlist() -> list[dict]:
    """Load the watchlist stocks."""
    watchlist_path = Path(__file__).parent / WATCHLIST_FILE
    with open(watchlist_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("stocks", [])


def main():
    if len(sys.argv) < 2:
        print("Usage: python scheduler.py [run|next|check|generate-cron|run-if-trading]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "check":
        if len(sys.argv) < 3:
            check_date = date.today()
        else:
            check_date = date.fromisoformat(sys.argv[2])
        result = is_trading_day(check_date)
        print(json.dumps({"date": str(check_date), "is_trading_day": result}))

    elif command == "next":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        jobs = get_next_jobs(count=count)
        if jobs:
            print(json.dumps(jobs, ensure_ascii=False, indent=2))
        else:
            print("No upcoming jobs found.")

    elif command == "generate-cron":
        config = load_config()
        entries = []
        for sched in config["schedules"]:
            if sched.get("enabled", False):
                entry = generate_cron_entry(sched)
                if entry:
                    entries.append(f"# {sched['name']}")
                    entries.append(entry)
        if entries:
            print("\n".join(entries))
        else:
            print("# No enabled schedules found")

    elif command == "run-if-trading":
        if len(sys.argv) < 3:
            print("Usage: python scheduler.py run-if-trading <script> [args...]")
            sys.exit(1)
        script = sys.argv[2]
        args = sys.argv[3:]
        sys.exit(run_if_trading(script, args))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
