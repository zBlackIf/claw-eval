#!/usr/bin/env python3
"""
Project Report Generator - generates Zentao project status reports.

Usage:
    python generate_reports.py

Reads projects.json and schedule.csv from the same directory,
outputs markdown reports to ./output/
"""
import json
import csv
import os
from datetime import datetime, date

CURRENT_DATE = date(2026, 4, 23)
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(DATA_DIR, "output")


def load_projects():
    with open(os.path.join(DATA_DIR, "projects.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def load_schedule():
    """Load schedule.csv and return a dict keyed by execution_id (int)."""
    schedule = {}
    # TODO: implement CSV loading
    # Each row has: execution_id, project_name, owner, phase, schedule_notes
    return schedule


def calculate_metrics(project, report_date):
    """Calculate project metrics: actual_progress, expected_progress, overdue tasks, lag_rate."""
    tasks = project.get("tasks", [])
    total = len(tasks)
    if total == 0:
        return {}

    done_count = 0
    overdue_tasks = []
    expected_done = 0

    for task in tasks:
        # TODO: calculate done_count, overdue_tasks, expected_done
        pass

    metrics = {
        "total_tasks": total,
        "done_count": done_count,
        "actual_progress": 0,
        "expected_progress": 0,
        "overdue_count": len(overdue_tasks),
        "overdue_tasks": overdue_tasks,
        "lag_rate": 0,
        "estimated_hours": sum(t.get("estimated_hours", 0) for t in tasks),
        "consumed_hours": sum(t.get("consumed_hours", 0) for t in tasks),
    }
    return metrics


def determine_risk_level(overdue_count, lag_rate):
    """Determine risk level based on overdue count and lag rate."""
    # TODO: implement risk level logic
    return "unknown"


def generate_report_markdown(project, metrics, schedule_info, report_date):
    """Generate markdown report string for a single project."""
    # TODO: implement report generation
    return ""


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    projects = load_projects()
    schedule = load_schedule()

    for project in projects:
        exec_id = project["id"]
        metrics = calculate_metrics(project, CURRENT_DATE)
        schedule_info = schedule.get(exec_id, {})
        report = generate_report_markdown(project, metrics, schedule_info, CURRENT_DATE)

        output_path = os.path.join(OUTPUT_DIR, f"report_{exec_id}.md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Generated: {output_path}")


if __name__ == "__main__":
    main()
