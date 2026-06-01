#!/usr/bin/env python3
"""In-container verifier for CP34_education_schedule_bug_fix.

Ports the original automated_score() to a script that runs under
env_snapshot_commands. Emits one JSON line with per-component scores plus
overall_score = mean(components).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

WORKSPACE = Path("/workspace")


def automated_score(workspace: Path) -> dict[str, float]:
    scores = {}

    backend = workspace / "backend" / "schedule_api.py"
    frontend = workspace / "frontend" / "ScheduleView.vue"

    be_text = backend.read_text(encoding="utf-8", errors="ignore") if backend.exists() else ""
    fe_text = frontend.read_text(encoding="utf-8", errors="ignore") if frontend.exists() else ""

    # Bug 1: Day-of-week off-by-one fixed
    original_map = '"Monday": 0' in be_text or "'Monday': 0" in be_text
    has_conversion = bool(re.search(r"target_day\s*[-+]\s*1|day.*-\s*1|index.*-\s*1|weekday\(\)\s*\+\s*1|frontend.*1", be_text, re.IGNORECASE))
    map_changed = bool(re.search(r"['\"]Monday['\"]\s*:\s*1", be_text))
    scores["day_off_by_one_fixed"] = (
        1.0 if (has_conversion or map_changed or not original_map) else 0.0
    )

    # Bug 2: Dropdown binding fixed
    has_object_binding = bool(re.search(r':value=["\']\s*[tr]\s*["\']', fe_text))
    teacher_id_binding = bool(re.search(r':value=["\']\s*(t\.id|t\.value|teacher\.id|teacher\.value)\s*["\']', fe_text))
    room_id_binding = bool(re.search(r':value=["\']\s*(r\.id|r\.value|room\.id|room\.value|classroom\.id|classroom\.value)\s*["\']', fe_text))
    has_id_binding = teacher_id_binding and room_id_binding
    scores["dropdown_binding_fixed"] = (
        1.0 if has_id_binding and not has_object_binding else 0.0
    )

    # Bug 3: API returns names or frontend does lookup
    has_name_join = bool(re.search(r"course_name|teacher_name|classroom_name|course.*name|teacher.*name|classroom.*name", be_text, re.IGNORECASE))
    has_fe_lookup = bool(re.search(
        r"find\(.*course.*id|courses\.find|teachers\.find|classrooms\.find|lookup.*name|get.*Name|map.*course|map.*teacher|map.*classroom", fe_text,
        re.IGNORECASE,
    ))
    has_refetch = bool(re.search(r"loadData\(\)", fe_text.split("createSchedule")[1])) if "createSchedule" in fe_text else False
    scores["card_display_fixed"] = (
        1.0 if (has_name_join or has_fe_lookup or has_refetch) else 0.0
    )

    # Bug 4: Card min-width CSS
    has_min_width = bool(re.search(r"min-width\s*:", fe_text))
    has_grid_width = bool(re.search(r"(table-layout\s*:\s*fixed|grid-template-columns|minmax\()", fe_text, re.IGNORECASE))
    has_nowrap = bool(re.search(r"(white-space\s*:\s*nowrap|overflow\s*:\s*hidden|text-overflow)", fe_text, re.IGNORECASE))
    scores["card_min_width_added"] = 1.0 if (has_min_width or has_grid_width or has_nowrap) else 0.0

    return scores


def main() -> dict:
    try:
        scores = automated_score(WORKSPACE)
    except Exception as exc:  # noqa: BLE001
        return {"scores": {}, "overall_score": 0.0, "error": f"{type(exc).__name__}: {exc}"}
    numeric = [float(v) for v in scores.values() if isinstance(v, (int, float))]
    overall = sum(numeric) / len(numeric) if numeric else 0.0
    return {"scores": scores, "overall_score": round(overall, 4)}


if __name__ == "__main__":
    sys.stdout.write(json.dumps(main(), ensure_ascii=False) + "\n")
