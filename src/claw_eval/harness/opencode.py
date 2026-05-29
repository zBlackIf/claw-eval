"""OpenCode CLI runner for Claw-Eval external harness runs."""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .claude_code import HarnessRunResult, _to_text


@dataclass
class OpenCodeRuntimeConfig:
    api_key: str
    base_url: str
    model_name: str
    provider_name: str
    api_format: str = "openai-completions"


_OPENCODE_RUNTIME_ENV_PREFIXES = (
    "OPENCODE_",
    "OPENAI_",
    "ANTHROPIC_",
    "CLAUDE_CODE_",
    "CODEX_",
)


def load_opencode_runtime_config(path: Path) -> OpenCodeRuntimeConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return OpenCodeRuntimeConfig(
        api_key=str(payload["api_key"]),
        base_url=str(payload["base_url"]),
        model_name=str(payload["model_name"]),
        provider_name=str(payload.get("provider_name", "anthropic")),
        api_format=str(payload.get("api_format", "openai-completions")),
    )


def _scrub_runtime_env(env: dict[str, str], prefixes: tuple[str, ...]) -> None:
    for key in list(env):
        if key.startswith(prefixes):
            env.pop(key, None)


def _opencode_provider_package(runtime: OpenCodeRuntimeConfig) -> str:
    if runtime.api_format == "anthropic-messages" or runtime.provider_name == "anthropic":
        return "@ai-sdk/anthropic"
    return "@ai-sdk/openai-compatible"


def _opencode_env_key(runtime: OpenCodeRuntimeConfig) -> str:
    if runtime.api_format == "anthropic-messages" or runtime.provider_name == "anthropic":
        return "ANTHROPIC_API_KEY"
    return f"{runtime.provider_name.upper()}_API_KEY"


def _opencode_base_url_env_key(runtime: OpenCodeRuntimeConfig) -> str:
    if runtime.api_format == "anthropic-messages" or runtime.provider_name == "anthropic":
        return "ANTHROPIC_BASE_URL"
    return f"{runtime.provider_name.upper()}_BASE_URL"


def _opencode_model_id(runtime: OpenCodeRuntimeConfig) -> str:
    return f"{runtime.provider_name}/{runtime.model_name}"


def _write_opencode_config(config_dir: Path, python: str, server_args: list[str], runtime: OpenCodeRuntimeConfig | None) -> Path:
    """Write OpenCode config with MCP server and model settings."""
    config_dir.mkdir(parents=True, exist_ok=True)
    config: dict = {
        "$schema": "https://opencode.ai/config.json",
        "mcp": {
            "claw-eval": {
                "type": "local",
                "command": [python, *server_args],
                "enabled": True,
            }
        }
    }
    if runtime:
        env_key = _opencode_env_key(runtime)
        options = {
            "apiKey": f"{{env:{env_key}}}",
        }
        if runtime.base_url:
            options["baseURL"] = runtime.base_url
        provider_config = {
            "npm": _opencode_provider_package(runtime),
            "name": runtime.provider_name,
            "options": options,
            "models": {
                runtime.model_name: {
                    "name": runtime.model_name,
                }
            },
        }
        config["provider"] = {
            runtime.provider_name: provider_config
        }
        config["model"] = _opencode_model_id(runtime)
    config_path = config_dir / "config.json"
    config_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return config_path


def _extract_output(stdout: str) -> tuple[str, int, int, int]:
    """Extract final answer, token usage, and turn count from OpenCode JSON output."""
    final_text = ""
    input_tokens = 0
    output_tokens = 0
    turns = 1
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        evt_type = event.get("type", "")
        if evt_type == "text" or evt_type == "message":
            text = event.get("text") or event.get("content") or ""
            if isinstance(text, str) and text.strip():
                final_text = text.strip()
        for key in ("result", "message", "text", "content", "final_response"):
            value = event.get(key)
            if isinstance(value, str) and value.strip():
                final_text = value.strip()
        usage = event.get("usage") or event.get("token_usage")
        if isinstance(usage, dict):
            input_tokens += int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
            output_tokens += int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
        raw_turns = event.get("num_turns") or event.get("turns")
        if raw_turns:
            try:
                turns = max(turns, int(raw_turns))
            except (TypeError, ValueError):
                pass
    if not final_text:
        for line in reversed(stdout.strip().splitlines()):
            line = line.strip()
            if line:
                try:
                    ev = json.loads(line)
                    final_text = ev.get("text") or ev.get("content") or ev.get("result") or line
                except json.JSONDecodeError:
                    final_text = line
                break
    return final_text, input_tokens, output_tokens, turns


def run_opencode(
    *,
    prompt: str,
    model: str | None,
    python: str,
    server_args: list[str],
    cwd: Path,
    timeout_seconds: int,
    raw_dir: Path,
    opencode_runtime_config: OpenCodeRuntimeConfig | None = None,
) -> HarnessRunResult:
    raw_dir.mkdir(parents=True, exist_ok=True)
    config_dir = raw_dir / "opencode-config"
    _write_opencode_config(config_dir, python, server_args, opencode_runtime_config)

    effective_model = _opencode_model_id(opencode_runtime_config) if opencode_runtime_config else model
    command = [
        "opencode",
        "run",
        "--format",
        "json",
        "--dangerously-skip-permissions",
    ]
    if effective_model:
        command.extend(["-m", effective_model])
    command.append(prompt)

    env = dict(os.environ)
    if opencode_runtime_config:
        _scrub_runtime_env(env, _OPENCODE_RUNTIME_ENV_PREFIXES)
        env_key = _opencode_env_key(opencode_runtime_config)
        env[env_key] = opencode_runtime_config.api_key
        if opencode_runtime_config.base_url:
            env[_opencode_base_url_env_key(opencode_runtime_config)] = opencode_runtime_config.base_url
    env["HOME"] = str(raw_dir / "opencode-home")
    env["OPENCODE_CONFIG"] = str(config_dir / "config.json")
    env["OPENCODE_EXPERIMENTAL_BASH_DEFAULT_TIMEOUT_MS"] = str(min(timeout_seconds * 1000, 300000))
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
    (raw_dir / "opencode.stdout.jsonl").write_text(stdout, encoding="utf-8")
    (raw_dir / "opencode.stderr.log").write_text(stderr, encoding="utf-8")
    final_text, input_tokens, output_tokens, turns = _extract_output(stdout)
    failure_modes: list[str] = []
    if returncode == 124:
        failure_modes.append(f"Timed out after {timeout_seconds} seconds")
    return HarnessRunResult(
        harness="opencode",
        command=command,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        final_text=final_text,
        wall_time_s=wall_time_s,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        turns=turns,
        failure_modes=failure_modes,
    )
