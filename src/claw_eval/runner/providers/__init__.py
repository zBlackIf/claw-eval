"""Model providers — three-protocol dispatch.

v0.30.1 ark overlay (replaces upstream providers/__init__.py).

The provider class is selected by ModelConfig.api_format in config.yaml,
matched against the model_id at construction time. The trick: monkey-patch
the symbol `OpenAICompatProvider` on the `openai_compat` module so that
upstream's `from .runner.providers.openai_compat import OpenAICompatProvider`
in cli.py transparently picks up our dispatcher class — no cli.py overlay
needed.

Default behavior (api_format unset): falls back to the real
OpenAICompatProvider, identical to upstream.
"""

from __future__ import annotations

from . import openai_compat as _openai_compat_mod
from .openai_compat import OpenAICompatProvider as _RealOpenAICompatProvider
from .anthropic_messages import AnthropicMessagesProvider
from .openai_responses import OpenAIResponsesProvider


_OPENAI_LIKE = {None, "", "openai", "openai-completions", "completions", "chat", "chat-completions"}
_RESPONSES = {"openai-responses", "responses"}
_ANTHROPIC = {"anthropic", "anthropic-messages", "messages"}


def _normalize_api_format(raw: str | None) -> str:
    fmt = (raw or "").strip().lower() or None
    if fmt in _ANTHROPIC:
        return "anthropic-messages"
    if fmt in _RESPONSES:
        return "openai-responses"
    return "openai-completions"


def _resolve_model_api_format(model_id: str | None) -> str:
    """Read api_format from the active ModelConfig (set by load_config in cli.py)."""
    try:
        from ...config import get_last_loaded_config
    except ImportError:  # pragma: no cover — defensive only
        return "openai-completions"

    cfg = get_last_loaded_config()
    if cfg is None:
        return "openai-completions"

    if model_id is None:
        return _normalize_api_format(cfg.model.api_format)

    if model_id == cfg.model.model_id and cfg.model.api_format is not None:
        return _normalize_api_format(cfg.model.api_format)
    # When judge==model (smoke runs) judge constructs a provider too in some
    # code paths — fall through to judge.api_format if model side doesn't match.
    if model_id == cfg.judge.model_id and cfg.judge.api_format is not None:
        return _normalize_api_format(cfg.judge.api_format)
    return "openai-completions"


def get_provider(
    model_id: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    **kwargs,
):
    """Construct the provider whose protocol matches the loaded config.yaml."""
    fmt = _resolve_model_api_format(model_id)
    if fmt == "anthropic-messages":
        return AnthropicMessagesProvider(model_id=model_id, api_key=api_key, base_url=base_url, **kwargs)
    if fmt == "openai-responses":
        return OpenAIResponsesProvider(model_id=model_id, api_key=api_key, base_url=base_url, **kwargs)
    return _RealOpenAICompatProvider(model_id=model_id, api_key=api_key, base_url=base_url, **kwargs)


class _DispatchingOpenAICompatProvider:
    """Smart shim that keeps the upstream class name.

    cli.py constructs `OpenAICompatProvider(model_id=..., api_key=..., ...)`
    in 4 places. Replacing the class symbol with this shim means each call
    transparently routes to the right provider for the configured api_format.
    """

    def __new__(cls, *args, **kwargs):
        # cli.py always uses kwargs; positional args path is here for safety
        model_id = kwargs.get("model_id")
        if model_id is None and args:
            model_id = args[0]
        fmt = _resolve_model_api_format(model_id)
        if fmt == "anthropic-messages":
            return AnthropicMessagesProvider(*args, **kwargs)
        if fmt == "openai-responses":
            return OpenAIResponsesProvider(*args, **kwargs)
        return _RealOpenAICompatProvider(*args, **kwargs)


# v0.30.1: rebind the symbol on the openai_compat module itself.
# Subsequent `from .runner.providers.openai_compat import OpenAICompatProvider`
# in cli.py picks up our dispatcher. Direct reads of
# `_openai_compat_mod._RealOpenAICompatProvider` (we keep the real class
# under its original name in this package) still work for our shim.
_openai_compat_mod.OpenAICompatProvider = _DispatchingOpenAICompatProvider


# Re-exports for symmetry / external callers
OpenAICompatProvider = _DispatchingOpenAICompatProvider

__all__ = [
    "OpenAICompatProvider",
    "AnthropicMessagesProvider",
    "OpenAIResponsesProvider",
    "get_provider",
]
