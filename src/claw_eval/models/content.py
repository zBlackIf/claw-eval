"""Typed content blocks matching Anthropic Messages API.

v0.30.7 ark overlay: add Anthropic extended-thinking blocks so provider
responses can be persisted in traces and replayed in later turns.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field


class TextBlock(BaseModel):
    type: Literal["text"] = "text"
    text: str


class ThinkingBlock(BaseModel):
    type: Literal["thinking"] = "thinking"
    thinking: str
    signature: str | None = None


class RedactedThinkingBlock(BaseModel):
    type: Literal["redacted_thinking"] = "redacted_thinking"
    data: str


class ToolUseBlock(BaseModel):
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: dict[str, Any] = Field(default_factory=dict)


class ToolResultBlock(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: list[TextBlock] = Field(default_factory=list)
    is_error: bool = False


class ImageBlock(BaseModel):
    type: Literal["image"] = "image"
    data: str
    mime_type: str
    source_path: str | None = None


class AudioBlock(BaseModel):
    type: Literal["audio"] = "audio"
    data: str
    mime_type: str
    source_path: str | None = None


class VideoBlock(BaseModel):
    type: Literal["video"] = "video"
    data: str
    mime_type: str
    source_path: str | None = None


ContentBlock = Annotated[
    Union[
        TextBlock,
        ThinkingBlock,
        RedactedThinkingBlock,
        ToolUseBlock,
        ToolResultBlock,
        ImageBlock,
        AudioBlock,
        VideoBlock,
    ],
    Field(discriminator="type"),
]
