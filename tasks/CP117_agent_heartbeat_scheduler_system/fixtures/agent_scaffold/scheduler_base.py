"""
Agent Task Scheduler - Base Module

This module provides the foundation for a scheduled task system
that an AI agent uses internally for periodic operations like
heartbeat checks, log rotation, and directory monitoring.

Requirements (from team lead):
- Must support interval-based and cron-based scheduling
- Tasks must be start/stop/status controllable at runtime
- All executions must be logged with timestamps
- Heartbeat tasks must check configured directories for changes
- Must handle graceful shutdown (SIGTERM/SIGINT)
- Log output must follow the format in config.json
- Must support "silent mode" where heartbeat runs but produces
  no user-visible output (only internal log)
"""

import json
import signal
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable


class TaskState:
    """Represents the runtime state of a scheduled task."""
    PENDING = "pending"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class ScheduledTask:
    """A single scheduled task definition."""

    def __init__(self, task_id: str, description: str, enabled: bool = True):
        self.task_id = task_id
        self.description = description
        self.enabled = enabled
        self.state = TaskState.PENDING
        self.last_run: Optional[datetime] = None
        self.run_count: int = 0
        self.errors: list = []


# TODO: Implement the following classes:
# 1. HeartbeatTask(ScheduledTask) - periodic health check that monitors
#    configured directories for file changes
# 2. CronTask(ScheduledTask) - cron-expression based scheduling
# 3. TaskScheduler - main scheduler that manages all tasks, supports
#    start/stop/status/list operations
# 4. TaskLogger - handles log file writing with rotation support

# The scheduler should be usable like:
#   scheduler = TaskScheduler.from_config("config.json")
#   scheduler.start("heartbeat_check")
#   scheduler.status()  # returns dict of all task states
#   scheduler.stop("heartbeat_check")
#   scheduler.shutdown()  # graceful stop all
