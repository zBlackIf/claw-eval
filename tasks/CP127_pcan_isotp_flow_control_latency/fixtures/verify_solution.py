"""Hidden verifier for CP127 — PCAN ISO-TP Flow Control Latency Optimization.

Checks that the agent has properly optimized the PCAN driver and ISO-TP layer
to minimize Flow Control response latency after receiving a First Frame.

Grading dimensions:
1. sleep_reduction: The 100ms sleep in _loop() is reduced to <=5ms or eliminated
2. event_driven_or_fast_poll: Uses event-driven reception OR tight polling (<2ms)
3. display_incremental: GUI display_messages() uses incremental update (no full rebuild)
4. fc_fast_path: Flow Control is sent quickly (ideally from driver thread or with minimal delay)
5. thread_priority: Thread priority is elevated OR other latency-reduction technique applied
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_file(ws: Path, filename: str) -> Path | None:
    """Search workspace for a file by name."""
    for p in ws.rglob(filename):
        return p
    return None


def _check_sleep_reduction(pcan_src: str) -> float:
    """Check that the 100ms sleep in the reception loop is reduced or removed."""
    # Look for sleep calls in the code
    sleep_calls = re.findall(r'time\.sleep\(([\d.]+)\)', pcan_src)
    sleep_calls_win = re.findall(r'Sleep\((\d+)\)', pcan_src)

    # Original has time.sleep(0.1) in the polling loop
    has_100ms_sleep = any(float(s) >= 0.05 for s in sleep_calls)

    if has_100ms_sleep:
        return 0.0

    # Check if sleep is reduced to small value
    has_small_sleep = any(0 < float(s) <= 0.005 for s in sleep_calls)
    has_win_small_sleep = any(0 < int(s) <= 5 for s in sleep_calls_win)
    has_no_sleep_in_loop = not any(float(s) > 0 for s in sleep_calls)
    has_spin_or_event = ("WaitForSingleObject" in pcan_src or
                         "Event()" in pcan_src or
                         "spin" in pcan_src.lower() or
                         "busy" in pcan_src.lower() or
                         "sleep(0)" in pcan_src)

    if has_no_sleep_in_loop or has_spin_or_event:
        return 1.0
    elif has_small_sleep or has_win_small_sleep:
        return 0.8
    else:
        return 0.5


def _check_event_driven(pcan_src: str) -> float:
    """Check if reception uses event-driven approach or fast polling."""
    score = 0.0

    # Event-driven indicators (must actually USE the API, not just define constants)
    if "WaitForSingleObject" in pcan_src:
        score += 0.5
    # Only count PCAN_RECEIVE_EVENT if it's actually passed to an API call
    if re.search(r'(GetValue|SetValue|WaitFor).*PCAN_RECEIVE_EVENT', pcan_src):
        score += 0.3
    elif "SetEvent" in pcan_src or "CreateEvent" in pcan_src:
        score += 0.3
    if "ResetEvent" in pcan_src:
        score += 0.2

    # Alternative: tight polling with yield
    if score == 0.0:
        # Check for very tight polling (sleep(0) or sleep(0.001))
        tight_sleep = re.findall(r'time\.sleep\((0(?:\.00[01])?\d*)\)', pcan_src)
        if tight_sleep and all(float(s) <= 0.002 for s in tight_sleep):
            score = 0.6
        # Or Windows Sleep(1)
        if re.search(r'Sleep\([01]\)', pcan_src):
            score = max(score, 0.6)
        # Or ctypes kernel32 sleep
        if "kernel32" in pcan_src and "Sleep" in pcan_src:
            score = max(score, 0.7)

    # timeBeginPeriod for timer resolution
    if "timeBeginPeriod" in pcan_src:
        score = min(1.0, score + 0.2)

    return min(1.0, score)


def _check_display_incremental(gui_src: str) -> float:
    """Check that display_messages() doesn't rebuild the entire table."""
    if not gui_src:
        return 0.0

    # The original has: self.message_table.setRowCount(0) followed by full rebuild
    # Check if the setRowCount(0) pattern is still there in display_messages

    # Find the display_messages function
    display_match = re.search(
        r'def _?display_messages?\(self[^)]*\).*?(?=\n    def |\nclass |\Z)',
        gui_src,
        re.DOTALL,
    )
    if not display_match:
        # Function might be renamed or removed; check for any incremental approach
        if "insertRow" in gui_src and "setRowCount(0)" not in gui_src:
            return 0.8
        return 0.3

    display_fn = display_match.group(0)

    # Check for problematic pattern: clear + full rebuild
    has_clear = "setRowCount(0)" in display_fn
    has_full_iter = "for row" in display_fn and "enumerate" in display_fn

    if has_clear and has_full_iter:
        return 0.0  # Still doing full rebuild

    # Check for incremental approach indicators
    incremental_indicators = 0
    if "insertRow" in display_fn:
        incremental_indicators += 1
    if "_display_index" in display_fn or "_last_row" in display_fn or "current_rows" in display_fn:
        incremental_indicators += 1
    if "rowCount()" in display_fn and "setRowCount(0)" not in display_fn:
        incremental_indicators += 1
    if "append" in display_fn.lower() or "only" in display_fn.lower():
        incremental_indicators += 1

    # scrollToBottom removed or made conditional
    scroll_removed = "scrollToBottom" not in display_fn

    score = min(1.0, incremental_indicators * 0.3 + (0.2 if scroll_removed else 0.0))
    return score


def _check_fc_fast_path(pcan_src: str, isotp_src: str) -> float:
    """Check if Flow Control frame is sent with minimal delay.

    Best: FC sent directly in the driver receive thread (bypasses GUI).
    Good: FC sent immediately in isotp process_can_message without going through queue.
    """
    score = 0.0

    # Check if pcan_driver has direct FC sending logic
    if "flow_control" in pcan_src.lower() or "send_fc" in pcan_src.lower() or "FC" in pcan_src:
        # Driver-level fast FC response
        has_ff_detect = ("0x1" in pcan_src and ">> 4" in pcan_src) or "FRAME_TYPE_FF" in pcan_src or "first_frame" in pcan_src.lower()
        has_fc_send = "send" in pcan_src.lower() and ("0x30" in pcan_src or "FC" in pcan_src or "flow" in pcan_src.lower())
        if has_ff_detect and has_fc_send:
            score = 1.0
        elif has_fc_send:
            score = 0.7

    # Check if isotp layer has optimized FC sending (only counts if ALSO moved to driver)
    # The baseline already has FC in isotp _handle_first_frame - that alone is not enough
    # because it still goes through the on_message callback chain (with 100ms sleep delay)
    if score < 0.3 and isotp_src:
        # Only give partial credit if isotp added explicit latency-aware improvements
        ff_handler = re.search(r'def _handle_first_frame.*?(?=\n    def |\Z)', isotp_src, re.DOTALL)
        if ff_handler:
            handler_code = ff_handler.group(0)
            # Only credit if there's evidence of optimization (not just baseline behavior)
            has_timing = "time" in handler_code.lower() or "perf_counter" in handler_code
            has_priority = "priority" in handler_code.lower() or "immediate" in handler_code.lower()
            if has_timing or has_priority:
                score = max(score, 0.3)

    # Check for flag to prevent duplicate FC (both driver and isotp sending)
    if "fc_sent" in pcan_src or "fc_sent" in isotp_src:
        score = min(1.0, score + 0.2)
    if "_fc_handled" in pcan_src or "_fc_handled" in isotp_src:
        score = min(1.0, score + 0.2)

    return score


def _check_thread_priority(pcan_src: str) -> float:
    """Check if thread priority optimization or other latency techniques are used."""
    score = 0.0

    # Windows thread priority
    if "SetThreadPriority" in pcan_src or "THREAD_PRIORITY" in pcan_src:
        score += 0.5
    if "TIME_CRITICAL" in pcan_src or "ABOVE_NORMAL" in pcan_src or "HIGHEST" in pcan_src:
        score += 0.3

    # Process priority
    if "SetPriorityClass" in pcan_src or "HIGH_PRIORITY_CLASS" in pcan_src:
        score += 0.2

    # timeBeginPeriod (Windows timer resolution)
    if "timeBeginPeriod" in pcan_src:
        score += 0.3

    # Thread affinity
    if "SetThreadAffinityMask" in pcan_src or "affinity" in pcan_src.lower():
        score += 0.2

    # GIL release techniques
    if "nogil" in pcan_src or "release_gil" in pcan_src.lower():
        score += 0.2

    return min(1.0, score)


def grade_workspace(ws: Path) -> dict:
    """Grade the optimized workspace."""
    # Find the key files
    pcan_file = _find_file(ws, "pcan_driver.py")
    isotp_file = _find_file(ws, "isotp.py")
    gui_file = _find_file(ws, "gui_app.py")

    pcan_src = _read(pcan_file) if pcan_file else ""
    isotp_src = _read(isotp_file) if isotp_file else ""
    gui_src = _read(gui_file) if gui_file else ""

    if not pcan_src:
        return {"overall_score": 0.0, "components": {}, "error": "pcan_driver.py not found"}

    components = {
        "sleep_reduction": _check_sleep_reduction(pcan_src),
        "event_driven_or_fast_poll": _check_event_driven(pcan_src),
        "display_incremental": _check_display_incremental(gui_src),
        "fc_fast_path": _check_fc_fast_path(pcan_src, isotp_src),
        "thread_priority": _check_thread_priority(pcan_src),
    }

    weights = {
        "sleep_reduction": 0.30,
        "event_driven_or_fast_poll": 0.25,
        "display_incremental": 0.15,
        "fc_fast_path": 0.20,
        "thread_priority": 0.10,
    }

    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    # Try both possible locations
    ws = Path("/workspace/fixtures/pcan_testtool")
    if not ws.exists():
        ws = Path("/workspace/pcan_testtool")
    if not ws.exists():
        # Fallback: search for pcan_driver.py anywhere in workspace
        workspace_root = Path("/workspace")
        pcan_file = _find_file(workspace_root, "pcan_driver.py")
        if pcan_file:
            ws = pcan_file.parent.parent  # Go up from src/pcan_driver.py
        else:
            ws = workspace_root

    result = grade_workspace(ws)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
