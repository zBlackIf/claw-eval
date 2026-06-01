"""Agent Command Dispatcher - Routes RUN commands to handlers."""
from __future__ import annotations

import importlib
import json
import re
import sys
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any


CONFIG_PATH = Path(__file__).parent / "dispatch_config.yaml"
LOG_PATH = Path(__file__).parent / "run_log.jsonl"


class DispatchError(Exception):
    pass


class CommandDispatcher:
    def __init__(self, config_path: Path = CONFIG_PATH):
        self.config = self._load_config(config_path)
        self.handlers: dict[str, Any] = {}

    def _load_config(self, path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def parse_command(self, raw: str) -> tuple[str, str | None]:
        """Parse a RUN command string into (command_type, report_type).

        Examples:
            'RUN REPORT_TYPE=快报' -> ('report', '快报')
            'RUN DAILY_REVIEW' -> ('daily_review', None)
            'RUN DAILY_CHECK' -> ('daily_check', None)
        """
        raw = raw.strip()

        # Match RUN REPORT_TYPE commands
        m = re.match(r"RUN\s+REPORT_TYPE(.+)", raw)
        if m:
            return ("report", m.group(1).strip())

        # Match daily commands
        if raw == "RUN DAILY_REVIEW":
            return ("daily_review", None)
        if raw == "RUN DAILY_CHECK":
            return ("daily_check", None)

        raise DispatchError(f"Unknown command format: {raw}")

    def _resolve_handler(self, handler_path: str):
        """Import and cache handler module."""
        if handler_path in self.handlers:
            return self.handlers[handler_path]

        mod = importlib.import_module(handler_path)
        self.handlers[handler_path] = mod
        return mod

    def dispatch(self, raw_command: str, timestamp: str | None = None) -> dict:
        """Dispatch a command to its handler and return status."""
        ts = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cmd_type, report_type = self.parse_command(raw_command)

        # Find matching rule
        rule = None
        for r in self.config.get("dispatch_rules", []):
            if r["command"] == raw_command:
                rule = r
                break

        if not rule:
            return {"status": "error", "message": f"No rule for: {raw_command}"}

        # Resolve handler
        handler_mod = self._resolve_handler(rule["handler"])
        method_name = rule.get("method", "handle")
        handler_fn = getattr(handler_mod, method_name)

        # Execute
        result = handler_fn(report_type=report_type, timestamp=ts)

        # Log
        log_entry = {
            "timestamp": ts,
            "command": raw_command,
            "handler": rule["handler"],
            "status": result.get("status", "unknown"),
        }
        self._append_log(log_entry)

        return result

    def _append_log(self, entry: dict):
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def generate_daily_check(self) -> dict:
        """Generate daily check summary from run log."""
        today = datetime.now().strftime("%Y-%m-%d")
        entries = []

        with open(LOG_PATH, "r") as f:
            for line in f:
                entry = json.loads(line)
                if entry["timestamp"].startswith(today):
                    entries.append(entry)

        # BUG: wrong aggregation - counts all entries as successful
        return {
            "date": today,
            "total_reports": len(entries),
            "successful": len(entries),
            "failed": 0,
            "report": f"Daily check {today}: {len(entries)} reports generated"
        }

    def validate_config(self) -> list[str]:
        """Validate dispatch configuration. Returns list of errors."""
        errors = []

        for i, rule in enumerate(self.config.get("dispatch_rules", [])):
            # Check handler exists
            handler_path = rule.get("handler", "")
            try:
                self._resolve_handler(handler_path)
            except (ImportError, ModuleNotFoundError) as e:
                errors.append(f"Rule {i}: handler '{handler_path}' not importable: {e}")

            # Check schedule format (basic cron validation)
            schedule = rule.get("schedule", "")
            parts = schedule.split()
            if len(parts) != 5:
                errors.append(f"Rule {i}: invalid cron '{schedule}' (need 5 fields)")

        return errors


def main():
    """CLI entry point for testing."""
    if len(sys.argv) < 2:
        print("Usage: python dispatcher.py <command>")
        print("  e.g.: python dispatcher.py 'RUN REPORT_TYPE=快报'")
        sys.exit(1)

    dispatcher = CommandDispatcher()

    # Validate first
    errors = dispatcher.validate_config()
    if errors:
        print("Config validation errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    result = dispatcher.dispatch(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
