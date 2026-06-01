"""Hidden verifier for CP113 — Agent Notification Log Processor."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from datetime import datetime, timedelta


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _load_json(p: Path) -> dict | list | None:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def grade_workspace(ws: Path) -> dict:
    """Grade the notification processor output."""
    base = ws / "project-notifications"
    # Fallback paths
    if not base.exists():
        base = ws / "fixtures" / "project-notifications"

    components = {k: 0.0 for k in [
        "processor_implemented",
        "daily_log_generated",
        "summary_json_generated",
        "throttling_correctness",
        "escalation_detection",
        "patrol_dedup",
        "dedup_count_accuracy",
        "resolution_timeline",
        "max_entries_enforcement",
        "feedback_attribution",
        "blocker_duration_calc",
    ]}

    # --- 1. Check processor.py is properly implemented (not just the stub) ---
    processor_file = base / "processor.py"
    if not processor_file.exists():
        for p in ws.rglob("processor.py"):
            processor_file = p
            break

    if processor_file.exists():
        code = _read(processor_file)
        logic_lines = [l for l in code.splitlines()
                       if l.strip() and not l.strip().startswith(('#', 'import ', 'from ', '"""', "'''"))
                       and l.strip() not in ('pass', 'def main():', 'if __name__ == "__main__":', 'main()')]
        has_real_logic = len(logic_lines) > 15

        if not has_real_logic:
            components["processor_implemented"] = 0.0
        else:
            has_json_load = "json.load" in code or "json.loads" in code
            has_file_read = "open(" in code or "read_text" in code
            has_output_write = (".write(" in code or "write_text" in code) and "output" in code.lower()
            has_datetime = "timedelta" in code or "fromisoformat" in code or "strptime" in code
            has_logic = len(code) > 800

            score = 0.0
            if has_json_load:
                score += 0.25
            if has_file_read:
                score += 0.20
            if has_output_write:
                score += 0.25
            if has_datetime:
                score += 0.15
            if has_logic:
                score += 0.15
            components["processor_implemented"] = min(1.0, score)

    # --- 2. Check daily_log.md was generated ---
    log_file = None
    for candidate in [
        base / "output" / "daily_log.md",
        base / "daily_log.md",
        ws / "output" / "daily_log.md",
        ws / "daily_log.md",
    ]:
        if candidate.exists():
            log_file = candidate
            break
    if not log_file:
        for p in ws.rglob("daily_log.md"):
            log_file = p
            break

    if log_file:
        content = _read(log_file)
        has_heading = "#" in content
        has_timestamp = "04:" in content or "05:" in content or "06:" in content or "07:" in content
        has_task_ref = "task-11" in content or "task-8" in content or "task-15" in content
        has_member_names = any(n in content for n in ["baiyuekui", "lancer", "rider", "archer"])
        has_escalation_section = any(k in content.lower() for k in ["escalat", "block", "阻塞", "升级", "priority", "优先"])
        has_structure = content.count("#") >= 3 or content.count("##") >= 2

        score = 0.0
        if has_heading:
            score += 0.15
        if has_timestamp:
            score += 0.15
        if has_task_ref:
            score += 0.20
        if has_member_names:
            score += 0.15
        if has_escalation_section:
            score += 0.20
        if has_structure:
            score += 0.15
        components["daily_log_generated"] = min(1.0, score)

    # --- 3. Check summary.json was generated ---
    summary_file = None
    for candidate in [
        base / "output" / "summary.json",
        base / "summary.json",
        ws / "output" / "summary.json",
        ws / "summary.json",
    ]:
        if candidate.exists():
            summary_file = candidate
            break
    if not summary_file:
        for p in ws.rglob("summary.json"):
            summary_file = p
            break

    if summary_file:
        summary = _load_json(summary_file)
        if isinstance(summary, dict):
            has_blockers = any(k in summary for k in ["blockers", "escalations", "blocked_tasks", "blocking"])
            has_throttled = any(k in summary for k in ["throttled", "deduplicated", "suppressed", "dedup"])
            has_priority = any(k in summary for k in ["priority", "action_items", "decisions", "actions", "attention"])

            score = 0.0
            if has_blockers:
                score += 0.35
            if has_throttled:
                score += 0.35
            if has_priority:
                score += 0.30
            components["summary_json_generated"] = min(1.0, score)

    # --- 4. Throttling correctness (HIDDEN/HARD) ---
    # Input data analysis:
    # task-11 system_timeout events at: 04:01, 04:28, 04:39, 05:01, 06:05, 07:30
    #   Plus task-8 system_timeout at 05:30
    # With 30-min dedup window per task_id:
    #   task-11: 04:01 (keep), 04:28 within 30min of 04:01 (drop),
    #            04:39 within 30min of 04:01 (drop),
    #            05:01 is 60min after 04:01 (keep), 06:05 is 64min after 05:01 (keep),
    #            07:30 is 85min after 06:05 (keep)
    #   So task-11 should have 4 kept, 3 dropped (using sliding window from last kept)
    #   OR with strict 30-min windows: 04:01(keep), 04:28(drop, <30 from 04:01),
    #     04:39(drop, <30 from 04:01), 05:01(keep, >30 from 04:01),
    #     06:05(keep, >30 from 05:01), 07:30(keep, >30 from 06:05) = 4 kept, 3 dropped
    #   task-8: only 1 timeout, nothing to dedup
    #
    # A correct implementation drops exactly 3 task-11 timeouts.
    # Weak models often get this wrong (keep all 7, or miscalculate windows).
    if summary_file:
        summary = _load_json(summary_file)
        if isinstance(summary, dict):
            throttled = summary.get("throttled", summary.get("deduplicated", summary.get("suppressed", [])))
            score = 0.0
            if isinstance(throttled, list):
                # Check if task-11 throttled entry shows correct counts
                for entry in throttled:
                    if isinstance(entry, dict):
                        tid = entry.get("task_id", entry.get("id", ""))
                        if "task-11" in str(tid) or "11" in str(tid):
                            orig = entry.get("original_count", entry.get("total", entry.get("count", 0)))
                            kept = entry.get("kept_count", entry.get("kept", entry.get("after", 0)))
                            dropped = entry.get("dropped_count", entry.get("dropped", entry.get("suppressed", 0)))
                            # Correct: original=7, kept=4, dropped=3
                            # Accept slight variations (kept=3 or 4, dropped=3 or 4)
                            if isinstance(orig, int) and orig == 7:
                                score += 0.25
                            if isinstance(kept, int) and kept in (3, 4):
                                score += 0.25
                            if isinstance(dropped, int) and dropped in (3, 4):
                                score += 0.25
                            # At least has numeric data about dedup
                            if any(isinstance(entry.get(k), int) for k in
                                   ["original_count", "kept_count", "dropped_count",
                                    "total", "kept", "dropped", "count", "suppressed"]):
                                score += 0.15
                            break
                if score == 0.0 and len(throttled) > 0:
                    # Has throttled list but no numeric accuracy
                    score = 0.2
            elif isinstance(throttled, dict):
                # Alternative format: {task_id: {original: N, kept: M}}
                t11 = throttled.get("task-11", {})
                if isinstance(t11, dict):
                    orig = t11.get("original_count", t11.get("total", t11.get("count", 0)))
                    kept = t11.get("kept_count", t11.get("kept", 0))
                    dropped = t11.get("dropped_count", t11.get("dropped", 0))
                    if isinstance(orig, int) and orig == 7:
                        score += 0.25
                    if isinstance(kept, int) and kept in (3, 4):
                        score += 0.25
                    if isinstance(dropped, int) and dropped in (3, 4):
                        score += 0.25
                    if t11:
                        score += 0.15
            components["throttling_correctness"] = min(1.0, score)

    # Also verify via log: count task-11 system_timeout entries in daily_log
    if log_file and components["throttling_correctness"] < 0.5:
        content = _read(log_file)
        # Count lines that are specifically system_timeout events for task-11
        # Must match timeout EVENT lines, not feedback lines that happen to mention "超时"
        task11_timeout_lines = 0
        for line in content.splitlines():
            line_lower = line.lower()
            # Must be a timeout event line (contains system_timeout or is clearly a timeout entry)
            is_timeout_event = "system_timeout" in line_lower or (
                "timeout" in line_lower and "feedback" not in line_lower
            )
            # Also match Chinese timeout format but exclude feedback that mentions 超时
            if not is_timeout_event:
                is_timeout_event = (
                    "超时" in line and "member_feedback" not in line_lower
                    and "提醒" not in line and "收到" not in line
                )
            if is_timeout_event and ("task-11" in line_lower or "课程ppt" in line_lower):
                task11_timeout_lines += 1
        # Correct answer: 4 kept (or 3 with slightly different window interpretation)
        if task11_timeout_lines in (3, 4):
            components["throttling_correctness"] = max(components["throttling_correctness"], 0.7)
        elif task11_timeout_lines in (2, 5):
            components["throttling_correctness"] = max(components["throttling_correctness"], 0.4)

    # --- 5. Check escalation detection ---
    if log_file:
        content = _read(log_file)
        mentions_task15 = "task-15" in content or "视频录制" in content
        mentions_blocker = any(k in content.lower() for k in ["block", "阻塞", "escalat", "升级"])
        mentions_resolution = any(k in content.lower() for k in ["解除", "resolv", "完成", "修正", "unblock"])

        score = 0.0
        if mentions_task15:
            score += 0.35
        if mentions_blocker:
            score += 0.35
        if mentions_resolution:
            score += 0.30
        components["escalation_detection"] = min(1.0, score)

    if summary_file and components["escalation_detection"] < 1.0:
        summary = _load_json(summary_file)
        if isinstance(summary, dict):
            blockers = summary.get("blockers", summary.get("escalations", summary.get("blocked_tasks", [])))
            if isinstance(blockers, list):
                blocker_text = json.dumps(blockers)
                if "task-15" in blocker_text or "视频" in blocker_text or "rider" in blocker_text:
                    components["escalation_detection"] = max(components["escalation_detection"], 0.7)

    # --- 6. Patrol request dedup (HIDDEN/HARD) ---
    # project_config specifies patrol_min_interval_minutes: 20
    # There are 2 patrol_requests at 04:50 and 06:10 (80 min apart, both should be kept)
    # A truly correct implementation should ALSO apply patrol dedup rules.
    # Check: does the processor handle patrol_request type at all?
    # AND does the summary or log show awareness of patrol events?
    if processor_file.exists():
        code = _read(processor_file)
        has_patrol_handling = "patrol" in code.lower()
        has_patrol_interval = "patrol_min_interval" in code or ("patrol" in code.lower() and "20" in code)
        score = 0.0
        if has_patrol_handling:
            score += 0.4
        if has_patrol_interval:
            score += 0.3
        # Check if patrol events appear in log
        if log_file:
            log_content = _read(log_file)
            if "patrol" in log_content.lower() or "巡检" in log_content.lower() or "项目状态更新" in log_content:
                score += 0.3
        components["patrol_dedup"] = min(1.0, score)

    # --- 7. Dedup count accuracy in summary.json (HIDDEN/HARD) ---
    # Verify the summary.json has numerically accurate dedup statistics
    # Expected: task-11 had 7 timeouts, kept ~4, dropped ~3
    # Also: max_identical_log_entries config is 3 - this is an additional constraint
    # that limits any single task to at most 3 log entries of the same type
    if summary_file:
        summary = _load_json(summary_file)
        if isinstance(summary, dict):
            score = 0.0
            # Check action_items has correct prioritization
            actions = summary.get("action_items", summary.get("actions", summary.get("decisions", [])))
            if isinstance(actions, list) and len(actions) > 0:
                actions_text = json.dumps(actions, ensure_ascii=False).lower()
                # Should mention task-15 as highest priority (it was blocked)
                has_task15_priority = "task-15" in actions_text and any(
                    k in actions_text for k in ["high", "优先", "urgent", "critical", "阻塞", "block"]
                )
                # Should NOT list task-11 as blocker (it's just timeout, not blocked)
                task11_not_blocker = "task-11" not in actions_text or "block" not in actions_text.split("task-11")[0][-50:]
                if has_task15_priority:
                    score += 0.5
                if task11_not_blocker:
                    score += 0.2
            # Check blockers has resolution info
            blockers = summary.get("blockers", summary.get("escalations", []))
            if isinstance(blockers, list):
                for b in blockers:
                    if isinstance(b, dict) and "task-15" in str(b.get("task_id", "")):
                        has_resolved = b.get("resolved", b.get("is_resolved")) is True or \
                                       "resolved" in str(b).lower() or "解除" in str(b)
                        has_resolution_time = any(k in b for k in [
                            "resolution_time", "resolved_at", "unblocked_at",
                            "resolved_time", "end_time"
                        ])
                        if has_resolved:
                            score += 0.15
                        if has_resolution_time:
                            score += 0.15
                        break
            components["dedup_count_accuracy"] = min(1.0, score)

    # --- 8. Resolution timeline accuracy (HIDDEN/HARD) ---
    # task-15 timeline: escalation at 06:00, archer responds 06:15,
    # resolution at 06:45, rider confirms 07:00
    # A strong solution captures this full timeline with timestamps
    if log_file:
        content = _read(log_file)
        score = 0.0
        # Check for precise timeline markers
        has_escalation_time = "06:00" in content or "6:00" in content
        has_response_time = "06:15" in content or "6:15" in content
        has_resolution_time = "06:45" in content or "6:45" in content
        has_confirm_time = "07:00" in content or "7:00" in content

        # Need at least 3 of 4 timestamps for task-15 flow to show full timeline
        timeline_hits = sum([has_escalation_time, has_response_time,
                            has_resolution_time, has_confirm_time])
        if timeline_hits >= 4:
            score = 1.0
        elif timeline_hits == 3:
            score = 0.7
        elif timeline_hits == 2:
            score = 0.4
        elif timeline_hits == 1:
            score = 0.15
        components["resolution_timeline"] = score

    # --- 9. max_identical_log_entries enforcement (HIDDEN/HARD) ---
    # project_config.throttle_config.max_identical_log_entries = 3
    # After 30-min window dedup, task-11 still has 4 system_timeout events
    # (04:01, 05:01, 06:05, 07:30). The max_identical_log_entries=3 constraint
    # means only 3 of these should appear in the final daily_log.
    # Weak models ignore this second-layer constraint entirely.
    if log_file:
        content = _read(log_file)
        score = 0.0
        # Count how many task-11 system_timeout entries appear in the log
        task11_timeout_in_log = 0
        for line in content.splitlines():
            line_lower = line.lower()
            # Match timeout event lines for task-11 (not feedback lines)
            is_timeout_line = (
                ("system_timeout" in line_lower or "超时" in line_lower or "timeout" in line_lower)
                and "feedback" not in line_lower
                and "member_feedback" not in line_lower
                and "收到" not in line_lower
                and "提醒已收到" not in line_lower
            )
            if is_timeout_line and ("task-11" in line_lower or "课程ppt" in line_lower or "白月魁" in line_lower):
                task11_timeout_in_log += 1

        # Correct: exactly 3 (respecting max_identical_log_entries=3)
        # 4 means they did dedup but missed max_entries cap
        # 7 means no dedup at all
        if task11_timeout_in_log == 3:
            score = 1.0
        elif task11_timeout_in_log == 4:
            # Did dedup but missed max_entries — partial credit
            score = 0.35
        elif task11_timeout_in_log in (1, 2):
            # Over-filtered but at least tried
            score = 0.25
        elif task11_timeout_in_log >= 5:
            # Barely any dedup
            score = 0.05
        components["max_entries_enforcement"] = score

    # --- 10. Feedback attribution correctness (HIDDEN/HARD) ---
    # The log should attribute feedback to correct agents with substance.
    # Key: archer's feedback at 06:15 and 06:45 is about task-15, not task-11.
    # Weak models often conflate agents/tasks or omit feedback substance.
    if log_file:
        content = _read(log_file)
        score = 0.0
        content_lower = content.lower()

        # Check archer is associated with task-15 (not task-11)
        # Archer's only involvement is task-15 review
        archer_task15 = False
        for line in content.splitlines():
            ll = line.lower()
            if "archer" in ll and ("task-15" in ll or "视频" in ll or "脚本" in ll):
                archer_task15 = True
                break

        # Check rider is associated with task-15 escalation
        rider_task15 = False
        for line in content.splitlines():
            ll = line.lower()
            if "rider" in ll and ("task-15" in ll or "视频" in ll or "录制" in ll):
                rider_task15 = True
                break

        # Check lancer is associated with task-8 (not task-11 or task-15)
        lancer_task8 = False
        for line in content.splitlines():
            ll = line.lower()
            if "lancer" in ll and ("task-8" in ll or "校验" in ll or "资料" in ll):
                lancer_task8 = True
                break

        # Check that feedback substance is included (not just "received feedback")
        has_substance = any(k in content for k in [
            "100%", "就绪", "无阻塞", "修正完毕", "继续录制",
            "技术描述", "打包", "集成反馈",
        ])

        if archer_task15:
            score += 0.30
        if rider_task15:
            score += 0.25
        if lancer_task8:
            score += 0.20
        if has_substance:
            score += 0.25
        components["feedback_attribution"] = min(1.0, score)

    # --- 11. Blocker duration calculation (HIDDEN/HARD) ---
    # task-15 was blocked from 06:00 (escalation) to 06:45 (resolution) = 45 minutes.
    # A strong implementation calculates and reports this duration.
    # Check both daily_log and summary.json for duration mention.
    blocker_duration_score = 0.0
    duration_found = False

    if log_file:
        content = _read(log_file)
        # Look for "45" minutes mentioned near task-15/blocker context
        if "45" in content:
            # Verify it's in a blocking/resolution context
            for line in content.splitlines():
                if "45" in line and any(k in line.lower() for k in [
                    "分钟", "minute", "min", "duration", "耗时", "持续",
                    "阻塞", "block", "resolv", "解除",
                ]):
                    duration_found = True
                    break
            # Also check if 45 appears in a nearby context (within 3 lines of task-15)
            if not duration_found:
                lines = content.splitlines()
                for i, line in enumerate(lines):
                    if "task-15" in line.lower() or "视频录制" in line:
                        context = " ".join(lines[max(0,i-2):min(len(lines),i+3)])
                        if "45" in context:
                            duration_found = True
                            break

    if summary_file and not duration_found:
        summary = _load_json(summary_file)
        if isinstance(summary, dict):
            summary_str = json.dumps(summary, ensure_ascii=False)
            # Check for 45 minutes in blockers context
            if "45" in summary_str:
                # Verify it's associated with duration/resolution
                blockers = summary.get("blockers", summary.get("escalations", []))
                if isinstance(blockers, list):
                    for b in blockers:
                        b_str = json.dumps(b, ensure_ascii=False) if isinstance(b, dict) else str(b)
                        if "45" in b_str or "0:45" in b_str:
                            duration_found = True
                            break
                # Also check action_items
                if not duration_found:
                    actions = summary.get("action_items", summary.get("actions", []))
                    actions_str = json.dumps(actions, ensure_ascii=False) if isinstance(actions, list) else str(actions)
                    if "45" in actions_str and any(k in actions_str for k in ["task-15", "视频", "rider"]):
                        duration_found = True

    if duration_found:
        blocker_duration_score = 1.0
    else:
        # Partial credit: mentions both escalation time and resolution time
        # (shows awareness of timeline even without explicit duration)
        if log_file:
            content = _read(log_file)
            has_both_times = ("06:00" in content or "6:00" in content) and \
                            ("06:45" in content or "6:45" in content)
            if has_both_times:
                blocker_duration_score = 0.3
    components["blocker_duration_calc"] = blocker_duration_score

    # --- Weights: hard hidden checks get more weight ---
    weights = {
        "processor_implemented": 0.08,       # easy - reduced
        "daily_log_generated": 0.08,         # easy - reduced
        "summary_json_generated": 0.07,      # easy - reduced
        "throttling_correctness": 0.14,      # hard
        "escalation_detection": 0.06,        # easy - reduced
        "patrol_dedup": 0.07,                # medium
        "dedup_count_accuracy": 0.10,        # medium/hard
        "resolution_timeline": 0.05,         # medium
        "max_entries_enforcement": 0.14,     # HIDDEN/HARD - new
        "feedback_attribution": 0.09,        # HIDDEN/HARD - new
        "blocker_duration_calc": 0.12,       # HIDDEN/HARD - new
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    ws = Path("/workspace")
    if (ws / "fixtures" / "project-notifications").exists():
        pass  # grade_workspace handles both paths
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
