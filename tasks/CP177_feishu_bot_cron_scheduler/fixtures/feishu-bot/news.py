"""Feishu Bot - News aggregator."""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class NewsAggregator:
    """Aggregates hot news from multiple sources."""

    def __init__(self, searxng_url: str = "http://localhost:8080"):
        self.searxng_url = searxng_url

    def search_news(self, query: str, count: int = 5) -> list[dict[str, Any]]:
        """Search for news articles."""
        resp = httpx.get(
            f"{self.searxng_url}/search",
            params={
                "q": query,
                "format": "json",
                "categories": "news",
                "language": "zh",
                "pageno": 1,
            },
        )
        results = resp.json().get("results", [])
        return results[:count]

    def get_daily_hot_news(self, count: int = 5) -> list[dict[str, str]]:
        """Get daily hot news summary."""
        results = self.search_news("今日热点新闻", count=count)
        return [
            {"title": r.get("title", ""), "url": r.get("url", ""), "summary": r.get("content", "")}
            for r in results
        ]

    def format_news_bulletin(self, news_items: list[dict[str, str]]) -> str:
        """Format news items into a readable bulletin."""
        if not news_items:
            return "今日暂无热点新闻"
        lines = ["今日热点新闻:"]
        for i, item in enumerate(news_items, 1):
            lines.append(f"{i}. {item['title']}")
            if item.get("summary"):
                lines.append(f"   {item['summary'][:100]}")
        return "\n".join(lines)
