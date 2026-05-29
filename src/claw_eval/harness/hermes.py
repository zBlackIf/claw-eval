"""Hermes Agent CLI runner for Claw-Eval external harness runs."""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .claude_code import HarnessRunResult, _to_text


@dataclass
class HermesRuntimeConfig:
    api_key: str
    base_url: str
    model_name: str
    provider_name: str
    api_format: str = "openai-completions"


_HERMES_RUNTIME_ENV_PREFIXES = (
    "HERMES_",
    "OPENAI_",
    "ANTHROPIC_",
    "CLAUDE_CODE_",
    "CODEX_",
)
_HERMES_MCP_SERVER_NAME = "claw-eval"
_HERMES_MAX_TOKENS_CAP = 32768
_HERMES_CONTEXT_LENGTH = 256000


def load_hermes_runtime_config(path: Path) -> HermesRuntimeConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return HermesRuntimeConfig(
        api_key=str(payload["api_key"]),
        base_url=str(payload["base_url"]),
        model_name=str(payload["model_name"]),
        provider_name=str(payload.get("provider_name", "openrouter")),
        api_format=str(payload.get("api_format", "openai-completions")),
    )


def _scrub_runtime_env(env: dict[str, str], prefixes: tuple[str, ...]) -> None:
    for key in list(env):
        if key.startswith(prefixes):
            env.pop(key, None)


def _hermes_provider(runtime: HermesRuntimeConfig) -> str:
    if runtime.api_format == "anthropic-messages" or runtime.provider_name == "anthropic":
        return "anthropic"
    return "custom"


def _write_hermes_config(home_dir: Path, python: str, server_args: list[str], runtime: HermesRuntimeConfig | None) -> Path:
    """Write an isolated ~/.hermes/config.yaml for this Claw-Eval task."""
    config_dir = home_dir / ".hermes"
    config_dir.mkdir(parents=True, exist_ok=True)
    config: dict = {
        "mcp_servers": {
            _HERMES_MCP_SERVER_NAME: {
                "command": python,
                "args": server_args,
                "enabled": True,
                "connect_timeout": 20,
                "timeout": 180,
            }
        },
        "toolsets": [_HERMES_MCP_SERVER_NAME],
    }
    if runtime:
        model_config = {
            "provider": _hermes_provider(runtime),
            "default": runtime.model_name,
            "context_length": _HERMES_CONTEXT_LENGTH,
            "max_tokens": _HERMES_MAX_TOKENS_CAP,
        }
        if runtime.base_url and model_config["provider"] == "custom":
            model_config["base_url"] = runtime.base_url
        config["model"] = model_config
    config_path = config_dir / "config.yaml"
    import yaml
    config_path.write_text(
        yaml.dump(config, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    return config_path


def _extract_final_text(stdout: str) -> tuple[str, int, int, int]:
    """Extract final answer, token usage, and turn count from Hermes output."""
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
            if line:
                final_text = line
            continue
        if not isinstance(event, dict):
            continue
        for key in ("result", "message", "text", "content", "final_response"):
            value = event.get(key)
            if isinstance(value, str) and value.strip():
                final_text = value.strip()
        item = event.get("item")
        if isinstance(item, dict):
            text = item.get("text") or item.get("content")
            if isinstance(text, str) and text.strip():
                final_text = text.strip()
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
        final_text = stdout.strip()
    return final_text, input_tokens, output_tokens, turns


def run_hermes(
    *,
    prompt: str,
    model: str | None,
    python: str,
    server_args: list[str],
    cwd: Path,
    timeout_seconds: int,
    raw_dir: Path,
    hermes_runtime_config: HermesRuntimeConfig | None = None,
) -> HarnessRunResult:
    raw_dir.mkdir(parents=True, exist_ok=True)
    home_dir = raw_dir / "hermes-home"
    _write_hermes_config(home_dir, python, server_args, hermes_runtime_config)

    effective_model = hermes_runtime_config.model_name if hermes_runtime_config else model
    max_turns = max(50, timeout_seconds // 10)
    command = [
        "hermes",
        "chat",
        "-Q",
        "-q",
        prompt,
        "--yolo",
        "--ignore-rules",
        "--max-turns",
        str(max_turns),
        "--toolsets",
        _HERMES_MCP_SERVER_NAME,
    ]
    if hermes_runtime_config:
        command.extend(["--provider", _hermes_provider(hermes_runtime_config)])
        if effective_model:
            command.extend(["--model", effective_model])
    elif effective_model:
        command.extend(["--model", effective_model])

    env = dict(os.environ)
    if hermes_runtime_config:
        _scrub_runtime_env(env, _HERMES_RUNTIME_ENV_PREFIXES)
        if _hermes_provider(hermes_runtime_config) == "anthropic":
            env["ANTHROPIC_API_KEY"] = hermes_runtime_config.api_key
            if hermes_runtime_config.base_url:
                env["ANTHROPIC_BASE_URL"] = hermes_runtime_config.base_url
        else:
            env["OPENAI_API_KEY"] = hermes_runtime_config.api_key
            if hermes_runtime_config.base_url:
                env["OPENAI_BASE_URL"] = hermes_runtime_config.base_url
        env["HERMES_INFERENCE_MODEL"] = hermes_runtime_config.model_name
    env["HOME"] = str(home_dir)
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
    (raw_dir / "hermes.stdout.log").write_text(stdout, encoding="utf-8")
    (raw_dir / "hermes.stderr.log").write_text(stderr, encoding="utf-8")
    final_text, input_tokens, output_tokens, turns = _extract_final_text(stdout)
    failure_modes: list[str] = []
    if returncode == 124:
        failure_modes.append(f"Timed out after {timeout_seconds} seconds")
    return HarnessRunResult(
        harness="hermes",
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
