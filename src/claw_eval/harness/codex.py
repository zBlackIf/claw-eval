"""Codex CLI runner for Claw-Eval external harness runs."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from .claude_code import HarnessRunResult, _to_text


def _extract_final_text(stdout: str, last_message_path: Path) -> str:
    if last_message_path.exists():
        text = last_message_path.read_text(encoding="utf-8", errors="replace").strip()
        if text:
            return text
    final_text = ""
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        for key in ("message", "text", "content", "final_response"):
            value = event.get(key)
            if isinstance(value, str) and value.strip():
                final_text = value.strip()
        item = event.get("item")
        if isinstance(item, dict):
            text = item.get("text") or item.get("content")
            if isinstance(text, str) and text.strip():
                final_text = text.strip()
    return final_text


def run_codex(
    *,
    prompt: str,
    model: str | None,
    config_overrides: list[str],
    cwd: Path,
    timeout_seconds: int,
    raw_dir: Path,
) -> HarnessRunResult:
    raw_dir.mkdir(parents=True, exist_ok=True)
    last_message_path = raw_dir / "codex.last_message.txt"
    command = [
        "codex",
        "--ask-for-approval",
        "never",
        "exec",
        "--json",
        "--ignore-user-config",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--cd",
        str(cwd),
        "--output-last-message",
        str(last_message_path),
    ]
    if model:
        command.extend(["--model", model])
    for override in config_overrides:
        command.extend(["-c", override])
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
    (raw_dir / "codex.stdout.jsonl").write_text(stdout, encoding="utf-8")
    (raw_dir / "codex.stderr.log").write_text(stderr, encoding="utf-8")
    return HarnessRunResult(
        harness="codex",
        command=command,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        final_text=_extract_final_text(stdout, last_message_path),
        wall_time_s=wall_time_s,
    )
