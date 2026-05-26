"""Schedule API - handles course scheduling for education management system.

Known issues reported by users:
- Repeated scheduling puts courses on wrong day (e.g., schedule for Tuesday but appears on Wednesday)
- Teacher/classroom dropdowns not selectable
- Schedule cards don't display course/teacher/classroom names after creation (only after refresh)
"""
import json
from datetime import datetime, timedelta
from typing import Optional

# Simulated database
_schedules = []
_teachers = [
    {"id": 1, "name": "Zhang Wei", "subject": "Mathematics"},
    {"id": 2, "name": "Li Na", "subject": "Physics"},
    {"id": 3, "name": "Wang Fang", "subject": "English"},
]
_classrooms = [
    {"id": 1, "name": "Room 101", "capacity": 40},
    {"id": 2, "name": "Room 202", "capacity": 30},
    {"id": 3, "name": "Lab A", "capacity": 25},
]
_courses = [
    {"id": 1, "name": "Advanced Math", "credits": 4},
    {"id": 2, "name": "General Physics", "credits": 3},
    {"id": 3, "name": "College English", "credits": 2},
]

# BUG: Day-of-week mapping is off-by-one (Monday=0 in Python but frontend sends Monday=1)
DAY_MAP = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}


def get_teachers():
    """Return list of teachers for dropdown."""
    return _teachers


def get_classrooms():
    """Return list of classrooms for dropdown."""
    return _classrooms


def create_schedule(
    course_id: int,
    teacher_id: int,
    classroom_id: int,
    day_of_week: str,
    start_time: str,
    end_time: str,
    repeat_weeks: int = 1,
) -> dict:
    """Create a schedule entry, optionally repeating for multiple weeks."""
    created = []
    base_date = _get_next_weekday(day_of_week)

    for week in range(repeat_weeks):
        schedule_date = base_date + timedelta(weeks=week)
        entry = {
            "id": len(_schedules) + 1,
            "course_id": course_id,
            "teacher_id": teacher_id,
            "classroom_id": classroom_id,
            "day_of_week": day_of_week,
            "date": schedule_date.strftime("%Y-%m-%d"),
            "start_time": start_time,
            "end_time": end_time,
        }
        _schedules.append(entry)
        created.append(entry)

    return {"status": "success", "created": created}


def _get_next_weekday(day_name: str) -> datetime:
    """Get the date of the next occurrence of the given weekday."""
    target_day = DAY_MAP.get(day_name, 0)
    today = datetime.now()
    days_ahead = target_day - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


def list_schedules():
    """Return all schedules."""
    return _schedules
