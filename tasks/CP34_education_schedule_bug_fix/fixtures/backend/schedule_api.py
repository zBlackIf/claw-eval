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
    # BUG: Returns raw dict instead of serializable format with 'value'/'label' keys
    # Frontend expects: [{"value": id, "label": name}, ...]
    return _teachers


def get_classrooms():
    """Return list of classrooms for dropdown."""
    # Same bug as get_teachers
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
    """Create a schedule entry, optionally repeating for multiple weeks.

    Args:
        course_id: ID of the course
        teacher_id: ID of the teacher
        classroom_id: ID of the classroom
        day_of_week: Day name (e.g., "Tuesday")
        start_time: Start time (e.g., "09:00")
        end_time: End time (e.g., "10:30")
        repeat_weeks: Number of weeks to repeat (1 = no repeat)

    Returns:
        dict with created schedule entries
    """
    created = []
    base_date = _get_next_weekday(day_of_week)

    for week in range(repeat_weeks):
        schedule_date = base_date + timedelta(weeks=week)
        # BUG: When repeat_weeks > 1, the day shifts by +1 because
        # _get_next_weekday already returns next occurrence, and adding
        # timedelta(weeks=week) when week=0 is correct, but the _get_next_weekday
        # function itself has the off-by-one from DAY_MAP
        entry = {
            "id": len(_schedules) + 1,
            "course_id": course_id,
            "teacher_id": teacher_id,
            "classroom_id": classroom_id,
            "day_of_week": day_of_week,
            "date": schedule_date.strftime("%Y-%m-%d"),
            "start_time": start_time,
            "end_time": end_time,
            # BUG: Only stores IDs, not names - frontend needs names for display
            # without an extra lookup
        }
        _schedules.append(entry)
        created.append(entry)

    return {"status": "success", "created": created}


def get_schedule_display(schedule_id: int) -> Optional[dict]:
    """Get schedule entry with display information.

    BUG: Does not join course/teacher/classroom names into the response.
    Frontend has to make 3 extra API calls to display card content.
    """
    for s in _schedules:
        if s["id"] == schedule_id:
            return s
    return None


def _get_next_weekday(day_name: str) -> datetime:
    """Get the date of the next occurrence of the given weekday.

    BUG: Uses DAY_MAP which maps Monday=0, but Python's weekday()
    also uses Monday=0. The real bug is that the frontend sends
    day_of_week as 1-indexed (Monday=1, Tuesday=2, etc.) while
    this function treats it as 0-indexed via DAY_MAP.
    Result: Tuesday schedule ends up on Wednesday.
    """
    target_day = DAY_MAP.get(day_name, 0)
    today = datetime.now()
    days_ahead = target_day - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


def list_schedules():
    """Return all schedules."""
    return _schedules
