#!/usr/bin/env python3
"""In-container verifier for CP50_tester_ops_debug_blocks.

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

    # Check if agent verified all three prerequisite files
    prefs = workspace / "memory" / "user_preferences.md"
    todo = workspace / "workspace" / "TODO.md"
    todolist = workspace / "workspace" / "projectTest" / "todolist.md"

    files_exist = all(f.exists() for f in [prefs, todo, todolist])
    scores["prerequisite_files_checked"] = 1.0 if files_exist else 0.0

    # Check if todolist was updated (Phase 3 marked complete)
    if todolist.exists():
        content = todolist.read_text()

        # Check if Phase 3 is now marked as complete
        phase3_complete = bool(re.search(
            r'\[x\]\s*Phase\s*3', content, re.IGNORECASE
        ))
        scores["phase3_executed"] = 1.0 if phase3_complete else 0.0

        # Check that phases 0-2 are still marked complete (not reset)
        phase0_ok = bool(re.search(r'\[x\]\s*Phase\s*0', content, re.IGNORECASE))
        phase1_ok = bool(re.search(r'\[x\]\s*Phase\s*1', content, re.IGNORECASE))
        phase2_ok = bool(re.search(r'\[x\]\s*Phase\s*2', content, re.IGNORECASE))
        scores["previous_phases_preserved"] = (
            1.0 if all([phase0_ok, phase1_ok, phase2_ok]) else 0.0
        )

        # Phase 4+ may be completed after Phase 3. Penalize only impossible skips:
        # a later phase marked done while Phase 3 is still incomplete.
        later_done = bool(re.search(r'\[x\]\s*Phase\s*[4-7]', content, re.IGNORECASE))
        impossible_skip = later_done and not phase3_complete
        scores["no_phase_skipping"] = 0.0 if impossible_skip else 1.0
    else:
        scores["phase3_executed"] = 0.0
        scores["previous_phases_preserved"] = 0.0
        scores["no_phase_skipping"] = 0.0

    # Check if test plan deliverable was created
    test_plan_candidates = [
        workspace / "workspace" / "projectTest" / "test_plan.md",
        workspace / "workspace" / "projectTest" / "phase3_test_plan.md",
        workspace / "workspace" / "projectTest" / "测试计划.md",
    ]
    plan_exists = any(f.exists() for f in test_plan_candidates)

    # Also check if plan content was appended to todolist
    plan_in_todolist = False
    if todolist.exists():
        content = todolist.read_text()
        plan_keywords = ["5w1h", "what", "when", "where", "who", "how",
                       "测试范围", "测试目标", "test scope", "test plan"]
        plan_in_todolist = any(k in content.lower() for k in plan_keywords)

    scores["test_plan_created"] = 1.0 if (plan_exists or plan_in_todolist) else 0.0

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
