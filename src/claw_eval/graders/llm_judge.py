"""LLM-as-judge for subjective communication quality scoring.

v0.30.1 ark overlay: adds three-protocol dispatch (OpenAI Chat Completions /
OpenAI Responses / Anthropic Messages). Selection is driven by api_format on
the JudgeConfig in config.yaml — see backend/benchmarks/claweval/_overlays/README.md.
"""

from __future__ import annotations

import json
import random
import re
import time

from openai import OpenAI
from pydantic import BaseModel

from ..config import get_last_loaded_config
from ..models.trace import _now

DEFAULT_MAX_RETRIES = 30


def _normalize_max_retries(value: int | None, default: int = DEFAULT_MAX_RETRIES) -> int:
    if value is None:
        return default
    retries = int(value)
    if retries < 0:
        raise ValueError("max_retries must be >= 0")
    return retries


class JudgeResult(BaseModel):
    score: float  # 0.0-1.0
    reasoning: str


class JudgeParseExhaustedError(RuntimeError):
    """Raised when the judge never returns a parseable score after retries."""


_SYSTEM_PROMPT = """\
You are an evaluation judge for an AI assistant.
You will be given a task prompt, a conversation, a summary of actions taken, and a rubric.
Follow the rubric to score the assistant's response on a 0.0-1.0 scale.
Respond with JSON only: {"score": <float>, "reasoning": "<brief explanation>"}
"""

_ACTIONS_SYSTEM_PROMPT = """\
You are an evaluation judge for an AI agent's actions.
You will be given a task prompt, a record of actions the agent actually performed \
(extracted from the server-side audit log, not from the agent's self-report), \
and a rubric.
Follow the rubric to score the quality of the agent's actions on a 0.0-1.0 scale.
Respond with JSON only: {"score": <float>, "reasoning": "<brief explanation>"}
"""

_VISUAL_SYSTEM_PROMPT = """\
You are a STRICT visual evaluation judge. Your job is to compare candidate images \
against reference images and/or a detailed rubric, then assign a score from 0.0 to 1.0.

CRITICAL RULES:
- You must be HARSH and PRECISE. Do NOT give generous scores.
- If the rubric describes specific content (e.g., specific notes, pitches, patterns, \
station names, colors), you MUST verify each detail. Getting the general layout right \
but the specific content wrong should score LOW (0.1-0.3).
- A visually "nice-looking" output that has WRONG content is a FAILURE.
- Only score above 0.5 if the MAJORITY of rubric criteria are clearly satisfied.
- Only score above 0.7 if the content is substantially correct with minor issues.
- Only score above 0.9 if the output is nearly perfect.
- Score 0.0-0.2 if the output is mostly wrong or unrecognizable.
- When reference images are provided, compare the candidate DIRECTLY against them — \
the reference is ground truth.

Respond with JSON only: {"score": <float>, "reasoning": "<brief explanation>"}
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
    return "openai-completions"


def _resolve_judge_api_format(model_id: str) -> str:
    """Read api_format from the active JudgeConfig (set by load_config in cli.py)."""
    cfg = get_last_loaded_config()
    if cfg is None:
        return "openai-completions"
    # Normal case: judge.model_id matches the model_id we're being constructed with
    if model_id == cfg.judge.model_id and cfg.judge.api_format is not None:
        return _normalize_api_format(cfg.judge.api_format)
    # Fallback: when judge==model (smoke runs), match against model side
    if model_id == cfg.model.model_id and cfg.model.api_format is not None:
        return _normalize_api_format(cfg.model.api_format)
    return "openai-completions"


def _resolve_judge_extra_body(model_id: str) -> dict:
    cfg = get_last_loaded_config()
    if cfg is None:
        return {}
    if model_id == cfg.judge.model_id:
        value = getattr(cfg.judge, "extra_body", None)
        return dict(value) if isinstance(value, dict) else {}
    if model_id == cfg.model.model_id:
        value = getattr(cfg.model, "extra_body", None)
        extra = dict(value) if isinstance(value, dict) else {}
        if getattr(cfg.model, "temperature", 0.0) is None and "temperature" not in extra:
            extra["temperature"] = None
        return extra
    return {}


def _content_parts_to_anthropic(content_parts: list[dict]) -> list[dict]:
    """Convert OpenAI-style content parts (text + image_url) to Anthropic blocks."""
    blocks: list[dict] = []
    for part in content_parts:
        ptype = part.get("type")
        if ptype == "text":
            blocks.append({"type": "text", "text": part.get("text", "")})
        elif ptype == "image_url":
            url = (part.get("image_url") or {}).get("url", "")
            # Expect data URLs like "data:image/png;base64,<b64>"
            m = re.match(r"data:([^;]+);base64,(.+)", url)
            if m:
                blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": m.group(1),
                        "data": m.group(2),
                    },
                })
            # else: silently drop non-base64 image refs (Anthropic Messages
            # does not accept arbitrary URLs in all gateways).
    return blocks


def _content_parts_to_responses(content_parts: list[dict]) -> list[dict]:
    """Convert OpenAI Chat-style content parts to OpenAI Responses input parts."""
    out: list[dict] = []
    for part in content_parts:
        ptype = part.get("type")
        if ptype == "text":
            out.append({"type": "input_text", "text": part.get("text", "")})
        elif ptype == "image_url":
            url = (part.get("image_url") or {}).get("url", "")
            out.append({"type": "input_image", "image_url": url})
    return out


# ----------------------------------------------------------------------
# v0.30.1: OpenAI-shape facade over Anthropic SDK.
#
# Some upstream task graders (tasks/T001zh_email_triage/grader.py and
# T002_email_triage/grader.py at pin 39b27dcc) bypass LLMJudge.evaluate
# and call ``judge.client.chat.completions.create(...)`` directly. When
# api_format=anthropic-messages, the underlying client is an Anthropic
# instance which has no ``.chat`` attribute → AttributeError storms.
#
# Rather than patching every task grader, we wrap the Anthropic client in
# a facade that also quacks like OpenAI: ``.chat.completions.create`` is
# translated to ``.messages.create`` and the response is duck-typed to look
# like an OpenAI ChatCompletion (with .choices[0].message.content). The
# native ``.messages`` attribute is preserved for our own _call_llm path.
# ----------------------------------------------------------------------


class _OpenAIChatRespShim:
    """Duck-typed OpenAI ChatCompletion response."""

    class _Msg:
        def __init__(self, content: str):
            self.content = content

    class _Choice:
        def __init__(self, message):
            self.message = message

    def __init__(self, content: str):
        self.choices = [self._Choice(self._Msg(content))]


class _AnthropicAsOpenAIChatShim:
    """Translates ``.chat.completions.create(...)`` calls into Anthropic ``.messages.create(...)``.

    Only handles the call signature used by upstream task graders: model,
    messages (list of {role, content}), temperature, max_tokens. Tool calls
    are NOT supported on this shim — graders that need tool-calling should
    go through ``LLMJudge.evaluate*`` instead, which dispatches properly.
    """

    def __init__(self, anth_client):
        self._anth = anth_client

    @property
    def completions(self):
        return self

    def create(self, *, model: str, messages: list[dict],
               temperature: float = 0.0, max_tokens: int = 8192,
               **_extra):
        system_parts: list[str] = []
        anth_messages: list[dict] = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if isinstance(content, str):
                text = content
            else:
                # OpenAI list-of-parts content; only keep text parts here
                # (the legacy grader pattern uses string content anyway).
                text = "\n".join(
                    p.get("text", "")
                    for p in content
                    if isinstance(p, dict) and p.get("type") in ("text", "input_text")
                )
            if role == "system":
                system_parts.append(text)
                continue
            anth_messages.append({
                "role": role,
                "content": [{"type": "text", "text": text}],
            })

        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": anth_messages,
        }
        if system_parts:
            kwargs["system"] = "\n\n".join(p for p in system_parts if p)

        resp = self._anth.messages.create(**kwargs)
        text = "".join(
            getattr(b, "text", "") or ""
            for b in (resp.content or [])
            if getattr(b, "type", None) == "text"
        )
        return _OpenAIChatRespShim(text)


class _AnthropicFacade:
    """Wraps an Anthropic client to expose both native + OpenAI-shape APIs.

    - ``.messages.create(...)``                     → native passthrough
    - ``.chat.completions.create(...)``             → translated to messages.create
    """

    def __init__(self, anth_client):
        self._anth = anth_client

    @property
    def messages(self):
        return self._anth.messages

    @property
    def chat(self):
        return _AnthropicAsOpenAIChatShim(self._anth)


class LLMJudge:
    """Judge communication quality using an LLM.

    v0.30.1: protocol selection comes from JudgeConfig.api_format in config.yaml,
    matched against this judge's model_id via get_last_loaded_config(). Default
    is openai-completions (upstream behavior).
    """

    def __init__(
        self,
        model_id: str = "google/gemini-2.5-flash",
        api_key: str | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
        max_retries: int | None = None,
    ) -> None:
        self.model_id = model_id
        self._call_log: list[dict] = []
        self.max_retries = _normalize_max_retries(max_retries)
        self.api_format = _resolve_judge_api_format(model_id)
        self.extra_body = _resolve_judge_extra_body(model_id)
        self._base_url = base_url
        self._api_key = api_key

        if self.api_format == "anthropic-messages":
            from anthropic import Anthropic
            # Anthropic SDK expects base_url WITHOUT trailing /v1; it appends /v1/messages itself
            anthropic_base = base_url.rstrip("/")
            if anthropic_base.endswith("/v1"):
                anthropic_base = anthropic_base[:-3].rstrip("/")
            anth_client = Anthropic(api_key=api_key or "dummy", base_url=anthropic_base or None)
            # v0.30.1: wrap in OpenAI-shape facade so legacy task graders that
            # do `judge.client.chat.completions.create(...)` still work
            # (T001zh_email_triage / T002_email_triage at upstream pin 39b27dcc).
            self.client = _AnthropicFacade(anth_client)
        else:
            # openai-completions and openai-responses both use the OpenAI SDK
            self.client = OpenAI(api_key=api_key or "dummy", base_url=base_url)

    # ------------------------------------------------------------------
    # Protocol-aware single-shot LLM call. content_parts (list of OpenAI-style
    # parts) takes precedence over user_msg (plain string) when provided.
    # ------------------------------------------------------------------
    def _call_llm(
        self,
        system_msg: str,
        user_msg: str | None = None,
        content_parts: list[dict] | None = None,
    ) -> str:
        if self.api_format == "anthropic-messages":
            request_extra = dict(getattr(self, "extra_body", {}) or {})
            temperature = request_extra.pop("temperature", 0.0)
            max_tokens = request_extra.pop("max_tokens", 8192)
            request_extra.pop("thinking", None)
            if content_parts is not None:
                anth_content = _content_parts_to_anthropic(content_parts)
            else:
                anth_content = [{"type": "text", "text": user_msg or ""}]
            kwargs = {
                "model": self.model_id,
                "max_tokens": max_tokens,
                "system": system_msg,
                "messages": [{"role": "user", "content": anth_content}],
            }
            if temperature is not None:
                kwargs["temperature"] = temperature
            if request_extra:
                kwargs.update(request_extra)
            resp = self.client.messages.create(**kwargs)
            for block in resp.content or []:
                if getattr(block, "type", None) == "text":
                    return block.text or "{}"
            return "{}"

        if self.api_format == "openai-responses":
            request_extra = dict(getattr(self, "extra_body", {}) or {})
            temperature = request_extra.pop("temperature") if "temperature" in request_extra else 0.0
            max_output_tokens = request_extra.pop("max_output_tokens", 8192)
            if content_parts is not None:
                user_input = _content_parts_to_responses(content_parts)
            else:
                user_input = [{"type": "input_text", "text": user_msg or ""}]
            kwargs = {
                "model": self.model_id,
                "max_output_tokens": max_output_tokens,
                "input": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_input},
                ],
            }
            if temperature is not None:
                kwargs["temperature"] = temperature
            if request_extra:
                kwargs["extra_body"] = request_extra
            resp = self.client.responses.create(**kwargs)
            return getattr(resp, "output_text", None) or "{}"

        # openai-completions (upstream default)
        request_extra = dict(getattr(self, "extra_body", {}) or {})
        temperature = request_extra.pop("temperature") if "temperature" in request_extra else 0.0
        max_tokens = request_extra.pop("max_tokens", 8192)
        if content_parts is not None:
            user_payload: str | list = content_parts
        else:
            user_payload = user_msg or ""
        kwargs = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_payload},
            ],
            "max_tokens": max_tokens,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        if request_extra:
            kwargs["extra_body"] = request_extra
        resp = self.client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or "{}"

    # ------------------------------------------------------------------
    # Shared JSON extraction.
    # ------------------------------------------------------------------
    @staticmethod
    def _strip_json_fence(raw: str) -> str:
        text = raw.strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
        if fenced:
            return fenced.group(1).strip()
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        return text.strip()

    @staticmethod
    def _score_from_object(parsed) -> tuple[float, str]:
        if not isinstance(parsed, dict):
            raise KeyError("score")
        if "score" not in parsed:
            raise KeyError("score")
        return float(parsed["score"]), str(parsed.get("reasoning", ""))

    @staticmethod
    def _parse_score(raw: str) -> tuple[float, str]:
        raw = LLMJudge._strip_json_fence(raw)
        try:
            parsed = json.loads(raw)
            return LLMJudge._score_from_object(parsed)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            pass

        decoder = json.JSONDecoder()
        for match in re.finditer(r"\{", raw):
            try:
                parsed, _idx = decoder.raw_decode(raw, match.start())
                return LLMJudge._score_from_object(parsed)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue

        score_m = re.search(
            r'"score"\s*:\s*(-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)',
            raw,
        )
        reason_m = re.search(r'"reasoning"\s*:\s*"((?:[^"\\]|\\.)*)"', raw)
        if score_m:
            reasoning = ""
            if reason_m:
                try:
                    reasoning = json.loads(f'"{reason_m.group(1)}"')
                except json.JSONDecodeError:
                    reasoning = reason_m.group(1)
            return float(score_m.group(1)), reasoning
        raise json.JSONDecodeError("No score found in raw", raw, 0)

    def _append_call_log(
        self,
        *,
        method: str,
        rubric: str,
        system_msg: str,
        user_msg: str,
        raw_response: str | None,
        attempt: int,
        max_attempts: int,
        result: JudgeResult | None = None,
        exc: Exception | None = None,
        status: object | None = None,
        extra: dict | None = None,
    ) -> None:
        entry = {
            "method": method,
            "rubric_preview": rubric[:300],
            "system_msg": system_msg,
            "user_msg": user_msg,
            "raw_response": raw_response or "",
            "attempt": attempt,
            "max_attempts": max_attempts,
            "timestamp": _now(),
        }
        if result is not None:
            entry.update({
                "score": result.score,
                "reasoning": result.reasoning,
            })
        if exc is not None:
            entry.update({
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "status": status,
            })
        if extra:
            entry.update(extra)
        self._call_log.append(entry)

    def _evaluate_with_retries(
        self,
        *,
        method: str,
        system_msg: str,
        user_msg: str,
        rubric: str,
        retry_label: str,
        call_kwargs: dict,
        log_extra: dict | None = None,
    ) -> JudgeResult:
        max_retries = _normalize_max_retries(getattr(self, "max_retries", None))
        max_attempts = max_retries + 1
        last_exc: Exception | None = None
        for attempt_index in range(max_attempts):
            attempt = attempt_index + 1
            raw: str | None = None
            try:
                raw = self._call_llm(system_msg, **call_kwargs)
                score, reasoning = self._parse_score(raw)
                result = JudgeResult(
                    score=max(0.0, min(1.0, float(score))),
                    reasoning=str(reasoning),
                )
                self._append_call_log(
                    method=method,
                    rubric=rubric,
                    system_msg=system_msg,
                    user_msg=user_msg,
                    raw_response=raw,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    result=result,
                    extra=log_extra,
                )
                return result
            except Exception as exc:
                last_exc = exc
                status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
                self._append_call_log(
                    method=method,
                    rubric=rubric,
                    system_msg=system_msg,
                    user_msg=user_msg,
                    raw_response=raw,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    exc=exc,
                    status=status,
                    extra=log_extra,
                )
                if attempt == max_attempts:
                    break
                delay = min(2 ** attempt, 8) + random.uniform(0, 1)
                print(f"[{retry_label}] ({status or type(exc).__name__}), "
                      f"attempt {attempt}/{max_attempts}, waiting {delay:.1f}s ...")
                time.sleep(delay)

        raise JudgeParseExhaustedError(
            f"judge {method} exhausted after {max_attempts} attempts: "
            f"{type(last_exc).__name__}: {last_exc}"
        ) from last_exc

    def evaluate(
        self,
        task_prompt: str,
        conversation: str,
        actions_summary: str,
        rubric: str,
    ) -> JudgeResult:
        """Evaluate communication quality and return a JudgeResult."""
        user_msg = (
            f"## Task Prompt\n{task_prompt}\n\n"
            f"## Conversation\n{conversation}\n\n"
            f"## Actions Taken\n{actions_summary}\n\n"
            f"## Rubric\n{rubric}"
        )
        return self._evaluate_with_retries(
            method="evaluate",
            system_msg=_SYSTEM_PROMPT,
            user_msg=user_msg,
            rubric=rubric,
            retry_label="judge-retry",
            call_kwargs={"user_msg": user_msg},
        )

    def evaluate_actions(
        self,
        task_prompt: str,
        artifacts: str,
        rubric: str,
    ) -> JudgeResult:
        """Evaluate the quality of agent actions/artifacts from audit log."""
        user_msg = (
            f"## Task Prompt\n{task_prompt}\n\n"
            f"## Agent Actions (from server audit log)\n{artifacts}\n\n"
            f"## Rubric\n{rubric}"
        )
        return self._evaluate_with_retries(
            method="evaluate_actions",
            system_msg=_ACTIONS_SYSTEM_PROMPT,
            user_msg=user_msg,
            rubric=rubric,
            retry_label="judge-retry",
            call_kwargs={"user_msg": user_msg},
        )

    def evaluate_visual(
        self,
        rubric: str,
        reference_images_b64: list[str],
        candidate_images_b64: list[str],
        context: str = "",
    ) -> JudgeResult:
        """Evaluate visual similarity between reference and candidate images."""
        content_parts: list[dict] = []

        header = "## Visual Evaluation\n"
        if context:
            header += f"{context}\n\n"
        header += f"## Rubric\n{rubric}\n\n"
        header += (
            "## Scoring Calibration\n"
            "- 0.0-0.2: Output is mostly wrong, unrecognizable, or missing most required content\n"
            "- 0.2-0.4: Some elements present but major content errors (wrong notes, wrong colors, wrong layout)\n"
            "- 0.4-0.6: General structure is right but significant content inaccuracies remain\n"
            "- 0.6-0.8: Most content is correct with some minor issues\n"
            "- 0.8-1.0: Content is substantially correct, matching reference closely\n\n"
            "IMPORTANT: Looking nice is NOT enough. The CONTENT must be accurate. "
            "Check each rubric criterion individually and sum up the weighted scores.\n\n"
        )
        header += "Below are reference images followed by candidate images.\n"
        header += 'Respond with JSON only: {"score": <float>, "reasoning": "<brief explanation>"}'
        content_parts.append({"type": "text", "text": header})

        if reference_images_b64:
            content_parts.append({"type": "text", "text": f"\n### Reference ({len(reference_images_b64)} images)"})
            for img_b64 in reference_images_b64:
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                })

        if candidate_images_b64:
            content_parts.append({"type": "text", "text": f"\n### Candidate ({len(candidate_images_b64)} images)"})
            for img_b64 in candidate_images_b64:
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                })

        # Capture the visual prompt as a synthetic user_msg (text +
        # image-count placeholder) so the UI can render the judge transcript
        # uniformly. We don't store base64 image bytes to keep call_log small.
        _text_parts = [
            p.get("text", "")
            for p in content_parts
            if isinstance(p, dict) and p.get("type") == "text"
        ]
        _user_msg = "\n".join(_text_parts) + (
            f"\n\n[reference images: {len(reference_images_b64)}, "
            f"candidate images: {len(candidate_images_b64)}]"
        )
        result = self._evaluate_with_retries(
            method="evaluate_visual",
            system_msg=_VISUAL_SYSTEM_PROMPT,
            user_msg=_user_msg,
            rubric=rubric,
            retry_label="judge-visual-retry",
            call_kwargs={"content_parts": content_parts},
            log_extra={
                "n_ref_images": len(reference_images_b64),
                "n_cand_images": len(candidate_images_b64),
                "context_preview": context[:200],
            },
        )
        print(f"[judge-visual] score={result.score:.2f} reasoning={result.reasoning[:200]}")
        return result

    def get_call_log(self) -> list[dict]:
        return list(self._call_log)

    def reset_call_log(self) -> None:
        self._call_log.clear()
