"""Test for SSE chat streaming."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import Response

from app.api.routers.chat import chat_with_novel


class FakeAsyncIterator:
    """Simulates upstream SSE lines from LangChain."""

    def __init__(self, lines):
        self.lines = iter(lines)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.lines)
        except StopIteration:
            raise StopAsyncIteration


UPSTREAM_SSE_LINES = [
    "data: 你好！",
    "data: 根据",
    "data: 你",
    "data: 提供的",
    "data: 小说",
    "data: 内容",
    "data: 摘要",
    "data: ，",
    "data: 我",
    "data: 已",
    "data: 了解。",
    "",  # empty line (SSE separator)
    "data: [DONE]",
]

EXPECTED_CLEAN_OUTPUT = [
    "你好！",
    "根据",
    "你",
    "提供的",
    "小说",
    "内容",
    "摘要",
    "，",
    "我",
    "已",
    "了解。",
]


def test_description():
    """
    BUG REPORT:
    When using /chat endpoint, the frontend displays:
    "你好！data: 根据data: 你data: 提供的data: 小说data: 内容..."

    The upstream LangChain SSE service returns standard SSE format with
    "data: " prefix on each line. Our proxy endpoint blindly forwards these
    lines without stripping the SSE "data: " prefix, causing the frontend
    to display the raw SSE framing as visible text.

    EXPECTED: The proxy should strip "data: " prefix from upstream SSE lines
    before forwarding to the client, so the frontend receives clean text tokens.
    """
    pass
