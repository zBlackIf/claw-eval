"""Sandbox-aware tool dispatcher.

Routes sandbox tool calls either:
  - Over HTTP to a remote sandbox container (when *sandbox_url* is provided), OR
  - Locally via subprocess/filesystem (fallback for backward compatibility).

All other tool calls are delegated to the standard HTTP ToolDispatcher.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
from json import JSONDecodeError
import os
import re
import subprocess
import time
from pathlib import Path

from ..models.content import ImageBlock, TextBlock, ToolResultBlock, ToolUseBlock
from ..models.trace import ToolDispatch
from .dispatcher import ToolDispatcher
from .sandbox_errors import SandboxInfraError
from .sandbox_tools import SANDBOX_TOOL_NAMES

# Tools whose responses always contain extractable image frames
_ALWAYS_MEDIA_TOOLS = frozenset({"ReadMedia", "BrowserScreenshot"})
# Tools that conditionally return frames (e.g. Read with image/PDF)
_CONDITIONAL_MEDIA_TOOLS = frozenset({"Read"})

# v0.30.12 ark overlay: lossless artifact staging for oversized sandbox
# outputs, plus recoverable tool-use validation errors.
_MALFORMED_TOOL_INPUT_KEY = "__ark_malformed_tool_input__"
TOOL_CACHE_ROOT = os.environ.get("ARK_CLAW_EVAL_TOOL_CACHE_ROOT", "/workspace/.tool_cache")
MAX_INLINE_TOOL_RESULT_CHARS = int(os.environ.get("ARK_CLAW_EVAL_MAX_INLINE_TOOL_RESULT_CHARS", "30000"))
TOOL_RESULT_PREVIEW_CHARS = int(os.environ.get("ARK_CLAW_EVAL_TOOL_RESULT_PREVIEW_CHARS", "4000"))
MAX_READ_INLINE_CHARS = int(os.environ.get("ARK_CLAW_EVAL_MAX_READ_INLINE_CHARS", "30000"))


def _compress_image_b64(
    data_b64: str, max_dimension: int, quality: int = 60
) -> str:
    """Resize + JPEG-compress a base64-encoded image.

    - Resizes so the longest edge <= *max_dimension* (if needed).
    - Converts to JPEG at the given *quality* (0–100).
    - Handles RGBA / palette images by compositing onto white background.

    Returns the original data unchanged when Pillow is unavailable or
    any decoding/encoding error occurs.
    """
    try:
        from PIL import Image as _PILImage

        raw = base64.b64decode(data_b64)
        img = _PILImage.open(io.BytesIO(raw))
        w, h = img.size

        # Resize if needed
        needs_resize = max_dimension > 0 and max(w, h) > max_dimension
        if needs_resize:
            scale = max_dimension / max(w, h)
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))
            img = img.resize((new_w, new_h), _PILImage.LANCZOS)

        # Convert to RGB for JPEG (handle RGBA, palette, LA, etc.)
        if img.mode not in ("RGB", "L"):
            background = _PILImage.new("RGB", img.size, (255, 255, 255))
            if img.mode in ("RGBA", "LA") or (
                img.mode == "P" and "transparency" in img.info
            ):
                background.paste(img, mask=img.split()[-1])
            else:
                background.paste(img)
            img = background

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return data_b64


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _byte_len(text: str) -> int:
    return len(text.encode("utf-8", errors="replace"))


def _decode_process_output(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.decode("utf-8", errors="replace")


def _safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("_") or "tool"


def _json_type_name(value) -> str:
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


def _preview_payload(text: str) -> dict:
    preview = max(0, TOOL_RESULT_PREVIEW_CHARS)
    if len(text) <= preview:
        return {"preview": text}
    return {
        "preview_head": text[:preview],
        "preview_tail": text[-preview:] if preview else "",
    }


def _read_hint(path: str) -> str:
    return f"Use Read with offset and limit to inspect the full output, e.g. Read(file_path='{path}', offset=1, limit=200)."


class SandboxToolDispatcher:
    """Routes sandbox tools to container HTTP or local fallback; others via HTTP."""

    def __init__(
        self,
        http_dispatcher: ToolDispatcher,
        *,
        sandbox_url: str | None = None,
        sandbox_identity: dict[str, str] | None = None,
        max_images_per_turn: int = 64,
        tool_image_max_dimension: int = 1280,
        tool_image_quality: int = 60,
    ) -> None:
        self._http = http_dispatcher
        self._sandbox_url = sandbox_url
        self._sandbox_identity = sandbox_identity or {}
        self._client = None  # lazy-init httpx client for remote mode
        self._max_per_turn = max_images_per_turn
        self._max_dimension = tool_image_max_dimension
        self._image_quality = tool_image_quality

    # ---- public interface (same signature as ToolDispatcher) ---------------

    def dispatch(
        self, tool_use: ToolUseBlock, trace_id: str
    ) -> tuple[ToolResultBlock, ToolDispatch, list[ImageBlock] | None]:
        malformed = self._malformed_tool_input(tool_use)
        if malformed is not None:
            return self._tool_input_error_result(tool_use, trace_id, malformed)
        if tool_use.name in SANDBOX_TOOL_NAMES:
            return self._dispatch_sandbox(tool_use, trace_id)
        result, event = self._http.dispatch(tool_use, trace_id)
        result = self._apply_generic_output_policy(tool_use, trace_id, result)
        return result, event, None

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
        self._http.close()

    # ---- sandbox routing -------------------------------------------------

    def _dispatch_sandbox(
        self, tool_use: ToolUseBlock, trace_id: str
    ) -> tuple[ToolResultBlock, ToolDispatch, list[ImageBlock] | None]:
        if self._sandbox_url:
            return self._dispatch_remote(tool_use, trace_id)
        return self._dispatch_local(tool_use, trace_id)

    # ---- remote mode: HTTP to container ----------------------------------

    _PATH_MAP = {
        "Bash": "/exec",
        "Read": "/read",
        "Write": "/write",
        "Edit": "/edit",
        "Glob": "/glob",
        "Grep": "/grep",
        "BrowserScreenshot": "/screenshot",
        "ReadMedia": "/read_media",
        "Download": "/download",
    }

    def _get_client(self):
        if self._client is None:
            import httpx
            self._client = httpx.Client(timeout=120.0)
        return self._client

    # v0.50.11：host→容器 transport 超时必须 ≥ 容器内命令超时(min(req,900))+缓冲。否则模型跑的
    # 长命令(build/test >120s)会被 host 固定 120s ReadTimeout 截断 → 误判 sandbox_transport infra
    # 污染(把模型正常行为当评测故障，还提前掐断了可能成功的命令)。放宽后容器内"优雅命令超时"先触发，
    # 把"Timed out after Ns"作为正常 tool 结果回给模型，正常计入评分。真正的 transport 故障(连接
    # 重置/断开)走连接错误、不受此影响仍会 taint。见 v0.50.11 acceptance issues（R2-E2/R3-E2）。
    _SANDBOX_CMD_TIMEOUT_CAP_S = 900   # 容器 sandbox_server shell exec 上限 min(timeout,900)
    _SANDBOX_TRANSPORT_BUFFER_S = 60

    def _request_timeout_for(self, tool_use, payload: dict) -> float:
        """命令类工具(Bash/shell)：host 等到容器自身命令超时之后再放弃；其余工具保留 120s。"""
        is_cmd = getattr(tool_use, "name", "") == "Bash" or "command" in (payload or {})
        if not is_cmd:
            return 120.0
        raw = (payload or {}).get("timeout_seconds")
        try:
            cmd_to = int(raw) if raw is not None else 30
        except (TypeError, ValueError):
            cmd_to = 30
        cmd_to = max(1, min(cmd_to, self._SANDBOX_CMD_TIMEOUT_CAP_S))
        return float(cmd_to + self._SANDBOX_TRANSPORT_BUFFER_S)

    def _identity_headers(self) -> dict[str, str]:
        if not self._sandbox_identity:
            return {}
        headers: dict[str, str] = {}
        run_id = self._sandbox_identity.get("run_id")
        task_id = self._sandbox_identity.get("task_id")
        token = self._sandbox_identity.get("token")
        if run_id:
            headers["X-Claw-Sandbox-Run-Id"] = run_id
        if task_id:
            headers["X-Claw-Sandbox-Task-Id"] = task_id
        if token:
            headers["X-Claw-Sandbox-Token"] = token
        return headers

    @staticmethod
    def _is_infra_body(status_code: int, body) -> bool:
        if not isinstance(body, dict):
            return status_code >= 500
        error_code = str(body.get("error_code") or "")
        return (
            bool(body.get("infra_error"))
            or error_code.startswith("sandbox_")
            or status_code >= 500
        )

    @staticmethod
    def _translate_payload(tool_use: ToolUseBlock) -> dict:
        """Translate client-facing param names to server-side param names."""
        payload = dict(tool_use.input)
        if tool_use.name == "Bash":
            if "timeout" in payload:
                payload["timeout_seconds"] = max(1, payload.pop("timeout") // 1000)
            payload.pop("description", None)
            payload.pop("run_in_background", None)
        elif tool_use.name in ("Read", "Write", "Edit"):
            if "file_path" in payload:
                payload["path"] = payload.pop("file_path")
        elif tool_use.name == "Grep":
            # Translate Claude Code param names to server grep params
            if "case_insensitive" in payload:
                payload["case_insensitive"] = payload.pop("case_insensitive")
            if "context_lines" in payload:
                payload["context_lines"] = payload.pop("context_lines")
            if "after_context" in payload:
                payload["after_context"] = payload.pop("after_context")
            if "before_context" in payload:
                payload["before_context"] = payload.pop("before_context")
        return payload

    def _dispatch_remote(
        self, tool_use: ToolUseBlock, trace_id: str
    ) -> tuple[ToolResultBlock, ToolDispatch, list[ImageBlock] | None]:
        schema_error = self._validate_tool_use(tool_use)
        if schema_error is not None:
            return self._tool_input_error_result(tool_use, trace_id, schema_error)

        path = self._PATH_MAP.get(tool_use.name)
        if not path:
            return self._error_result(
                tool_use, trace_id,
                f"Unknown sandbox tool: {tool_use.name}",
                status=404,
            )

        endpoint_url = f"{self._sandbox_url}{path}"
        payload = self._translate_payload(tool_use)
        request_timeout = self._request_timeout_for(tool_use, payload)
        t0 = time.monotonic()
        try:
            client = self._get_client()
            resp = client.post(
                endpoint_url,
                json=payload,
                headers=self._identity_headers(),
                timeout=request_timeout,
            )
            latency_ms = (time.monotonic() - t0) * 1000
            body = resp.json()
            is_error = resp.status_code >= 400
        except Exception as exc:
            latency_ms = (time.monotonic() - t0) * 1000
            status = 500 if isinstance(exc, JSONDecodeError) else 599
            # v0.50.11: the sandbox HTTP server dying mid-request — httpx
            # RemoteProtocolError / "server disconnected without sending a response" —
            # while executing the MODEL's tool call on the localhost container
            # connection means the model's own command crashed/exhausted the sandbox
            # (e.g. `ocrmypdf` on a multi-hundred-page PDF blowing past the 1g limit,
            # instead of using the provided ocr_extract_text tool). The intended task
            # path fits well within 1g, and a 127.0.0.1 socket has no network blips, so
            # attribute it to the model: sandbox_oom — a scored model failure, NOT eval
            # infra taint (Docker's OOMKilled flag is unreliable here, so we key off the
            # disconnect itself, not oom_killed). Genuine transport faults (connect
            # refused/reset, errno 104) keep error_code sandbox_transport → infra taint.
            exc_name = type(exc).__name__
            server_died = exc_name == "RemoteProtocolError" or "server disconnected" in str(exc).lower()
            error_code = "sandbox_oom" if server_died else "sandbox_transport"
            dispatch_event = ToolDispatch(
                trace_id=trace_id,
                tool_use_id=tool_use.id,
                tool_name=tool_use.name,
                endpoint_url=endpoint_url,
                request_body=tool_use.input,
                response_status=status,
                response_body={
                    "infra_error": not server_died,
                    "error_code": error_code,
                    "message": str(exc),
                    "exc_type": exc_name,
                },
                latency_ms=latency_ms,
            )
            raise SandboxInfraError(
                error_code,
                str(exc),
                diagnostics={"endpoint_url": endpoint_url, "exc_type": exc_name},
                dispatch_event=dispatch_event,
            )

        dispatch_event = ToolDispatch(
            trace_id=trace_id,
            tool_use_id=tool_use.id,
            tool_name=tool_use.name,
            endpoint_url=endpoint_url,
            request_body=tool_use.input,
            response_status=resp.status_code,
            response_body=body,
            latency_ms=latency_ms,
        )
        if self._is_infra_body(resp.status_code, body):
            if isinstance(body, dict):
                error_code = str(body.get("error_code") or "sandbox_transport")
                message = str(body.get("message") or body.get("error") or body)
                diagnostics = dict(body.get("diagnostics") or {})
            else:
                error_code = "sandbox_transport"
                message = str(body)
                diagnostics = {}
            raise SandboxInfraError(
                error_code,
                message,
                diagnostics=diagnostics,
                dispatch_event=dispatch_event,
            )

        # Extract images from media tool responses
        extra_images: list[ImageBlock] | None = None
        is_media_response = (
            tool_use.name in _ALWAYS_MEDIA_TOOLS
            or (tool_use.name in _CONDITIONAL_MEDIA_TOOLS and "frames" in body)
        )
        if is_media_response and not is_error:
            extra_images = []
            frames = body.get("frames", [])
            valid_frames = [f for f in frames if "image_b64" in f]
            total_available = len(valid_frames)
            budget = self._max_per_turn

            # Uniform sampling when more frames than budget
            if total_available <= budget:
                selected = valid_frames
            else:
                indices = [int(i * total_available / budget) for i in range(budget)]
                selected = [valid_frames[idx] for idx in indices]

            for frame in selected:
                compressed = _compress_image_b64(
                    frame["image_b64"], self._max_dimension, self._image_quality,
                )
                extra_images.append(ImageBlock(
                    data=compressed,
                    mime_type="image/jpeg",
                ))

            # Strip base64 data from text summary to save tokens
            summary_body = {k: v for k, v in body.items() if k != "frames"}
            summary_body["frame_count"] = total_available
            summary_body["frames_shown"] = len(selected)
            if total_available > len(selected):
                summary_body["sampling"] = f"uniform ({len(selected)} of {total_available})"
            text_content = json.dumps(summary_body, ensure_ascii=False)
            if not extra_images:
                extra_images = None
        else:
            body = self._apply_output_policy(tool_use, trace_id, body, remote=True)
            dispatch_event.response_body = body
            text_content = json.dumps(body, ensure_ascii=False)

        result = ToolResultBlock(
            tool_use_id=tool_use.id,
            content=[TextBlock(text=text_content)],
            is_error=is_error,
        )
        return result, dispatch_event, extra_images

    # ---- local mode: subprocess/filesystem (backward compat) -------------

    _LOCAL_HANDLERS: dict[str, str] = {
        "Bash": "_handle_shell_exec",
        "Read": "_handle_file_read",
        "Write": "_handle_file_write",
        "Edit": "_handle_edit",
        "Glob": "_handle_glob",
        "Grep": "_handle_grep",
        "BrowserScreenshot": "_handle_browser_screenshot",
        "ReadMedia": "_handle_not_available",
        "Download": "_handle_not_available",
    }

    def _dispatch_local(
        self, tool_use: ToolUseBlock, trace_id: str
    ) -> tuple[ToolResultBlock, ToolDispatch, list[ImageBlock] | None]:
        schema_error = self._validate_tool_use(tool_use)
        if schema_error is not None:
            return self._tool_input_error_result(tool_use, trace_id, schema_error)

        handler_name = self._LOCAL_HANDLERS.get(tool_use.name)
        if handler_name is None:
            return self._error_result(
                tool_use, trace_id,
                f"Unknown sandbox tool: {tool_use.name}",
                status=404,
            )

        handler = getattr(self, handler_name)
        t0 = time.monotonic()
        try:
            body = handler(tool_use.input)
            body = self._apply_output_policy(tool_use, trace_id, body, remote=False)
            latency_ms = (time.monotonic() - t0) * 1000
            content_text = json.dumps(body, ensure_ascii=False) if isinstance(body, dict) else str(body)
            result = ToolResultBlock(
                tool_use_id=tool_use.id,
                content=[TextBlock(text=content_text)],
                is_error=False,
            )
            dispatch_event = ToolDispatch(
                trace_id=trace_id,
                tool_use_id=tool_use.id,
                tool_name=tool_use.name,
                endpoint_url=f"local://sandbox/{tool_use.name}",
                request_body=tool_use.input,
                response_status=200,
                response_body=body,
                latency_ms=latency_ms,
            )
        except Exception as exc:
            latency_ms = (time.monotonic() - t0) * 1000
            return self._error_result(
                tool_use, trace_id, str(exc),
                status=500, latency_ms=latency_ms,
            )

        return result, dispatch_event, None

    # ---- local handlers --------------------------------------------------

    @staticmethod
    def _handle_shell_exec(inp: dict) -> dict:
        command = inp["command"]
        # Accept timeout in ms (Claude Code style) or seconds (legacy)
        timeout_ms = inp.get("timeout")
        if timeout_ms is not None:
            timeout = max(1, timeout_ms // 1000)
        else:
            timeout = inp.get("timeout_seconds", 30)
        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=False,
                timeout=timeout,
            )
            return {
                "exit_code": proc.returncode,
                "stdout": _decode_process_output(proc.stdout),
                "stderr": _decode_process_output(proc.stderr),
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
            }

    @staticmethod
    def _handle_file_read(inp: dict) -> dict:
        raw_path = inp.get("file_path") or inp.get("path")
        if not raw_path:
            return {"error": "Missing file_path or path parameter."}
        path = Path(raw_path)
        if not path.exists():
            return {"error": f"File not found: {path}"}
        content = path.read_text(encoding="utf-8", errors="replace")
        offset = inp.get("offset")
        limit = inp.get("limit")
        if offset is not None or limit is not None:
            lines = content.splitlines(keepends=True)
            start = (offset - 1) if offset and offset >= 1 else 0
            end = (start + limit) if limit else len(lines)
            selected = lines[start:end]
            # Format with cat -n style line numbers
            numbered = []
            for i, line in enumerate(selected, start=start + 1):
                numbered.append(f"     {i}\t{line.rstrip()}")
            return {"content": "\n".join(numbered)}
        return {"content": content}

    @staticmethod
    def _handle_file_write(inp: dict) -> dict:
        raw_path = inp.get("file_path") or inp.get("path")
        if not raw_path:
            return {"error": "Missing file_path or path parameter."}
        path = Path(raw_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(inp["content"], encoding="utf-8")
        return {"written": str(path), "bytes": len(inp["content"])}

    @staticmethod
    def _handle_edit(inp: dict) -> dict:
        raw_path = inp.get("file_path") or inp.get("path")
        if not raw_path:
            return {"error": "Missing file_path or path parameter."}
        path = Path(raw_path)
        if not path.exists():
            return {"error": f"File not found: {path}"}
        content = path.read_text(encoding="utf-8", errors="replace")
        old_string = inp["old_string"]
        new_string = inp["new_string"]
        replace_all = inp.get("replace_all", False)
        count = content.count(old_string)
        if count == 0:
            return {"error": f"old_string not found in {path}"}
        if count > 1 and not replace_all:
            return {"error": f"old_string found {count} times in {path}. Use replace_all=true to replace all."}
        if replace_all:
            new_content = content.replace(old_string, new_string)
        else:
            new_content = content.replace(old_string, new_string, 1)
        path.write_text(new_content, encoding="utf-8")
        return {"edited": str(path), "replacements": count if replace_all else 1}

    @staticmethod
    def _handle_glob(inp: dict) -> dict:
        import glob as _glob
        pattern = inp["pattern"]
        base_path = inp.get("path")
        if base_path:
            full_pattern = str(Path(base_path) / pattern)
        else:
            full_pattern = pattern
        matches = sorted(_glob.glob(full_pattern, recursive=True))
        files = [m for m in matches[:50] if Path(m).is_file()]
        return {"files": files}

    @staticmethod
    def _handle_grep(inp: dict) -> dict:
        pattern = inp["pattern"]
        path = inp.get("path", ".")
        cmd = ["grep", "-rP"]
        if inp.get("case_insensitive"):
            cmd.append("-i")
        output_mode = inp.get("output_mode", "files_with_matches")
        if output_mode == "files_with_matches":
            cmd.append("-l")
        elif output_mode == "count":
            cmd.append("-c")
        context = inp.get("context_lines")
        if context:
            cmd.extend(["-C", str(context)])
        after = inp.get("after_context")
        if after:
            cmd.extend(["-A", str(after)])
        before = inp.get("before_context")
        if before:
            cmd.extend(["-B", str(before)])
        glob_filter = inp.get("glob")
        if glob_filter:
            cmd.extend(["--include", glob_filter])
        head_limit = inp.get("head_limit")
        cmd.extend([pattern, path])
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=False, timeout=30,
            )
            output = _decode_process_output(proc.stdout)
            if head_limit and head_limit > 0:
                lines = output.splitlines()[:head_limit]
                output = "\n".join(lines)
            return {"output": output, "exit_code": proc.returncode}
        except subprocess.TimeoutExpired:
            return {"error": "Grep timed out after 30s"}

    @staticmethod
    def _handle_browser_screenshot(inp: dict) -> dict:
        url = inp["url"]
        try:
            from playwright.sync_api import sync_playwright  # type: ignore[import-untyped]
        except ImportError:
            return {
                "error": "playwright is not installed. "
                "Install with: pip install playwright && playwright install chromium",
                "url": url,
            }

        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1280, "height": 720})
                page.goto(url, wait_until="networkidle", timeout=30_000)
                title = page.title()
                text = page.inner_text("body")[:2000]
                browser.close()
            return {"url": url, "title": title, "body_text": text}
        except Exception as exc:
            return {"error": str(exc), "url": url}

    # ---- local-only fallback for media tools ----------------------------

    @staticmethod
    def _handle_not_available(inp: dict) -> dict:
        return {
            "error": "This tool requires a remote sandbox container (--sandbox mode).",
        }

    # ---- helpers ---------------------------------------------------------

    @staticmethod
    def _malformed_tool_input(tool_use: ToolUseBlock) -> dict | None:
        marker = tool_use.input.get(_MALFORMED_TOOL_INPUT_KEY)
        return marker if isinstance(marker, dict) else None

    @staticmethod
    def _validate_tool_use(tool_use: ToolUseBlock) -> dict | None:
        def missing(param: str) -> dict:
            return {
                "tool_name": tool_use.name,
                "input_type": "object",
                "message": f"The parameter `{param}` is required and must be a string.",
            }

        def not_string(param: str) -> dict:
            return {
                "tool_name": tool_use.name,
                "input_type": _json_type_name(tool_use.input.get(param)),
                "message": f"The parameter `{param}` must be a string.",
            }

        if tool_use.name == "Bash":
            value = tool_use.input.get("command")
            if value is None:
                return missing("command")
            if not isinstance(value, str):
                return not_string("command")
        elif tool_use.name == "Grep":
            value = tool_use.input.get("pattern")
            if value is None:
                return missing("pattern")
            if not isinstance(value, str):
                return not_string("pattern")
        elif tool_use.name == "Read":
            value = tool_use.input.get("file_path") or tool_use.input.get("path")
            if value is None:
                return {
                    "tool_name": tool_use.name,
                    "input_type": "object",
                    "message": "The parameter `file_path` or `path` is required and must be a string.",
                }
            if not isinstance(value, str):
                return {
                    "tool_name": tool_use.name,
                    "input_type": _json_type_name(value),
                    "message": "The parameter `file_path` or `path` must be a string.",
                }
        return None

    def _tool_cache_path(self, trace_id: str, tool_use: ToolUseBlock, suffix: str) -> str:
        base = _safe_name(f"{trace_id}_{tool_use.id}_{suffix}")
        return f"{TOOL_CACHE_ROOT.rstrip('/')}/{base}"

    def _write_artifact(self, path: str, content: str, *, remote: bool) -> dict:
        if remote:
            try:
                client = self._get_client()
                resp = client.post(
                    f"{self._sandbox_url}/write",
                    json={"path": path, "content": content},
                    headers=self._identity_headers(),
                )
                body = resp.json()
                if self._is_infra_body(resp.status_code, body):
                    raise SandboxInfraError(
                        str(body.get("error_code") or "sandbox_transport"),
                        str(body.get("message") or body.get("error") or body),
                        diagnostics=dict(body.get("diagnostics") or {}),
                    )
                if resp.status_code >= 400 or isinstance(body, dict) and body.get("error"):
                    return {"ok": False, "error": body}
                return {"ok": True, "response": body}
            except SandboxInfraError:
                raise
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

        local_root = Path(".tool_cache").resolve()
        local_root.mkdir(parents=True, exist_ok=True)
        local_path = local_root / Path(path).name
        local_path.write_text(content, encoding="utf-8")
        return {"ok": True, "response": {"written": str(local_path), "bytes": _byte_len(content)}}

    def _stage_large_text(
        self,
        *,
        tool_use: ToolUseBlock,
        trace_id: str,
        label: str,
        text: str,
        remote: bool,
        threshold: int | None = None,
    ) -> dict | None:
        threshold = MAX_INLINE_TOOL_RESULT_CHARS if threshold is None else threshold
        if len(text) <= threshold:
            return None
        path = self._tool_cache_path(trace_id, tool_use, label)
        write_result = self._write_artifact(path, text, remote=remote)
        staged = {
            f"{label}_path": path,
            "total_chars": len(text),
            "total_bytes": _byte_len(text),
            "sha256": _sha256_text(text),
            "truncated": True,
            "read_hint": _read_hint(path),
            **_preview_payload(text),
        }
        if not write_result.get("ok"):
            staged["artifact_write_error"] = write_result.get("error")
        return staged

    def _apply_output_policy(
        self,
        tool_use: ToolUseBlock,
        trace_id: str,
        body: dict,
        *,
        remote: bool,
    ) -> dict:
        if not isinstance(body, dict):
            return body
        out = dict(body)
        if tool_use.name == "Bash":
            for key in ("stdout", "stderr"):
                value = out.get(key)
                if isinstance(value, str):
                    staged = self._stage_large_text(
                        tool_use=tool_use,
                        trace_id=trace_id,
                        label=key,
                        text=value,
                        remote=remote,
                    )
                    if staged is not None:
                        out[key] = staged
        elif tool_use.name == "Grep":
            value = out.get("output")
            if isinstance(value, str):
                staged = self._stage_large_text(
                    tool_use=tool_use,
                    trace_id=trace_id,
                    label="output",
                    text=value,
                    remote=remote,
                )
                if staged is not None:
                    staged.pop("preview_tail", None)
                    staged["total_lines"] = len(value.splitlines())
                    staged["preview_lines"] = value.splitlines()[:20]
                    out["output"] = staged
        elif tool_use.name == "Read":
            value = out.get("content")
            if isinstance(value, str) and len(value) > MAX_READ_INLINE_CHARS:
                raw_path = tool_use.input.get("file_path") or tool_use.input.get("path") or ""
                out["content"] = value[:TOOL_RESULT_PREVIEW_CHARS]
                out["content_truncated"] = True
                out["total_chars"] = len(value)
                out["total_bytes"] = _byte_len(value)
                out["sha256"] = _sha256_text(value)
                out["read_hint"] = _read_hint(str(raw_path))
        return out

    def _apply_generic_output_policy(
        self,
        tool_use: ToolUseBlock,
        trace_id: str,
        result: ToolResultBlock,
    ) -> ToolResultBlock:
        """Stage oversized results from non-sandbox (mock-service) tools.

        Task mock-service tools (declared via ``tool_endpoints``, e.g.
        ``ocr_extract_text``) are routed through the plain HTTP dispatcher and
        otherwise bypass output staging entirely, so a large result (e.g. a
        full-document OCR dump) is injected verbatim and can blow the model's
        per-message token budget. Mirror ``_apply_output_policy``: write the full
        text to a workspace artifact and return a bounded preview + read_hint so
        the model can page through it via Read(offset, limit). See v0.50.11 (T080
        ocr_extract_text returned 428K chars -> 400 max-message-tokens).

        Returns the result unchanged when it is already within budget. The trace
        ``ToolDispatch.response_body`` is intentionally left intact so the full
        tool output remains observable for replay/debugging.
        """
        blocks = list(getattr(result, "content", None) or [])
        if not blocks or any(getattr(b, "text", None) is None for b in blocks):
            return result
        full_text = "".join(b.text for b in blocks)
        staged = self._stage_large_text(
            tool_use=tool_use,
            trace_id=trace_id,
            label="result",
            text=full_text,
            remote=bool(self._sandbox_url),
        )
        if staged is None:
            return result
        return ToolResultBlock(
            tool_use_id=result.tool_use_id,
            content=[TextBlock(text=json.dumps(staged, ensure_ascii=False))],
            is_error=result.is_error,
        )

    @staticmethod
    def _tool_input_error_message(tool_use: ToolUseBlock, marker: dict) -> str:
        provided = marker.get("input_type") or "unknown"
        message = marker.get("message")
        if not message:
            message = (
                "The parameter `tool_use.input` type is expected as `object` "
                f"but provided as `{provided}`."
            )
        return (
            "<tool_use_error>InputValidationError: "
            f"{tool_use.name} failed due to the following issue:\n"
            f"{message}</tool_use_error>"
        )

    def _tool_input_error_result(
        self,
        tool_use: ToolUseBlock,
        trace_id: str,
        marker: dict,
    ) -> tuple[ToolResultBlock, ToolDispatch, list[ImageBlock] | None]:
        error_msg = self._tool_input_error_message(tool_use, marker)
        result = ToolResultBlock(
            tool_use_id=tool_use.id,
            content=[TextBlock(text=error_msg)],
            is_error=True,
        )
        event = ToolDispatch(
            trace_id=trace_id,
            tool_use_id=tool_use.id,
            tool_name=tool_use.name,
            endpoint_url=f"local://sandbox/{tool_use.name}/input-validation",
            request_body=tool_use.input,
            response_status=400,
            response_body={"error": error_msg, "marker": marker},
            latency_ms=0.0,
        )
        return result, event, None

    @staticmethod
    def _error_result(
        tool_use: ToolUseBlock,
        trace_id: str,
        error_msg: str,
        *,
        status: int = 500,
        latency_ms: float = 0.0,
        endpoint_url: str | None = None,
    ) -> tuple[ToolResultBlock, ToolDispatch, list[ImageBlock] | None]:
        result = ToolResultBlock(
            tool_use_id=tool_use.id,
            content=[TextBlock(text=f"Error: {error_msg}")],
            is_error=True,
        )
        dispatch_event = ToolDispatch(
            trace_id=trace_id,
            tool_use_id=tool_use.id,
            tool_name=tool_use.name,
            endpoint_url=endpoint_url or f"local://sandbox/{tool_use.name}",
            request_body=tool_use.input,
            response_status=status,
            response_body={"error": error_msg},
            latency_ms=latency_ms,
        )
        return result, dispatch_event, None
