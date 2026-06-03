"""Message with content blocks, matching Anthropic Messages API.

v0.50.14 ark overlay: ``model_config = ConfigDict(extra="allow")`` lets the
OpenAI-compatible provider attach a ``provider_response_id`` (the response
``id`` == ARK ``x-request-id``) onto an assistant Message for allow-listed
models only. Because it is an *extra* field (not a declared one), it serializes
into the JSONL trace solely when set — every other model's message stays
byte-identical. See docs/v0.50/v0.50.14-save-provider-request-id-plan.md.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .content import ContentBlock, TextBlock


class Message(BaseModel):
    # v0.50.14: allow the provider to stamp `provider_response_id` on assistant
    # responses for selected models without polluting other models' traces.
    model_config = ConfigDict(extra="allow")

    role: Literal["user", "assistant", "system"]
    content: list[ContentBlock] = Field(default_factory=list)
    reasoning_content: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_str_content(cls, values: dict) -> dict:
        """Allow constructing with content='string' for convenience."""
        c = values.get("content")
        if isinstance(c, str):
            values["content"] = [TextBlock(text=c).model_dump()]
        return values

    @property
    def text(self) -> str:
        """Concatenate all TextBlock content."""
        return "\n".join(b.text for b in self.content if hasattr(b, "text") and b.type == "text")
