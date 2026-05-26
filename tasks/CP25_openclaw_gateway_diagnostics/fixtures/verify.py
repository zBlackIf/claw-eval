#!/usr/bin/env python3
"""In-container verifier for CP25_openclaw_gateway_diagnostics.

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

    # 1. Diagnosis report
    report = workspace / "diagnosis_report.md"
    if report.exists():
        content = report.read_text().lower()
        scores["diagnosis_report_present"] = 1.0
        scores["identifies_eaddrinuse"] = 1.0 if "eaddrinuse" in content or "address already in use" in content else 0.0
        scores["identifies_security_risk"] = 1.0 if ("0.0.0.0" in content and ("security" in content or "安全" in content or "risk" in content or "风险" in content)) else 0.0
        scores["error_chain_analysis"] = 1.0 if any(k in content for k in ["warn", "error", "fatal", "因果", "chain"]) else 0.0
    else:
        scores["diagnosis_report_present"] = 0.0
        scores["identifies_eaddrinuse"] = 0.0
        scores["identifies_security_risk"] = 0.0
        scores["error_chain_analysis"] = 0.0

    # 2. Gateway config modification
    config = workspace / "config" / "gateway.yaml"
    if config.exists():
        content = config.read_text()
        scores["config_present"] = 1.0
        scores["localhost_binding"] = 1.0 if "127.0.0.1" in content or "localhost" in content else 0.0
        scores["no_wildcard_bind"] = 0.0 if "0.0.0.0" in content else 1.0
    else:
        scores["config_present"] = 0.0
        scores["localhost_binding"] = 0.0
        scores["no_wildcard_bind"] = 0.0

    # 3. Restart script
    script = workspace / "scripts" / "safe_restart.sh"
    if script.exists():
        content = script.read_text()
        scores["restart_script_present"] = 1.0
        scores["checks_port"] = 1.0 if any(k in content for k in ["lsof", "ss ", "netstat", "fuser"]) else 0.0
        scores["has_health_check"] = 1.0 if any(k in content for k in ["curl", "wget", "health", "nc "]) else 0.0
        scores["has_rollback"] = 1.0 if any(k in content for k in ["rollback", "backup", "restore", "cp "]) else 0.0
    else:
        scores["restart_script_present"] = 0.0
        scores["checks_port"] = 0.0
        scores["has_health_check"] = 0.0
        scores["has_rollback"] = 0.0

    # 4. Alerts config
    alerts = workspace / "config" / "alerts.yaml"
    if alerts.exists():
        content = alerts.read_text().lower()
        scores["alerts_config_present"] = 1.0
        scores["port_alert"] = 1.0 if "port" in content or "端口" in content else 0.0
        scores["process_alert"] = 1.0 if "process" in content or "进程" in content else 0.0
    else:
        scores["alerts_config_present"] = 0.0
        scores["port_alert"] = 0.0
        scores["process_alert"] = 0.0

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
