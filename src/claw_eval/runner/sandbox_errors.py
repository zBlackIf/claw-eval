"""Structured sandbox infrastructure failures.

Ark overlay marker: sandbox_identity_mismatch.
"""

from __future__ import annotations

from typing import Any

from ..models.trace import ToolDispatch


class SandboxInfraError(ConnectionError):
    """Failure in sandbox infrastructure, not in the evaluated model output."""

    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        diagnostics: dict[str, Any] | None = None,
        dispatch_event: ToolDispatch | None = None,
    ) -> None:
        super().__init__(f"{error_code}: {message}")
        self.error_code = error_code
        self.message = message
        self.diagnostics = diagnostics or {}
        self.dispatch_event = dispatch_event

