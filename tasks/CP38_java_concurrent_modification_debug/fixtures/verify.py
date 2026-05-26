#!/usr/bin/env python3
"""In-container verifier for CP38_java_concurrent_modification_debug.

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

THREAD_SAFE_PATTERNS = [
        "CopyOnWriteArrayList",
        "Collections.unmodifiableList",
        "Collections.synchronizedList",
        "synchronized",
        "toArray(",
        ".stream()",
        "List.copyOf",
        "ImmutableList",
        "ReentrantReadWriteLock",
        "volatile",
    ]


def automated_score(workspace: Path) -> dict[str, float]:
    scores = {}

    req_util = workspace / "src" / "main" / "java" / "cn" / "dreamit" / "p1000" / "util" / "RequestUtil.java"
    if req_util.exists():
        content = req_util.read_text()
        scores["fix_file_present"] = 1.0

        has_thread_safe = any(k in content for k in THREAD_SAFE_PATTERNS)
        scores["thread_safety_applied"] = 1.0 if has_thread_safe else 0.0

        suppresses = bool(re.search(r"catch\s*\(\s*ConcurrentModificationException", content))
        scores["no_exception_suppression"] = 0.0 if suppresses else 1.0
    else:
        scores["fix_file_present"] = 0.0
        scores["thread_safety_applied"] = 0.0
        scores["no_exception_suppression"] = 1.0

    diag = workspace / "diagnosis.md"
    if diag.exists():
        dc = diag.read_text().lower()
        scores["diagnosis_exists"] = 1.0

        has_shared_state = any(k in dc for k in ["shared", "static", "mutable", "共享"])
        has_concurrent = any(k in dc for k in [
            "concurrent", "thread", "race condition", "iterator",
            "fail-fast", "并发", "线程"
        ])
        has_arraylist = "arraylist" in dc
        scores["root_cause_identified"] = (
            sum([has_shared_state, has_concurrent, has_arraylist]) / 3.0
        )
    else:
        scores["diagnosis_exists"] = 0.0
        scores["root_cause_identified"] = 0.0

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
