"""Daily check and review handler."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


LOG_PATH = Path(__file__).parent.parent / "run_log.jsonl"


def generate_review(report_type: str | None = None, timestamp: str | None = None) -> dict:
    """Generate detailed daily review."""
    today = datetime.now().strftime("%Y-%m-%d")
    entries = _load_today_entries(today)

    review_lines = [f"# Daily Review - {today}", ""]
    for e in entries:
        review_lines.append(f"- [{e['timestamp']}] {e['command']} → {e['status']}")

    return {
        "status": "success",
        "report_type": "daily_review",
        "timestamp": timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "content": "\n".join(review_lines),
    }


def generate_check(report_type: str | None = None, timestamp: str | None = None) -> dict:
    """Generate simplified daily check with counts."""
    today = datetime.now().strftime("%Y-%m-%d")
    entries = _load_today_entries(today)

    total = len(entries)
    successful = sum(1 for e in entries if e.get("status") == "success")
    failed = sum(1 for e in entries if e.get("status") == "failed")
    denied = sum(1 for e in entries if e.get("status") == "denied")

    return {
        "status": "success",
        "report_type": "daily_check",
        "timestamp": timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "date": today,
            "total_reports": total,
            "successful": successful,
            "failed": failed,
            "denied": denied,
        },
    }


def _load_today_entries(today: str) -> list[dict]:
    """Load today's entries from run log."""
    entries = []
    if not LOG_PATH.exists():
        return entries
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("timestamp", "").startswith(today):
                    entries.append(entry)
            except json.JSONDecodeError:
                continue
    return entries
