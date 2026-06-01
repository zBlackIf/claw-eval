"""Basic tests for the scheduler system - provided to the agent."""

import json
import time
import tempfile
from pathlib import Path


def test_config_loading():
    """Scheduler should load from config.json."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from scheduler import TaskScheduler

    config_path = Path(__file__).parent.parent / "config.json"
    scheduler = TaskScheduler.from_config(str(config_path))
    assert scheduler is not None
    tasks = scheduler.list_tasks()
    assert len(tasks) >= 2
    assert any(t["task_id"] == "heartbeat_check" for t in tasks)


def test_start_stop():
    """Scheduler should support start/stop lifecycle."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from scheduler import TaskScheduler

    config_path = Path(__file__).parent.parent / "config.json"
    scheduler = TaskScheduler.from_config(str(config_path))
    scheduler.start("heartbeat_check")
    status = scheduler.status("heartbeat_check")
    assert status["state"] == "running"
    scheduler.stop("heartbeat_check")
    status = scheduler.status("heartbeat_check")
    assert status["state"] == "stopped"
    scheduler.shutdown()


def test_heartbeat_logs():
    """Heartbeat execution should produce log entries."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from scheduler import TaskScheduler

    with tempfile.TemporaryDirectory() as tmpdir:
        config = {
            "agent_name": "test-agent",
            "workspace_root": tmpdir,
            "heartbeat_interval_minutes": 0.01,
            "log_dir": "logs",
            "knowledge_dir": "knowledge",
            "memory_dir": "memory",
            "max_log_entries_per_file": 100,
            "tasks": [
                {
                    "task_id": "heartbeat_check",
                    "description": "test heartbeat",
                    "enabled": True,
                    "interval_minutes": 0.01,
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

        scheduler = TaskScheduler.from_config(str(config_path))
        scheduler.start("heartbeat_check")
        time.sleep(2)
        scheduler.stop("heartbeat_check")
        scheduler.shutdown()

        log_dir = Path(tmpdir) / "logs"
        log_files = list(log_dir.glob("*.log")) + list(log_dir.glob("*.md"))
        assert len(log_files) > 0, "No log files created"
        log_content = log_files[0].read_text()
        assert "heartbeat" in log_content.lower()


if __name__ == "__main__":
    test_config_loading()
    print("PASS: test_config_loading")
    test_start_stop()
    print("PASS: test_start_stop")
    test_heartbeat_logs()
    print("PASS: test_heartbeat_logs")
    print("\nAll basic tests passed!")
