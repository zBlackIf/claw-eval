"""Real Web API proxy service for agent evaluation (FastAPI on port 9114).

v0.30.15 ark overlay: surface SERP provider failures in /web/search response
bodies, and avoid caching provider-error empty results.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Real Web API Proxy")

from mock_services._base import add_error_injection

add_error_injection(app)


CACHE_DIR = Path(os.environ.get("WEB_REAL_CACHE_DIR", "/tmp/web_real_cache"))
CACHE_TTL_HOURS = int(os.environ.get("CACHE_TTL", "24"))
MAX_SEARCHES = int(os.environ.get("MAX_SEARCHES", "20"))
MAX_FETCHES = int(os.environ.get("MAX_FETCHES", "30"))
MAX_CONTENT_CHARS = 50_000

_search_count = 0
_fetch_count = 0
_audit_log: list[dict[str, Any]] = []
_notifications: list[dict[str, Any]] = []

CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_key(prefix: str, value: str) -> str:
    return hashlib.sha256(f"{prefix}:{value}".encode()).hexdigest()


def _search_cache_scope() -> str:
    # SERP_API_URL carries the run-level provider query parameter injected by
    # the Ark backend. Keep provider-specific search responses isolated.
    return os.environ.get("SERP_API_URL", "")


def _cache_get(key: str) -> dict | None:
    cache_file = CACHE_DIR / f"{key}.json"
    if not cache_file.exists():
        return None
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        cached_at = data.get("_cached_at", 0)
        if time.time() - cached_at > CACHE_TTL_HOURS * 3600:
            cache_file.unlink(missing_ok=True)
            return None
        data.pop("_cached_at", None)
        return data
    except Exception:
        return None


def _cache_set(key: str, data: dict) -> None:
    try:
        to_write = {**data, "_cached_at": time.time()}
        cache_file = CACHE_DIR / f"{key}.json"
        cache_file.write_text(json.dumps(to_write, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _extract_content(html: str, url: str) -> str:
    try:
        import trafilatura
        result = trafilatura.extract(html, url=url, include_links=True)
        if result:
            return result[:MAX_CONTENT_CHARS]
    except ImportError:
        pass

    import re
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_CONTENT_CHARS]


def _extract_title(html: str) -> str:
    import re
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""


def _log_call(endpoint: str, request_body: dict[str, Any], response_body: Any) -> None:
    _audit_log.append({
        "endpoint": endpoint,
        "request_body": request_body,
        "response_body": response_body,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


class SearchRequest(BaseModel):
    query: str
    max_results: int = 10


class FetchRequest(BaseModel):
    url: str
    timeout_seconds: int = 30


class NotifyRequest(BaseModel):
    channel: str = Field(..., description="Notification channel: email, slack, sms, etc.")
    message: str = Field(..., description="Notification content")
    recipients: list[str] = Field(default_factory=list)


@app.get("/web/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/web/search")
def web_search(req: SearchRequest) -> dict[str, Any]:
    global _search_count

    if _search_count >= MAX_SEARCHES:
        resp = {
            "results": [],
            "total": 0,
            "query": req.query,
            "error": f"Session search limit reached ({MAX_SEARCHES})",
        }
        _log_call("/web/search", req.model_dump(), resp)
        return resp

    cache_k = _cache_key("search", f"{_search_cache_scope()}:{req.query}:{req.max_results}")
    cached = _cache_get(cache_k)
    if cached:
        resp = cached
        _log_call("/web/search", req.model_dump(), resp)
        return resp

    _search_count += 1

    try:
        from search_serp import search_serp
    except ImportError as exc:
        print(f"search_serp module not available: {exc}", file=sys.stderr)
        resp = {
            "results": [],
            "total": 0,
            "query": req.query,
            "error": f"search_serp module not found: {exc}",
        }
        _log_call("/web/search", req.model_dump(), resp)
        return resp

    try:
        num = min(req.max_results, 10)
        serp_result = search_serp(query=req.query, num=num, timeout=20)
        provider_status = int(serp_result.get("status") or 0)
        provider_error = str(serp_result.get("error") or "").strip()
        if provider_error or provider_status != 200:
            resp = {
                "results": [],
                "total": 0,
                "query": req.query,
                "error": provider_error or f"SERP provider returned status {provider_status}",
                "provider_status": provider_status,
            }
            _log_call("/web/search", req.model_dump(), resp)
            return resp

        results = []
        for item in serp_result.get("output", []):
            results.append({
                "url": item.get("link", ""),
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "source": "",
                "published_at": item.get("date", ""),
            })

        resp = {"results": results, "total": len(results), "query": req.query}
        _cache_set(cache_k, resp)
    except Exception as exc:  # noqa: BLE001 - trace should show unexpected web_real failures.
        print(f"SERP API error: {exc}", file=sys.stderr)
        resp = {
            "results": [],
            "total": 0,
            "query": req.query,
            "error": f"Search failed: {str(exc)[:200]}",
        }

    _log_call("/web/search", req.model_dump(), resp)
    return resp


@app.post("/web/fetch")
def web_fetch(req: FetchRequest) -> dict[str, Any]:
    global _fetch_count

    if _fetch_count >= MAX_FETCHES:
        resp = {
            "status_code": 429,
            "url": req.url,
            "error": f"Session fetch limit reached ({MAX_FETCHES})",
            "content": None,
        }
        _log_call("/web/fetch", req.model_dump(), resp)
        return resp

    cache_k = _cache_key("fetch", req.url)
    cached = _cache_get(cache_k)
    if cached:
        resp = cached
        _log_call("/web/fetch", req.model_dump(), resp)
        return resp

    _fetch_count += 1

    try:
        import httpx
        with httpx.Client(timeout=req.timeout_seconds, follow_redirects=True) as client:
            response = client.get(req.url, headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                )
            })

        content_type = response.headers.get("content-type", "")
        html = response.text
        content = _extract_content(html, req.url)
        title = _extract_title(html)

        resp = {
            "status_code": response.status_code,
            "url": str(response.url),
            "title": title,
            "content": content,
            "content_type": content_type,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        if response.status_code == 200 and content:
            _cache_set(cache_k, resp)
    except Exception as exc:  # noqa: BLE001 - preserve error for trace.
        print(f"Fetch error for {req.url}: {exc}", file=sys.stderr)
        resp = {
            "status_code": 500,
            "url": req.url,
            "error": f"Fetch failed: {str(exc)[:200]}",
            "content": None,
        }

    _log_call("/web/fetch", req.model_dump(), resp)
    return resp


@app.post("/web/notify")
def web_notify(req: NotifyRequest) -> dict[str, Any]:
    resp = {
        "success": False,
        "error": "Real notifications are disabled in evaluation environment",
        "channel": req.channel,
    }
    _notifications.append({
        **req.model_dump(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    _log_call("/web/notify", req.model_dump(), resp)
    return resp


@app.get("/web/audit")
def get_audit() -> dict[str, Any]:
    return {"calls": _audit_log, "notifications": _notifications}


@app.post("/web/reset")
def reset() -> dict[str, str]:
    global _search_count, _fetch_count, _audit_log, _notifications
    _search_count = 0
    _fetch_count = 0
    _audit_log = []
    _notifications = []
    return {"status": "reset"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "9114")))
