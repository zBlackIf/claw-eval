"""WeChat platform message handler.

Currently handles ALL business logic inline:
- Express tracking (pattern matching for tracking numbers)
- Train ticket queries
- Reminder management
- General chat (LLM fallback)

This violates SRP and makes the codebase hard to maintain.
Every new feature requires modifying this file.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class WeixinPlatform:
    """WeChat message handler - currently a monolith."""

    def __init__(self, config: dict):
        self.config = config
        self.express_appcode = config.get("alicloud_appcode", "")

    async def _process_message(self, user_id: str, message: str) -> str:
        """Process incoming WeChat message.

        WARNING: This method handles ALL business routing and logic.
        It should only handle message receiving and response sending.
        """
        logger.info(f"Received message from {user_id}: {message[:50]}")

        # Express tracking - hardcoded pattern matching
        tracking_pattern = r'\b\d{12,15}\b'
        tracking_match = re.search(tracking_pattern, message)
        if tracking_match and any(kw in message for kw in ['查', '快递', '物流', 'track']):
            tracking_number = tracking_match.group()
            logger.info(f"Express query detected: {tracking_number}")
            result = await self._query_express(tracking_number)
            return result

        # Train ticket - hardcoded
        if any(kw in message for kw in ['火车', '高铁', '车票', 'train']):
            return "Train ticket query is not yet implemented"

        # Reminder - hardcoded
        if any(kw in message for kw in ['提醒', '闹钟', 'remind']):
            return "Reminder feature is not yet implemented"

        # Default: chat via LLM
        return await self._chat_with_llm(user_id, message)

    async def _query_express(self, tracking_number: str) -> str:
        """Query express tracking info via AliCloud API."""
        import aiohttp
        url = f"https://wuliu.market.alicloudapi.com/kdi?no={tracking_number}"
        headers = {"Authorization": f"APPCODE {self.express_appcode}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return self._format_express_result(data)
                else:
                    return f"Express query failed with status {resp.status}"

    def _format_express_result(self, data: dict) -> str:
        """Format express API response into human-readable message."""
        result = data.get("result", {})
        company = result.get("expName", "Unknown")
        traces = result.get("list", [])
        if not traces:
            return "No tracking information found"
        lines = [f"Carrier: {company}"]
        for trace in traces[:5]:
            lines.append(f"  {trace.get('time', '')}: {trace.get('status', '')}")
        return "\n".join(lines)

    async def _chat_with_llm(self, user_id: str, message: str) -> str:
        """Fallback to LLM for general chat."""
        return f"[LLM response placeholder for: {message[:30]}]"
