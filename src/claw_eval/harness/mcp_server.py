"""MCP stdio server exposing Claw-Eval task tools to external harnesses."""

from __future__ import annotations

import argparse
import asyncio
import json
import threading
from pathlib import Path
from typing import Any
from uuid import uuid4

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from claw_eval.models.content import ToolUseBlock
from claw_eval.models.task import TaskDefinition
from claw_eval.runner.dispatcher import ToolDispatcher
from claw_eval.runner.sandbox_dispatcher import SandboxToolDispatcher
from claw_eval.runner.sandbox_tools import SANDBOX_TOOLS


def _load_task(task_yaml: Path, port_offset: int) -> TaskDefinition:
    task = TaskDefinition.from_yaml(task_yaml)
    if port_offset:
        task.apply_port_offset(port_offset)
    return task


def _tool_specs(task: TaskDefinition) -> list:
    existing = {tool.name for tool in task.tools}
    tools = list(task.tools)
    tools.extend(tool for tool in SANDBOX_TOOLS if tool.name not in existing)
    return tools


def _mcp_content_from_result(result, extra_media) -> list:
    content: list[Any] = []
    for block in result.content:
        content.append(types.TextContent(type="text", text=block.text))
    for block in extra_media or []:
        if block.type == "image":
            content.append(
                types.ImageContent(
                    type="image",
                    data=block.data,
                    mimeType=block.mime_type,
                )
            )
    if not content:
        content.append(types.TextContent(type="text", text=""))
    return content


def build_server(
    *,
    task_yaml: Path,
    trace_id: str,
    dispatch_log: Path,
    sandbox_url: str | None,
    port_offset: int,
) -> Server:
    task = _load_task(task_yaml, port_offset)
    http_dispatcher = ToolDispatcher(task.get_endpoint_map())
    dispatcher = SandboxToolDispatcher(http_dispatcher, sandbox_url=sandbox_url)
    lock = threading.Lock()
    dispatch_log.parent.mkdir(parents=True, exist_ok=True)

    server = Server("claw-eval", version="1.0.0")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name=tool.name,
                description=tool.description,
                inputSchema=tool.input_schema or {"type": "object", "properties": {}},
            )
            for tool in _tool_specs(task)
        ]

    @server.call_tool(validate_input=False)
    async def call_tool(name: str, arguments: dict[str, Any]) -> types.CallToolResult:
        tool_use = ToolUseBlock(
            id=f"mcp-{name}-{uuid4().hex}",
            name=name,
            input=arguments or {},
        )
        result, dispatch_event, extra_media = dispatcher.dispatch(tool_use, trace_id)
        with lock:
            with dispatch_log.open("a", encoding="utf-8") as fh:
                fh.write(dispatch_event.model_dump_json() + "\n")
        return types.CallToolResult(
            content=_mcp_content_from_result(result, extra_media),
            isError=result.is_error,
            structuredContent={
                "tool_name": name,
                "response_status": dispatch_event.response_status,
                "response_body": dispatch_event.response_body,
            },
        )

    return server


async def _run(args: argparse.Namespace) -> None:
    server = build_server(
        task_yaml=Path(args.task),
        trace_id=args.trace_id,
        dispatch_log=Path(args.dispatch_log),
        sandbox_url=args.sandbox_url,
        port_offset=args.port_offset,
    )
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the Claw-Eval MCP stdio server")
    parser.add_argument("--task", required=True, help="Path to task.yaml")
    parser.add_argument("--trace-id", required=True)
    parser.add_argument("--dispatch-log", required=True)
    parser.add_argument("--sandbox-url", default=None)
    parser.add_argument("--port-offset", type=int, default=0)
    args = parser.parse_args(argv)
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
