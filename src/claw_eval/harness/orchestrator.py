"""Run Claw-Eval tasks through external Claude Code or Codex harnesses."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from claw_eval.config import Config
from claw_eval.graders.registry import get_grader
from claw_eval.models.content import TextBlock, ToolResultBlock, ToolUseBlock
from claw_eval.models.message import Message
from claw_eval.models.scoring import compute_task_score, is_pass
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import (
    AuditSnapshot,
    DimensionScores,
    GradingResult,
    TokenUsage,
    TraceEnd,
    TraceMessage,
    TraceStart,
    ToolDispatch,
)
from claw_eval.runner.services import ServiceManager
from claw_eval.trace.writer import TraceWriter

from .claude_code import HarnessRunResult, load_claude_code_runtime_config, run_claude_code
from .codex import load_codex_runtime_config, run_codex
from .config_gen import codex_mcp_config_overrides, mcp_server_args, shell_join, write_claude_mcp_config
from .openclaw import load_openclaw_runtime_config, run_openclaw
from .hermes import load_hermes_runtime_config, run_hermes
from .opencode import load_opencode_runtime_config, run_opencode


HARNESS_NAMES = ("claude-code", "codex", "openclaw", "hermes", "opencode")


@dataclass
class McpPreflightResult:
    ok: bool
    detail: str = ""
    tool_count: int = 0
    command: list[str] | None = None


def _resolve_tasks_dir(task_yaml: Path) -> Path:
    return task_yaml.parent.parent


def _make_trace_dir(base_dir: str | Path, model_id: str, harness: str) -> Path:
    from datetime import datetime

    date_str = datetime.now().strftime("%y-%m-%d-%H-%M")
    safe_model = model_id.replace("/", "_")
    path = Path(base_dir) / harness / f"{safe_model}_{date_str}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_dispatches(path: Path) -> list[ToolDispatch]:
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(ToolDispatch.model_validate_json(line))
    return events


def _collect_audit(task: TaskDefinition, trace_id: str) -> list[AuditSnapshot]:
    import httpx

    events: list[AuditSnapshot] = []
    for svc in task.services:
        if not svc.reset_endpoint:
            continue
        audit_url = svc.reset_endpoint.rsplit("/reset", 1)[0] + "/audit"
        try:
            resp = httpx.get(audit_url, timeout=5)
            events.append(
                AuditSnapshot(
                    trace_id=trace_id,
                    service_name=svc.name,
                    audit_url=audit_url,
                    audit_data=resp.json(),
                )
            )
        except Exception:
            pass
    return events


def _make_prompt(task: TaskDefinition) -> str:
    return (
        "Complete this Claw-Eval task. Use the available claw-eval MCP tools "
        "for task APIs and sandbox operations. When the task is complete, "
        "provide a concise final answer.\n\n"
        f"{task.prompt.text}"
    )


_MCP_PREFLIGHT_CODE = r"""
import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    server_command = sys.argv[1]
    server_args = json.loads(sys.argv[2])
    params = StdioServerParameters(command=server_command, args=server_args)
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = [tool.name for tool in tools.tools]
            print(json.dumps({"tool_count": len(names), "tools": names}, ensure_ascii=False))


asyncio.run(main())
"""


def _preflight_mcp_server(
    *,
    python: str,
    server_args: list[str],
    timeout_seconds: int = 15,
) -> McpPreflightResult:
    command = [
        python,
        "-c",
        _MCP_PREFLIGHT_CODE,
        python,
        json.dumps(server_args),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        detail = f"timed out after {timeout_seconds}s"
        if exc.stderr:
            detail += f": {exc.stderr}"
        return McpPreflightResult(ok=False, detail=detail, command=command)
    except OSError as exc:
        return McpPreflightResult(ok=False, detail=str(exc), command=command)

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or f"exit {result.returncode}").strip()
        return McpPreflightResult(ok=False, detail=detail[:2000], command=command)
    try:
        payload = json.loads((result.stdout or "{}").splitlines()[-1])
        tool_count = int(payload.get("tool_count") or 0)
    except Exception:
        tool_count = 0
    if tool_count <= 0:
        return McpPreflightResult(
            ok=False,
            detail="MCP server initialized but returned no tools",
            tool_count=tool_count,
            command=command,
        )
    return McpPreflightResult(ok=True, detail=result.stdout.strip(), tool_count=tool_count, command=command)


def _response_body_text(value) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return str(value)


def _write_trace(
    *,
    trace_path: Path,
    trace_id: str,
    task: TaskDefinition,
    model_id: str,
    harness_result: HarnessRunResult,
    dispatches: list[ToolDispatch],
    audits: list[AuditSnapshot],
    wall_time_s: float,
    start_timestamp: str,
    scores=None,
    task_score: float | None = None,
    passed: bool | None = None,
) -> None:
    if trace_path.exists():
        trace_path.unlink()
    with TraceWriter(trace_path) as writer:
        writer.write_event(
            TraceStart(
                trace_id=trace_id,
                task_id=task.task_id,
                model=model_id,
                persona=harness_result.harness,
                timestamp=start_timestamp,
            )
        )
        writer.write_event(
            TraceMessage(
                trace_id=trace_id,
                message=Message(role="user", content=[TextBlock(text=task.prompt.text)]),
            )
        )
        for dispatch in dispatches:
            writer.write_event(
                TraceMessage(
                    trace_id=trace_id,
                    message=Message(
                        role="assistant",
                        content=[
                            ToolUseBlock(
                                id=dispatch.tool_use_id,
                                name=dispatch.tool_name,
                                input=dispatch.request_body,
                            )
                        ],
                    ),
                )
            )
            writer.write_event(dispatch)
            writer.write_event(
                TraceMessage(
                    trace_id=trace_id,
                    message=Message(
                        role="user",
                        content=[
                            ToolResultBlock(
                                tool_use_id=dispatch.tool_use_id,
                                content=[TextBlock(text=_response_body_text(dispatch.response_body))],
                                is_error=dispatch.response_status >= 400,
                            )
                        ],
                    ),
                )
            )
        if harness_result.final_text:
            writer.write_event(
                TraceMessage(
                    trace_id=trace_id,
                    message=Message(role="assistant", content=[TextBlock(text=harness_result.final_text)]),
                    usage=TokenUsage(
                        input_tokens=harness_result.input_tokens,
                        output_tokens=harness_result.output_tokens,
                    ),
                )
            )
        for audit in audits:
            writer.write_event(audit)
        failure_modes = list(harness_result.failure_modes)
        if harness_result.returncode != 0:
            failure_modes.append(f"{harness_result.harness} exited with {harness_result.returncode}")
        writer.write_event(
            TraceEnd(
                trace_id=trace_id,
                total_turns=max(1, harness_result.turns),
                model_input_tokens=harness_result.input_tokens,
                model_output_tokens=harness_result.output_tokens,
                input_tokens=harness_result.input_tokens,
                output_tokens=harness_result.output_tokens,
                total_tokens=harness_result.input_tokens + harness_result.output_tokens,
                model_time_s=round(harness_result.wall_time_s, 2),
                tool_time_s=round(sum(d.latency_ms for d in dispatches) / 1000.0, 2),
                wall_time_s=round(wall_time_s, 2),
                scores=scores or DimensionScores(),
                task_score=task_score or 0.0,
                passed=bool(passed),
                failure_modes=failure_modes,
            )
        )
        if scores is not None and task_score is not None and passed is not None:
            writer.write_event(
                GradingResult(
                    trace_id=trace_id,
                    task_id=task.task_id,
                    scores=scores,
                    task_score=task_score,
                    passed=passed,
                    failure_modes=failure_modes,
                )
            )


def run_harness_task(
    *,
    task_yaml: Path,
    harness: str,
    model_id: str,
    cfg: Config,
    trace_dir: Path,
    port_offset: int = 0,
    sandbox: bool = False,
    sandbox_image: str | None = None,
    no_judge: bool = False,
    claude_code_runtime_config: Path | None = None,
    codex_runtime_config: Path | None = None,
    openclaw_runtime_config: Path | None = None,
    hermes_runtime_config: Path | None = None,
    opencode_runtime_config: Path | None = None,
) -> dict:
    if harness not in HARNESS_NAMES:
        raise ValueError(f"Unknown harness: {harness}")

    task = TaskDefinition.from_yaml(task_yaml)
    if port_offset:
        task.apply_port_offset(port_offset)

    trace_id = str(uuid4())
    task_trace_dir = trace_dir / f"{task.task_id}_{trace_id[:8]}"
    raw_dir = task_trace_dir / "raw"
    task_trace_dir.mkdir(parents=True, exist_ok=True)
    dispatch_log = task_trace_dir / "dispatches.jsonl"
    trace_path = trace_dir / f"{task.task_id}_{trace_id[:8]}.jsonl"
    start_timestamp = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()

    sandbox_runner = None
    handle = None
    env_snapshot = None
    audits: list[AuditSnapshot] = []

    with tempfile.TemporaryDirectory(prefix="claw-eval-harness-") as tmp:
        tmp_dir = Path(tmp)
        try:
            with ServiceManager(
                task.services,
                cwd=_resolve_tasks_dir(task_yaml).parent,
                mock_today=task.environment.mock_today,
                task_id=task.task_id,
            ):
                if sandbox:
                    from claw_eval.runner.sandbox_runner import SandboxRunner
                    from claw_eval.cli import _collect_env_snapshot, _save_env_snapshot

                    sandbox_runner = SandboxRunner(cfg.sandbox, image=sandbox_image or cfg.sandbox.image)
                    handle = sandbox_runner.start_container(run_id=f"{task.task_id}-{trace_id[:8]}")
                    sandbox_runner.inject_files(handle, task, task_dir=str(task_yaml.parent))

                server_args = mcp_server_args(
                    task_yaml=task_yaml,
                    trace_id=trace_id,
                    dispatch_log=dispatch_log,
                    sandbox_url=handle.sandbox_url if handle else None,
                    port_offset=port_offset,
                )
                prompt = _make_prompt(task)
                preflight = _preflight_mcp_server(
                    python=sys.executable,
                    server_args=server_args,
                    timeout_seconds=min(20, max(5, task.environment.timeout_seconds)),
                )
                if not preflight.ok:
                    harness_result = HarnessRunResult(
                        harness=harness,
                        command=preflight.command or [sys.executable, *server_args],
                        returncode=126,
                        stdout=preflight.detail,
                        stderr=preflight.detail,
                        final_text="",
                        wall_time_s=0.0,
                        failure_modes=[f"MCP preflight failed: {preflight.detail}"],
                    )
                    raw_dir.mkdir(parents=True, exist_ok=True)
                    (raw_dir / "mcp_preflight_error.log").write_text(preflight.detail, encoding="utf-8")
                else:
                    if harness == "claude-code":
                        mcp_config = write_claude_mcp_config(
                            path=tmp_dir / "claude_mcp_config.json",
                            python=sys.executable,
                            server_args=server_args,
                        )
                        claude_runtime = (
                            load_claude_code_runtime_config(
                                Path(claude_code_runtime_config),
                                config_dir=task_trace_dir / "claude-code-config",
                            )
                            if claude_code_runtime_config
                            else None
                        )
                        harness_result = run_claude_code(
                            prompt=prompt,
                            model=claude_runtime.model_name if claude_runtime else model_id,
                            mcp_config=mcp_config,
                            cwd=tmp_dir,
                            timeout_seconds=task.environment.timeout_seconds,
                            raw_dir=raw_dir,
                            claude_runtime_config=claude_runtime,
                        )
                    elif harness == "codex":
                        codex_runtime = (
                            load_codex_runtime_config(Path(codex_runtime_config))
                            if codex_runtime_config
                            else None
                        )
                        harness_result = run_codex(
                            prompt=prompt,
                            model=codex_runtime.model_name if codex_runtime else model_id,
                            config_overrides=codex_mcp_config_overrides(
                                python=sys.executable,
                                server_args=server_args,
                            ),
                            cwd=tmp_dir,
                            timeout_seconds=task.environment.timeout_seconds,
                            raw_dir=raw_dir,
                            codex_runtime_config=codex_runtime,
                        )
                    elif harness == "openclaw":
                        oc_runtime = (
                            load_openclaw_runtime_config(Path(openclaw_runtime_config))
                            if openclaw_runtime_config
                            else None
                        )
                        harness_result = run_openclaw(
                            prompt=prompt,
                            model=oc_runtime.model_name if oc_runtime else model_id,
                            python=sys.executable,
                            server_args=server_args,
                            cwd=tmp_dir,
                            timeout_seconds=task.environment.timeout_seconds,
                            raw_dir=raw_dir,
                            openclaw_runtime_config=oc_runtime,
                        )
                    elif harness == "hermes":
                        h_runtime = (
                            load_hermes_runtime_config(Path(hermes_runtime_config))
                            if hermes_runtime_config
                            else None
                        )
                        harness_result = run_hermes(
                            prompt=prompt,
                            model=h_runtime.model_name if h_runtime else model_id,
                            python=sys.executable,
                            server_args=server_args,
                            cwd=tmp_dir,
                            timeout_seconds=task.environment.timeout_seconds,
                            raw_dir=raw_dir,
                            hermes_runtime_config=h_runtime,
                        )
                    elif harness == "opencode":
                        ocode_runtime = (
                            load_opencode_runtime_config(Path(opencode_runtime_config))
                            if opencode_runtime_config
                            else None
                        )
                        harness_result = run_opencode(
                            prompt=prompt,
                            model=ocode_runtime.model_name if ocode_runtime else model_id,
                            python=sys.executable,
                            server_args=server_args,
                            cwd=tmp_dir,
                            timeout_seconds=task.environment.timeout_seconds,
                            raw_dir=raw_dir,
                            opencode_runtime_config=ocode_runtime,
                        )
                    else:
                        raise ValueError(f"Unknown harness: {harness}")

                if handle:
                    from claw_eval.cli import _collect_env_snapshot, _save_env_snapshot

                    sandbox_runner.inject_grader_files(handle, task, task_dir=str(task_yaml.parent))
                    env_snapshot = _collect_env_snapshot(handle.sandbox_url, task)
                    _save_env_snapshot(env_snapshot, trace_path, task.task_id)
                audits = _collect_audit(task, trace_id)
        finally:
            if handle and sandbox_runner:
                sandbox_runner.stop_container(handle)

    wall_time_s = time.monotonic() - started
    dispatches = _load_dispatches(dispatch_log)
    _write_trace(
        trace_path=trace_path,
        trace_id=trace_id,
        task=task,
        model_id=model_id,
        harness_result=harness_result,
        dispatches=dispatches,
        audits=audits,
        wall_time_s=wall_time_s,
        start_timestamp=start_timestamp,
    )

    if harness_result.failure_modes or harness_result.returncode != 0:
        scores = DimensionScores()
        passed = False
        task_score = 0.0
        _write_trace(
            trace_path=trace_path,
            trace_id=trace_id,
            task=task,
            model_id=model_id,
            harness_result=harness_result,
            dispatches=dispatches,
            audits=audits,
            wall_time_s=wall_time_s,
            start_timestamp=start_timestamp,
            scores=scores,
            task_score=task_score,
            passed=passed,
        )
        return {
            "task_id": task.task_id,
            "task_name": task.task_name,
            "harness": harness,
            "model": model_id,
            "trace": str(trace_path),
            "raw_dir": str(raw_dir),
            "command": shell_join(harness_result.command),
            "returncode": harness_result.returncode,
            "error": "; ".join(harness_result.failure_modes) or f"{harness} exited with {harness_result.returncode}",
            "failure_modes": harness_result.failure_modes,
            "turns": harness_result.turns,
            "input_tokens": harness_result.input_tokens,
            "output_tokens": harness_result.output_tokens,
            "tokens": harness_result.input_tokens + harness_result.output_tokens,
            "model_input_tokens": harness_result.input_tokens,
            "model_output_tokens": harness_result.output_tokens,
            "model_time_s": round(harness_result.wall_time_s, 2),
            "tool_time_s": round(sum(d.latency_ms for d in dispatches) / 1000.0, 2),
            "other_time_s": 0.0,
            "wall_time_s": round(wall_time_s, 2),
            "completion": scores.completion,
            "robustness": scores.robustness,
            "communication": scores.communication,
            "safety": scores.safety,
            "task_score": task_score,
            "passed": passed,
            "judge_calls": [],
        }

    from claw_eval.cli import _grade_with_optional_params, _make_judge
    from claw_eval.trace.reader import load_trace

    judge = None if no_judge else _make_judge(cfg, type("Args", (), {"no_judge": no_judge, "judge_model": None})())
    start, messages, loaded_dispatches, media_events, end, audit_data = load_trace(trace_path)
    grader = get_grader(task.task_id, tasks_dir=_resolve_tasks_dir(task_yaml), task_dir=task_yaml.parent)
    scores, judge_calls = _grade_with_optional_params(
        grader,
        messages,
        loaded_dispatches,
        task,
        audit_data=audit_data,
        judge=judge,
        media_events=media_events,
        env_snapshot=env_snapshot,
    )
    task_score = compute_task_score(scores)
    passed = is_pass(task_score)
    _write_trace(
        trace_path=trace_path,
        trace_id=trace_id,
        task=task,
        model_id=model_id,
        harness_result=harness_result,
        dispatches=dispatches,
        audits=audits,
        wall_time_s=wall_time_s,
        start_timestamp=start_timestamp,
        scores=scores,
        task_score=task_score,
        passed=passed,
    )
    return {
        "task_id": task.task_id,
        "task_name": task.task_name,
        "harness": harness,
        "model": model_id,
        "trace": str(trace_path),
        "raw_dir": str(raw_dir),
        "command": shell_join(harness_result.command),
        "returncode": harness_result.returncode,
        "failure_modes": harness_result.failure_modes,
        "turns": harness_result.turns,
        "input_tokens": harness_result.input_tokens,
        "output_tokens": harness_result.output_tokens,
        "tokens": harness_result.input_tokens + harness_result.output_tokens,
        "model_input_tokens": harness_result.input_tokens,
        "model_output_tokens": harness_result.output_tokens,
        "model_time_s": round(harness_result.wall_time_s, 2),
        "tool_time_s": round(sum(d.latency_ms for d in dispatches) / 1000.0, 2),
        "other_time_s": round(max(0.0, wall_time_s - harness_result.wall_time_s - sum(d.latency_ms for d in dispatches) / 1000.0), 2),
        "wall_time_s": round(wall_time_s, 2),
        "completion": scores.completion,
        "robustness": scores.robustness,
        "communication": scores.communication,
        "safety": scores.safety,
        "task_score": task_score,
        "passed": passed,
        "judge_calls": judge_calls,
    }
