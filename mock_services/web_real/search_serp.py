"""
Search SERP - raw web skill.

v0.30.15 ark overlay: preserve provider failure detail so web_real traces can
show Brave/Ark quota, auth, parameter, and transport errors instead of only
showing a successful empty result list.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import requests


SERP_API_URL = os.getenv("SERP_API_URL", "https://scraperapi.novada.com/search")
SERP_DEV_KEY = os.getenv("SERP_DEV_KEY", "YOUR_API_KEY")
RATE_LIMIT_RETRY_HINT = "Upstream web search MCP is rate limited (QPS=5; please retry after a short delay)."


def _detect_language(query: str) -> tuple[str, str]:
    if re.search(r"[\u4e00-\u9fff]", query):
        return "zh", "cn"
    return "en", "us"


def _response_snippet(resp: requests.Response) -> str:
    try:
        payload = resp.json()
    except ValueError:
        return (resp.text or "")[:1000]
    if isinstance(payload, dict):
        for key in ("detail", "error", "message"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:1000]
    try:
        return json.dumps(payload, ensure_ascii=False)[:1000]
    except TypeError:
        return str(payload)[:1000]


def _error_result(status: int, message: str) -> dict[str, Any]:
    return {
        "status": status,
        "output": [],
        "error": message,
    }


def _with_rate_limit_retry_hint(message: str, *, status: int) -> str:
    if "QPS=5" in message or not _looks_like_rate_limit(message, status=status):
        return message
    return f"{message} | {RATE_LIMIT_RETRY_HINT}"


def _looks_like_rate_limit(message: str, *, status: int) -> bool:
    lowered = message.lower()
    if status == 429:
        return True
    return any(
        marker in lowered
        for marker in (
            "rate limit",
            "rate_limit",
            "ratelimit",
            "too many requests",
            "too frequent",
            "qps",
        )
    )


def search_serp(
    query: str,
    timeout: int = 20,
    num: int = 10,
    start: int = 1,
    raw_save_path: str | None = None,
) -> dict[str, Any]:
    """Search Google via SERP API and return extracted results."""
    hl, gl = _detect_language(query)
    params = {
        "engine": "google",
        "api_key": SERP_DEV_KEY,
        "q": query,
        "num": str(min(max(num, 1), 10)),
        "hl": hl,
        "gl": gl,
        "start": str(max(start, 1)),
        "fetch_mode": "static",
        "no_cache": "true",
    }
    task_id = os.getenv("CLAW_EVAL_TASK_ID", "").strip()
    if task_id:
        params["task_id"] = task_id
    try:
        resp = requests.get(SERP_API_URL, params=params, timeout=timeout)
        if raw_save_path and resp.status_code == 200:
            os.makedirs(os.path.dirname(raw_save_path) or ".", exist_ok=True)
            with open(raw_save_path, "w", encoding="utf-8") as f:
                f.write(resp.text)
        if resp.status_code != 200:
            detail = _response_snippet(resp)
            return _error_result(
                resp.status_code,
                _with_rate_limit_retry_hint(
                    f"SERP provider HTTP {resp.status_code}: {detail}",
                    status=resp.status_code,
                ),
            )
        data = resp.json().get("data", {})
        results = [
            {
                "title": item.get("title", ""),
                "link": item.get("url", ""),
                "snippet": item.get("description", ""),
                "date": item.get("date", ""),
                "query": query,
            }
            for item in data.get("organic_results", [])
        ]
        return {"status": resp.status_code, "output": results}
    except requests.RequestException as exc:
        return _error_result(
            -1,
            f"SERP provider request failed: {type(exc).__name__}: {exc}",
        )
    except Exception as exc:  # noqa: BLE001 - trace should show unexpected adapter failures.
        return _error_result(
            -1,
            f"SERP provider adapter failed: {type(exc).__name__}: {exc}",
        )


if __name__ == "__main__":
    result = search_serp("Python web scraping", num=3)
    print(f"status={result['status']}  count={len(result['output'])}")
    print(json.dumps(result, indent=2, ensure_ascii=False)[:1000])
