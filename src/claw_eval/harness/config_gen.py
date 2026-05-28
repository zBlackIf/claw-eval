"""Temporary MCP config generation for external Claw-Eval harnesses."""

from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any


def mcp_server_args(
    *,
    task_yaml: Path,
    trace_id: str,
    dispatch_log: Path,
    sandbox_url: str | None,
    port_offset: int,
) -> list[str]:
    args = [
        "-m",
        "claw_eval.harness.mcp_server",
        "--task",
        str(task_yaml.resolve()),
        "--trace-id",
        trace_id,
        "--dispatch-log",
        str(dispatch_log.resolve()),
    ]
    if sandbox_url:
        args.extend(["--sandbox-url", sandbox_url])
    if port_offset:
        args.extend(["--port-offset", str(port_offset)])
    return args


def write_claude_mcp_config(
    *,
    path: Path,
    python: str,
    server_args: list[str],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "mcpServers": {
            "claw-eval": {
                "command": python,
                "args": server_args,
            }
        }
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def codex_mcp_config_overrides(*, python: str, server_args: list[str]) -> list[str]:
    quoted_args = "[" + ",".join(json.dumps(arg) for arg in server_args) + "]"
    return [
        "mcp_servers.claw-eval.enabled=true",
        'mcp_servers.claw-eval.default_tools_approval_mode="approve"',
        "mcp_servers.claw-eval.startup_timeout_sec=20",
        "mcp_servers.claw-eval.tool_timeout_sec=180",
        f"mcp_servers.claw-eval.command={json.dumps(python)}",
        f"mcp_servers.claw-eval.args={quoted_args}",
    ]


def shell_join(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)
