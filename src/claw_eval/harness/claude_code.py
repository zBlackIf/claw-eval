"""Claude Code CLI runner for Claw-Eval external harness runs."""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class HarnessRunResult:
    harness: str
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    final_text: str
    wall_time_s: float
    input_tokens: int = 0
    output_tokens: int = 0


def _extract_text(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                if item.get("type") == "text" and isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif isinstance(item.get("content"), str):
                    parts.append(item["content"])
        return "\n".join(parts)
    if isinstance(value, dict):
        for key in ("result", "text", "content", "message"):
            text = _extract_text(value.get(key))
            if text:
                return text
    return ""


def _extract_final_text(stdout: str) -> tuple[str, int, int]:
    final_text = ""
    input_tokens = 0
    output_tokens = 0
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = _extract_text(event)
        if text:
            final_text = text
        usage = event.get("usage") if isinstance(event, dict) else None
        if isinstance(usage, dict):
            input_tokens += int(usage.get("input_tokens") or usage.get("input") or 0)
            output_tokens += int(usage.get("output_tokens") or usage.get("output") or 0)
    if not final_text:
        try:
            payload = json.loads(stdout)
            final_text = _extract_text(payload)
        except json.JSONDecodeError:
            final_text = stdout.strip()
    return final_text, input_tokens, output_tokens


def _to_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def run_claude_code(
    *,
    prompt: str,
    model: str | None,
    mcp_config: Path,
    cwd: Path,
    timeout_seconds: int,
    raw_dir: Path,
) -> HarnessRunResult:
    raw_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "claude",
        "-p",
        "--verbose",
        "--output-format",
        "stream-json",
        "--mcp-config",
        str(mcp_config),
        "--strict-mcp-config",
        "--allowedTools",
        "mcp__claw-eval__*",
        "--permission-mode",
        "dontAsk",
        "--no-session-persistence",
    ]
    if model:
        command.extend(["--model", model])
    command.append(prompt)

    env = dict(os.environ)
    env.setdefault("NO_PROXY", "localhost,127.0.0.1")
    env.setdefault("no_proxy", "localhost,127.0.0.1")

    started = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        returncode = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
    except subprocess.TimeoutExpired as exc:
        returncode = 124
        stdout = _to_text(exc.stdout)
        stderr = _to_text(exc.stderr)
        stderr = (stderr + "\n" if stderr else "") + f"Timed out after {timeout_seconds} seconds"
    wall_time_s = time.monotonic() - started
    (raw_dir / "claude-code.stdout.jsonl").write_text(stdout, encoding="utf-8")
    (raw_dir / "claude-code.stderr.log").write_text(stderr, encoding="utf-8")
    final_text, input_tokens, output_tokens = _extract_final_text(stdout)
    return HarnessRunResult(
        harness="claude-code",
        command=command,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        final_text=final_text,
        wall_time_s=wall_time_s,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
