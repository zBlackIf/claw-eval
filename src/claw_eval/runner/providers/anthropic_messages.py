"""Anthropic Messages provider for Claw-Eval.

v0.30.12 ark overlay (new file). Implements the same chat() contract as
OpenAICompatProvider so runner/loop.py can swap providers transparently.

The module-level get_provider() / dispatch is in providers/__init__.py;
this file just defines the provider class.
"""

from __future__ import annotations

import json
import random
import time
from typing import Any
from uuid import uuid4

import httpx

from ...models.content import (
    ImageBlock,
    RedactedThinkingBlock,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)
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
            f"Claw-Eval anthropic-messages provider requires extra_body.{field}; "
            "configure maxTokens / Max Output Tokens in the model config."
        )
    raw_value = values.pop(field)
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Claw-Eval anthropic-messages provider requires positive integer extra_body.{field}; "
            "configure maxTokens / Max Output Tokens in the model config."
        ) from exc
    if value <= 0:
        raise ValueError(
            f"Claw-Eval anthropic-messages provider requires positive integer extra_body.{field}; "
            "configure maxTokens / Max Output Tokens in the model config."
        )
    return value


def _normalize_anthropic_base_url(base_url: str | None) -> str | None:
    """Anthropic SDK appends /v1/messages itself — strip /v1 suffix if present."""
    if not base_url:
        return None
    u = base_url.rstrip("/")
    if u.endswith("/v1"):
        u = u[:-3].rstrip("/")
    return u or None


def _tool_spec_to_anthropic(spec: ToolSpec) -> dict[str, Any]:
    """ToolSpec -> Anthropic tool format (1:1 mapping)."""
    return {
        "name": spec.name,
        "description": spec.description,
        "input_schema": spec.input_schema or {"type": "object", "properties": {}},
    }


def _block_get(block: Any, key: str, default: Any = None) -> Any:
    if isinstance(block, dict):
        return block.get(key, default)
    return getattr(block, key, default)


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


def _split_system(messages: list[Message]) -> tuple[str, list[Message]]:
    """Anthropic puts system as a top-level param, not a message role.

    Concatenate any leading role=='system' messages and return the rest.
    """
    system_parts: list[str] = []
    rest: list[Message] = []
    for m in messages:
        if m.role == "system":
            system_parts.extend(b.text for b in m.content if b.type == "text")
        else:
            rest.append(m)
    return "\n\n".join(p for p in system_parts if p), rest


def _block_to_anthropic(block) -> dict[str, Any] | None:
    """Convert a single Claw-Eval ContentBlock to an Anthropic content block."""
    btype = block.type
    if btype == "text":
        return {"type": "text", "text": block.text}
    if btype == "thinking":
        b = block if isinstance(block, ThinkingBlock) else ThinkingBlock.model_validate(block)
        out = {"type": "thinking", "thinking": b.thinking}
        if b.signature is not None:
            out["signature"] = b.signature
        return out
    if btype == "redacted_thinking":
        b = block if isinstance(block, RedactedThinkingBlock) else RedactedThinkingBlock.model_validate(block)
        return {"type": "redacted_thinking", "data": b.data}
    if btype == "tool_use":
        # Claw-Eval ToolUseBlock: id, name, input — same shape
        return {
            "type": "tool_use",
            "id": block.id,
            "name": block.name,
            "input": block.input or {},
        }
    if btype == "tool_result":
        inner_text = "\n".join(t.text for t in block.content) if block.content else ""
        return {
            "type": "tool_result",
            "tool_use_id": block.tool_use_id,
            "content": [{"type": "text", "text": inner_text}],
            "is_error": bool(block.is_error),
        }
    if btype == "image":
        b = block if isinstance(block, ImageBlock) else ImageBlock.model_validate(block)
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": b.mime_type,
                "data": b.data,
            },
        }
    if btype in ("audio", "video"):
        # Anthropic Messages doesn't natively support audio/video — emit text marker
        return {
            "type": "text",
            "text": f"[{btype} attached: {getattr(block, 'mime_type', '?')}; not supported by Anthropic Messages]",
        }
    return None


def _message_to_anthropic(msg: Message) -> dict[str, Any]:
    """Claw-Eval Message -> Anthropic message dict."""
    blocks = []
    for b in msg.content:
        ab = _block_to_anthropic(b)
        if ab is not None:
            blocks.append(ab)
    return {"role": msg.role, "content": blocks or [{"type": "text", "text": ""}]}


def _from_anthropic_response(resp) -> Message:
    """Anthropic response -> Claw-Eval Message with ContentBlock[]."""
    out_blocks = []
    for block in resp.content or []:
        btype = _block_get(block, "type")
        if btype == "text":
            text = _block_get(block, "text", "") or ""
            if text:
                out_blocks.append(TextBlock(text=text))
        elif btype == "thinking":
            out_blocks.append(ThinkingBlock(
                thinking=_block_get(block, "thinking", "") or "",
                signature=_block_get(block, "signature"),
            ))
        elif btype == "redacted_thinking":
            out_blocks.append(RedactedThinkingBlock(
                data=_block_get(block, "data", "") or "",
            ))
        elif btype == "tool_use":
            tool_name = _block_get(block, "name", "")
            out_blocks.append(ToolUseBlock(
                id=_block_get(block, "id", f"toolu_{uuid4().hex[:12]}"),
                name=tool_name,
                input=_coerce_tool_input(tool_name, _block_get(block, "input", {})),
            ))
    return Message(role="assistant", content=out_blocks)


class AnthropicProviderExhaustedError(RuntimeError):
    """Raised when retryable Anthropic provider failures never recover."""


def _is_retryable_anthropic_error(exc: Exception) -> bool:
    if isinstance(exc, json.JSONDecodeError):
        return True
    if isinstance(exc, (httpx.RemoteProtocolError, httpx.ReadError, httpx.TimeoutException)):
        return True

    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    try:
        status_int = int(status)
    except (TypeError, ValueError):
        status_int = None
    if status_int in (429, 500, 502, 503, 529):
        return True

    exc_str = str(exc).lower()
    retryable_needles = (
        "timeout",
        "connection",
        "overloaded",
        "expecting value",
        "jsondecodeerror",
        "invalid json",
        "non-json",
        "non json",
        "empty response",
        "empty body",
        "remote protocol",
        "server disconnected",
        "peer closed",
    )
    return any(needle in exc_str for needle in retryable_needles)


class AnthropicMessagesProvider:
    """Calls /v1/messages on an Anthropic-compatible endpoint.

    Same chat() signature as OpenAICompatProvider so runner/loop.py is unchanged.
    """

    def __init__(
        self,
        model_id: str = "claude-opus-4-6",
        api_key: str | None = None,
        base_url: str | None = None,
        extra_body: dict | None = None,
        temperature: float | None = 0.0,
        reasoning_effort: str | None = None,
        max_retries: int | None = None,
    ) -> None:
        from anthropic import Anthropic

        self.model_id = model_id
        self.extra_body = extra_body or {}
        self.temperature = temperature
        self.reasoning_effort = reasoning_effort
        self.max_retries = _normalize_max_retries(max_retries)
        normalized = _normalize_anthropic_base_url(base_url)
        self.client = Anthropic(api_key=api_key or "dummy", base_url=normalized)

    def chat(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
    ) -> tuple[Message, TokenUsage]:
        system_msg, conv = _split_system(messages)
        anth_messages = [_message_to_anthropic(m) for m in conv]
        anth_tools = [_tool_spec_to_anthropic(t) for t in (tools or [])]
        request_extra_body = dict(self.extra_body or {})
        max_tokens = _pop_required_positive_int(request_extra_body, "max_tokens")

        kwargs: dict[str, Any] = {
            "model": self.model_id,
            "max_tokens": max_tokens,
            "messages": anth_messages,
        }
        if system_msg:
            kwargs["system"] = system_msg
        if anth_tools:
            kwargs["tools"] = anth_tools
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        if request_extra_body:
            # Pass-through extra body fields (e.g., thinking, anthropic_beta)
            kwargs.update(request_extra_body)

        max_retries = _normalize_max_retries(getattr(self, "max_retries", None))
        max_attempts = max_retries + 1
        last_exc: Exception | None = None
        for attempt in range(max_attempts):
            try:
                with self.client.messages.stream(**kwargs) as stream:
                    resp = stream.get_final_message()
                msg = _from_anthropic_response(resp)
                usage = TokenUsage(
                    input_tokens=getattr(resp.usage, "input_tokens", 0) or 0,
                    output_tokens=getattr(resp.usage, "output_tokens", 0) or 0,
                )
                return msg, usage
            except Exception as exc:
                last_exc = exc
                status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
                retryable = _is_retryable_anthropic_error(exc)
                if not retryable:
                    raise
                if attempt == max_retries:
                    raise AnthropicProviderExhaustedError(
                        f"anthropic messages provider exhausted after {max_attempts} attempts: "
                        f"{type(exc).__name__}: {exc}"
                    ) from exc
                delay = random.uniform(2, 4)
                print(f"[anthropic-retry] ({status or type(exc).__name__}), "
                      f"attempt {attempt + 1}/{max_attempts}, waiting {delay:.1f}s ...")
                time.sleep(delay)

        raise AnthropicProviderExhaustedError(
            f"anthropic messages provider exhausted after {max_attempts} attempts"
        ) from last_exc
