"""OpenAI Responses API provider for Claw-Eval.

v0.30.12 ark overlay (new file). Implements the same chat() contract as
OpenAICompatProvider so runner/loop.py can swap providers transparently.

Only text + tool_use / tool_result are first-class. Image input is supported
via input_image (base64 data URLs). Audio/video gracefully degrade to text
markers.
"""

from __future__ import annotations

import json
import os
import random
import time
from typing import Any
from uuid import uuid4

from openai import OpenAI

from ...models.content import ImageBlock, TextBlock, ToolUseBlock
from ...models.message import Message
from ...models.tool import ToolSpec
from ...models.trace import TokenUsage

_MALFORMED_TOOL_INPUT_KEY = "__ark_malformed_tool_input__"
DEFAULT_MAX_RETRIES = 20


def _normalize_max_retries(value: int | None, default: int = DEFAULT_MAX_RETRIES) -> int:
    if value is None:
        return default
    retries = int(value)
    if retries < 0:
        raise ValueError("max_retries must be >= 0")
    return retries


def _pop_required_positive_int(values: dict[str, Any], field: str) -> int:
    if field not in values:
        raise ValueError(
            f"Claw-Eval openai-responses provider requires extra_body.{field}; "
            "configure maxTokens / Max Output Tokens in the model config."
        )
    raw_value = values.pop(field)
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Claw-Eval openai-responses provider requires positive integer extra_body.{field}; "
            "configure maxTokens / Max Output Tokens in the model config."
        ) from exc
    if value <= 0:
        raise ValueError(
            f"Claw-Eval openai-responses provider requires positive integer extra_body.{field}; "
            "configure maxTokens / Max Output Tokens in the model config."
        )
    return value


def _tool_spec_to_responses(spec: ToolSpec) -> dict[str, Any]:
    """ToolSpec -> OpenAI Responses tool (top-level name/description/parameters)."""
    return {
        "type": "function",
        "name": spec.name,
        "description": spec.description,
        "parameters": spec.input_schema or {"type": "object", "properties": {}},
    }


def _json_preview(value: Any, limit: int = 500) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except TypeError:
        text = repr(value)
    return text if len(text) <= limit else text[:limit] + "...[truncated]"


def _json_type_name(value: Any) -> str:
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    return type(value).__name__


def _coerce_tool_input(tool_name: str, raw_input: Any) -> dict[str, Any]:
    if isinstance(raw_input, dict):
        return raw_input
    return {
        _MALFORMED_TOOL_INPUT_KEY: {
            "tool_name": tool_name,
            "input_type": _json_type_name(raw_input),
            "input_preview": _json_preview(raw_input),
        }
    }


def _content_for_role(msg: Message, role: str) -> list[dict[str, Any]]:
    """Convert message blocks to Responses-API content parts.

    User/system messages use `input_text` / `input_image`. Assistant messages
    (when echoing back) use `output_text`.
    """
    text_type = "output_text" if role == "assistant" else "input_text"
    out: list[dict[str, Any]] = []
    for b in msg.content:
        if b.type == "text":
            out.append({"type": text_type, "text": b.text})
        elif b.type == "image" and role != "assistant":
            blk = b if isinstance(b, ImageBlock) else ImageBlock.model_validate(b)
            out.append({
                "type": "input_image",
                "image_url": f"data:{blk.mime_type};base64,{blk.data}",
            })
        elif b.type in ("audio", "video"):
            out.append({
                "type": text_type,
                "text": f"[{b.type} attached; not supported by Responses input parts]",
            })
        # tool_use / tool_result handled at the message level (not as content parts)
    return out


def _messages_to_responses_input(messages: list[Message]) -> list[dict[str, Any]]:
    """Flatten messages into Responses input items.

    Tool calls/results map to top-level items:
      tool_use      -> {type: function_call, call_id, name, arguments}
      tool_result   -> {type: function_call_output, call_id, output}
    """
    out: list[dict[str, Any]] = []
    for msg in messages:
        # Tool result messages — emit as function_call_output items
        tool_results = [b for b in msg.content if b.type == "tool_result"]
        if tool_results:
            for tr in tool_results:
                inner_text = "\n".join(t.text for t in tr.content) if tr.content else ""
                out.append({
                    "type": "function_call_output",
                    "call_id": tr.tool_use_id,
                    "output": inner_text,
                })
            continue

        # Assistant tool_use → function_call items
        tool_uses = [b for b in msg.content if b.type == "tool_use"]
        if tool_uses and msg.role == "assistant":
            text_blocks = [b for b in msg.content if b.type == "text"]
            if text_blocks:
                out.append({
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": b.text} for b in text_blocks],
                })
            for tu in tool_uses:
                out.append({
                    "type": "function_call",
                    "call_id": tu.id,
                    "name": tu.name,
                    "arguments": json.dumps(tu.input or {}),
                })
            continue

        # Plain user / assistant / system messages
        parts = _content_for_role(msg, msg.role)
        if parts:
            out.append({"role": msg.role, "content": parts})

    return out


def _from_responses_output(resp) -> tuple[Message, list[ToolUseBlock]]:
    """Parse Responses .output[] into Claw-Eval Message + tool_uses."""
    text_chunks: list[str] = []
    tool_uses: list[ToolUseBlock] = []

    output = getattr(resp, "output", None) or []
    for item in output:
        itype = getattr(item, "type", None)
        if itype == "message":
            for part in getattr(item, "content", []) or []:
                ptype = getattr(part, "type", None)
                if ptype in ("output_text", "text"):
                    t = getattr(part, "text", "") or ""
                    if t:
                        text_chunks.append(t)
        elif itype == "function_call":
            try:
                args = json.loads(getattr(item, "arguments", "") or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_name = getattr(item, "name", "")
            tool_uses.append(ToolUseBlock(
                id=getattr(item, "call_id", f"toolu_{uuid4().hex[:12]}"),
                name=tool_name,
                input=_coerce_tool_input(tool_name, args),
            ))

    # Fall back to convenience property if structured parse turned up empty
    if not text_chunks:
        ot = getattr(resp, "output_text", None)
        if ot:
            text_chunks.append(ot)

    blocks = []
    if text_chunks:
        blocks.append(TextBlock(text="\n".join(text_chunks)))
    blocks.extend(tool_uses)
    return Message(role="assistant", content=blocks), tool_uses


class OpenAIResponsesProvider:
    """Calls /v1/responses on an OpenAI-compatible Responses endpoint."""

    def __init__(
        self,
        model_id: str = "gpt-5",
        api_key: str | None = None,
        base_url: str | None = None,
        extra_body: dict | None = None,
        temperature: float | None = 0.0,
        reasoning_effort: str | None = None,
        max_retries: int | None = None,
    ) -> None:
        self.model_id = model_id
        self.extra_body = extra_body or {}
        self.temperature = temperature
        self.reasoning_effort = reasoning_effort
        self.max_retries = _normalize_max_retries(max_retries)
        resolved_key = api_key or os.environ.get("OPENAI_API_KEY") or "unused"
        self.client = OpenAI(api_key=resolved_key, base_url=base_url)

    def chat(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
    ) -> tuple[Message, TokenUsage]:
        input_items = _messages_to_responses_input(messages)
        responses_tools = [_tool_spec_to_responses(t) for t in (tools or [])]
        request_extra_body = dict(self.extra_body or {})
        max_output_tokens = _pop_required_positive_int(request_extra_body, "max_output_tokens")

        kwargs: dict[str, Any] = {
            "model": self.model_id,
            "input": input_items,
            "max_output_tokens": max_output_tokens,
        }
        if responses_tools:
            kwargs["tools"] = responses_tools
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        if self.reasoning_effort:
            kwargs["reasoning"] = {"effort": self.reasoning_effort}
        if request_extra_body:
            kwargs["extra_body"] = request_extra_body

        max_retries = _normalize_max_retries(getattr(self, "max_retries", None))
        last_exc: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                resp = self.client.responses.create(**kwargs)
                msg, _ = _from_responses_output(resp)
                usage_obj = getattr(resp, "usage", None)
                usage = TokenUsage(
                    input_tokens=getattr(usage_obj, "input_tokens", 0) or 0,
                    output_tokens=getattr(usage_obj, "output_tokens", 0) or 0,
                )
                return msg, usage
            except Exception as exc:
                last_exc = exc
                status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
                exc_str = str(exc).lower()
                retryable = (
                    status in (429, 500, 502, 503, 529)
                    or "timeout" in exc_str
                    or "connection" in exc_str
                )
                if not retryable or attempt == max_retries:
                    raise
                delay = random.uniform(2, 4)
                print(f"[responses-retry] ({status or type(exc).__name__}), "
                      f"attempt {attempt + 1}/{max_retries}, waiting {delay:.1f}s ...")
                time.sleep(delay)

        raise last_exc or RuntimeError("All retries exhausted")
