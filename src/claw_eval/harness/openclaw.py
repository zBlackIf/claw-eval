"""OpenClaw CLI runner for Claw-Eval external harness runs."""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .claude_code import HarnessRunResult, _to_text


@dataclass
class OpenClawRuntimeConfig:
    api_key: str
    base_url: str
    model_name: str
    api_format: str = "openai-completions"
    provider_name: str = "modelhub"


_OPENCLAW_RUNTIME_ENV_PREFIXES = (
    "OPENCLAW_",
    "OPENAI_",
    "ANTHROPIC_",
    "CLAUDE_CODE_",
    "CODEX_",
)

_OPENCLAW_MAX_TOKENS_CAP = 32768


def load_openclaw_runtime_config(path: Path) -> OpenClawRuntimeConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return OpenClawRuntimeConfig(
        api_key=str(payload["api_key"]),
        base_url=str(payload["base_url"]),
        model_name=str(payload["model_name"]),
        api_format=str(payload.get("api_format", "openai-completions")),
        provider_name=str(payload.get("provider_name", "modelhub")),
    )


def _scrub_runtime_env(env: dict[str, str], prefixes: tuple[str, ...]) -> None:
    for key in list(env):
        if key.startswith(prefixes):
            env.pop(key, None)


def _openclaw_api(runtime: OpenClawRuntimeConfig) -> str:
    if runtime.api_format == "anthropic-messages":
        return "anthropic-messages"
    if runtime.api_format == "openai-responses":
        return "openai-responses"
    return "openai-completions"


def _openclaw_model_ref(runtime: OpenClawRuntimeConfig) -> str:
    provider = runtime.provider_name.strip() or "modelhub"
    model_name = runtime.model_name.strip()
    if model_name.startswith(f"{provider}/"):
        return model_name
    return f"{provider}/{model_name}"


def _openclaw_model_entry(runtime: OpenClawRuntimeConfig) -> dict:
    entry: dict = {
        "id": runtime.model_name,
        "name": runtime.model_name,
        "contextWindow": 1000000,
        "maxTokens": _OPENCLAW_MAX_TOKENS_CAP,
        "input": ["text", "image"],
        "reasoning": True,
    }
    if runtime.api_format == "openai-responses":
        # OpenClaw otherwise sends store=false and then previous_response_id on
        # follow-up tool turns, which Responses-compatible gateways reject.
        entry["compat"] = {"supportsStore": False}
    return entry


def _write_openclaw_config(
    home_dir: Path,
    python: str,
    server_args: list[str],
    runtime: OpenClawRuntimeConfig | None,
) -> Path:
    """Write an isolated OpenClaw config with Claw-Eval MCP and model provider."""
    config_dir = home_dir / ".openclaw"
    config_dir.mkdir(parents=True, exist_ok=True)
    config: dict = {
        "mcp": {
            "servers": {
                "claw-eval": {
                    "command": python,
                    "args": server_args,
                }
            }
        }
    }
    if runtime:
        provider = runtime.provider_name.strip() or "modelhub"
        model_ref = _openclaw_model_ref(runtime)
        config["agents"] = {
            "defaults": {
                "model": {"primary": model_ref},
                "models": {model_ref: {}},
                "workspace": str(home_dir / "workspace"),
            }
        }
        config["models"] = {
            "mode": "replace",
            "providers": {
                provider: {
                    "api": _openclaw_api(runtime),
                    "apiKey": runtime.api_key,
                    "baseUrl": runtime.base_url,
                    "models": [_openclaw_model_entry(runtime)],
                }
            },
        }
    config_path = config_dir / "openclaw.json"
    config_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return config_path


def _extract_final_text(stdout: str) -> tuple[str, int, int, int]:
    """Extract final answer, token usage, and turn count from OpenClaw JSON output."""
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
        final_text = stdout.strip().split("\n")[-1] if stdout.strip() else ""
    return final_text, input_tokens, output_tokens, turns


def run_openclaw(
    *,
    prompt: str,
    model: str | None,
    python: str,
    server_args: list[str],
    cwd: Path,
    timeout_seconds: int,
    raw_dir: Path,
    openclaw_runtime_config: OpenClawRuntimeConfig | None = None,
) -> HarnessRunResult:
    raw_dir.mkdir(parents=True, exist_ok=True)
    home_dir = raw_dir / "openclaw-home"
    config_path = _write_openclaw_config(home_dir, python, server_args, openclaw_runtime_config)

    effective_model = _openclaw_model_ref(openclaw_runtime_config) if openclaw_runtime_config else model
    session_id = "claw-eval-" + raw_dir.parent.name.replace("/", "_")[:80]
    command = [
        "openclaw",
        "agent",
        "--session-id",
        session_id,
        "--message",
        prompt,
        "--json",
        "--local",
        "--timeout",
        str(timeout_seconds),
    ]
    if effective_model:
        command.extend(["--model", effective_model])

    env = dict(os.environ)
    if openclaw_runtime_config:
        _scrub_runtime_env(env, _OPENCLAW_RUNTIME_ENV_PREFIXES)
        if (
            openclaw_runtime_config.api_format == "anthropic-messages"
            or openclaw_runtime_config.provider_name == "anthropic"
        ):
            env["ANTHROPIC_API_KEY"] = openclaw_runtime_config.api_key
            env["ANTHROPIC_AUTH_TOKEN"] = openclaw_runtime_config.api_key
            if openclaw_runtime_config.base_url:
                env["ANTHROPIC_BASE_URL"] = openclaw_runtime_config.base_url
        else:
            env["OPENAI_API_KEY"] = openclaw_runtime_config.api_key
            if openclaw_runtime_config.base_url:
                env["OPENAI_BASE_URL"] = openclaw_runtime_config.base_url
    env["HOME"] = str(home_dir)
    env["OPENCLAW_CONFIG_PATH"] = str(config_path)
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
            timeout=timeout_seconds + 30,
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
    (raw_dir / "openclaw.stdout.jsonl").write_text(stdout, encoding="utf-8")
    (raw_dir / "openclaw.stderr.log").write_text(stderr, encoding="utf-8")
    final_text, input_tokens, output_tokens, turns = _extract_final_text(stdout)
    failure_modes: list[str] = []
    if returncode == 124:
        failure_modes.append(f"Timed out after {timeout_seconds} seconds")
    return HarnessRunResult(
        harness="openclaw",
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
