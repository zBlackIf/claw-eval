#!/usr/bin/env python3
"""In-container verifier for CP48_video_stream_download_optimization.

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

    video_loader = workspace / "video_loader.py"
    if not video_loader.exists():
        return {
            "stream_mode": 0.0,
            "early_stop": 0.0,
            "fallback": 0.0,
            "config_updated": 0.0,
            "interface_compat": 0.0,
        }

    content = video_loader.read_text()

    # Check streaming implementation
    stream_patterns = [
        r'\.stream\s*\(',
        r'aiter_bytes',
        r'aiter_raw',
        r'iter_bytes',
        r'iter_raw',
        r'async\s+for\s+\w+\s+in\s+\w+',
    ]
    has_stream = any(re.search(p, content) for p in stream_patterns)
    scores["stream_mode"] = 1.0 if has_stream else 0.0

    # Check early termination logic
    early_stop_patterns = [
        r'MAX_FRAMES|max_frames',
        r'(break|return|stop).*frame',
        r'frame.*>.*\d+.*break',
        r'extracted.*>=',
        r'enough.*frame',
    ]
    has_early_stop = sum(
        1 for p in early_stop_patterns if re.search(p, content, re.IGNORECASE)
    )
    scores["early_stop"] = min(has_early_stop / 2.0, 1.0)

    # Check fallback mechanism
    fallback_patterns = [
        r'except.*:.*\n.*(?:fall|download|_download)',
        r'fallback',
        r'try.*stream.*except',
        r'except.*(?:httpx|HTTP|Error)',
    ]
    has_fallback = any(
        re.search(p, content, re.DOTALL | re.IGNORECASE)
        for p in fallback_patterns
    )
    scores["fallback"] = 1.0 if has_fallback else 0.0

    # Check config updates
    config_file = workspace / "config.py"
    if config_file.exists():
        config_content = config_file.read_text()
        has_stream_config = any(k in config_content.upper() for k in [
            "STREAM", "CHUNK_SIZE", "CHECK_INTERVAL", "FRAME_CHECK"
        ])
        scores["config_updated"] = 1.0 if has_stream_config else 0.0
    else:
        scores["config_updated"] = 0.0

    # Check interface compatibility (load_video signature preserved)
    has_load_video = bool(re.search(
        r'async\s+def\s+load_video\s*\(\s*self\s*,\s*file_id',
        content
    ))
    has_return_tuple = bool(re.search(
        r'Tuple\[Optional\[str\],\s*int,\s*str\]', content
    ))
    scores["interface_compat"] = (
        0.5 * (1.0 if has_load_video else 0.0)
        + 0.5 * (1.0 if has_return_tuple else 0.0)
    )

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
