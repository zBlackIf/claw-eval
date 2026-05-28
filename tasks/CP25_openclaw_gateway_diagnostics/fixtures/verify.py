#!/usr/bin/env python3
"""In-container verifier for CP25_openclaw_gateway_diagnostics.

Ports the original automated_score() to a script that runs under
env_snapshot_commands. Emits one JSON line with per-component scores plus
overall_score = mean(components).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path("/workspace")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def _first_existing(*paths: Path) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def _bash_syntax_ok(path: Path | None) -> bool:
    if path is None:
        return False
    try:
        proc = subprocess.run(
            ["bash", "-n", str(path)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return proc.returncode == 0
    except Exception:
        return False


def automated_score(workspace: Path) -> dict[str, float]:
    scores = {}

    # 1. Diagnosis report
    report = workspace / "diagnosis_report.md"
    if report.exists():
        content = _read(report).lower()
        scores["diagnosis_report_present"] = 1.0
        scores["identifies_eaddrinuse"] = 1.0 if "eaddrinuse" in content or "address already in use" in content else 0.0
        scores["identifies_security_risk"] = 1.0 if ("0.0.0.0" in content and ("security" in content or "安全" in content or "risk" in content or "风险" in content)) else 0.0
        chain_hits = sum(1 for k in ["warn", "error", "fatal", "econnrefused", "因果", "chain"] if k in content)
        scores["error_chain_analysis"] = min(chain_hits / 4.0, 1.0)
    else:
        scores["diagnosis_report_present"] = 0.0
        scores["identifies_eaddrinuse"] = 0.0
        scores["identifies_security_risk"] = 0.0
        scores["error_chain_analysis"] = 0.0

    # 2. Gateway config modification
    config = workspace / "config" / "gateway.yaml"
    if config.exists():
        content = _read(config)
        scores["config_present"] = 1.0
        scores["localhost_binding"] = 1.0 if "127.0.0.1" in content or "localhost" in content else 0.0
        scores["no_wildcard_bind"] = 0.0 if "0.0.0.0" in content else 1.0
    else:
        scores["config_present"] = 0.0
        scores["localhost_binding"] = 0.0
        scores["no_wildcard_bind"] = 0.0

    # 3. Restart script. Accept the prompt's restart_gateway.sh and the older
    # scripts/safe_restart.sh name to avoid prompt-rubric contract mismatch.
    script = _first_existing(
        workspace / "restart_gateway.sh",
        workspace / "scripts" / "safe_restart.sh",
        workspace / "scripts" / "restart_gateway.sh",
    )
    if script is not None and script.exists():
        content = _read(script)
        scores["restart_script_present"] = 1.0
        scores["checks_port"] = 1.0 if any(k in content for k in ["lsof", "ss ", "netstat", "fuser"]) else 0.0
        scores["has_health_check"] = 1.0 if any(k in content for k in ["curl", "wget", "health", "nc "]) else 0.0
        scores["has_rollback"] = 1.0 if any(k in content for k in ["rollback", "backup", "restore", "cp "]) else 0.0
        scores["restart_script_syntax"] = 1.0 if _bash_syntax_ok(script) else 0.0
    else:
        scores["restart_script_present"] = 0.0
        scores["checks_port"] = 0.0
        scores["has_health_check"] = 0.0
        scores["has_rollback"] = 0.0
        scores["restart_script_syntax"] = 0.0

    # 4. Health-check script was explicitly requested in the prompt.
    health_script = _first_existing(
        workspace / "health_check.sh",
        workspace / "scripts" / "health_check.sh",
    )
    if health_script:
        content = _read(health_script).lower()
        scores["health_script_present"] = 1.0
        scores["health_checks_process"] = 1.0 if any(k in content for k in ["pgrep", "ps ", "systemctl", "process", "进程"]) else 0.0
        scores["health_checks_port"] = 1.0 if any(k in content for k in ["18789", "lsof", "ss ", "netstat", "nc "]) else 0.0
        scores["health_checks_local_bind"] = 1.0 if ("127.0.0.1" in content and "0.0.0.0" in content) else 0.0
        scores["health_checks_models"] = min(sum(1 for p in ["8081", "8082", "8083"] if p in content) / 3.0, 1.0)
        scores["health_script_syntax"] = 1.0 if _bash_syntax_ok(health_script) else 0.0
    else:
        scores["health_script_present"] = 0.0
        scores["health_checks_process"] = 0.0
        scores["health_checks_port"] = 0.0
        scores["health_checks_local_bind"] = 0.0
        scores["health_checks_models"] = 0.0
        scores["health_script_syntax"] = 0.0

    # Optional operational alerting can add confidence, but missing alerts no
    # longer block success because the prompt did not request alerts.yaml.
    alerts = workspace / "config" / "alerts.yaml"
    if alerts.exists():
        content = _read(alerts).lower()
        scores["optional_alerts"] = 1.0 if (("port" in content or "端口" in content) and ("process" in content or "进程" in content)) else 0.5
    else:
        scores["optional_alerts"] = 1.0

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
