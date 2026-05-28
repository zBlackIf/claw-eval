"""Codex CLI runner for Claw-Eval external harness runs."""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .claude_code import HarnessRunResult, _to_text


@dataclass
class CodexRuntimeConfig:
    api_key: str
    base_url: str
    model_name: str
    provider_name: str
    env_key: str
    wire_api: str


_CODEX_RUNTIME_ENV_PREFIXES = (
    "OPENAI_",
    "CODEX_",
    "ANTHROPIC_",
    "CLAUDE_CODE_",
    "AWS_",
    "BEDROCK_",
    "VERTEX_",
    "GOOGLE_VERTEX_",
    "FOUNDRY_",
)


def load_codex_runtime_config(path: Path) -> CodexRuntimeConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return CodexRuntimeConfig(
        api_key=str(payload["api_key"]),
        base_url=str(payload["base_url"]),
        model_name=str(payload["model_name"]),
        provider_name=str(payload["provider_name"]),
        env_key=str(payload["env_key"]),
        wire_api=str(payload["wire_api"]),
    )


def _codex_runtime_overrides(runtime: CodexRuntimeConfig) -> list[str]:
    provider = runtime.provider_name
    return [
        f"model_provider={json.dumps(provider)}",
        f"model_providers.{provider}.name={json.dumps(provider)}",
        f"model_providers.{provider}.base_url={json.dumps(runtime.base_url)}",
        f"model_providers.{provider}.env_key={json.dumps(runtime.env_key)}",
        f"model_providers.{provider}.wire_api={json.dumps(runtime.wire_api)}",
    ]


def _scrub_runtime_env(env: dict[str, str], prefixes: tuple[str, ...]) -> None:
    for key in list(env):
        if key.startswith(prefixes):
            env.pop(key, None)


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
    codex_runtime_config: CodexRuntimeConfig | None = None,
) -> HarnessRunResult:
    raw_dir.mkdir(parents=True, exist_ok=True)
    last_message_path = raw_dir / "codex.last_message.txt"
    effective_model = codex_runtime_config.model_name if codex_runtime_config else model
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
    if effective_model:
        command.extend(["--model", effective_model])
    runtime_overrides = _codex_runtime_overrides(codex_runtime_config) if codex_runtime_config else []
    for override in runtime_overrides + config_overrides:
        command.extend(["-c", override])
    command.append(prompt)

    env = dict(os.environ)
    if codex_runtime_config:
        _scrub_runtime_env(env, _CODEX_RUNTIME_ENV_PREFIXES)
        env[codex_runtime_config.env_key] = codex_runtime_config.api_key
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
    except OSError as exc:
        returncode = 127
        stdout = ""
        stderr = str(exc)
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
