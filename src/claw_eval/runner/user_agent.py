"""Simulated user agent with Ark protocol dispatch and fail-fast errors.

v0.30.9 ark overlay. Upstream returned ``None`` after provider retry
exhaustion, which the outer loop interpreted as an explicit ``[DONE]`` from
the simulated user. This overlay preserves ``None`` exclusively for real
``[DONE]`` responses and raises a structured error for provider failures.
"""

from __future__ import annotations

import random
import time
from typing import Any

from ..models.content import TextBlock
from ..models.message import Message


_SYSTEM_PROMPT = """\
你是一个模拟用户。你的任务是根据以下人设与AI助手进行对话。

## 你的人设
{persona}

## 规则
1. 始终保持人设角色，用自然口语回复，不要暴露你是AI
2. 根据助手的提问如实回答（基于你的人设信息）
3. 如果助手问了你人设中没有的信息，说"不太清楚具体数字"或类似自然回复
4. 如果助手已经给出了完整的计算结果和建议，且你没有更多问题，输出 [DONE]
5. 如果你对回答满意或助手已充分回答了你的问题，输出 [DONE]
6. 回复要简短自然，像真实用户一样（1-3句话）
"""


_OPENAI_LIKE = {None, "", "openai", "openai-completions", "completions", "chat", "chat-completions"}
_RESPONSES = {"openai-responses", "responses"}
_ANTHROPIC = {"anthropic", "anthropic-messages", "messages"}


def _normalize_api_format(raw: str | None) -> str:
    fmt = (raw or "").strip().lower() or None
    if fmt in _ANTHROPIC:
        return "anthropic-messages"
    if fmt in _RESPONSES:
        return "openai-responses"
    if fmt in _OPENAI_LIKE:
        return "openai-completions"
    return "openai-completions"


def _format_transcript(messages: list[Message]) -> str:
    """Format conversation messages into a readable transcript."""
    lines = []
    for msg in messages:
        if msg.role == "system":
            continue
        text = msg.text
        if not text:
            continue
        if msg.role == "user":
            if text.startswith("[user_agent]"):
                text = text[len("[user_agent]"):].strip()
            lines.append(f"[用户]: {text}")
        elif msg.role == "assistant":
            lines.append(f"[助手]: {text}")
    return "\n".join(lines)


class UserAgentProviderExhaustedError(RuntimeError):
    """Raised when the simulated user model fails all retry attempts."""


def _loaded_user_agent_config(model_id: str) -> dict[str, Any]:
    try:
        from ..config import get_last_loaded_config
    except ImportError:
        return {}

    cfg = get_last_loaded_config()
    if cfg is None:
        return {}
    ua_cfg = getattr(cfg, "user_agent_model", None)
    if ua_cfg is None:
        return {}
    if getattr(ua_cfg, "model_id", None) != model_id:
        return {}
    return {
        "api_format": getattr(ua_cfg, "api_format", None),
        "extra_body": getattr(ua_cfg, "extra_body", None),
        "temperature": getattr(ua_cfg, "temperature", 0.7),
    }


def _make_provider(
    *,
    model_id: str,
    api_key: str,
    base_url: str,
    api_format: str,
    extra_body: dict | None,
    temperature: float | None,
):
    if api_format == "anthropic-messages":
        from .providers.anthropic_messages import AnthropicMessagesProvider

        return AnthropicMessagesProvider(
            model_id=model_id,
            api_key=api_key,
            base_url=base_url,
            extra_body=extra_body,
            temperature=temperature,
        )
    if api_format == "openai-responses":
        from .providers.openai_responses import OpenAIResponsesProvider

        return OpenAIResponsesProvider(
            model_id=model_id,
            api_key=api_key,
            base_url=base_url,
            extra_body=extra_body,
            temperature=temperature,
        )

    from .providers.openai_compat import OpenAICompatProvider

    return OpenAICompatProvider(
        model_id=model_id,
        api_key=api_key,
        base_url=base_url,
        extra_body=extra_body,
        temperature=temperature,
    )


class UserAgent:
    """Simulated user that generates responses via an LLM."""

    def __init__(
        self,
        model_id: str,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
    ) -> None:
        cfg = _loaded_user_agent_config(model_id)
        self.model_id = model_id
        self.base_url = base_url
        self.api_format = _normalize_api_format(cfg.get("api_format"))
        self.provider = _make_provider(
            model_id=model_id,
            api_key=api_key,
            base_url=base_url,
            api_format=self.api_format,
            extra_body=cfg.get("extra_body") if isinstance(cfg.get("extra_body"), dict) else None,
            temperature=cfg.get("temperature") if "temperature" in cfg else 0.7,
        )

    def generate_response(
        self,
        persona: str,
        conversation_messages: list[Message],
    ) -> str | None:
        """Generate a simulated user reply.

        Returns reply text, or None only when the model explicitly emits
        ``[DONE]``.
        """
        system = _SYSTEM_PROMPT.format(persona=persona)
        transcript = _format_transcript(conversation_messages)
        user_msg = (
            f"以下是到目前为止的对话：\n\n{transcript}\n\n"
            "请根据你的人设回复助手的最新消息。如果你满意了就输出 [DONE]。"
        )
        messages = [
            Message(role="system", content=[TextBlock(text=system)]),
            Message(role="user", content=[TextBlock(text=user_msg)]),
        ]

        max_retries = 30
        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                msg, _usage = self.provider.chat(messages)
                text = (msg.text or "").strip()
                if "[DONE]" in text:
                    return None
                if text:
                    return text
                raise RuntimeError("empty user-agent response")
            except Exception as exc:
                last_exc = exc
                delay = min(2 ** (attempt + 1), 16) + random.uniform(0, 1)
                print(
                    f"[user-agent-retry] {type(exc).__name__}, "
                    f"attempt {attempt + 1}/{max_retries}, waiting {delay:.1f}s ..."
                )
                if attempt < max_retries - 1:
                    time.sleep(delay)

        exc_type = type(last_exc).__name__ if last_exc is not None else "UnknownError"
        raise UserAgentProviderExhaustedError(
            "UserAgentProviderExhaustedError: "
            f"model={self.model_id} api_format={self.api_format} "
            f"endpoint={self.base_url} exception={exc_type}"
        ) from last_exc
