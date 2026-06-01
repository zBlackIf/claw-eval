"""Simple cron-based task scheduler with reminder management.

Known issues reported by user:
1. Timezone is wrong (should be Asia/Shanghai, not UTC)
2. After user says "已打卡", remaining reminders for that day still fire
3. No per-task ack tracking — need ack state per task per day
4. retry logic ignores acknowledgment status
5. Missing: ability to add new tasks via CLI without editing YAML directly
"""
from __future__ import annotations

import datetime
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent / "config.yaml"
STATE_PATH = Path(__file__).parent / "state.json"


@dataclass
class TaskState:
    task_id: str
    last_fired: str | None = None
    ack_date: str | None = None  # date string YYYY-MM-DD when last acked


@dataclass
class SchedulerState:
    tasks: dict[str, TaskState] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"tasks": {k: {"task_id": v.task_id, "last_fired": v.last_fired, "ack_date": v.ack_date} for k, v in self.tasks.items()}}

    @classmethod
    def from_dict(cls, d: dict) -> "SchedulerState":
        tasks = {}
        for k, v in d.get("tasks", {}).items():
            tasks[k] = TaskState(task_id=v["task_id"], last_fired=v.get("last_fired"), ack_date=v.get("ack_date"))
        return cls(tasks=tasks)


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def load_state() -> SchedulerState:
    if STATE_PATH.exists():
        with open(STATE_PATH) as f:
            return SchedulerState.from_dict(json.load(f))
    return SchedulerState()


def save_state(state: SchedulerState) -> None:
    with open(STATE_PATH, "w") as f:
        json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)


def get_now(config: dict) -> datetime.datetime:
    """Get current time in configured timezone.

    BUG: Currently ignores config timezone and uses UTC.
    Should use Asia/Shanghai when config says so.
    """
    # BUG: always returns UTC regardless of config
    return datetime.datetime.now(datetime.timezone.utc)


def should_fire(task_config: dict, now: datetime.datetime, state: SchedulerState) -> bool:
    """Determine if a task should fire right now.

    BUG: Does not check if task was already acknowledged today.
    """
    task_id = task_config["id"]
    cron_expr = task_config["cron"]

    # Simple cron parsing (minute hour dom month dow)
    parts = cron_expr.split()
    minute, hour, dom, month, dow = parts

    if minute != "*" and int(minute) != now.minute:
        return False
    if hour != "*" and int(hour) != now.hour:
        return False
    if dom != "*" and int(dom) != now.day:
        return False
    if month != "*" and int(month) != now.month:
        return False
    if dow != "*" and int(dow) != now.weekday():
        return False

    # BUG: missing ack check — should not fire if already acked today
    return True


def should_retry(task_config: dict, config: dict, now: datetime.datetime, state: SchedulerState) -> bool:
    """Determine if a retry reminder should fire.

    BUG: Does not respect suppress_after_ack setting or per-task ack state.
    """
    task_id = task_config["id"]
    task_state = state.tasks.get(task_id)
    if not task_state or not task_state.last_fired:
        return False

    last_fired = datetime.datetime.fromisoformat(task_state.last_fired)
    retry_interval = config.get("notification_settings", {}).get("retry_interval_minutes", 120)
    max_retries = config.get("notification_settings", {}).get("max_retries", 7)

    elapsed_minutes = (now - last_fired).total_seconds() / 60
    retry_count = int(elapsed_minutes / retry_interval)

    if retry_count >= max_retries:
        return False

    # BUG: should check if task was acked today — if yes, no retry
    if elapsed_minutes >= retry_interval and (elapsed_minutes % retry_interval) < 1:
        return True

    return False


def acknowledge_task(task_id: str) -> bool:
    """Mark a task as acknowledged for today.

    BUG: Currently does nothing useful — doesn't actually prevent future retries.
    """
    state = load_state()
    config = load_config()
    now = get_now(config)
    today = now.strftime("%Y-%m-%d")

    if task_id not in state.tasks:
        state.tasks[task_id] = TaskState(task_id=task_id)

    state.tasks[task_id].ack_date = today
    save_state(state)
    # BUG: returns True but the should_fire/should_retry don't check ack_date
    return True


def add_task(task_id: str, name: str, cron: str, message: str, channel: str = "feishu", target_group: str = "") -> bool:
    """Add a new scheduled task to config.

    NOT IMPLEMENTED: User requested ability to add tasks without editing YAML.
    """
    raise NotImplementedError("add_task CLI not yet implemented")


def list_tasks() -> list[dict]:
    """List all configured tasks with their current state."""
    config = load_config()
    state = load_state()
    result = []
    for task in config.get("tasks", []):
        task_state = state.tasks.get(task["id"])
        result.append({
            "id": task["id"],
            "name": task["name"],
            "cron": task["cron"],
            "message": task["message"],
            "last_fired": task_state.last_fired if task_state else None,
            "ack_date": task_state.ack_date if task_state else None,
        })
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "list":
            for t in list_tasks():
                print(f"  [{t['id']}] {t['name']} | cron: {t['cron']} | acked: {t['ack_date']}")
        elif cmd == "ack" and len(sys.argv) > 2:
            ok = acknowledge_task(sys.argv[2])
            print(f"Acknowledged: {ok}")
        elif cmd == "add":
            print("ERROR: add_task not implemented")
            sys.exit(1)
        else:
            print(f"Unknown command: {cmd}")
            sys.exit(1)
    else:
        print("Usage: scheduler.py [list|ack <task_id>|add ...]")
