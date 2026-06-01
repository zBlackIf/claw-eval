#!/usr/bin/env python3
"""In-container verifier for CP35_industrial_sdk_data_components.

Ports the original automated_score() to a script that runs under
env_snapshot_commands. Emits one JSON line with per-component scores plus
overall_score = mean(components).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path("/workspace")


def automated_score(workspace: Path) -> dict[str, float]:
    scores = {}

    # Check CircularBuffer
    buffer_files = list(workspace.rglob("CircularBuffer.cs")) + list(workspace.rglob("*circular*buffer*.cs"))
    if buffer_files:
        content = buffer_files[0].read_text(encoding="utf-8", errors="ignore")
        scores["buffer_created"] = 1.0
        has_generic = "CircularBuffer<T>" in content or "CircularBuffer<" in content
        has_thread_safe = "SemaphoreSlim" in content or "lock" in content or "Monitor" in content
        has_methods = all(m in content for m in ["Write", "Read", "Count", "Capacity"])
        has_wraparound = any(k in content for k in ["% Capacity", "% _capacity", "head", "tail", "_head", "_tail"])
        scores["buffer_quality"] = (
            1.0 if (has_generic and has_thread_safe and has_methods and has_wraparound)
            else (0.5 if has_generic else 0.0)
        )
    else:
        scores["buffer_created"] = 0.0
        scores["buffer_quality"] = 0.0

    # Check AlarmManager
    alarm_files = list(workspace.rglob("AlarmManager.cs")) + list(workspace.rglob("*alarm*.cs"))
    if alarm_files:
        content = alarm_files[0].read_text(encoding="utf-8", errors="ignore")
        scores["alarm_created"] = 1.0
        has_severity = "AlarmSeverity" in content or "Severity" in content
        has_event = "event" in content or "Event" in content
        has_methods = "RaiseAlarm" in content and "AcknowledgeAlarm" in content
        has_state = any(k in content for k in ["Active", "Acknowledged", "Cleared", "Timestamp"])
        scores["alarm_quality"] = (
            1.0 if (has_severity and has_event and has_methods and has_state)
            else (0.5 if has_severity else 0.0)
        )
    else:
        scores["alarm_created"] = 0.0
        scores["alarm_quality"] = 0.0

    # Check LogLevel
    log_files = list(workspace.rglob("LogLevel.cs")) + list(workspace.rglob("*log*level*.cs"))
    if log_files:
        content = log_files[0].read_text(encoding="utf-8", errors="ignore")
        scores["log_created"] = 1.0
        has_enum = "enum LogLevel" in content or "enum" in content
        has_extension = "Extensions" in content or "static" in content
        has_values = sum(1 for v in ["Trace", "Debug", "Info", "Warning", "Error", "Critical"] if v in content)
        scores["log_quality"] = 1.0 if (has_enum and has_extension and has_values >= 4) else (0.5 if has_enum else 0.0)
    else:
        scores["log_created"] = 0.0
        scores["log_quality"] = 0.0

    # Namespace consistency
    all_cs = list(workspace.rglob("*.cs"))
    ns_correct = sum(
        1 for f in all_cs
        if "MinqiaIndustrialComponentLibrary" in f.read_text(encoding="utf-8", errors="ignore")
    )
    scores["namespace_consistent"] = 1.0 if ns_correct >= 3 else (0.5 if ns_correct >= 1 else 0.0)
    if shutil.which("dotnet") and (workspace / "MinqiaIndustrialComponentLibrary.csproj").exists():
        try:
            proc = subprocess.run(
                ["dotnet", "build", "--nologo"],
                cwd=str(workspace),
                capture_output=True,
                text=True,
                timeout=30,
            )
            scores["dotnet_build"] = 1.0 if proc.returncode == 0 else 0.0
        except Exception:
            scores["dotnet_build"] = 0.0
    else:
        scores["dotnet_build"] = scores["namespace_consistent"]

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
