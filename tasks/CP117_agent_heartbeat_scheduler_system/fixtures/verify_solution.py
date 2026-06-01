"""Hidden verifier for CP117 — Agent Heartbeat Scheduler System.

Checks 11 dimensions (5 basic + 6 hidden advanced):
1. scheduler_module_exists - A scheduler.py with TaskScheduler class
2. heartbeat_implementation - HeartbeatTask that monitors directories
3. lifecycle_management - start/stop/status/list/shutdown operations
4. logging_system - Log entries with timestamps and rotation
5. graceful_shutdown - Signal handling for clean exit
6. [HIDDEN] runtime_correctness - Actually load & run the scheduler, verify behavior
7. [HIDDEN] thread_safety - Proper locking, no race conditions in shared state
8. [HIDDEN] error_resilience - Handles missing dirs, invalid config, double-start/stop
9. [HIDDEN] concurrent_multi_task - Run multiple tasks simultaneously, verify independence
10. [HIDDEN] directory_change_detection - Heartbeat detects actual file changes in dirs
11. [HIDDEN] log_rotation_behavior - Log rotation actually triggers at max_entries limit
"""
from __future__ import annotations

import json
import sys
import os
import time
import signal
import tempfile
import importlib.util
import threading
import re
from pathlib import Path
from datetime import datetime


def _find_scheduler_module(ws: Path) -> Path | None:
    """Find the main scheduler module."""
    scaffold = ws / "agent_scaffold"
    if not scaffold.exists():
        scaffold = ws / "fixtures" / "agent_scaffold"
    if not scaffold.exists():
        for p in ws.rglob("scheduler.py"):
            if "test" not in str(p) and "__pycache__" not in str(p):
                return p
        for p in ws.rglob("task_scheduler.py"):
            if "test" not in str(p) and "__pycache__" not in str(p):
                return p
        return None

    candidates = [
        scaffold / "scheduler.py",
        scaffold / "task_scheduler.py",
        scaffold / "scheduler" / "__init__.py",
        scaffold / "scheduler" / "main.py",
        scaffold / "src" / "scheduler.py",
    ]
    for c in candidates:
        if c.exists():
            return c

    for p in scaffold.rglob("scheduler*.py"):
        if "test" not in str(p) and "base" not in str(p) and "__pycache__" not in str(p):
            return p
    return None


def _load_module(path: Path, name: str = "scheduler"):
    """Dynamically load a module from path."""
    # Add parent to sys.path so relative imports work
    parent = str(path.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _get_all_code(ws: Path) -> str:
    """Get all non-test, non-base source code under the scaffold."""
    scaffold = ws / "agent_scaffold"
    if not scaffold.exists():
        scaffold = ws / "fixtures" / "agent_scaffold"
    if not scaffold.exists():
        scaffold = ws

    all_code = ""
    for py in scaffold.rglob("*.py"):
        if "__pycache__" not in str(py) and "test" not in py.name and "scheduler_base" not in py.name:
            all_code += _read(py) + "\n"
    return all_code


# ============================================================================
# Dim 1-5: Basic structural checks (reduced weight, easier to pass)
# ============================================================================

def check_scheduler_module(ws: Path) -> tuple[float, dict]:
    """Dim 1: Does a proper scheduler module with TaskScheduler class exist?"""
    info = {"found": False, "has_task_scheduler": False, "has_from_config": False,
            "has_scheduled_task": False, "path": None}

    mod_path = _find_scheduler_module(ws)
    if mod_path is None:
        return 0.0, info

    info["found"] = True
    info["path"] = str(mod_path)
    content = _read(mod_path)

    if "class TaskScheduler" in content or "class Scheduler" in content:
        info["has_task_scheduler"] = True
    if "from_config" in content or "load_config" in content:
        info["has_from_config"] = True
    if "class HeartbeatTask" in content or "class ScheduledTask" in content or "class CronTask" in content:
        info["has_scheduled_task"] = True

    parent = mod_path.parent
    for py in parent.rglob("*.py"):
        if py == mod_path:
            continue
        c = _read(py)
        if "class HeartbeatTask" in c or "class CronTask" in c:
            info["has_scheduled_task"] = True
            break

    score = 0.0
    if info["has_task_scheduler"]:
        score += 0.4
    if info["has_from_config"]:
        score += 0.3
    if info["has_scheduled_task"]:
        score += 0.3
    return score, info


def check_heartbeat_implementation(ws: Path) -> tuple[float, dict]:
    """Dim 2: Does HeartbeatTask monitor directories and report status?"""
    info = {"has_heartbeat_class": False, "monitors_dirs": False,
            "reports_status": False, "uses_threading": False}

    all_code = _get_all_code(ws)

    if "class HeartbeatTask" in all_code or "class Heartbeat" in all_code:
        info["has_heartbeat_class"] = True
    elif "def heartbeat" in all_code or "def run_heartbeat" in all_code:
        info["has_heartbeat_class"] = True

    dir_checks = ["os.listdir", "os.scandir", "Path.iterdir", "glob", "check_dirs",
                  "listdir", ".iterdir()", "os.path.exists"]
    if any(k in all_code for k in dir_checks):
        info["monitors_dirs"] = True

    status_checks = ["heartbeat_ok", "status", "no_changes", "system_normal", "all_clear"]
    if any(k in all_code.lower() for k in status_checks):
        info["reports_status"] = True

    if "threading" in all_code or "asyncio" in all_code or "Timer" in all_code:
        info["uses_threading"] = True

    score = 0.0
    if info["has_heartbeat_class"]:
        score += 0.3
    if info["monitors_dirs"]:
        score += 0.3
    if info["reports_status"]:
        score += 0.2
    if info["uses_threading"]:
        score += 0.2
    return score, info


def check_lifecycle_management(ws: Path) -> tuple[float, dict]:
    """Dim 3: start/stop/status/list/shutdown operations."""
    info = {"has_start": False, "has_stop": False, "has_status": False,
            "has_list": False, "has_shutdown": False}

    all_code = _get_all_code(ws)

    if "def start(" in all_code or "def start_task(" in all_code:
        info["has_start"] = True
    if "def stop(" in all_code or "def stop_task(" in all_code:
        info["has_stop"] = True
    if "def status(" in all_code or "def get_status(" in all_code:
        info["has_status"] = True
    if "def list_tasks(" in all_code or "def list(" in all_code or "def get_tasks(" in all_code:
        info["has_list"] = True
    if "def shutdown(" in all_code or "def stop_all(" in all_code or "def close(" in all_code:
        info["has_shutdown"] = True

    score = sum([
        0.25 if info["has_start"] else 0.0,
        0.25 if info["has_stop"] else 0.0,
        0.20 if info["has_status"] else 0.0,
        0.15 if info["has_list"] else 0.0,
        0.15 if info["has_shutdown"] else 0.0,
    ])
    return score, info


def check_logging_system(ws: Path) -> tuple[float, dict]:
    """Dim 4: Logging with timestamps and proper format."""
    info = {"has_logger_class": False, "uses_timestamps": False,
            "writes_to_file": False, "supports_rotation": False}

    all_code = _get_all_code(ws)

    if "class TaskLogger" in all_code or "class Logger" in all_code or "class SchedulerLogger" in all_code:
        info["has_logger_class"] = True
    elif "logging.getLogger" in all_code or "import logging" in all_code:
        info["has_logger_class"] = True

    ts_patterns = ["strftime", "datetime.now()", "time.strftime",
                   "%H:%M", "%Y-%m-%d", "isoformat", "timestamp"]
    if any(p in all_code for p in ts_patterns):
        info["uses_timestamps"] = True

    file_patterns = ["open(", "write_text", ".write(", "FileHandler",
                     "log_file", "log_path", "log_dir"]
    if any(p in all_code for p in file_patterns):
        info["writes_to_file"] = True

    rotation_patterns = ["max_log_entries", "rotate", "RotatingFileHandler",
                         "max_size", "max_entries", "truncate", "archive"]
    if any(p in all_code for p in rotation_patterns):
        info["supports_rotation"] = True

    score = 0.0
    if info["has_logger_class"]:
        score += 0.25
    if info["uses_timestamps"]:
        score += 0.30
    if info["writes_to_file"]:
        score += 0.25
    if info["supports_rotation"]:
        score += 0.20
    return score, info


def check_graceful_shutdown(ws: Path) -> tuple[float, dict]:
    """Dim 5: Signal handling for graceful shutdown."""
    info = {"handles_signals": False, "cleans_up_threads": False,
            "saves_state": False}

    all_code = _get_all_code(ws)

    if "signal.signal" in all_code or "signal.SIGTERM" in all_code or "signal.SIGINT" in all_code:
        info["handles_signals"] = True
    elif "atexit" in all_code:
        info["handles_signals"] = True

    thread_cleanup = [".join()", "daemon=True", "threading.Event",
                      "_stop_event", "cancel()", ".set()", ".is_set()"]
    if any(p in all_code for p in thread_cleanup):
        info["cleans_up_threads"] = True

    state_patterns = ["save_state", "persist", "json.dump", "last_run", "state_file"]
    if any(p in all_code for p in state_patterns):
        info["saves_state"] = True

    score = 0.0
    if info["handles_signals"]:
        score += 0.40
    if info["cleans_up_threads"]:
        score += 0.40
    if info["saves_state"]:
        score += 0.20
    return score, info


# ============================================================================
# Dim 6-8: HIDDEN advanced checks (higher weight, much harder to pass)
# ============================================================================

def check_runtime_correctness(ws: Path) -> tuple[float, dict]:
    """Dim 6 [HIDDEN]: Actually instantiate and run the scheduler to verify behavior.

    Tests:
    - Can load from config without crash
    - start() actually begins periodic execution (run_count increments)
    - stop() actually halts execution
    - status() returns correct state transitions
    - Log files are actually created with expected format (HH:MM - heartbeat: <status>)
    """
    info = {"loads_config": False, "runs_heartbeat": False, "stop_halts": False,
            "status_accurate": False, "log_format_correct": False}

    mod_path = _find_scheduler_module(ws)
    if mod_path is None:
        return 0.0, info

    mod = _load_module(mod_path)
    if mod is None:
        return 0.0, info

    TaskScheduler = getattr(mod, "TaskScheduler", None)
    if TaskScheduler is None:
        # Try alternate name
        TaskScheduler = getattr(mod, "Scheduler", None)
    if TaskScheduler is None:
        return 0.0, info

    # Test with a temp directory to avoid polluting workspace
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "agent_name": "verify-agent",
                "workspace_root": tmpdir,
                "heartbeat_interval_minutes": 0.005,  # 0.3 seconds
                "log_dir": "logs",
                "knowledge_dir": "knowledge",
                "memory_dir": "memory",
                "max_log_entries_per_file": 100,
                "tasks": [
                    {
                        "task_id": "heartbeat_check",
                        "description": "verify heartbeat",
                        "enabled": True,
                        "interval_minutes": 0.005,
                        "check_dirs": ["knowledge", "memory"],
                        "log_format": "HH:MM - heartbeat: <status>"
                    }
                ]
            }
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text(json.dumps(config))
            Path(tmpdir, "knowledge").mkdir()
            Path(tmpdir, "memory").mkdir()
            Path(tmpdir, "logs").mkdir()

            # Test 1: Load from config
            scheduler = None
            try:
                from_config = getattr(TaskScheduler, "from_config", None)
                if from_config:
                    scheduler = from_config(str(config_path))
                else:
                    scheduler = TaskScheduler(str(config_path))
                if scheduler is not None:
                    info["loads_config"] = True
            except Exception:
                return 0.0, info

            if scheduler is None:
                return 0.0, info

            # Test 2: Start and verify it runs
            try:
                scheduler.start("heartbeat_check")
                time.sleep(1.5)  # Wait for a few heartbeat cycles

                # Check if anything happened — look for log files or run_count
                status_result = None
                try:
                    status_fn = getattr(scheduler, "status", None) or getattr(scheduler, "get_status", None)
                    if status_fn:
                        status_result = status_fn("heartbeat_check")
                except Exception:
                    pass

                # Check run_count or running state
                if status_result and isinstance(status_result, dict):
                    state = status_result.get("state", status_result.get("status", ""))
                    run_count = status_result.get("run_count", 0)
                    if state == "running" or run_count > 0:
                        info["runs_heartbeat"] = True
                    if state == "running":
                        info["status_accurate"] = True

                # Also check log files as evidence of running
                log_dir = Path(tmpdir) / "logs"
                log_files = list(log_dir.glob("*"))
                if log_files:
                    info["runs_heartbeat"] = True
                    # Check log format matches "HH:MM - heartbeat: <status>"
                    for lf in log_files:
                        content = _read(lf)
                        if re.search(r"\d{2}:\d{2}\s*-\s*heartbeat:", content):
                            info["log_format_correct"] = True
                            break

            except Exception:
                pass

            # Test 3: Stop halts execution
            try:
                scheduler.stop("heartbeat_check")
                time.sleep(0.5)
                # Check state after stop
                try:
                    status_fn = getattr(scheduler, "status", None) or getattr(scheduler, "get_status", None)
                    if status_fn:
                        status_result = status_fn("heartbeat_check")
                        if isinstance(status_result, dict):
                            state = status_result.get("state", status_result.get("status", ""))
                            if state in ("stopped", "pending", "idle"):
                                info["stop_halts"] = True
                                info["status_accurate"] = True
                except Exception:
                    pass
            except Exception:
                pass

            # Cleanup
            try:
                shutdown_fn = getattr(scheduler, "shutdown", None) or getattr(scheduler, "stop_all", None)
                if shutdown_fn:
                    shutdown_fn()
            except Exception:
                pass

    except Exception:
        pass

    score = 0.0
    if info["loads_config"]:
        score += 0.15
    if info["runs_heartbeat"]:
        score += 0.25
    if info["stop_halts"]:
        score += 0.20
    if info["status_accurate"]:
        score += 0.20
    if info["log_format_correct"]:
        score += 0.20
    return score, info


def check_thread_safety(ws: Path) -> tuple[float, dict]:
    """Dim 7 [HIDDEN]: Check for proper thread safety patterns.

    Checks:
    - Uses Lock/RLock for shared state (task registry, running tasks dict)
    - Uses threading.Event (not bare booleans) for stop signaling
    - Does not use bare time.sleep() in main thread for scheduling
    - Thread-safe status reporting (lock around state reads)
    """
    info = {"uses_lock": False, "uses_event_for_stop": False,
            "no_busy_wait": False, "atomic_state_access": False}

    all_code = _get_all_code(ws)
    if not all_code.strip():
        return 0.0, info

    # Check for Lock/RLock usage
    lock_patterns = ["threading.Lock()", "threading.RLock()", "Lock()", "RLock()",
                     "self._lock", "self.lock", "with self._lock", "with self.lock"]
    if any(p in all_code for p in lock_patterns):
        info["uses_lock"] = True

    # Check for Event-based stop signaling (not bare bool flags)
    # Good: threading.Event() with .set()/.wait()/.is_set()
    # Bad: self._running = False (a bare boolean)
    event_patterns = ["threading.Event()", "Event()", "_stop_event", "stop_event",
                      "_shutdown_event", "shutdown_event"]
    if any(p in all_code for p in event_patterns):
        # Verify it's actually used for control flow (wait/is_set)
        if ".wait(" in all_code or ".is_set()" in all_code:
            info["uses_event_for_stop"] = True

    # Check that scheduling doesn't use busy-wait (while True: sleep(interval))
    # Good patterns: Event.wait(timeout=interval), Timer, sched module
    # Bad: while self._running: time.sleep(self.interval)
    has_event_wait = ".wait(" in all_code and "timeout" in all_code
    has_timer = "threading.Timer" in all_code or "Timer(" in all_code
    has_sched = "sched.scheduler" in all_code
    if has_event_wait or has_timer or has_sched:
        info["no_busy_wait"] = True

    # Check for atomic state access (lock around state modifications)
    # Look for 'with self.*lock' patterns near state changes
    lock_context_pattern = r"with\s+self[._]\w*lock"
    if re.search(lock_context_pattern, all_code):
        info["atomic_state_access"] = True
    # Also accept acquire/release pattern
    elif "acquire()" in all_code and "release()" in all_code:
        info["atomic_state_access"] = True

    score = 0.0
    if info["uses_lock"]:
        score += 0.30
    if info["uses_event_for_stop"]:
        score += 0.30
    if info["no_busy_wait"]:
        score += 0.20
    if info["atomic_state_access"]:
        score += 0.20
    return score, info


def check_error_resilience(ws: Path) -> tuple[float, dict]:
    """Dim 8 [HIDDEN]: Error handling and edge cases.

    Tests (runtime):
    - Handles missing/non-existent directories gracefully (no crash)
    - Handles starting an already-running task (idempotent or raises clear error)
    - Handles stopping an already-stopped task
    - Handles invalid task_id in start/stop/status
    - Config with no tasks doesn't crash
    """
    info = {"handles_missing_dirs": False, "handles_double_start": False,
            "handles_double_stop": False, "handles_invalid_task_id": False,
            "handles_empty_config": False}

    mod_path = _find_scheduler_module(ws)
    if mod_path is None:
        return 0.0, info

    mod = _load_module(mod_path)
    if mod is None:
        return 0.0, info

    TaskScheduler = getattr(mod, "TaskScheduler", None)
    if TaskScheduler is None:
        TaskScheduler = getattr(mod, "Scheduler", None)
    if TaskScheduler is None:
        return 0.0, info

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test 1: Config with check_dirs pointing to non-existent directories
            config_missing_dirs = {
                "agent_name": "test-agent",
                "workspace_root": tmpdir,
                "heartbeat_interval_minutes": 0.005,
                "log_dir": "logs",
                "knowledge_dir": "nonexistent_knowledge_xyz",
                "memory_dir": "nonexistent_memory_xyz",
                "max_log_entries_per_file": 100,
                "tasks": [
                    {
                        "task_id": "heartbeat_check",
                        "description": "test heartbeat",
                        "enabled": True,
                        "interval_minutes": 0.005,
                        "check_dirs": ["nonexistent_knowledge_xyz", "nonexistent_memory_xyz"],
                        "log_format": "HH:MM - heartbeat: <status>"
                    }
                ]
            }
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text(json.dumps(config_missing_dirs))
            Path(tmpdir, "logs").mkdir(exist_ok=True)

            try:
                from_config = getattr(TaskScheduler, "from_config", None)
                if from_config:
                    scheduler = from_config(str(config_path))
                else:
                    scheduler = TaskScheduler(str(config_path))

                # Start with missing dirs — should not crash
                try:
                    scheduler.start("heartbeat_check")
                    time.sleep(0.5)
                    scheduler.stop("heartbeat_check")
                    info["handles_missing_dirs"] = True
                except (FileNotFoundError, OSError):
                    # Crashed on missing dir — fails this check
                    pass
                except Exception:
                    # Other exception but didn't crash the process — partial credit
                    info["handles_missing_dirs"] = True
            except Exception:
                pass

            # Test 2: Double start
            config_normal = {
                "agent_name": "test-agent",
                "workspace_root": tmpdir,
                "heartbeat_interval_minutes": 60,
                "log_dir": "logs",
                "knowledge_dir": "knowledge",
                "memory_dir": "memory",
                "max_log_entries_per_file": 100,
                "tasks": [
                    {
                        "task_id": "heartbeat_check",
                        "description": "test",
                        "enabled": True,
                        "interval_minutes": 60,
                        "check_dirs": ["knowledge", "memory"],
                        "log_format": "HH:MM - heartbeat: <status>"
                    }
                ]
            }
            config_path.write_text(json.dumps(config_normal))
            Path(tmpdir, "knowledge").mkdir(exist_ok=True)
            Path(tmpdir, "memory").mkdir(exist_ok=True)

            try:
                from_config = getattr(TaskScheduler, "from_config", None)
                if from_config:
                    scheduler = from_config(str(config_path))
                else:
                    scheduler = TaskScheduler(str(config_path))

                scheduler.start("heartbeat_check")
                # Starting again should not crash or create duplicate threads
                try:
                    scheduler.start("heartbeat_check")
                    info["handles_double_start"] = True
                except (ValueError, RuntimeError, KeyError):
                    # Raising a clear error is acceptable
                    info["handles_double_start"] = True
                except Exception:
                    pass

                # Test 3: Double stop
                scheduler.stop("heartbeat_check")
                try:
                    scheduler.stop("heartbeat_check")
                    info["handles_double_stop"] = True
                except (ValueError, RuntimeError, KeyError):
                    info["handles_double_stop"] = True
                except Exception:
                    pass

                # Test 4: Invalid task_id
                try:
                    scheduler.start("nonexistent_task_xyz_999")
                except (KeyError, ValueError, RuntimeError):
                    # Proper error for invalid task
                    info["handles_invalid_task_id"] = True
                except Exception:
                    pass

                try:
                    shutdown_fn = getattr(scheduler, "shutdown", None)
                    if shutdown_fn:
                        shutdown_fn()
                except Exception:
                    pass

            except Exception:
                pass

            # Test 5: Empty task list config
            config_empty = {
                "agent_name": "test-agent",
                "workspace_root": tmpdir,
                "heartbeat_interval_minutes": 60,
                "log_dir": "logs",
                "knowledge_dir": "knowledge",
                "memory_dir": "memory",
                "max_log_entries_per_file": 100,
                "tasks": []
            }
            config_path.write_text(json.dumps(config_empty))
            try:
                from_config = getattr(TaskScheduler, "from_config", None)
                if from_config:
                    scheduler = from_config(str(config_path))
                else:
                    scheduler = TaskScheduler(str(config_path))
                # Should not crash with empty tasks
                tasks = None
                list_fn = getattr(scheduler, "list_tasks", None) or getattr(scheduler, "get_tasks", None)
                if list_fn:
                    tasks = list_fn()
                info["handles_empty_config"] = True
                try:
                    shutdown_fn = getattr(scheduler, "shutdown", None)
                    if shutdown_fn:
                        shutdown_fn()
                except Exception:
                    pass
            except Exception:
                pass

    except Exception:
        pass

    score = 0.0
    if info["handles_missing_dirs"]:
        score += 0.25
    if info["handles_double_start"]:
        score += 0.20
    if info["handles_double_stop"]:
        score += 0.20
    if info["handles_invalid_task_id"]:
        score += 0.20
    if info["handles_empty_config"]:
        score += 0.15
    return score, info


# ============================================================================
# Dim 9-11: HIDDEN advanced checks (harder behavioral verification)
# ============================================================================

def check_concurrent_multi_task(ws: Path) -> tuple[float, dict]:
    """Dim 9 [HIDDEN]: Run multiple tasks concurrently and verify independence.

    Tests:
    - Can start two tasks simultaneously without crash
    - Each task maintains its own independent run_count
    - Stopping one task does not affect the other
    - list_tasks() accurately reflects mixed running/stopped states
    """
    info = {"multi_start_ok": False, "independent_run_counts": False,
            "selective_stop_ok": False, "list_reflects_mixed_state": False}

    mod_path = _find_scheduler_module(ws)
    if mod_path is None:
        return 0.0, info

    mod = _load_module(mod_path)
    if mod is None:
        return 0.0, info

    TaskScheduler = getattr(mod, "TaskScheduler", None)
    if TaskScheduler is None:
        TaskScheduler = getattr(mod, "Scheduler", None)
    if TaskScheduler is None:
        return 0.0, info

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "agent_name": "multi-task-test",
                "workspace_root": tmpdir,
                "heartbeat_interval_minutes": 0.005,
                "log_dir": "logs",
                "knowledge_dir": "knowledge",
                "memory_dir": "memory",
                "max_log_entries_per_file": 100,
                "tasks": [
                    {
                        "task_id": "task_alpha",
                        "description": "Alpha heartbeat",
                        "enabled": True,
                        "interval_minutes": 0.005,
                        "check_dirs": ["knowledge"],
                        "log_format": "HH:MM - heartbeat: <status>"
                    },
                    {
                        "task_id": "task_beta",
                        "description": "Beta heartbeat",
                        "enabled": True,
                        "interval_minutes": 0.005,
                        "check_dirs": ["memory"],
                        "log_format": "HH:MM - heartbeat: <status>"
                    }
                ]
            }
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text(json.dumps(config))
            Path(tmpdir, "knowledge").mkdir()
            Path(tmpdir, "memory").mkdir()
            Path(tmpdir, "logs").mkdir()

            from_config = getattr(TaskScheduler, "from_config", None)
            if from_config:
                scheduler = from_config(str(config_path))
            else:
                scheduler = TaskScheduler(str(config_path))

            if scheduler is None:
                return 0.0, info

            # Test 1: Start both tasks
            try:
                scheduler.start("task_alpha")
                scheduler.start("task_beta")
                info["multi_start_ok"] = True
            except Exception:
                try:
                    shutdown_fn = getattr(scheduler, "shutdown", None)
                    if shutdown_fn:
                        shutdown_fn()
                except Exception:
                    pass
                return 0.0, info

            time.sleep(1.5)

            # Test 2: Both tasks ran independently (each has run_count > 0)
            try:
                status_fn = getattr(scheduler, "status", None) or getattr(scheduler, "get_status", None)
                if status_fn:
                    sa = status_fn("task_alpha")
                    sb = status_fn("task_beta")
                    if isinstance(sa, dict) and isinstance(sb, dict):
                        rc_a = sa.get("run_count", 0)
                        rc_b = sb.get("run_count", 0)
                        if rc_a > 0 and rc_b > 0:
                            info["independent_run_counts"] = True
            except Exception:
                pass

            # Test 3: Stop only one task, other keeps running
            try:
                scheduler.stop("task_alpha")
                time.sleep(0.8)
                status_fn = getattr(scheduler, "status", None) or getattr(scheduler, "get_status", None)
                if status_fn:
                    sa = status_fn("task_alpha")
                    sb = status_fn("task_beta")
                    if isinstance(sa, dict) and isinstance(sb, dict):
                        state_a = sa.get("state", sa.get("status", ""))
                        state_b = sb.get("state", sb.get("status", ""))
                        if state_a in ("stopped", "pending", "idle") and state_b == "running":
                            info["selective_stop_ok"] = True
            except Exception:
                pass

            # Test 4: list_tasks reflects the mixed state
            try:
                list_fn = getattr(scheduler, "list_tasks", None) or getattr(scheduler, "get_tasks", None)
                if list_fn:
                    tasks_list = list_fn()
                    if isinstance(tasks_list, list) and len(tasks_list) >= 2:
                        states = set()
                        for t in tasks_list:
                            if isinstance(t, dict):
                                s = t.get("state", t.get("status", ""))
                                states.add(s)
                        # Should have at least two different states (running + stopped)
                        if len(states) >= 2:
                            info["list_reflects_mixed_state"] = True
            except Exception:
                pass

            # Cleanup
            try:
                shutdown_fn = getattr(scheduler, "shutdown", None) or getattr(scheduler, "stop_all", None)
                if shutdown_fn:
                    shutdown_fn()
            except Exception:
                pass

    except Exception:
        pass

    score = 0.0
    if info["multi_start_ok"]:
        score += 0.20
    if info["independent_run_counts"]:
        score += 0.30
    if info["selective_stop_ok"]:
        score += 0.30
    if info["list_reflects_mixed_state"]:
        score += 0.20
    return score, info


def check_directory_change_detection(ws: Path) -> tuple[float, dict]:
    """Dim 10 [HIDDEN]: Heartbeat actually detects file changes in monitored dirs.

    Tests:
    - Heartbeat reports different status when monitored dir content changes
    - Adding a file to a monitored dir is reflected in heartbeat output/status
    - Removing a file is also detected
    """
    info = {"detects_file_addition": False, "status_changes_on_mutation": False,
            "log_reflects_change": False}

    mod_path = _find_scheduler_module(ws)
    if mod_path is None:
        return 0.0, info

    mod = _load_module(mod_path)
    if mod is None:
        return 0.0, info

    TaskScheduler = getattr(mod, "TaskScheduler", None)
    if TaskScheduler is None:
        TaskScheduler = getattr(mod, "Scheduler", None)
    if TaskScheduler is None:
        return 0.0, info

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "agent_name": "change-detect-test",
                "workspace_root": tmpdir,
                "heartbeat_interval_minutes": 0.005,
                "log_dir": "logs",
                "knowledge_dir": "knowledge",
                "memory_dir": "memory",
                "max_log_entries_per_file": 200,
                "tasks": [
                    {
                        "task_id": "heartbeat_check",
                        "description": "change detection test",
                        "enabled": True,
                        "interval_minutes": 0.005,
                        "check_dirs": ["knowledge"],
                        "log_format": "HH:MM - heartbeat: <status>"
                    }
                ]
            }
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text(json.dumps(config))
            knowledge_dir = Path(tmpdir, "knowledge")
            knowledge_dir.mkdir()
            Path(tmpdir, "memory").mkdir()
            Path(tmpdir, "logs").mkdir()

            from_config = getattr(TaskScheduler, "from_config", None)
            if from_config:
                scheduler = from_config(str(config_path))
            else:
                scheduler = TaskScheduler(str(config_path))

            if scheduler is None:
                return 0.0, info

            # Run heartbeat with empty dir first
            try:
                scheduler.start("heartbeat_check")
                time.sleep(1.0)

                # Capture status/logs before change
                status_fn = getattr(scheduler, "status", None) or getattr(scheduler, "get_status", None)
                status_before = None
                if status_fn:
                    status_before = status_fn("heartbeat_check")

                # Now add files to the monitored directory
                (knowledge_dir / "new_document.md").write_text("# New Doc\nContent here.")
                (knowledge_dir / "data.json").write_text('{"key": "value"}')

                time.sleep(1.5)

                # Check if heartbeat detected the change
                status_after = None
                if status_fn:
                    status_after = status_fn("heartbeat_check")

                # Check run_count increased (heartbeat kept running)
                if status_after and isinstance(status_after, dict):
                    rc = status_after.get("run_count", 0)
                    if rc >= 2:
                        info["detects_file_addition"] = True

                # Check if status has any notion of "changes detected"
                if status_before and status_after:
                    if isinstance(status_before, dict) and isinstance(status_after, dict):
                        # Look for any change indicator: last_change, changes_detected, etc.
                        change_keys = ["last_change", "changes_detected", "files_changed",
                                       "change_count", "dir_changes", "last_status"]
                        for k in change_keys:
                            if k in status_after and status_after[k] != status_before.get(k):
                                info["status_changes_on_mutation"] = True
                                break
                        # Also check if the status message itself changed
                        msg_b = str(status_before.get("last_result", status_before.get("message", "")))
                        msg_a = str(status_after.get("last_result", status_after.get("message", "")))
                        if msg_b and msg_a and msg_b != msg_a:
                            info["status_changes_on_mutation"] = True

                # Check logs for evidence of change detection
                log_dir = Path(tmpdir) / "logs"
                log_files = list(log_dir.glob("*"))
                for lf in log_files:
                    content = _read(lf)
                    # Look for change-related words in log output
                    change_indicators = ["change", "modified", "new file", "added",
                                         "different", "updated", "2 file", "new_document"]
                    if any(ind in content.lower() for ind in change_indicators):
                        info["log_reflects_change"] = True
                        break

                scheduler.stop("heartbeat_check")
            except Exception:
                pass

            # Cleanup
            try:
                shutdown_fn = getattr(scheduler, "shutdown", None) or getattr(scheduler, "stop_all", None)
                if shutdown_fn:
                    shutdown_fn()
            except Exception:
                pass

    except Exception:
        pass

    score = 0.0
    if info["detects_file_addition"]:
        score += 0.30
    if info["status_changes_on_mutation"]:
        score += 0.40
    if info["log_reflects_change"]:
        score += 0.30
    return score, info


def check_log_rotation_behavior(ws: Path) -> tuple[float, dict]:
    """Dim 11 [HIDDEN]: Log rotation actually triggers when max_entries is exceeded.

    Tests:
    - With max_log_entries=5, after 8+ heartbeat cycles, rotation occurs
    - Old log file is archived/rotated (new file started or entries trimmed)
    - Multiple log files exist OR single file has <= max entries
    """
    info = {"rotation_triggers": False, "entries_bounded": False,
            "archive_created": False}

    mod_path = _find_scheduler_module(ws)
    if mod_path is None:
        return 0.0, info

    mod = _load_module(mod_path)
    if mod is None:
        return 0.0, info

    TaskScheduler = getattr(mod, "TaskScheduler", None)
    if TaskScheduler is None:
        TaskScheduler = getattr(mod, "Scheduler", None)
    if TaskScheduler is None:
        return 0.0, info

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use a very low max_log_entries to trigger rotation quickly
            config = {
                "agent_name": "rotation-test",
                "workspace_root": tmpdir,
                "heartbeat_interval_minutes": 0.003,
                "log_dir": "logs",
                "knowledge_dir": "knowledge",
                "memory_dir": "memory",
                "max_log_entries_per_file": 5,
                "tasks": [
                    {
                        "task_id": "heartbeat_check",
                        "description": "rotation test heartbeat",
                        "enabled": True,
                        "interval_minutes": 0.003,
                        "check_dirs": ["knowledge"],
                        "log_format": "HH:MM - heartbeat: <status>"
                    }
                ]
            }
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text(json.dumps(config))
            Path(tmpdir, "knowledge").mkdir()
            Path(tmpdir, "memory").mkdir()
            Path(tmpdir, "logs").mkdir()

            from_config = getattr(TaskScheduler, "from_config", None)
            if from_config:
                scheduler = from_config(str(config_path))
            else:
                scheduler = TaskScheduler(str(config_path))

            if scheduler is None:
                return 0.0, info

            try:
                scheduler.start("heartbeat_check")
                # Run long enough for at least 8-10 heartbeat cycles (at 0.003 min = 0.18s)
                time.sleep(3.0)
                scheduler.stop("heartbeat_check")
            except Exception:
                pass

            # Cleanup scheduler
            try:
                shutdown_fn = getattr(scheduler, "shutdown", None) or getattr(scheduler, "stop_all", None)
                if shutdown_fn:
                    shutdown_fn()
            except Exception:
                pass

            # Now inspect log directory
            log_dir = Path(tmpdir) / "logs"
            all_log_files = list(log_dir.rglob("*"))
            # Filter to actual files (not dirs)
            log_files = [f for f in all_log_files if f.is_file()]

            if len(log_files) == 0:
                return 0.0, info

            # Check 1: Multiple log files created (rotation happened)
            if len(log_files) >= 2:
                info["rotation_triggers"] = True
                info["archive_created"] = True

            # Check 2: No single file has more than max_entries (5) lines of log content
            max_entries_in_file = 0
            for lf in log_files:
                content = _read(lf)
                # Count log entry lines (lines matching heartbeat pattern or non-empty)
                entry_lines = [l for l in content.strip().splitlines()
                               if l.strip() and "heartbeat" in l.lower()]
                if not entry_lines:
                    # Fallback: count all non-empty lines
                    entry_lines = [l for l in content.strip().splitlines() if l.strip()]
                max_entries_in_file = max(max_entries_in_file, len(entry_lines))

            # If the maximum entries per file is bounded near max_log_entries (allow some slack)
            if max_entries_in_file <= 7:  # max_log_entries=5, allow slight overshoot
                info["entries_bounded"] = True
                if not info["rotation_triggers"]:
                    # Single file but entries are bounded -> rotation may have truncated
                    info["rotation_triggers"] = True

    except Exception:
        pass

    score = 0.0
    if info["rotation_triggers"]:
        score += 0.35
    if info["entries_bounded"]:
        score += 0.35
    if info["archive_created"]:
        score += 0.30
    return score, info


# ============================================================================
# Main grading
# ============================================================================

def grade_workspace(ws: Path) -> dict:
    """Main grading function with rebalanced weights.

    Basic checks (dims 1-5): 25% total — easy to pass, establishes baseline
    Hidden checks (dims 6-11): 75% total — much harder, separates strong from weak

    Target: strong model 0.7-0.85, weak model 0.4-0.6
    """
    dims = {}

    # Basic structural checks (reduced weights — easy for all models)
    weights = {
        "scheduler_module": 0.06,
        "heartbeat_implementation": 0.06,
        "lifecycle_management": 0.05,
        "logging_system": 0.04,
        "graceful_shutdown": 0.04,
        # Hidden advanced checks (higher weights — hard behavioral verification)
        "runtime_correctness": 0.20,
        "thread_safety": 0.12,
        "error_resilience": 0.13,
        "concurrent_multi_task": 0.12,
        "directory_change_detection": 0.10,
        "log_rotation_behavior": 0.08,
    }

    s1, d1 = check_scheduler_module(ws)
    s2, d2 = check_heartbeat_implementation(ws)
    s3, d3 = check_lifecycle_management(ws)
    s4, d4 = check_logging_system(ws)
    s5, d5 = check_graceful_shutdown(ws)
    s6, d6 = check_runtime_correctness(ws)
    s7, d7 = check_thread_safety(ws)
    s8, d8 = check_error_resilience(ws)
    s9, d9 = check_concurrent_multi_task(ws)
    s10, d10 = check_directory_change_detection(ws)
    s11, d11 = check_log_rotation_behavior(ws)

    dims["scheduler_module"] = {"score": round(s1, 4), "details": d1}
    dims["heartbeat_implementation"] = {"score": round(s2, 4), "details": d2}
    dims["lifecycle_management"] = {"score": round(s3, 4), "details": d3}
    dims["logging_system"] = {"score": round(s4, 4), "details": d4}
    dims["graceful_shutdown"] = {"score": round(s5, 4), "details": d5}
    dims["runtime_correctness"] = {"score": round(s6, 4), "details": d6}
    dims["thread_safety"] = {"score": round(s7, 4), "details": d7}
    dims["error_resilience"] = {"score": round(s8, 4), "details": d8}
    dims["concurrent_multi_task"] = {"score": round(s9, 4), "details": d9}
    dims["directory_change_detection"] = {"score": round(s10, 4), "details": d10}
    dims["log_rotation_behavior"] = {"score": round(s11, 4), "details": d11}

    overall = sum(weights[k] * dims[k]["score"] for k in weights)

    return {
        "overall_score": round(overall, 4),
        "dimensions": dims,
        "weights": weights,
    }


def main():
    ws = Path("/workspace")
    if not (ws / "agent_scaffold").exists() and not (ws / "fixtures" / "agent_scaffold").exists():
        found = list(ws.rglob("scheduler.py"))
        if found:
            pass
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
